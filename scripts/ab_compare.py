#!/usr/bin/env python3
"""Generate an A/B listening comparison WAV from two source WAVs.

Given two WAVs (typically GME ground truth vs our render), produces a
single WAV that plays:
  [segment A from file 1] [1 sec silence] [same segment from file 2]
  [1 sec silence]
  [next segment from file 1] [1 sec silence] [same from file 2]
  ...

The segmented interleaving lets you hear short passages back-to-back
so differences are obvious without context-switching between files.

Usage:
    python scripts/ab_compare.py <a.wav> <b.wav> -o ab.wav \
        [--seg-len 10] [--gap 1] [--label-a GME] [--label-b ours]

Defaults: 10 second segments with 1 second gap, total ~30s covered.
"""
import argparse
import numpy as np
from pathlib import Path
from scipy.io import wavfile
from scipy.signal import resample_poly
from math import gcd


def load_mono(path, target_sr=44100):
    sr, data = wavfile.read(str(path))
    if data.ndim == 2:
        data = data.mean(axis=1)
    max_val = float(np.iinfo(data.dtype).max) if data.dtype.kind == 'i' else 1.0
    data = data.astype(np.float64) / max_val
    if sr != target_sr:
        g = gcd(int(sr), int(target_sr))
        data = resample_poly(data, target_sr // g, sr // g)
    return data, target_sr


def normalize(x, target_peak=0.8):
    pk = np.max(np.abs(x))
    if pk < 1e-9:
        return x
    return x * (target_peak / pk)


def make_beep(sr, duration=0.1, freq=880):
    """Short tone marker to separate A from B."""
    t = np.arange(int(sr * duration)) / sr
    return np.sin(2 * np.pi * freq * t) * 0.1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a', type=Path, help='WAV A (e.g. GME reference)')
    ap.add_argument('b', type=Path, help='WAV B (e.g. our render)')
    ap.add_argument('-o', '--out', type=Path, required=True)
    ap.add_argument('--seg-len', type=float, default=10.0,
                    help='segment length in seconds (default 10)')
    ap.add_argument('--gap', type=float, default=1.0,
                    help='gap between A and B segments (default 1)')
    ap.add_argument('--n-segments', type=int, default=3,
                    help='number of A/B pairs to include (default 3)')
    ap.add_argument('--label-a', default='A',
                    help='label tone frequency for A (default 880 Hz)')
    ap.add_argument('--label-b', default='B',
                    help='label tone frequency for B (default 1320 Hz)')
    ap.add_argument('--match-levels', action='store_true',
                    help='normalize both to same peak (often useful)')
    args = ap.parse_args()

    sr = 44100
    a_data, _ = load_mono(args.a, sr)
    b_data, _ = load_mono(args.b, sr)

    if args.match_levels:
        a_data = normalize(a_data, 0.8)
        b_data = normalize(b_data, 0.8)

    seg_samples = int(args.seg_len * sr)
    gap_samples = int(args.gap * sr)
    gap = np.zeros(gap_samples)
    marker_a = make_beep(sr, 0.05, 880)   # higher pitch for A
    marker_b = make_beep(sr, 0.05, 523)   # lower pitch for B
    marker_gap = np.zeros(int(sr * 0.1))  # 100ms silence after marker

    parts = []
    for i in range(args.n_segments):
        off = i * seg_samples
        a_seg = a_data[off:off + seg_samples] if off + seg_samples <= len(a_data) else a_data[off:]
        b_seg = b_data[off:off + seg_samples] if off + seg_samples <= len(b_data) else b_data[off:]
        if len(a_seg) == 0 or len(b_seg) == 0:
            break
        # marker + silence + content
        parts.append(np.concatenate([marker_a, marker_gap, a_seg]))
        parts.append(gap)
        parts.append(np.concatenate([marker_b, marker_gap, b_seg]))
        if i < args.n_segments - 1:
            parts.append(gap * 2)  # longer gap between pairs

    out = np.concatenate(parts)
    out = np.clip(out, -0.99, 0.99)
    out_int = (out * 32767).astype(np.int16)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(args.out), sr, out_int)

    duration = len(out) / sr
    print(f'Wrote {args.out} ({duration:.1f}s)')
    print(f'Format: high-beep -> {args.label_a} {args.seg_len:.0f}s, '
          f'low-beep -> {args.label_b} {args.seg_len:.0f}s, x {args.n_segments}')


if __name__ == '__main__':
    main()
