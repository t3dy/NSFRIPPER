#!/usr/bin/env python3
"""Verify behavioral driver clusters via NSF init-routine byte matching.

We identified driver families by register behavior. This script checks
whether the behavioral clusters also share bytes in their init routines.
If yes: same driver code. If no: same publisher convention but different
codebases.
"""
import struct
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"


def read_init_region(nsf_path, length=256):
    """Return the bytes starting at init_addr, at most `length` bytes."""
    with open(nsf_path, "rb") as f:
        data = f.read()
    if data[:5] != b"NESM\x1A":
        return None
    load_addr = struct.unpack("<H", data[0x08:0x0A])[0]
    init_addr = struct.unpack("<H", data[0x0A:0x0C])[0]
    rom = data[0x80:]
    offset = init_addr - load_addr
    if offset < 0 or offset >= len(rom):
        return None
    return rom[offset:offset + length], init_addr, load_addr


def find_play_region(nsf_path, length=256):
    with open(nsf_path, "rb") as f:
        data = f.read()
    load_addr = struct.unpack("<H", data[0x08:0x0A])[0]
    play_addr = struct.unpack("<H", data[0x0C:0x0E])[0]
    rom = data[0x80:]
    offset = play_addr - load_addr
    if offset < 0 or offset >= len(rom):
        return None
    return rom[offset:offset + length], play_addr


def find_nsf(slug):
    d = OUTPUT_DIR / slug / "nsf"
    if not d.is_dir():
        return None
    nsfs = list(d.glob("*.nsf"))
    return nsfs[0] if nsfs else None


def compare_clusters():
    # Behavioral clusters from register_analysis
    clusters = {
        "Capcom late (confirmed)": [
            "Darkwing_Duck", "Little_Mermaid,_The", "Mega_Man_3", "Mega_Man_4",
            "Mighty_Final_Fight", "TaleSpin",
            "Tenchi_wo_Kurau_II_Shokatsu_Koumei_Den",
        ],
        "Capcom early (hypothesized)": [
            "Mega_Man", "Mega_Man_1", "Mega_Man_2",
            "Bionic_Commando", "Commando", "Ghosts_n_Goblins",
            "Section_Z", "Gun.Smoke",
        ],
        "Nintendo R&D (hypothesized)": [
            "Super_Mario_Bros", "Super_Mario_Bros._2", "Super_Mario_Bros._3",
            "Legend_of_Zelda,_The", "Zelda_II___The_Adventure_of_Link",
            "Punch_Out!!", "Mighty_Bomb_Jack",
        ],
        "Sunsoft (hypothesized)": [
            "Blaster_Master", "Batman", "Journey_to_Silius",
            "Gremlins_2_The_New_Batch", "Festers_Quest",
        ],
        "Konami (hypothesized)": [
            "Castlevania", "Contra", "Gradius",
            "Hyper_Sports", "Road_Fighter",
        ],
    }

    results = {}
    for cluster_name, games in clusters.items():
        print(f"\n=== {cluster_name} ===")
        init_regions = []
        play_regions = []
        for slug in games:
            nsf = find_nsf(slug)
            if not nsf:
                print(f"  {slug}: NSF not found")
                continue
            init = read_init_region(nsf, 64)
            play = find_play_region(nsf, 64)
            if init:
                init_regions.append((slug, init[0]))
            if play:
                play_regions.append((slug, play[0]))

        if len(init_regions) < 2:
            print(f"  Too few NSFs in cluster ({len(init_regions)})")
            continue

        # Find longest common prefix across all init routines
        min_len = min(len(r) for _, r in init_regions)
        common_prefix_len = 0
        for i in range(min_len):
            bytes_at_i = [r[i] for _, r in init_regions]
            if len(set(bytes_at_i)) == 1:
                common_prefix_len += 1
            else:
                break

        # And play routines
        min_len_p = min(len(r) for _, r in play_regions)
        play_prefix_len = 0
        for i in range(min_len_p):
            bytes_at_i = [r[i] for _, r in play_regions]
            if len(set(bytes_at_i)) == 1:
                play_prefix_len += 1
            else:
                break

        # Count byte-position agreement (fraction of positions where all match)
        position_match = 0
        for i in range(min_len):
            bytes_at_i = [r[i] for _, r in init_regions]
            if len(set(bytes_at_i)) == 1:
                position_match += 1

        results[cluster_name] = {
            "games": [s for s, _ in init_regions],
            "init_common_prefix_bytes": common_prefix_len,
            "init_agreement_first_64": position_match,
            "play_common_prefix_bytes": play_prefix_len,
        }

        print(f"  Games compared: {len(init_regions)}")
        print(f"  Init common prefix: {common_prefix_len} bytes")
        print(f"  Init byte-agreement rate: {position_match}/{min_len} positions ({position_match*100/min_len:.0f}%)")
        print(f"  Play common prefix: {play_prefix_len} bytes")
        # Show first 16 bytes of each
        print(f"  First 16 bytes of init routines:")
        for slug, region in init_regions:
            hex_preview = region[:16].hex()
            print(f"    {slug:<42s} {hex_preview}")

    return results


if __name__ == "__main__":
    compare_clusters()
