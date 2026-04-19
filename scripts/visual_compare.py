#!/usr/bin/env python3
"""Visual waveform + spectrogram comparison between two audio files.

Generates a side-by-side PNG showing:
  - Both waveforms stacked (so note onsets and durations visible)
  - Both spectrograms stacked (so pitches and harmonic content visible)
  - Overlaid onset detection (where note attacks occur)

If the melody/notes differ, this will be instantly visible.

Usage:
    python scripts/visual_compare.py <a.wav> <b.wav> -o out.png
"""
import argparse
import numpy as np
from pathlib import Path
from scipy.io import wavfile
from scipy.signal import stft
from math import gcd


def load_mono(path, target_sr=44100):
    sr, data = wavfile.read(str(path))
    if data.ndim == 2:
        data = data.mean(axis=1)
    data = data.astype(np.float64)
    maxv = np.max(np.abs(data))
    if maxv > 0:
        data = data / maxv
    if sr != target_sr:
        from scipy.signal import resample_poly
        g = gcd(int(sr), int(target_sr))
        data = resample_poly(data, target_sr // g, sr // g)
    return data, target_sr


def detect_onsets(audio, sr, hop=512):
    """Simple onset detector: spectral flux."""
    f, t, Z = stft(audio, fs=sr, nperseg=2048, noverlap=2048 - hop)
    mag = np.abs(Z)
    flux = np.diff(mag, axis=1).clip(min=0).sum(axis=0)
    # Normalize and threshold
    flux = flux / (flux.max() + 1e-9)
    threshold = np.percentile(flux, 85)
    # Find peaks
    peaks = []
    for i in range(2, len(flux) - 2):
        if flux[i] > threshold and flux[i] > flux[i-1] and flux[i] > flux[i+1]:
            # Require some minimum spacing
            if not peaks or (t[i+1] - peaks[-1]) > 0.05:
                peaks.append(float(t[i+1]))
    return peaks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a', type=Path, help='Reference audio (e.g. Zophar MP3 as WAV)')
    ap.add_argument('b', type=Path, help='Test audio (e.g. REAPER render)')
    ap.add_argument('-o', '--out', type=Path, required=True)
    ap.add_argument('--duration', type=float, default=15.0,
                    help='first N seconds to show (default 15)')
    ap.add_argument('--label-a', default='Reference')
    ap.add_argument('--label-b', default='Test')
    args = ap.parse_args()

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    a_data, sr = load_mono(args.a)
    b_data, _ = load_mono(args.b)

    n = int(args.duration * sr)
    a_data = a_data[:n]
    b_data = b_data[:n]

    a_onsets = detect_onsets(a_data, sr)
    b_onsets = detect_onsets(b_data, sr)

    t_wave = np.arange(len(a_data)) / sr

    fig, axes = plt.subplots(4, 1, figsize=(16, 12), sharex=True)

    # Waveforms
    axes[0].plot(t_wave, a_data, linewidth=0.3, color='steelblue')
    axes[0].set_title(f'{args.label_a} waveform - {len(a_onsets)} onsets detected')
    axes[0].set_ylabel('Amplitude')
    for o in a_onsets:
        if o < args.duration:
            axes[0].axvline(o, color='red', alpha=0.3, linewidth=0.5)

    axes[1].plot(t_wave[:len(b_data)], b_data, linewidth=0.3, color='darkorange')
    axes[1].set_title(f'{args.label_b} waveform - {len(b_onsets)} onsets detected')
    axes[1].set_ylabel('Amplitude')
    for o in b_onsets:
        if o < args.duration:
            axes[1].axvline(o, color='red', alpha=0.3, linewidth=0.5)

    # Spectrograms (log freq scale)
    for ax, (data, title) in zip(axes[2:], [(a_data, args.label_a), (b_data, args.label_b)]):
        f, t, Z = stft(data, fs=sr, nperseg=2048, noverlap=1024)
        mag = 20 * np.log10(np.abs(Z) + 1e-9)
        # Focus on musically relevant range (50 Hz - 4 kHz)
        fmask = (f >= 50) & (f <= 4000)
        ax.imshow(mag[fmask], aspect='auto', origin='lower',
                  extent=[t[0], t[-1], f[fmask][0], f[fmask][-1]],
                  cmap='viridis', vmin=-60, vmax=0)
        ax.set_title(f'{title} spectrogram (50 Hz - 4 kHz)')
        ax.set_ylabel('Hz')
        ax.set_yscale('log')
        ax.set_ylim(50, 4000)

    axes[-1].set_xlabel('Time (s)')
    plt.tight_layout()
    plt.savefig(args.out, dpi=100)
    print(f'Wrote {args.out}')
    print(f'{args.label_a}: {len(a_onsets)} onsets in {args.duration}s')
    print(f'{args.label_b}: {len(b_onsets)} onsets in {args.duration}s')
    if a_onsets and b_onsets:
        # Onset time comparison (first 20 of each)
        print(f'First 10 {args.label_a} onsets (s): {[f"{o:.2f}" for o in a_onsets[:10]]}')
        print(f'First 10 {args.label_b} onsets (s): {[f"{o:.2f}" for o in b_onsets[:10]]}')


if __name__ == '__main__':
    main()
