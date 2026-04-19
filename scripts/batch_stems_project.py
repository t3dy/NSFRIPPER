#!/usr/bin/env python3
"""Batch-build stem-based REAPER projects for all songs in an NSF.

For each song in the NSF:
  1. Render per-channel audio stems (pulse1/pulse2/triangle/noise)
  2. Build a REAPER project with the stems + editable MIDI tracks

The output layout:
    <out_dir>/stems/<song_slug>/{pulse1,pulse2,triangle,noise}.wav
    <out_dir>/reaper/<song_slug>.rpp
    <out_dir>/midi/<song_slug>.mid

Usage:
    python scripts/batch_stems_project.py <nsf> \
      [--name-json names.json] [--seconds 90] --out-dir outputv5/<Game>/
"""
import argparse
import json
import re
import subprocess
import sys
import wave
from datetime import datetime
from pathlib import Path


PIPELINE_VERSION = "v6.2"  # bumped when the stems pipeline contract changes


def slugify(s):
    s = re.sub(r'[\s]+', '_', s.strip())
    s = re.sub(r'[^\w\-_().]', '', s)
    return s or 'untitled'


def parse_m3u(m3u_path):
    """Return list of {num, name, seconds} from an nsfe2m3u-style playlist.

    Only tracks listed in the M3U are returned.  Many NSFs contain both
    music and sound-effect banks; the M3U is the canonical "music only"
    filter (e.g. Section Z lists tracks 21-32, SFX live at 1-20).

    Raises ValueError if any parsed `num` is < 1 (validation guard
    against malformed M3Us that could propagate as invalid NSF track
    indices through the pipeline).
    """
    tracks = []
    with open(m3u_path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            m = re.match(r'.*::NSF,(\d+),([^,]*),([^,]*)', line)
            if not m:
                continue
            num = int(m.group(1))
            if num < 1:
                raise ValueError(
                    f"M3U {m3u_path.name}: parsed NSF track number {num} < 1. "
                    "NSF track numbers are 1-indexed per NSF specification."
                )
            name = m.group(2).strip() or f'Song_{num}'
            dur = m.group(3).strip()
            seconds = 90.0
            try:
                parts = dur.split(':')
                if len(parts) == 3:
                    seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                elif len(parts) == 2:
                    seconds = int(parts[0]) * 60 + float(parts[1])
                elif len(parts) == 1 and parts[0]:
                    seconds = float(parts[0])
            except Exception:
                pass
            tracks.append({'num': num, 'name': name, 'seconds': max(seconds, 10)})
    return tracks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('nsf')
    ap.add_argument('--out-dir', type=Path, required=True)
    ap.add_argument('--seconds', type=float, default=90.0,
                    help='Default duration when no M3U. With M3U, per-track '
                         'durations are used (capped at this value).')
    ap.add_argument('--names', type=Path, help='JSON mapping track_num -> song_name (overrides M3U names)')
    ap.add_argument('--m3u', type=Path, help='Explicit M3U path (default: auto-detect next to NSF)')
    ap.add_argument('--no-m3u', action='store_true', help='Ignore M3U even if present (render all NSF tracks)')
    ap.add_argument('--numeric-labels', action='store_true',
                    help='Use numeric "Song_NN" labels (by NSF track number) '
                         'instead of M3U labels.  Still uses M3U for music-'
                         'track filtering and per-track durations.')
    ap.add_argument('--only', type=int, help='only render this track (1-indexed)')
    args = ap.parse_args()

    # Count tracks in the NSF
    with open(args.nsf, 'rb') as f:
        data = f.read()
    total_songs = data[6]
    print(f'NSF has {total_songs} songs')

    names = {}
    if args.names and args.names.is_file():
        names = json.loads(args.names.read_text())

    # Locate M3U: explicit --m3u, else same-name .m3u next to NSF
    m3u_tracks = []
    if not args.no_m3u:
        m3u_path = args.m3u
        if not m3u_path:
            nsf_path = Path(args.nsf)
            candidate = nsf_path.with_suffix('.m3u')
            if candidate.is_file():
                m3u_path = candidate
            else:
                for m in nsf_path.parent.glob('*.m3u'):
                    m3u_path = m
                    break
        if m3u_path and m3u_path.is_file():
            m3u_tracks = parse_m3u(m3u_path)
            print(f'M3U: {m3u_path.name} ({len(m3u_tracks)} music tracks)')
        else:
            print('No M3U found; rendering all NSF tracks')

    midi_dir = args.out_dir / 'midi'
    stems_root = args.out_dir / 'stems'
    rpp_dir = args.out_dir / 'reaper'
    for d in (midi_dir, stems_root, rpp_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Extraction stage: need MIDI per song
    # Piggyback on nsf_to_reaper for MIDI extraction
    midi_output_dir = args.out_dir / '_nsf_extract'
    midi_output_dir.mkdir(parents=True, exist_ok=True)

    # Build ordered (song_num, name, seconds) list. M3U order is preserved
    # so the first audible music track lands at position 1 in output.
    if m3u_tracks:
        queue = [(t['num'], t['name'], min(t['seconds'], args.seconds))
                 for t in m3u_tracks]
    else:
        queue = [(s, names.get(str(s), f'Song_{s:02d}'), args.seconds)
                 for s in range(1, total_songs + 1)]

    # Numeric-labels override: replace M3U/default names with "Song_NN"
    # where NN is the NSF track number.  Keeps M3U filtering (music only)
    # and durations, but avoids M3U label mistakes (e.g. Zophar's FF1
    # labels Battle Scene as NSF track 16 when it's actually elsewhere).
    if args.numeric_labels:
        queue = [(num, f'Song_{num:02d}', sec) for (num, _, sec) in queue]

    for position, (song, song_name, song_seconds) in enumerate(queue, start=1):
        if args.only and song != args.only:
            continue
        if args.names and str(song) in names:
            song_name = names[str(song)]

        slug = f'{position:02d}_{slugify(song_name)}'
        print(f'\n=== Position {position} / NSF track {song}: {song_name} ({song_seconds:.0f}s) ===')

        # Extract MIDI + run pipeline (also produces per-frame channels data)
        # Call nsf_to_reaper.py to get MIDI file into midi_output_dir
        subprocess.run([
            sys.executable, 'scripts/nsf_to_reaper.py',
            args.nsf, str(song), str(song_seconds),
            '-o', str(midi_output_dir),
            '--skip-wav',
        ], check=False)

        # Find the resulting MIDI file
        mids = list((midi_output_dir / 'midi').glob(f'*_{song:02d}_*.mid'))
        if not mids:
            print(f'  no MIDI produced, skipping')
            continue
        src_mid = mids[0]
        dst_mid = midi_dir / f'{slug}.mid'
        dst_mid.write_bytes(src_mid.read_bytes())

        # Guard: never pass a non-1-indexed NSF track number to the
        # stem renderer (see docs/NAMING_POLICY.md).  Silent off-by-one
        # caused the 2026-04-19 session's track-shift bug.
        if song < 1:
            print(f'  ERROR: NSF track number {song} < 1 is invalid, skipping')
            continue

        # Render stems
        stems_dir = stems_root / slug
        r = subprocess.run([
            sys.executable, 'scripts/render_channel_stems.py',
            args.nsf,
            '--song', str(song),
            '--seconds', str(song_seconds),
            '--out-dir', str(stems_dir),
        ])
        if r.returncode != 0:
            print(f'  stem render failed')
            continue

        # Emit sidecar track.json (source of truth for audit_names.py).
        # Name source mirrors the resolution order used above: --names
        # JSON > M3U label > "Song_NN" fallback (numeric-labels forces
        # the fallback form).
        if args.names and str(song) in names:
            name_source = 'names_json'
        elif args.numeric_labels:
            name_source = 'numeric_fallback'
        elif m3u_tracks:
            name_source = 'm3u'
        else:
            name_source = 'nsf_index_fallback'
        rendered_seconds = None
        p1 = stems_dir / 'pulse1.wav'
        if p1.is_file():
            try:
                with wave.open(str(p1)) as w:
                    rendered_seconds = round(w.getnframes() / w.getframerate(), 2)
            except Exception:
                pass
        m3u_decl_sec = None
        m3u_file = None
        if m3u_tracks:
            for t in m3u_tracks:
                if t['num'] == song:
                    m3u_decl_sec = round(t['seconds'], 2)
                    break
            if m3u_path:
                m3u_file = m3u_path.name
        sidecar = {
            'pipeline_version': PIPELINE_VERSION,
            'pipeline_date': datetime.now().strftime('%Y-%m-%d'),
            'nsf_file': Path(args.nsf).name,
            'nsf_track': song,
            'm3u_position': position,
            'name': song_name,
            'name_source': name_source,
            'm3u_file': m3u_file,
            'm3u_declared_seconds': m3u_decl_sec,
            'rendered_seconds': rendered_seconds,
            'seconds_cap': args.seconds,
        }
        (stems_dir / 'track.json').write_text(
            json.dumps(sidecar, indent=2), encoding='utf-8')

        # Build the stem RPP
        rpp_path = rpp_dir / f'{slug}.rpp'
        subprocess.run([
            sys.executable, 'scripts/generate_stems_rpp.py',
            '--midi', str(dst_mid),
            '--stems-dir', str(stems_dir),
            '--out', str(rpp_path),
        ], check=False)

        # Swap plugin to v2
        if rpp_path.is_file():
            t = rpp_path.read_text(encoding='utf-8')
            if 'ReapNES_APU2.jsfx' in t:
                rpp_path.write_text(t.replace('ReapNES_APU2.jsfx', 'ReapNES_APU2_v2.jsfx'), encoding='utf-8')

    print(f'\nAll done. Projects in: {rpp_dir}')


if __name__ == '__main__':
    main()
