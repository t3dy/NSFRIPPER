#!/usr/bin/env python3
"""Produce A/B/C variant REAPER projects for every game in outputv6.

Three variants per song (see docs/SYNTH_VS_SCRIPTS.md):

  A: stems + MIDI + JSFX  — both audio stems (archival) and MIDI
     tracks routed through the JSFX synth (live-playable).  This is
     the default output of generate_stems_rpp.py but with JSFX tracks
     default-UNmuted (so the user hears the synth, not just stems).

  B: MIDI + JSFX only      — no audio stems at all.  The only sound
     comes from the JSFX plugin on each MIDI track.  Fully playable
     live; MIDI keyboard input works per JSFX priority-3 mode.

  C: JSFX-rendered stems   — placeholder output requiring REAPER
     offline render automation (not implemented yet; this script
     writes a stub RPP identical to B that can be rendered later).

Output layout:
    outputv6_A/<game>/reaper/<song>.rpp  (references ../../outputv6/<game>/stems)
    outputv6_B/<game>/reaper/<song>.rpp
    outputv6_C/<game>/reaper/<song>.rpp  (same as B until offline render lands)

Usage:
    python scripts/generate_rpp_variants.py               # all games
    python scripts/generate_rpp_variants.py --only Metroid
    python scripts/generate_rpp_variants.py --variants A,B # skip C for now
"""
import argparse
import re
import shutil
import sys
import uuid
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
V6 = REPO / "outputv6"
V6_A = REPO / "outputv6_A"
V6_B = REPO / "outputv6_B"
V6_C = REPO / "outputv6_C"

sys.path.insert(0, str(Path(__file__).parent))
from generate_project import (  # noqa: E402
    rpp_header, rpp_track, apu2_slider_values, JSFX_PLUGIN_APU2,
    CHANNEL_LABELS, COLORS, analyze_midi, midi_track_to_events,
)
from generate_stems_rpp import audio_track, get_wav_length  # noqa: E402
import mido  # noqa: E402


def make_guid():
    return "{" + str(uuid.uuid4()).upper() + "}"


def variant_a_rpp(midi_path, stems_dir, out_path):
    """A: stems + MIDI+JSFX.  JSFX tracks default-UNmuted so user
    hears the live synth; stems are there as a reference/archival.
    """
    info = analyze_midi(midi_path)
    stats = info["channel_stats"]
    tempo = info["tempo_bpm"]

    stem_files = {}
    for role in ("pulse1", "pulse2", "triangle", "noise", "dmc"):
        p = stems_dir / f"{role}.wav"
        if p.is_file():
            stem_files[role] = p
    if "pulse1" not in stem_files:
        return False
    length = get_wav_length(stem_files["pulse1"])

    lines = [rpp_header(tempo=tempo, title=f"{midi_path.stem} - Variant A")]
    roles = [r for r in ("pulse1", "pulse2", "triangle", "noise", "dmc")
             if r in stem_files]
    nes_ch = {"pulse1": 0, "pulse2": 1, "triangle": 2, "noise": 3, "dmc": 4}

    mid = mido.MidiFile(str(midi_path))
    for role in roles:
        ch_idx = nes_ch[role]
        audio_name = f"[AUDIO] NES - {CHANNEL_LABELS[role]}"
        lines.append(audio_track(audio_name, stem_files[role], length))

        if ch_idx in stats and stats[ch_idx]["note_count"] > 0:
            target_ch = ch_idx
            ch_track = None
            sysex_trk = None
            for t in mid.tracks:
                if any(hasattr(m, "channel") and m.channel == target_ch for m in t):
                    ch_track = t
                if any(m.type == "sysex" for m in t) and not any(
                    hasattr(m, "type") and m.type == "note_on" and hasattr(m, "channel") for m in t
                ):
                    sysex_trk = t
            events = midi_track_to_events(ch_track, sysex_track=sysex_trk) if ch_track else None

            vals = apu2_slider_values(game="", channel=role)
            midi_name = f"[JSFX] NES - {CHANNEL_LABELS[role]}"
            midi_block = rpp_track(
                name=midi_name, color=COLORS[role], slider_values=vals,
                midi_length=length,
                armed=False, selected=False,
                jsfx_plugin=JSFX_PLUGIN_APU2,
                midi_events=events, ticks_per_beat=info["ticks_per_beat"],
            )
            # Variant A: JSFX default UNMUTED (user hears live synth)
            # Mute the audio stem track above (pair: last audio_track)
            # -- actually we want BOTH audible for A/B comparison so leave
            # both unmuted.  User can mute either in REAPER.
            lines.append(midi_block)

    lines.append(">")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return True


def variant_b_rpp(midi_path, stems_dir, out_path):
    """B: MIDI + JSFX only.  No audio stems.  The JSFX plugin is the
    only sound source.  Live-playable, MIDI keyboard works via JSFX
    priority-3 mode.
    """
    info = analyze_midi(midi_path)
    stats = info["channel_stats"]
    tempo = info["tempo_bpm"]

    # Estimate length from pulse1 stem if available, else 60 s fallback
    length = 60.0
    p1 = stems_dir / "pulse1.wav"
    if p1.is_file():
        length = get_wav_length(p1)

    lines = [rpp_header(tempo=tempo, title=f"{midi_path.stem} - Variant B")]
    nes_ch = {"pulse1": 0, "pulse2": 1, "triangle": 2, "noise": 3, "dmc": 4}

    mid = mido.MidiFile(str(midi_path))
    for role, ch_idx in nes_ch.items():
        if ch_idx not in stats or stats[ch_idx].get("note_count", 0) == 0:
            continue
        target_ch = ch_idx
        ch_track = None
        sysex_trk = None
        for t in mid.tracks:
            if any(hasattr(m, "channel") and m.channel == target_ch for m in t):
                ch_track = t
            if any(m.type == "sysex" for m in t) and not any(
                hasattr(m, "type") and m.type == "note_on" and hasattr(m, "channel") for m in t
            ):
                sysex_trk = t
        events = midi_track_to_events(ch_track, sysex_track=sysex_trk) if ch_track else None

        vals = apu2_slider_values(game="", channel=role)
        midi_name = f"[JSFX] NES - {CHANNEL_LABELS[role]}"
        midi_block = rpp_track(
            name=midi_name, color=COLORS[role], slider_values=vals,
            midi_length=length,
            armed=False, selected=False,
            jsfx_plugin=JSFX_PLUGIN_APU2,
            midi_events=events, ticks_per_beat=info["ticks_per_beat"],
        )
        lines.append(midi_block)

    lines.append(">")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return True


def variant_c_rpp(midi_path, stems_dir, out_path):
    """C: JSFX-rendered stems (placeholder).

    The eventual workflow:
      1. Start with Variant B (JSFX-only RPP).
      2. Use REAPER's offline render (via ReaScript / CLI) to bounce
         each JSFX track to a WAV.
      3. Build a new RPP referencing those JSFX-rendered WAVs as
         audio tracks.

    For now, C just writes the B template unchanged.  When ReaScript
    automation lands, this function is where it plugs in.
    """
    return variant_b_rpp(midi_path, stems_dir, out_path)


def process_game(game_dir, variants):
    """For each song in a outputv6/<game>/, produce variant RPPs."""
    midi_dir = game_dir / "midi"
    stems_root = game_dir / "stems"
    if not midi_dir.is_dir() or not stems_root.is_dir():
        return (0, 0)

    produced = 0
    failed = 0
    for midi_path in sorted(midi_dir.glob("*.mid")):
        slug = midi_path.stem
        stems_dir = stems_root / slug
        if not stems_dir.is_dir():
            continue

        for variant in variants:
            if variant == "A":
                target_root = V6_A
                builder = variant_a_rpp
            elif variant == "B":
                target_root = V6_B
                builder = variant_b_rpp
            elif variant == "C":
                target_root = V6_C
                builder = variant_c_rpp
            else:
                continue
            out_path = target_root / game_dir.name / "reaper" / f"{slug}.rpp"
            try:
                ok = builder(midi_path, stems_dir, out_path)
                if ok:
                    produced += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"  ERROR {variant} {slug}: {e}")
                failed += 1
    return produced, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--variants", default="A,B,C",
                    help="Comma-sep list of variants (A, B, C)")
    args = ap.parse_args()
    variants = [v.strip().upper() for v in args.variants.split(",") if v.strip()]

    games = sorted(p for p in V6.iterdir()
                   if p.is_dir() and not p.name.startswith("_"))
    if args.only:
        games = [g for g in games if g.name in args.only]

    total_produced = 0
    total_failed = 0
    for game_dir in games:
        p, f = process_game(game_dir, variants)
        total_produced += p
        total_failed += f
        if p or f:
            print(f"  {game_dir.name:40}  produced={p:3}  failed={f}")

    print(f"\nTotal RPPs produced: {total_produced}  failed: {total_failed}")
    for v in variants:
        root = {"A": V6_A, "B": V6_B, "C": V6_C}[v]
        n = len(list(root.rglob("*.rpp"))) if root.is_dir() else 0
        print(f"  outputv6_{v}/: {n} RPPs")


if __name__ == "__main__":
    main()
