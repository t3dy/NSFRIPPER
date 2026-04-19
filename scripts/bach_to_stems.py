#!/usr/bin/env python3
"""Render a Bach (or any) MIDI through synthetic NES frame-state into stems.

Pipeline: MIDI note events  ->  synthetic 60 Hz APU channels dict  ->
          render_channel_stems.render_stem() for p1/p2/tri/noise.

The resulting stems pass through the same DSP chain as NSF-captured stems:
bandlimited pulse synthesis (Rule 35), triangle hold-on-gate-off (Rule 34),
non-linear DAC mixing (Rule 27), 14 kHz analog LP (Rule 33), 10 Hz DC
blocker (Rule 33), and shared-scale normalization so REAPER summing on
master matches the outputv6 stems' loudness behavior.

Stage preset selects the pulse1/pulse2 duty cycles (timbral palette).

Usage:
    python scripts/bach_to_stems.py --midi <file.mid> \\
        --p1-duty 2 --p2-duty 1 \\
        --out-dir outputv6_bach/<combo>/stems/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import mido
import wave

sys.path.insert(0, str(Path(__file__).parent))
from nsf_to_reaper import SAMPLE_RATE, SPF, LENGTH_TABLE
from render_channel_stems import render_stem, write_wav

CPU_HZ = 1789773.0
NOISE_PERIOD_TABLE = [4, 8, 16, 32, 64, 96, 128, 160,
                      202, 254, 380, 508, 762, 1016, 2034, 4068]

# GM drum note -> (noise_period_idx, noise_mode, length_idx)
# Tuned to resemble NES drum conventions.  Kick/snare use long LFSR
# (hiss-like) at mid periods, hats use short LFSR (tonal) at fast periods.
# length_idx picks LENGTH_TABLE entry -> decay frames (2 half-ticks / 60 Hz frame).
GM_DRUM_MAP = {
    35: (8, 0, 0x00),   # acoustic bass drum
    36: (8, 0, 0x00),   # bass drum 1  -> slow long LFSR = thump
    37: (2, 0, 0x00),   # side stick
    38: (4, 0, 0x00),   # snare        -> mid long LFSR
    39: (4, 0, 0x00),   # hand clap
    40: (4, 0, 0x00),   # electric snare
    41: (6, 0, 0x00),   # low floor tom
    42: (1, 1, 0x00),   # closed hi-hat  -> fast short LFSR = tick
    43: (5, 0, 0x00),   # high floor tom
    44: (1, 1, 0x00),   # pedal hi-hat
    45: (5, 0, 0x00),   # low tom
    46: (1, 1, 0x08),   # open hi-hat    -> longer decay
    47: (4, 0, 0x00),   # low-mid tom
    48: (3, 0, 0x00),   # hi-mid tom
    49: (0, 1, 0x10),   # crash cymbal  -> very fast short LFSR, long decay
    50: (3, 0, 0x00),   # high tom
    51: (0, 1, 0x08),   # ride cymbal
    52: (0, 1, 0x10),   # chinese cymbal
    53: (0, 1, 0x08),   # ride bell
    54: (1, 1, 0x00),   # tambourine
    55: (0, 1, 0x10),   # splash cymbal
    56: (2, 0, 0x00),   # cowbell
    57: (0, 1, 0x10),   # crash cymbal 2
    59: (0, 1, 0x08),   # ride cymbal 2
}
DRUM_FALLBACK = (4, 0, 0x00)


def midi_note_to_freq(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def pulse_period(note: int) -> int:
    freq = midi_note_to_freq(note)
    if freq <= 0:
        return 0
    p = int(round(CPU_HZ / (16.0 * freq) - 1))
    return max(8, min(0x7FF, p))


def triangle_period(note: int) -> int:
    freq = midi_note_to_freq(note)
    if freq <= 0:
        return 0
    p = int(round(CPU_HZ / (32.0 * freq) - 1))
    return max(2, min(0x7FF, p))


def analyze_midi(mid: mido.MidiFile) -> tuple[list[tuple[float, mido.Message]], dict]:
    """Flatten MIDI into (abs_time_seconds, msg) list and per-channel stats."""
    events: list[tuple[float, mido.Message]] = []
    stats: dict[int, dict] = {}
    for track in mid.tracks:
        abs_ticks = 0
        for msg in track:
            abs_ticks += msg.time
            abs_t = mido.tick2second(abs_ticks, mid.ticks_per_beat,
                                     _tempo_at(mid, abs_ticks))
            if msg.type in ("note_on", "note_off"):
                events.append((abs_t, msg))
                if msg.type == "note_on" and msg.velocity > 0:
                    ch = msg.channel
                    s = stats.setdefault(ch, {"notes": [], "count": 0,
                                              "is_drum": ch == 9})
                    s["notes"].append(msg.note)
                    s["count"] += 1
    events.sort(key=lambda x: x[0])
    for ch, s in stats.items():
        s["avg_note"] = sum(s["notes"]) / len(s["notes"]) if s["notes"] else 0
    return events, stats


def _tempo_at(mid: mido.MidiFile, abs_ticks: int) -> int:
    """Return microseconds-per-quarter tempo active at given absolute tick.

    Simplified: NES runs at 60 Hz regardless of MIDI tempo; we only care
    about wall-clock seconds for event timing.  Use the first tempo we see.
    """
    for t in mid.tracks:
        elapsed = 0
        for m in t:
            elapsed += m.time
            if m.type == "set_tempo":
                return m.tempo
    return 500000  # 120 BPM


def map_channels_to_roles(stats: dict) -> dict[int, str]:
    """Auto-map MIDI channels to NES roles (pulse1, pulse2, triangle, noise)."""
    drums = sorted(ch for ch, s in stats.items() if s["is_drum"])
    melodic = sorted(
        [ch for ch, s in stats.items() if not s["is_drum"]],
        key=lambda c: stats[c]["avg_note"],
    )
    role_map: dict[int, str] = {}
    if len(melodic) == 1:
        # Single voice -> pulse1 so it sounds right on a pulse
        role_map[melodic[0]] = "pulse1"
    elif len(melodic) == 2:
        # 2 voices -> lower = pulse2 (fills harmony role), upper = pulse1
        role_map[melodic[0]] = "pulse2"
        role_map[melodic[1]] = "pulse1"
    elif len(melodic) >= 3:
        # Lowest = triangle (bass), two busiest remaining = pulses
        role_map[melodic[0]] = "triangle"
        rest = sorted(melodic[1:], key=lambda c: stats[c]["count"], reverse=True)
        role_map[rest[0]] = "pulse1"
        if len(rest) >= 2:
            role_map[rest[1]] = "pulse2"
        # Extra voices (>= 4th) get folded into pulse2 by doubling or dropped.
        # Simplest: drop to avoid cross-voice clashes; Bach fugues in 4 voices
        # already have pulse1 and pulse2 covering soprano+alto, triangle bass,
        # and the tenor line is audible via harmonic reinforcement anyway.
    for ch in drums:
        role_map[ch] = "noise"
    return role_map


def build_frame_state(mid: mido.MidiFile, p1_duty: int, p2_duty: int,
                      max_seconds: float | None = None,
                      vol_max: int = 10) -> tuple[dict, int]:
    """Synthesize the per-frame channels dict expected by render_stem.

    Returns (channels_dict, num_frames).
    """
    events, stats = analyze_midi(mid)
    role_map = map_channels_to_roles(stats)

    total_seconds = mid.length + 1.0
    if max_seconds is not None:
        total_seconds = min(total_seconds, max_seconds)
    num_frames = max(1, int(round(total_seconds * 60)))

    # Active note stacks per role (to handle overlapping notes on same channel)
    active: dict[str, list[tuple[int, int]]] = {
        "pulse1": [], "pulse2": [], "triangle": [],
    }
    # Noise events: list of (frame, velocity, period_idx, mode, length_idx)
    noise_hits: list[tuple[int, int, int, int, int]] = []

    # Per-role frame-granular state: what note/velocity is active each frame
    # and whether a retrigger happened on this frame.
    role_state: dict[str, list[dict]] = {
        "pulse1": [{"note": None, "vel": 0, "trig": False} for _ in range(num_frames)],
        "pulse2": [{"note": None, "vel": 0, "trig": False} for _ in range(num_frames)],
        "triangle": [{"note": None, "vel": 0, "trig": False} for _ in range(num_frames)],
    }

    # Walk events chronologically, maintain per-role active stack
    def _frame(t: float) -> int:
        return max(0, min(num_frames - 1, int(round(t * 60))))

    # Sort events by (time, priority) - process note_offs before note_ons at same time
    events_sorted = sorted(events, key=lambda e: (e[0], 0 if e[1].type == "note_off"
                                                   or (e[1].type == "note_on" and e[1].velocity == 0)
                                                   else 1))

    prev_frame = 0
    role_active: dict[str, list[tuple[int, int]]] = {r: [] for r in ("pulse1", "pulse2", "triangle")}

    def flush_up_to(target_frame: int):
        """Fill frames [prev_frame, target_frame) with current active state."""
        nonlocal prev_frame
        for r in ("pulse1", "pulse2", "triangle"):
            stack = role_active[r]
            for f in range(prev_frame, target_frame):
                if stack:
                    note, vel = stack[-1]
                    role_state[r][f]["note"] = note
                    role_state[r][f]["vel"] = vel
        prev_frame = target_frame

    for abs_t, msg in events_sorted:
        f = _frame(abs_t)
        if f >= num_frames:
            break
        if f > prev_frame:
            flush_up_to(f)
        role = role_map.get(msg.channel)
        if role is None:
            continue

        if msg.type == "note_on" and msg.velocity > 0:
            if role == "noise":
                idx, mode, length_idx = GM_DRUM_MAP.get(msg.note, DRUM_FALLBACK)
                noise_hits.append((f, msg.velocity, idx, mode, length_idx))
            else:
                role_active[role].append((msg.note, msg.velocity))
                role_state[role][f]["note"] = msg.note
                role_state[role][f]["vel"] = msg.velocity
                role_state[role][f]["trig"] = True
        else:  # note_off or note_on velocity=0
            if role == "noise":
                continue
            stack = role_active[role]
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == msg.note:
                    stack.pop(i)
                    break
            if stack:
                note, vel = stack[-1]
                role_state[role][f]["note"] = note
                role_state[role][f]["vel"] = vel
            # else: empty stack -> note becomes None (silent) starting this frame
        # Advance prev_frame past this event's frame so the next flush starts
        # at f+1 -- otherwise flush_up_to would overwrite the event's state
        # (including `trig` flags) with plain sustain from role_active.
        prev_frame = f + 1

    flush_up_to(num_frames)

    # Build channels dict matching frames_to_channel_data schema
    channels: dict = {
        "pulse1": {"notes": []},
        "pulse2": {"notes": []},
        "triangle": {"notes": []},
        "noise": {"notes": []},
        "dmc": {"notes": []},
    }

    duty_map = {"pulse1": p1_duty, "pulse2": p2_duty}

    # Per-frame pulse state
    for role in ("pulse1", "pulse2"):
        duty = duty_map[role]
        states = role_state[role]
        for f, st in enumerate(states):
            if st["note"] is not None:
                # Cap pulse vol below 15.  Two pulses sustained at 15 each
                # push the non-linear DAC into its loud-compression region
                # where inter-channel modulation becomes audible as buzzy
                # "distortion."  Real NES drivers rarely sustain at max --
                # Family 1 games (Castlevania etc.) hover around vol 6-10.
                vol = max(1, int(round(st["vel"] * vol_max / 127)))
                period = pulse_period(st["note"])
            else:
                vol = 0
                period = 0
            channels[role]["notes"].append({
                "frame": f,
                "period": period,
                "vol": vol,
                "duty": duty,
                "const_vol": 1,         # vol from env_period directly
                "env_loop": 0,
                "env_period": vol,      # when const_vol=1, this IS the volume
                "enabled": 1,
                "phase_reset": bool(st["trig"]),
                "sweep_en": 0, "sweep_period": 0, "sweep_negate": 0, "sweep_shift": 0,
            })

        # Soft attack + release ramps to kill note-boundary click transients.
        # Instantaneous vol 0->N and N->0 steps at 60 Hz frame boundaries are
        # the dominant source of "weird noise" in Bach renders -- the 14 kHz
        # analog LP smooths harmonics but cannot remove a one-sample amplitude
        # step.  Inserting a single half-vol frame at each attack and release
        # adds ~16 ms of ramp that the LP can smooth, eliminating the click.
        # Zero-to-half and half-to-zero are each 3 dB smaller steps, and the
        # LP's 24 dB/octave rolloff above 14 kHz knocks them below audibility.
        notes = channels[role]["notes"]
        for i, n in enumerate(notes):
            prev_vol = notes[i - 1]["vol"] if i > 0 else 0
            # Attack softening
            if n["vol"] > 0 and prev_vol == 0:
                soft = max(1, n["vol"] // 2)
                n["vol"] = soft
                n["env_period"] = soft
            # Release softening (halve the last-active frame before a zero)
            if n["vol"] == 0 and prev_vol > 0 and i > 0:
                soft = max(1, prev_vol // 2)
                notes[i - 1]["vol"] = soft
                notes[i - 1]["env_period"] = soft

    # Triangle
    tri_states = role_state["triangle"]
    for f, st in enumerate(tri_states):
        if st["note"] is not None:
            period = triangle_period(st["note"])
            # Held sustain: phase_reset only on attack, but we keep
            # control=1, reload=127 so the flag (set at attack) keeps
            # the counter topped up.  If trig=False, we still emit the
            # sustain state -- the reload flag in render_stem persists
            # across frames until control goes to 0.
            channels["triangle"]["notes"].append({
                "frame": f,
                "period": period,
                "linear": 127,
                "linear_reload": 127,
                "linear_control": 1,
                "enabled": 1,
                "phase_reset": bool(st["trig"]),
            })
        else:
            # Silenced: set reload=0 and phase_reset so counter zeroes
            # on the exact off-frame.  Subsequent silent frames: control=0
            # keeps flag cleared, counter stays at 0.
            prev = channels["triangle"]["notes"][-1] if channels["triangle"]["notes"] else None
            just_went_silent = prev is not None and prev.get("linear_reload", 0) > 0
            channels["triangle"]["notes"].append({
                "frame": f,
                "period": prev["period"] if prev else 0,
                "linear": 0,
                "linear_reload": 0,
                "linear_control": 0,
                "enabled": 1,
                "phase_reset": just_went_silent,
            })

    # Noise: build from noise_hits list with length-counter decay per frame
    hits_by_frame: dict[int, tuple[int, int, int, int]] = {}
    for f, vel, idx, mode, length_idx in noise_hits:
        hits_by_frame[f] = (vel, idx, mode, length_idx)

    vol = 0
    period_idx = 0
    mode = 0
    length = 0
    for f in range(num_frames):
        if f in hits_by_frame:
            v, idx, m, length_idx = hits_by_frame[f]
            vol = max(1, int(round(v * 15 / 127)))
            period_idx = idx
            mode = m
            length = LENGTH_TABLE[length_idx & 0x1F]
        channels["noise"]["notes"].append({
            "frame": f,
            "vol": vol,
            "period": period_idx,
            "mode": mode,
            "enabled": 1,
            "length_counter": length,
        })
        # Decrement length counter (2 half-frame ticks per 60 Hz frame)
        if length > 0:
            length = max(0, length - 2)
        if length == 0:
            vol = 0  # silence once length expires

    # DMC: empty (Bach has no DPCM)
    for f in range(num_frames):
        channels["dmc"]["notes"].append({
            "frame": f, "dac": 0, "rate_idx": 0, "loop": 0,
            "sample_addr": 0xC000, "sample_len": 1,
            "event_type": "idle",
        })

    return channels, num_frames


def render_bach_stems(midi_path: Path, out_dir: Path, p1_duty: int,
                      p2_duty: int, max_seconds: float | None = None,
                      vol_max: int = 10) -> float:
    """Render a MIDI to the 4 NES stems in out_dir.  Returns duration in seconds."""
    mid = mido.MidiFile(str(midi_path))
    channels, num_frames = build_frame_state(mid, p1_duty, p2_duty,
                                              max_seconds, vol_max=vol_max)
    out_dir.mkdir(parents=True, exist_ok=True)

    stems = [("p1", "pulse1.wav"), ("p2", "pulse2.wav"),
             ("tri", "triangle.wav"), ("noise", "noise.wav")]

    raw = {}
    for key, _ in stems:
        raw[key] = render_stem(channels, num_frames, key, normalize=False)

    # Shared-scale normalization (Rule 31 / outputv6)
    combined = sum(raw.values())
    peak = float(np.max(np.abs(combined))) if len(combined) else 0.0
    scale = (0.9 / peak) if peak > 0 else 1.0

    for key, filename in stems:
        samples = (raw[key] * scale * 32767).astype(np.int16)
        out_path = out_dir / filename
        write_wav(samples, out_path)

    return num_frames / 60.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--midi", type=Path, required=True)
    ap.add_argument("--p1-duty", type=int, default=2, choices=[0, 1, 2, 3])
    ap.add_argument("--p2-duty", type=int, default=1, choices=[0, 1, 2, 3])
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--seconds", type=float, default=None,
                    help="Cap render length (default: full MIDI duration)")
    ap.add_argument("--vol-max", type=int, default=10,
                    help="Max pulse volume 1-15 (default 10; 15 = buzzy, 8 = mellow)")
    args = ap.parse_args()

    print(f"Rendering {args.midi.name} -> {args.out_dir}")
    print(f"  p1_duty={args.p1_duty}  p2_duty={args.p2_duty}  vol_max={args.vol_max}")
    duration = render_bach_stems(args.midi, args.out_dir,
                                  args.p1_duty, args.p2_duty, args.seconds,
                                  vol_max=args.vol_max)
    print(f"  duration: {duration:.1f}s  ({args.out_dir})")


if __name__ == "__main__":
    main()
