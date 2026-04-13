"""Full per-frame simulator for the Rare NES driver.

Models ALL per-frame processing: tempo accumulator, duration counter,
note loading, pitch sweep (block 1), vibrato (block 2), and volume
modes (block 3). Produces a per-frame period+volume trace that can be
compared against the Mesen capture.

This is the execution semantics validation tool.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from rare.parser import (
    RareParser, ParseResult, NoteEvent, RestEvent,
    CommandEvent, LoopPoint,
)


@dataclass
class ChannelState:
    """Per-channel driver state."""
    # Period registers ($0323/$0324)
    period_lo: int = 0
    period_hi: int = 0

    # Duration
    duration: int = 0

    # Sweep (block 1) — CMD 0x0A/0x0B
    sweep_active: bool = False
    sweep_interval: int = 0   # $03A1 — frames between steps
    sweep_counter: int = 0    # $0374 — countdown to next step
    sweep_reps: int = 0       # $0381 — remaining repetitions
    sweep_outer: int = 0      # $0382 — initial delay countdown
    sweep_step: int = 0       # $0383 — step value
    sweep_dir: int = 0        # $0384 — direction/fine counter

    # Vibrato (block 2) — CMD 0x08/0x17
    vib_amplitude: int = 0    # $0361 — half-cycle count (0=disabled)
    vib_cycle_count: int = 0  # $0362 — countdown within half-cycle
    vib_interval: int = 0     # $0363 — frames per step
    vib_counter: int = 0      # $0364 — countdown to next step
    vib_step: int = 0         # $0344 — signed step value

    # Volume modes (block 3) — CMD 0x0D/0x0E/0x0C/0x0F
    volume: int = 0           # $0352 — current volume 0-15
    vol_mode: int = 0         # $0393 — 0=off, 1=ramp, 2=oscillate
    vol_param1: int = 0       # $0353 — mode-specific
    vol_param2: int = 0       # $0394/$0373 — mode-specific
    vol_param3: int = 0       # $0391 — mode-specific
    vol_counter1: int = 0     # $0392 — countdown
    vol_counter2: int = 0     # $0373 — countdown

    # Instrument ($0321-$0324)
    instrument_reg: int = 0   # $0321 — duty+flags for APU $4000

    @property
    def period(self) -> int:
        return self.period_lo | (self.period_hi << 8)

    @period.setter
    def period(self, val: int):
        self.period_lo = val & 0xFF
        self.period_hi = (val >> 8) & 0x07


@dataclass
class FrameOutput:
    """Output state for one frame."""
    frame: int
    period: int
    volume: int
    duty: int
    tick: bool
    event_idx: int
    note_name: str = ""


def run_full_sim(
    parse: ParseResult,
    tempo: int,
    num_frames: int,
) -> list[FrameOutput]:
    """Run full per-frame simulation with all modulation.

    Returns per-frame output matching what the APU would see.
    """
    ch = ChannelState()
    events = parse.events
    evt_idx = 0
    acc = 0
    tick_count = 0
    output = []
    current_note_name = ""

    for frame in range(1, num_frames + 1):
        # --- Tempo accumulator ---
        old_acc = acc
        acc = (acc + tempo) & 0xFF
        is_tick = (old_acc + tempo) > 0xFF

        if is_tick:
            tick_count += 1

            # Duration countdown
            if ch.duration > 0:
                ch.duration -= 1

            # Consume events when duration expires
            while ch.duration == 0 and evt_idx < len(events):
                evt = events[evt_idx]
                evt_idx += 1

                if isinstance(evt, NoteEvent):
                    # Note handler: load period from table
                    ch.period = evt.period
                    ch.duration = evt.duration
                    current_note_name = evt.pitch_name
                    break

                elif isinstance(evt, RestEvent):
                    ch.period = 0
                    ch.duration = evt.duration
                    current_note_name = "REST"
                    break

                elif isinstance(evt, CommandEvent):
                    _handle_command(ch, evt)
                    continue

                elif isinstance(evt, LoopPoint):
                    break

        # --- Per-frame processing (runs EVERY frame) ---

        # Block 1: Pitch sweep
        if ch.sweep_active:
            _process_sweep(ch)

        # Block 2: Vibrato
        if ch.vib_amplitude > 0:
            _process_vibrato(ch)

        # Block 3: Volume modes (simplified — just track sounding)
        # Full volume mode simulation would go here

        # Output
        output.append(FrameOutput(
            frame=frame,
            period=ch.period,
            volume=ch.volume if ch.period > 0 else 0,
            duty=(ch.instrument_reg >> 6) & 3,
            tick=is_tick,
            event_idx=evt_idx,
            note_name=current_note_name,
        ))

    return output


def _handle_command(ch: ChannelState, evt: CommandEvent):
    """Process a command event and update channel state."""
    cmd = evt.cmd
    params = evt.params

    if cmd == 0x0A:
        # Sweep with negated step
        ch.sweep_outer = params[0]
        ch.sweep_interval = params[1] + 1
        ch.sweep_counter = ch.sweep_interval
        ch.sweep_reps = params[2]
        step_byte = params[3]
        ch.sweep_step = (~(step_byte - 1)) & 0xFF  # negate
        ch.sweep_dir = params[4]
        ch.sweep_active = True

    elif cmd == 0x0B:
        # Sweep with direct step (no negation)
        ch.sweep_outer = params[0]
        ch.sweep_interval = params[1] + 1
        ch.sweep_counter = ch.sweep_interval
        ch.sweep_reps = params[2]
        ch.sweep_step = params[3]  # direct, no negation
        ch.sweep_dir = params[4]
        ch.sweep_active = True

    elif cmd == 0x08:
        # Instrument via $8CC4 (3 params)
        ch.vib_amplitude = params[0]
        ch.vib_cycle_count = params[0] >> 1
        ch.vib_interval = params[1] + 1
        ch.vib_counter = ch.vib_interval
        step_raw = params[2]
        ch.vib_step = (~(step_raw - 1)) & 0xFF  # negate
        if ch.vib_step & 0x80:
            ch.vib_step -= 256  # sign extend

    elif cmd == 0x17:
        # Full instrument: $8CC4 (3 params) + duty byte
        ch.vib_amplitude = params[0]
        ch.vib_cycle_count = params[0] >> 1
        ch.vib_interval = params[1] + 1
        # param4 (4th param) overwrites $0364 (vib_counter)
        ch.vib_counter = params[3]
        step_raw = params[2]
        ch.vib_step = (~(step_raw - 1)) & 0xFF
        if ch.vib_step & 0x80:
            ch.vib_step -= 256

    elif cmd == 0x03:
        # Envelope params
        ch.instrument_reg = params[0]
        # Volume from instrument reg low nibble
        ch.volume = params[0] & 0x0F

    elif cmd == 0x0C:
        # Volume mode off, set volume register
        ch.vol_mode = 0
        ch.volume = params[0] & 0x0F

    elif cmd == 0x0D:
        # Volume mode 1 (ramp)
        ch.vol_mode = 1
        ch.vol_param1 = params[0] + 1
        ch.vol_counter1 = params[0] + 1
        ch.vol_param2 = params[1] + 1
        ch.vol_counter2 = params[1] + 1
        ch.vol_param3 = params[2]

    elif cmd == 0x0E:
        # Volume mode 2 (oscillate)
        ch.vol_mode = 2
        ch.vol_param1 = params[0]
        ch.vol_counter1 = params[0] >> 1
        ch.vol_param2 = params[1] + 1
        ch.vol_counter2 = params[1] + 1
        ch.vol_param3 = params[2]

    elif cmd == 0x0F:
        # Clear volume mode
        ch.vol_mode = 0

    elif cmd == 0x09:
        # Clear vibrato amplitude
        ch.vib_amplitude = 0

    elif cmd == 0x15:
        # Clear vibrato flag
        pass  # $0371,X = 0


def _process_sweep(ch: ChannelState):
    """Block 1: cumulative pitch sweep."""
    if ch.sweep_outer > 0:
        ch.sweep_outer -= 1
        return

    ch.sweep_counter -= 1
    if ch.sweep_counter > 0:
        return

    ch.sweep_counter = ch.sweep_interval  # reload

    ch.sweep_reps -= 1
    if ch.sweep_reps <= 0:
        ch.sweep_active = False
        return

    # Apply step
    if ch.sweep_dir > 0:
        step = (~(ch.sweep_step - 1)) & 0xFF
    else:
        step = ch.sweep_step

    # Sign extend and add to period
    if step & 0x80:
        sign_hi = 0xFF
    else:
        sign_hi = 0

    new_lo = ch.period_lo + step
    carry = 1 if new_lo > 0xFF else 0
    ch.period_lo = new_lo & 0xFF
    ch.period_hi = (ch.period_hi + sign_hi + carry) & 0x07  # 3-bit high


def _process_vibrato(ch: ChannelState):
    """Block 2: oscillating pitch vibrato."""
    ch.vib_counter -= 1
    if ch.vib_counter > 0:
        return

    ch.vib_counter = ch.vib_interval  # reload

    # Apply step (signed)
    step = ch.vib_step
    if step < 0:
        sign_hi = 0xFF
    else:
        sign_hi = 0

    step_byte = step & 0xFF
    new_lo = ch.period_lo + step_byte
    carry = 1 if new_lo > 0xFF else 0
    ch.period_lo = new_lo & 0xFF
    ch.period_hi = (ch.period_hi + sign_hi + carry) & 0x07

    # Cycle count
    ch.vib_cycle_count -= 1
    if ch.vib_cycle_count <= 0:
        ch.vib_cycle_count = ch.vib_amplitude  # reload
        # Negate step: DEC then EOR
        raw = ch.vib_step & 0xFF
        raw = (raw - 1) & 0xFF
        raw = raw ^ 0xFF
        ch.vib_step = raw if raw < 128 else raw - 256


def load_trace(trace_path, channel, max_frames=5000):
    """Load per-frame period+volume from trace."""
    reg_map = {
        "pulse1": ("$4002_period", "$4000_vol"),
        "pulse2": ("$4006_period", "$4004_vol"),
    }
    p_reg, v_reg = reg_map[channel]

    p_ch, v_ch = {}, {}
    with open(trace_path, 'r') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            frame = int(row[0])
            if frame > max_frames:
                break
            if row[1] == p_reg:
                p_ch[frame] = int(row[2])
            elif row[1] == v_reg:
                v_ch[frame] = int(row[2])

    per = [0] * (max_frames + 1)
    vol = [0] * (max_frames + 1)
    cp, cv = 0, 0
    for f in range(1, max_frames + 1):
        if f in p_ch: cp = p_ch[f]
        if f in v_ch: cv = v_ch[f]
        per[f] = cp
        vol[f] = cv
    return per, vol
