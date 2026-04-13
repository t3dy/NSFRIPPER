#!/usr/bin/env python3
"""Survey NES music driver characteristics across all extracted games.

Analyzes MIDI output to build a comparative database of how different
games encode their music. Reveals driver families, envelope styles,
channel usage patterns, and instrumentation approaches.

Usage:
    python scripts/driver_survey.py                    # survey all games
    python scripts/driver_survey.py --game DuckTales   # single game detail
    python scripts/driver_survey.py --report           # generate markdown report
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import mido

REPO_ROOT = Path(__file__).resolve().parent.parent


def analyze_track(track):
    """Extract characteristics from a single MIDI track."""
    notes = []
    cc11_events = []  # volume
    cc12_events = []  # duty
    current_time = 0

    for msg in track:
        current_time += msg.time
        if msg.type == 'note_on' and msg.velocity > 0:
            notes.append({'time': current_time, 'note': msg.note, 'vel': msg.velocity})
        elif msg.type == 'control_change':
            if msg.control == 11:
                cc11_events.append({'time': current_time, 'value': msg.value})
            elif msg.control == 12:
                cc12_events.append({'time': current_time, 'value': msg.value})

    if not notes:
        return None

    # Note statistics
    pitches = [n['note'] for n in notes]
    velocities = [n['vel'] for n in notes]

    # Duration between consecutive notes (in ticks)
    durations = []
    for i in range(1, len(notes)):
        dur = notes[i]['time'] - notes[i-1]['time']
        if dur > 0:
            durations.append(dur)

    # CC density: how many CC events per note
    cc11_per_note = len(cc11_events) / len(notes) if notes else 0
    cc12_per_note = len(cc12_events) / len(notes) if notes else 0

    # Duty cycle distribution
    duty_values = Counter(e['value'] for e in cc12_events)
    # Map to NES duty: 0-31=12.5%, 32-63=25%, 64-95=50%, 96-127=75%
    duty_dist = {0: 0, 1: 0, 2: 0, 3: 0}
    for val, count in duty_values.items():
        duty = min(val // 32, 3)
        duty_dist[duty] += count

    # Volume envelope shape: look at CC11 values right after note attacks
    # Group CC11 values by proximity to note attacks
    envelope_shapes = []
    for note in notes[:20]:  # sample first 20 notes
        # Find CC11 events within 128 ticks of this note
        nearby_cc = [e['value'] for e in cc11_events
                     if 0 <= e['time'] - note['time'] <= 128]
        if nearby_cc:
            envelope_shapes.append(nearby_cc)

    # Classify envelope type
    if not cc11_events:
        env_type = "none"
    elif cc11_per_note < 1.5:
        env_type = "sparse"  # ≤1 CC per note — simple on/off
    elif cc11_per_note < 3:
        env_type = "moderate"  # 2-3 CCs per note — basic envelope
    elif cc11_per_note < 6:
        env_type = "detailed"  # 4-6 CCs per note — per-frame updates
    else:
        env_type = "dense"  # 6+ CCs per note — heavy automation

    # Volume range
    cc11_vals = [e['value'] for e in cc11_events]
    vol_range = (min(cc11_vals), max(cc11_vals)) if cc11_vals else (0, 0)

    return {
        'notes': len(notes),
        'pitch_range': (min(pitches), max(pitches)),
        'pitch_mean': sum(pitches) / len(pitches),
        'vel_range': (min(velocities), max(velocities)),
        'duration_median': sorted(durations)[len(durations)//2] if durations else 0,
        'duration_min': min(durations) if durations else 0,
        'cc11_count': len(cc11_events),
        'cc11_per_note': round(cc11_per_note, 1),
        'cc12_count': len(cc12_events),
        'cc12_per_note': round(cc12_per_note, 1),
        'duty_dist': duty_dist,
        'envelope_type': env_type,
        'vol_range': vol_range,
    }


def analyze_song(midi_path):
    """Analyze a complete MIDI file (all 4 channels)."""
    try:
        mid = mido.MidiFile(str(midi_path))
    except Exception:
        return None

    channels = {}
    channel_names = {
        'Square 1': 'pulse1', 'Square 2': 'pulse2',
        'Triangle': 'triangle', 'Noise': 'noise',
        'lead': 'pulse1', 'harmony': 'pulse2', 'bass': 'triangle', 'drums': 'noise'
    }

    for track in mid.tracks:
        name = track.name if hasattr(track, 'name') and track.name else ''
        ch_key = None
        for keyword, key in channel_names.items():
            if keyword.lower() in name.lower():
                ch_key = key
                break
        if not ch_key:
            continue

        stats = analyze_track(track)
        if stats:
            channels[ch_key] = stats

    if not channels:
        return None

    total_notes = sum(ch.get('notes', 0) for ch in channels.values())

    return {
        'channels': channels,
        'total_notes': total_notes,
        'active_channels': list(channels.keys()),
        'has_noise': 'noise' in channels,
    }


def analyze_game(game_slug):
    """Analyze all songs for a game, return aggregate driver profile."""
    midi_dir = REPO_ROOT / "output" / game_slug / "midi"
    nsf_dir = REPO_ROOT / "output" / game_slug / "nsf"

    if not midi_dir.exists():
        return None

    midis = sorted(midi_dir.glob("*.mid"))
    if not midis:
        return None

    # NSF metadata
    nsf_info = {}
    nsfs = list(nsf_dir.glob("*.nsf")) if nsf_dir.exists() else []
    if nsfs:
        with open(nsfs[0], 'rb') as f:
            h = f.read(128)
            nsf_info = {
                'total_songs': h[6],
                'title': h[14:46].decode('ascii', errors='replace').rstrip('\x00'),
                'artist': h[46:78].decode('ascii', errors='replace').rstrip('\x00'),
                'load_addr': f"${h[8] | h[9] << 8:04X}",
                'init_addr': f"${h[10] | h[11] << 8:04X}",
                'play_addr': f"${h[12] | h[13] << 8:04X}",
                'uses_bankswitch': any(h[0x70:0x78]),
            }

    songs = []
    for midi_path in midis:
        song = analyze_song(midi_path)
        if song:
            songs.append(song)

    if not songs:
        return None

    # Aggregate across all songs
    all_env_types = defaultdict(int)
    all_cc11_rates = []
    all_cc12_rates = []
    all_duty_dists = {0: 0, 1: 0, 2: 0, 3: 0}
    channel_usage = Counter()
    noise_count = 0
    total_notes = 0

    for song in songs:
        total_notes += song['total_notes']
        for ch_name in song['active_channels']:
            channel_usage[ch_name] += 1
        if song['has_noise']:
            noise_count += 1

        for ch_name, ch_stats in song['channels'].items():
            if ch_name in ('pulse1', 'pulse2'):
                all_env_types[ch_stats['envelope_type']] += 1
                all_cc11_rates.append(ch_stats['cc11_per_note'])
                all_cc12_rates.append(ch_stats['cc12_per_note'])
                for duty, count in ch_stats['duty_dist'].items():
                    all_duty_dists[duty] += count

    # Dominant envelope type
    dominant_env = max(all_env_types, key=all_env_types.get) if all_env_types else "unknown"

    # Average CC rates
    avg_cc11 = sum(all_cc11_rates) / len(all_cc11_rates) if all_cc11_rates else 0
    avg_cc12 = sum(all_cc12_rates) / len(all_cc12_rates) if all_cc12_rates else 0

    # Dominant duty cycle
    dominant_duty = max(all_duty_dists, key=all_duty_dists.get) if any(all_duty_dists.values()) else -1
    duty_names = {0: "12.5%", 1: "25%", 2: "50%", 3: "75%"}

    return {
        'game': game_slug,
        'songs_extracted': len(midis),
        'songs_with_audio': len(songs),
        'total_notes': total_notes,
        'nsf': nsf_info,
        'driver_profile': {
            'envelope_type': dominant_env,
            'avg_cc11_per_note': round(avg_cc11, 1),
            'avg_cc12_per_note': round(avg_cc12, 1),
            'dominant_duty': duty_names.get(dominant_duty, "none"),
            'duty_distribution': {duty_names[k]: v for k, v in all_duty_dists.items()},
            'uses_noise': noise_count > 0,
            'noise_pct': round(100 * noise_count / len(songs), 0) if songs else 0,
            'channel_usage': dict(channel_usage),
        },
    }


def classify_driver_family(profile):
    """Classify a game into a driver family based on its characteristics."""
    dp = profile['driver_profile']
    env = dp['envelope_type']
    cc11 = dp['avg_cc11_per_note']
    cc12 = dp['avg_cc12_per_note']

    if env == 'dense' and cc12 > 1.0:
        return "Konami-style (per-frame volume + duty animation)"
    elif env == 'detailed' and cc12 > 0.5:
        return "Capcom-style (detailed envelopes, moderate duty switching)"
    elif env == 'detailed' and cc12 <= 0.5:
        return "Sunsoft-style (detailed volume, static duty)"
    elif env == 'moderate':
        return "Standard (basic envelope shaping)"
    elif env == 'sparse':
        return "Minimal (simple on/off, little automation)"
    elif env == 'none':
        return "Raw (no CC automation — velocity only)"
    else:
        return "Unclassified"


def generate_report(profiles):
    """Generate a markdown report comparing all games."""
    lines = ["# NES Driver Survey Report", "",
             f"**{len(profiles)} games analyzed**", ""]

    # Sort by driver family
    families = defaultdict(list)
    for p in profiles:
        family = classify_driver_family(p)
        families[family].append(p)

    lines.append("## Driver Families\n")
    for family in sorted(families, key=lambda f: -len(families[f])):
        games = families[family]
        lines.append(f"### {family} ({len(games)} games)\n")
        lines.append("| Game | Songs | Notes | CC11/note | CC12/note | Duty | Noise |")
        lines.append("|------|-------|-------|-----------|-----------|------|-------|")
        for p in sorted(games, key=lambda x: -x['total_notes']):
            dp = p['driver_profile']
            lines.append(
                f"| {p['game']} | {p['songs_with_audio']} | {p['total_notes']} "
                f"| {dp['avg_cc11_per_note']} | {dp['avg_cc12_per_note']} "
                f"| {dp['dominant_duty']} | {'Y' if dp['uses_noise'] else 'N'} |"
            )
        lines.append("")

    # Envelope density ranking
    lines.append("## Envelope Density Ranking (most automated first)\n")
    lines.append("| Rank | Game | CC11/note | CC12/note | Type |")
    lines.append("|------|------|-----------|-----------|------|")
    ranked = sorted(profiles, key=lambda p: -p['driver_profile']['avg_cc11_per_note'])
    for i, p in enumerate(ranked[:30], 1):
        dp = p['driver_profile']
        lines.append(f"| {i} | {p['game']} | {dp['avg_cc11_per_note']} | {dp['avg_cc12_per_note']} | {dp['envelope_type']} |")

    lines.append("")

    # NSF metadata
    lines.append("## NSF Metadata\n")
    lines.append("| Game | Songs | Load | Init | Play | Bankswitch |")
    lines.append("|------|-------|------|------|------|------------|")
    for p in sorted(profiles, key=lambda x: x['game']):
        nsf = p.get('nsf', {})
        if nsf:
            lines.append(
                f"| {p['game']} | {nsf.get('total_songs', '?')} "
                f"| {nsf.get('load_addr', '?')} | {nsf.get('init_addr', '?')} "
                f"| {nsf.get('play_addr', '?')} | {'Y' if nsf.get('uses_bankswitch') else 'N'} |"
            )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Survey NES music driver characteristics")
    parser.add_argument("--game", help="Analyze a single game in detail")
    parser.add_argument("--report", action="store_true", help="Generate markdown report")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.game:
        profile = analyze_game(args.game)
        if not profile:
            print(f"No MIDI data found for {args.game}")
            return
        print(f"\n{'='*60}")
        print(f"Driver Profile: {args.game}")
        print(f"{'='*60}")
        print(f"Songs: {profile['songs_with_audio']} / {profile['songs_extracted']}")
        print(f"Total notes: {profile['total_notes']}")
        dp = profile['driver_profile']
        print(f"\nEnvelope type: {dp['envelope_type']}")
        print(f"Volume automation: {dp['avg_cc11_per_note']} CC11 events per note")
        print(f"Duty automation: {dp['avg_cc12_per_note']} CC12 events per note")
        print(f"Dominant duty: {dp['dominant_duty']}")
        print(f"Duty distribution: {dp['duty_distribution']}")
        print(f"Uses noise/drums: {dp['uses_noise']} ({dp['noise_pct']}% of songs)")
        print(f"Channel usage: {dp['channel_usage']}")
        family = classify_driver_family(profile)
        print(f"\nDriver family: {family}")

        if profile['nsf']:
            nsf = profile['nsf']
            print(f"\nNSF: {nsf.get('title', '?')} by {nsf.get('artist', '?')}")
            print(f"  Load: {nsf['load_addr']}, Init: {nsf['init_addr']}, Play: {nsf['play_addr']}")
            print(f"  Bankswitch: {'Yes' if nsf.get('uses_bankswitch') else 'No'}")
        return

    # Survey all games
    output_dir = REPO_ROOT / "output"
    profiles = []

    game_dirs = sorted(d.name for d in output_dir.iterdir()
                       if d.is_dir() and (d / "midi").exists())

    print(f"Surveying {len(game_dirs)} games with MIDI output...")
    for game_slug in game_dirs:
        profile = analyze_game(game_slug)
        if profile:
            family = classify_driver_family(profile)
            profiles.append(profile)
            dp = profile['driver_profile']
            print(f"  {game_slug:40s} {profile['songs_with_audio']:3d} songs  "
                  f"CC11={dp['avg_cc11_per_note']:4.1f}  CC12={dp['avg_cc12_per_note']:4.1f}  "
                  f"{dp['envelope_type']:10s} [{family}]")

    print(f"\nTotal: {len(profiles)} games profiled")

    if args.report:
        report = generate_report(profiles)
        report_path = REPO_ROOT / "docs" / "DRIVER_SURVEY.md"
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"Report written to {report_path}")

    if args.json:
        json_path = REPO_ROOT / "data" / "driver_survey.json"
        with open(json_path, 'w') as f:
            json.dump(profiles, f, indent=2)
        print(f"JSON written to {json_path}")


if __name__ == "__main__":
    main()
