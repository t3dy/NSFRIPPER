#!/usr/bin/env python3
"""Convert VGM (Video Game Music) files to per-frame APU state.

VGM files are timestamped logs of register writes to sound chips.
For the NES APU (chip type RP2A03), VGM logs contain the same
information as Mesen trace captures: per-frame $4000-$4015 state.

This tool converts VGM register logs into the same per-frame format
used by nsf_to_reaper.py, enabling independent validation of our
NSF extraction pipeline without requiring Mesen traces.

VGM format reference: https://vgmrips.net/wiki/VGM_Specification
NES APU registers: $4000-$4013, $4015 (enable), $4017 (frame counter)

Usage:
    python scripts/vgm_to_frame_state.py <vgm_file> -o output.json
    python scripts/vgm_to_frame_state.py <vgm_file> --midi -o output.mid
    python scripts/vgm_to_frame_state.py <vgm_file> --compare <nsf_midi>
"""

import argparse
import gzip
import json
import math
import struct
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# NES APU constants
NTSC_CLOCK = 1789773
NTSC_FRAME_RATE = 60.0988  # exact NTSC frame rate
SAMPLES_PER_FRAME = 44100 / NTSC_FRAME_RATE  # ~735 samples at 44.1kHz

# VGM command bytes
VGM_END = 0x66
VGM_WAIT_NNNN = 0x61
VGM_WAIT_735 = 0x62   # wait 1/60s (NTSC frame)
VGM_WAIT_882 = 0x63   # wait 1/50s (PAL frame)
VGM_NES_APU = 0xB4     # NES APU register write: B4 aa dd


def read_vgm(path):
    """Read and parse a VGM or VGZ (gzip-compressed VGM) file.

    Returns the raw data bytes after decompression.
    """
    path = Path(path)
    with open(path, 'rb') as f:
        data = f.read()

    # VGZ = gzip-compressed VGM
    if data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)

    # Validate VGM magic
    if data[:4] != b'Vgm ':
        raise ValueError(f"Not a VGM file: magic is {data[:4]!r}, expected b'Vgm '")

    return data


def parse_vgm_header(data):
    """Parse VGM header fields relevant to NES APU.

    Returns dict with version, clock rates, data offset, etc.
    """
    header = {}

    # Standard fields (all 32-bit LE)
    header['eof_offset'] = struct.unpack_from('<I', data, 0x04)[0] + 0x04
    header['version'] = struct.unpack_from('<I', data, 0x08)[0]
    header['total_samples'] = struct.unpack_from('<I', data, 0x18)[0]
    header['loop_offset'] = struct.unpack_from('<I', data, 0x1C)[0]
    header['loop_samples'] = struct.unpack_from('<I', data, 0x20)[0]
    header['rate'] = struct.unpack_from('<I', data, 0x24)[0]

    # VGM data offset (version >= 1.50)
    if header['version'] >= 0x150:
        rel_offset = struct.unpack_from('<I', data, 0x34)[0]
        header['data_offset'] = 0x34 + rel_offset if rel_offset else 0x40
    else:
        header['data_offset'] = 0x40

    # NES APU clock (offset 0x84, version >= 1.61)
    if len(data) > 0x88 and header['version'] >= 0x161:
        header['nes_apu_clock'] = struct.unpack_from('<I', data, 0x84)[0]
    else:
        header['nes_apu_clock'] = 0

    # GD3 tag offset (for metadata)
    gd3_rel = struct.unpack_from('<I', data, 0x14)[0]
    header['gd3_offset'] = 0x14 + gd3_rel if gd3_rel else 0

    return header


def parse_gd3_tags(data, offset):
    """Parse GD3 metadata tags from VGM file.

    Returns dict with track_name, game_name, system, author, etc.
    """
    if offset == 0 or offset + 12 > len(data):
        return {}

    magic = data[offset:offset+4]
    if magic != b'Gd3 ':
        return {}

    # GD3 version and data length
    gd3_len = struct.unpack_from('<I', data, offset + 8)[0]
    gd3_data = data[offset + 12:offset + 12 + gd3_len]

    # GD3 stores null-terminated UTF-16LE strings in order:
    # track_name_en, track_name_jp, game_name_en, game_name_jp,
    # system_en, system_jp, author_en, author_jp, date, ripper, notes
    fields = ['track_name', 'track_name_jp', 'game_name', 'game_name_jp',
              'system', 'system_jp', 'author', 'author_jp', 'date',
              'ripper', 'notes']

    strings = gd3_data.decode('utf-16-le', errors='replace').split('\x00')
    tags = {}
    for i, field in enumerate(fields):
        if i < len(strings):
            tags[field] = strings[i]

    return tags


def extract_nes_apu_writes(data, header):
    """Extract all NES APU register writes with timestamps from VGM data.

    Returns list of (sample_time, register, value) tuples.
    register is 0x00-0x1F mapping to APU $4000-$401F.
    """
    writes = []
    pos = header['data_offset']
    sample_time = 0
    eof = min(header['eof_offset'], len(data))

    while pos < eof:
        cmd = data[pos]

        if cmd == VGM_END:
            break

        elif cmd == VGM_NES_APU:
            # B4 aa dd: write value dd to NES APU register aa
            if pos + 2 >= eof:
                break
            reg = data[pos + 1]   # 0x00-0x1F → $4000-$401F
            val = data[pos + 2]
            writes.append((sample_time, reg, val))
            pos += 3

        elif cmd == VGM_WAIT_735:
            # Wait 735 samples (1 NTSC frame at 44100 Hz)
            sample_time += 735
            pos += 1

        elif cmd == VGM_WAIT_882:
            # Wait 882 samples (1 PAL frame at 44100 Hz)
            sample_time += 882
            pos += 1

        elif cmd == VGM_WAIT_NNNN:
            # Wait N samples (16-bit)
            if pos + 2 >= eof:
                break
            wait = struct.unpack_from('<H', data, pos + 1)[0]
            sample_time += wait
            pos += 3

        elif 0x70 <= cmd <= 0x7F:
            # Wait (cmd & 0x0F) + 1 samples
            sample_time += (cmd & 0x0F) + 1
            pos += 1

        elif 0x80 <= cmd <= 0x8F:
            # YM2612 DAC + wait (not relevant for NES, skip)
            sample_time += cmd & 0x0F
            pos += 1

        elif cmd in (0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37,
                     0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F):
            # 2-byte commands for various chips (skip)
            pos += 2

        elif cmd in (0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47,
                     0x48, 0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F,
                     0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57,
                     0x58, 0x59, 0x5A, 0x5B, 0x5C, 0x5D, 0x5E, 0x5F,
                     0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7,
                     0xA8, 0xA9, 0xAA, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF,
                     0xB0, 0xB1, 0xB2, 0xB3, 0xB5, 0xB6, 0xB7, 0xB8,
                     0xB9, 0xBA, 0xBB, 0xBC, 0xBD, 0xBE, 0xBF):
            # 3-byte commands for various chips (skip)
            pos += 3

        elif cmd in (0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7,
                     0xC8, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6,
                     0xE0, 0xE1):
            # 4-byte commands (skip)
            pos += 4

        elif cmd == 0x67:
            # Data block: 67 66 tt ss ss ss ss [data]
            if pos + 6 >= eof:
                break
            block_size = struct.unpack_from('<I', data, pos + 3)[0]
            pos += 7 + block_size

        elif cmd == 0x68:
            # PCM RAM write: skip
            if pos + 11 >= eof:
                break
            pos += 12

        else:
            # Unknown command — try to skip 1 byte
            pos += 1

    return writes


def writes_to_frame_state(writes, frame_rate=NTSC_FRAME_RATE):
    """Convert timestamped register writes to per-frame APU state.

    Groups writes into frames based on sample timing (44100 Hz).
    Returns list of frame dicts matching nsf_to_reaper.py format:
        [{"frame": N, "writes": [(reg_addr, value), ...]}, ...]
    """
    samples_per_frame = 44100 / frame_rate
    frames = []
    current_frame = 0
    current_writes = []

    # APU register state (persistent across frames)
    apu_state = [0] * 0x20  # $4000-$401F

    for sample_time, reg, val in writes:
        frame_num = int(sample_time / samples_per_frame)

        # Emit completed frames
        while current_frame < frame_num:
            frames.append({
                "frame": current_frame,
                "writes": list(current_writes),
            })
            current_writes = []
            current_frame += 1

        # Map VGM register offset (0x00-0x1F) to APU address ($4000-$401F)
        apu_addr = 0x4000 + reg
        apu_state[reg] = val
        current_writes.append((apu_addr, val))

    # Emit final frame
    if current_writes:
        frames.append({
            "frame": current_frame,
            "writes": list(current_writes),
        })

    return frames


def frame_state_to_channel_summary(frames):
    """Extract per-channel summary from frame state for comparison.

    Returns dict with per-channel note events (period changes),
    volume events, and duty events — the same data nsf_to_reaper
    captures via CC11/CC12.
    """
    channels = {
        "pulse1": {"period": 0, "vol": 0, "duty": 0, "events": []},
        "pulse2": {"period": 0, "vol": 0, "duty": 0, "events": []},
        "triangle": {"period": 0, "events": []},
        "noise": {"vol": 0, "period": 0, "mode": 0, "events": []},
    }

    for frame_data in frames:
        frame_num = frame_data["frame"]
        for reg, val in frame_data["writes"]:
            # Pulse 1
            if reg == 0x4000:
                new_vol = val & 0x0F
                new_duty = (val >> 6) & 3
                const_vol = (val >> 4) & 1
                if new_vol != channels["pulse1"]["vol"] or new_duty != channels["pulse1"]["duty"]:
                    channels["pulse1"]["events"].append({
                        "frame": frame_num, "type": "env",
                        "vol": new_vol, "duty": new_duty,
                        "const_vol": const_vol,
                    })
                    channels["pulse1"]["vol"] = new_vol
                    channels["pulse1"]["duty"] = new_duty
            elif reg == 0x4002:
                old_p = channels["pulse1"]["period"]
                channels["pulse1"]["period"] = (old_p & 0x700) | val
            elif reg == 0x4003:
                old_p = channels["pulse1"]["period"]
                new_p = (old_p & 0xFF) | ((val & 7) << 8)
                if new_p != old_p:
                    channels["pulse1"]["events"].append({
                        "frame": frame_num, "type": "period",
                        "period": new_p,
                    })
                    channels["pulse1"]["period"] = new_p

            # Pulse 2
            elif reg == 0x4004:
                new_vol = val & 0x0F
                new_duty = (val >> 6) & 3
                const_vol = (val >> 4) & 1
                if new_vol != channels["pulse2"]["vol"] or new_duty != channels["pulse2"]["duty"]:
                    channels["pulse2"]["events"].append({
                        "frame": frame_num, "type": "env",
                        "vol": new_vol, "duty": new_duty,
                        "const_vol": const_vol,
                    })
                    channels["pulse2"]["vol"] = new_vol
                    channels["pulse2"]["duty"] = new_duty
            elif reg == 0x4006:
                old_p = channels["pulse2"]["period"]
                channels["pulse2"]["period"] = (old_p & 0x700) | val
            elif reg == 0x4007:
                old_p = channels["pulse2"]["period"]
                new_p = (old_p & 0xFF) | ((val & 7) << 8)
                if new_p != old_p:
                    channels["pulse2"]["events"].append({
                        "frame": frame_num, "type": "period",
                        "period": new_p,
                    })
                    channels["pulse2"]["period"] = new_p

            # Triangle
            elif reg == 0x400A:
                old_p = channels["triangle"].get("period", 0)
                channels["triangle"]["period"] = (old_p & 0x700) | val
            elif reg == 0x400B:
                old_p = channels["triangle"].get("period", 0)
                new_p = (old_p & 0xFF) | ((val & 7) << 8)
                if new_p != old_p:
                    channels["triangle"]["events"].append({
                        "frame": frame_num, "type": "period",
                        "period": new_p,
                    })
                    channels["triangle"]["period"] = new_p

            # Noise
            elif reg == 0x400C:
                new_vol = val & 0x0F
                if new_vol != channels["noise"]["vol"]:
                    channels["noise"]["events"].append({
                        "frame": frame_num, "type": "env",
                        "vol": new_vol,
                    })
                    channels["noise"]["vol"] = new_vol
            elif reg == 0x400E:
                new_period = val & 0x0F
                new_mode = (val >> 7) & 1
                if new_period != channels["noise"]["period"] or new_mode != channels["noise"]["mode"]:
                    channels["noise"]["events"].append({
                        "frame": frame_num, "type": "period",
                        "period": new_period, "mode": new_mode,
                    })
                    channels["noise"]["period"] = new_period
                    channels["noise"]["mode"] = new_mode

            # DAC / DMC writes ($4011)
            elif reg == 0x4011:
                # Track $4011 writes for algorithmic percussion detection
                # (e.g., Battletoads drums are computed ramps to $4011)
                pass  # TODO: extend Frame IR with DAC event type

    return channels


def compare_with_nsf_midi(vgm_channels, midi_path):
    """Compare VGM-derived channel data against NSF-extracted MIDI.

    Compares note timing and pitch sequences to find divergences.
    Returns comparison report dict.
    """
    import mido

    mid = mido.MidiFile(str(midi_path))
    report = {"matches": 0, "mismatches": 0, "details": []}

    channel_names = {
        'Square 1': 'pulse1', 'Square 2': 'pulse2',
        'Triangle': 'triangle', 'Noise': 'noise',
        'lead': 'pulse1', 'harmony': 'pulse2',
        'bass': 'triangle', 'drums': 'noise',
    }

    for track in mid.tracks:
        name = track.name if hasattr(track, 'name') and track.name else ''
        ch_key = None
        for keyword, key in channel_names.items():
            if keyword.lower() in name.lower():
                ch_key = key
                break
        if not ch_key or ch_key not in vgm_channels:
            continue

        # Extract MIDI note events with timing
        midi_notes = []
        tick_time = 0
        for msg in track:
            tick_time += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                # Convert ticks to frames: 16 ticks/frame at 128.6 BPM
                frame = tick_time / 16
                midi_notes.append({"frame": frame, "note": msg.note})

        # Extract VGM period-change events
        vgm_notes = [e for e in vgm_channels[ch_key]["events"]
                     if e["type"] == "period"]

        # Compare note counts
        detail = {
            "channel": ch_key,
            "vgm_notes": len(vgm_notes),
            "midi_notes": len(midi_notes),
            "count_match": abs(len(vgm_notes) - len(midi_notes)) <= 5,
        }

        # Compare first N note pitches (period → MIDI note)
        n_compare = min(50, len(vgm_notes), len(midi_notes))
        pitch_matches = 0
        pitch_mismatches = []
        for i in range(n_compare):
            vgm_period = vgm_notes[i]["period"]
            is_tri = (ch_key == "triangle")
            div = 32 if is_tri else 16
            if vgm_period > (2 if is_tri else 8):
                freq = NTSC_CLOCK / (div * (vgm_period + 1))
                vgm_midi = round(69 + 12 * math.log2(freq / 440))
            else:
                vgm_midi = 0

            midi_note = midi_notes[i]["note"]
            if abs(vgm_midi - midi_note) <= 1:  # within 1 semitone
                pitch_matches += 1
            else:
                pitch_mismatches.append({
                    "index": i,
                    "vgm_period": vgm_period,
                    "vgm_midi": vgm_midi,
                    "nsf_midi": midi_note,
                    "diff": vgm_midi - midi_note,
                })

        detail["pitch_matches"] = pitch_matches
        detail["pitch_mismatches"] = len(pitch_mismatches)
        detail["pitch_match_pct"] = round(100 * pitch_matches / n_compare, 1) if n_compare else 0
        detail["first_mismatches"] = pitch_mismatches[:5]

        report["matches"] += pitch_matches
        report["mismatches"] += len(pitch_mismatches)
        report["details"].append(detail)

    total = report["matches"] + report["mismatches"]
    report["overall_match_pct"] = round(100 * report["matches"] / total, 1) if total else 0
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Convert VGM register logs to per-frame APU state")
    parser.add_argument("vgm_file", help="VGM or VGZ file to parse")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--compare", help="NSF-extracted MIDI to compare against")
    parser.add_argument("--info", action="store_true",
                        help="Print VGM header info and GD3 tags only")
    parser.add_argument("--summary", action="store_true",
                        help="Print per-channel event summary")
    args = parser.parse_args()

    # Read VGM
    data = read_vgm(args.vgm_file)
    header = parse_vgm_header(data)
    tags = parse_gd3_tags(data, header['gd3_offset'])

    if args.info:
        print(f"VGM version: {header['version']:#06x}")
        print(f"NES APU clock: {header['nes_apu_clock']} Hz")
        print(f"Total samples: {header['total_samples']}")
        duration = header['total_samples'] / 44100
        print(f"Duration: {duration:.1f}s ({duration/60:.1f}m)")
        if tags:
            print(f"\nTrack: {tags.get('track_name', '?')}")
            print(f"Game:  {tags.get('game_name', '?')}")
            print(f"Author: {tags.get('author', '?')}")
            print(f"System: {tags.get('system', '?')}")
            print(f"Ripper: {tags.get('ripper', '?')}")
        return

    # Extract register writes
    writes = extract_nes_apu_writes(data, header)
    nes_writes = [(t, r, v) for t, r, v in writes if r <= 0x17]
    print(f"Extracted {len(nes_writes)} NES APU register writes "
          f"({len(writes)} total writes)")

    if not nes_writes:
        print("No NES APU data found in VGM file.")
        print("This VGM may be for a different sound chip.")
        return

    # Convert to per-frame state
    frames = writes_to_frame_state(nes_writes)
    print(f"Converted to {len(frames)} frames "
          f"({len(frames)/60:.1f}s at 60 Hz)")

    if args.summary or not args.output:
        channels = frame_state_to_channel_summary(frames)
        print(f"\nPer-channel event counts:")
        for ch_name, ch_data in channels.items():
            events = ch_data["events"]
            period_events = [e for e in events if e["type"] == "period"]
            env_events = [e for e in events if e["type"] == "env"]
            print(f"  {ch_name:10s}: {len(period_events):4d} period changes, "
                  f"{len(env_events):4d} envelope changes")

            # CC density metric
            if period_events:
                cc_per_note = len(env_events) / len(period_events)
                print(f"             CC11/note equivalent: {cc_per_note:.1f}")

    # Save frame state
    if args.output:
        output_path = Path(args.output)
        output_data = {
            "source": str(args.vgm_file),
            "format": "vgm_frame_state",
            "tags": tags,
            "header": {k: v for k, v in header.items()
                       if isinstance(v, (int, float, str))},
            "total_frames": len(frames),
            "frames": frames,
        }
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"Frame state written to {output_path}")

    # Cross-validation
    if args.compare:
        channels = frame_state_to_channel_summary(frames)
        report = compare_with_nsf_midi(channels, args.compare)
        print(f"\n{'='*60}")
        print(f"Cross-Validation: VGM vs NSF-extracted MIDI")
        print(f"{'='*60}")
        print(f"Overall pitch match: {report['overall_match_pct']}%")
        for detail in report["details"]:
            print(f"\n  {detail['channel']}:")
            print(f"    VGM notes: {detail['vgm_notes']}, "
                  f"MIDI notes: {detail['midi_notes']}")
            print(f"    Pitch match: {detail['pitch_match_pct']}% "
                  f"({detail['pitch_matches']}/{detail['pitch_matches']+detail['pitch_mismatches']})")
            if detail["first_mismatches"]:
                print(f"    First mismatches:")
                for mm in detail["first_mismatches"]:
                    print(f"      note {mm['index']}: VGM={mm['vgm_midi']} "
                          f"NSF={mm['nsf_midi']} (diff={mm['diff']:+d})")

        # Save comparison report
        if args.output:
            report_path = Path(args.output).with_suffix('.comparison.json')
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nComparison report: {report_path}")


if __name__ == "__main__":
    main()
