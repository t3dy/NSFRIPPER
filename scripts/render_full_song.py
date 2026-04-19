#!/usr/bin/env python3
"""Render a full-length WAV for a given NSF track via Python render_wav().

Separate from nsf_to_reaper.py which is the full pipeline; this one
just produces the audio for the audio-track-in-REAPER architecture.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
# Avoid import side effects; reuse the extraction functions directly
from nsf_to_reaper import (
    run_emulation_capture, frames_to_channel_data, render_wav
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('nsf')
    ap.add_argument('--song', type=int, required=True, help='1-indexed track')
    ap.add_argument('--seconds', type=float, default=90.0)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    frames_target = int(args.seconds * 60)
    print(f'Emulating {args.nsf} song {args.song} for {frames_target} frames...')
    emu_state = run_emulation_capture(args.nsf, args.song - 1, frames_target)
    channels = frames_to_channel_data(emu_state['frames'], emu_state.get('expansion_chips'))
    duration = render_wav(channels, args.out, frames_target)
    print(f'Wrote {args.out} ({duration:.1f}s)')


if __name__ == '__main__':
    main()
