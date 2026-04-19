#!/usr/bin/env python3
"""Bach x NES stage-preset batch -- outputv6 stems edition.

Pairs Bach (and other classical) MIDIs with per-game NES stage presets
(pulse1/pulse2 duty cycles) and renders hardware-accurate stems via
scripts/bach_to_stems.py, then produces a REAPER project with stems as
audio tracks + editable MIDI tracks alongside -- identical layout to
outputv6 game projects.

Usage:
    python scripts/batch_bach_v6.py --list                  # preview combos
    python scripts/batch_bach_v6.py --top 10                # top-scoring 10
    python scripts/batch_bach_v6.py --composer Bach --voices 2
    python scripts/batch_bach_v6.py --game Castlevania
    python scripts/batch_bach_v6.py --all                   # everything

Output: outputv6_bach/<combo_slug>/
  stems/pulse1.wav pulse2.wav triangle.wav noise.wav
  <combo_slug>.mid   (MIDI remapped to NES channels 0-3)
  <combo_slug>.rpp
"""
from __future__ import annotations

import argparse
import re
import sys
import uuid
from pathlib import Path

import mido
from scipy.io import wavfile

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Reuse presets and piece catalog from the legacy script.
from bach_nes_mashup import (  # noqa: E402
    STAGE_PRESETS, BACH_PIECES, get_all_combos, find_midi,
)
from bach_to_stems import (  # noqa: E402
    render_bach_stems, analyze_midi as bach_analyze, map_channels_to_roles,
)
from generate_project import (  # noqa: E402
    rpp_header, rpp_track, apu2_slider_values, JSFX_PLUGIN_APU2,
    CHANNEL_LABELS, COLORS, midi_track_to_events,
)

OUT_ROOT = REPO_ROOT / "outputv6_bach"
NES_CH = {"pulse1": 0, "pulse2": 1, "triangle": 2, "noise": 3}


def make_guid() -> str:
    return "{" + str(uuid.uuid4()).upper() + "}"


def slugify(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    return s.strip("_")


def remap_midi_to_nes(src: Path, dst: Path, role_map: dict[int, str]) -> None:
    """Copy MIDI to dst with channels remapped to NES roles 0-3.

    Channels not present in role_map are dropped entirely (keeps only the
    voices that will actually play through the NES pipeline).
    """
    mid = mido.MidiFile(str(src))
    out = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat, type=mid.type)
    for track in mid.tracks:
        new_track = mido.MidiTrack()
        for msg in track:
            if hasattr(msg, "channel"):
                role = role_map.get(msg.channel)
                if role is None:
                    # Drop events on channels we don't map (non-playing voices)
                    if msg.type in ("note_on", "note_off", "control_change",
                                    "program_change", "pitchwheel", "aftertouch",
                                    "polytouch"):
                        continue
                    new_track.append(msg.copy())
                else:
                    new_track.append(msg.copy(channel=NES_CH[role]))
            else:
                new_track.append(msg.copy())
        out.tracks.append(new_track)
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(str(dst))


def audio_track(name: str, audio_path: Path, length_seconds: float) -> str:
    guid = make_guid()
    item_guid = make_guid()
    return f"""  <TRACK {guid}
    NAME "{name}"
    PEAKCOL 25600
    BEAT -1
    AUTOMODE 0
    PANLAWFLAGS 3
    VOLPAN 1 0 -1 -1 1
    MUTESOLO 0 0 0
    IPHASE 0
    PLAYOFFS 0 1
    ISBUS 0 0
    BUSCOMP 0 0 0 0 0
    SHOWINMIX 1 0.6667 0.5 1 0.5 0 0 0
    FIXEDLANES 9 0 0 0 0
    SEL 0
    REC 0 0 1 0 0 0 0 0
    VU 2
    TRACKHEIGHT 0 0 0 0 0 0 0
    INQ 0 0 0 0.5 100 0 0 100
    NCHAN 2
    FX 0
    TRACKID {guid}
    PERF 0
    MIDIOUT -1
    MAINSEND 1 0
    <ITEM
      POSITION 0
      LENGTH {length_seconds:.6f}
      LOOP 0
      ALLTAKES 0
      FADEIN 0 0 0 0 0 0 0
      FADEOUT 0 0 0 0 0 0 0
      MUTE 0 0
      SEL 0
      IGUID {item_guid}
      IID 1
      NAME "{audio_path.name}"
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {make_guid()}
      <SOURCE WAVE
        FILE "{audio_path.resolve().as_posix()}"
      >
    >
  >
"""


def wav_duration(path: Path) -> float:
    sr, d = wavfile.read(str(path))
    return len(d) / sr


def build_project(midi_path: Path, stems_dir: Path, rpp_path: Path,
                  title: str) -> None:
    """Build a REAPER project: stems as audio tracks + MIDI tracks with JSFX."""
    mid = mido.MidiFile(str(midi_path))
    tempo_us = 500000
    for t in mid.tracks:
        for m in t:
            if m.type == "set_tempo":
                tempo_us = m.tempo
                break
    tempo_bpm = 60_000_000 / tempo_us

    # Gather per-channel note counts (using remapped MIDI -> ch 0..3)
    ch_counts: dict[int, int] = {}
    for t in mid.tracks:
        for m in t:
            if m.type == "note_on" and m.velocity > 0:
                ch_counts[m.channel] = ch_counts.get(m.channel, 0) + 1

    stem_paths = {r: stems_dir / f"{r if r!='triangle' else 'triangle'}.wav"
                  for r in ("pulse1", "pulse2", "triangle", "noise")}
    length = wav_duration(stem_paths["pulse1"])

    lines = [rpp_header(tempo=tempo_bpm, title=title)]
    roles = ["pulse1", "pulse2", "triangle", "noise"]

    for role in roles:
        ch_idx = NES_CH[role]

        # 1. Audio track with the rendered stem
        audio_name = f"[AUDIO] NES - {CHANNEL_LABELS[role]}"
        lines.append(audio_track(audio_name, stem_paths[role], length))

        # 2. MIDI track with the JSFX synth (muted by default, user can unmute
        #    for live keyboard / editing). Only include if this role has notes.
        if ch_counts.get(ch_idx, 0) > 0:
            ch_track = None
            for t in mid.tracks:
                if any(hasattr(m, "channel") and m.channel == ch_idx for m in t):
                    ch_track = t
                    break
            events = midi_track_to_events(ch_track) if ch_track else None

            vals = apu2_slider_values(game="", channel=role)
            midi_name = f"[MIDI] NES - {CHANNEL_LABELS[role]}"
            midi_block = rpp_track(
                name=midi_name, color=COLORS[role], slider_values=vals,
                midi_length=length,
                armed=False, selected=False,
                jsfx_plugin=JSFX_PLUGIN_APU2,
                midi_events=events, ticks_per_beat=mid.ticks_per_beat,
            )
            # Default-mute so user hears the stem, not the JSFX synth
            midi_block = re.sub(r"    MUTESOLO 0 0 0",
                                "    MUTESOLO 1 0 0", midi_block, count=1)
            lines.append(midi_block)

    lines.append(">")
    rpp_path.parent.mkdir(parents=True, exist_ok=True)
    rpp_path.write_text("\n".join(lines), encoding="utf-8")


def render_combo(combo: dict, seconds: float | None = None,
                 force: bool = False, vol_max: int = 10) -> Path | None:
    """Render stems + MIDI + RPP for a single Bach x stage combo."""
    bach = combo["bach"]
    stage = combo["stage"]
    midi_src = find_midi(bach["file"])
    if midi_src is None:
        print(f"  SKIP (missing MIDI): {bach['file']}")
        return None

    slug = slugify(combo["name"])
    project_dir = OUT_ROOT / slug
    stems_dir = project_dir / "stems"
    rpp_path = project_dir / f"{slug}.rpp"
    midi_dst = project_dir / f"{slug}.mid"

    if rpp_path.exists() and not force:
        print(f"  SKIP (exists): {slug}")
        return rpp_path

    # 1. Render stems (shared-scale normalized per outputv6 convention)
    render_bach_stems(midi_src, stems_dir, stage["p1_duty"], stage["p2_duty"],
                      max_seconds=seconds, vol_max=vol_max)

    # 2. Remap MIDI to NES channels 0-3 (using same role auto-mapping as stems)
    mid = mido.MidiFile(str(midi_src))
    _, stats = bach_analyze(mid)
    role_map = map_channels_to_roles(stats)
    remap_midi_to_nes(midi_src, midi_dst, role_map)

    # 3. Build REAPER project
    title = f"Bach x {stage['label']} - {bach['title']}"
    build_project(midi_dst, stems_dir, rpp_path, title)

    print(f"  [{combo['score']}/10] {slug}")
    return rpp_path


def main() -> None:
    ap = argparse.ArgumentParser()
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--list", action="store_true",
                     help="Preview combos without rendering")
    grp.add_argument("--top", type=int, metavar="N",
                     help="Render the top-N scoring combos")
    grp.add_argument("--all", action="store_true",
                     help="Render every available combo")

    ap.add_argument("--voices", type=int, default=None,
                    help="Filter Bach pieces by voice count (e.g. 2, 3, 4)")
    ap.add_argument("--game", type=str, default=None,
                    help="Filter stages by game (e.g. Castlevania)")
    ap.add_argument("--composer", type=str, default=None,
                    help="Filter by composer prefix (e.g. Bach, Mozart)")
    ap.add_argument("--new-games", action="store_true",
                    help="Only use new game presets (JtS/Gradius/GnG/BC)")

    ap.add_argument("--seconds", type=float, default=None,
                    help="Cap render length per combo (default: full piece)")
    ap.add_argument("--force", action="store_true",
                    help="Re-render even if the .rpp already exists")
    ap.add_argument("--vol-max", type=int, default=10,
                    help="Max pulse volume 1-15 (default 10; 15 = buzzy, 8 = mellow)")
    args = ap.parse_args()

    filt = dict(voices=args.voices, new_games_only=args.new_games,
                game=args.game, composer=args.composer)
    combos = get_all_combos(**filt)

    # Apply top / all / list
    if args.list:
        print(f"{'Score':>5}  {'Piece':<50} {'Stage':<30}")
        print("-" * 95)
        for c in combos[:50]:
            print(f"  {c['score']:>3}   {c['bach']['title']:<50} {c['stage']['label']:<30}")
        if len(combos) > 50:
            print(f"  ... +{len(combos) - 50} more")
        print(f"\nTotal matching: {len(combos)}")
        return

    if args.top:
        # Diversity: max 2 projects per Bach piece, max 3 per stage
        selected = []
        bach_seen, stage_seen = {}, {}
        for c in combos:
            bk = c["bach"]["file"]
            sk = c["stage"]["stage"]
            if bach_seen.get(bk, 0) >= 2: continue
            if stage_seen.get(sk, 0) >= 3: continue
            selected.append(c)
            bach_seen[bk] = bach_seen.get(bk, 0) + 1
            stage_seen[sk] = stage_seen.get(sk, 0) + 1
            if len(selected) >= args.top:
                break
        combos = selected
    elif not args.all:
        ap.print_help()
        return

    print(f"Rendering {len(combos)} projects into {OUT_ROOT}/")
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    rendered = 0
    for c in combos:
        p = render_combo(c, seconds=args.seconds, force=args.force,
                         vol_max=args.vol_max)
        if p is not None:
            rendered += 1
    print(f"\nDone.  {rendered} projects in {OUT_ROOT}/")


if __name__ == "__main__":
    main()
