#!/usr/bin/env python3
"""Keyboard-pop A/B test: Rule 34 triangle hold in ReapNES_HW vs APU2_v2.

Produces TWO REAPER projects side by side:

  out/keyboard_pop_test/old_apu2v2.rpp   -- uses ReapNES_APU2_v2.jsfx
  out/keyboard_pop_test/new_hw.rpp       -- uses ReapNES_HW.jsfx (Rule 34 port)

Both load the same Fugue1 MIDI with W&W-style CC11 envelope on pulses
and triangle notes truncated to ~180 ms.  Each track is armed for MIDI
keyboard input so the user can play along.  Only difference between the
two projects is which plugin the JSFX block points at.

What to listen for:
  1. Let the MIDI play through the triangle voice.  Focus on each bass
     note_off transition.  Old plugin: audible vinyl-pop click at every
     release.  New plugin: clean decay via held DAC value.
  2. Play single triangle notes on a MIDI keyboard, let each fade.  Old
     plugin: pop at release.  New plugin: no pop.
  3. Pulse notes should sound the same in both -- Rule 35 (bandlimited
     pulse) is NOT yet ported.  Any bright-pitch pulse pops you hear are
     a separate issue (next fix).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import mido

REPO = Path(__file__).resolve().parent.parent.parent.parent
APPROACH = REPO / "approaches" / "hardware_semantic"
SCRIPTS = REPO / "scripts"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from generate_project import (  # noqa: E402
    rpp_header, rpp_track, APU2_DEFAULTS, JSFX_PLUGIN_APU2,
    analyze_midi, midi_track_to_events,
)

# The Rule-34-ported plugin, installed alongside APU2_v2 at the
# REAPER Effects subfolder "ReapNES Studio/".  The plugin file
# is at approaches/hardware_semantic/jsfx/ReapNES_HW.jsfx.
JSFX_PLUGIN_HW = "ReapNES Studio/ReapNES_HW.jsfx"


# Reuse W&W Title instrument profile from bach_test.py so both plugins
# play the same notes with the same settings.
from approaches.hardware_semantic.scripts.bach_test import (  # noqa: E402
    ww_slider_values, WW_TITLE_PROFILE, TRACK_COLORS,
)


def build_rpp(midi_path: Path, out_path: Path, jsfx_plugin: str) -> bool:
    info = analyze_midi(midi_path)
    stats = info["channel_stats"]
    tempo = info["tempo_bpm"]

    length = 60.0
    try:
        length = mido.MidiFile(str(midi_path)).length or 60.0
    except Exception:
        pass

    title_tag = "HW (Rule 34 port)" if "HW" in jsfx_plugin else "APU2_v2 (baseline)"
    lines = [rpp_header(tempo=tempo,
                        title=f"{midi_path.stem} -- {title_tag}")]

    nes_ch = {"pulse1": 0, "pulse2": 1, "triangle": 2, "noise": 3}
    mid = mido.MidiFile(str(midi_path))
    built_any = False
    for role, ch_idx in nes_ch.items():
        if ch_idx not in stats or stats[ch_idx].get("note_count", 0) == 0:
            continue
        ch_track = None
        sysex_trk = None
        for t in mid.tracks:
            if any(hasattr(m, "channel") and m.channel == ch_idx for m in t):
                ch_track = t
            if any(m.type == "sysex" for m in t) and not any(
                hasattr(m, "type") and m.type == "note_on" and hasattr(m, "channel") for m in t
            ):
                sysex_trk = t
        events = midi_track_to_events(ch_track, sysex_track=sysex_trk) if ch_track else None

        track_block = rpp_track(
            name=f"{WW_TITLE_PROFILE[role]['display_name']}  [{title_tag}]",
            color=TRACK_COLORS[role],
            slider_values=ww_slider_values(role),
            midi_length=length,
            armed=True,          # arm for MIDI keyboard input
            selected=not built_any,
            jsfx_plugin=jsfx_plugin,
            midi_events=events,
            ticks_per_beat=info["ticks_per_beat"],
        )
        lines.append(track_block)
        built_any = True

    if not built_any:
        return False
    lines.append(">")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--midi", type=Path,
                    default=APPROACH / "output" / "bach_test"
                            / "fugue1_C_major" / "midi"
                            / "fugue1_C_major_ww_cc.mid",
                    help="MIDI file (default: fugue1 ww_cc)")
    ap.add_argument("--out-dir", type=Path,
                    default=APPROACH / "output" / "keyboard_pop_test")
    args = ap.parse_args()

    if not args.midi.is_file():
        raise SystemExit(
            f"MIDI not found: {args.midi}\n"
            f"Run 'python approaches/hardware_semantic/scripts/bach_test.py' first."
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    local_midi = args.out_dir / args.midi.name
    shutil.copy2(args.midi, local_midi)

    old_rpp = args.out_dir / "old_apu2v2.rpp"
    new_rpp = args.out_dir / "new_hw.rpp"

    build_rpp(local_midi, old_rpp, JSFX_PLUGIN_APU2)
    build_rpp(local_midi, new_rpp, JSFX_PLUGIN_HW)

    _write_readme(args.out_dir, args.midi.name)
    print(f"Wrote:")
    print(f"  {old_rpp.relative_to(REPO)}  (uses ReapNES_APU2_v2.jsfx)")
    print(f"  {new_rpp.relative_to(REPO)}  (uses ReapNES_HW.jsfx -- Rule 34 port)")
    print(f"\nOpen both and A/B.  Each track is armed for MIDI keyboard input.")


def _write_readme(out_root: Path, midi_name: str):
    lines = [
        "# Keyboard-pop A/B test -- ReapNES_HW plugin",
        "",
        "Two REAPER projects, same MIDI, same instrument profile, **only",
        "the JSFX plugin differs**:",
        "",
        f"- `old_apu2v2.rpp` -- loads `ReapNES Studio/ReapNES_APU2.jsfx` "
        f"(the mainline plugin)",
        f"- `new_hw.rpp`     -- loads `ReapNES Studio/ReapNES_HW.jsfx` "
        f"(hardware_semantic copy with three fixes applied)",
        "",
        f"MIDI: `{midi_name}` (copied into this folder).",
        "",
        "## What changed in ReapNES_HW.jsfx (three fixes)",
        "",
        "**Fix 1: Attack Enhancer off (via slider preset).**  The plugin's",
        "`slider20` (Attack Enhancer) defaults to 0.4, firing a velocity-",
        "scaled transient burst of up to 6 NES vol units over ~20 ms on",
        "every pulse note_on.  Designed as a 'tink' for CC11-quantized game",
        "MIDIs; for live play / Bach (no CC11 automation) it's a pop per",
        "note.  All hardware_semantic RPPs now set it to 0.  Plugin header",
        "itself says: 'Set to 0 for pure hardware fidelity.'",
        "",
        "**Fix 2: Rule 34 triangle hold on gate-off** (in JSFX code).  The",
        "triangle output path has three branches (one per input-priority",
        "mode).  All three now hold the DAC value when the gate closes:",
        "",
        "| Branch | Old (`APU2_v2`) | New (`HW`) |",
        "|---|---|---|",
        "| SysEx (priority 1) | `tri_out = tt[...]`  (hold) | same -- already correct |",
        "| CC (priority 2)    | `tri_out = 0`        (pop)  | `tri_out = tt[...]`  (hold) |",
        "| ADSR (priority 3)  | `tri_out = 0`        (pop, two spots) | `tri_out = tt[...]`  (hold) |",
        "",
        "`tt[...]` is the triangle-wave lookup table evaluated at the",
        "CURRENT phase, so the DAC sits at whatever step the sequencer was",
        "paused on.  Matches real NES hardware behavior per NESdev wiki.",
        "",
        "**Fix 3: Rule 33 LP + DC blocker at output** (in JSFX code).  This",
        "is the main fix for on-hit / on-release pops: when `p1_en` flips",
        "from 0 to 1 on note_on, `out` jumps from 0 to approximately +/-0.5",
        "in a single sample.  That's broadband energy -> audible click.",
        "",
        "New output chain: channel mix -> HP440 (existing) -> **2-pole",
        "Butterworth LP at 14 kHz** -> **1-pole HP at 10 Hz (DC blocker)**",
        "-> output.  Same design as `scripts/render_channel_stems.py`",
        "`apply_nes_analog_lp()` + `dc_block()`.  The LP spreads 1-sample",
        "steps across ~4 samples (~90 us), well below the ear's click",
        "threshold.  The HP removes any DC offset from stuck triangle holds",
        "or duty-asymmetric pulse averages.",
        "",
        "## What to listen for",
        "",
        "1. **Note-on / note-off clicks.** Play the MIDI, play single",
        "   keyboard notes.  Old: pop per note on hit and release.  New:",
        "   smooth attack, smooth release.  The LP filter is doing most",
        "   of this work.",
        "2. **Triangle note-off specifically.** With Rule 34 hold, triangle",
        "   notes should decay into silence rather than step to zero.",
        "3. **High-pitched pulse timbre.** The 14 kHz LP takes edge off the",
        "   pulse-edge aliasing grit that Rule 35 would fully solve.  If",
        "   bright pulse notes still sound wrong (hissy / gritty rather",
        "   than clicky), Rule 35 is the next port (analytical-integral",
        "   bandlimited pulse synthesis).",
        "4. **Nothing else should sound different.**  Game stems in other",
        "   projects continue to use the mainline `ReapNES_APU2.jsfx` and",
        "   are unchanged by this work.",
        "",
        "## Rolling back",
        "",
        "If the new plugin sounds wrong, just delete it:",
        "",
        "```",
        "rm 'C:\\Users\\PC\\AppData\\Roaming\\REAPER\\Effects\\ReapNES Studio\\ReapNES_HW.jsfx'",
        "```",
        "",
        "REAPER falls back to showing the projects with a missing-plugin",
        "error on `new_hw.rpp` only.  `old_apu2v2.rpp` and every other",
        "existing project is unaffected -- this plugin lives parallel to",
        "APU2_v2, not in place.",
        "",
        "## If the fix sounds right",
        "",
        "The change in the repo is at",
        "`approaches/hardware_semantic/jsfx/ReapNES_HW.jsfx`.  We can then",
        "choose: keep the new plugin as the hardware-semantic path's",
        "default (design doc Phase 3), or backport the same three-line",
        "change into the mainline `studio/jsfx/ReapNES_APU2_v2.jsfx`.",
        "The second option updates every existing RPP without renaming",
        "plugins.",
    ]
    (out_root / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
