#!/usr/bin/env python3
"""Batch extract MIDI from games that have NSFs but no MIDIs yet.

Reads collection_state.json, finds nsf_only games, runs nsf_to_reaper.py
on each with dynamic timeouts and proper M3U track name handling.

Usage:
    python scripts/batch_extract_nsf_only.py                # all nsf_only games
    python scripts/batch_extract_nsf_only.py --limit 20     # first 20 (smallest first)
    python scripts/batch_extract_nsf_only.py --publisher Konami  # filter by publisher
    python scripts/batch_extract_nsf_only.py --skip-existing     # skip if any MIDI exists
"""

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Fix Windows encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
DATA_DIR = REPO_ROOT / "data"


def parse_m3u(m3u_path):
    """Parse M3U file for track names, handling escaped commas."""
    names = []
    try:
        with open(m3u_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # M3U format: filename::NSF:tracknum,Track Name,duration,...
                parts = line.split(',', 1)
                if len(parts) >= 2:
                    rest = parts[1]
                    # Track name is the next field, but may contain \, (escaped commas)
                    # Split on unescaped commas
                    name_chars = []
                    i = 0
                    while i < len(rest):
                        if rest[i] == '\\' and i + 1 < len(rest) and rest[i + 1] == ',':
                            name_chars.append(',')
                            i += 2
                        elif rest[i] == ',':
                            break
                        else:
                            name_chars.append(rest[i])
                            i += 1
                    name = ''.join(name_chars).strip()
                    if name:
                        names.append(name)
    except Exception:
        return None
    return names if names else None


def main():
    parser = argparse.ArgumentParser(description='Batch extract nsf_only games')
    parser.add_argument('--limit', type=int, default=0, help='Max games to process')
    parser.add_argument('--publisher', help='Filter by publisher')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip games that already have any MIDI files')
    parser.add_argument('--status', default='nsf_only',
                        help='Status filter (default: nsf_only, use "partial" for retries)')
    args = parser.parse_args()

    state_path = DATA_DIR / "collection_state.json"
    if not state_path.exists():
        print("Run collection_state.py --save first")
        sys.exit(1)

    with open(state_path) as f:
        games = json.load(f)

    # Filter
    targets = [g for g in games if g['status'] == args.status]

    if args.publisher:
        targets = [g for g in targets
                    if args.publisher.lower() in [p.lower() for p in g.get('publishers', [])]]

    if args.skip_existing:
        targets = [g for g in targets
                    if not list((OUTPUT_DIR / g['slug'] / 'midi').glob('*.mid'))
                    if (OUTPUT_DIR / g['slug'] / 'midi').exists()]

    # Sort by song count (smallest first for fast wins)
    targets.sort(key=lambda g: g.get('nsf_songs', 0))

    if args.limit:
        targets = targets[:args.limit]

    print(f"Batch extraction: {len(targets)} games ({args.status})")
    if targets:
        print(f"Song range: {targets[0].get('nsf_songs', '?')} to {targets[-1].get('nsf_songs', '?')}")
    print()

    success = 0
    failed = 0
    skipped = 0
    start_time = time.time()

    for i, g in enumerate(targets):
        slug = g['slug']
        nsf_dir = OUTPUT_DIR / slug / 'nsf'
        nsfs = list(nsf_dir.glob('*.nsf')) if nsf_dir.exists() else []

        if not nsfs:
            print(f"[{i+1}/{len(targets)}] SKIP {slug} - no NSF file")
            skipped += 1
            continue

        nsf_path = nsfs[0]
        output_dir = str(OUTPUT_DIR / slug)
        songs = g.get('nsf_songs', 0)
        timeout = max(600, 60 + songs * 20)

        cmd = [
            sys.executable, str(REPO_ROOT / "scripts" / "nsf_to_reaper.py"),
            str(nsf_path), "--all", "-o", output_dir,
        ]

        # Handle track names from M3U
        m3u_files = list(nsf_dir.glob('*.m3u'))
        names_tmpfile = None
        if m3u_files:
            track_names = parse_m3u(m3u_files[0])
            if track_names:
                # Write to temp JSON file for --names-json
                names_tmpfile = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.json', delete=False, encoding='utf-8'
                )
                json.dump(track_names, names_tmpfile)
                names_tmpfile.close()
                cmd.extend(["--names-json", names_tmpfile.name])

        print(f"[{i+1}/{len(targets)}] {slug} ({songs} songs, t/o={timeout}s)... ",
              end='', flush=True)

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                encoding='utf-8', errors='replace', timeout=timeout
            )

            midi_dir = Path(output_dir) / 'midi'
            midi_count = len(list(midi_dir.glob('*.mid'))) if midi_dir.exists() else 0

            if result.returncode == 0 and midi_count > 0:
                print(f"OK ({midi_count} MIDIs)")
                success += 1
            else:
                err = result.stderr[:200] if result.stderr else 'no stderr'
                print(f"FAIL ({err})")
                failed += 1
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT ({timeout}s)")
            failed += 1
        except Exception as e:
            print(f"ERROR ({e})")
            failed += 1
        finally:
            if names_tmpfile:
                try:
                    Path(names_tmpfile.name).unlink()
                except Exception:
                    pass

    elapsed = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"RESULTS: {success} OK, {failed} failed, {skipped} skipped / {len(targets)} total")
    print(f"Elapsed: {elapsed/60:.1f} minutes")


if __name__ == "__main__":
    main()
