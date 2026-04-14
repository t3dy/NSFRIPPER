#!/usr/bin/env python3
"""Scan NSF files for expansion audio chip flags.

Reads the expansion byte at NSF header offset 0x7B for every NSF file
in the output directory. Reports per-chip game counts and full game
lists as JSON.

NSF header expansion byte (offset 0x7B):
    Bit 0: VRC6  (Konami, ~24 games — 2 pulse + 1 saw)
    Bit 1: VRC7  (Konami, 1 game — 6-ch FM synthesis)
    Bit 2: FDS   (Nintendo, ~200 games — 1 wavetable + mod)
    Bit 3: MMC5  (Nintendo, ~3 games — 2 pulse + 1 PCM)
    Bit 4: N163  (Namco, ~19 games — 1-8 wavetable)
    Bit 5: 5B    (Sunsoft, 1 game — 3 square + noise + env)

Reference: https://www.nesdev.org/wiki/NSF

Usage:
    python scripts/expansion_detect.py                     # scan all, print summary
    python scripts/expansion_detect.py --json              # output full JSON report
    python scripts/expansion_detect.py --json -o report.json  # save to file
    python scripts/expansion_detect.py --chip fds          # list only FDS games
"""

import argparse
import json
import os
import struct
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"

# Expansion chip definitions keyed by bit position
EXPANSION_CHIPS = {
    0: {"name": "VRC6", "manufacturer": "Konami",
        "channels": "2 pulse (8 duty) + 1 sawtooth",
        "cc12_compat": "breaks (8 duty settings vs 4)"},
    1: {"name": "VRC7", "manufacturer": "Konami",
        "channels": "6 FM (OPLL/YM2413)",
        "cc12_compat": "breaks (FM synthesis)"},
    2: {"name": "FDS", "manufacturer": "Nintendo",
        "channels": "1 wavetable (64×6-bit) + modulation",
        "cc12_compat": "N/A (wavetable, no duty)"},
    3: {"name": "MMC5", "manufacturer": "Nintendo",
        "channels": "2 pulse (mirrors APU) + 1 PCM",
        "cc12_compat": "compatible (same duty model)"},
    4: {"name": "N163", "manufacturer": "Namco",
        "channels": "1-8 wavetable (shared 128B RAM)",
        "cc12_compat": "N/A (wavetable, no duty)"},
    5: {"name": "5B", "manufacturer": "Sunsoft",
        "channels": "3 square + noise + HW envelope (YM2149)",
        "cc12_compat": "N/A (square only, no duty)"},
}


def read_nsf_header(path):
    """Read NSF header and return parsed metadata.

    Returns dict with expansion flags, track count, game name, etc.
    Returns None if file is not a valid NSF.
    """
    try:
        with open(path, "rb") as f:
            header = f.read(128)
    except (IOError, OSError):
        return None

    if len(header) < 128:
        return None

    magic = header[0:5]
    if magic not in (b"NESM\x1a", b"NSFE"):
        return None

    # NSF header fields
    version = header[5]
    total_songs = header[6]
    starting_song = header[7]
    load_addr = struct.unpack_from("<H", header, 0x08)[0]
    init_addr = struct.unpack_from("<H", header, 0x0A)[0]
    play_addr = struct.unpack_from("<H", header, 0x0C)[0]
    game_name = header[0x0E:0x2E].split(b"\x00")[0].decode("ascii", errors="replace").strip()
    artist = header[0x2E:0x4E].split(b"\x00")[0].decode("ascii", errors="replace").strip()
    copyright_str = header[0x4E:0x6E].split(b"\x00")[0].decode("ascii", errors="replace").strip()
    expansion = header[0x7B]

    # Decode expansion bits
    chips = []
    for bit, chip_info in EXPANSION_CHIPS.items():
        if expansion & (1 << bit):
            chips.append(chip_info["name"])

    return {
        "path": str(path),
        "magic": magic.decode("ascii", errors="replace"),
        "version": version,
        "total_songs": total_songs,
        "game_name": game_name,
        "artist": artist,
        "copyright": copyright_str,
        "expansion_byte": expansion,
        "expansion_chips": chips,
        "is_standard_only": expansion == 0,
    }


def scan_output_directory(output_dir=None):
    """Scan all NSF files in output/<Game>/nsf/ directories.

    Returns list of parsed header dicts.
    """
    if output_dir is None:
        output_dir = OUTPUT_DIR

    results = []
    output_path = Path(output_dir)

    if not output_path.exists():
        print(f"Error: output directory not found: {output_path}", file=sys.stderr)
        return results

    # Walk all game directories
    for game_dir in sorted(output_path.iterdir()):
        if not game_dir.is_dir():
            continue
        nsf_dir = game_dir / "nsf"
        if not nsf_dir.is_dir():
            continue

        for nsf_file in sorted(nsf_dir.glob("*.nsf")):
            info = read_nsf_header(nsf_file)
            if info is not None:
                info["game_slug"] = game_dir.name
                results.append(info)

    return results


def build_report(results):
    """Build structured report from scan results.

    Returns dict with:
        - summary: per-chip counts
        - per_chip: game lists per chip
        - standard_only: games with no expansion
        - multi_chip: games using multiple expansion chips
        - total_games: count of all NSFs scanned
        - total_songs: sum of all track counts
    """
    per_chip = defaultdict(list)
    standard_only = []
    multi_chip = []

    for info in results:
        if info["is_standard_only"]:
            standard_only.append({
                "game_slug": info["game_slug"],
                "game_name": info["game_name"],
                "total_songs": info["total_songs"],
            })
        else:
            for chip in info["expansion_chips"]:
                per_chip[chip].append({
                    "game_slug": info["game_slug"],
                    "game_name": info["game_name"],
                    "total_songs": info["total_songs"],
                    "expansion_byte": f"0x{info['expansion_byte']:02X}",
                    "all_chips": info["expansion_chips"],
                })
            if len(info["expansion_chips"]) > 1:
                multi_chip.append({
                    "game_slug": info["game_slug"],
                    "game_name": info["game_name"],
                    "chips": info["expansion_chips"],
                })

    # Summary counts
    summary = {}
    for bit, chip_info in EXPANSION_CHIPS.items():
        name = chip_info["name"]
        summary[name] = {
            "count": len(per_chip.get(name, [])),
            "manufacturer": chip_info["manufacturer"],
            "channels": chip_info["channels"],
            "cc12_compat": chip_info["cc12_compat"],
        }

    total_songs = sum(info["total_songs"] for info in results)

    return {
        "scan_date": "2026-04-13",
        "total_nsfs_scanned": len(results),
        "total_songs_across_all_games": total_songs,
        "standard_only_count": len(standard_only),
        "expansion_count": len(results) - len(standard_only),
        "multi_chip_count": len(multi_chip),
        "summary": summary,
        "per_chip": {k: v for k, v in sorted(per_chip.items())},
        "multi_chip_games": multi_chip,
        "standard_only_games": standard_only,
    }


def print_summary(report):
    """Print human-readable summary to stdout."""
    print(f"NSF Expansion Audio Audit")
    print(f"=" * 60)
    print(f"Total NSFs scanned:    {report['total_nsfs_scanned']}")
    print(f"Total songs:           {report['total_songs_across_all_games']}")
    print(f"Standard APU only:     {report['standard_only_count']}")
    print(f"With expansion audio:  {report['expansion_count']}")
    print(f"Multi-chip:            {report['multi_chip_count']}")
    print()

    print("Per-Chip Breakdown:")
    print("-" * 60)
    for name, info in sorted(report["summary"].items(),
                              key=lambda x: x[1]["count"], reverse=True):
        count = info["count"]
        if count == 0:
            continue
        mfg = info["manufacturer"]
        channels = info["channels"]
        compat = info["cc12_compat"]
        print(f"  {name:6s} ({mfg:10s}): {count:3d} games  |  {channels}")
        print(f"         CC12 compat: {compat}")
    print()

    # Show zero-count chips too
    zero_chips = [name for name, info in report["summary"].items()
                  if info["count"] == 0]
    if zero_chips:
        print(f"  No games found for: {', '.join(zero_chips)}")
        print()

    if report["multi_chip_games"]:
        print("Multi-Chip Games:")
        print("-" * 60)
        for g in report["multi_chip_games"]:
            print(f"  {g['game_slug']:40s} [{', '.join(g['chips'])}]")
        print()

    # Per-chip game lists
    for chip_name, games in sorted(report["per_chip"].items()):
        print(f"\n{chip_name} Games ({len(games)}):")
        print("-" * 60)
        for g in sorted(games, key=lambda x: x["game_slug"]):
            songs = g["total_songs"]
            print(f"  {g['game_slug']:45s} ({songs:3d} tracks)")


def main():
    parser = argparse.ArgumentParser(
        description="Scan NSF files for expansion audio chip flags"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output full report as JSON"
    )
    parser.add_argument(
        "-o", "--output", type=str, default=None,
        help="Write JSON report to file (implies --json)"
    )
    parser.add_argument(
        "--chip", type=str, default=None,
        choices=["vrc6", "vrc7", "fds", "mmc5", "n163", "5b"],
        help="Filter to show only games using this chip"
    )
    parser.add_argument(
        "--dir", type=str, default=None,
        help="Override output directory to scan"
    )
    args = parser.parse_args()

    scan_dir = args.dir if args.dir else OUTPUT_DIR
    results = scan_output_directory(scan_dir)

    if not results:
        print("No NSF files found.", file=sys.stderr)
        sys.exit(1)

    report = build_report(results)

    if args.output:
        args.json = True

    if args.json:
        output_data = report
        if args.chip:
            chip_upper = args.chip.upper()
            output_data = {
                "chip": chip_upper,
                "count": report["summary"].get(chip_upper, {}).get("count", 0),
                "games": report["per_chip"].get(chip_upper, []),
            }
        json_str = json.dumps(output_data, indent=2, ensure_ascii=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_str + "\n")
            print(f"Report written to {args.output}")
        else:
            print(json_str)
    else:
        if args.chip:
            chip_upper = args.chip.upper()
            games = report["per_chip"].get(chip_upper, [])
            print(f"{chip_upper} Games ({len(games)}):")
            print("-" * 60)
            for g in sorted(games, key=lambda x: x["game_slug"]):
                print(f"  {g['game_slug']:45s} ({g['total_songs']:3d} tracks)")
        else:
            print_summary(report)


if __name__ == "__main__":
    main()
