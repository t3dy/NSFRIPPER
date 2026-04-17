#!/usr/bin/env python3
"""Measure per-driver note duration distributions.

For each pulse1 note attack, count frames until the next attack
(or until vol=0 for >N frames = end of note). This tells us:
- Staccato drivers: short durations, many short notes
- Legato drivers: long durations, few long notes
- Rhythmic character at the driver level

Also reveals tempo/beat structure when plotted as a histogram.
"""
import mido
from collections import Counter, defaultdict
from pathlib import Path
import statistics

OUTPUT_DIR = Path('output')


def decode_apu(data):
    if len(data) < 13 or data[0] != 0x7D or data[1] != 0x02:
        return None
    ch = data[2]
    regs = [(data[3 + i * 2] | (data[4 + i * 2] << 7)) for i in range(4)]
    return ch, regs, data[11], data[12]


def measure_durations(game_dir, max_songs=5, min_silence=2):
    """Return list of note durations (in frames) for pulse1.

    A note ends when volume stays 0 for at least `min_silence` consecutive
    frames, OR when a phase_reset ($4003 write) happens.
    """
    midi_dir = game_dir / 'midi'
    if not midi_dir.is_dir():
        return None

    durations = []  # frames
    midis = sorted(midi_dir.glob('*.mid'))
    midis = [m for m in midis if m.stat().st_size > 3000][:max_songs]

    for mf in midis:
        try:
            mid = mido.MidiFile(str(mf))
        except Exception:
            continue

        song_frames = []  # list of (vol, phase_reset_bool) per frame
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
                if ch != 0:  # pulse 1 only
                    continue
                vol = regs[0] & 0x0F
                phase_reset = bool(mask & 0x08)
                song_frames.append((vol, phase_reset))

        # Walk the frames to find notes
        note_start = None
        silence_count = 0
        for i, (vol, pr) in enumerate(song_frames):
            if note_start is None:
                # Looking for attack
                if vol > 0:
                    note_start = i
                    silence_count = 0
            else:
                # Inside a note
                if pr and i > note_start:
                    # Phase reset ends the current note and starts a new one
                    durations.append(i - note_start)
                    note_start = i
                    silence_count = 0
                elif vol == 0:
                    silence_count += 1
                    if silence_count >= min_silence:
                        durations.append(i - silence_count + 1 - note_start)
                        note_start = None
                        silence_count = 0
                else:
                    silence_count = 0

    return durations


def summarize(durations, frame_rate=60.0):
    if not durations:
        return None
    # Histogram buckets
    buckets = {
        'staccato (1-3f/17-50ms)': sum(1 for d in durations if 1 <= d <= 3),
        'short (4-7f/67-117ms)': sum(1 for d in durations if 4 <= d <= 7),
        'eighth (8-15f/133-250ms)': sum(1 for d in durations if 8 <= d <= 15),
        'quarter (16-31f/267-517ms)': sum(1 for d in durations if 16 <= d <= 31),
        'half (32-63f/533-1050ms)': sum(1 for d in durations if 32 <= d <= 63),
        'whole (64+f/1067+ms)': sum(1 for d in durations if d >= 64),
    }
    total = len(durations)
    median = statistics.median(durations)
    mean = statistics.mean(durations)
    return {
        'total_notes': total,
        'median_dur': median,
        'mean_dur': mean,
        'buckets': {k: (v, v * 100 / total) for k, v in buckets.items()},
    }


def main():
    games = [
        # Capcom clusters
        ('Capcom late (6C80)', ['Mega_Man_3', 'Mega_Man_4', 'Darkwing_Duck', 'TaleSpin']),
        ('Capcom early', ['Mega_Man_2', 'Bionic_Commando', 'Ghosts_n_Goblins']),
        ('Capcom Jun.A', ['Sweet_Home', 'Marusa_no_Onna']),
        # Konami
        ('Konami CV/Contra', ['Castlevania', 'Contra', 'Gradius']),
        # Sunsoft
        ('Sunsoft', ['Blaster_Master', 'Batman', 'Journey_to_Silius']),
        # Nintendo
        ('Nintendo R&D', ['Super_Mario_Bros', 'Super_Mario_Bros._3',
                          'Legend_of_Zelda,_The', 'Kirbys_Adventure',
                          'Metroid']),
        # Square/Uematsu
        ('Square/Uematsu', ['3_D_Battles_of_WorldRunner', 'JJ_Tobidase_Daisakusen_Part_2',
                            'Final_Fantasy', 'Final_Fantasy_II', 'Final_Fantasy_III']),
        # Rare
        ('Rare', ['Battletoads', 'R.C._Pro_Am', 'Cobra_Triangle',
                  'Wizards_and_Warriors']),
        # Tecmo
        ('Tecmo', ['Ninja_Gaiden', 'Ninja_Gaiden_II___The_Dark_Sword_of_Chaos',
                   'Solomons_Key', 'Tecmo_Bowl', 'Mighty_Bomb_Jack',
                   'Captain_Tsubasa_II_Super_Striker']),
        # Taito
        ('Taito', ['Don_Doko_Don_2', 'Kyattou_Ninden_Teyandee']),
        # Jaleco
        ('Jaleco', ['Bases_Loaded']),
    ]

    print(f'{"Driver family / game":<42s} {"Notes":>6s} {"Med":>4s} {"Mean":>5s} {"Stac%":>5s} {"Short%":>6s} {"8th%":>5s} {"4th%":>5s} {"Half%":>5s}')
    print('-' * 115)

    summaries = defaultdict(list)
    for family, slugs in games:
        family_durs = []
        for slug in slugs:
            gd = OUTPUT_DIR / slug
            if not gd.is_dir():
                continue
            durs = measure_durations(gd)
            if not durs:
                continue
            s = summarize(durs)
            if not s:
                continue
            bs = s['buckets']
            print(f'  {slug:<40s} {s["total_notes"]:>6d} {s["median_dur"]:>4.0f} {s["mean_dur"]:>5.1f} '
                  f'{bs["staccato (1-3f/17-50ms)"][1]:>4.0f}% '
                  f'{bs["short (4-7f/67-117ms)"][1]:>5.0f}% '
                  f'{bs["eighth (8-15f/133-250ms)"][1]:>4.0f}% '
                  f'{bs["quarter (16-31f/267-517ms)"][1]:>4.0f}% '
                  f'{bs["half (32-63f/533-1050ms)"][1]:>4.0f}%')
            family_durs.extend(durs)
        if family_durs:
            s = summarize(family_durs)
            bs = s['buckets']
            print(f'==> {family:<38s} {s["total_notes"]:>6d} {s["median_dur"]:>4.0f} {s["mean_dur"]:>5.1f} '
                  f'{bs["staccato (1-3f/17-50ms)"][1]:>4.0f}% '
                  f'{bs["short (4-7f/67-117ms)"][1]:>5.0f}% '
                  f'{bs["eighth (8-15f/133-250ms)"][1]:>4.0f}% '
                  f'{bs["quarter (16-31f/267-517ms)"][1]:>4.0f}% '
                  f'{bs["half (32-63f/533-1050ms)"][1]:>4.0f}%')
            print()


if __name__ == '__main__':
    main()
