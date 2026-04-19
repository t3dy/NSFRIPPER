#!/usr/bin/env python3
"""Cache the Zophar NES NSF index for fuzzy slug resolution.

Zophar's game URLs use a hyphenated-lowercase slug convention that
doesn't always match the obvious transliteration of the English title
(e.g. 'Hydlide' is 'hydlide' but 'Bard's Tale' is
'bards-tale-tales-of-the-unknown').  Scraping all paginated index
pages once and caching the result lets other scripts resolve game
names to Zophar slugs without repeat scraping.

The cache is saved to data/zophar_nes_slugs.json.  Re-run when you
suspect new games may have been added.

Also exposes resolve_slug(name) as a module function:
    from scripts.zophar_index import resolve_slug
    slug = resolve_slug("Bard's Tale")   # -> 'bards-tale-tales-of-the-unknown'
    slug = resolve_slug("Wizardry")       # -> None (not on Zophar)
"""
import argparse
import gzip
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

USER_AGENT = "Mozilla/5.0 (NSFRIPPER/zophar_index.py)"
CACHE_PATH = Path(__file__).parent.parent / "data" / "zophar_nes_slugs.json"
INDEX_URL = "https://www.zophar.net/music/nintendo-nes-nsf"


def fetch(url, tries=4):
    last_err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                if r.headers.get("content-encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", errors="replace")
        except Exception as e:
            last_err = e
            if i == tries - 1:
                raise
            time.sleep(2 * (2 ** i))
    raise last_err


def refresh_cache():
    """Scrape all Zophar NES index pages and cache slugs."""
    all_slugs = set()
    for page in range(1, 20):
        url = INDEX_URL if page == 1 else f"{INDEX_URL}?page={page}"
        try:
            html = fetch(url)
        except Exception as e:
            print(f"page {page}: {e}")
            break
        hits = re.findall(r'/music/nintendo-nes-nsf/([a-z0-9-]+)"', html)
        before = len(all_slugs)
        all_slugs.update(hits)
        added = len(all_slugs) - before
        print(f"page {page}: +{added} new, total {len(all_slugs)}")
        if added == 0:
            break
        time.sleep(1.0)

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(sorted(all_slugs), indent=2))
    print(f"cached {len(all_slugs)} slugs to {CACHE_PATH}")
    return sorted(all_slugs)


def load_cache():
    if CACHE_PATH.is_file():
        return json.loads(CACHE_PATH.read_text())
    return None


def _normalize(s: str) -> str:
    """Normalize a game name for fuzzy matching."""
    s = s.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s


def resolve_slug(name: str, slugs=None):
    """Return best Zophar slug for a game name, or None if not found.

    Matching strategy:
    1. Exact slug match after normalization.
    2. Substring match (name tokens contained in slug).
    3. First slug that has all major tokens (>=4 chars) of the name.
    """
    if slugs is None:
        slugs = load_cache() or []
    target = _normalize(name)
    if target in slugs:
        return target
    tokens = [t for t in target.split("-") if len(t) >= 4]
    if not tokens:
        tokens = target.split("-")
    # Prefer slugs where every token appears
    candidates = [s for s in slugs if all(t in s for t in tokens)]
    if candidates:
        candidates.sort(key=len)  # prefer shortest (least noise)
        return candidates[0]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true",
                    help="Re-scrape Zophar index (else use cache)")
    ap.add_argument("--resolve", nargs="+",
                    help="Resolve these game names to slugs")
    ap.add_argument("--grep", help="Filter cache for substring")
    args = ap.parse_args()

    slugs = None
    if args.refresh or not CACHE_PATH.is_file():
        slugs = refresh_cache()
    else:
        slugs = load_cache()
        print(f"loaded {len(slugs)} slugs from {CACHE_PATH}")

    if args.grep:
        hits = [s for s in slugs if args.grep.lower() in s]
        print(f"\n{len(hits)} slugs matching {args.grep!r}:")
        for s in hits:
            print(f"  {s}")

    if args.resolve:
        print()
        for name in args.resolve:
            slug = resolve_slug(name, slugs)
            status = slug if slug else "NOT FOUND"
            print(f"  {name:40s} -> {status}")


if __name__ == "__main__":
    main()
