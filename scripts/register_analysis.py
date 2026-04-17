#!/usr/bin/env python3
"""Analyze APU register usage patterns from MIDI SysEx streams.

Each extracted MIDI includes a SysEx track carrying full per-frame APU
register state (type 0x02 messages for APU, 0x04 for expansion). This
script reconstructs the register writes and measures patterns that tell
us about driver behavior:

- const_vol bit usage ($4000/$4004 bit 4): hardware envelope vs software
- envelope loop bit ($4000 bit 5): length counter halt vs env loop
- Phase reset frequency ($4003/$4007 write rate per second)
- Sweep unit usage ($4001/$4005): how many games actually use it musically
- Frame counter mode ($4017): 4-step vs 5-step timing
- Triangle gating: linear counter vs length counter usage
- DPCM rate distribution: which sample rates drivers pick
- $4015 write frequency: per-note gating vs init-only

Usage:
    python scripts/register_analysis.py               # scan all games
    python scripts/register_analysis.py --game <slug> # one game detail
    python scripts/register_analysis.py --json <out>  # save full data
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import mido

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"


def decode_sysex_apu(data):
    """Parse a type 0x02 APU SysEx message into (channel, [regs], enable, mask).

    Format: F0 7D 02 <ch> <r0_lo> <r0_hi> <r1_lo> <r1_hi> <r2_lo> <r2_hi>
            <r3_lo> <r3_hi> <enable> <write_mask> F7
    data is the payload after F0 (so starts with 7D).
    Returns None if not a type 0x02 APU frame.
    """
    if len(data) < 13 or data[0] != 0x7D or data[1] != 0x02:
        return None
    ch = data[2]
    regs = []
    for i in range(4):
        lo = data[3 + i * 2]
        hi = data[4 + i * 2]
        regs.append((hi << 7) | lo)
    enable = data[11]
    write_mask = data[12]
    return ch, regs, enable, write_mask


def analyze_game(game_dir, max_songs=5):
    """Analyze register usage for up to max_songs per game.

    Sampling a handful of songs is sufficient for driver signature —
    most drivers are uniform across songs, and analyzing all 98 MM4 songs
    is wasteful. 5 songs gives 15-30k frames which is statistically solid.
    """
    midi_dir = game_dir / "midi"
    if not midi_dir.exists():
        return None

    stats = {
        "game": game_dir.name,
        "songs_analyzed": 0,
        "total_frames": 0,
        # Per-channel envelope mode counts
        "pulse1_const_vol_frames": 0,
        "pulse2_const_vol_frames": 0,
        "pulse1_env_loop_frames": 0,
        "pulse2_env_loop_frames": 0,
        # Phase reset / retrigger events
        "pulse1_phase_resets": 0,  # frames where reg3 was written
        "pulse2_phase_resets": 0,
        "triangle_retriggers": 0,  # frames where reg3 ($400B) was written
        # Sweep usage (reg1 write)
        "pulse1_sweep_writes": 0,
        "pulse2_sweep_writes": 0,
        "pulse1_sweep_enabled_frames": 0,
        "pulse2_sweep_enabled_frames": 0,
        # Triangle gating
        "triangle_linear_frames": 0,   # frames where linear > 0
        "triangle_length_enabled_frames": 0,  # frames where enable bit 2 set
        # DPCM rate distribution (0-15 index)
        "dmc_rate_histogram": [0] * 16,
        "dmc_triggers": 0,
        "dmc_dac_writes": 0,
        # $4015 activity — indirect: count distinct enable patterns seen
        "enable_patterns_seen": set(),
        # Duty cycle distribution (per channel)
        "pulse1_duty_histogram": [0, 0, 0, 0],
        "pulse2_duty_histogram": [0, 0, 0, 0],
        # Volume patterns — sustained vs transient (how many 0-vol frames after non-0)
        "pulse1_volume_resets": 0,
        "pulse2_volume_resets": 0,
    }

    # Skip trivial songs (<30s = ~1800 frames), they are often title/game-over
    # stubs and don't show musical driver patterns. Then sample the first
    # max_songs musical songs.
    all_midis = sorted(midi_dir.glob("*.mid"))
    sampled = []
    for mf in all_midis:
        if len(sampled) >= max_songs:
            break
        try:
            stat = mf.stat()
            if stat.st_size < 3000:  # tiny MIDI = stub
                continue
        except OSError:
            continue
        sampled.append(mf)

    for midi_file in sampled:
        try:
            mid = mido.MidiFile(str(midi_file))
        except Exception:
            continue

        # Find the SysEx track
        sysex_track = None
        for track in mid.tracks:
            if any(m.type == "sysex" for m in track):
                sysex_track = track
                break
        if sysex_track is None:
            continue

        # Per-channel previous state for delta detection
        prev_reg = {0: [0, 0, 0, 0], 1: [0, 0, 0, 0], 2: [0, 0, 0, 0], 3: [0, 0, 0, 0], 4: [0, 0, 0, 0]}
        prev_vol = {0: 0, 1: 0}
        # Count frames by ch==0 messages (pulse1 is always present).
        # This gives accurate per-channel frame counts regardless of how many
        # expansion channels the game has.
        song_frames = 0

        for msg in sysex_track:
            if msg.type != "sysex":
                continue
            parsed = decode_sysex_apu(msg.data)
            if parsed is None:
                continue
            ch, regs, enable, write_mask = parsed

            stats["enable_patterns_seen"].add(enable & 0x1F)

            if ch == 0:
                song_frames += 1

            # Pulse 1 (ch 0) and Pulse 2 (ch 1)
            if ch in (0, 1):
                reg0 = regs[0]
                # const_vol bit 4
                const_vol = (reg0 >> 4) & 1
                env_loop = (reg0 >> 5) & 1
                duty = (reg0 >> 6) & 3
                vol = reg0 & 0x0F

                if ch == 0:
                    stats["pulse1_const_vol_frames"] += const_vol
                    stats["pulse1_env_loop_frames"] += env_loop
                    stats["pulse1_duty_histogram"][duty] += 1
                    # Phase reset = reg3 written this frame
                    if write_mask & 0x08:
                        stats["pulse1_phase_resets"] += 1
                    # Sweep = reg1 written this frame
                    if write_mask & 0x02:
                        stats["pulse1_sweep_writes"] += 1
                    # Sweep enabled (reg1 bit 7)
                    if regs[1] & 0x80:
                        stats["pulse1_sweep_enabled_frames"] += 1
                    # Volume resets (went from non-zero to zero)
                    if vol == 0 and prev_vol[0] > 0:
                        stats["pulse1_volume_resets"] += 1
                    prev_vol[0] = vol
                else:
                    stats["pulse2_const_vol_frames"] += const_vol
                    stats["pulse2_env_loop_frames"] += env_loop
                    stats["pulse2_duty_histogram"][duty] += 1
                    if write_mask & 0x08:
                        stats["pulse2_phase_resets"] += 1
                    if write_mask & 0x02:
                        stats["pulse2_sweep_writes"] += 1
                    if regs[1] & 0x80:
                        stats["pulse2_sweep_enabled_frames"] += 1
                    if vol == 0 and prev_vol[1] > 0:
                        stats["pulse2_volume_resets"] += 1
                    prev_vol[1] = vol

            elif ch == 2:  # Triangle
                # reg0 = $4008 = linear counter control + reload value
                linear_reload = regs[0] & 0x7F
                if linear_reload > 0:
                    stats["triangle_linear_frames"] += 1
                if enable & 0x04:
                    stats["triangle_length_enabled_frames"] += 1
                if write_mask & 0x08:
                    stats["triangle_retriggers"] += 1

            elif ch == 4:  # DMC
                # reg0 = $4010 = rate/loop/IRQ
                rate_idx = regs[0] & 0x0F
                if write_mask & 0x0C:  # $4012 or $4013 written
                    stats["dmc_triggers"] += 1
                    stats["dmc_rate_histogram"][rate_idx] += 1
                elif write_mask & 0x02:  # only $4011 written
                    stats["dmc_dac_writes"] += 1

        stats["songs_analyzed"] += 1
        stats["total_frames"] += song_frames

    # Convert set to list for JSON
    stats["enable_patterns_seen"] = sorted(list(stats["enable_patterns_seen"]))
    return stats


def summarize(all_stats):
    """Compute cross-game summary statistics."""
    by_metric = {
        "hw_envelope_dominant": [],       # const_vol=0 dominant
        "sw_envelope_dominant": [],       # const_vol=1 dominant
        "heavy_sweep_users": [],          # games with >5% sweep-enabled frames
        "phase_reset_heavy": [],          # games with many same-pitch retriggers
        "dmc_sample_users": [],           # games using dpcm_trigger
        "dmc_dac_users": [],              # games using direct DAC writes
        "dmc_both_mechanisms": [],        # games that use both
        "channel_gating_via_4015": [],    # games with multiple $4015 patterns
    }

    for s in all_stats:
        total_f = max(1, s["total_frames"])

        # Envelope mode (pulse 1 as proxy — most games use same mode both pulses)
        p1_cv = s["pulse1_const_vol_frames"]
        p1_frames = max(1, s["pulse1_const_vol_frames"] + (total_f - s["pulse1_const_vol_frames"]))
        if p1_cv > total_f * 0.5:
            by_metric["sw_envelope_dominant"].append((s["game"], p1_cv / total_f))
        else:
            by_metric["hw_envelope_dominant"].append((s["game"], 1 - p1_cv / total_f))

        # Sweep users
        sweep_frames = s["pulse1_sweep_enabled_frames"] + s["pulse2_sweep_enabled_frames"]
        if sweep_frames > total_f * 0.02:
            by_metric["heavy_sweep_users"].append((s["game"], sweep_frames / total_f, s["pulse1_sweep_writes"] + s["pulse2_sweep_writes"]))

        # Phase reset heavy
        phase_events = s["pulse1_phase_resets"] + s["pulse2_phase_resets"] + s["triangle_retriggers"]
        if phase_events > total_f * 0.05:
            by_metric["phase_reset_heavy"].append((s["game"], phase_events))

        # DMC mechanisms
        if s["dmc_triggers"] > 10:
            by_metric["dmc_sample_users"].append((s["game"], s["dmc_triggers"]))
        if s["dmc_dac_writes"] > 50:
            by_metric["dmc_dac_users"].append((s["game"], s["dmc_dac_writes"]))
        if s["dmc_triggers"] > 10 and s["dmc_dac_writes"] > 50:
            by_metric["dmc_both_mechanisms"].append((s["game"], s["dmc_triggers"], s["dmc_dac_writes"]))

        # Multiple $4015 patterns = drivers that toggle channels
        if len(s["enable_patterns_seen"]) >= 3:
            by_metric["channel_gating_via_4015"].append((s["game"], len(s["enable_patterns_seen"]), s["enable_patterns_seen"]))

    return by_metric


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", help="Analyze a single game by slug")
    ap.add_argument("--json", help="Save full results to this path")
    ap.add_argument("--summary", action="store_true", help="Print summary only")
    args = ap.parse_args()

    if args.game:
        game_dir = OUTPUT_DIR / args.game
        if not game_dir.exists():
            print(f"Game not found: {args.game}")
            sys.exit(1)
        stats = analyze_game(game_dir)
        if stats is None:
            print(f"No MIDI files in {args.game}")
            sys.exit(1)
        print(json.dumps(stats, indent=2))
        return

    all_stats = []
    game_dirs = sorted([d for d in OUTPUT_DIR.iterdir() if d.is_dir() and (d / "midi").exists()])
    print(f"Analyzing {len(game_dirs)} games...", file=sys.stderr, flush=True)

    # Write incremental results so a killed run still leaves data
    incremental_path = args.json if args.json else None

    for i, game_dir in enumerate(game_dirs):
        stats = analyze_game(game_dir)
        if stats:
            all_stats.append(stats)
        if i % 10 == 0:
            print(f"  [{i+1}/{len(game_dirs)}] {game_dir.name}", file=sys.stderr, flush=True)
            # Save partial result every 10 games
            if incremental_path:
                with open(incremental_path + ".partial", "w") as f:
                    json.dump({"per_game": all_stats, "progress": f"{i+1}/{len(game_dirs)}"}, f, indent=2)

    summary = summarize(all_stats)

    print(f"\n=== Register Analysis: {len(all_stats)} games ===\n")

    print(f"Hardware envelope dominant ({len(summary['hw_envelope_dominant'])} games):")
    for g, pct in sorted(summary['hw_envelope_dominant'], key=lambda x: -x[1])[:15]:
        print(f"  {g}: {pct*100:.0f}% HW envelope frames")
    print(f"  ... (showing top 15)")

    print(f"\nSoftware envelope dominant ({len(summary['sw_envelope_dominant'])} games):")
    for g, pct in sorted(summary['sw_envelope_dominant'], key=lambda x: -x[1])[:15]:
        print(f"  {g}: {pct*100:.0f}% SW envelope (const_vol=1)")

    print(f"\nHeavy sweep users ({len(summary['heavy_sweep_users'])} games):")
    for g, pct, writes in sorted(summary['heavy_sweep_users'], key=lambda x: -x[1])[:10]:
        print(f"  {g}: {pct*100:.1f}% frames with sweep enabled, {writes} sweep writes")

    print(f"\nDMC sample users ({len(summary['dmc_sample_users'])} games):")
    for g, n in sorted(summary['dmc_sample_users'], key=lambda x: -x[1])[:10]:
        print(f"  {g}: {n} dpcm_trigger events")

    print(f"\nDMC DAC-only users ({len(summary['dmc_dac_users'])} games):")
    for g, n in sorted(summary['dmc_dac_users'], key=lambda x: -x[1])[:10]:
        print(f"  {g}: {n} direct DAC writes")

    print(f"\nGames using $4015 channel toggling ({len(summary['channel_gating_via_4015'])} games):")
    for g, n, patterns in sorted(summary['channel_gating_via_4015'], key=lambda x: -x[1])[:10]:
        print(f"  {g}: {n} distinct enable patterns: {patterns}")

    if args.json:
        out = {
            "per_game": all_stats,
            "summary": {k: v for k, v in summary.items()},
        }
        with open(args.json, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\nWrote {args.json}")


if __name__ == "__main__":
    main()
