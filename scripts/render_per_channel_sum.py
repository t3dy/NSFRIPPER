#!/usr/bin/env python3
"""Render each NES channel in isolation then LINEARLY SUM them.
Mimics what REAPER's multi-track architecture produces.

If this output matches REAPER's render, the JSFX is just reproducing
the linear-sum artifact. If this output has all notes but REAPER doesn't,
the JSFX has an extra bug we need to find.
"""
import sys
import numpy as np
import wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from nsf_to_reaper import (
    NsfEmulator, frames_to_channel_data, SAMPLE_RATE, SPF
)

import argparse
ap = argparse.ArgumentParser()
ap.add_argument('nsf')
ap.add_argument('--song', type=int, required=True)
ap.add_argument('--seconds', type=float, default=30.0)
ap.add_argument('--out', required=True)
args = ap.parse_args()

frames_target = int(args.seconds * 60)
emu = NsfEmulator(args.nsf)
frames = emu.play_song(args.song - 1, frames_target)
channels = frames_to_channel_data(frames, getattr(emu, 'expansion_chips', None))

actual_frames = len(channels["pulse1"]["notes"])
num_frames = min(frames_target, actual_frames)
total_samples = num_frames * SPF

# Run the SAME envelope + LC sim render_wav() does, but produce
# per-channel waveforms (no non-linear DAC). Then linearly sum.
phase = {"p1": 0.0, "p2": 0.0, "tri": 0.0}
p_env = {
    "pulse1": {"decay": 15, "divider": 0, "start_flag": False},
    "pulse2": {"decay": 15, "divider": 0, "start_flag": False},
}
tri_linear_live = 0
tri_reload_flag = False

# One audio buffer per channel, each centered (like a REAPER track output would be)
p1_audio = np.zeros(total_samples)
p2_audio = np.zeros(total_samples)
tri_audio = np.zeros(total_samples)
noi_audio = np.zeros(total_samples)

for frame in range(num_frames):
    s = frame * SPF

    # HW envelope ticks (same as render_wav)
    for ch_name in ("pulse1", "pulse2"):
        fd = channels[ch_name]["notes"][frame]
        env = p_env[ch_name]
        if fd["phase_reset"]:
            env["start_flag"] = True
        period = fd["env_period"]
        loop = fd["env_loop"]
        for _ in range(4):
            if env["start_flag"]:
                env["decay"] = 15
                env["divider"] = period
                env["start_flag"] = False
            else:
                if env["divider"] == 0:
                    if env["decay"] > 0:
                        env["decay"] -= 1
                    elif loop:
                        env["decay"] = 15
                    env["divider"] = period
                else:
                    env["divider"] -= 1

    # Triangle LC ticks
    tri_fd = channels["triangle"]["notes"][frame]
    if tri_fd["phase_reset"]:
        tri_reload_flag = True
    tri_ctrl = tri_fd["linear_control"]
    tri_reload = tri_fd["linear_reload"]
    for _ in range(4):
        if tri_reload_flag:
            tri_linear_live = tri_reload
        elif tri_linear_live > 0:
            tri_linear_live -= 1
        if tri_ctrl == 0:
            tri_reload_flag = False

    # Generate per-channel waveforms
    for ch_name, ph_key, out_arr in [("pulse1", "p1", p1_audio), ("pulse2", "p2", p2_audio)]:
        fd = channels[ch_name]["notes"][frame]
        p, d = fd["period"], fd["duty"]
        effective_vol = fd["env_period"] if fd["const_vol"] else p_env[ch_name]["decay"]
        if p >= 8 and effective_vol > 0:
            freq = 1789773 / (16 * (p + 1))
            dv = [0.125, 0.25, 0.5, 0.75][d]
            pa = (np.arange(SPF) * freq / SAMPLE_RATE + phase[ph_key]) % 1.0
            # Center around 0: v/15 - 0.5 when in "on" half, 0 - 0.5 when "off"
            wave_raw = np.where(pa < dv, effective_vol / 15.0, 0.0) - 0.5
            out_arr[s:s+SPF] = wave_raw
            phase[ph_key] = (phase[ph_key] + SPF * freq / SAMPLE_RATE) % 1.0

    p = tri_fd["period"]
    if p >= 2 and tri_linear_live > 0:
        freq = 1789773 / (32 * (p + 1))
        pa = (np.arange(SPF) * freq / SAMPLE_RATE + phase["tri"]) % 1.0
        tri_wave = np.where(pa < 0.5, pa * 30, (1.0 - pa) * 30) / 15.0 - 0.5
        tri_audio[s:s+SPF] = tri_wave
        phase["tri"] = (phase["tri"] + SPF * freq / SAMPLE_RATE) % 1.0

    fd = channels["noise"]["notes"][frame]
    nv = fd["vol"]
    if nv > 0:
        noi_audio[s:s+SPF] = (np.random.uniform(0, nv, SPF) / 15.0) - 0.5

# Linear sum as REAPER master bus would do, then scale
sum_wave = (p1_audio + p2_audio + tri_audio + noi_audio) * 0.2
sum_wave = np.clip(sum_wave, -0.99, 0.99)
audio = (sum_wave * 32767).astype(np.int16)

with wave.open(args.out, 'w') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(audio.tobytes())

print(f'Wrote {args.out}')
