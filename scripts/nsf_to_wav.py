#!/usr/bin/env python3
"""Render an NSF track to WAV using Game Music Emu (ffmpeg's libgme demuxer).

GME is the reference NSF player used by most emulator frontends. Its
output IS the hardware-accurate "this is what the NSF driver produces
on real NES APU" audio. Use this as ground truth for audio diff against
our REAPER-rendered or Python-rendered output.

Note: GME simulates the NSF init + play routines internally using its
own 6502 emulator + APU. It handles bankswitching, expansion audio
(VRC6/FDS/MMC5/VRC7/5B), non-linear mixing, and all envelope / linear
counter / sweep state. Much more complete than our Python render_wav().

Usage:
    python scripts/nsf_to_wav.py <nsf_path> --song <1-indexed> --out <out.wav>
    python scripts/nsf_to_wav.py <nsf_path> --song 3 --out ref.wav --duration 30

Optional:
    --duration <sec>    render duration in seconds (default: 60)
    --fade <sec>        fade-out at end (default: 2; set 0 to disable)
    --sample-rate <hz>  output sample rate (default: 44100)
    --ffmpeg <path>     path to ffmpeg.exe (default: resolve via PATH)
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def render_nsf(nsf_path, song_1indexed, out_wav, duration=60, fade=2,
               sample_rate=44100, ffmpeg_exe='ffmpeg'):
    if not os.path.exists(nsf_path):
        print(f'ERROR: NSF not found: {nsf_path}', file=sys.stderr)
        return 1

    if not shutil.which(ffmpeg_exe):
        print(f'ERROR: ffmpeg not found (tried: {ffmpeg_exe})', file=sys.stderr)
        print('Install ffmpeg or point --ffmpeg at its path.', file=sys.stderr)
        return 2

    os.makedirs(os.path.dirname(os.path.abspath(out_wav)) or '.', exist_ok=True)
    track_index = song_1indexed - 1
    cmd = [
        ffmpeg_exe, '-hide_banner', '-y',
        '-track_index', str(track_index),
        '-i', str(nsf_path),
        '-t', str(duration),
        '-ac', '2',
        '-ar', str(sample_rate),
    ]
    # Apply a short fade-out so endings don't click
    if fade > 0:
        fade_start = max(0, duration - fade)
        cmd += ['-af', f'afade=t=out:st={fade_start}:d={fade}']
    cmd.append(str(out_wav))

    print(f'Rendering NSF track {song_1indexed} ({duration}s) via libgme...')
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f'ffmpeg stderr:\n{result.stderr}', file=sys.stderr)
        return 3

    size_kb = os.path.getsize(out_wav) / 1024
    print(f'Wrote {size_kb:.0f} KB -> {out_wav}')
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    ap.add_argument('nsf', help='NSF file path')
    ap.add_argument('--song', type=int, required=True, help='track number (1-indexed)')
    ap.add_argument('--out', required=True, help='output WAV path')
    ap.add_argument('--duration', type=float, default=60, help='seconds')
    ap.add_argument('--fade', type=float, default=2, help='fade-out seconds (0 = none)')
    ap.add_argument('--sample-rate', type=int, default=44100)
    ap.add_argument('--ffmpeg', default='ffmpeg', help='ffmpeg executable')
    args = ap.parse_args()
    sys.exit(render_nsf(args.nsf, args.song, args.out, args.duration,
                         args.fade, args.sample_rate, args.ffmpeg))


if __name__ == '__main__':
    main()
