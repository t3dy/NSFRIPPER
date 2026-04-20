#!/usr/bin/env python3
"""HiroPlantagenet Layer 2 — enumerate games, tracks, and synths for the UI.

Reads:
  outputv6/<game>/midi/*.mid       — track source (canonical, present for all 113 games)
  outputv6/<game>/stems/           — optional per-channel audio
  outputv6_B/<game>/reaper/*.rpp   — Variant B MIDI+JSFX projects (30 games as of 2026-04-19)
  keyboard_lab/db/keyboard.db      — approaches + presets (synth options)

Writes:
  keyboard_lab/db/ui_library.json  — consumed by the upcoming launcher UI

Read-only wrt source data.  Idempotent.
"""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTV6 = ROOT / "outputv6"
OUTV6B = ROOT / "outputv6_B"
DB_PATH = ROOT / "keyboard_lab" / "db" / "keyboard.db"
OUT_PATH = ROOT / "keyboard_lab" / "db" / "ui_library.json"


def slugify_display(slug: str) -> str:
    return slug.replace("_", " ")


def scan_games() -> list[dict]:
    games: list[dict] = []
    if not OUTV6.exists():
        return games
    for g in sorted(OUTV6.iterdir()):
        if not g.is_dir():
            continue
        midi_dir = g / "midi"
        stems_dir = g / "stems"
        midi_files = sorted(midi_dir.glob("*.mid")) if midi_dir.exists() else []
        if not midi_files:
            continue
        vb_dir = OUTV6B / g.name / "reaper"
        rpp_files = sorted(vb_dir.glob("*.rpp")) if vb_dir.exists() else []
        games.append({
            "slug": g.name,
            "display_name": slugify_display(g.name),
            "n_tracks": len(midi_files),
            "has_stems": stems_dir.exists() and any(stems_dir.iterdir()),
            "has_variant_b_rpp": len(rpp_files) > 0,
            "midi_root": str(midi_dir.relative_to(ROOT)).replace("\\", "/"),
            "rpp_root": str(vb_dir.relative_to(ROOT)).replace("\\", "/") if rpp_files else None,
            "confidence": "high",
        })
    return games


def scan_tracks(game_slug: str) -> list[dict]:
    midi_dir = OUTV6 / game_slug / "midi"
    vb_dir = OUTV6B / game_slug / "reaper"
    tracks: list[dict] = []
    if not midi_dir.exists():
        return tracks
    for mid in sorted(midi_dir.glob("*.mid")):
        # filename format: 01_Song_01.mid
        stem = mid.stem
        parts = stem.split("_", 1)
        idx = 0
        try:
            idx = int(parts[0])
        except (IndexError, ValueError):
            pass
        display = parts[1].replace("_", " ") if len(parts) > 1 else stem
        rpp_match = None
        if vb_dir.exists():
            candidates = list(vb_dir.glob(f"{stem}*.rpp"))
            if candidates:
                rpp_match = str(candidates[0].relative_to(ROOT)).replace("\\", "/")
        tracks.append({
            "track_idx": idx,
            "display_name": display,
            "midi_path": str(mid.relative_to(ROOT)).replace("\\", "/"),
            "rpp_path": rpp_match,
            "confidence": "high",
        })
    return tracks


def scan_synths(db_path: Path) -> list[dict]:
    synths: list[dict] = []
    # JSFX variants on disk, not all tracked in DB yet
    jsfx_dir = ROOT / "studio" / "jsfx"
    if jsfx_dir.exists():
        for jsfx in sorted(jsfx_dir.glob("ReapNES_*.jsfx")):
            # Skip test/clean/backup copies
            name = jsfx.stem
            if any(tag in name for tag in ("_clean_", "_test_", "_backup")):
                continue
            synths.append({
                "id": f"jsfx:{name}",
                "name": name,
                "kind": "jsfx_variant",
                "parent_jsfx": None,
                "pal_coverage_exact_count": None,
                "pal_coverage_approx_count": None,
                "path": str(jsfx.relative_to(ROOT)).replace("\\", "/"),
                "confidence": "high" if name in (
                    "ReapNES_APU2_v2", "ReapNES_Console"
                ) else "low",
            })
    # Approaches + presets from DB
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        # Coverage counts per approach
        cov_by_approach: dict[int, dict[str, int]] = {}
        for row in cur.execute(
            "SELECT approach_id, coverage, COUNT(*) "
            "FROM approach_capabilities GROUP BY approach_id, coverage"
        ):
            aid, cov, n = row
            cov_by_approach.setdefault(aid, {})[cov] = n
        approach_ids: list[tuple[int, str, str]] = list(cur.execute(
            "SELECT id, name, category FROM approaches ORDER BY id"
        ))
        for aid, name, cat in approach_ids:
            cov = cov_by_approach.get(aid, {})
            synths.append({
                "id": f"approach:{aid}",
                "name": name,
                "kind": "approach",
                "parent_jsfx": "ReapNES_APU2_v2" if name.startswith("ReapNES_") else None,
                "category": cat,
                "pal_coverage_exact_count": cov.get("exact", 0),
                "pal_coverage_approx_count": cov.get("approximate", 0),
                "confidence": "high",
            })
        preset_rows = list(cur.execute(
            "SELECT id, approach_id, driver_family, name FROM presets ORDER BY id"
        ))
        for pid, aid, fam, pname in preset_rows:
            synths.append({
                "id": f"preset:{pid}",
                "name": pname,
                "kind": "preset",
                "parent_approach_id": aid,
                "driver_family": fam,
                "confidence": "high",
            })
        conn.close()
    return synths


def main() -> None:
    games = scan_games()
    tracks = {g["slug"]: scan_tracks(g["slug"]) for g in games}
    synths = scan_synths(DB_PATH)
    payload = {
        "_source": "HiroPlantagenet Layer 2 — library enumeration",
        "_generated": "2026-04-19",
        "_root": str(ROOT).replace("\\", "/"),
        "counts": {
            "games": len(games),
            "games_with_rpp": sum(1 for g in games if g["has_variant_b_rpp"]),
            "games_with_stems": sum(1 for g in games if g["has_stems"]),
            "total_tracks": sum(len(v) for v in tracks.values()),
            "synths": len(synths),
            "presets": sum(1 for s in synths if s["kind"] == "preset"),
        },
        "games": games,
        "tracks": tracks,
        "synths": synths,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    print(f"  games={payload['counts']['games']} "
          f"tracks={payload['counts']['total_tracks']} "
          f"synths={payload['counts']['synths']} "
          f"presets={payload['counts']['presets']}")


if __name__ == "__main__":
    main()
