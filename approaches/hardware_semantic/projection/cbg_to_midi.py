"""Liveness-driven MIDI projection.

The new rule compared to scripts/nsf_to_reaper.py::build_midi:

  OLD: note = period_fn(period) if period > N and vol > 0 else 0
       note_on when note changes AND vol > 0
       note_off when note goes to 0 OR period changes

  NEW: emit notes only during AUDIBLE runs of liveness.frames.
       note_on at liveness AUDIBLE-transition, using current period.
       note_off at liveness SILENT/GATED/DEGENERATE transition.
       Within an AUDIBLE run, re-trigger on:
         - period changes to a new pitch, OR
         - liveness.retrigger[i] is True (phase_reset / linear_reload)

This is what dissolves the W&W note_boundary_map workaround AND the
Contra triangle drone: triangle liveness goes SILENT between driver
retriggers because linear_live decays.  No game-specific boundary
patch needed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import mido

_SCRIPTS = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from nsf_to_reaper import period_to_midi, TICKS_PER_BEAT, TICKS_PER_FRAME  # noqa: E402

from ..cbg.schema import Audibility, ChannelLiveness


# Track layout matches the stems pipeline -- so generate_stems_rpp
# can consume our MIDI unchanged.
_TRACKS = [
    ("pulse1",   "Square 1 [lead]",       0, 80),
    ("pulse2",   "Square 2 [harmony]",    1, 81),
    ("triangle", "Triangle [bass]",       2, 38),
    ("noise",    "Noise [drums]",         3, 0),
]


def build_midi_from_cbg(
    channels: dict,
    liveness: dict[str, ChannelLiveness],
    game_title: str,
    song_name: str,
    song_num: int,
    out_path: str | Path,
    tempo_bpm: float = 128.6,
) -> mido.MidiFile:
    """Write a MIDI file using CBG liveness for note boundaries.

    The channels dict is the one produced by frames_to_channel_data
    and augmented by hw_sim.simulate_hw_state.  The liveness dict is
    what resolve_liveness returns.
    """
    mid = mido.MidiFile(ticks_per_beat=TICKS_PER_BEAT)

    # Track 0: metadata
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo_bpm)))
    meta.append(mido.MetaMessage('time_signature', numerator=4, denominator=4))
    meta.append(mido.MetaMessage('text',
        text=f'Game: {game_title}'.encode('latin-1', 'replace').decode('latin-1')))
    meta.append(mido.MetaMessage('text',
        text=f'Song: {song_name}'.encode('latin-1', 'replace').decode('latin-1')))
    meta.append(mido.MetaMessage('text', text='Source: CBG liveness projection (hardware_semantic)'))
    meta.append(mido.MetaMessage('text', text=f'Track: {song_num}'))
    mid.tracks.append(meta)

    for ch_name, label, midi_ch, program in _TRACKS:
        if ch_name not in channels or ch_name not in liveness:
            continue
        track = _build_channel_track(
            ch_name, label, midi_ch, program,
            channels[ch_name]["notes"],
            liveness[ch_name],
        )
        mid.tracks.append(track)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(out_path)
    return mid


def _build_channel_track(ch_name, label, midi_ch, program,
                         frames, cl: ChannelLiveness) -> mido.MidiTrack:
    track = mido.MidiTrack()
    track.append(mido.MetaMessage('track_name', name=label))
    if program > 0:
        track.append(mido.Message('program_change', channel=midi_ch, program=program))

    is_tri = (ch_name == "triangle")
    prev_note = 0
    prev_vol = -1
    prev_duty = -1
    ticks = 0

    for i, fd in enumerate(frames):
        audible = cl.is_audible(i)
        retrig = bool(cl.retrigger[i])

        if ch_name in ("pulse1", "pulse2"):
            period = fd.get("sweep_period", fd["period"])
            vol = fd.get("effective_vol", fd["vol"])
            duty = fd["duty"]
            this_note = period_to_midi(period) if audible else 0

            # CC12 duty
            if audible and duty != prev_duty:
                track.append(mido.Message('control_change', channel=midi_ch,
                                          control=12, value=[16, 32, 64, 96][duty],
                                          time=ticks))
                ticks = 0
                prev_duty = duty

            # CC11 vol
            if audible and vol != prev_vol:
                track.append(mido.Message('control_change', channel=midi_ch,
                                          control=11, value=min(127, vol * 8),
                                          time=ticks))
                ticks = 0
                prev_vol = vol

            # Note on/off logic
            ticks = _emit_note_events(
                track, midi_ch, this_note, prev_note, retrig and audible,
                audible, vol, ticks,
            )
            prev_note = this_note

        elif ch_name == "triangle":
            period = fd["period"]
            this_note = period_to_midi(period, is_tri=True) if audible else 0

            # Triangle CC11 is gate-only (127 when audible, absent otherwise)
            if audible and prev_note == 0 and this_note > 0:
                track.append(mido.Message('control_change', channel=midi_ch,
                                          control=11, value=127, time=ticks))
                ticks = 0

            ticks = _emit_note_events(
                track, midi_ch, this_note, prev_note, retrig and audible,
                audible, 127, ticks,
            )
            prev_note = this_note

        elif ch_name == "noise":
            vol = fd["vol"]
            period = fd["period"] & 0x0F
            if audible and prev_note == 0:
                # New drum hit -- map period to GM drum note
                if period <= 4:
                    drum = 42   # closed hi-hat
                elif period <= 8:
                    drum = 38   # snare
                else:
                    drum = 36   # kick
                track.append(mido.Message('note_on', note=drum,
                                          velocity=min(127, vol * 8),
                                          channel=midi_ch, time=ticks))
                ticks = 0
                prev_note = drum
            elif not audible and prev_note > 0:
                track.append(mido.Message('note_off', note=prev_note,
                                          velocity=0, channel=midi_ch,
                                          time=ticks))
                ticks = 0
                prev_note = 0

        ticks += TICKS_PER_FRAME

    # Close dangling note
    if prev_note > 0:
        track.append(mido.Message('note_off', note=prev_note, velocity=0,
                                  channel=midi_ch, time=ticks))

    return track


def _emit_note_events(track, midi_ch, this_note, prev_note, retrig,
                     audible, vol, ticks):
    """Emit note_on/off based on liveness-driven transitions.

    Returns updated ticks counter.
    """
    need_retrigger = retrig and this_note > 0 and this_note == prev_note

    if need_retrigger and prev_note > 0:
        # Same-pitch retrigger: close prev and open again
        track.append(mido.Message('note_off', note=prev_note, velocity=0,
                                  channel=midi_ch, time=ticks))
        ticks = 0
        track.append(mido.Message('note_on', note=this_note,
                                  velocity=min(127, max(1, vol * 8)),
                                  channel=midi_ch, time=ticks))
        ticks = 0
    elif this_note != prev_note:
        if prev_note > 0:
            track.append(mido.Message('note_off', note=prev_note, velocity=0,
                                      channel=midi_ch, time=ticks))
            ticks = 0
        if this_note > 0:
            track.append(mido.Message('note_on', note=this_note,
                                      velocity=min(127, max(1, vol * 8)),
                                      channel=midi_ch, time=ticks))
            ticks = 0
    return ticks
