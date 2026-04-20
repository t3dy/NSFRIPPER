#!/usr/bin/env python3
"""Render every NSF under output/<slug>/nsf/ into outputv6/<slug>/.

Successor to rebuild_v6.py now that outputv5/ (the previous authoritative
game list) has been deleted.  Walks output/ directly, renders any NSF
that doesn't already have an RPP in outputv6/<slug>/reaper/.

Usage:
    python scripts/render_all_nsfs.py                 # render missing games
    python scripts/render_all_nsfs.py --force         # re-render everything
    python scripts/render_all_nsfs.py --only NAME     # render specific slug(s)
    python scripts/render_all_nsfs.py --skip NAME     # skip specific slug(s)
    python scripts/render_all_nsfs.py --seconds 180   # per-song max duration
"""
import argparse
import os
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


def preflight_disk_check(num_games, seconds_cap, out_dir=Path(".")):
    """Estimate disk footprint and refuse if it exceeds 50% of free space.

    Per architecture.md Rule 38.  Prevents the 2026-04-18 and
    2026-04-19 disk-full failures from recurring.

    Estimate: ~1 GB per game at seconds_cap=180 (stems + midi + RPP).
    Linear with seconds_cap.
    """
    gb_per_game = (seconds_cap / 180.0) * 1.0
    est_gb = num_games * gb_per_game
    free_gb = shutil.disk_usage(str(out_dir)).free / (1024 ** 3)
    print(f"Pre-flight disk check:")
    print(f"  estimated output: {est_gb:.1f} GB for {num_games} games at "
          f"{seconds_cap}s each")
    print(f"  free space: {free_gb:.1f} GB")
    if est_gb > free_gb * 0.5:
        print(f"\n  ERROR: estimated footprint exceeds 50% of free disk.")
        print(f"  Refusing to run.  Options:")
        print(f"    - Lower --seconds (halve it to halve the footprint)")
        print(f"    - Free disk (delete outputv6_*/, old stems, etc.)")
        print(f"    - Override with --disk-override if you accept the risk")
        return False
    return True

REPO = Path(__file__).resolve().parent.parent
OUTPUT = REPO / "output"
V6 = REPO / "outputv6"


def _render_one(item, force, seconds, numeric_labels, m3u_labels, total):
    """Top-level worker (must be importable for multiprocessing pickling)."""
    i, slug, nsf_s, out_s, reaper_s = item
    nsf = Path(nsf_s)
    out_dir = Path(out_s)
    reaper_dir = Path(reaper_s)
    print(f"[{i:3d}/{total}] {slug}: rendering...", flush=True)
    if force and out_dir.is_dir():
        for sub in ("reaper", "stems", "midi", "_nsf_extract"):
            target = out_dir / sub
            if target.is_dir():
                try:
                    shutil.rmtree(target)
                except OSError:
                    pass
    log_path = V6 / f"_log_{slug}.log"
    cmd = [
        sys.executable, "scripts/batch_stems_project.py",
        str(nsf), "--seconds", str(seconds),
        "--out-dir", str(out_dir),
    ]
    if numeric_labels and not m3u_labels:
        cmd.append("--numeric-labels")
    with open(log_path, "w", encoding="utf-8") as logf:
        r = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT,
                           cwd=str(REPO))
    if r.returncode == 0 and reaper_dir.is_dir():
        n = len(list(reaper_dir.glob("*.rpp")))
        return (slug, "ok", n)
    return (slug, "failed", r.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--skip", action="append", default=[])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--seconds", type=float, default=180.0)
    ap.add_argument("--numeric-labels", action="store_true", default=True,
                    help="(default) Use Song_NN naming instead of M3U labels")
    ap.add_argument("--m3u-labels", action="store_true",
                    help="Use M3U labels (overrides --numeric-labels)")
    ap.add_argument("--from-list", type=Path,
                    help="Read game slugs from a text file, one per line. "
                         "Produced by apply_repairs.py --emit-rerender-list.")
    ap.add_argument("-j", "--jobs", type=int, default=1,
                    help="Render N games in parallel (each game is CPU-"
                         "bound; on a multicore machine 4-8 is a good "
                         "starting point).  Default 1 = sequential.")
    ap.add_argument("--disk-override", action="store_true",
                    help="Skip the disk-space preflight check.  Only pass "
                         "this if you understand what you are doing.  "
                         "The default check refuses to run if estimated "
                         "output > 50%% of free space.")
    args = ap.parse_args()

    if args.from_list:
        if not args.from_list.is_file():
            print(f"ERROR: --from-list file not found: {args.from_list}",
                  file=sys.stderr)
            sys.exit(1)
        list_slugs = [line.strip() for line in
                      args.from_list.read_text(encoding="utf-8").splitlines()
                      if line.strip() and not line.strip().startswith("#")]
        args.only = list(args.only) + list_slugs

    V6.mkdir(exist_ok=True)

    candidates = []
    for game_dir in sorted(OUTPUT.iterdir()):
        if not game_dir.is_dir():
            continue
        nsf_dir = game_dir / "nsf"
        if not nsf_dir.is_dir():
            continue
        nsfs = sorted(nsf_dir.glob("*.nsf"))
        if not nsfs:
            continue
        slug = game_dir.name
        if args.only and slug not in args.only:
            continue
        if slug in args.skip:
            continue
        candidates.append((slug, nsfs[0]))

    print(f"Found {len(candidates)} games with NSFs under {OUTPUT}")

    # Pre-flight disk check (architecture.md Rule 38).  Refuse to run
    # if the estimated output would fill more than half the free disk.
    if not args.disk_override:
        if not preflight_disk_check(len(candidates), args.seconds, V6):
            sys.exit(2)

    successes = []
    skipped = []
    failures = []

    # Pre-filter: skip candidates that already have RPPs when not --force
    # so the parallel executor never sees them.
    work = []
    for i, (slug, nsf) in enumerate(candidates, 1):
        out_dir = V6 / slug
        reaper_dir = out_dir / "reaper"
        if not args.force and reaper_dir.is_dir():
            existing = list(reaper_dir.glob("*.rpp"))
            if existing:
                print(f"[{i:3d}/{len(candidates)}] {slug}: {len(existing)} RPPs already exist, skipping")
                skipped.append(slug)
                continue
        # Items carry str paths (pickle-safe).
        work.append((i, slug, str(nsf), str(out_dir), str(reaper_dir)))

    total = len(candidates)

    def do_render(item):
        return _render_one(item, args.force, args.seconds,
                           args.numeric_labels, args.m3u_labels, total)

    if args.jobs <= 1:
        results = [do_render(item) for item in work]
    else:
        results = []
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            futures = {ex.submit(_render_one, item, args.force, args.seconds,
                                 args.numeric_labels, args.m3u_labels,
                                 total): item
                       for item in work}
            for fut in as_completed(futures):
                results.append(fut.result())

    for slug, status, detail in results:
        if status == "ok":
            print(f"            ok, {detail} songs -> {slug}", flush=True)
            successes.append(slug)
        else:
            print(f"            FAILED (exit {detail}) -> {slug}", flush=True)
            failures.append((slug, f"exit_{detail}"))

    print(f"\nDone. {len(successes)} rendered / {len(skipped)} skipped / {len(failures)} failed.")
    if failures:
        print("Failures:")
        for slug, why in failures:
            print(f"  {slug}: {why}")


if __name__ == "__main__":
    main()
