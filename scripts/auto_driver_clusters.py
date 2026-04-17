#!/usr/bin/env python3
"""Find all driver code-identity clusters across the full NSF library.

For each game, extract N bytes from init_addr and play_addr. Group games
by matching prefix. This finds every shared-driver cluster without
hypothesizing them first.

Strategy:
1. Read init+play routines from every NSF
2. Build a hash-by-prefix index at multiple prefix lengths (8/16/32 bytes)
3. Report clusters of 2+ games at each prefix length
4. Cross-reference with publishers/composers (from NSF header) to name
   the driver families
"""
import struct
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"


def read_header_and_routines(nsf_path, bytes_each=128):
    try:
        with open(nsf_path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    if data[:5] != b"NESM\x1A":
        return None

    total_songs = data[0x06]
    load_addr = struct.unpack("<H", data[0x08:0x0A])[0]
    init_addr = struct.unpack("<H", data[0x0A:0x0C])[0]
    play_addr = struct.unpack("<H", data[0x0C:0x0E])[0]
    title = data[0x0E:0x2E].rstrip(b"\x00").decode("latin-1", errors="replace").strip()
    artist = data[0x2E:0x4E].rstrip(b"\x00").decode("latin-1", errors="replace").strip()
    copy = data[0x4E:0x6E].rstrip(b"\x00").decode("latin-1", errors="replace").strip()
    expansion = data[0x7B]

    rom = data[0x80:]
    init_off = init_addr - load_addr
    play_off = play_addr - load_addr

    init_bytes = None
    play_bytes = None
    if 0 <= init_off < len(rom):
        init_bytes = rom[init_off:init_off + bytes_each]
    if 0 <= play_off < len(rom):
        play_bytes = rom[play_off:play_off + bytes_each]

    return {
        "total_songs": total_songs,
        "load_addr": load_addr,
        "init_addr": init_addr,
        "play_addr": play_addr,
        "title": title,
        "artist": artist,
        "copyright": copy,
        "expansion_byte": expansion,
        "init_bytes": init_bytes,
        "play_bytes": play_bytes,
    }


def cluster_by_prefix(games_info, routine_key, prefix_len):
    """Group games by matching first `prefix_len` bytes of the named routine."""
    clusters = defaultdict(list)
    for slug, info in games_info.items():
        routine = info.get(routine_key)
        if routine is None or len(routine) < prefix_len:
            continue
        key = routine[:prefix_len]
        # Skip bad keys: all-same-byte (often zero-padding or erased)
        if len(set(key)) == 1:
            continue
        clusters[key].append(slug)
    return {k: v for k, v in clusters.items() if len(v) >= 2}


def main():
    game_dirs = sorted([d for d in OUTPUT_DIR.iterdir() if d.is_dir() and (d / "nsf").is_dir()])
    print(f"Scanning {len(game_dirs)} games...\n", flush=True)

    games_info = {}
    for gd in game_dirs:
        nsf_dir = gd / "nsf"
        nsfs = list(nsf_dir.glob("*.nsf"))
        if not nsfs:
            continue
        info = read_header_and_routines(nsfs[0])
        if info:
            games_info[gd.name] = info

    print(f"Read NSF headers for {len(games_info)} games\n")

    # Try multiple prefix lengths — longer = stricter code identity
    for prefix_len in [32, 16, 8]:
        init_clusters = cluster_by_prefix(games_info, "init_bytes", prefix_len)
        play_clusters = cluster_by_prefix(games_info, "play_bytes", prefix_len)

        init_games = sum(len(v) for v in init_clusters.values())
        play_games = sum(len(v) for v in play_clusters.values())

        print(f"=== Prefix length: {prefix_len} bytes ===")
        print(f"  Init clusters: {len(init_clusters)} covering {init_games} games")
        print(f"  Play clusters: {len(play_clusters)} covering {play_games} games\n")

    # Detailed report at 16-byte prefix (sweet spot: strict but catches variants)
    print(f"\n=== DETAILED: Init clusters at 16-byte prefix ===\n")
    init_clusters = cluster_by_prefix(games_info, "init_bytes", 16)
    sorted_clusters = sorted(init_clusters.items(), key=lambda x: -len(x[1]))

    for i, (prefix, slugs) in enumerate(sorted_clusters):
        if len(slugs) < 2:
            continue
        artists = [games_info[s]["artist"] or "?" for s in slugs]
        distinct_artists = set(a for a in artists if a and a != "<?>")
        expansion_flags = set(games_info[s]["expansion_byte"] for s in slugs)

        print(f"Cluster {i+1}: {prefix.hex()} — {len(slugs)} games")
        print(f"  Expansion: {[f'0x{e:02X}' for e in expansion_flags]}")
        print(f"  Distinct artists: {sorted(distinct_artists) or ['(all unknown)']}")
        for s in sorted(slugs):
            artist = games_info[s]["artist"] or "?"
            print(f"    {s:<48s} [{artist[:35]}]")
        print()

    # Also look at play-routine clusters — sometimes play code is more
    # shared than init (init sets up driver-specific state, play is the
    # per-frame runner)
    print(f"\n=== DETAILED: Play clusters at 16-byte prefix ===\n")
    play_clusters = cluster_by_prefix(games_info, "play_bytes", 16)
    sorted_p = sorted(play_clusters.items(), key=lambda x: -len(x[1]))
    for i, (prefix, slugs) in enumerate(sorted_p[:20]):
        if len(slugs) < 2:
            continue
        artists = [games_info[s]["artist"] or "?" for s in slugs]
        distinct_artists = set(a for a in artists if a and a != "<?>")
        print(f"Cluster {i+1}: {prefix.hex()} — {len(slugs)} games")
        print(f"  Distinct artists: {sorted(distinct_artists)[:5] or ['(all unknown)']}")
        for s in sorted(slugs)[:10]:
            artist = games_info[s]["artist"] or "?"
            print(f"    {s:<48s} [{artist[:35]}]")
        if len(slugs) > 10:
            print(f"    ... and {len(slugs) - 10} more")
        print()


if __name__ == "__main__":
    main()
