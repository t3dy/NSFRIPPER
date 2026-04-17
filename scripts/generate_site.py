"""
Generate Jekyll pages for each game in the output directory.
Creates a games/ directory with one .md page per game listing all tracks.

Usage:
    python scripts/generate_site.py
"""

import json
import os
import mido
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
GAMES_DIR = REPO_ROOT / "games"


def load_census():
    """Load family census data for per-game classification."""
    census_path = REPO_ROOT / "data" / "family_census_v2.json"
    if not census_path.exists():
        return {}
    with open(census_path) as f:
        data = json.load(f)
    return {g['game']: g for g in data.get('games', [])}


def slugify(name):
    return name.lower().replace(" ", "-").replace("'", "").replace("_", "-").replace(".", "").replace("!", "").replace(",", "")


def get_game_info(game_dir):
    """Extract track info from a game's output directory."""
    midi_dir = game_dir / "midi"
    reaper_dir = game_dir / "reaper"
    wav_dir = game_dir / "wav"

    if not midi_dir.exists():
        return None

    tracks = []
    for f in sorted(midi_dir.iterdir()):
        if not f.suffix == ".mid":
            continue

        try:
            mid = mido.MidiFile(str(f))
        except Exception:
            continue

        # Count notes per channel and detect expansion/DMC tracks
        note_counts = []
        cc_counts = []
        expansion_chip = None
        has_dmc = False
        for t in mid.tracks:
            notes = sum(1 for m in t if m.type == "note_on")
            ccs = sum(1 for m in t if m.type == "control_change")
            if notes > 0 or ccs > 0:
                note_counts.append(notes)
                cc_counts.append(ccs)
            # Detect expansion and DMC from track names
            for m in t:
                if m.type == "track_name":
                    if "VRC6" in m.name:
                        expansion_chip = "VRC6"
                    elif "FDS" in m.name:
                        expansion_chip = "FDS"
                    # Require more than trivial activity to count as DMC-active
                    # (1 write during NSF init produces 1 note even for non-DMC games)
                    if "DMC" in m.name and notes >= 3:
                        has_dmc = True

        total_notes = sum(note_counts)
        total_ccs = sum(cc_counts)

        # Get duration
        dur_ticks = sum(msg.time for t in mid.tracks for msg in t)
        dur_sec = dur_ticks / mid.ticks_per_beat * 0.467  # approximate at ~128 BPM

        # Extract name from filename
        name = f.stem
        # Remove game prefix and version suffix
        for prefix in [game_dir.name + "_", game_dir.name.replace("_", "") + "_"]:
            if name.startswith(prefix):
                name = name[len(prefix):]
        name = name.replace("_v1", "").replace("_v2", "").replace("_nsf", "")
        name = name.replace("_", " ").strip()

        # Check if REAPER project exists
        rpp_exists = any(reaper_dir.glob(f"*{f.stem}*")) if reaper_dir.exists() else False

        tracks.append({
            "name": name,
            "midi_file": f.name,
            "notes": total_notes,
            "ccs": total_ccs,
            "duration": dur_sec,
            "has_rpp": rpp_exists,
            "expansion_chip": expansion_chip,
            "has_dmc": has_dmc,
        })

    return tracks


def generate_game_page(game_name, tracks, slug, census_entry=None):
    """Generate a Jekyll markdown page for one game."""
    clean_name = game_name.replace("_", " ").replace("  ", " ").strip()

    lines = [
        "---",
        "layout: default",
        f"title: {clean_name}",
        "---",
        "",
        f"# {clean_name}",
        "",
        f"**{len(tracks)} tracks** extracted via NSF emulation with per-frame APU register capture.",
        "",
    ]

    if census_entry:
        fam = census_entry.get('family_name', 'Unknown')
        fid = census_entry.get('family_id', '?')
        cc11 = census_entry.get('cc11_per_note', 0)
        cc12 = census_entry.get('cc12_per_note', 0)
        sub = census_entry.get('sub_group', '')
        fuzzy = census_entry.get('fuzzy_zone', False)
        fam_label = f"Family {fid}: {fam}"
        if sub:
            fam_label += f" (sub-group {sub})"
        if fuzzy:
            fam_label += " *(fuzzy zone)*"
        lines.append(f"**Driver family:** {fam_label} — CC11/note: {cc11}, CC12/note: {cc12}")
        lines.append("")

    # Detect expansion audio and DMC from track data
    expansion_chips = set(t.get("expansion_chip") for t in tracks if t.get("expansion_chip"))
    dmc_tracks = sum(1 for t in tracks if t.get("has_dmc"))
    has_dmc = dmc_tracks >= max(1, len(tracks) // 4)  # DMC counts if present in 25%+ of tracks

    base_ch = "Pulse 1, Pulse 2, Triangle, Noise"
    dmc_suffix = ", DMC (samples/DAC)" if has_dmc else ""
    dmc_count = 1 if has_dmc else 0

    if "VRC6" in expansion_chips:
        total = 7 + dmc_count
        channel_desc = f"{total}-channel MIDI (4 APU + {dmc_count} DMC + 3 VRC6: {base_ch}{dmc_suffix}, VRC6 Pulse 1, VRC6 Pulse 2, VRC6 Sawtooth)"
        lines.append("**Expansion audio:** VRC6 (2 pulse + 1 sawtooth)")
        if has_dmc:
            lines.append("**DMC:** sample playback and/or DAC writes detected")
        lines.append("")
    elif "FDS" in expansion_chips:
        total = 5 + dmc_count
        channel_desc = f"{total}-channel MIDI (4 APU + {dmc_count} DMC + 1 FDS: {base_ch}{dmc_suffix}, FDS Wavetable)"
        lines.append("**Expansion audio:** FDS (1 wavetable)")
        if has_dmc:
            lines.append("**DMC:** sample playback and/or DAC writes detected")
        lines.append("")
    elif has_dmc:
        channel_desc = f"5-channel MIDI (4 APU + 1 DMC: {base_ch}{dmc_suffix})"
        lines.append("**DMC:** sample playback and/or DAC writes detected")
        lines.append("")
    else:
        channel_desc = f"4-channel MIDI ({base_ch})"

    lines.extend([
        f"Each track includes {channel_desc} with CC11 volume envelopes and CC12 duty cycle automation, plus a REAPER project with the ReapNES NES APU synthesizer plugin loaded.",
        "",
        "## Track List",
        "",
        "| # | Track | Notes | CCs | Duration |",
        "|---|-------|-------|-----|----------|",
    ])

    for i, t in enumerate(tracks):
        dur_str = f"{int(t['duration'])}s" if t['duration'] > 0 else "—"
        lines.append(f"| {i+1} | {t['name']} | {t['notes']} | {t['ccs']} | {dur_str} |")

    total_notes = sum(t['notes'] for t in tracks)
    total_ccs = sum(t['ccs'] for t in tracks)

    lines.extend([
        "",
        f"**Total: {total_notes:,} note events, {total_ccs:,} CC automation events**",
        "",
        "## Downloads",
        "",
        "MIDI files and REAPER projects are available in the [GitHub repository](https://github.com/t3dy/NSFRIPPER).",
        "",
        "[← Back to Game Library](../)",
    ])

    return "\n".join(lines)


def main():
    GAMES_DIR.mkdir(exist_ok=True)

    census = load_census()
    game_dirs = sorted([d for d in OUTPUT_DIR.iterdir() if d.is_dir() and (d / "midi").exists()])

    print(f"Found {len(game_dirs)} games with MIDI output")
    print(f"Census data available for {len(census)} games")

    for game_dir in game_dirs:
        tracks = get_game_info(game_dir)
        if not tracks:
            continue

        slug = slugify(game_dir.name)
        census_entry = census.get(game_dir.name)
        page_content = generate_game_page(game_dir.name, tracks, slug, census_entry)

        page_path = GAMES_DIR / f"{slug}.md"
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(page_content)

        total_notes = sum(t['notes'] for t in tracks)
        print(f"  {game_dir.name}: {len(tracks)} tracks, {total_notes} notes -> {page_path.name}")

    print(f"\nGenerated {len(game_dirs)} game pages in games/")


if __name__ == "__main__":
    main()
