#!/usr/bin/env python3
"""Fetch NSF from joshw.info, extract all songs to MIDI, build REAPER projects.

End-to-end pipeline: one command gets you from game name to playable REAPER projects.

Usage:
    python scripts/fetch_and_extract.py "DuckTales"              # single game
    python scripts/fetch_and_extract.py "DuckTales" --songs 1-5  # specific songs
    python scripts/fetch_and_extract.py --batch 10               # first 10 games missing NSF
    python scripts/fetch_and_extract.py --batch all               # all games missing NSF
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Fix Windows cp1252 encoding errors with non-ASCII NSF metadata
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from fetch_nsf import fetch_full_index, fuzzy_match, download_and_extract, name_to_slug


def find_nsf(game_slug):
    """Find the NSF file for a game slug. Returns path or None."""
    nsf_dir = REPO_ROOT / "output" / game_slug / "nsf"
    if not nsf_dir.exists():
        return None
    nsfs = list(nsf_dir.glob("*.nsf"))
    return nsfs[0] if nsfs else None


def find_m3u(game_slug):
    """Find the M3U tracklist for a game slug. Returns path or None."""
    nsf_dir = REPO_ROOT / "output" / game_slug / "nsf"
    if not nsf_dir.exists():
        return None
    m3us = list(nsf_dir.glob("*.m3u"))
    return m3us[0] if m3us else None


def read_track_names(m3u_path):
    """Extract track names from M3U playlist."""
    if not m3u_path or not m3u_path.exists():
        return None

    names = []
    with open(m3u_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            # Format: file::NSF,song_num,title,duration,...
            # Handle escaped commas (\,) in track names by temporarily replacing them
            line_clean = line.replace('\\,', '\x00')
            parts = line_clean.split(',')
            if len(parts) >= 3:
                title = parts[2].replace('\x00', ',').strip()
                if ' - ' in title:
                    segments = title.split(' - ')
                    title = segments[-1] if len(segments) > 2 else title
                names.append(title)

    return names if names else None


def run_nsf_to_reaper(nsf_path, game_slug, track_names=None, songs=None):
    """Run nsf_to_reaper.py on an NSF file."""
    output_dir = str(REPO_ROOT / "output" / game_slug)

    cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "nsf_to_reaper.py"),
        str(nsf_path),
        "--all",
        "-o", output_dir,
    ]

    if track_names:
        cmd.extend(["--names", ",".join(track_names)])

    print(f"\n  Running nsf_to_reaper.py...")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)

    if result.returncode != 0:
        print(f"  Error: {result.stderr[:2000]}")
        return False

    # Count output files
    midi_dir = Path(output_dir) / "midi"
    reaper_dir = Path(output_dir) / "reaper"
    midi_count = len(list(midi_dir.glob("*.mid"))) if midi_dir.exists() else 0
    rpp_count = len(list(reaper_dir.glob("*.rpp"))) if reaper_dir.exists() else 0

    print(f"  -> {midi_count} MIDIs, {rpp_count} REAPER projects")
    return True


def process_game(game_name, index, songs=None):
    """Full pipeline: fetch NSF → extract → MIDI → RPP."""
    # Find in index
    matches = fuzzy_match(game_name, index)
    if not matches:
        print(f"'{game_name}' not found in joshw.info archive")
        return False

    filename, matched_name, url = matches[0]
    slug = name_to_slug(matched_name)
    print(f"\n{'='*60}")
    print(f"Processing: {matched_name} -> {slug}")
    print(f"{'='*60}")

    # Step 1: Download NSF
    nsf_path = find_nsf(slug)
    if not nsf_path:
        nsf_path = download_and_extract(url, slug)
        if not nsf_path:
            print(f"  Failed to download NSF")
            return False

    # Read song count
    with open(nsf_path, 'rb') as f:
        header = f.read(128)
        total_songs = header[6]
    print(f"  NSF: {nsf_path.name} ({total_songs} songs)")

    # Step 2: Read track names from M3U
    m3u_path = find_m3u(slug)
    track_names = read_track_names(m3u_path)
    if track_names:
        print(f"  Track names: {len(track_names)} from M3U")

    # Step 3: Check if MIDI already exists
    midi_dir = REPO_ROOT / "output" / slug / "midi"
    if midi_dir.exists() and list(midi_dir.glob("*.mid")):
        existing = len(list(midi_dir.glob("*.mid")))
        if existing >= total_songs:
            print(f"  Skip extraction: already have {existing} MIDIs")
            return True

    # Step 4: Extract all songs
    success = run_nsf_to_reaper(nsf_path, slug, track_names, songs)
    return success


def find_games_needing_nsf():
    """Find games in output/ that don't have NSF + MIDI yet."""
    output = REPO_ROOT / "output"
    needing = []
    for d in sorted(output.iterdir()):
        if not d.is_dir():
            continue
        # Has rom_capture but no midi? Needs NSF pipeline
        midi_dir = d / "midi"
        if midi_dir.exists() and list(midi_dir.glob("*.mid")):
            continue  # Already has MIDI
        needing.append(d.name)
    return needing


def find_publisher_games(index, publisher):
    """Find all games from a publisher in the joshw index, excluding already-extracted ones."""
    import re
    output = REPO_ROOT / "output"
    games = []
    for filename, url in index.items():
        if f"({publisher})" not in filename:
            continue
        # Extract game title (before first parenthesis)
        m = re.match(r'^(.+?)\s*\(', filename)
        if not m:
            continue
        title = m.group(1).strip()
        slug = name_to_slug(title)
        # Skip if already extracted
        midi_dir = output / slug / "midi"
        if midi_dir.exists() and list(midi_dir.glob("*.mid")):
            continue
        games.append((title, slug, filename, url))
    return games


def main():
    parser = argparse.ArgumentParser(
        description="Fetch NSF + extract all songs to MIDI/REAPER")
    parser.add_argument("game", nargs="?", help="Game name (fuzzy match)")
    parser.add_argument("--songs", help="Song range, e.g. '1-5' or '3'")
    parser.add_argument("--batch", help="Process N games missing MIDI ('all' or number)")
    parser.add_argument("--publisher", help="Process all unextracted games from a publisher (e.g. Capcom, Konami, Sunsoft)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    args = parser.parse_args()

    if not args.game and not args.batch and not args.publisher:
        parser.print_help()
        return

    index = fetch_full_index()

    if args.publisher:
        games = find_publisher_games(index, args.publisher)
        print(f"\n{args.publisher}: {len(games)} games to extract")

        success = 0
        failed = 0
        for title, slug, filename, url in games:
            if args.dry_run:
                print(f"  Would process: {title} -> {slug}")
                continue

            try:
                if process_game(title, index):
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"  Error processing {title}: {e}")
                failed += 1

        print(f"\n{'='*60}")
        print(f"{args.publisher} batch complete: {success} success, {failed} failed")
        return

    if args.batch:
        games = find_games_needing_nsf()
        limit = len(games) if args.batch == "all" else int(args.batch)
        games = games[:limit]
        print(f"\nBatch processing {len(games)} games:")

        success = 0
        failed = 0
        skipped = 0
        for game_slug in games:
            # Convert slug back to searchable name
            search_name = game_slug.replace("__", " - ").replace("_", " ")
            matches = fuzzy_match(search_name, index)
            if not matches:
                print(f"\n  {game_slug}: no NSF match found, skipping")
                skipped += 1
                continue

            if args.dry_run:
                print(f"  Would process: {game_slug} <- {matches[0][1]}")
                continue

            try:
                if process_game(search_name, index):
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"  Error processing {game_slug}: {e}")
                failed += 1

        print(f"\n{'='*60}")
        print(f"Batch complete: {success} success, {failed} failed, {skipped} no match")
        return

    # Single game
    process_game(args.game, index, args.songs)


if __name__ == "__main__":
    main()
