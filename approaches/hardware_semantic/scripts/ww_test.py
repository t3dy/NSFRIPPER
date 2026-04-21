#!/usr/bin/env python3
"""W&W Phase-1 CBG test: first 4 songs in M3U order.

Validates that liveness-driven MIDI boundaries fix the W&W bass
ring-over AND drop-out problem (Rule 34 / DESIGN.md section 3).

Pipeline per song:
  1. NSF emulation             (scripts/nsf_to_reaper.py::NsfEmulator)
  2. frames -> channels dict   (frames_to_channel_data)
  3. HW state machines         (cbg.hw_sim.simulate_hw_state) -- NEW
  4. Resolve liveness          (cbg.liveness.resolve_liveness) -- NEW
  5. CBG -> MIDI               (projection.cbg_to_midi)        -- NEW
  6. Channel audio stems       (render_channel_stems.render_stem)
  7. Assemble REAPER project   (scripts/generate_stems_rpp.py, subprocess)

Output: approaches/hardware_semantic/output/ww_test/<slug>/{midi,stems,reaper}/

Also writes the existing-pipeline MIDI side-by-side for A/B inspection
in REAPER.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent.parent.parent
APPROACH = REPO / "approaches" / "hardware_semantic"
SCRIPTS = REPO / "scripts"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# Existing pipeline pieces we reuse as-is
from nsf_to_reaper import (  # noqa: E402
    NsfEmulator, frames_to_channel_data, build_midi, period_to_midi,
    load_wizards_and_warriors_note_boundaries,
)
from render_channel_stems import render_stem, render_dmc_stem, write_wav  # noqa: E402

# New CBG pieces
from approaches.hardware_semantic.cbg.hw_sim import simulate_hw_state  # noqa: E402
from approaches.hardware_semantic.cbg.liveness import (  # noqa: E402
    resolve_liveness, summarize,
)
from approaches.hardware_semantic.projection.cbg_to_midi import (  # noqa: E402
    build_midi_from_cbg,
)


DEFAULT_NSF = REPO / "state" / "ww_ref" / (
    "Wizards & Warriors [Densetsu no Kishi - Elrond] (1987-12)(Rare)(Acclaim).nsf"
)
DEFAULT_OUT = APPROACH / "output" / "ww_test"

# M3U play order for W&W.  Columns: (m3u_index, nsf_track, slug, name, m3u_seconds).
# First 4 songs = the user's ear-test targets.
W_AND_W_FIRST_FOUR = [
    (1,  1,  "01_title",            "Wizards & Warriors Title",   36.6),
    (2,  11, "02_map",              "Map",                          4.4),
    (3,  2,  "03_forest_of_elrond", "Forest of Elrond",            77.7),
    (4,  10, "04_entering_a_door",  "Entering a Door",              1.4),
]


def run_song(emu: NsfEmulator, nsf_track: int, seconds: float, slug: str,
             song_name: str, out_root: Path, *, also_write_legacy: bool = True):
    """Run the full pipeline for one song and report liveness stats."""
    frames_target = int(seconds * 60)
    print(f"\n=== {slug}: NSF track {nsf_track}, {seconds:.1f}s ({frames_target} frames) ===")

    # ---- 1. NSF emulation ----
    frames = emu.play_song(nsf_track, frames_target)
    channels = frames_to_channel_data(frames, emu.expansion_chips)
    actual_frames = len(channels["pulse1"]["notes"])
    print(f"    captured {actual_frames} frames")

    # ---- 2. HW state machines ----
    simulate_hw_state(channels)

    # ---- 3. Resolve liveness ----
    liveness = resolve_liveness(channels)
    print("    liveness:")
    print(summarize(liveness))

    # ---- 4. CBG -> MIDI (liveness-driven boundaries) ----
    midi_dir = out_root / slug / "midi"
    midi_dir.mkdir(parents=True, exist_ok=True)
    cbg_midi = midi_dir / f"{slug}_cbg.mid"
    build_midi_from_cbg(
        channels, liveness,
        game_title="Wizards & Warriors",
        song_name=song_name,
        song_num=nsf_track,
        out_path=cbg_midi,
    )
    cbg_note_count = _count_notes(cbg_midi)
    print(f"    CBG MIDI   -> {cbg_midi.relative_to(REPO)}  ({cbg_note_count} notes)")

    # ---- 5. Legacy MIDI for A/B comparison ----
    if also_write_legacy:
        legacy_midi = midi_dir / f"{slug}_legacy.mid"
        note_boundaries = load_wizards_and_warriors_note_boundaries(
            str(emu.nsf_path), nsf_track
        )
        legacy = build_midi(
            channels,
            game_title="Wizards & Warriors",
            song_name=song_name,
            song_num=nsf_track,
            frames=None,
            period_fn=period_to_midi,
            source_text="NSF emulation (legacy boundary logic, for A/B)",
            note_boundaries=note_boundaries,
        )
        legacy.save(legacy_midi)
        legacy_note_count = _count_notes(legacy_midi)
        print(f"    legacy MIDI-> {legacy_midi.relative_to(REPO)}  ({legacy_note_count} notes)")
        cbg_per_ch = _count_notes_per_channel(cbg_midi)
        legacy_per_ch = _count_notes_per_channel(legacy_midi)
        ch_names = {0: "pulse1", 1: "pulse2", 2: "triangle", 3: "noise"}
        diffs = []
        for ch, name in ch_names.items():
            c = cbg_per_ch.get(ch, 0)
            l = legacy_per_ch.get(ch, 0)
            diffs.append(f"{name}:{c}/{l}({c - l:+d})")
        print(f"    per-ch CBG/legacy(delta):  {'  '.join(diffs)}")

    # ---- 6. Audio stems (reuse existing renderer) ----
    stems_dir = out_root / slug / "stems"
    stems_dir.mkdir(parents=True, exist_ok=True)
    _render_all_stems(channels, actual_frames, emu, stems_dir)
    print(f"    stems      -> {stems_dir.relative_to(REPO)}/")

    # ---- 7. REAPER projects (CBG + legacy MIDI, same stems, for A/B) ----
    reaper_dir = out_root / slug / "reaper"
    reaper_dir.mkdir(parents=True, exist_ok=True)
    rpp_out = reaper_dir / f"{slug}_cbg.rpp"
    _build_rpp(cbg_midi, stems_dir, rpp_out)
    print(f"    CBG RPP    -> {rpp_out.relative_to(REPO)}")
    if also_write_legacy:
        rpp_legacy = reaper_dir / f"{slug}_legacy.rpp"
        _build_rpp(legacy_midi, stems_dir, rpp_legacy)
        print(f"    legacy RPP -> {rpp_legacy.relative_to(REPO)}")

    return {
        "slug": slug, "name": song_name, "frames": actual_frames,
        "cbg_notes": cbg_note_count,
        "legacy_notes": legacy_note_count if also_write_legacy else None,
        "liveness": {
            k: {
                "audible": int((v.frames == 1).sum()),
                "silent":  int((v.frames == 0).sum()),
                "gated":   int((v.frames == -1).sum()),
                "transitions": int(sum(1 for _ in v.transitions())),
                "retriggers": int(v.retrigger.sum()),
            }
            for k, v in liveness.items()
        },
    }


def _count_notes(mid_path: Path) -> int:
    import mido
    m = mido.MidiFile(str(mid_path))
    return sum(1 for t in m.tracks for msg in t if msg.type == "note_on")


def _count_notes_per_channel(mid_path: Path) -> dict[int, int]:
    """Return {midi_channel: note_on_count}."""
    import mido
    m = mido.MidiFile(str(mid_path))
    counts: dict[int, int] = {}
    for t in m.tracks:
        for msg in t:
            if msg.type == "note_on":
                counts[msg.channel] = counts.get(msg.channel, 0) + 1
    return counts


def _render_all_stems(channels, actual_frames, emu, stems_dir: Path):
    """Render per-channel stems to WAV with shared-scale normalization."""
    raw = {}
    for key in ("p1", "p2", "tri", "noise"):
        raw[key] = render_stem(channels, actual_frames, key, normalize=False)

    has_dmc = any(n["event_type"] != "idle" for n in channels["dmc"]["notes"])
    if has_dmc:
        raw["dmc"] = render_dmc_stem(
            channels, actual_frames, emu.rom_data, emu.load_addr, normalize=False
        )

    combined = sum(raw.values())
    peak = float(np.max(np.abs(combined))) if len(combined) else 0.0
    scale = (0.9 / peak) if peak > 0 else 1.0

    name_map = {"p1": "pulse1.wav", "p2": "pulse2.wav",
                "tri": "triangle.wav", "noise": "noise.wav",
                "dmc": "dmc.wav"}
    for key, buf in raw.items():
        samples = (buf * scale * 32767).astype(np.int16)
        write_wav(samples, stems_dir / name_map[key])


def _build_rpp(midi_path: Path, stems_dir: Path, rpp_out: Path):
    """Call the existing generate_stems_rpp as a subprocess."""
    cmd = [
        sys.executable, str(SCRIPTS / "generate_stems_rpp.py"),
        "--midi", str(midi_path),
        "--stems-dir", str(stems_dir),
        "--out", str(rpp_out),
    ]
    subprocess.run(cmd, check=True, cwd=str(REPO))


def _check_disk(out_root: Path, songs, seconds_per_song: float) -> None:
    """Rule 38 pre-flight."""
    # 5 stems * seconds * 44100 * 2 bytes, ~2x for legacy RPP + MIDI + overhead
    est_bytes = sum(
        5 * seconds_per_song * 44100 * 2 * 2 for _ in songs
    )
    est_gb = est_bytes / (1024 ** 3)
    free_gb = shutil.disk_usage(str(out_root.parent.parent)).free / (1024 ** 3)
    print(f"disk: estimate {est_gb:.2f} GB for this run, {free_gb:.1f} GB free")
    if est_gb > free_gb * 0.5:
        raise SystemExit(
            f"Aborting: estimate {est_gb:.1f} GB exceeds 50% of {free_gb:.1f} GB free. "
            f"Reduce --seconds or free disk."
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nsf", type=Path, default=DEFAULT_NSF,
                    help="Path to W&W NSF (default: state/ww_ref/...)")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT,
                    help="Output root (default: approaches/hardware_semantic/output/ww_test)")
    ap.add_argument("--seconds", type=float, default=30.0,
                    help="Render cap per song, seconds (default 30).  Shorter "
                         "M3U tracks are automatically clipped.")
    ap.add_argument("--songs", type=str, default="all",
                    help="Comma-separated M3U indices 1..4, or 'all' (default).")
    args = ap.parse_args()

    if not args.nsf.is_file():
        raise SystemExit(f"NSF not found: {args.nsf}")

    if args.songs == "all":
        songs = W_AND_W_FIRST_FOUR
    else:
        picks = {int(x) for x in args.songs.split(",")}
        songs = [s for s in W_AND_W_FIRST_FOUR if s[0] in picks]

    _check_disk(args.out_dir, songs, args.seconds)

    print(f"NSF:      {args.nsf.name}")
    print(f"Output:   {args.out_dir.relative_to(REPO)}")
    print(f"Songs:    {[s[2] for s in songs]}")
    print(f"Cap:      {args.seconds}s per song (M3U durations clipped to this)")

    emu = NsfEmulator(str(args.nsf))

    summaries = []
    for m3u_idx, nsf_track, slug, name, m3u_sec in songs:
        # Per-song duration = min(M3U duration + 1s buffer, cap)
        dur = min(m3u_sec + 1.0, args.seconds)
        result = run_song(emu, nsf_track, dur, slug, name, args.out_dir)
        summaries.append(result)

    _write_readme(args.out_dir, summaries, args.seconds)
    print(f"\nDone.  Open any reaper/*.rpp in REAPER to A/B.")
    print(f"Audio stems (known-good hardware simulation) + CBG-derived MIDI (new).")


def _write_readme(out_root: Path, summaries, seconds_cap: float):
    lines = [
        "# W&W Phase-1 CBG Test Output",
        "",
        "First 4 songs in M3U play order, processed through the",
        "hardware-semantic stack (CBG middle layer) instead of the legacy",
        "boundary-map MIDI path.",
        "",
        f"Render cap: {seconds_cap:.0f} s per song (M3U durations clipped).",
        "",
        "## What to listen for",
        "",
        "Triangle bass articulation in Title and Forest of Elrond.",
        "The audio stems are rendered from the same HW simulation the",
        "stems pipeline already ear-confirmed; the CBG-derived MIDI now",
        "marks note boundaries using the same liveness logic instead of",
        "the legacy pitch-continuity + W&W-specific note_boundary_map.",
        "",
        "In REAPER, the audio track plays by default; the MIDI/JSFX track",
        "is muted.  Unmute the MIDI track to hear the current JSFX output",
        "driven by CBG-derived boundaries; compare to the audio stem (ground",
        "truth).  For legacy comparison, open `midi/<slug>_legacy.mid`.",
        "",
        "## Per-song summary",
        "",
    ]
    for s in summaries:
        lines.append(f"### {s['slug']} -- {s['name']}")
        lines.append(f"- frames captured: {s['frames']}")
        lines.append(f"- CBG notes:    {s['cbg_notes']}")
        if s['legacy_notes'] is not None:
            delta = s['cbg_notes'] - s['legacy_notes']
            lines.append(f"- legacy notes: {s['legacy_notes']}  "
                         f"(delta: {delta:+d})")
        lines.append(f"- liveness:")
        for ch, stats in s['liveness'].items():
            lines.append(
                f"    - **{ch}**: {stats['audible']} audible / {stats['silent']} silent / "
                f"{stats['gated']} gated; {stats['transitions']} transitions, "
                f"{stats['retriggers']} retriggers"
            )
        lines.append("")
    (out_root / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
