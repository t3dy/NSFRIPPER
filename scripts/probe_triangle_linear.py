#!/usr/bin/env python3
"""Triangle linear counter value distributions per driver family.

$4008 = CLLLLLLL
  C (bit 7): control flag. Set = linear counter halted (note sustains).
             Clear = linear counter counts down at 240Hz, triangle gates
             off when it reaches 0.
  L (bits 0-6): linear counter reload value (0-127).

$400B write reloads the linear counter from the stored reload value.
Control flag + reload together define the triangle's "note length budget":
- C=1, L=anything: sustained note, length bounded only by length counter
  (which finding 2 proves is never used — so effectively infinite sustain)
- C=0, L=N: note auto-silences after ~N * (1/240)s ≈ N * 4.17ms

Per driver we measure:
- reload-value histogram across frames where triangle active
- control-bit distribution (halt vs count-down ratio)
- reload-write rate per frame (how often driver retriggers)
- dominant reload value and its standard deviation
"""
import mido
from collections import Counter
from pathlib import Path

OUTPUT_DIR = Path('output')


def decode_apu(data):
    if len(data) < 13 or data[0] != 0x7D or data[1] != 0x02:
        return None
    ch = data[2]
    regs = [(data[3 + i * 2] | (data[4 + i * 2] << 7)) for i in range(4)]
    return ch, regs, data[11], data[12]


def scan_triangle(game_dir, max_songs=5):
    midi_dir = game_dir / 'midi'
    if not midi_dir.is_dir():
        return None

    reload_vals = Counter()
    control_vals = Counter()  # 0 (count-down) vs 1 (halt)
    reload_writes = 0          # frames where $4008 was written (mask bit 0)
    retrigger_writes = 0       # frames where $400B was written (mask bit 3)
    active_frames = 0          # frames where triangle considered active
    total_frames = 0
    reloads_when_active = []   # reload value seen during active frames

    midis = sorted(midi_dir.glob('*.mid'))
    midis = [m for m in midis if m.stat().st_size > 3000][:max_songs]

    for mf in midis:
        try:
            mid = mido.MidiFile(str(mf))
        except Exception:
            continue

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
                if ch != 2:  # triangle
                    continue

                total_frames += 1
                reg0 = regs[0]
                period = regs[2] | ((regs[3] & 0x07) << 8)
                control = (reg0 >> 7) & 1
                reload = reg0 & 0x7F

                reload_vals[reload] += 1
                control_vals[control] += 1
                if mask & 0x01:
                    reload_writes += 1
                if mask & 0x08:
                    retrigger_writes += 1

                # Triangle "active" = period set and reload non-zero
                if period > 8 and reload > 0:
                    active_frames += 1
                    reloads_when_active.append(reload)

    if total_frames == 0:
        return None

    # Dominant reload during active frames
    dominant = 0
    dominant_pct = 0.0
    if reloads_when_active:
        dom_counter = Counter(reloads_when_active)
        dominant, n = dom_counter.most_common(1)[0]
        dominant_pct = n / len(reloads_when_active)

    return {
        'total_frames': total_frames,
        'active_frames': active_frames,
        'reload_writes': reload_writes,
        'retrigger_writes': retrigger_writes,
        'control_halt_pct': control_vals[1] / total_frames,
        'reload_hist': dict(reload_vals),
        'dominant_reload': dominant,
        'dominant_pct': dominant_pct,
        'distinct_reloads': len(set(reloads_when_active)),
    }


# Driver family cohorts — game slugs validated against output/ directory
FAMILIES = {
    'Capcom late 6C80':  ['Mega_Man_3', 'Mega_Man_4', 'Darkwing_Duck', 'TaleSpin',
                          'Little_Mermaid__The', 'Mighty_Final_Fight'],
    'Capcom MM1 era':    ['Mega_Man', 'Mega_Man_1'],
    'Capcom MM2 era':    ['Mega_Man_2', 'Bionic_Commando'],
    'Capcom GnG/other':  ['Ghosts_n_Goblins', 'Gun_Smoke', 'Section_Z'],
    'Capcom Jun.A':      ['Sweet_Home', 'Marusa_no_Onna'],
    'Konami canonical':  ['Castlevania', 'Contra', 'Gradius', 'Castlevania_III'],
    'Konami arcade':     ['Hyper_Sports', 'Road_Fighter', 'Circus_Charlie',
                          'Yie_Ar_Kung_Fu'],
    'Konami Goonies':    ['Goonies_II_The', 'Goonies,_The'],
    'Sunsoft':           ['Blaster_Master', 'Batman', 'Journey_to_Silius',
                          'Gremlins_2', 'Festers_Quest'],
    'Nintendo R&D':      ['Super_Mario_Bros', 'Super_Mario_Bros._3',
                          'Legend_of_Zelda,_The', 'Zelda_II___The_Adventure_of_Link',
                          'Kirbys_Adventure', 'Metroid', 'Punch_Out!!'],
    'Square Uematsu':    ['3_D_Battles_of_WorldRunner', 'JJ_Tobidase_Daisakusen_Part_2',
                          'Final_Fantasy', 'Final_Fantasy_II', 'Final_Fantasy_III'],
    'Rare':              ['Battletoads', 'R.C._Pro_Am', 'Wizards_and_Warriors',
                          'Captain_Skyhawk', 'Cobra_Triangle'],
    'Tecmo':             ['Ninja_Gaiden', 'Ninja_Gaiden_II___The_Dark_Sword_of_Chaos',
                          'Mighty_Bomb_Jack', 'Tecmo_Bowl', 'Solomons_Key'],
    'HW-envelope users': ['Commando', 'Smash_T.V', 'Super_Arabian'],
    'Tengen/3rd-party':  ['After_Burner', 'Alien_Syndrome'],
    'Gimmick (5B)':      ['Gimmick', 'Mr_Gimmick'],
}


def main():
    # Aggregate per family
    print(f"{'Family':<22s} {'Game':<42s} {'ActPct':>6s} {'Halt%':>6s} "
          f"{'Dom':>4s} {'DomPct':>6s} {'#Vals':>5s} {'Rel/F':>5s}")
    print('-' * 110)

    family_reloads = {}  # family -> list of dominant reloads
    family_halts = {}    # family -> list of halt pcts

    for family, slugs in FAMILIES.items():
        family_reloads[family] = []
        family_halts[family] = []
        for slug in slugs:
            gd = OUTPUT_DIR / slug
            if not gd.is_dir():
                continue
            s = scan_triangle(gd)
            if not s or s['active_frames'] < 100:
                continue
            act_pct = s['active_frames'] / s['total_frames']
            rel_per_frame = s['reload_writes'] / s['total_frames']
            print(f"{family:<22s} {slug:<42s} {act_pct*100:>5.0f}% "
                  f"{s['control_halt_pct']*100:>5.0f}% "
                  f"{s['dominant_reload']:>4d} {s['dominant_pct']*100:>5.0f}% "
                  f"{s['distinct_reloads']:>5d} {rel_per_frame:>5.2f}")
            family_reloads[family].append(s['dominant_reload'])
            family_halts[family].append(s['control_halt_pct'])

    # Family summary
    print()
    print('=== Per-family summary ===')
    print(f"{'Family':<22s} {'Games':>5s} {'MedianReload':>12s} {'MedianHalt%':>12s} "
          f"{'ReloadRange':<18s}")
    print('-' * 80)
    for family in FAMILIES:
        vals = family_reloads[family]
        halts = family_halts[family]
        if not vals:
            continue
        import statistics
        med_r = statistics.median(vals)
        med_h = statistics.median(halts) * 100
        lo, hi = min(vals), max(vals)
        print(f"{family:<22s} {len(vals):>5d} {med_r:>12.0f} {med_h:>11.0f}% "
              f"{f'{lo}..{hi}':<18s}")


if __name__ == '__main__':
    main()
