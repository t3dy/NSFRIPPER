#!/usr/bin/env python3
"""Spectral diff between two WAV files.  Tells you WHERE and IN WHICH BAND
our rendered audio diverges from a reference.

Use cases:
- reference = NSFPlay render of the NSF (hardware-accurate ground truth)
- reference = Mesen audio dump from real game playback
- reference = Our own render_wav() output (Python pipeline)
- test = REAPER render of the generated RPP project
- test = Any other pipeline output you want to validate

Output:
- Console: per-band divergence summary + top N mismatch time-windows
- CSV: per-frame, per-band dB delta (for further analysis)
- PNG: heatmap of dB delta over time x frequency band (optional)

Usage:
    python scripts/audio_diff.py <reference.wav> <test.wav> [--out diff.csv]
    python scripts/audio_diff.py --reference ref.wav --test test.wav --plot diff.png

Align strategy: cross-correlate first 2 seconds of both; shift test by
the lag that maximizes correlation. Normalize both to unit RMS so we
compare spectral shape, not absolute level.

Banding: 8 log-frequency bands covering 50 Hz to 16 kHz. Catches the
main perceptual regions (sub, bass, low-mid, mid, upper-mid, presence,
brilliance, air).
"""
import argparse
import csv
import numpy as np
from pathlib import Path
from scipy.io import wavfile
from scipy.signal import stft, correlate


BAND_EDGES_HZ = [50, 120, 250, 500, 1000, 2000, 4000, 8000, 16000]
BAND_NAMES = ['sub(50-120)', 'bass(120-250)', 'lowmid(250-500)',
              'mid(500-1k)', 'uppermid(1-2k)', 'presence(2-4k)',
              'brilliance(4-8k)', 'air(8-16k)']


def load_mono(path, target_sr=44100):
    sr, data = wavfile.read(str(path))
    if data.ndim == 2:
        data = data.mean(axis=1)
    data = data.astype(np.float64)
    # Normalize by dtype range
    if data.dtype != np.float64:
        pass  # already converted
    max_abs = np.max(np.abs(data))
    if max_abs > 0:
        data = data / max_abs
    # Resample if needed
    if sr != target_sr:
        from scipy.signal import resample_poly
        from math import gcd
        g = gcd(int(sr), int(target_sr))
        up = target_sr // g
        down = sr // g
        data = resample_poly(data, up, down)
    return data, target_sr


def align_by_xcorr(ref, test, sr, max_shift_s=2.0):
    """Return test shifted to align with ref. Uses xcorr on first window."""
    win = min(int(sr * max_shift_s), len(ref), len(test))
    ref_win = ref[:win]
    test_win = test[:win]
    corr = correlate(test_win, ref_win, mode='full', method='fft')
    lag = corr.argmax() - (len(ref_win) - 1)
    if lag > 0:
        aligned = test[lag:]
    elif lag < 0:
        aligned = np.concatenate([np.zeros(-lag), test])
    else:
        aligned = test
    # Match length
    n = min(len(ref), len(aligned))
    return ref[:n], aligned[:n], lag


def rms_normalize(x):
    rms = np.sqrt(np.mean(x * x))
    return x / rms if rms > 1e-9 else x


def band_energies(Zxx, freqs, edges):
    """Zxx: (freq_bins, frames) complex STFT.  Returns (n_bands, frames) dB."""
    mag = np.abs(Zxx)
    n_bands = len(edges) - 1
    n_frames = mag.shape[1]
    out = np.zeros((n_bands, n_frames))
    for b in range(n_bands):
        f_lo, f_hi = edges[b], edges[b + 1]
        mask = (freqs >= f_lo) & (freqs < f_hi)
        if mask.any():
            energy = np.sqrt(np.mean(mag[mask, :] ** 2, axis=0) + 1e-12)
            # Floor at -80 dBFS to avoid "near-silence vs silence" showing
            # as 100+ dB mismatches.  Real musical divergence is at most ~40 dB.
            out[b] = np.maximum(20 * np.log10(energy + 1e-9), -80.0)
    return out


def spectral_diff(ref, test, sr, window_s=0.050):
    """Return (time_s, band_delta_db, band_names, ref_rms_dbfs, test_rms_dbfs)."""
    nperseg = int(sr * window_s)
    nperseg = max(256, min(4096, nperseg))
    # STFT with 50% overlap
    f_ref, t_ref, Z_ref = stft(ref, fs=sr, nperseg=nperseg, noverlap=nperseg // 2,
                                boundary=None, padded=False)
    f_test, t_test, Z_test = stft(test, fs=sr, nperseg=nperseg, noverlap=nperseg // 2,
                                    boundary=None, padded=False)
    n_frames = min(Z_ref.shape[1], Z_test.shape[1])
    Z_ref = Z_ref[:, :n_frames]
    Z_test = Z_test[:, :n_frames]
    t_ref = t_ref[:n_frames]

    band_ref = band_energies(Z_ref, f_ref, BAND_EDGES_HZ)
    band_test = band_energies(Z_test, f_ref, BAND_EDGES_HZ)
    # Delta = test minus ref.  Positive = test louder, negative = test quieter.
    band_delta = band_test - band_ref
    return t_ref, band_delta, BAND_NAMES


def find_divergence_hotspots(t, band_delta, top_n=10, min_db=6.0):
    """Return list of (time_s, band_idx, band_name, delta_db, sign) for the
    top N most divergent frames (by abs value), above min_db threshold."""
    abs_delta = np.abs(band_delta)
    # Flatten indices
    flat = abs_delta.flatten()
    order = np.argsort(flat)[::-1]  # descending
    hotspots = []
    seen_windows = set()
    for idx in order:
        band_idx, frame_idx = np.unravel_index(idx, abs_delta.shape)
        delta = band_delta[band_idx, frame_idx]
        if abs(delta) < min_db:
            break
        # Deduplicate within 200ms windows
        win_key = (int(t[frame_idx] * 5), band_idx)
        if win_key in seen_windows:
            continue
        seen_windows.add(win_key)
        hotspots.append({
            'time_s': float(t[frame_idx]),
            'frame': int(frame_idx),
            'band': BAND_NAMES[band_idx],
            'delta_db': float(delta),
            'sign': 'TEST LOUDER' if delta > 0 else 'TEST QUIETER',
        })
        if len(hotspots) >= top_n:
            break
    return hotspots


def summarize_bands(band_delta):
    """Per-band overall bias summary."""
    rows = []
    for b, name in enumerate(BAND_NAMES):
        d = band_delta[b]
        rows.append({
            'band': name,
            'mean_db': float(d.mean()),
            'std_db': float(d.std()),
            'p50': float(np.percentile(d, 50)),
            'p95_abs': float(np.percentile(np.abs(d), 95)),
        })
    return rows


def write_csv(path, t, band_delta):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['time_s'] + BAND_NAMES)
        for frame_idx in range(len(t)):
            row = [f'{t[frame_idx]:.3f}']
            row += [f'{band_delta[b, frame_idx]:.2f}' for b in range(len(BAND_NAMES))]
            w.writerow(row)


def save_plot(path, t, band_delta):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(14, 5))
    # Clip to +-24 dB for visibility
    cb = ax.imshow(band_delta, aspect='auto', origin='lower',
                   extent=[t[0], t[-1], 0, len(BAND_NAMES)],
                   vmin=-24, vmax=24, cmap='RdBu_r', interpolation='nearest')
    ax.set_yticks(np.arange(len(BAND_NAMES)) + 0.5)
    ax.set_yticklabels(BAND_NAMES, fontsize=8)
    ax.set_xlabel('Time (s)')
    ax.set_title('Spectral diff (test - reference), dB. Red=test louder, blue=test quieter')
    plt.colorbar(cb, ax=ax, label='dB')
    plt.tight_layout()
    plt.savefig(path, dpi=100)
    plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('reference', type=Path, help='reference WAV (ground truth)')
    ap.add_argument('test', type=Path, help='test WAV (your render)')
    ap.add_argument('--out', type=Path, help='CSV path for per-frame data')
    ap.add_argument('--plot', type=Path, help='PNG heatmap path')
    ap.add_argument('--top', type=int, default=15, help='top N divergence hotspots')
    ap.add_argument('--min-db', type=float, default=6.0, help='hotspot threshold in dB')
    ap.add_argument('--window-ms', type=float, default=50.0, help='STFT window length')
    ap.add_argument('--no-align', action='store_true', help='skip xcorr alignment')
    ap.add_argument('--no-normalize', action='store_true',
                    help='skip RMS normalization - compare absolute levels')
    args = ap.parse_args()

    print(f'Loading reference: {args.reference}')
    ref, sr = load_mono(args.reference)
    print(f'Loading test:      {args.test}')
    test, _ = load_mono(args.test, target_sr=sr)

    if not args.no_normalize:
        ref = rms_normalize(ref)
        test = rms_normalize(test)

    if not args.no_align:
        ref, test, lag = align_by_xcorr(ref, test, sr)
        print(f'Alignment shift: {lag} samples ({lag / sr * 1000:.1f} ms)')

    t, delta, names = spectral_diff(ref, test, sr, window_s=args.window_ms / 1000.0)

    print(f'\n=== Per-band overall divergence ===')
    print(f'{"Band":<22s} {"mean dB":>8s} {"std":>6s} {"p50":>6s} {"p95_abs":>8s}')
    print('-' * 60)
    for row in summarize_bands(delta):
        print(f'{row["band"]:<22s} {row["mean_db"]:>+7.1f} '
              f'{row["std_db"]:>5.1f} {row["p50"]:>+5.1f} '
              f'{row["p95_abs"]:>7.1f}')

    print(f'\n=== Top {args.top} divergence hotspots (>{args.min_db} dB) ===')
    hotspots = find_divergence_hotspots(t, delta, args.top, args.min_db)
    if not hotspots:
        print('(no frames exceed threshold -- test and reference are close)')
    else:
        print(f'{"Time":>7s} {"Band":<22s} {"Delta":>8s} Direction')
        print('-' * 65)
        for h in hotspots:
            print(f'{h["time_s"]:>6.2f}s {h["band"]:<22s} {h["delta_db"]:>+6.1f} dB  {h["sign"]}')

    if args.out:
        write_csv(args.out, t, delta)
        print(f'\nWrote per-frame CSV: {args.out}')

    if args.plot:
        save_plot(args.plot, t, delta)
        print(f'Wrote heatmap PNG:   {args.plot}')


if __name__ == '__main__':
    main()
