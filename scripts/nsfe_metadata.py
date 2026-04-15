#!/usr/bin/env python3
"""Parse NSFE (Extended NSF) files for track metadata.

NSFE files wrap NSF music data with per-track metadata:
- Track names
- Track durations (in milliseconds)
- Fade-out times
- Playlist ordering
- Ripper credits

This script extracts metadata from NSFE files and can merge it with
our existing NSF-based pipeline output (M3U playlists, MIDI files).

NSFE format: https://www.nesdev.org/wiki/NSFe
NSF2 format: https://www.nesdev.org/wiki/NSF2

Usage:
    python scripts/nsfe_metadata.py <nsfe_file>              # show metadata
    python scripts/nsfe_metadata.py <nsfe_file> --m3u        # generate M3U playlist
    python scripts/nsfe_metadata.py --scan <directory>        # scan for all NSFE files
    python scripts/nsfe_metadata.py --merge <nsfe> <game_slug>  # merge into pipeline
"""

import argparse
import json
import struct
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_nsfe(path):
    """Parse an NSFE file and extract all metadata chunks.

    NSFE structure:
    - 4 bytes: 'NSFE' magic
    - Chunks until 'NEND':
        - 4 bytes: chunk data length (LE)
        - 4 bytes: chunk FourCC
        - N bytes: chunk data

    Chunk types:
    - 'INFO': NSF header equivalent (required, must be first)
    - 'DATA': NSF program data (required)
    - 'NEND': end marker (required, must be last)
    - 'plst': playlist ordering
    - 'time': track durations (int32 ms per track)
    - 'fade': fade-out durations (int32 ms per track)
    - 'tlbl': track labels (null-terminated UTF-8 strings)
    - 'auth': author info (4 null-terminated strings)
    - 'text': free-form text
    """
    with open(path, 'rb') as f:
        data = f.read()

    if data[:4] != b'NSFE':
        raise ValueError(f"Not an NSFE file: magic is {data[:4]!r}")

    chunks = {}
    pos = 4

    while pos < len(data):
        if pos + 8 > len(data):
            break

        chunk_len = struct.unpack_from('<I', data, pos)[0]
        fourcc = data[pos + 4:pos + 8].decode('ascii', errors='replace')
        chunk_data = data[pos + 8:pos + 8 + chunk_len]
        pos += 8 + chunk_len

        chunks[fourcc] = chunk_data

        if fourcc == 'NEND':
            break

    return chunks


def extract_info(chunks):
    """Extract INFO chunk (NSF header equivalent)."""
    info_data = chunks.get('INFO', b'')
    if len(info_data) < 9:
        return {}

    info = {
        'load_addr': struct.unpack_from('<H', info_data, 0)[0],
        'init_addr': struct.unpack_from('<H', info_data, 2)[0],
        'play_addr': struct.unpack_from('<H', info_data, 4)[0],
        'pal_ntsc': info_data[6],  # 0=NTSC, 1=PAL, 2=both
        'expansion': info_data[7],  # expansion chip flags
        'total_songs': info_data[8],
    }
    if len(info_data) > 9:
        info['starting_song'] = info_data[9]

    return info


def extract_track_labels(chunks):
    """Extract track labels from 'tlbl' chunk.

    Labels are null-terminated UTF-8 strings concatenated together.
    """
    tlbl_data = chunks.get('tlbl', b'')
    if not tlbl_data:
        return []

    labels = tlbl_data.decode('utf-8', errors='replace').split('\x00')
    # Remove trailing empty string
    while labels and labels[-1] == '':
        labels.pop()
    return labels


def extract_track_times(chunks):
    """Extract track durations from 'time' chunk.

    Each entry is a signed 32-bit LE integer in milliseconds.
    Negative values mean "use default duration."
    """
    time_data = chunks.get('time', b'')
    if not time_data:
        return []

    count = len(time_data) // 4
    times = []
    for i in range(count):
        ms = struct.unpack_from('<i', time_data, i * 4)[0]
        times.append(ms)
    return times


def extract_fade_times(chunks):
    """Extract fade-out durations from 'fade' chunk."""
    fade_data = chunks.get('fade', b'')
    if not fade_data:
        return []

    count = len(fade_data) // 4
    fades = []
    for i in range(count):
        ms = struct.unpack_from('<i', fade_data, i * 4)[0]
        fades.append(ms)
    return fades


def extract_auth(chunks):
    """Extract author info from 'auth' chunk.

    Four null-terminated strings: game, artist, copyright, ripper.
    """
    auth_data = chunks.get('auth', b'')
    if not auth_data:
        return {}

    strings = auth_data.decode('utf-8', errors='replace').split('\x00')
    fields = ['game', 'artist', 'copyright', 'ripper']
    auth = {}
    for i, field in enumerate(fields):
        if i < len(strings):
            auth[field] = strings[i]
    return auth


def extract_playlist(chunks):
    """Extract playlist ordering from 'plst' chunk.

    Each byte is a track index (0-based).
    """
    plst_data = chunks.get('plst', b'')
    return list(plst_data)


def parse_nsfe_full(path):
    """Parse NSFE file and return complete metadata dict."""
    chunks = parse_nsfe(path)

    metadata = {
        'file': str(path),
        'info': extract_info(chunks),
        'auth': extract_auth(chunks),
        'labels': extract_track_labels(chunks),
        'times': extract_track_times(chunks),
        'fades': extract_fade_times(chunks),
        'playlist': extract_playlist(chunks),
        'has_text': 'text' in chunks,
        'chunks': list(chunks.keys()),
    }

    return metadata


def generate_m3u(metadata, nsf_filename):
    """Generate M3U playlist from NSFE metadata.

    Format matches our existing M3U convention:
    filename::NSF,track_num,track_name,duration,...
    """
    lines = []
    labels = metadata.get('labels', [])
    times = metadata.get('times', [])
    total = metadata['info'].get('total_songs', len(labels))

    for i in range(total):
        name = labels[i] if i < len(labels) else f"Track {i + 1}"
        duration_ms = times[i] if i < len(times) else -1
        # Format duration as mm:ss.mmm
        if duration_ms > 0:
            secs = duration_ms / 1000.0
            mins = int(secs) // 60
            remaining = secs - mins * 60
            duration_str = f"{mins}:{remaining:06.3f}"
        else:
            duration_str = "3:00.000"  # default 3 minutes

        lines.append(f"{nsf_filename}::NSF,{i + 1},{name},{duration_str}")

    return "\n".join(lines)


def merge_into_pipeline(metadata, game_slug):
    """Merge NSFE metadata into existing pipeline output.

    Updates M3U playlist and stores metadata JSON for the game.
    """
    output_dir = REPO_ROOT / "output" / game_slug
    nsf_dir = output_dir / "nsf"

    if not output_dir.exists():
        print(f"No output directory for {game_slug}")
        return False

    # Find existing NSF
    nsfs = list(nsf_dir.glob("*.nsf")) if nsf_dir.exists() else []
    nsf_name = nsfs[0].name if nsfs else f"{game_slug}.nsf"

    # Generate M3U
    m3u_content = generate_m3u(metadata, nsf_name)
    m3u_path = nsf_dir / f"{Path(nsf_name).stem}.m3u"
    m3u_path.parent.mkdir(parents=True, exist_ok=True)
    with open(m3u_path, 'w', encoding='utf-8') as f:
        f.write(m3u_content)
    print(f"  M3U written: {m3u_path}")

    # Save full metadata JSON
    meta_path = output_dir / "metadata.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"  Metadata: {meta_path}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Parse NSFE files for track metadata")
    parser.add_argument("nsfe_file", nargs='?', help="NSFE file to parse")
    parser.add_argument("--m3u", action="store_true",
                        help="Generate M3U playlist")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--scan", help="Scan directory for NSFE files")
    parser.add_argument("--merge", help="Game slug to merge metadata into")
    args = parser.parse_args()

    if args.scan:
        scan_dir = Path(args.scan)
        nsfe_files = sorted(scan_dir.rglob("*.nsfe")) + sorted(scan_dir.rglob("*.NSFE"))
        print(f"Found {len(nsfe_files)} NSFE files in {scan_dir}")
        for nsfe_path in nsfe_files:
            try:
                meta = parse_nsfe_full(nsfe_path)
                auth = meta.get('auth', {})
                labels = meta.get('labels', [])
                info = meta.get('info', {})
                print(f"  {nsfe_path.name}: "
                      f"{info.get('total_songs', '?')} tracks, "
                      f"{len(labels)} labeled, "
                      f"game='{auth.get('game', '?')}', "
                      f"artist='{auth.get('artist', '?')}'")
            except Exception as e:
                print(f"  {nsfe_path.name}: ERROR: {e}")
        return

    if not args.nsfe_file:
        parser.print_help()
        return

    metadata = parse_nsfe_full(args.nsfe_file)

    if args.json:
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
        return

    if args.merge:
        merge_into_pipeline(metadata, args.merge)
        return

    # Display metadata
    info = metadata['info']
    auth = metadata['auth']
    labels = metadata['labels']
    times = metadata['times']

    print(f"\n{'='*60}")
    print(f"NSFE: {args.nsfe_file}")
    print(f"{'='*60}")

    if auth:
        print(f"Game:      {auth.get('game', '?')}")
        print(f"Artist:    {auth.get('artist', '?')}")
        print(f"Copyright: {auth.get('copyright', '?')}")
        print(f"Ripper:    {auth.get('ripper', '?')}")

    print(f"\nTracks: {info.get('total_songs', '?')}")
    print(f"Region: {'NTSC' if info.get('pal_ntsc') == 0 else 'PAL' if info.get('pal_ntsc') == 1 else 'Both'}")
    exp = info.get('expansion', 0)
    if exp:
        chips = []
        if exp & 1: chips.append("VRC6")
        if exp & 2: chips.append("VRC7")
        if exp & 4: chips.append("FDS")
        if exp & 8: chips.append("MMC5")
        if exp & 16: chips.append("N163")
        if exp & 32: chips.append("5B")
        print(f"Expansion: {', '.join(chips)}")

    print(f"Chunks:  {', '.join(metadata['chunks'])}")

    if labels:
        print(f"\nTrack listing:")
        for i, label in enumerate(labels):
            duration = ""
            if i < len(times) and times[i] > 0:
                secs = times[i] / 1000.0
                mins = int(secs) // 60
                remaining = secs - mins * 60
                duration = f" [{mins}:{remaining:04.1f}]"
            print(f"  {i + 1:3d}. {label}{duration}")

    if args.m3u:
        nsf_name = Path(args.nsfe_file).stem + ".nsf"
        m3u = generate_m3u(metadata, nsf_name)
        print(f"\n--- M3U ---")
        print(m3u)


if __name__ == "__main__":
    main()
