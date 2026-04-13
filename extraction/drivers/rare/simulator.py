"""Frame-by-frame execution simulator for the Rare NES driver.

Simulates the driver's tempo accumulator, duration counter, and
event advancement to produce per-frame APU state. This is then
compared against the Mesen trace to validate execution semantics.

This is NOT a musical interpretation layer. It's a driver model test.
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
class FrameState:
    """Simulated APU state for one channel on one frame."""
    frame: int
    period: int = 0         # base period from note (pre-arpeggio)
    volume: int = 0         # current volume level (0-15)
    duty: int = 0           # duty cycle (0-3)
    duration_left: int = 0  # remaining ticks for current note
    event_idx: int = 0      # which parsed event is active
    tick_happened: bool = False  # did a music tick occur this frame


@dataclass
class SimResult:
    """Result of frame simulation."""
    channel: str
    frames: list[FrameState]
    ticks_total: int
    events_consumed: int


@dataclass
class CompareResult:
    """Comparison of simulated vs trace state."""
    channel: str
    total_frames: int
    period_matches: int
    period_mismatches: int
    volume_matches: int
    volume_mismatches: int
    first_period_mismatch: int | None  # frame number
    first_volume_mismatch: int | None
    mismatches: list[dict]  # first N mismatches with details


def simulate_channel(
    parse: ParseResult,
    tempo: int,
    num_frames: int,
) -> SimResult:
    """Simulate the driver's frame-by-frame execution for one channel.

    Args:
        parse: Parsed event stream from RareParser.
        tempo: Initial tempo value (written to zp $33).
        num_frames: How many frames to simulate.

    Returns:
        SimResult with per-frame state.
    """
    frames = []
    accumulator = 0  # tempo accumulator ($32)
    current_tempo = tempo
    duration_counter = 0
    current_period = 0
    current_volume = 0
    current_duty = 0
    event_idx = 0
    ticks = 0
    events_consumed = 0

    # Pre-filter events into a flat list for sequential consumption
    events = parse.events

    for frame_num in range(1, num_frames + 1):
        # Tempo accumulator: 8-bit addition
        old_acc = accumulator
        accumulator = (accumulator + current_tempo) & 0xFF
        carry = (old_acc + current_tempo) > 0xFF
        tick = carry

        if tick:
            ticks += 1

            # Duration counter decrement
            if duration_counter > 0:
                duration_counter -= 1

            # If duration expired, consume events until we get a note/rest
            while duration_counter == 0 and event_idx < len(events):
                evt = events[event_idx]
                event_idx += 1
                events_consumed += 1

                if isinstance(evt, NoteEvent):
                    current_period = evt.period
                    duration_counter = evt.duration
                    # Volume would come from envelope, but we don't model that yet
                    # For now just mark as "note active"
                    current_volume = 6  # placeholder
                    break

                elif isinstance(evt, RestEvent):
                    current_period = 0
                    current_volume = 0
                    duration_counter = evt.duration
                    break

                elif isinstance(evt, CommandEvent):
                    # Commands that affect tempo
                    if evt.cmd == 0x10 and evt.params:
                        current_tempo = evt.params[0]
                    elif evt.cmd == 0x11 and evt.params:
                        current_tempo = (current_tempo + evt.params[0]) & 0xFF
                    # Other commands are handled by the parser's state tracking
                    # (transposition, duration mode, etc.)
                    continue

                elif isinstance(evt, LoopPoint):
                    break  # stop at loop

        fs = FrameState(
            frame=frame_num,
            period=current_period,
            volume=current_volume,
            duty=current_duty,
            duration_left=duration_counter,
            event_idx=event_idx,
            tick_happened=tick,
        )
        frames.append(fs)

    return SimResult(
        channel=parse.channel,
        frames=frames,
        ticks_total=ticks,
        events_consumed=events_consumed,
    )


def load_trace_channel(
    trace_path: str | Path,
    channel: str,
    max_frames: int = 5000,
) -> tuple[list[int], list[int]]:
    """Load per-frame period and volume from Mesen trace.

    Args:
        trace_path: Path to Mesen capture CSV.
        channel: "pulse1", "pulse2", "triangle", or "noise".
        max_frames: Maximum frames to load.

    Returns:
        (periods, volumes) — lists indexed by frame number.
    """
    # Map channel to register names
    reg_map = {
        "pulse1": ("$4002_period", "$4000_vol"),
        "pulse2": ("$4006_period", "$4004_vol"),
        "triangle": ("$400A_period", "$4008_vol"),
        "noise": ("$400E_period", "$400C_vol"),
    }
    period_reg, vol_reg = reg_map[channel]

    period_changes = {}
    vol_changes = {}

    with open(trace_path, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            frame = int(row[0])
            if frame > max_frames:
                break
            if row[1] == period_reg:
                period_changes[frame] = int(row[2])
            elif row[1] == vol_reg:
                vol_changes[frame] = int(row[2])

    # Build per-frame arrays
    periods = [0] * (max_frames + 1)
    volumes = [0] * (max_frames + 1)
    cur_p = 0
    cur_v = 0
    for f in range(1, max_frames + 1):
        if f in period_changes:
            cur_p = period_changes[f]
        if f in vol_changes:
            cur_v = vol_changes[f]
        periods[f] = cur_p
        volumes[f] = cur_v

    return periods, volumes


def compare_sim_trace(
    sim: SimResult,
    trace_periods: list[int],
    trace_volumes: list[int],
    max_mismatches: int = 20,
) -> CompareResult:
    """Compare simulated state against trace.

    NOTE: This comparison is PERIOD-LEVEL, not pitch-level.
    The sim gives the BASE period (from note handler).
    The trace gives the FINAL period (after arpeggio/vibrato).
    These WILL differ when arpeggio is active.

    For initial validation, we compare:
    - Note boundary timing (when does duration_counter hit zero?)
    - Volume transitions (when does volume go from 0 to non-zero?)
    """
    period_match = 0
    period_mismatch = 0
    vol_match = 0
    vol_mismatch = 0
    first_period_mm = None
    first_vol_mm = None
    mismatches = []

    for fs in sim.frames:
        f = fs.frame
        if f >= len(trace_periods):
            break

        # Period comparison (base vs trace)
        # NOTE: these WILL differ due to arpeggio. This is expected.
        # We only flag it for tracking, not as an error.
        if fs.period == trace_periods[f]:
            period_match += 1
        else:
            period_mismatch += 1
            if first_period_mm is None:
                first_period_mm = f

        # Volume comparison (coarse: both zero or both non-zero)
        sim_sounding = fs.volume > 0 and fs.period > 0
        trace_sounding = trace_volumes[f] > 0 and trace_periods[f] > 0
        if sim_sounding == trace_sounding:
            vol_match += 1
        else:
            vol_mismatch += 1
            if first_vol_mm is None:
                first_vol_mm = f
            if len(mismatches) < max_mismatches:
                mismatches.append({
                    "frame": f,
                    "sim_period": fs.period,
                    "trace_period": trace_periods[f],
                    "sim_vol": fs.volume,
                    "trace_vol": trace_volumes[f],
                    "sim_dur_left": fs.duration_left,
                    "sim_event": fs.event_idx,
                    "tick": fs.tick_happened,
                })

    total = len(sim.frames)
    return CompareResult(
        channel=sim.channel,
        total_frames=total,
        period_matches=period_match,
        period_mismatches=period_mismatch,
        volume_matches=vol_match,
        volume_mismatches=vol_mismatch,
        first_period_mismatch=first_period_mm,
        first_volume_mismatch=first_vol_mm,
        mismatches=mismatches,
    )
