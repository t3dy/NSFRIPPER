#!/usr/bin/env python3
"""Extract per-driver volume envelope shape fingerprints.

For each note attack (vol transition from 0 to non-zero), capture the
next N frames of volume. Average across all attacks to get the driver's
characteristic envelope curve.

Also probes $4017 (frame counter mode) writes — a small but unexplored
area. 4-step vs 5-step mode affects envelope/sweep/length tick rate.
"""
import mido
import sys
from collections import Counter, defaultdict
from pathlib import Path

OUTPUT_DIR = Path('output')
ATTACK_WINDOW = 30  # capture up to 30 frames after each attack (0.5s at 60Hz)


def decode_apu(data):
    if len(data) < 13 or data[0] != 0x7D or data[1] != 0x02:
        return None
    ch = data[2]
    regs = [(data[3 + i * 2] | (data[4 + i * 2] << 7)) for i in range(4)]
    return ch, regs, data[11], data[12]


def scan_envelopes(game_dir, max_songs=5):
    """Extract attack-window envelope profiles from pulse1 frames."""
    midi_dir = game_dir / 'midi'
    if not midi_dir.is_dir():
        return None

    # Collect (attack_frame_idx, [vols for next 30 frames]) per song
    profiles = []  # list of [vols] windows

    midis = sorted(midi_dir.glob('*.mid'))
    midis = [m for m in midis if m.stat().st_size > 3000][:max_songs]

    for mf in midis:
        try:
            mid = mido.MidiFile(str(mf))
        except Exception:
            continue

        # First pass: extract per-frame pulse1 state
        song_frames = []  # list of vol per frame
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
                if ch == 0:  # pulse 1
                    reg0 = regs[0]
                    const_vol = (reg0 >> 4) & 1
                    vol = reg0 & 0x0F
                    song_frames.append((vol, const_vol))

        # Find attack events: vol transitions 0 -> non-zero
        for i in range(1, len(song_frames) - ATTACK_WINDOW):
            prev_vol = song_frames[i - 1][0]
            cur_vol = song_frames[i][0]
            if prev_vol == 0 and cur_vol > 0:
                # Capture window
                window = [song_frames[i + k][0] for k in range(ATTACK_WINDOW)]
                profiles.append(window)

    return profiles


def summarize_envelope(profiles):
    """Produce a representative envelope shape from profile list."""
    if not profiles:
        return None
    # Average at each offset
    avg = [0.0] * ATTACK_WINDOW
    for w in profiles:
        for k, v in enumerate(w):
            avg[k] += v
    avg = [a / len(profiles) for a in avg]
    # Also: peak frame, mean duration (frames until vol<=1)
    peak_idx = max(range(ATTACK_WINDOW), key=lambda i: avg[i])
    # Sustain-level estimate: average of frames 15-29
    tail = sum(avg[15:30]) / 15
    return {
        'avg_curve': avg,
        'peak_idx': peak_idx,
        'peak_vol': avg[peak_idx],
        'tail_vol': tail,
        'num_attacks': len(profiles),
    }


def main():
    # Mix of games across driver families
    games = [
        # Capcom late 6C80
        'Mega_Man_3', 'Mega_Man_4', 'Darkwing_Duck', 'TaleSpin',
        # Capcom early variants
        'Mega_Man_2', 'Bionic_Commando', 'Ghosts_n_Goblins',
        # Konami
        'Castlevania', 'Contra', 'Gradius',
        # Sunsoft
        'Blaster_Master', 'Batman', 'Journey_to_Silius',
        # Nintendo R&D
        'Super_Mario_Bros', 'Super_Mario_Bros._3',
        'Legend_of_Zelda,_The', 'Zelda_II___The_Adventure_of_Link',
        'Kirbys_Adventure', 'Metroid',
        # Rare
        'Battletoads', 'R.C._Pro_Am',
        # Square/Uematsu
        '3_D_Battles_of_WorldRunner',
        # HW envelope dominant games
        'Commando', 'Ghosts_n_Goblins', 'Smash_T.V',
    ]

    print(f'{"Game":<42s} {"#Att":>5s} {"Peak":>5s} {"Tail":>5s} {"Curve (avg volume per frame)":<s}')
    print('-' * 120)

    summaries = {}
    for slug in games:
        gd = OUTPUT_DIR / slug
        if not gd.is_dir():
            continue
        profiles = scan_envelopes(gd)
        if not profiles:
            continue
        s = summarize_envelope(profiles)
        summaries[slug] = s
        # Compact curve view: show first 15 frames
        curve_str = ''
        for k in range(15):
            v = int(s['avg_curve'][k])
            curve_str += f'{v:2d} '
        print(f'{slug:<42s} {s["num_attacks"]:>5d} {s["peak_vol"]:>5.1f} {s["tail_vol"]:>5.1f} {curve_str}')


if __name__ == '__main__':
    main()
