"""Inject W&W Title-style per-frame CC11 envelope onto bare Bach MIDIs.

The goal is to force the JSFX plugin into priority-2 (CC-driven) mode
so each note gets the sharp-attack-then-continuous-linear-decay shape
that makes W&W pulses sound *plinky*.  Priority-3 ADSR mode flattens
after the decay phase, which is why Bach MIDIs through our ADSR sound
organ-like instead of plinky.

Canonical W&W Title pulse 1 envelope (extracted from the CBG MIDI):

    Frame   0:  note_on vel=120      (NES vol 15)
    Frame   1:  CC11=112             (NES vol 14)
    Frame   3:  CC11=104             (NES vol 13)
    Frame   4:  CC11= 96             (NES vol 12)
    Frame   6:  CC11= 88             (NES vol 11)
    Frame   7:  CC11= 80             (NES vol 10)
    Frame   9:  CC11= 72             (NES vol  9)
    Frame  10:  CC11= 64             (NES vol  8)
    Frame  12:  CC11= 56             (NES vol  7)
    ...

Which is a linear software decay: CC11 drops ~8 units every ~1.5 frames
(driver updates volume on most passes but skips some).  The floor is
around 8 (the minimum observed in the W&W Title CC11 stream).

For Bach MIDIs we approximate this as **CC11 = max(8, 120 - 4*frame)**
emitted every frame (16 ticks).  This hits the same slope (8 per 2
frames) and floors at 8.  Released notes stop receiving CC11 events;
the plugin handles note_off via its release stage as normal.

Only pulse channels (MIDI ch 0 + 1) get the envelope.  Triangle (ch 2)
stays at its implicit gate volume.  Noise (ch 3) is untouched.
"""
from __future__ import annotations

from pathlib import Path

import mido

CC_DECAY_START = 120     # peak CC11 on note_on (matches W&W attack)
CC_DECAY_PER_FRAME = 4   # linear drop per 60 Hz frame (= 8 units per 2 frames)
CC_DECAY_FLOOR = 8       # lowest CC11 (matches W&W min)

# 1 NES frame at 60 Hz.  We compute ticks-per-frame from the MIDI's
# ppq + first tempo so the decay RATE stays constant in real time
# regardless of the MIDI's tick resolution.  Fallback = 16 ticks
# (matches our 128.6 BPM / 480 ppq game MIDIs).
DEFAULT_TICKS_PER_FRAME = 16

PULSE_CHANNELS = (0, 1)

# Triangle note-duration truncation.
#
# W&W Title triangle rings for ~100-200 ms per note then decays to
# silence via the linear counter.  The driver retriggers every
# ~400 ms for sustained musical notes, creating the plinky staccato
# bass character.
#
# Bach bass notes are often held quarters / halves / whole notes
# (500 ms+), so with no truncation the plugin plays them full-length
# and the result sounds droning, not plinky.  Truncating every triangle
# note to a max audible duration simulates the linear counter decay
# even though the plugin's priority-2 path doesn't actually gate on
# CC11.
#
# Default 180 ms is a bit longer than the W&W Title linear counter
# life (reload=15 -> ~62 ms pure, but combined with phase-reset
# afterglow and mild envelope release it's closer to 150-200 ms
# audible per note).
TRIANGLE_MAX_DURATION_MS = 180
TRIANGLE_CHANNEL = 2


def _ticks_per_frame(mid: "mido.MidiFile") -> int:
    """ticks = ppq * bpm / 3600 (1 frame = 1/60 s)."""
    ppq = mid.ticks_per_beat
    # Find first tempo event; default 120 BPM if missing
    bpm = 120.0
    for tr in mid.tracks:
        for msg in tr:
            if msg.type == "set_tempo":
                bpm = 60_000_000.0 / msg.tempo
                break
        else:
            continue
        break
    tpf = round(ppq * bpm / 3600.0)
    return max(1, tpf)


def inject_ww_envelope(
    src_midi: Path, dst_midi: Path,
    *, ticks_per_frame: int | None = None,
    start: int = CC_DECAY_START, step: int = CC_DECAY_PER_FRAME,
    floor: int = CC_DECAY_FLOOR,
    triangle_max_ms: int = TRIANGLE_MAX_DURATION_MS,
) -> dict:
    """Copy src MIDI to dst MIDI with CC11 injected on pulse channels
    and triangle notes truncated to `triangle_max_ms` milliseconds.

    If `ticks_per_frame` is None, it is auto-computed from the MIDI's
    ppq and first tempo so the injected decay rate stays at 4 CC11
    units per 60 Hz frame (the W&W Title slope) regardless of the
    MIDI's tick resolution.

    Set `triangle_max_ms=0` to disable triangle truncation (bass notes
    play their full MIDI duration).

    Returns stats dict with:
      notes_automated       -- pulse notes that got a CC11 envelope
      cc_events_inserted    -- total CC11 events injected
      triangle_truncated    -- triangle notes that got shortened
      triangle_max_ticks    -- resolved ticks-per-note cap on triangle
      ticks_per_frame       -- effective 1-frame tick count used
    """
    mid = mido.MidiFile(str(src_midi))
    out = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)

    if ticks_per_frame is None:
        ticks_per_frame = _ticks_per_frame(mid)

    # Compute triangle-truncation cap in ticks using the same tempo
    # derivation.  triangle_max_ticks = ticks_per_frame * (ms / 16.667).
    triangle_max_ticks = 0
    if triangle_max_ms > 0:
        triangle_max_ticks = max(1, round(ticks_per_frame * triangle_max_ms / (1000.0 / 60.0)))

    stats = {"notes_automated": 0, "cc_events_inserted": 0,
             "triangle_truncated": 0, "triangle_max_ticks": triangle_max_ticks,
             "ticks_per_frame": ticks_per_frame}

    for src_track in mid.tracks:
        touches_pulse = any(
            hasattr(m, "channel") and m.channel in PULSE_CHANNELS
            and m.type in ("note_on", "note_off")
            for m in src_track
        )
        touches_tri = any(
            hasattr(m, "channel") and m.channel == TRIANGLE_CHANNEL
            and m.type in ("note_on", "note_off")
            for m in src_track
        ) and triangle_max_ticks > 0

        if not (touches_pulse or touches_tri):
            out.tracks.append(mido.MidiTrack(list(src_track)))
            continue

        new_track, s = _rebuild_track_with_envelope(
            src_track, ticks_per_frame=ticks_per_frame,
            start=start, step=step, floor=floor,
            triangle_max_ticks=triangle_max_ticks,
        )
        out.tracks.append(new_track)
        stats["notes_automated"] += s["notes_automated"]
        stats["cc_events_inserted"] += s["cc_events_inserted"]
        stats["triangle_truncated"] += s["triangle_truncated"]

    dst_midi.parent.mkdir(parents=True, exist_ok=True)
    out.save(str(dst_midi))
    return stats


def _rebuild_track_with_envelope(src_track: mido.MidiTrack, *,
                                 ticks_per_frame: int,
                                 start: int, step: int, floor: int,
                                 triangle_max_ticks: int):
    """Walk src in absolute time, interleave CC11 on pulses and truncate
    triangle notes that exceed triangle_max_ticks of hold duration."""
    abs_events = []  # list[(abs_tick, msg)]
    t = 0
    for msg in src_track:
        t += msg.time
        abs_events.append((t, msg))

    # Build the new event stream:
    #  - For pulses: inject CC11 events per frame until note_off.
    #  - For triangle: if note exceeds triangle_max_ticks, emit an early
    #    note_off and drop the original note_off.  This simulates the
    #    linear-counter decay since the plugin's CC path doesn't gate
    #    triangle on CC11 value, only on note_on/note_off.
    active_pulse = {}    # (channel, note) -> attack_tick  (pulse only)
    active_tri = {}      # note -> (attack_tick, original_off_index)
    injected: list[tuple[int, mido.Message]] = []
    drop_events: set[int] = set()   # indices into abs_events to suppress

    notes_automated = 0
    cc_inserted = 0
    tri_truncated = 0

    for idx, (abs_t, msg) in enumerate(abs_events):
        # ----- Pulse note_on / off with CC11 injection -----
        if msg.type == "note_on" and msg.velocity > 0 and msg.channel in PULSE_CHANNELS:
            active_pulse[(msg.channel, msg.note)] = abs_t
            notes_automated += 1
        elif (msg.type == "note_off" or
              (msg.type == "note_on" and msg.velocity == 0)) \
                and msg.channel in PULSE_CHANNELS:
            key = (msg.channel, msg.note)
            if key in active_pulse:
                attack_t = active_pulse.pop(key)
                duration_frames = (abs_t - attack_t) // ticks_per_frame
                for frame in range(1, duration_frames + 1):
                    cc_val = max(floor, start - step * frame)
                    cc_tick = attack_t + frame * ticks_per_frame
                    if cc_tick >= abs_t:
                        break
                    injected.append((cc_tick, mido.Message(
                        "control_change", channel=msg.channel,
                        control=11, value=cc_val, time=0,
                    )))
                    cc_inserted += 1

        # ----- Triangle note_on / off with truncation -----
        elif msg.type == "note_on" and msg.velocity > 0 and msg.channel == TRIANGLE_CHANNEL:
            active_tri[msg.note] = (abs_t, idx)
        elif (msg.type == "note_off" or
              (msg.type == "note_on" and msg.velocity == 0)) \
                and msg.channel == TRIANGLE_CHANNEL:
            if msg.note in active_tri and triangle_max_ticks > 0:
                attack_t, _ = active_tri.pop(msg.note)
                dur = abs_t - attack_t
                if dur > triangle_max_ticks:
                    # Drop the original note_off; emit early note_off
                    drop_events.add(idx)
                    early_off_t = attack_t + triangle_max_ticks
                    injected.append((early_off_t, mido.Message(
                        "note_off", channel=TRIANGLE_CHANNEL,
                        note=msg.note, velocity=0, time=0,
                    )))
                    tri_truncated += 1

    # Merge injected events with the original stream, skipping drops.
    merged = []
    for idx, (abs_t, msg) in enumerate(abs_events):
        if idx not in drop_events:
            merged.append((abs_t, msg))
    merged.extend(injected)
    merged.sort(key=lambda kv: (kv[0],
                                0 if kv[1].type == "control_change" else
                                1 if kv[1].type == "note_off" else 2))

    # Convert back to relative-time MidiTrack
    out_track = mido.MidiTrack()
    prev_t = 0
    for abs_t, msg in merged:
        dt = abs_t - prev_t
        m = msg.copy(time=dt) if hasattr(msg, "copy") else msg
        out_track.append(m)
        prev_t = abs_t

    return out_track, {
        "notes_automated": notes_automated,
        "cc_events_inserted": cc_inserted,
        "triangle_truncated": tri_truncated,
    }
