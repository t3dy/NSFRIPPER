#!/usr/bin/env python3
"""Deterministic audit of outputv6 track names vs rendered audio.

For every rendered song in outputv6/, compares:

  1. M3U-declared name for the NSF track
  2. Current filename slug
  3. Sidecar track.json (if present) — source of truth for what NSF
     track the stems actually contain

Classifies each song into one of:

  correct            — sidecar matches M3U at declared position,
                       name and duration match
  rename_only        — audio is from the correct NSF track but the
                       filename carries a wrong or stale name
  re_render_required — audio was rendered from the WRONG NSF track
                       (sidecar mismatch OR duration mismatch large
                       enough to prove a shifted track)
  truncated          — correct track, rendered much shorter than M3U
                       declared (silence/stuck truncation)
  m3u_missing        — no M3U found for the game
  ambiguous          — signals disagree; requires human
  unaudited          — no sidecar AND no M3U → cannot decide safely

Usage:
    python scripts/audit_names.py                   # print summary
    python scripts/audit_names.py --only Metroid    # one game
    python scripts/audit_names.py --json OUT.json   # machine output
    python scripts/audit_names.py --csv OUT.csv     # spreadsheet
    python scripts/audit_names.py --verbose         # per-song detail

Outputs (stable CSV columns):
    game, song_dir, m3u_position, nsf_track_sidecar,
    nsf_track_expected, expected_name, current_name,
    actual_seconds, expected_seconds, issue_type, action

"issue_type" is always exactly one of the categories listed above.
"action" is one of:
    none, rename_only, re_render, manual_review
"""
import argparse
import csv
import json
import re
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUTPUT = REPO / "output"
V6 = REPO / "outputv6"


def parse_m3u(path):
    """Return ordered list of {num, name, seconds} from M3U."""
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
            if num < 1:
                continue
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
            tracks.append({"num": num, "name": name,
                           "seconds": max(seconds, 10.0)})
    return tracks


def find_m3u(game_dir):
    nsf_dir = game_dir / "nsf"
    if not nsf_dir.is_dir():
        return None
    for p in sorted(nsf_dir.glob("*.m3u")):
        return p
    return None


def wav_duration(path):
    try:
        with wave.open(str(path)) as w:
            return w.getnframes() / w.getframerate()
    except Exception:
        return None


def parse_song_dir_name(song_dir_name):
    """Extract (m3u_position, filename_slug) from a song dir name.

    Examples:
      '01_Song_01' -> (1, 'Song_01')
      '03_Song_08' -> (3, 'Song_08')  (numeric-labels: position 3, NSF 8)
      '16_Battle_Scene' -> (16, 'Battle_Scene')
    """
    m = re.match(r"^(\d+)_(.+)$", song_dir_name)
    if not m:
        return None, song_dir_name
    return int(m.group(1)), m.group(2)


def slug_equal(a, b):
    """Loose slug equality ignoring punctuation and case."""
    norm = lambda s: re.sub(r"[^A-Za-z0-9]+", "", s or "").lower()
    return norm(a) == norm(b)


def audit_one_song(song_dir, m3u_tracks, tolerance_dur=0.10,
                   min_dur_for_check=10.0):
    """Audit a single song dir.  Returns dict keyed by audit schema."""
    position, filename_slug = parse_song_dir_name(song_dir.name)

    sidecar_path = song_dir / "track.json"
    sidecar = None
    if sidecar_path.is_file():
        try:
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except Exception:
            sidecar = None

    p1 = song_dir / "pulse1.wav"
    actual_sec = wav_duration(p1) if p1.is_file() else None

    expected_m3u = None
    if m3u_tracks and position is not None and 1 <= position <= len(m3u_tracks):
        expected_m3u = m3u_tracks[position - 1]

    row = {
        "song_dir": song_dir.name,
        "m3u_position": position,
        "nsf_track_sidecar": sidecar["nsf_track"] if sidecar else None,
        "nsf_track_expected": expected_m3u["num"] if expected_m3u else None,
        "expected_name": expected_m3u["name"] if expected_m3u else None,
        "current_name": sidecar["name"] if sidecar else filename_slug,
        "actual_seconds": round(actual_sec, 2) if actual_sec else None,
        "expected_seconds": round(expected_m3u["seconds"], 2) if expected_m3u else None,
        "sidecar_present": sidecar is not None,
        "pipeline_version": sidecar.get("pipeline_version") if sidecar else None,
        "issue_type": None,
        "action": "none",
    }

    # Classification
    if expected_m3u is None:
        row["issue_type"] = "m3u_missing" if m3u_tracks is None else "ambiguous"
        row["action"] = "manual_review"
        return row

    # We have an M3U expectation for this position.
    if sidecar is None:
        # Legacy output (pre-2026-04-19 pipeline).  We can't prove the
        # audio matches the M3U position without re-rendering.  Safest
        # call is re_render_required -- the pre-fix pipeline had the
        # off-by-one bug that made most legacy stems wrong.
        row["issue_type"] = "re_render_required"
        row["action"] = "re_render"
        row["_detail"] = "no sidecar, pre-fix pipeline"
        return row

    # Sidecar present.  Check nsf_track alignment.
    if sidecar["nsf_track"] != expected_m3u["num"]:
        row["issue_type"] = "re_render_required"
        row["action"] = "re_render"
        row["_detail"] = (
            f"sidecar says NSF track {sidecar['nsf_track']}, "
            f"M3U position {position} wants NSF track {expected_m3u['num']}"
        )
        return row

    # Audio track is correct.  Check duration if M3U says > min_dur_for_check.
    expected_dur = expected_m3u["seconds"]
    if actual_sec is None:
        row["issue_type"] = "ambiguous"
        row["action"] = "manual_review"
        row["_detail"] = "no pulse1.wav to measure"
        return row
    seconds_cap = sidecar.get("seconds_cap", 180.0)
    capped_expected = min(expected_dur, seconds_cap)
    if (capped_expected > min_dur_for_check
            and actual_sec < capped_expected * (1.0 - tolerance_dur)):
        row["issue_type"] = "truncated"
        row["action"] = "re_render"
        row["_detail"] = (
            f"rendered {actual_sec:.1f}s, expected {capped_expected:.1f}s"
        )
        return row

    # Name check.  The sidecar's name is what the pipeline decided.
    # Does it match M3U's name for this track?  (Only matters when the
    # render used M3U labels, not numeric labels.)
    name_matches_m3u = slug_equal(sidecar["name"], expected_m3u["name"])
    if (sidecar.get("name_source") == "m3u"
            and not name_matches_m3u):
        # Sidecar says m3u but name doesn't match -- odd but recoverable
        # by rename_only.
        row["issue_type"] = "rename_only"
        row["action"] = "rename_only"
        row["_detail"] = (
            f"sidecar name '{sidecar['name']}' != "
            f"M3U name '{expected_m3u['name']}'"
        )
        return row

    # Filename vs sidecar name.  If sidecar name matches M3U but the
    # filename slug doesn't (e.g. stale file from pre-fix), that's
    # rename_only.
    if (not slug_equal(filename_slug.replace("Song_", ""), expected_m3u["name"])
            and sidecar.get("name_source") not in ("numeric_fallback",)
            and not slug_equal(sidecar["name"], filename_slug)):
        row["issue_type"] = "rename_only"
        row["action"] = "rename_only"
        row["_detail"] = (
            f"filename slug '{filename_slug}' doesn't match sidecar "
            f"name '{sidecar['name']}'"
        )
        return row

    row["issue_type"] = "correct"
    row["action"] = "none"
    return row


def audit_game(game_dir):
    slug = game_dir.name
    out_dir = V6 / slug
    stems_root = out_dir / "stems"

    rows = []
    if not stems_root.is_dir():
        return rows  # not rendered yet

    m3u = find_m3u(game_dir)
    m3u_tracks = parse_m3u(m3u) if m3u else None

    for song_dir in sorted(stems_root.iterdir()):
        if not song_dir.is_dir():
            continue
        row = audit_one_song(song_dir, m3u_tracks)
        row["game"] = slug
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--json", type=Path)
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--tolerance", type=float, default=0.10,
                    help="Duration tolerance (0.10 = 10%%)")
    args = ap.parse_args()

    game_dirs = sorted(p for p in OUTPUT.iterdir()
                       if p.is_dir() and (p / "nsf").is_dir())
    if args.only:
        game_dirs = [g for g in game_dirs if g.name in args.only]

    all_rows = []
    for game_dir in game_dirs:
        rows = audit_game(game_dir)
        all_rows.extend(rows)

    by_type = {}
    by_action = {}
    by_game_issue = {}
    for r in all_rows:
        by_type[r["issue_type"]] = by_type.get(r["issue_type"], 0) + 1
        by_action[r["action"]] = by_action.get(r["action"], 0) + 1
        if r["issue_type"] != "correct":
            by_game_issue.setdefault(r["game"], []).append(r)

    print(f"Audited {len(all_rows)} songs across {len(game_dirs)} games.\n")
    print("By issue type:")
    for k in sorted(by_type):
        print(f"  {k:22} {by_type[k]:5}")
    print("\nBy action:")
    for k in sorted(by_action):
        print(f"  {k:22} {by_action[k]:5}")

    if args.verbose:
        print("\n== Flagged songs ==")
        for game, rows in sorted(by_game_issue.items()):
            print(f"\n{game}:")
            for r in rows:
                detail = f"  [{r.get('_detail', '')}]" if r.get("_detail") else ""
                print(f"  {r['song_dir']:30}  {r['issue_type']:22}  "
                      f"{r['action']}{detail}")

    if args.csv:
        fields = [
            "game", "song_dir", "m3u_position", "nsf_track_sidecar",
            "nsf_track_expected", "expected_name", "current_name",
            "actual_seconds", "expected_seconds", "sidecar_present",
            "pipeline_version", "issue_type", "action",
        ]
        with open(args.csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for r in all_rows:
                w.writerow(r)
        print(f"\nCSV report: {args.csv}")

    if args.json:
        args.json.write_text(
            json.dumps({"songs": all_rows,
                        "summary": {"by_type": by_type,
                                    "by_action": by_action}}, indent=2),
            encoding="utf-8",
        )
        print(f"JSON report: {args.json}")


if __name__ == "__main__":
    main()
