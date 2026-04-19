#!/usr/bin/env python3
"""Wizards & Warriors: measure pipeline flattening across all dimensions.

Context (see extraction/analysis/reconciled/wizards_and_warriors_*.md):
The user reports missing note boundaries + timbres on latest W&W output.
Earlier research sessions identified two hardware-state misinterpretations
in the extraction pipeline (nsf_to_reaper.py lines 360, 378, 393):

1. PULSE: writes env_period field into "vol" when const_vol=0
   - $4000=0x45 → const_vol=0, env_period=5
   - Pipeline emits CC11 at level 5 (flattened, steady)
   - Truth: hardware envelope starts at 15 and decays using period=5
   - Symptom: no percussive "tink"; pulses sound like static blobs

2. TRIANGLE: writes linear_reload into "linear" as if it were live state
   - $4008=0x81 → control=1, reload=1
   - Pipeline reads "linear=1, gate alive" and sustains forever
   - Truth: reload is loaded into an internal counter that decrements
     at 240Hz when control=0
   - Symptom: bass over-sustains

This probe quantifies the impact across all 16 W&W songs + identifies
other library-wide games with the same hidden flattening.

Runs:
1. Per-song W&W: const_vol distribution, env_period mix, retrigger rate,
   triangle control/reload distribution
2. Aggregate: how many frames of W&W are affected
3. Library-wide: rank games by "flattening exposure"
"""
import mido
from collections import Counter
from pathlib import Path
import json
import sys

OUTPUT_DIR = Path('output')


def decode_apu(data):
    if len(data) < 13 or data[0] != 0x7D or data[1] != 0x02:
        return None
    ch = data[2]
    regs = [(data[3 + i * 2] | (data[4 + i * 2] << 7)) for i in range(4)]
    return ch, regs, data[11], data[12]


def simulate_hw_envelope(frames_p1):
    """Simulate the APU hardware envelope for pulse1.

    Each frame is (reg0_value, phase_reset_bool).
    Returns list of effective volumes per frame.

    Hardware behavior (from NESDev):
    - const_vol=1: envelope disabled, output = env_period nibble
    - const_vol=0: envelope divider counts down from env_period+1.
      When it hits 0, the envelope decay level decrements (from 15→0).
      Phase reset ($4003 write) restarts: divider reloaded, level=15.
      If env_loop=1 the level wraps 0→15 instead of staying at 0.
    - The envelope clocks at quarter-frame (240Hz). We approximate at
      60Hz frame rate = 4 quarter-frames per frame.
    """
    out = []
    env_level = 15
    env_divider = 0
    for (reg0, phase_reset) in frames_p1:
        const_vol = (reg0 >> 4) & 1
        env_loop = (reg0 >> 5) & 1
        env_period = reg0 & 0x0F
        if phase_reset:
            env_level = 15
            env_divider = env_period
        if const_vol:
            effective = env_period
        else:
            # Tick envelope 4 times per frame (240Hz quarter-frames)
            for _ in range(4):
                if env_divider == 0:
                    if env_level > 0:
                        env_level -= 1
                    elif env_loop:
                        env_level = 15
                    env_divider = env_period
                else:
                    env_divider -= 1
            effective = env_level
        out.append(effective)
    return out


def simulate_tri_linear(frames_tri):
    """Simulate the triangle linear counter gate.

    Each frame is (reg0_value, phase_reset_bool).  (phase_reset = $400B write)
    Returns list of booleans: True if gate open this frame.

    Hardware behavior:
    - On $400B write: internal reload_flag set, length counter reloads.
    - Linear counter loads from reload value when reload_flag set; reload_flag
      cleared by quarter-frame clock UNLESS control bit is set.
    - If control bit (bit 7) = 1: reload_flag stays set; linear counter keeps
      reloading to reload value every quarter-frame = effectively halted at
      reload value (non-zero reload = gate always open).
    - If control bit = 0: linear counter counts down at 240Hz; gate closes
      when it reaches 0.
    - Triangle produces output only when linear > 0 AND length > 0 AND period > 1.
    """
    out = []
    lin_counter = 0
    reload_flag = False
    for (reg0, phase_reset) in frames_tri:
        control = (reg0 >> 7) & 1
        reload = reg0 & 0x7F
        if phase_reset:
            reload_flag = True
        # 4 quarter-frames per frame
        for _ in range(4):
            if reload_flag:
                lin_counter = reload
            elif lin_counter > 0:
                lin_counter -= 1
            # Control bit clears reload_flag (unless control=1 keeps it latched)
            if control == 0:
                reload_flag = False
        out.append(lin_counter > 0)
    return out


def measure_song(midi_path):
    """Extract per-frame pulse1/pulse2/triangle state + derive mismatches."""
    try:
        mid = mido.MidiFile(str(midi_path))
    except Exception:
        return None

    p1_frames = []  # (reg0, phase_reset)
    p2_frames = []
    tri_frames = []
    for track in mid.tracks:
        if not any(m.type == 'sysex' for m in track):
            continue
        for msg in track:
            if msg.type != 'sysex':
                continue
            parsed = decode_apu(msg.data)
            if not parsed:
                continue
            ch, regs, en, mask = parsed
            phase_reset = bool(mask & 0x08)
            if ch == 0:
                p1_frames.append((regs[0], phase_reset))
            elif ch == 1:
                p2_frames.append((regs[0], phase_reset))
            elif ch == 2:
                tri_frames.append((regs[0], phase_reset))

    if not p1_frames:
        return None

    # --- Pulse stats ---
    p1_const_vol_frames = sum(1 for (r0, _) in p1_frames if (r0 >> 4) & 1)
    p1_hw_envelope_frames = len(p1_frames) - p1_const_vol_frames
    p1_env_periods = Counter(r0 & 0x0F for (r0, _) in p1_frames if not ((r0 >> 4) & 1))

    p2_const_vol_frames = sum(1 for (r0, _) in p2_frames if (r0 >> 4) & 1)
    p2_hw_envelope_frames = len(p2_frames) - p2_const_vol_frames

    # Simulate hidden envelope for pulse1 and diff vs current flattened output
    truth_p1 = simulate_hw_envelope(p1_frames)
    flat_p1 = [r0 & 0x0F for (r0, _) in p1_frames]  # what pipeline emits
    p1_mismatch = sum(1 for a, b in zip(truth_p1, flat_p1) if a != b)
    p1_peak_loss = sum(max(0, a - b) for a, b in zip(truth_p1, flat_p1))  # underplay
    p1_attack_loss = sum(1 for a, b in zip(truth_p1, flat_p1) if a >= 12 and b < 8)

    # --- Triangle stats ---
    tri_control_halt = sum(1 for (r0, _) in tri_frames if (r0 >> 7) & 1)
    tri_reload_dist = Counter(r0 & 0x7F for (r0, _) in tri_frames)

    # Simulate triangle gate and diff vs pipeline-alive interpretation
    truth_tri = simulate_tri_linear(tri_frames)
    flat_tri = [(r0 & 0x7F) > 0 for (r0, _) in tri_frames]  # pipeline: alive if reload>0
    tri_overhang = sum(1 for a, b in zip(truth_tri, flat_tri) if not a and b)

    return {
        'song': midi_path.stem,
        'frames': len(p1_frames),
        'p1_hw_env_pct': p1_hw_envelope_frames / max(1, len(p1_frames)),
        'p2_hw_env_pct': p2_hw_envelope_frames / max(1, len(p2_frames)),
        'p1_env_periods_top3': p1_env_periods.most_common(3),
        'p1_mismatched_frames': p1_mismatch,
        'p1_attack_loss_frames': p1_attack_loss,
        'p1_peak_loss_total': p1_peak_loss,
        'tri_control_halt_pct': tri_control_halt / max(1, len(tri_frames)),
        'tri_reload_top3': tri_reload_dist.most_common(3),
        'tri_overhang_frames': tri_overhang,
        'tri_frames': len(tri_frames),
    }


def scan_ww():
    """Per-song W&W analysis."""
    ww_dir = OUTPUT_DIR / 'Wizards_and_Warriors' / 'midi'
    if not ww_dir.exists():
        print(f"W&W not found at {ww_dir}", file=sys.stderr)
        return []
    results = []
    for mf in sorted(ww_dir.glob('*.mid')):
        r = measure_song(mf)
        if r:
            results.append(r)
    return results


def library_exposure():
    """Scan entire library for games with high HW-envelope usage."""
    rows = []
    for gd in sorted(OUTPUT_DIR.iterdir()):
        if not gd.is_dir() or not (gd / 'midi').is_dir():
            continue
        midis = sorted((gd / 'midi').glob('*.mid'))
        midis = [m for m in midis if m.stat().st_size > 3000][:3]  # sample 3 songs
        if not midis:
            continue
        total_p1 = 0
        hw_p1 = 0
        total_tri = 0
        halt_tri = 0
        for mf in midis:
            r = measure_song(mf)
            if not r:
                continue
            total_p1 += r['frames']
            hw_p1 += int(r['p1_hw_env_pct'] * r['frames'])
            total_tri += r['tri_frames']
            halt_tri += int(r['tri_control_halt_pct'] * r['tri_frames'])
        if total_p1 >= 1000:
            rows.append({
                'game': gd.name,
                'p1_hw_env_pct': hw_p1 / total_p1,
                'tri_halt_pct': halt_tri / max(1, total_tri),
                'frames': total_p1,
            })
    return rows


def main():
    print("=" * 92)
    print("Wizards & Warriors flattening analysis")
    print("=" * 92)
    results = scan_ww()
    if not results:
        print("No data.")
        return

    print(f"\n{'Song':<55s} {'P1HW%':>6s} {'P2HW%':>6s} {'P1Mism':>7s} "
          f"{'AtkLos':>6s} {'TriHalt%':>9s} {'TriOver':>7s}")
    print('-' * 100)
    total_frames = 0
    total_p1_mismatch = 0
    total_attack_loss = 0
    total_tri_overhang = 0
    total_tri_frames = 0
    for r in results:
        print(f"{r['song']:<55s} "
              f"{r['p1_hw_env_pct']*100:>5.0f}% "
              f"{r['p2_hw_env_pct']*100:>5.0f}% "
              f"{r['p1_mismatched_frames']:>7d} "
              f"{r['p1_attack_loss_frames']:>6d} "
              f"{r['tri_control_halt_pct']*100:>8.0f}% "
              f"{r['tri_overhang_frames']:>7d}")
        total_frames += r['frames']
        total_p1_mismatch += r['p1_mismatched_frames']
        total_attack_loss += r['p1_attack_loss_frames']
        total_tri_overhang += r['tri_overhang_frames']
        total_tri_frames += r['tri_frames']

    print('-' * 100)
    print(f"TOTAL frames: {total_frames}, pulse1 flattened frames: "
          f"{total_p1_mismatch} ({100*total_p1_mismatch/max(1,total_frames):.1f}%)")
    print(f"  Attack frames with wrong (too-quiet) volume: {total_attack_loss} "
          f"({100*total_attack_loss/max(1,total_frames):.1f}%)")
    print(f"Triangle overhang frames (pipeline alive, real gate closed): "
          f"{total_tri_overhang} ({100*total_tri_overhang/max(1,total_tri_frames):.1f}%)")

    # Env period distribution across all songs
    print("\n=== Pulse1 env_period distribution when const_vol=0 (W&W) ===")
    all_periods = Counter()
    for r in results:
        for period, count in r['p1_env_periods_top3']:
            all_periods[period] += count
    for period, count in all_periods.most_common():
        print(f"  period={period:2d}: {count} frames "
              f"(decay time ~{(period+1)*15*4.17:.0f}ms from vol 15 to 0)")

    # Library-wide exposure
    print("\n" + "=" * 92)
    print("Library-wide HW envelope + triangle-halt exposure (games that share W&W's bug)")
    print("=" * 92)
    rows = library_exposure()
    # Top games by combined exposure (HW envelope + triangle halted)
    rows.sort(key=lambda r: -(r['p1_hw_env_pct'] * 0.6 + r['tri_halt_pct'] * 0.4))
    print(f"\n{'Game':<52s} {'P1HWEnv%':>9s} {'TriHalt%':>9s} {'Frames':>8s}")
    print('-' * 85)
    for r in rows[:30]:
        if r['p1_hw_env_pct'] < 0.15 and r['tri_halt_pct'] < 0.5:
            continue
        print(f"{r['game']:<52s} {r['p1_hw_env_pct']*100:>8.0f}% "
              f"{r['tri_halt_pct']*100:>8.0f}% {r['frames']:>8d}")


if __name__ == '__main__':
    main()
