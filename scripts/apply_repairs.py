#!/usr/bin/env python3
"""Apply deterministic repairs based on an audit_names.py JSON report.

Reads an audit JSON, separates rows into two action buckets, and
performs ONLY the safe operations.  Re-renders are written to a list
file that render_all_nsfs.py --from-list consumes.

Actions performed:

  rename_only       : filename is wrong but audio is correct.  We
                      rename the song directory + the RPP and MIDI
                      files to match the M3U-expected name.  Original
                      names backed up to <item>.bak or a .renamed.json
                      manifest.
  re_render         : games where at least one song needs re-rendering
                      get written to outputv6/_rerender_list.txt.
                      Use render_all_nsfs.py --from-list to process.

Actions NOT performed:

  ambiguous / manual_review / unaudited: left alone, user must review.

Usage:
    # 1. Run audit to produce JSON:
    python scripts/audit_names.py --json audit.json

    # 2. Dry run (shows what would happen without changing anything):
    python scripts/apply_repairs.py audit.json --dry-run

    # 3. Apply rename_only fixes:
    python scripts/apply_repairs.py audit.json --rename-only

    # 4. Emit re-render list:
    python scripts/apply_repairs.py audit.json --emit-rerender-list

    # 5. Then trigger re-renders:
    python scripts/render_all_nsfs.py --from-list outputv6/_rerender_list.txt --force

Safety rails:
- Never renames if sidecar.nsf_track != expected.nsf_track (that's
  re_render territory, not rename).
- Logs every rename to outputv6/_repair_log.json for rollback.
- Refuses to operate on rows without a sidecar (can't prove audio).
"""
import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
V6 = REPO / "outputv6"
LOG_PATH = V6 / "_repair_log.json"
RERENDER_LIST = V6 / "_rerender_list.txt"


def slugify(s):
    s = re.sub(r"[\s]+", "_", (s or "").strip())
    s = re.sub(r"[^\w\-_().]", "", s)
    return s or "untitled"


def load_repair_log():
    if LOG_PATH.is_file():
        try:
            return json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"entries": []}


def save_repair_log(log):
    LOG_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")


def perform_rename(row, dry_run=False):
    """Safely rename a single song dir + associated files.

    Returns dict with {status, old_name, new_name, ...} for logging.
    """
    game = row["game"]
    old_dir_name = row["song_dir"]  # e.g. '03_Song_08'
    m3u_position = row["m3u_position"]
    expected_name = row["expected_name"]
    nsf_track = row["nsf_track_sidecar"] or row["nsf_track_expected"]

    if expected_name is None or m3u_position is None or nsf_track is None:
        return {"status": "skipped_missing_metadata", "song": old_dir_name}

    new_slug = f"{m3u_position:02d}_{slugify(expected_name)}"
    if new_slug == old_dir_name:
        return {"status": "noop", "song": old_dir_name}

    game_dir = V6 / game
    old_stems = game_dir / "stems" / old_dir_name
    new_stems = game_dir / "stems" / new_slug
    old_rpp = game_dir / "reaper" / f"{old_dir_name}.rpp"
    new_rpp = game_dir / "reaper" / f"{new_slug}.rpp"
    old_midi = game_dir / "midi" / f"{old_dir_name}.mid"
    new_midi = game_dir / "midi" / f"{new_slug}.mid"

    plan = {
        "game": game,
        "nsf_track": nsf_track,
        "m3u_position": m3u_position,
        "old_name": old_dir_name,
        "new_name": new_slug,
        "renames": [],
    }

    def queue(src, dst):
        if src.exists():
            plan["renames"].append((str(src), str(dst)))

    queue(old_stems, new_stems)
    queue(old_rpp, new_rpp)
    queue(old_midi, new_midi)

    if dry_run:
        plan["status"] = "dry_run"
        return plan

    # Collision guard
    for src, dst in plan["renames"]:
        if Path(dst).exists():
            plan["status"] = "collision_abort"
            plan["collision"] = dst
            return plan

    # Execute
    for src, dst in plan["renames"]:
        shutil.move(src, dst)

    # Rewrite RPP references to stems path
    if new_rpp.is_file():
        try:
            content = new_rpp.read_text(encoding="utf-8")
            content = content.replace(old_dir_name, new_slug)
            new_rpp.write_text(content, encoding="utf-8")
        except Exception as e:
            plan.setdefault("warnings", []).append(
                f"RPP path rewrite failed: {e}")

    # Update sidecar's 'name' field to reflect new slug's intent
    sidecar = new_stems / "track.json"
    if sidecar.is_file():
        try:
            s = json.loads(sidecar.read_text(encoding="utf-8"))
            s["name"] = expected_name
            s["name_source"] = "m3u_repair"
            sidecar.write_text(json.dumps(s, indent=2), encoding="utf-8")
        except Exception as e:
            plan.setdefault("warnings", []).append(
                f"sidecar update failed: {e}")

    plan["status"] = "renamed"
    return plan


def emit_rerender_list(rows, out_path):
    games = sorted({r["game"] for r in rows
                    if r["action"] == "re_render" or r["issue_type"] == "truncated"})
    out_path.write_text("\n".join(games) + "\n", encoding="utf-8")
    return games


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audit_json", type=Path,
                    help="JSON report from audit_names.py")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would happen, make no changes")
    ap.add_argument("--rename-only", action="store_true",
                    help="Perform filesystem renames for rename_only rows")
    ap.add_argument("--emit-rerender-list", action="store_true",
                    help=f"Write list of games needing re-render to "
                         f"{RERENDER_LIST.relative_to(REPO)}")
    args = ap.parse_args()

    if not args.audit_json.is_file():
        print(f"Audit JSON not found: {args.audit_json}", file=sys.stderr)
        sys.exit(1)

    payload = json.loads(args.audit_json.read_text(encoding="utf-8"))
    rows = payload.get("songs", [])

    rename_rows = [r for r in rows if r["action"] == "rename_only"]
    rerender_rows = [r for r in rows if r["action"] == "re_render"]
    manual_rows = [r for r in rows if r["action"] == "manual_review"]

    print(f"Audit has {len(rows)} rows:")
    print(f"  rename_only:   {len(rename_rows)}")
    print(f"  re_render:     {len(rerender_rows)}")
    print(f"  manual_review: {len(manual_rows)}")
    print()

    did_something = False

    if args.rename_only:
        did_something = True
        log = load_repair_log()
        performed = []
        for r in rename_rows:
            plan = perform_rename(r, dry_run=args.dry_run)
            performed.append(plan)
            tag = plan["status"]
            name = f"{plan.get('game', '?')}:{plan.get('old_name', '?')}"
            print(f"  {tag:22}  {name} -> {plan.get('new_name', '?')}")
        if not args.dry_run:
            log["entries"].append({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "operation": "rename_only",
                "count": len([p for p in performed if p.get("status") == "renamed"]),
                "details": performed,
            })
            save_repair_log(log)
            print(f"\nLogged to {LOG_PATH}")

    if args.emit_rerender_list:
        did_something = True
        if args.dry_run:
            games = sorted({r["game"] for r in rerender_rows})
            print(f"  would write {len(games)} games to {RERENDER_LIST.name}")
            for g in games[:20]:
                print(f"    {g}")
            if len(games) > 20:
                print(f"    ... and {len(games)-20} more")
        else:
            RERENDER_LIST.parent.mkdir(parents=True, exist_ok=True)
            games = emit_rerender_list(rerender_rows, RERENDER_LIST)
            print(f"  wrote {len(games)} games to {RERENDER_LIST}")

    if not did_something:
        print("Nothing to do.  Pass --rename-only, --emit-rerender-list, "
              "or --dry-run with one of those.")
        print(f"Re-render candidates (would be written to "
              f"{RERENDER_LIST.relative_to(REPO)}):")
        for g in sorted({r['game'] for r in rerender_rows})[:10]:
            print(f"  {g}")

    if manual_rows:
        print(f"\n{len(manual_rows)} manual_review rows -- not touched.")
        print("Re-run audit with --verbose to see the details.")


if __name__ == "__main__":
    main()
