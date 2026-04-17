#!/usr/bin/env python3
"""Probe Gimmick!'s Sunsoft 5B (YM2149) register usage.

5B uses a latched-register protocol:
- Write register address to $C000
- Write register data to $E000

Registers (AY-3-8910/YM2149 compatible):
  $00: Ch A fine tone period
  $01: Ch A coarse tone period (4 bits)
  $02: Ch B fine
  $03: Ch B coarse
  $04: Ch C fine
  $05: Ch C coarse
  $06: Noise period (5 bits)
  $07: Mixer control — bits 0-2 = tone disable A/B/C, bits 3-5 = noise disable
  $08: Ch A volume (0-15) + envelope flag (bit 4)
  $09: Ch B volume + envelope flag
  $0A: Ch C volume + envelope flag
  $0B: Envelope fine period
  $0C: Envelope coarse period (8 bits)
  $0D: Envelope shape (4 bits, 16 shapes)

Key questions:
1. Does Gimmick! use the hardware envelope? If so, which shapes?
2. Does it use noise? On which channels?
3. Which volume mode: direct (bit 4=0) or envelope (bit 4=1)?
4. How often is each register written per frame?

This is the first look at any 5B game in the library.
"""
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, '.')
from scripts.nsf_to_reaper import NsfEmulator

REPO = Path('.')


def main():
    nsf_path = None
    for f in (REPO / 'output' / 'Gimmick' / 'nsf').glob('*.nsf'):
        nsf_path = f
        break
    if not nsf_path:
        print("Gimmick! NSF not found")
        return

    emu = NsfEmulator(nsf_path)
    print(f'Gimmick! has {emu.total_songs} songs')
    print(f'Expansion byte: 0x{emu.expansion_flags:02X} (has_5b={emu.has_5b})')

    # Play song 3 ("Good Weather") for 1800 frames
    frames = emu.play_song(3, 1800)

    # 5B uses latched-register protocol. We need to track the sequence:
    # write addr to $C000, then data to $E000 = one register write to
    # register_addr := last_C000_value
    reg_state = [0] * 16  # 16 possible 5B registers
    reg_write_counts = Counter()  # reg# -> number of times written
    reg_value_distributions = {i: Counter() for i in range(16)}

    c000_total = 0
    e000_total = 0
    last_addr = None

    for frame_idx, frame in enumerate(frames):
        for reg, val in frame['writes']:
            if reg == 0xC000:
                last_addr = val & 0x0F  # only low 4 bits matter for 5B (16 regs)
                c000_total += 1
            elif reg == 0xE000:
                e000_total += 1
                if last_addr is not None and last_addr < 16:
                    reg_state[last_addr] = val
                    reg_write_counts[last_addr] += 1
                    reg_value_distributions[last_addr][val] += 1

    print(f'\nRaw stats:')
    print(f'  $C000 writes (addr latch): {c000_total}')
    print(f'  $E000 writes (data): {e000_total}')
    print(f'  Frames: {len(frames)}\n')

    # Register-level analysis
    REG_NAMES = {
        0: 'ChA fine tone', 1: 'ChA coarse tone',
        2: 'ChB fine tone', 3: 'ChB coarse tone',
        4: 'ChC fine tone', 5: 'ChC coarse tone',
        6: 'Noise period',
        7: 'Mixer control',
        8: 'ChA vol+env', 9: 'ChB vol+env', 10: 'ChC vol+env',
        11: 'Env fine', 12: 'Env coarse', 13: 'Env shape',
        14: 'IO Port A (unused)', 15: 'IO Port B (unused)',
    }

    print('Register write frequency (song 3):')
    for reg in range(16):
        count = reg_write_counts[reg]
        if count == 0:
            continue
        per_frame = count / len(frames)
        top_vals = reg_value_distributions[reg].most_common(3)
        top_str = ', '.join(f'${v:02X}({n})' for v, n in top_vals)
        print(f'  R{reg:2d} ({REG_NAMES[reg]:<18s}): {count:4d} writes ({per_frame:4.2f}/frame) top: {top_str}')

    # Analyze what each channel is doing
    print('\n=== Channel analysis ===')

    # Volume register R8/R9/R10: low 4 bits = volume (0-15), bit 4 = envelope flag
    for ch_idx, reg in enumerate([8, 9, 10]):
        ch_letter = chr(ord('A') + ch_idx)
        vals = reg_value_distributions[reg]
        env_frames = sum(v for val, v in vals.items() if val & 0x10)
        direct_frames = sum(v for val, v in vals.items() if not (val & 0x10))
        total = env_frames + direct_frames
        if total == 0:
            print(f'Channel {ch_letter}: silent')
            continue
        env_pct = env_frames * 100 / total
        # Volume distribution (direct mode only, bit 4=0)
        direct_vols = Counter()
        for val, v in vals.items():
            if not (val & 0x10):
                direct_vols[val & 0x0F] += v
        top_vols = direct_vols.most_common(5)
        print(f'Channel {ch_letter}: {total} vol writes — {env_pct:.0f}% envelope-mode, {100-env_pct:.0f}% direct')
        if top_vols:
            vol_str = ', '.join(f'vol{v}({n})' for v, n in top_vols)
            print(f'  Direct-mode volumes: {vol_str}')

    # Mixer register (R7): bit 0-2 tone enable (0=enabled), bit 3-5 noise enable
    print('\n=== Mixer ($07) analysis ===')
    mixer_vals = reg_value_distributions[7]
    for val, count in sorted(mixer_vals.items(), key=lambda x: -x[1])[:5]:
        # Bit 0=tone A disable, 1=tone B, 2=tone C, 3=noise A, 4=noise B, 5=noise C
        ta = 'OFF' if (val >> 0) & 1 else 'on'
        tb = 'OFF' if (val >> 1) & 1 else 'on'
        tc = 'OFF' if (val >> 2) & 1 else 'on'
        na = 'OFF' if (val >> 3) & 1 else 'on'
        nb = 'OFF' if (val >> 4) & 1 else 'on'
        nc = 'OFF' if (val >> 5) & 1 else 'on'
        print(f'  ${val:02X}: {count} writes — tone A={ta} B={tb} C={tc}, noise A={na} B={nb} C={nc}')

    # Envelope shape (R13)
    print('\n=== Envelope shape ($0D) usage ===')
    shape_vals = reg_value_distributions[13]
    SHAPE_NAMES = {
        0x00: 'decay-single', 0x01: 'decay-single', 0x02: 'decay-single', 0x03: 'decay-single',
        0x04: 'attack-single', 0x05: 'attack-single', 0x06: 'attack-single', 0x07: 'attack-single',
        0x08: 'decay-loop (repeating saw-down)',
        0x09: 'decay-single then silent',
        0x0A: 'decay-attack loop (triangle)',
        0x0B: 'decay-single then hold high',
        0x0C: 'attack-loop (repeating saw-up)',
        0x0D: 'attack-single then hold high',
        0x0E: 'attack-decay loop (inverted triangle)',
        0x0F: 'attack-single then silent',
    }
    for val, count in sorted(shape_vals.items(), key=lambda x: -x[1]):
        name = SHAPE_NAMES.get(val & 0x0F, f'raw {val:02X}')
        print(f'  ${val:02X}: {count} writes — {name}')


if __name__ == '__main__':
    main()
