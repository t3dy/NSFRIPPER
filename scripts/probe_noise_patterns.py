#!/usr/bin/env python3
"""Analyze noise channel usage patterns across drivers.

The noise channel ($400C-$400F) has:
- $400C: envelope/const_vol/loop + 4-bit volume
- $400E: mode bit (7) + 4-bit period index (bits 0-3)
- $400F: length counter load (bits 3-7) + unused

Noise is universally used for percussion. Key questions:
1. Which period indices (0-15) do drivers pick for drums?
   - Period 0-3: short periods = high-pitched (hi-hat, crash)
   - Period 4-8: mid (snare)
   - Period 9-15: long = low-pitched (kick, rumble)
2. Do drivers use short-mode (tonal/metallic) noise vs long-mode (standard)?
3. How often are new noise "notes" triggered?

Findings feed the drum mapping in build_midi().
"""
import mido
from collections import Counter, defaultdict
from pathlib import Path

OUTPUT_DIR = Path('output')


def decode_apu(data):
    if len(data) < 13 or data[0] != 0x7D or data[1] != 0x02:
        return None
    ch = data[2]
    regs = [(data[3 + i * 2] | (data[4 + i * 2] << 7)) for i in range(4)]
    return ch, regs, data[11], data[12]


def scan_noise(game_dir, max_songs=5):
    midi_dir = game_dir / 'midi'
    if not midi_dir.is_dir():
        return None

    period_hist = Counter()    # noise period index 0-15
    mode_hist = Counter()      # 0=long (hissy), 1=short (tonal)
    volumes = Counter()        # volumes used
    new_hits = 0               # transitions from vol=0 to vol>0
    total_active_frames = 0

    midis = sorted(midi_dir.glob('*.mid'))
    # Skip trivial
    midis = [m for m in midis if m.stat().st_size > 3000][:max_songs]

    for mf in midis:
        try:
            mid = mido.MidiFile(str(mf))
        except Exception:
            continue
        prev_vol = 0
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
                if ch != 3:  # noise
                    continue
                # $400E value = regs[2]
                reg2 = regs[2]
                period_idx = reg2 & 0x0F
                mode = (reg2 >> 7) & 1
                vol = regs[0] & 0x0F

                if vol > 0:
                    total_active_frames += 1
                    volumes[vol] += 1
                    period_hist[period_idx] += 1
                    mode_hist[mode] += 1
                    if prev_vol == 0:
                        new_hits += 1
                prev_vol = vol

    return {
        'period_hist': dict(period_hist),
        'mode_hist': dict(mode_hist),
        'volumes': dict(volumes),
        'new_hits': new_hits,
        'total_active_frames': total_active_frames,
    }


def summarize_periods(ph):
    total = sum(ph.values()) or 1
    # Buckets
    short = sum(v for p, v in ph.items() if p <= 3) / total
    mid = sum(v for p, v in ph.items() if 4 <= p <= 8) / total
    long = sum(v for p, v in ph.items() if p >= 9) / total
    return short, mid, long


def main():
    # Focus on drum-heavy games and drivers we've identified
    candidates = [
        # Capcom late driver
        'Mega_Man_3', 'Mega_Man_4', 'Darkwing_Duck', 'TaleSpin',
        'Little_Mermaid,_The', 'Mighty_Final_Fight',
        # Capcom early
        'Mega_Man_2', 'Bionic_Commando', 'Ghosts_n_Goblins',
        'Commando', 'Section_Z',
        # Konami
        'Castlevania', 'Contra', 'Gradius',
        # Sunsoft
        'Blaster_Master', 'Batman', 'Journey_to_Silius',
        'Gremlins_2_The_New_Batch', 'Festers_Quest',
        # Nintendo
        'Super_Mario_Bros', 'Super_Mario_Bros._2', 'Super_Mario_Bros._3',
        'Legend_of_Zelda,_The', 'Zelda_II___The_Adventure_of_Link',
        'Kirbys_Adventure', 'Metroid', 'Punch_Out!!',
        # Rare
        'Battletoads', 'Wizards_and_Warriors', 'R.C._Pro_Am',
        'Captain_Skyhawk',
        # Square
        '3_D_Battles_of_WorldRunner', 'JJ_Tobidase_Daisakusen_Part_2',
    ]

    print(f'{"Game":<42s} {"Short%":>6s} {"Mid%":>5s} {"Long%":>5s} {"Mode0%":>6s} {"Hits":>5s} {"TopPeriods":>20s}')
    print('-' * 115)

    results = {}
    for slug in candidates:
        gd = OUTPUT_DIR / slug
        if not gd.is_dir():
            continue
        res = scan_noise(gd)
        if not res or res['total_active_frames'] == 0:
            continue

        ph = res['period_hist']
        short, mid, long = summarize_periods(ph)
        total = res['total_active_frames']

        mode0_pct = res['mode_hist'].get(0, 0) / total * 100

        # Top 3 periods
        top = sorted(ph.items(), key=lambda x: -x[1])[:3]
        top_str = ','.join(f'{p}({n * 100 // total}%)' for p, n in top)

        print(f'{slug:<42s} {short * 100:>5.0f}  {mid * 100:>4.0f}  {long * 100:>4.0f}  '
              f'{mode0_pct:>5.0f}  {res["new_hits"]:>5d}  {top_str:>20s}')
        results[slug] = res

    # Cross-game period histogram
    print('\n=== Aggregate noise period usage across tested games ===')
    agg = Counter()
    for r in results.values():
        for p, c in r['period_hist'].items():
            agg[p] += c
    tot = sum(agg.values())
    for p in range(16):
        if agg[p] > 0:
            bar_len = min(60, int(60 * agg[p] / max(agg.values())))
            bar = '#' * bar_len
            print(f'  Period {p:2d}: {agg[p]:6d} ({agg[p] * 100 / tot:4.1f}%) {bar}')


if __name__ == '__main__':
    main()
