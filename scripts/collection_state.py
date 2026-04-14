#!/usr/bin/env python3
"""Build and query the collection state table — the extraction control plane.

Scans the joshw index, output folders, driver survey, and NSF metadata to
produce a unified view of every game's extraction status.

Usage:
    python scripts/collection_state.py                    # build state table
    python scripts/collection_state.py --summary          # publisher/status summary
    python scripts/collection_state.py --publisher Capcom # show one publisher
    python scripts/collection_state.py --status failed    # show games by status
    python scripts/collection_state.py --queue             # show prioritized extraction queue
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Fix Windows encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
DATA_DIR = REPO_ROOT / "data"

# Driver family classification thresholds (from driver survey research)
FAMILY_THRESHOLDS = {
    "minimal":        {"cc11_max": 3.0, "cc12_max": 0.5},
    "sunsoft_style":  {"cc11_min": 3.0, "cc11_max": 5.0, "cc12_max": 0.5},
    "dense_automator": {"cc11_min": 5.0, "cc12_max": 0.5},
    "duty_switcher":  {"cc12_min": 0.5},
    "full_animation": {"cc11_min": 5.0, "cc12_min": 0.5},
}

# Estimated seconds per song for 6502 emulation (empirical)
AVG_SECONDS_PER_SONG = 95  # ~90s emulation + overhead


def extract_publisher(filename):
    """Extract publisher(s) from joshw index filename."""
    groups = re.findall(r'\(([^)]+)\)', filename)
    # Skip year and developer markers, return likely publishers
    publishers = []
    for g in groups:
        if re.match(r'\d{4}', g):
            continue
        if g in ('NES', 'FDS', 'VRC6', 'VRC7', 'MMC5', 'N163', 'S5B'):
            continue
        publishers.append(g)
    return publishers


def extract_title(filename):
    """Extract game title from joshw index filename."""
    m = re.match(r'^(.+?)\s*\(', filename)
    return m.group(1).strip() if m else filename


def classify_driver_family(profile):
    """Classify a game's driver profile into a family."""
    if not profile:
        return "unknown"
    cc11 = profile.get("avg_cc11_per_note", 0)
    cc12 = profile.get("avg_cc12_per_note", 0)

    if cc12 >= 0.5 and cc11 >= 5.0:
        return "full_animation"
    if cc12 >= 0.5:
        return "duty_switcher"
    if cc11 >= 5.0:
        return "dense_automator"
    if cc11 >= 3.0:
        return "sunsoft_style"
    return "minimal"


def get_extraction_status(game_dir):
    """Determine extraction status for a game output directory."""
    if not game_dir.exists():
        return "not_started", {}

    nsf_dir = game_dir / "nsf"
    midi_dir = game_dir / "midi"
    reaper_dir = game_dir / "reaper"
    wav_dir = game_dir / "wav"

    has_nsf = nsf_dir.exists() and list(nsf_dir.glob("*.nsf"))
    midi_files = list(midi_dir.glob("*.mid")) if midi_dir.exists() else []
    rpp_files = list(reaper_dir.glob("*.rpp")) if reaper_dir.exists() else []
    wav_files = list(wav_dir.glob("*.wav")) if wav_dir.exists() else []

    # Get NSF song count
    nsf_songs = 0
    if has_nsf:
        nsf_path = list(nsf_dir.glob("*.nsf"))[0]
        try:
            with open(nsf_path, 'rb') as f:
                header = f.read(128)
                nsf_songs = header[6] if len(header) > 6 else 0
        except Exception:
            pass

    # Validity checks on MIDI files
    invalid_midis = 0
    empty_midis = 0
    for mf in midi_files:
        try:
            if mf.stat().st_size < 100:  # truncated/empty
                invalid_midis += 1
                empty_midis += 1
        except Exception:
            invalid_midis += 1

    details = {
        "has_nsf": has_nsf,
        "nsf_songs": nsf_songs,
        "midi_count": len(midi_files),
        "rpp_count": len(rpp_files),
        "wav_count": len(wav_files),
        "invalid_midis": invalid_midis,
        "empty_midis": empty_midis,
    }

    if not has_nsf:
        return "no_nsf", details

    if len(midi_files) == 0:
        return "nsf_only", details

    if invalid_midis > 0:
        return "invalid", details

    if nsf_songs > 0 and len(midi_files) < nsf_songs:
        return "partial", details

    if len(midi_files) >= nsf_songs and nsf_songs > 0:
        if len(rpp_files) >= nsf_songs:
            return "complete", details
        return "midi_only", details

    return "complete", details


def estimate_cost(nsf_songs):
    """Estimate extraction runtime in seconds."""
    return nsf_songs * AVG_SECONDS_PER_SONG


def build_state():
    """Build the complete collection state table."""
    # Load joshw index
    index_path = DATA_DIR / "joshw_index.json"
    if index_path.exists():
        with open(index_path) as f:
            index = json.load(f)
    else:
        index = {}

    # Load driver survey
    survey_path = DATA_DIR / "driver_survey.json"
    survey_by_game = {}
    if survey_path.exists():
        with open(survey_path) as f:
            survey = json.load(f)
        for entry in survey:
            survey_by_game[entry["game"]] = entry

    # Build state for each game in the index
    games = []
    seen_slugs = set()

    for filename, url in sorted(index.items()):
        title = extract_title(filename)
        publishers = extract_publisher(filename)

        # Generate slug (same logic as fetch_nsf.name_to_slug)
        slug = re.sub(r'[^\w\s-]', '', title).replace(' ', '_').strip('_')
        if not slug:
            continue

        # Avoid duplicate slugs (JP/US versions map to same folder)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        game_dir = OUTPUT_DIR / slug
        status, details = get_extraction_status(game_dir)

        # Check survey data
        survey_entry = survey_by_game.get(title, survey_by_game.get(slug, None))
        driver_profile = survey_entry.get("driver_profile") if survey_entry else None
        driver_family = classify_driver_family(driver_profile) if driver_profile else "unknown"

        nsf_songs = details.get("nsf_songs", 0)

        game_entry = {
            "title": title,
            "slug": slug,
            "publishers": publishers,
            "status": status,
            "driver_family": driver_family,
            "nsf_songs": nsf_songs,
            "midi_count": details.get("midi_count", 0),
            "rpp_count": details.get("rpp_count", 0),
            "estimated_seconds": estimate_cost(nsf_songs) if nsf_songs > 0 else 0,
            "completeness": (
                round(details["midi_count"] / nsf_songs, 2)
                if nsf_songs > 0 else 0
            ),
        }

        games.append(game_entry)

    # Also scan output/ for games not in the index
    for d in sorted(OUTPUT_DIR.iterdir()):
        if not d.is_dir():
            continue
        slug = d.name
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        status, details = get_extraction_status(d)
        nsf_songs = details.get("nsf_songs", 0)

        game_entry = {
            "title": slug.replace('_', ' '),
            "slug": slug,
            "publishers": [],
            "status": status,
            "driver_family": "unknown",
            "nsf_songs": nsf_songs,
            "midi_count": details.get("midi_count", 0),
            "rpp_count": details.get("rpp_count", 0),
            "estimated_seconds": estimate_cost(nsf_songs) if nsf_songs > 0 else 0,
            "completeness": (
                round(details["midi_count"] / nsf_songs, 2)
                if nsf_songs > 0 else 0
            ),
        }
        games.append(game_entry)

    return games


def print_summary(games):
    """Print publisher/status summary."""
    status_counts = Counter(g["status"] for g in games)
    family_counts = Counter(g["driver_family"] for g in games if g["status"] == "complete")
    pub_counts = defaultdict(lambda: Counter())

    for g in games:
        for pub in g["publishers"]:
            pub_counts[pub][g["status"]] += 1

    print("=== EXTRACTION STATUS ===")
    for status, count in status_counts.most_common():
        print(f"  {status:15s} {count:5d}")
    print(f"  {'TOTAL':15s} {len(games):5d}")

    print(f"\n=== DRIVER FAMILIES (complete games only) ===")
    for family, count in family_counts.most_common():
        print(f"  {family:20s} {count:5d}")

    print(f"\n=== TOP PUBLISHERS ===")
    top_pubs = sorted(pub_counts.items(), key=lambda x: sum(x[1].values()), reverse=True)[:15]
    print(f"  {'Publisher':20s} {'Complete':>8s} {'Partial':>8s} {'NSF Only':>8s} {'No NSF':>8s} {'Total':>6s}")
    for pub, statuses in top_pubs:
        total = sum(statuses.values())
        print(f"  {pub:20s} {statuses.get('complete',0):8d} {statuses.get('partial',0):8d} {statuses.get('nsf_only',0):8d} {statuses.get('no_nsf',0)+statuses.get('not_started',0):8d} {total:6d}")


def print_queue(games, limit=50):
    """Print prioritized extraction queue."""
    queue = [g for g in games if g["status"] in ("nsf_only", "partial", "no_nsf")]

    # Sort: partial first (resume), then nsf_only, then by cost (small first)
    def priority(g):
        status_order = {"partial": 0, "nsf_only": 1, "no_nsf": 2}
        return (status_order.get(g["status"], 3), g["estimated_seconds"])

    queue.sort(key=priority)

    print(f"=== EXTRACTION QUEUE (top {limit}) ===")
    print(f"  {'Title':40s} {'Status':12s} {'Songs':>6s} {'Est':>8s} {'Family':>15s} {'Publisher':>15s}")
    for g in queue[:limit]:
        est = f"{g['estimated_seconds']//60}m" if g['estimated_seconds'] > 0 else "?"
        pub = g['publishers'][0] if g['publishers'] else "?"
        print(f"  {g['title'][:40]:40s} {g['status']:12s} {g['nsf_songs']:6d} {est:>8s} {g['driver_family']:>15s} {pub:>15s}")


def main():
    parser = argparse.ArgumentParser(description="Collection state control plane")
    parser.add_argument("--summary", action="store_true", help="Show summary")
    parser.add_argument("--publisher", help="Filter by publisher")
    parser.add_argument("--status", help="Filter by status")
    parser.add_argument("--queue", action="store_true", help="Show extraction queue")
    parser.add_argument("--save", action="store_true", help="Save state to JSON")
    args = parser.parse_args()

    games = build_state()

    if args.save or not any([args.summary, args.publisher, args.status, args.queue]):
        # Save state
        state_path = DATA_DIR / "collection_state.json"
        with open(state_path, 'w') as f:
            json.dump(games, f, indent=2)
        print(f"Saved {len(games)} games to {state_path}")

    if args.summary or not any([args.publisher, args.status, args.queue]):
        print_summary(games)

    if args.publisher:
        filtered = [g for g in games if args.publisher in str(g["publishers"])]
        print(f"\n=== {args.publisher} ({len(filtered)} games) ===")
        print(f"  {'Title':40s} {'Status':12s} {'MIDI':>5s} {'RPP':>5s} {'Family':>15s}")
        for g in sorted(filtered, key=lambda x: x["title"]):
            print(f"  {g['title'][:40]:40s} {g['status']:12s} {g['midi_count']:5d} {g['rpp_count']:5d} {g['driver_family']:>15s}")

    if args.status:
        filtered = [g for g in games if g["status"] == args.status]
        print(f"\n=== Status: {args.status} ({len(filtered)} games) ===")
        for g in sorted(filtered, key=lambda x: x["title"]):
            pub = g['publishers'][0] if g['publishers'] else "?"
            print(f"  {g['title'][:40]:40s} {pub:>15s} {g['driver_family']:>15s}")

    if args.queue:
        print_queue(games)


if __name__ == "__main__":
    main()
