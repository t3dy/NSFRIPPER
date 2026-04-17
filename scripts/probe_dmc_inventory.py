#!/usr/bin/env python3
"""Inventory DPCM samples used by each game.

Reads DMC trigger events from the SysEx stream — each dpcm_trigger
writes $4012 (sample_addr/64) and $4013 (sample_len/16+1). Distinct
(addr, len) pairs = distinct samples in the game's bank.
"""
import mido
from collections import defaultdict
from pathlib import Path

OUTPUT_DIR = Path('output')


def decode_apu_sysex(data):
    if len(data) < 13 or data[0] != 0x7D or data[1] != 0x02:
        return None
    ch = data[2]
    regs = [(data[3+i*2] | (data[4+i*2] << 7)) for i in range(4)]
    enable = data[11]
    write_mask = data[12]
    return ch, regs, enable, write_mask


def scan_game(game_dir, max_songs=None):
    """Return sample inventory as dict: (addr_byte, len_byte) -> frame_count."""
    midi_dir = game_dir / 'midi'
    if not midi_dir.is_dir():
        return {}

    samples = defaultdict(int)       # (addr, len) -> trigger count
    rate_per_sample = defaultdict(list)  # (addr, len) -> list of rate_idx seen

    midis = sorted(midi_dir.glob('*.mid'))
    if max_songs:
        midis = midis[:max_songs]

    for mf in midis:
        try:
            mid = mido.MidiFile(str(mf))
        except Exception:
            continue
        for track in mid.tracks:
            has_sysex = any(m.type == 'sysex' for m in track)
            if not has_sysex:
                continue
            prev_addr = 0
            prev_len = 0
            for msg in track:
                if msg.type != 'sysex':
                    continue
                parsed = decode_apu_sysex(msg.data)
                if not parsed:
                    continue
                ch, regs, enable, mask = parsed
                if ch != 4:  # DMC only
                    continue
                # mask bit 2 = $4012 written, bit 3 = $4013 written
                if not (mask & 0x0C):
                    continue
                rate_idx = regs[0] & 0x0F
                addr = regs[2]    # stored as byte, actual addr = $C000 + addr*64
                length = regs[3]  # actual bytes = length*16 + 1
                key = (addr, length)
                samples[key] += 1
                rate_per_sample[key].append(rate_idx)

    return samples, rate_per_sample


def main():
    # Focus on games with known DMC activity
    dmc_games = [
        'Batman', 'Blaster_Master', 'Journey_to_Silius',
        'Gremlins_2_The_New_Batch', 'Ninja_Gaiden',
        'Ninja_Gaiden_II___The_Dark_Sword_of_Chaos',
        'Ninja_Gaiden_III___The_Ancient_Ship_of_Doom',
        'Super_Mario_Bros._3', 'Contra', 'Kirbys_Adventure',
        'Legend_of_Zelda,_The', 'Metroid', 'Mega_Man_2',
        'Mega_Man_3', 'Mega_Man_4', 'DuckTales_2',
        'Battletoads', 'Wizards_and_Warriors',
        'Castlevania', 'Faxanadu',
    ]

    print(f'{"Game":<42s} {"Samples":>8s} {"Triggers":>9s} {"Rates":>10s}')
    print('-' * 75)

    for slug in dmc_games:
        gd = OUTPUT_DIR / slug
        if not gd.is_dir():
            continue
        samples, rates = scan_game(gd, max_songs=10)
        if not samples:
            continue
        total_triggers = sum(samples.values())
        unique_samples = len(samples)
        all_rates = set()
        for r_list in rates.values():
            all_rates.update(r_list)
        rate_str = ','.join(str(r) for r in sorted(all_rates))
        print(f'{slug:<42s} {unique_samples:>8d} {total_triggers:>9d} {rate_str:>10s}')

    # Detailed view for a couple games
    print('\n\n=== Batman sample inventory ===')
    samples, rates = scan_game(OUTPUT_DIR / 'Batman', max_songs=15)
    for (addr, length), count in sorted(samples.items(), key=lambda x: -x[1])[:15]:
        rom_addr = 0xC000 + addr * 64
        byte_len = length * 16 + 1
        all_rates = set(rates[(addr, length)])
        rate_preview = ','.join(str(r) for r in sorted(all_rates))
        print(f'  addr=${rom_addr:04X} len={byte_len:4d}B triggered {count:4d}x rates={rate_preview}')

    print('\n=== Battletoads sample inventory ===')
    samples, rates = scan_game(OUTPUT_DIR / 'Battletoads', max_songs=15)
    for (addr, length), count in sorted(samples.items(), key=lambda x: -x[1])[:15]:
        rom_addr = 0xC000 + addr * 64
        byte_len = length * 16 + 1
        all_rates = set(rates[(addr, length)])
        rate_preview = ','.join(str(r) for r in sorted(all_rates))
        print(f'  addr=${rom_addr:04X} len={byte_len:4d}B triggered {count:4d}x rates={rate_preview}')


if __name__ == '__main__':
    main()
