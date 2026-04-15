#!/usr/bin/env python3
"""Check bankswitch tables for specific NSF files."""

import os
import struct

GAMES = {
    "Ninja Gaiden": r"output\Ninja_Gaiden\nsf\Ninja Gaiden [Ninja Ryukenden] [Shadow Warriors] (1988-12-09)(Tecmo).nsf",
    "Legend of Zelda": r"output\Legend_of_Zelda,_The\nsf\Legend of Zelda, The (1987-08-22)(Nintendo EAD)(Nintendo).nsf",
    "Castlevania 3 (US)": r"output\Castlevania_3___Draculas_Curse\nsf\Castlevania 3 - Dracula's Curse [Akumajou Densetsu] (1989-12-22)(Konami).nsf",
    "Castlevania 3 (JP)": r"output\Castlevania_3___Draculas_Curse_JP\nsf\Castlevania 3 - Dracula's Curse JP [Akumajou Densetsu] (1989-12-22)(Konami).nsf",
    "Double Dribble": r"output\Double_Dribble\nsf\Double Dribble (1987-09)(Konami).nsf",
    "Kings Quest V": r"output\Kings_Quest_V\nsf\King's Quest V (1992-06)(Sierra)(Novotrade)(Konami).nsf",
}

BASE = r"C:\Dev\NSFRIPPER"

EXPANSION_NAMES = {
    0x01: "VRC6",
    0x02: "VRC7",
    0x04: "FDS",
    0x08: "MMC5",
    0x10: "Namco 163",
    0x20: "Sunsoft 5B",
}


def parse_nsf(filepath):
    with open(filepath, "rb") as f:
        data = f.read()

    if data[:5] != b"NESM\x1a":
        return None

    version = data[5]
    total_songs = data[6]
    starting_song = data[7]
    load_addr = struct.unpack_from("<H", data, 0x08)[0]
    init_addr = struct.unpack_from("<H", data, 0x0A)[0]
    play_addr = struct.unpack_from("<H", data, 0x0C)[0]

    song_name = data[0x0E:0x2E].split(b"\x00")[0].decode("ascii", errors="replace")
    artist = data[0x2E:0x4E].split(b"\x00")[0].decode("ascii", errors="replace")

    bankswitch = list(data[0x70:0x78])
    uses_bankswitch = any(b != 0 for b in bankswitch)

    expansion = data[0x7B]
    expansion_chips = []
    for bit, name in EXPANSION_NAMES.items():
        if expansion & bit:
            expansion_chips.append(name)

    # ROM data starts at offset 0x80
    rom_data_size = len(data) - 0x80
    num_4k_pages = rom_data_size // 4096
    leftover = rom_data_size % 4096

    # Load address alignment
    load_offset = load_addr & 0xFFF
    page_aligned = load_offset == 0

    return {
        "version": version,
        "total_songs": total_songs,
        "starting_song": starting_song,
        "load_addr": load_addr,
        "init_addr": init_addr,
        "play_addr": play_addr,
        "song_name": song_name,
        "artist": artist,
        "bankswitch": bankswitch,
        "uses_bankswitch": uses_bankswitch,
        "expansion": expansion,
        "expansion_chips": expansion_chips,
        "rom_data_size": rom_data_size,
        "num_4k_pages": num_4k_pages,
        "leftover_bytes": leftover,
        "page_aligned": page_aligned,
        "load_offset": load_offset,
    }


def slot_mapping(info):
    """Compute the address range for each bankswitch slot."""
    load_addr = info["load_addr"]
    bankswitch = info["bankswitch"]
    uses_bs = info["uses_bankswitch"]

    if not uses_bs:
        return "No bankswitch - linear load at ${:04X}".format(load_addr)

    lines = []

    # Check if load address is in $6000-$7FFF range
    uses_low_ram = load_addr < 0x8000

    if uses_low_ram:
        lines.append("  Load addr < $8000: slots $5FF6/$5FF7 control $6000-$7FFF")
        lines.append("  Slot layout:")
        slot_names = [
            ("$5FF6", "$6000-$6FFF"),
            ("$5FF7", "$7000-$7FFF"),
            ("$5FF8", "$8000-$8FFF"),
            ("$5FF9", "$9000-$9FFF"),
            ("$5FFA", "$A000-$AFFF"),
            ("$5FFB", "$B000-$BFFF"),
            ("$5FFC", "$C000-$CFFF"),
            ("$5FFD", "$D000-$DFFF"),
            ("$5FFE", "$E000-$EFFF"),
            ("$5FFF", "$F000-$FFFF"),
        ]
        # bankswitch[0] = $5FF6 ($6000), bankswitch[1] = $5FF7 ($7000)
        # bankswitch[2] = $5FF8 ($8000), ... bankswitch[7] = $5FFD ($D000)
        # Wait - NSF spec: bankswitch bytes 0-7 map to $5FF8-$5FFF
        # But if load < $8000, bytes 0-1 map to $5FF6-$5FF7 and 2-7 map to $5FF8-$5FFD
        # Actually per spec: bytes at $70-$77 init bankswitch regs $5FF8-$5FFF
        # If load addr in $6000-$7FFF, $70/$71 are for $6000/$7000 and $72-$77 for $8000-$DFFF
        # No wait, let me re-read: the 8 bytes at $70-$77 correspond to:
        #   $70 -> initial value of $5FF8 (maps $8000-$8FFF)
        #   $71 -> initial value of $5FF9 (maps $9000-$9FFF)
        #   ...
        #   $77 -> initial value of $5FFF (maps $F000-$FFFF)
        # If load addr < $8000:
        #   $70 -> $5FF6 (maps $6000-$6FFF)
        #   $71 -> $5FF7 (maps $7000-$7FFF)
        #   $72 -> $5FF8 (maps $8000-$8FFF)
        #   ...
        #   $77 -> $5FFD (maps $D000-$DFFF)
        # and $5FFE/$5FFF are FIXED to the last two pages

        for i, (reg, addr_range) in enumerate(slot_names[:8]):
            if i < len(bankswitch):
                lines.append(
                    f"    BS[{i}] = {bankswitch[i]:3d} (0x{bankswitch[i]:02X}) -> {reg} -> {addr_range}"
                )
        lines.append("    $5FFE/$5FFF ($E000-$FFFF): fixed to last 2 pages")
    else:
        lines.append("  Load addr >= $8000: standard mapping")
        lines.append("  Slot layout:")
        # Standard: $70-$77 -> $5FF8-$5FFF -> $8000-$FFFF
        slot_addrs = [
            ("$5FF8", "$8000-$8FFF"),
            ("$5FF9", "$9000-$9FFF"),
            ("$5FFA", "$A000-$AFFF"),
            ("$5FFB", "$B000-$BFFF"),
            ("$5FFC", "$C000-$CFFF"),
            ("$5FFD", "$D000-$DFFF"),
            ("$5FFE", "$E000-$EFFF"),
            ("$5FFF", "$F000-$FFFF"),
        ]
        for i, (reg, addr_range) in enumerate(slot_addrs):
            lines.append(
                f"    BS[{i}] = {bankswitch[i]:3d} (0x{bankswitch[i]:02X}) -> {reg} -> {addr_range}"
            )

    return "\n".join(lines)


def main():
    print("=" * 90)
    print("NSF BANKSWITCH TABLE ANALYSIS")
    print("=" * 90)

    for game_name, rel_path in GAMES.items():
        filepath = os.path.join(BASE, rel_path)

        if not os.path.exists(filepath):
            print(f"\n{'=' * 70}")
            print(f"  {game_name}: FILE NOT FOUND")
            print(f"  Path: {filepath}")
            continue

        info = parse_nsf(filepath)
        if info is None:
            print(f"\n  {game_name}: NOT A VALID NSF FILE")
            continue

        print(f"\n{'-' * 90}")
        print(f"  GAME: {game_name}")
        print(f"  File: {os.path.basename(filepath)}")
        print(f"  Song: {info['song_name']}")
        print(f"  Artist: {info['artist']}")
        print(f"  Songs: {info['total_songs']}")
        print(f"{'-' * 90}")

        print(f"  Load addr:  ${info['load_addr']:04X}    (offset within page: 0x{info['load_offset']:03X})")
        print(f"  Init addr:  ${info['init_addr']:04X}")
        print(f"  Play addr:  ${info['play_addr']:04X}")
        print(f"  Page-aligned: {'YES' if info['page_aligned'] else 'NO  *** NEEDS ADJUSTMENT ***'}")

        print(f"\n  Bankswitch table (bytes $70-$77):")
        bs = info["bankswitch"]
        print(f"    Raw: [{', '.join(f'{b:3d}' for b in bs)}]")
        print(f"    Hex: [{', '.join(f'0x{b:02X}' for b in bs)}]")
        print(f"    Uses bankswitch: {'YES' if info['uses_bankswitch'] else 'NO'}")

        print(f"\n  Expansion: 0x{info['expansion']:02X}", end="")
        if info["expansion_chips"]:
            print(f"  ({', '.join(info['expansion_chips'])})")
        else:
            print("  (none)")

        print(f"\n  ROM data size: {info['rom_data_size']:,} bytes ({info['rom_data_size'] / 1024:.1f} KB)")
        print(f"  4KB pages: {info['num_4k_pages']}", end="")
        if info["leftover_bytes"]:
            print(f"  + {info['leftover_bytes']} leftover bytes")
        else:
            print("  (exact)")

        print(f"\n  Slot mapping:")
        print(slot_mapping(info))

        # Extra analysis
        if info["uses_bankswitch"] and not info["page_aligned"]:
            print(f"\n  *** WARNING: Non-page-aligned load with bankswitch!")
            print(f"      Standard formula (addr-0x8000)/0x1000 needs +0x{info['load_offset']:03X} offset")
            print(f"      Actual data start within first bank: 0x{info['load_offset']:03X}")

        if info["uses_bankswitch"]:
            max_bank = max(bs)
            print(f"\n  Max bank index in table: {max_bank}")
            print(f"  Implied minimum ROM: {(max_bank + 1) * 4} KB ({(max_bank + 1)} x 4KB pages)")

    # Summary table
    print(f"\n\n{'=' * 90}")
    print("SUMMARY TABLE")
    print(f"{'=' * 90}")
    header = f"{'Game':<22} {'Load':>6} {'Init':>6} {'Play':>6} {'BS?':>4} {'Exp':>4} {'Pages':>6} {'Aligned':>8} {'BS Table'}"
    print(header)
    print("-" * 90)

    for game_name, rel_path in GAMES.items():
        filepath = os.path.join(BASE, rel_path)
        if not os.path.exists(filepath):
            print(f"{game_name:<22} FILE NOT FOUND")
            continue
        info = parse_nsf(filepath)
        if not info:
            continue
        bs_str = " ".join(f"{b:02X}" for b in info["bankswitch"])
        print(
            f"{game_name:<22} "
            f"${info['load_addr']:04X}  "
            f"${info['init_addr']:04X}  "
            f"${info['play_addr']:04X}  "
            f"{'YES' if info['uses_bankswitch'] else ' NO':>3}  "
            f"0x{info['expansion']:02X}  "
            f"{info['num_4k_pages']:>5}  "
            f"{'YES' if info['page_aligned'] else ' NO':>7}  "
            f"{bs_str}"
        )


if __name__ == "__main__":
    main()
