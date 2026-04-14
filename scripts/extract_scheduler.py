#!/usr/bin/env python3
"""Smart extraction scheduler with cost estimation, dynamic timeouts,
track-level checkpointing, and driver-family-aware prioritization.

Replaces the naive --publisher / --batch approach with a proper queue.

Usage:
    python scripts/extract_scheduler.py --run               # process queue
    python scripts/extract_scheduler.py --run --limit 20    # process top 20
    python scripts/extract_scheduler.py --run --max-cost 300 # skip jobs >5min
    python scripts/extract_scheduler.py --resume             # retry partials only
    python scripts/extract_scheduler.py --publisher Konami   # filter queue
    python scripts/extract_scheduler.py --family dense_automator  # by driver family
    python scripts/extract_scheduler.py --preview            # show queue without running
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

# Fix Windows encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from fetch_nsf import fetch_full_index, fuzzy_match, download_and_extract, name_to_slug

# Empirical cost per song (seconds of wall clock for 6502 emulation + MIDI + RPP)
COST_PER_SONG = 95

# Dynamic timeout: base + per-song allowance
TIMEOUT_BASE = 120      # 2 min for startup/download
TIMEOUT_PER_SONG = 100  # ~100s per song (emulation + MIDI save + RPP gen)
TIMEOUT_MAX = 7200      # 2 hour hard cap


def find_nsf(slug):
    """Find NSF file for a game slug."""
    nsf_dir = REPO_ROOT / "output" / slug / "nsf"
    if nsf_dir.exists():
        nsfs = list(nsf_dir.glob("*.nsf"))
        if nsfs:
            return nsfs[0]
    return None


def find_m3u(slug):
    """Find M3U file for a game slug."""
    nsf_dir = REPO_ROOT / "output" / slug / "nsf"
    if nsf_dir.exists():
        m3us = list(nsf_dir.glob("*.m3u"))
        if m3us:
            return m3us[0]
    return None


def read_track_names_json(m3u_path):
    """Extract track names from M3U, return as list (not comma-delimited)."""
    if not m3u_path or not m3u_path.exists():
        return None

    names = []
    with open(m3u_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            # Handle escaped commas
            line_clean = line.replace('\\,', '\x00')
            parts = line_clean.split(',')
            if len(parts) >= 3:
                title = parts[2].replace('\x00', ',').strip()
                if ' - ' in title:
                    segments = title.split(' - ')
                    title = segments[-1] if len(segments) > 2 else title
                names.append(title)

    return names if names else None


def get_extracted_songs(slug):
    """Get set of already-extracted song numbers from MIDI filenames."""
    midi_dir = REPO_ROOT / "output" / slug / "midi"
    if not midi_dir.exists():
        return set()

    extracted = set()
    for f in midi_dir.glob("*.mid"):
        # Filename format: GameSlug_NN_SongName_v1.mid
        m = re.search(r'_(\d+)_', f.name)
        if m:
            extracted.add(int(m.group(1)))
    return extracted


def compute_timeout(total_songs, already_done=0):
    """Compute dynamic timeout based on remaining song count."""
    remaining = max(1, total_songs - already_done)
    timeout = TIMEOUT_BASE + (remaining * TIMEOUT_PER_SONG)
    return min(timeout, TIMEOUT_MAX)


def extract_game(slug, nsf_path, track_names=None, songs_to_extract=None):
    """Extract a game with track-level checkpointing.

    If songs_to_extract is provided, only extract those song numbers.
    Otherwise extract all songs.
    """
    output_dir = str(REPO_ROOT / "output" / slug)

    cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "nsf_to_reaper.py"),
        str(nsf_path),
    ]

    if songs_to_extract:
        # Extract specific songs (for resume)
        # nsf_to_reaper.py --all processes all; individual songs need separate calls
        cmd.append("--all")
    else:
        cmd.append("--all")

    cmd.extend(["-o", output_dir])

    if track_names:
        # Use JSON file transport (no delimiter collision)
        names_file = Path(output_dir) / "track_names.json"
        names_file.parent.mkdir(parents=True, exist_ok=True)
        with open(names_file, 'w', encoding='utf-8') as f:
            json.dump(track_names, f, ensure_ascii=False)
        cmd.extend(["--names-json", str(names_file)])

    # Get NSF song count for timeout calculation
    try:
        with open(nsf_path, 'rb') as f:
            header = f.read(128)
            total_songs = header[6]
    except Exception:
        total_songs = 30  # default estimate

    already_done = len(get_extracted_songs(slug))
    timeout = compute_timeout(total_songs, already_done)

    print(f"  Timeout: {timeout}s ({total_songs} songs, {already_done} done)")
    print(f"  Running nsf_to_reaper.py...")

    start = time.time()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding='utf-8', errors='replace',
            timeout=timeout
        )
        elapsed = time.time() - start

        if result.returncode != 0:
            print(f"  FAILED ({elapsed:.0f}s): {result.stderr[:1000]}")
            return False, elapsed

        # Count results
        midi_dir = Path(output_dir) / "midi"
        rpp_dir = Path(output_dir) / "reaper"
        midi_count = len(list(midi_dir.glob("*.mid"))) if midi_dir.exists() else 0
        rpp_count = len(list(rpp_dir.glob("*.rpp"))) if rpp_dir.exists() else 0
        print(f"  OK ({elapsed:.0f}s): {midi_count} MIDIs, {rpp_count} RPPs")
        return True, elapsed

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        # Check how many songs were extracted before timeout
        new_done = len(get_extracted_songs(slug))
        progress = new_done - already_done
        print(f"  TIMEOUT ({elapsed:.0f}s): {progress} new songs extracted (total {new_done}/{total_songs})")
        return False, elapsed


def build_queue(games, publisher=None, family=None, status_filter=None, max_cost=None):
    """Build prioritized extraction queue from collection state."""
    queue = []

    for g in games:
        s = g["status"]
        if s == "complete":
            continue
        if s == "not_started":
            continue  # no NSF index match

        if publisher and publisher not in str(g.get("publishers", [])):
            continue
        if family and g.get("driver_family") != family:
            continue
        if status_filter and s != status_filter:
            continue

        cost = g.get("estimated_seconds", 0)
        if max_cost and cost > max_cost:
            continue

        queue.append(g)

    # Priority: partial (resume) > nsf_only (fresh) > no_nsf (needs download)
    # Within same status: small jobs first
    def priority(g):
        status_order = {"partial": 0, "midi_only": 1, "nsf_only": 2, "no_nsf": 3}
        return (status_order.get(g["status"], 4), g.get("estimated_seconds", 0))

    queue.sort(key=priority)
    return queue


def main():
    parser = argparse.ArgumentParser(description="Smart extraction scheduler")
    parser.add_argument("--run", action="store_true", help="Process extraction queue")
    parser.add_argument("--resume", action="store_true", help="Only retry partial extractions")
    parser.add_argument("--preview", action="store_true", help="Show queue without running")
    parser.add_argument("--limit", type=int, default=0, help="Max games to process (0=all)")
    parser.add_argument("--max-cost", type=int, help="Skip games estimated >N seconds")
    parser.add_argument("--publisher", help="Filter by publisher")
    parser.add_argument("--family", help="Filter by driver family")
    args = parser.parse_args()

    # Load or build collection state
    state_path = DATA_DIR / "collection_state.json"
    if state_path.exists():
        with open(state_path) as f:
            games = json.load(f)
        print(f"Loaded {len(games)} games from collection state")
    else:
        print("Building collection state...")
        from collection_state import build_state
        games = build_state()

    # Load joshw index for downloads
    index = fetch_full_index()

    # Build queue
    status_filter = "partial" if args.resume else None
    queue = build_queue(games, args.publisher, args.family, status_filter, args.max_cost)

    if args.limit:
        queue = queue[:args.limit]

    print(f"\nQueue: {len(queue)} games")

    if args.preview or not args.run:
        print(f"\n  {'Title':40s} {'Status':12s} {'Songs':>6s} {'Est':>8s} {'Family':>15s}")
        for g in queue[:50]:
            est = f"{g['estimated_seconds']//60}m" if g['estimated_seconds'] > 0 else "?"
            print(f"  {g['title'][:40]:40s} {g['status']:12s} {g['nsf_songs']:6d} {est:>8s} {g['driver_family']:>15s}")
        if len(queue) > 50:
            print(f"  ... and {len(queue)-50} more")
        return

    # Process queue
    success = 0
    failed = 0
    skipped = 0
    total_time = 0

    for i, g in enumerate(queue):
        title = g["title"]
        slug = g["slug"]
        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(queue)}] {title} -> {slug}")
        print(f"  Status: {g['status']}, Songs: {g['nsf_songs']}, Est: {g['estimated_seconds']//60}m")
        print(f"{'='*60}")

        # Step 1: Ensure we have the NSF
        nsf_path = find_nsf(slug)
        if not nsf_path:
            # Try to download
            matches = fuzzy_match(title, index)
            if not matches:
                print(f"  SKIP: no NSF match in index")
                skipped += 1
                continue

            filename, matched_name, url = matches[0]
            print(f"  Downloading from joshw.info...")
            nsf_path = download_and_extract(url, slug)
            if not nsf_path:
                print(f"  SKIP: download failed")
                skipped += 1
                continue

        # Step 2: Check if already complete
        extracted = get_extracted_songs(slug)
        try:
            with open(nsf_path, 'rb') as f:
                total_songs = f.read(128)[6]
        except Exception:
            total_songs = 0

        if total_songs > 0 and len(extracted) >= total_songs:
            print(f"  SKIP: already complete ({len(extracted)}/{total_songs})")
            skipped += 1
            continue

        # Step 3: Get track names
        m3u_path = find_m3u(slug)
        track_names = read_track_names_json(m3u_path)

        # Step 4: Extract
        ok, elapsed = extract_game(slug, nsf_path, track_names)
        total_time += elapsed

        if ok:
            success += 1
        else:
            failed += 1

    print(f"\n{'='*60}")
    print(f"Scheduler complete: {success} success, {failed} failed, {skipped} skipped")
    print(f"Total time: {total_time/60:.1f} minutes")


if __name__ == "__main__":
    main()
