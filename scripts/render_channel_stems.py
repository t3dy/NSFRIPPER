#!/usr/bin/env python3
"""Render each NES channel as its own hardware-accurate WAV stem.

Uses the same HW envelope + linear counter simulation as render_wav()
but runs the non-linear DAC for ONE channel at a time. Produces:

  p1.wav   - pulse 1 with only pulse 1 contribution through DAC
  p2.wav   - pulse 2 alone through DAC
  tri.wav  - triangle alone through TND DAC
  noise.wav - noise alone through TND DAC
  dmc.wav  - DMC alone through TND DAC (silent if game uses no DMC)

The 5 stems, loaded as separate tracks in REAPER and summed linearly on
master, approximate the full hardware mix.  Minor inaccuracy: hardware
non-linear DAC is non-additive, so sum of stems != full mix exactly.
But each stem is an authentic single-channel render -- user can
mute/solo/FX each channel and the sum sounds like the game.

Usage:
    python scripts/render_channel_stems.py <nsf> --song 3 --seconds 30 \
        --out-dir stems/ww_song3/
"""
import argparse
import sys
import numpy as np
import wave
from pathlib import Path
from scipy.signal import butter, lfilter

sys.path.insert(0, str(Path(__file__).parent))
from nsf_to_reaper import (
    NsfEmulator, frames_to_channel_data, SAMPLE_RATE, SPF,
    _apu_nonlinear_mix,
)


# NTSC DMC playback rates (CPU cycles per output bit, 16 entries by rate index)
NTSC_DMC_RATES = [428, 380, 340, 320, 286, 254, 226, 214,
                  190, 160, 142, 128, 106, 84, 72, 54]
CPU_HZ_F = 1789773.0

# NES analog output low-pass: the real hardware has an RC filter that
# smooths the DAC output.  Our pulse/triangle waves are sampled at 44.1 kHz
# with hard zero-to-amplitude edges, which produces aliasing AND per-note
# click transients when volume steps (0 -> 15) land between samples.
#
# A 4-pole Butterworth LP at ~14 kHz approximates the hardware's response
# (real NES has multi-stage RC filtering in the audio output path, not
# a single RC).  2-pole at Q=0.707 left ~0.1-magnitude single-sample
# clicks at pulse edges (the bandlimited synthesis reduces but does not
# eliminate one-sample edge steps -- the remaining 3-level edges still
# have broadband content).  4-pole gives 24 dB/octave rolloff above
# 14 kHz instead of 12 dB/octave, dropping 22 kHz content by ~12 dB vs
# ~6 dB, which audibly softens the "overdrive / hiss" on bright pulse
# notes without dulling the fundamentals.
_NES_LP_B, _NES_LP_A = butter(4, 14000.0, btype='low', fs=SAMPLE_RATE)

# DC blocker (one-pole HP ~10 Hz).  Replaces naive `mix -= mean(mix)`,
# which leaves a static DC offset in silent regions when the overall
# signal is asymmetric (drums on a noise stem -> silent regions ended up
# at -0.030 instead of 0, causing every frame to register as "active").
_DC_HP_B, _DC_HP_A = butter(1, 10.0, btype='high', fs=SAMPLE_RATE)


def apply_nes_analog_lp(signal):
    """Apply the NES analog output LP to a float signal."""
    return lfilter(_NES_LP_B, _NES_LP_A, signal)


def dc_block(signal):
    """Remove DC drift without introducing offsets in silent regions."""
    return lfilter(_DC_HP_B, _DC_HP_A, signal)


def _bandlimited_pulse(freq, duty, vol, phase, key):
    """Render SPF samples of a NES pulse with proper anti-aliased edges.

    Rule 35 (2026-04-18 evening): Instead of sampling the naive square wave
    `np.where(pa%1 < duty, vol, 0)` at the output rate -- which aliases
    every edge into audible grit -- we analytically integrate the ideal
    pulse function over each sample's time window:

        fraction_high = (H(pa_end) - H(pa_start)) / (pa_end - pa_start)

    where H(x) = duty*floor(x) + min(x-floor(x), duty) is the integral of
    1{pa%1 < duty} from 0 to x. This gives the exact time-averaged
    amplitude over the sample window, which is the correct band-limited
    value. Sample-level steps at pulse edges go from ~0.1 (naive) to
    near-zero (integrated), eliminating the "hiss / overdrive" from
    high-pitched pulses.

    Phase advances to pa_end of the last sample (continuous across frames).
    """
    step = freq / SAMPLE_RATE
    if step <= 0.0:
        return np.zeros(SPF)
    p0 = phase[key]
    pa_start = np.arange(SPF, dtype=np.float64) * step + p0
    pa_end = pa_start + step
    # H(x) = duty * floor(x) + min(x - floor(x), duty)
    h_start = duty * np.floor(pa_start) + np.minimum(pa_start - np.floor(pa_start), duty)
    h_end = duty * np.floor(pa_end) + np.minimum(pa_end - np.floor(pa_end), duty)
    fraction_high = (h_end - h_start) / step
    phase[key] = pa_end[-1] % 1.0
    return fraction_high * vol


def render_dmc_stem(channels, num_frames, rom_data, load_addr, normalize=True):
    """Render DMC channel: DPCM sample playback + direct DAC writes.

    Two mechanisms (per architecture.md Rule 28):
      1. dpcm_trigger event: sample loaded from ROM at sample_addr,
         delta-decoded at NTSC_DMC_RATES[rate_idx] CPU cycles per bit.
      2. dac_write event: $4011 written directly, sets DAC value.
    """
    actual_frames = len(channels["dmc"]["notes"])
    num_frames = min(num_frames, actual_frames)
    total_samples = num_frames * SPF
    dac_signal = np.zeros(total_samples, dtype=np.float64)

    # DMC playback state
    sample_running = False
    sample_addr = 0xC000
    sample_addr_start = 0xC000
    sample_bytes_remaining = 0
    sample_len_start = 1
    sample_byte = 0
    bit_counter = 0
    rate_cycles = 428
    cycle_accum = 0.0
    dac = 0  # 7-bit DAC value, 0-127
    loop = False

    cycles_per_sample = CPU_HZ_F / SAMPLE_RATE  # ~40.58

    rom_len = len(rom_data)

    def read_rom(addr):
        # NSF maps rom_data starting at load_addr.  Bankswitched NSFs
        # would need bank tracking; fallback: clamp to rom range, return 0
        # if out of bounds.
        offset = addr - load_addr
        if 0 <= offset < rom_len:
            return rom_data[offset]
        return 0

    def fetch_next_byte():
        nonlocal sample_byte, sample_addr, sample_bytes_remaining
        nonlocal sample_running, loop
        if sample_bytes_remaining <= 0:
            if loop:
                sample_addr = sample_addr_start
                sample_bytes_remaining = sample_len_start
            else:
                sample_running = False
                return
        sample_byte = read_rom(sample_addr)
        sample_addr = (sample_addr + 1) & 0xFFFF
        sample_bytes_remaining -= 1

    for frame in range(num_frames):
        s = frame * SPF
        fd = channels["dmc"]["notes"][frame]

        if fd["event_type"] == "dpcm_trigger":
            sample_addr_start = fd["sample_addr"]
            sample_len_start = fd["sample_len"]
            sample_addr = sample_addr_start
            sample_bytes_remaining = sample_len_start
            bit_counter = 0
            loop = bool(fd["loop"])
            rate_cycles = NTSC_DMC_RATES[fd["rate_idx"] & 0x0F]
            sample_running = True
            fetch_next_byte()
        elif fd["event_type"] == "dac_write":
            # $4011 directly written - sets DAC, no DMA started
            dac = fd["dac"] & 0x7F

        # Generate audio samples for this frame
        for i in range(SPF):
            if sample_running:
                cycle_accum += cycles_per_sample
                while cycle_accum >= rate_cycles:
                    cycle_accum -= rate_cycles
                    bit = (sample_byte >> bit_counter) & 1
                    if bit:
                        if dac <= 125:
                            dac += 2
                    else:
                        if dac >= 2:
                            dac -= 2
                    bit_counter += 1
                    if bit_counter >= 8:
                        bit_counter = 0
                        fetch_next_byte()
                        if not sample_running:
                            break
            dac_signal[s + i] = dac

    # Apply TND DAC formula (DMC alone, no triangle/noise)
    # tnd = 159.79 * (dpcm/22638) / (1 + 100*(dpcm/22638))
    w = dac_signal / 22638.0
    nonzero = w > 0
    out = np.zeros_like(dac_signal)
    out[nonzero] = 159.79 * w[nonzero] / (1.0 + 100.0 * w[nonzero])

    # Smooth DAC output through the NES analog LP (~14 kHz).  Without this
    # the DPCM DAC changes are perceived as clicks in a DAW.
    out = apply_nes_analog_lp(out)
    # DC center
    out = dc_block(out)
    if not normalize:
        return out
    pk = np.max(np.abs(out))
    if pk > 0:
        out = out / pk * 0.9
    return (out * 32767).astype(np.int16)


def render_stem(channels, num_frames, keep, normalize=True):
    """Render a single channel's DAC contribution as WAV samples.

    keep: one of "p1", "p2", "tri", "noise"  (use render_dmc_stem for "dmc")
    Returns np.int16 array.
    """
    actual_frames = len(channels["pulse1"]["notes"])
    num_frames = min(num_frames, actual_frames)
    total_samples = num_frames * SPF
    mix = np.zeros(total_samples, dtype=np.float64)
    phase = {"p1": 0.0, "p2": 0.0, "tri": 0.0}

    # NES noise: 15-bit LFSR, shifted at CPU_CYCLES / period_table[period_idx].
    # Output bit = LFSR & 1 (inverted: 0 bit means channel silent that tick).
    # Mode 0: feedback = bit0 XOR bit1 (long sequence, hiss)
    # Mode 1: feedback = bit0 XOR bit6 (short sequence, metallic tonal)
    lfsr = 1
    lfsr_accum = 0.0  # fractional cycle accumulator
    CPU_HZ = 1789773.0
    NOISE_PERIOD = [4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068]

    p_env = {
        "pulse1": {"decay": 15, "divider": 0, "start_flag": False},
        "pulse2": {"decay": 15, "divider": 0, "start_flag": False},
    }
    tri_linear_live = 0
    tri_reload_flag = False

    # Sweep unit state per pulse channel.
    # Hardware sweep clocks at half-frame rate (120 Hz NTSC, 2 ticks/frame).
    # Each tick: decrement divider; if zero AND enabled AND shift>0:
    #   target = current_period + (negate ? -change-1ifP1elseNeg : change)
    #   where change = current_period >> shift.
    #   If target > 0x7FF or current_period < 8: MUTE the channel.
    #   Else: current_period = target, reload divider.
    # Reload divider at end-of-period or on register write (write_mask bit 1).
    p_sweep = {
        "pulse1": {"divider": 0, "muted": False, "current_period": 0},
        "pulse2": {"divider": 0, "muted": False, "current_period": 0},
    }

    for frame in range(num_frames):
        s = frame * SPF

        p1_wave = np.zeros(SPF)
        p2_wave = np.zeros(SPF)
        tri_wave = np.zeros(SPF)
        noise_wave = np.zeros(SPF)

        # HW envelope ticks (always update state even if we won't use it)
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

        # Sweep unit clocks at 120 Hz = 2 ticks per 60 Hz frame
        for ch_name, neg_offset in (("pulse1", 1), ("pulse2", 0)):
            fd = channels[ch_name]["notes"][frame]
            sw = p_sweep[ch_name]
            sw["current_period"] = fd["period"]  # driver may have written new period
            for _ in range(2):  # 2 sweep ticks per 60 Hz frame
                if sw["divider"] == 0:
                    if (fd["sweep_en"] and fd["sweep_shift"] > 0
                            and not sw["muted"]):
                        change = sw["current_period"] >> fd["sweep_shift"]
                        if fd["sweep_negate"]:
                            change = -change - neg_offset  # P1 ones-complement
                        target = sw["current_period"] + change
                        if target > 0x7FF or sw["current_period"] < 8:
                            sw["muted"] = True
                        else:
                            sw["current_period"] = target
                    sw["divider"] = fd["sweep_period"]
                else:
                    sw["divider"] -= 1
            # Re-arm mute when sweep disabled or driver explicitly silences
            if not fd["sweep_en"]:
                sw["muted"] = False

        # Generate the channel we keep
        if keep == "p1":
            fd = channels["pulse1"]["notes"][frame]
            d = fd["duty"]
            # Use sweep-modulated period (driver may have changed it via $4002/$4003,
            # but sweep unit can also shift it for vibrato/glissando effects)
            p = p_sweep["pulse1"]["current_period"]
            effective_vol = fd["env_period"] if fd["const_vol"] else p_env["pulse1"]["decay"]
            # Sweep mute or period-too-low silences the channel
            if p >= 8 and effective_vol > 0 and not p_sweep["pulse1"]["muted"]:
                freq = 1789773 / (16 * (p + 1))
                dv = [0.125, 0.25, 0.5, 0.75][d]
                p1_wave[:] = _bandlimited_pulse(freq, dv, effective_vol, phase, "p1")

        elif keep == "p2":
            fd = channels["pulse2"]["notes"][frame]
            d = fd["duty"]
            p = p_sweep["pulse2"]["current_period"]
            effective_vol = fd["env_period"] if fd["const_vol"] else p_env["pulse2"]["decay"]
            if p >= 8 and effective_vol > 0 and not p_sweep["pulse2"]["muted"]:
                freq = 1789773 / (16 * (p + 1))
                dv = [0.125, 0.25, 0.5, 0.75][d]
                p2_wave[:] = _bandlimited_pulse(freq, dv, effective_vol, phase, "p2")

        elif keep == "tri":
            p = tri_fd["period"]
            if p >= 2 and tri_linear_live > 0:
                freq = 1789773 / (32 * (p + 1))
                pa = (np.arange(SPF) * freq / SAMPLE_RATE + phase["tri"]) % 1.0
                tri_wave[:] = np.where(pa < 0.5, pa * 30, (1.0 - pa) * 30)
                phase["tri"] = (phase["tri"] + SPF * freq / SAMPLE_RATE) % 1.0
            else:
                # Rule 34 (2026-04-18 evening): Gate-off holds last DAC value.
                # NESdev: "If the linear counter or length counter is zero,
                # the sequencer is held at its current position." Hardware
                # DAC keeps outputting that held step's value.  Zeroing the
                # wave here produced a 38%-scale click every 14 Hz in
                # Battletoads (and similarly in any game using triangle
                # staccato gating).  DC blocker will still resolve the held
                # value to silence over ~50 ms.  Phase is NOT advanced while
                # gated off (matches HW sequencer pause).
                pa = phase["tri"]
                held = pa * 30 if pa < 0.5 else (1.0 - pa) * 30
                tri_wave[:] = held

        elif keep == "noise":
            fd = channels["noise"]["notes"][frame]
            nv = fd["vol"]
            nper_idx = fd["period"] & 0x0F
            nmode = fd["mode"]
            # Noise respects $4015 bit 3 (enabled) AND the hardware length
            # counter (see architecture.md Rules 30/32).  Many Nintendo-1st
            # party drivers (SMB/Kondo) write vol once and rely on length
            # counter expiry to silence each drum hit.  Gate on all three.
            length = fd.get("length_counter", 1)  # older captures lack this field
            if nv > 0 and fd["enabled"] and length > 0:
                # NES noise at fast periods (idx 0-4) shifts faster than
                # the audio sample rate, which would alias badly if we
                # just sampled the LFSR at sample-rate ticks. Instead:
                # walk through each audio sample as a 1-unit time window,
                # tracking LFSR shift events within that window, and
                # compute the *time-weighted average* of the LFSR output
                # bit over the window. This is proper band-limited
                # synthesis and matches what the hardware DAC + low-pass
                # filter effectively produces.
                shift_rate = CPU_HZ / NOISE_PERIOD[nper_idx]
                sample_per_shift = SAMPLE_RATE / shift_rate
                current_bit_value = 0.0 if (lfsr & 1) else nv
                for i in range(SPF):
                    time_left = 1.0  # one sample = 1.0 unit of time
                    accum = 0.0
                    while True:
                        time_to_shift = sample_per_shift - lfsr_accum
                        if time_to_shift >= time_left:
                            # No shift this sample - current bit for remaining time
                            accum += current_bit_value * time_left
                            lfsr_accum += time_left
                            break
                        # Shift occurs before sample ends
                        accum += current_bit_value * time_to_shift
                        time_left -= time_to_shift
                        lfsr_accum = 0.0
                        # Clock the LFSR
                        if nmode:
                            fb = (lfsr & 1) ^ ((lfsr >> 6) & 1)
                        else:
                            fb = (lfsr & 1) ^ ((lfsr >> 1) & 1)
                        lfsr = ((lfsr >> 1) | (fb << 14)) & 0x7FFF
                        current_bit_value = 0.0 if (lfsr & 1) else nv
                    noise_wave[i] = accum

        # Non-linear DAC with only this one channel active
        for i in range(SPF):
            mix[s + i] = _apu_nonlinear_mix(
                p1_wave[i], p2_wave[i], tri_wave[i], noise_wave[i]
            )

    # NES analog output LP.  Removes the per-note "click" artifact caused
    # by instantaneous volume / phase-reset steps, and attenuates the
    # harshest aliasing from naive-sampled pulse edges.  Approximates the
    # real hardware's 14 kHz RC filter.
    mix = apply_nes_analog_lp(mix)
    # DC blocker: leaves silent regions at zero.  Mean subtraction would
    # shift silent frames off-zero when the overall signal is asymmetric
    # (drums on a noise stem bias the mean positive, so quiet regions
    # register as negative DC instead of true silence).
    mix = dc_block(mix)
    if not normalize:
        return mix
    pk = np.max(np.abs(mix))
    if pk > 0:
        mix = mix / pk * 0.9
    return (mix * 32767).astype(np.int16)


def write_wav(samples, path):
    with wave.open(str(path), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(samples.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("nsf")
    ap.add_argument("--song", type=int, required=True)
    ap.add_argument("--seconds", type=float, default=90.0)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Guard: NSF track numbers are 1-indexed (see docs/NAMING_POLICY.md
    # invariant #2).  play_song() does its own `-1` for INIT; passing 0
    # here silently renders NSF track 0xFF (invalid).
    if args.song < 1:
        print(f"ERROR: --song {args.song} is invalid; NSF track numbers "
              "are 1-indexed (1 = first song).", file=sys.stderr)
        sys.exit(2)

    frames_target = int(args.seconds * 60)
    print(f"Emulating '{Path(args.nsf).name}' song {args.song} for {frames_target} frames...")
    emu = NsfEmulator(args.nsf)
    if args.song > emu.total_songs:
        print(f"ERROR: --song {args.song} exceeds NSF total songs "
              f"({emu.total_songs}).", file=sys.stderr)
        sys.exit(2)
    # play_song() itself treats song_num as 1-indexed and does the -1
    # internally before the INIT call.  Passing args.song-1 here caused a
    # double-subtract: the first track (song=1) went through as a=-1=0xFF
    # at INIT which most drivers handle as no-op, resulting in empty stems
    # (observed on Metroid Intro: 0.5-10s of near-silence despite 92s M3U
    # duration).  Use args.song directly (1-indexed).
    frames = emu.play_song(args.song, frames_target)
    channels = frames_to_channel_data(frames, getattr(emu, 'expansion_chips', None))
    actual = len(channels['pulse1']['notes'])
    print(f"  captured {actual} frames")

    stems = [("p1", "pulse1.wav"), ("p2", "pulse2.wav"),
             ("tri", "triangle.wav"), ("noise", "noise.wav")]

    # Render each stem as a raw (unnormalized) float array so we can apply
    # ONE shared scale factor across all stems.  Independent normalization
    # per stem made a naturally-quiet noise stem as loud as the pulses when
    # summed in REAPER, producing excess noise in the final mix.
    raw = {}
    for key, _ in stems:
        print(f"  rendering {key} stem...")
        raw[key] = render_stem(channels, frames_target, key, normalize=False)

    # DMC stem (samples + DAC writes) joins the shared scale too
    has_dmc_events = any(
        n["event_type"] != "idle" for n in channels["dmc"]["notes"]
    )
    if has_dmc_events:
        print("  rendering dmc stem (DPCM samples + DAC writes)...")
        raw["dmc"] = render_dmc_stem(
            channels, frames_target, emu.rom_data, emu.load_addr, normalize=False
        )
    else:
        print("  dmc stem: skipped (no DMC events in this song)")

    # Shared scale factor: peak of the summed stems.  When REAPER linearly
    # sums these audio tracks on the master bus, the resulting peak will be
    # ~0.9 (matches render_wav full-mix normalization target).  Per-channel
    # DAC proportions are preserved, so noise stays at its natural level
    # relative to the pulses rather than being independently boosted.
    combined = sum(raw.values())
    peak = float(np.max(np.abs(combined))) if len(combined) else 0.0
    scale = (0.9 / peak) if peak > 0 else 1.0

    stem_files = list(stems)
    if "dmc" in raw:
        stem_files.append(("dmc", "dmc.wav"))
    for key, filename in stem_files:
        samples = (raw[key] * scale * 32767).astype(np.int16)
        out_path = args.out_dir / filename
        write_wav(samples, out_path)
        size_kb = out_path.stat().st_size / 1024
        print(f"    -> {out_path} ({size_kb:.0f} KB)")

    print(f"Stems in {args.out_dir}")


if __name__ == "__main__":
    main()
