#!/usr/bin/env python3
"""Import Zophar's Music Domain NSF zip files into the project.

Scans a directory (default: ~/Downloads) for files matching
``*(EMU).zophar*.zip``, extracts each zip, and places the NSF (+ M3U
if present) into ``output/<slug>/nsf/``.

The slug is derived from the NSF filename by dropping the
(year-date)(author)(publisher).nsf suffix and normalizing punctuation
to underscores, matching the convention used by the outputv5 / outputv6
pipeline.

Usage:
    python scripts/import_zophar_nsfs.py                   # ~/Downloads, everything
    python scripts/import_zophar_nsfs.py --src DIR         # different source dir
    python scripts/import_zophar_nsfs.py --only Faxanadu   # single game by slug match
    python scripts/import_zophar_nsfs.py --dry-run         # show what would be done
"""
import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO / "output"


def slug_from_nsf_name(nsf_name: str) -> str:
    """Derive a game slug from an NSF filename.

    Examples:
      'Final Fantasy (1987-12-18)(Square).nsf'
          -> 'Final_Fantasy'
      "Goonies II, The [Goonies 2 - Fratelli Saigo no Chousen] (1987-03-18)(Konami).nsf"
          -> 'Goonies_II'
      "Castlevania 3 - Dracula's Curse [Akumajou Densetsu] (1989-12-22)(Konami).nsf"
          -> 'Castlevania_3___Draculas_Curse'
      "Wizards & Warriors (1987-12)(Rare)(Acclaim).nsf"
          -> 'Wizards_and_Warriors'
    """
    # Drop extension
    stem = nsf_name.rsplit(".nsf", 1)[0]
    # Drop content in [...] (alternative title like Japanese name)
    stem = re.sub(r"\s*\[[^\]]*\]", "", stem)
    # Drop trailing (year-month-day)(author)(publisher) chain -- anything from
    # the first ` (20xx` or ` (19xx` pattern onward.
    stem = re.sub(r"\s*\(\d{4}.*$", "", stem)
    # Common typographic substitutions
    stem = stem.replace("&", "and")
    stem = stem.replace("'", "")
    # Remove remaining non-alphanumeric-hyphen-underscore-space characters
    stem = re.sub(r"[^A-Za-z0-9 _\-]", "_", stem)
    # Collapse whitespace and hyphens to single underscores
    stem = re.sub(r"\s+", "_", stem)
    stem = re.sub(r"-", "_", stem)
    stem = re.sub(r"_+", "_", stem)
    return stem.strip("_")


def find_zophar_zips(src_dir: Path):
    patterns = [
        "*(EMU).zophar.zip",
        "*(EMU).zophar (*).zip",  # numbered duplicates
    ]
    seen_base = set()
    out = []
    for pat in patterns:
        for p in sorted(src_dir.glob(pat)):
            # Deduplicate games (prefer the non-numbered copy)
            # Base name = strip " (1)", " (2)" before .zip
            base = re.sub(r" \(\d+\)\.zip$", ".zip", p.name)
            if base not in seen_base:
                seen_base.add(base)
                out.append(p)
    return out


def import_zip(zip_path: Path, dry_run: bool = False, force: bool = False):
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        nsf_names = [n for n in names if n.lower().endswith(".nsf")]
        m3u_names = [n for n in names if n.lower().endswith(".m3u")]
        if not nsf_names:
            print(f"  SKIP (no NSF inside): {zip_path.name}")
            return None
        # Pick the first NSF
        primary = nsf_names[0]
        slug = slug_from_nsf_name(primary.split("/")[-1])
        out_dir = OUTPUT_DIR / slug / "nsf"
        out_nsf = out_dir / primary.split("/")[-1]

        if out_nsf.is_file() and not force:
            print(f"  EXISTS (skip): {out_nsf.relative_to(REPO)}")
            return slug

        print(f"  -> {slug}")
        if dry_run:
            for n in nsf_names + m3u_names:
                print(f"     would extract {n}")
            return slug

        out_dir.mkdir(parents=True, exist_ok=True)
        for n in nsf_names + m3u_names:
            target = out_dir / n.split("/")[-1]
            with zf.open(n) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            print(f"     extracted {target.relative_to(REPO)}")
        return slug


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path,
                    default=Path.home() / "Downloads",
                    help="Directory to scan for zophar zips")
    ap.add_argument("--only", action="append", default=[],
                    help="Only import games whose slug contains this (repeatable)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="Re-extract even if target NSF already exists")
    args = ap.parse_args()

    if not args.src.is_dir():
        print(f"ERROR: source dir {args.src} does not exist", file=sys.stderr)
        sys.exit(1)

    zips = find_zophar_zips(args.src)
    print(f"Found {len(zips)} Zophar zip files in {args.src}")

    imported_slugs = []
    for zp in zips:
        if args.only:
            check = any(o.lower() in zp.name.lower() for o in args.only)
            if not check:
                continue
        print(f"\n{zp.name}:")
        slug = import_zip(zp, dry_run=args.dry_run, force=args.force)
        if slug:
            imported_slugs.append(slug)

    print(f"\n{'Would have imported' if args.dry_run else 'Imported'}: "
          f"{len(imported_slugs)} games")
    for s in sorted(set(imported_slugs)):
        print(f"  {s}")


if __name__ == "__main__":
    main()
