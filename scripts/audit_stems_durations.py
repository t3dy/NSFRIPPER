#!/usr/bin/env python3
"""Audit outputv6 stem durations against M3U-declared track lengths.

Walks every outputv6/<game>/stems/<song>/pulse1.wav, reads its duration,
and compares to the M3U-declared length for that track.  Flags any song
that rendered shorter than 90% of its M3U duration — those are
candidates for re-rendering (usually a silence / stuck / off-by-one
truncation).

Usage:
    python scripts/audit_stems_durations.py                      # all games
    python scripts/audit_stems_durations.py --only Metroid       # one game
    python scripts/audit_stems_durations.py --tolerance 0.05     # 5% tolerance
    python scripts/audit_stems_durations.py --json out.json      # machine output
    python scripts/audit_stems_durations.py --fix                # auto re-render flagged

Requires the M3U file for each game to be at
``output/<game>/nsf/*.m3u`` (as set up by import_zophar_nsfs.py).

NOTE: --fix triggers a `python scripts/batch_stems_project.py` subprocess
per flagged game, using --force and --numeric-labels with --seconds 180.
"""
import argparse
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUTPUT = REPO / "output"
V6 = REPO / "outputv6"


def parse_m3u(path: Path):
    """Return list of {num, name, seconds, position} from an M3U."""
    tracks = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            m = re.match(r".*::NSF,(\d+),([^,]*),([^,]*)", line)
            if not m:
                continue
            num = int(m.group(1))
            name = m.group(2).strip() or f"Song_{num}"
            dur = m.group(3).strip()
            seconds = 90.0
            try:
                parts = dur.split(":")
                if len(parts) == 3:
                    seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                elif len(parts) == 2:
                    seconds = int(parts[0]) * 60 + float(parts[1])
                elif len(parts) == 1 and parts[0]:
                    seconds = float(parts[0])
            except Exception:
                pass
            tracks.append({
                "num": num, "name": name,
                "seconds": max(seconds, 10),  # 10 s floor matches batch_stems
                "position": len(tracks) + 1,
            })
    return tracks


def wav_duration(path: Path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def audit_game(game_dir: Path, tolerance: float, cap_seconds: float):
    """Return (issues, all_data) for one game.

    An "issue" is a song rendered to <tolerance fraction of its M3U
    duration (e.g. 0.9 means must reach 90%).  Songs hitting the
    --seconds cap are not considered issues.
    """
    slug = game_dir.name
    out_dir = V6 / slug
    stems_root = out_dir / "stems"
    if not stems_root.is_dir():
        return [{"game": slug, "why": "no_stems_dir"}], []

    # Locate M3U
    nsf_dir = game_dir / "nsf"
    m3u = None
    if nsf_dir.is_dir():
        for p in nsf_dir.glob("*.m3u"):
            m3u = p
            break
    if not m3u:
        return [{"game": slug, "why": "no_m3u"}], []

    m3u_tracks = parse_m3u(m3u)
    if not m3u_tracks:
        return [{"game": slug, "why": "m3u_empty"}], []

    song_dirs = sorted(stems_root.iterdir())
    issues = []
    all_data = []
    for idx, song_dir in enumerate(song_dirs):
        p1 = song_dir / "pulse1.wav"
        if not p1.is_file():
            continue
        actual = wav_duration(p1)
        # Match this rendered song to its M3U entry by position (the
        # batch pipeline preserves M3U order as 01_, 02_, ...).
        if idx >= len(m3u_tracks):
            continue
        m3u_entry = m3u_tracks[idx]
        expected = min(m3u_entry["seconds"], cap_seconds)
        ratio = actual / expected if expected > 0 else 1.0
        all_data.append({
            "game": slug,
            "song_dir": song_dir.name,
            "nsf_track": m3u_entry["num"],
            "m3u_name": m3u_entry["name"],
            "actual_s": round(actual, 1),
            "expected_s": round(expected, 1),
            "ratio": round(ratio, 3),
        })
        if ratio < tolerance and expected - actual > 3.0:
            issues.append(all_data[-1])
    return issues, all_data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--tolerance", type=float, default=0.9,
                    help="Min ratio of actual/expected before flagging (default 0.9 = 90%%)")
    ap.add_argument("--cap", type=float, default=180.0,
                    help="--seconds cap used for the render (so songs legitimately "
                         "truncated at this cap don't get flagged)")
    ap.add_argument("--json", type=Path, help="Write machine-readable JSON report")
    ap.add_argument("--fix", action="store_true",
                    help="For each flagged game, re-render the whole game via batch_stems_project")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    all_issues = []
    all_ok = []
    game_dirs = sorted([p for p in OUTPUT.iterdir()
                        if p.is_dir() and (p / "nsf").is_dir()])
    if args.only:
        game_dirs = [p for p in game_dirs if p.name in args.only]

    print(f"Auditing {len(game_dirs)} games (tol={args.tolerance*100:.0f}%, cap={args.cap:.0f}s)\n")

    for game_dir in game_dirs:
        issues, data = audit_game(game_dir, args.tolerance, args.cap)
        if args.verbose and data:
            print(f"{game_dir.name}:")
            for d in data:
                marker = " *FLAG*" if d in issues else ""
                print(f"  {d['song_dir']:30}  actual={d['actual_s']:6.1f}s  "
                      f"expected={d['expected_s']:6.1f}s  ratio={d['ratio']:.2f}{marker}")
        if issues:
            all_issues.extend(issues)
        else:
            all_ok.append(game_dir.name)

    print(f"\n== Summary ==")
    print(f"Games with all tracks at >= {int(args.tolerance*100)}% of expected: {len(all_ok)}")
    print(f"Games with at least one truncated track: "
          f"{len({i.get('game') for i in all_issues})}")
    print(f"Total truncated tracks: {len(all_issues)}")
    if all_issues:
        print("\nFlagged tracks:")
        for i in all_issues:
            if "why" in i:
                print(f"  {i['game']:40}  [{i['why']}]")
            else:
                print(f"  {i['game']:30} {i['song_dir']:26}  "
                      f"{i['actual_s']:5.1f}s / {i['expected_s']:5.1f}s  "
                      f"= {i['ratio']*100:4.0f}%")

    if args.json:
        args.json.write_text(json.dumps(
            {"flagged": all_issues, "ok_games": all_ok}, indent=2))
        print(f"\nJSON report: {args.json}")

    if args.fix and all_issues:
        games_to_fix = sorted({i["game"] for i in all_issues if "why" not in i})
        print(f"\n--fix: re-rendering {len(games_to_fix)} games")
        for slug in games_to_fix:
            nsfs = list((OUTPUT / slug / "nsf").glob("*.nsf"))
            if not nsfs:
                print(f"  {slug}: NO NSF, skipping")
                continue
            out_dir = V6 / slug
            print(f"  {slug}: re-rendering...")
            import shutil
            if out_dir.is_dir():
                for sub in ("reaper", "stems", "midi", "_nsf_extract"):
                    target = out_dir / sub
                    if target.is_dir():
                        try:
                            shutil.rmtree(target)
                        except OSError:
                            pass
            log = V6 / f"_log_{slug}.log"
            with open(log, "w", encoding="utf-8") as lf:
                subprocess.run(
                    [sys.executable, "scripts/batch_stems_project.py",
                     str(nsfs[0]),
                     "--seconds", str(args.cap),
                     "--out-dir", str(out_dir),
                     "--numeric-labels"],
                    stdout=lf, stderr=subprocess.STDOUT, cwd=str(REPO))


if __name__ == "__main__":
    main()
