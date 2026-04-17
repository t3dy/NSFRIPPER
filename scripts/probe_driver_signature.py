#!/usr/bin/env python3
"""Extract per-driver signatures from a curated set of games.

Looks at raw NSF binaries for driver identification patterns, and at
the first few frames of SysEx to identify the driver's init signature.
"""
import sys
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"


def read_nsf_header(nsf_path):
    """Read NSF header metadata and compute driver signature."""
    with open(nsf_path, "rb") as f:
        data = f.read()

    if data[:5] != b"NESM\x1A":
        return None

    total_songs = data[0x06]
    load_addr = struct.unpack("<H", data[0x08:0x0A])[0]
    init_addr = struct.unpack("<H", data[0x0A:0x0C])[0]
    play_addr = struct.unpack("<H", data[0x0C:0x0E])[0]
    title = data[0x0E:0x2E].rstrip(b"\x00").decode("latin-1", errors="replace")
    artist = data[0x2E:0x4E].rstrip(b"\x00").decode("latin-1", errors="replace")
    copyright_field = data[0x4E:0x6E].rstrip(b"\x00").decode("latin-1", errors="replace")
    ntsc_speed = struct.unpack("<H", data[0x6E:0x70])[0]
    bankswitch = data[0x70:0x78]
    uses_bankswitch = any(b != 0 for b in bankswitch)
    expansion = data[0x7B]

    # Signature: first 32 bytes after init_addr (offset into ROM)
    rom = data[0x80:]
    init_offset = init_addr - load_addr
    signature = None
    if 0 <= init_offset < len(rom) - 32:
        signature = rom[init_offset:init_offset + 32].hex()

    return {
        "file": nsf_path.name,
        "total_songs": total_songs,
        "load_addr": f"${load_addr:04X}",
        "init_addr": f"${init_addr:04X}",
        "play_addr": f"${play_addr:04X}",
        "title": title,
        "artist": artist,
        "copyright": copyright_field,
        "ntsc_speed": ntsc_speed,
        "bankswitch": uses_bankswitch,
        "expansion_byte": f"0x{expansion:02X}",
        "signature_32b": signature,
    }


def find_driver_clusters(game_dirs):
    """Group games by matching signatures."""
    sigs = {}  # first 16 bytes -> list of games
    load_addrs = {}

    for gd in game_dirs:
        nsf_dir = gd / "nsf"
        if not nsf_dir.is_dir():
            continue
        nsfs = list(nsf_dir.glob("*.nsf"))
        if not nsfs:
            continue
        info = read_nsf_header(nsfs[0])
        if info is None:
            continue

        # Short signature (first 16 bytes of init routine)
        short_sig = info["signature_32b"][:32] if info["signature_32b"] else None
        if short_sig:
            sigs.setdefault(short_sig, []).append((gd.name, info))

        la_key = info["load_addr"]
        load_addrs.setdefault(la_key, []).append(gd.name)

    return sigs, load_addrs


def main():
    game_dirs = [d for d in OUTPUT_DIR.iterdir() if d.is_dir() and (d / "nsf").is_dir()]
    print(f"Analyzing {len(game_dirs)} games...\n")

    sigs, load_addrs = find_driver_clusters(game_dirs)

    # Find clusters of 2+ games with matching signatures
    shared_sigs = [(s, games) for s, games in sigs.items() if len(games) >= 2]
    shared_sigs.sort(key=lambda x: -len(x[1]))

    print(f"=== Shared Driver Signatures (2+ games with matching init sig) ===\n")
    print(f"Found {len(shared_sigs)} shared signatures covering {sum(len(g) for _, g in shared_sigs)} games\n")
    for sig, games in shared_sigs[:25]:
        print(f"  Sig {sig[:16]}... ({len(games)} games)")
        for game, info in games[:8]:
            artist = info.get("artist", "")[:30]
            print(f"    {game} [{artist}]")
        if len(games) > 8:
            print(f"    ... and {len(games) - 8} more")
        print()

    # Also by load_addr — tells us common memory layouts
    print(f"\n=== Load Address Distribution ===\n")
    for la, games in sorted(load_addrs.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"  {la}: {len(games)} games")

    # Artist / publisher clusters
    artist_counts = {}
    for gd in game_dirs:
        nsf_dir = gd / "nsf"
        if not nsf_dir.is_dir():
            continue
        nsfs = list(nsf_dir.glob("*.nsf"))
        if not nsfs:
            continue
        info = read_nsf_header(nsfs[0])
        if info:
            artist = info.get("artist", "").strip() or "(unknown)"
            artist_counts.setdefault(artist, []).append(gd.name)

    print(f"\n=== Games by Artist (top 10) ===\n")
    for a, gs in sorted(artist_counts.items(), key=lambda x: -len(x[1]))[:15]:
        print(f"  {a}: {len(gs)}")


if __name__ == "__main__":
    main()
