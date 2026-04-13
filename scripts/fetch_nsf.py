#!/usr/bin/env python3
"""Download NSF files from nsf.joshw.info and extract to output/<Game>/nsf/.

Usage:
    python scripts/fetch_nsf.py "Castlevania"          # single game (fuzzy match)
    python scripts/fetch_nsf.py --list                  # show all available games
    python scripts/fetch_nsf.py --match-existing        # download NSFs for all games in output/
    python scripts/fetch_nsf.py --match-existing --dry-run  # show what would be downloaded
"""

import argparse
import io
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

try:
    import py7zr
except ImportError:
    sys.exit("py7zr not installed. Run: pip install py7zr")

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://nsf.joshw.info"
LETTERS = list("abcdefghijklmnopqrstuvwxyz") + ["0-9"]
USER_AGENT = "NSFRIPPER/1.0 (NES music extraction project)"
INDEX_CACHE = REPO_ROOT / "data" / "joshw_index.json"


def fetch_index(letter):
    """Fetch directory listing for one letter, return list of (filename, url)."""
    url = f"{BASE_URL}/{letter}/"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  Warning: could not fetch {url}: {e}", file=sys.stderr)
        return []

    # Parse href links ending in .7z
    links = re.findall(r'href="([^"]+\.7z)"', html)
    results = []
    for link in links:
        decoded = urllib.parse.unquote(link)
        full_url = f"{BASE_URL}/{letter}/{link}"
        results.append((decoded, full_url))
    return results


def fetch_full_index(force_refresh=False):
    """Fetch the complete index across all letters. Returns dict: filename -> url.

    Caches to data/joshw_index.json for 7 days to avoid hammering the server.
    """
    # Check cache
    if not force_refresh and INDEX_CACHE.exists():
        age_days = (time.time() - INDEX_CACHE.stat().st_mtime) / 86400
        if age_days < 7:
            with open(INDEX_CACHE) as f:
                index = json.load(f)
            print(f"Using cached index ({len(index)} games, {age_days:.1f} days old)")
            return index

    print("Fetching joshw.info index (first run, will cache for 7 days)...")
    index = {}
    for letter in LETTERS:
        entries = fetch_index(letter)
        for filename, url in entries:
            index[filename] = url
        if entries:
            print(f"  {letter}: {len(entries)} games")
    print(f"Total: {len(index)} NSF archives available")

    # Cache
    INDEX_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_CACHE, 'w') as f:
        json.dump(index, f, indent=1)
    print(f"Cached to {INDEX_CACHE}")

    return index


def extract_game_name(filename):
    """Extract the human-readable game name from a joshw filename.

    'Castlevania [Akumajou Dracula] (1987-05)(Konami)[NES].7z'
    -> 'Castlevania'
    """
    # Remove .7z
    name = filename.replace(".7z", "")
    # Remove [platform] tag at end
    name = re.sub(r'\[(?:NES|FDS|Famicom)\]$', '', name).strip()
    # Remove (year)(developer)(publisher) parentheticals
    name = re.sub(r'\([^)]*\)', '', name).strip()
    # Remove [Japanese title] brackets
    name = re.sub(r'\[[^\]]*\]', '', name).strip()
    return name


def name_to_slug(name):
    """Convert game name to output directory slug.

    'Castlevania 3 - Dracula's Curse' -> 'Castlevania_3___Draculas_Curse'
    """
    slug = name.replace("'", "").replace("!", "").replace("?", "")
    slug = slug.replace(" - ", "__")
    slug = slug.replace("-", "_")
    slug = slug.replace(" ", "_")
    slug = slug.replace(":", "")
    slug = slug.replace("&", "and")
    slug = re.sub(r'_+', '_', slug)
    slug = slug.strip("_")
    return slug


def normalize_for_search(text):
    """Normalize a string for fuzzy comparison."""
    t = text.lower()
    # Remove common suffixes/prefixes
    t = re.sub(r'\b(the|a|an)\b', '', t)
    # Normalize punctuation and spacing
    t = t.replace("-", " ").replace("_", " ").replace("'", "").replace("!", "")
    t = t.replace(":", "").replace("&", "and").replace("+", "and")
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def fuzzy_match(query, index):
    """Find best matches for a query string in the index."""
    query_norm = normalize_for_search(query)
    query_words = set(query_norm.split())
    matches = []
    for filename in index:
        game_name = extract_game_name(filename)
        name_norm = normalize_for_search(game_name)

        # Exact normalized match
        if query_norm == name_norm:
            matches.append((filename, game_name, index[filename], 100))
            continue

        # Query contained in name or vice versa
        if query_norm in name_norm or name_norm in query_norm:
            matches.append((filename, game_name, index[filename], 80))
            continue

        # Word overlap score
        name_words = set(name_norm.split())
        overlap = len(query_words & name_words)
        if overlap >= max(1, len(query_words) - 1):
            score = overlap * 20
            matches.append((filename, game_name, index[filename], score))

    # Sort by score descending, then name length ascending
    matches.sort(key=lambda x: (-x[3], len(x[1])))
    # Return without score
    return [(m[0], m[1], m[2]) for m in matches]


def download_and_extract(url, game_slug, dry_run=False):
    """Download .7z from URL, extract .nsf and .m3u to output/<slug>/nsf/."""
    nsf_dir = REPO_ROOT / "output" / game_slug / "nsf"

    # Check if NSF already exists
    if nsf_dir.exists():
        existing_nsf = list(nsf_dir.glob("*.nsf"))
        if existing_nsf:
            print(f"  Skip {game_slug}: already has {existing_nsf[0].name}")
            return existing_nsf[0]

    if dry_run:
        print(f"  Would download: {game_slug}")
        return None

    print(f"  Downloading {game_slug}...")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        data = resp.read()
    except Exception as e:
        print(f"  Error downloading: {e}", file=sys.stderr)
        return None

    # Extract .nsf and .m3u from 7z
    nsf_dir.mkdir(parents=True, exist_ok=True)
    nsf_path = None
    try:
        with py7zr.SevenZipFile(io.BytesIO(data), mode='r') as z:
            names_to_extract = [n for n in z.getnames()
                                if n.lower().endswith(('.nsf', '.m3u'))]
            if names_to_extract:
                z.extract(path=str(nsf_dir), targets=names_to_extract)
                for name in names_to_extract:
                    if name.lower().endswith('.nsf'):
                        nsf_path = nsf_dir / name
    except Exception as e:
        print(f"  Error extracting 7z: {e}", file=sys.stderr)
        # Try with subprocess 7z as fallback
        try:
            import subprocess
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.7z', delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            result = subprocess.run(
                ['7z', 'e', '-y', f'-o{nsf_dir}', tmp_path, '*.nsf', '*.m3u'],
                capture_output=True, timeout=30)
            os.unlink(tmp_path)
            if result.returncode == 0:
                nsfs = list(nsf_dir.glob("*.nsf"))
                nsf_path = nsfs[0] if nsfs else None
            else:
                print(f"  7z fallback also failed", file=sys.stderr)
                return None
        except (FileNotFoundError, Exception):
            # No 7z binary available either
            return None

    if nsf_path and nsf_path.exists():
        # Read song count from header
        with open(nsf_path, 'rb') as f:
            header = f.read(128)
            total_songs = header[6]
            title = header[14:46].decode('ascii', errors='replace').rstrip('\x00')
        print(f"  -> {nsf_path.name} ({total_songs} songs, \"{title}\")")
        return nsf_path
    else:
        print(f"  Warning: no .nsf found in archive")
        return None


def match_existing_games(index):
    """Match games in output/ against the joshw index."""
    output_dir = REPO_ROOT / "output"
    if not output_dir.exists():
        return []

    matches = []
    game_dirs = sorted(d.name for d in output_dir.iterdir() if d.is_dir())

    for game_slug in game_dirs:
        # Skip if already has NSF
        nsf_dir = output_dir / game_slug / "nsf"
        if nsf_dir.exists() and list(nsf_dir.glob("*.nsf")):
            continue

        # Try to match against index
        # Convert slug back to searchable name
        search_name = game_slug.replace("__", " - ").replace("_", " ")
        found = fuzzy_match(search_name, index)
        if found:
            # Take best match (shortest name = most likely exact match)
            matches.append((game_slug, found[0]))

    return matches


def main():
    parser = argparse.ArgumentParser(description="Download NSF files from nsf.joshw.info")
    parser.add_argument("game", nargs="?", help="Game name to search for (fuzzy match)")
    parser.add_argument("--list", action="store_true", help="List all available games")
    parser.add_argument("--match-existing", action="store_true",
                        help="Download NSFs for all games in output/ that don't have one")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded")
    parser.add_argument("--force", action="store_true", help="Re-download even if NSF exists")
    parser.add_argument("--first", action="store_true",
                        help="Auto-select first match (no interactive prompt)")
    parser.add_argument("--all-matches", action="store_true",
                        help="Download all matches (no interactive prompt)")
    parser.add_argument("--refresh", action="store_true",
                        help="Force refresh the joshw.info index cache")
    args = parser.parse_args()

    if not args.game and not args.list and not args.match_existing:
        parser.print_help()
        return

    index = fetch_full_index(force_refresh=args.refresh)

    if args.list:
        for filename in sorted(index.keys()):
            name = extract_game_name(filename)
            print(f"  {name}")
        return

    if args.match_existing:
        matches = match_existing_games(index)
        print(f"\nFound {len(matches)} games in output/ that could get NSF files:")
        downloaded = 0
        for game_slug, (filename, game_name, url) in matches:
            print(f"  {game_slug} <- {game_name}")
            result = download_and_extract(url, game_slug, dry_run=args.dry_run)
            if result:
                downloaded += 1
        if not args.dry_run:
            print(f"\nDownloaded {downloaded} NSF files")
        return

    # Single game search
    matches = fuzzy_match(args.game, index)
    if not matches:
        print(f"No matches for '{args.game}'")
        print("Try --list to see all available games")
        return

    if len(matches) == 1 or args.first:
        filename, game_name, url = matches[0]
        slug = name_to_slug(game_name)
        print(f"Match: {game_name}")
        download_and_extract(url, slug, dry_run=args.dry_run)
    elif args.all_matches:
        print(f"Downloading all {len(matches)} matches for '{args.game}':")
        for filename, game_name, url in matches:
            slug = name_to_slug(game_name)
            download_and_extract(url, slug, dry_run=args.dry_run)
    else:
        print(f"Multiple matches for '{args.game}':")
        for i, (filename, game_name, url) in enumerate(matches[:20]):
            print(f"  [{i+1}] {game_name}")

        try:
            choice = input("\nDownload which? (number, 'all', or Enter to cancel): ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if choice.lower() == "all":
            for filename, game_name, url in matches:
                slug = name_to_slug(game_name)
                download_and_extract(url, slug, dry_run=args.dry_run)
        elif choice.isdigit() and 1 <= int(choice) <= len(matches):
            idx = int(choice) - 1
            filename, game_name, url = matches[idx]
            slug = name_to_slug(game_name)
            download_and_extract(url, slug, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
