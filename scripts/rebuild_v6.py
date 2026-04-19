#!/usr/bin/env python3
"""Rebuild every game currently in outputv5/ into outputv6/ using the
updated pipeline (shared-scale stems + LP anti-alias + DC blocker + noise
length counter).

Iterates each game directory under outputv5/, finds its NSF under
output/<game>/nsf/, and runs batch_stems_project.py into outputv6/<game>/.

outputv5/ is left untouched as the "noisy example" archive.

Usage:
    python scripts/rebuild_v6.py [--only GAME] [--seconds 60]
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "output"
V5 = REPO_ROOT / "outputv5"
V6 = REPO_ROOT / "outputv6"


def find_nsf(game_slug):
    # Exact match first
    nsf_dir = OUTPUT / game_slug / "nsf"
    if nsf_dir.is_dir():
        nsfs = sorted(nsf_dir.glob("*.nsf"))
        if nsfs:
            return nsfs[0]

    # Fuzzy match: outputv5 slugs are simplified (no punctuation/subtitles),
    # output/ paths include original title ("Legend_of_Zelda,_The",
    # "Zelda_II___The_Adventure_of_Link", etc.).  Also normalize Roman
    # numerals (ii/iii/iv) <-> Arabic (2/3/4) so Final_Fantasy_2 resolves
    # to Final_Fantasy_II.
    def normalize(s):
        s = s.lower().replace("_", "").replace(",", "").replace(" ", "")
        # Replace roman numeral runs in word-boundary-ish positions.  Only
        # handle II..VI because that's what the NES library uses.
        roman_map = [("viii", "8"), ("vii", "7"), ("vi", "6"), ("iv", "4"),
                     ("iii", "3"), ("ii", "2"), ("ix", "9"), ("v", "5"),
                     ("x", "10")]
        for r, a in roman_map:
            s = s.replace(r, a)
        return s

    normalized_slug = normalize(game_slug)
    for candidate in OUTPUT.iterdir():
        if not candidate.is_dir():
            continue
        name_norm = normalize(candidate.name)
        if name_norm == normalized_slug or name_norm.startswith(normalized_slug):
            cand_nsf = candidate / "nsf"
            if cand_nsf.is_dir():
                nsfs = sorted(cand_nsf.glob("*.nsf"))
                if nsfs:
                    return nsfs[0]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[],
                    help="Only render this game (repeatable)")
    ap.add_argument("--seconds", type=float, default=180.0,
                    help="Max duration per song (M3U may be shorter). "
                         "Bumped 60->180 2026-04-18 evening after user "
                         "reported Metroid Brinstar (95.9s M3U) cut off "
                         "at 60s.  Short songs still use their M3U length.")
    ap.add_argument("--skip", action="append", default=[],
                    help="Skip this game (repeatable)")
    ap.add_argument("--force", action="store_true",
                    help="Re-render even if outputv6/GAME already has RPPs")
    ap.add_argument("--numeric-labels", action="store_true",
                    help="Pass --numeric-labels to batch_stems_project.py "
                         "(numeric Song_NN names, avoids M3U label errors)")
    args = ap.parse_args()

    V6.mkdir(exist_ok=True)

    games = sorted(p.name for p in V5.iterdir()
                   if p.is_dir() and not p.name.startswith("_"))
    if args.only:
        games = [g for g in games if g in args.only]
    games = [g for g in games if g not in args.skip]

    print(f"Rebuilding {len(games)} games into {V6}")
    successes = []
    failures = []
    for i, slug in enumerate(games, 1):
        nsf = find_nsf(slug)
        if not nsf:
            print(f"[{i:2d}/{len(games)}] {slug}: NO NSF FOUND, skipping")
            failures.append((slug, "no_nsf"))
            continue

        out_dir = V6 / slug
        # Skip if already complete (idempotent) unless --force
        if not args.force and (out_dir / "reaper").is_dir():
            existing = list((out_dir / "reaper").glob("*.rpp"))
            if existing:
                print(f"[{i:2d}/{len(games)}] {slug}: {len(existing)} RPPs already exist, skipping")
                successes.append(slug)
                continue

        print(f"[{i:2d}/{len(games)}] {slug}: rendering...")
        # Clean stale output when force-rendering.  Without this, --force
        # just overwrites files one-by-one but leaves files from previous
        # runs (especially if earlier runs used different naming -- e.g.
        # M3U labels vs --numeric-labels).
        if args.force and out_dir.is_dir():
            for sub in ("reaper", "stems", "midi", "_nsf_extract"):
                target = out_dir / sub
                if target.is_dir():
                    try:
                        shutil.rmtree(target)
                    except OSError:
                        pass  # locked files (REAPER open) will be overwritten where possible
        log_path = V6 / f"_log_{slug}.log"
        batch_cmd = [
            sys.executable, "scripts/batch_stems_project.py",
            str(nsf), "--seconds", str(args.seconds),
            "--out-dir", str(out_dir),
        ]
        if args.numeric_labels:
            batch_cmd.append("--numeric-labels")
        with open(log_path, "w", encoding="utf-8") as logf:
            r = subprocess.run(batch_cmd,
                               stdout=logf, stderr=subprocess.STDOUT,
                               cwd=str(REPO_ROOT))
        if r.returncode == 0:
            n = len(list((out_dir / "reaper").glob("*.rpp"))) if (out_dir / "reaper").is_dir() else 0
            print(f"            ok, {n} songs -> {out_dir}")
            successes.append(slug)
        else:
            print(f"            FAILED (exit {r.returncode}), see {log_path}")
            failures.append((slug, f"exit_{r.returncode}"))

    print(f"\nDone. {len(successes)} ok / {len(failures)} failed.")
    if failures:
        print("Failures:")
        for slug, why in failures:
            print(f"  {slug}: {why}")


if __name__ == "__main__":
    main()
