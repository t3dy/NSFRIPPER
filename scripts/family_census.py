#!/usr/bin/env python3
"""Fast CC11/CC12 density census across all extracted games.

Computes per-game average CC11/note and CC12/note ratios for the first
song of each game (representative sample), outputs JSON for analysis.
Much faster than the full driver_survey.py which parses every track.

Usage:
    python scripts/family_census.py              # JSON to stdout
    python scripts/family_census.py --all-tracks # analyze every track (slow)
    python scripts/family_census.py --csv        # CSV format
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict

import mido

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"


def analyze_midi(midi_path):
    """Extract CC11/note and CC12/note density from a MIDI file."""
    try:
        mid = mido.MidiFile(str(midi_path))
    except Exception:
        return None

    total_notes = 0
    total_cc11 = 0
    total_cc12 = 0
    channels = set()
    channel_stats = {}

    for i, track in enumerate(mid.tracks):
        notes = 0
        cc11 = 0
        cc12 = 0
        ch = None
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                notes += 1
                ch = msg.channel
            elif msg.type == 'control_change':
                if msg.control == 11:
                    cc11 += 1
                elif msg.control == 12:
                    cc12 += 1
                if ch is None:
                    ch = msg.channel

        if notes > 0:
            total_notes += notes
            total_cc11 += cc11
            total_cc12 += cc12
            if ch is not None:
                channels.add(ch)
                channel_stats[ch] = {
                    'notes': notes,
                    'cc11': cc11,
                    'cc12': cc12,
                    'cc11_per_note': round(cc11 / notes, 2),
                    'cc12_per_note': round(cc12 / notes, 2),
                }

    if total_notes == 0:
        return None

    return {
        'notes': total_notes,
        'cc11': total_cc11,
        'cc12': total_cc12,
        'cc11_per_note': round(total_cc11 / total_notes, 2),
        'cc12_per_note': round(total_cc12 / total_notes, 2),
        'channels': len(channels),
        'channel_stats': channel_stats,
    }


def classify_family(cc11_per_note, cc12_per_note):
    """Classify into revised 4-family model (2026-04-14 census).

    Family 5 (Full Animation) eliminated — zero members in 271-game census.
    Family 1 split into sub-groups 1A (ultra-sparse) and 1B (moderate-sparse).
    CC12 >= 0.7 is the sole axis for Duty Animators (Family 3).
    Games with CC12 0.3-0.7 are flagged as fuzzy-zone.

    Returns: (family_id, family_name, sub_group)
        sub_group is "1A", "1B", or None
    """
    # Duty Animators: defined by CC12, not CC11
    if cc12_per_note >= 0.7:
        return 3, "Duty Animators", None
    # Dense Automators: extreme CC11 density
    if cc11_per_note > 5.6:
        return 4, "Dense Automators", None
    # Active Envelope: regular per-frame volume, static duty
    if cc11_per_note > 2.8:
        return 2, "Active Envelope", None
    # Sparse Envelope: minimal per-frame volume writes
    if cc11_per_note <= 0.5:
        return 1, "Sparse Envelope", "1A"
    return 1, "Sparse Envelope", "1B"


def classify_family_simple(cc11_per_note, cc12_per_note):
    """Return just (family_id, family_name) for backwards compat."""
    fam_id, fam_name, _ = classify_family(cc11_per_note, cc12_per_note)
    return fam_id, fam_name


def is_fuzzy_zone(cc12_per_note):
    """Flag games in the CC12 0.3-0.7 boundary zone for ear-check."""
    return 0.3 <= cc12_per_note < 0.7


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all-tracks', action='store_true',
                        help='Analyze all tracks per game (slower)')
    parser.add_argument('--csv', action='store_true', help='CSV output')
    args = parser.parse_args()

    results = []

    for game_dir in sorted(OUTPUT_DIR.iterdir()):
        if not game_dir.is_dir():
            continue
        midi_dir = game_dir / "midi"
        if not midi_dir.exists():
            continue

        midis = sorted(midi_dir.glob("*.mid"))
        if not midis:
            continue

        if args.all_tracks:
            # Analyze all MIDIs, average the results
            all_notes = 0
            all_cc11 = 0
            all_cc12 = 0
            analyzed = 0
            for m in midis:
                r = analyze_midi(m)
                if r:
                    all_notes += r['notes']
                    all_cc11 += r['cc11']
                    all_cc12 += r['cc12']
                    analyzed += 1
            if all_notes > 0:
                cc11_pn = round(all_cc11 / all_notes, 2)
                cc12_pn = round(all_cc12 / all_notes, 2)
                fam_id, fam_name, sub_group = classify_family(cc11_pn, cc12_pn)
                entry = {
                    'game': game_dir.name,
                    'tracks_analyzed': analyzed,
                    'total_midis': len(midis),
                    'notes': all_notes,
                    'cc11_per_note': cc11_pn,
                    'cc12_per_note': cc12_pn,
                    'family_id': fam_id,
                    'family_name': fam_name,
                }
                if sub_group:
                    entry['sub_group'] = sub_group
                if is_fuzzy_zone(cc12_pn):
                    entry['fuzzy_zone'] = True
                results.append(entry)
        else:
            # Just analyze first MIDI (representative)
            r = analyze_midi(midis[0])
            if r:
                fam_id, fam_name, sub_group = classify_family(
                    r['cc11_per_note'], r['cc12_per_note'])
                entry = {
                    'game': game_dir.name,
                    'total_midis': len(midis),
                    'cc11_per_note': r['cc11_per_note'],
                    'cc12_per_note': r['cc12_per_note'],
                    'family_id': fam_id,
                    'family_name': fam_name,
                    'channels': r['channels'],
                }
                if sub_group:
                    entry['sub_group'] = sub_group
                if is_fuzzy_zone(r['cc12_per_note']):
                    entry['fuzzy_zone'] = True
                results.append(entry)

    if args.csv:
        print("game,total_midis,cc11_per_note,cc12_per_note,family_id,family_name")
        for r in results:
            print(f"{r['game']},{r['total_midis']},{r['cc11_per_note']},"
                  f"{r['cc12_per_note']},{r['family_id']},{r['family_name']}")
    else:
        # Summary statistics
        family_counts = defaultdict(list)
        for r in results:
            family_counts[r['family_id']].append(r)

        summary = {
            'total_games': len(results),
            'family_distribution': {},
            'games': results,
        }
        for fam_id in sorted(family_counts.keys()):
            games = family_counts[fam_id]
            cc11s = [g['cc11_per_note'] for g in games]
            cc12s = [g['cc12_per_note'] for g in games]
            summary['family_distribution'][fam_id] = {
                'name': games[0]['family_name'],
                'count': len(games),
                'cc11_range': [min(cc11s), max(cc11s)],
                'cc12_range': [min(cc12s), max(cc12s)],
                'cc11_mean': round(sum(cc11s) / len(cc11s), 2),
                'cc12_mean': round(sum(cc12s) / len(cc12s), 2),
            }

        json.dump(summary, sys.stdout, indent=2)
        print()


if __name__ == '__main__':
    main()
