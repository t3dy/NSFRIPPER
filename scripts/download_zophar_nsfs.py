#!/usr/bin/env python3
"""Download NSF zip files from Zophar's Music Domain.

Given a list of game slugs, scrapes each game's page at
zophar.net/music/nintendo-nes-nsf/<slug>, finds the (EMU) zip download
link, and fetches it into ~/Downloads/ where import_zophar_nsfs.py
can pick it up.

Slugs are lowercase-with-hyphens forms of the game title, matching
Zophar's URL convention.  Examples:
  bubble-bobble
  double-dragon
  double-dragon-ii-the-revenge
  dragon-warrior-ii
  crystalis
  startropics
  shadowgate

Usage:
    python scripts/download_zophar_nsfs.py bubble-bobble double-dragon
    python scripts/download_zophar_nsfs.py --from-file slugs.txt
"""
import argparse
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path


USER_AGENT = "Mozilla/5.0 (NSFRIPPER/download_zophar_nsfs.py)"

# Zophar throttles aggressive scraping; 1s between requests is polite.
REQUEST_DELAY = 1.0


def fetch(url, max_tries=5):
    """Fetch a URL with a browser-like user agent, with retries.

    Zophar returns HTTP 404 (not 429) when rate-limiting aggressive
    scraping.  We've confirmed this by seeing the same URL return 404
    under load and 200 seconds later.  So retries use exponential
    backoff and treat 404 as a transient failure.
    """
    last_err = None
    for attempt in range(max_tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            last_err = e
            if attempt == max_tries - 1:
                raise
            # Exponential backoff: 2s, 5s, 12s, 30s
            backoff = min(30, 2 * (2.4 ** attempt))
            print(f"    retry {attempt+1} after {backoff:.0f}s: {e}")
            time.sleep(backoff)
    raise last_err  # unreachable


def find_emu_url(html: str):
    """Extract the (EMU).zophar.zip download URL from a Zophar game page.

    The URL in the HTML uses URL-encoded parens: `%28EMU%29` instead of
    `(EMU)`.  Match both forms in case Zophar changes encoding.
    """
    for emu_pat in (r"%28EMU%29", r"\(EMU\)"):
        for base in (r"https?://[^\"]*", r"/[^\"]*"):
            m = re.search(
                rf'href="({base}?/soundfiles/nintendo-nes-nsf/[^"]*?'
                rf'{emu_pat}[^"]*\.zip)"',
                html,
            )
            if m:
                url = m.group(1)
                if url.startswith("/"):
                    url = "https://www.zophar.net" + url
                return url
    return None


def download_game(slug: str, dest_dir: Path, resolver=None):
    """Download a game's NSF zip.  If slug doesn't resolve and a
    resolver callable is provided, fall back to fuzzy-matching the
    slug against the cached Zophar index."""
    print(f"\n{slug}")
    page_url = f"https://www.zophar.net/music/nintendo-nes-nsf/{slug}"
    try:
        html = fetch(page_url).decode("utf-8", errors="replace")
    except Exception as e:
        # If the slug is genuinely wrong, try fuzzy matching via the index.
        if resolver:
            alt = resolver(slug)
            if alt and alt != slug:
                print(f"  {slug} -> {alt} (fuzzy-resolved)")
                return download_game(alt, dest_dir, resolver=None)
        print(f"  ERROR fetching page: {e}")
        return False

    emu_url = find_emu_url(html)
    if not emu_url:
        print(f"  no (EMU) zip found on {page_url}")
        # Diagnostic: show what zip links do exist
        zips = re.findall(r'href="([^"]*\.zip)"', html)[:5]
        if zips:
            print(f"  zip links found: {zips}")
        return False

    print(f"  -> {emu_url}")
    # Derive filename from URL
    fname = emu_url.rsplit("/", 1)[-1]
    # URL-decode the %20 etc.
    fname = urllib.parse.unquote(fname)
    target = dest_dir / fname

    if target.is_file() and target.stat().st_size > 0:
        print(f"  EXISTS (skip): {target.name}")
        return True

    try:
        data = fetch(emu_url)
    except Exception as e:
        print(f"  ERROR downloading zip: {e}")
        return False

    dest_dir.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    print(f"  saved: {target} ({len(data)} bytes)")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*",
                    help="Game slugs (zophar.net URL form). "
                         "Example: bubble-bobble double-dragon")
    ap.add_argument("--from-file", type=Path,
                    help="File with one slug per line")
    ap.add_argument("--dest", type=Path,
                    default=Path.home() / "Downloads",
                    help="Where to save zips (default: ~/Downloads)")
    args = ap.parse_args()

    slugs = list(args.slugs)
    if args.from_file:
        slugs.extend(
            line.strip() for line in args.from_file.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

    if not slugs:
        ap.print_help()
        sys.exit(1)

    # Build a resolver from the cached index (if available) so that
    # mistyped slugs auto-correct (e.g. "wizardry" -> "wizardry-proving-grounds-of-mad-overlord").
    resolver = None
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from zophar_index import resolve_slug, load_cache
        cache = load_cache()
        if cache:
            resolver = lambda s: resolve_slug(s, cache)
            print(f"(fuzzy resolver active, {len(cache)} slugs in index)")
    except Exception as e:
        print(f"(no fuzzy resolver: {e})")

    successes = 0
    failures = []
    for slug in slugs:
        if download_game(slug, args.dest, resolver=resolver):
            successes += 1
        else:
            failures.append(slug)
        time.sleep(REQUEST_DELAY)

    print(f"\n{successes}/{len(slugs)} downloaded")
    if failures:
        print("Failed: " + ", ".join(failures))


if __name__ == "__main__":
    main()
