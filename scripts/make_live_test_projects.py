"""
make_live_test_projects.py

Build REAPER test projects tuned for LIVE keyboard play of three games:
  - Super Mario Bros (Overworld feel)
  - Legend of Zelda (Dungeon feel)
  - Marble Madness (Stage 1 Rare plucky feel)

Each project has 4 tracks (P1/P2/Triangle/Noise), all armed, keyboard mode ON,
ReapNES_APU2_v2.jsfx loaded with per-game sliders tuned to match the game's
envelope/duty character.  Velocity -> volume+transient (PAL Must-do #1),
mod wheel -> duty (Must-do #2), aftertouch -> vibrato (Must-do #3), and
the low-C keyswitch (MIDI note 24 by default) fires a phase-reset tick
(Should-do #7).

Output: test_projects/live_<game>/<game>.rpp

No MIDI items, no stems -- this is a pure live-play scratch pad.
The user plays the keyboard and picks which track to solo/arm.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from generate_project import rpp_header, rpp_track, make_guid  # type: ignore

V2_PLUGIN = "ReapNES Studio/ReapNES_APU2_v2.jsfx"

# ---------------------------------------------------------------------------
# v2 slider layout (1-indexed; 0-indexed here):
#   [ 0] slider1  Channel Mode (0=P1, 1=P2, 2=Tri, 3=Noise, 4=Full)
#   [ 1] slider2  Keyboard Mode (1=ON)
#   [ 2] slider3  P1 Duty (0-3 -> 12.5/25/50/75%)
#   [ 3] slider4  P1 Volume (0-15)
#   [ 4] slider5  P1 Attack (ms)
#   [ 5] slider6  P1 Decay  (ms)
#   [ 6] slider7  P1 Sustain (0-15)
#   [ 7] slider8  P1 Release (ms)
#   [ 8] slider9  P2 Duty
#   [ 9] slider10 P2 Volume
#   [10] slider11 P2 Attack
#   [11] slider12 P2 Decay
#   [12] slider13 P2 Sustain
#   [13] slider14 P2 Release
#   [14] slider15 Tri Attack (ms)
#   [15] slider16 Tri Release (ms)
#   [16] slider17 Noise Attack
#   [17] slider18 Noise Decay
#   [18] slider19 Master Gain
#   [19] slider20 Attack Enhancer (0-1)
#   [20] slider21 Enhancer Decay (5-80 ms)
#   [21] slider22 Phase-Reset Keyswitch Note (MIDI 0-60)
# ---------------------------------------------------------------------------

CH_MODE = {"pulse1": 0, "pulse2": 1, "triangle": 2, "noise": 3}

# Per-game envelope/duty presets.  See docs/DRIVER_FAMILIES_AND_GAMES.md and
# .claude/rules/synth_fidelity.md Rule 8 for the family -> ADSR mapping.
PRESETS = {
    # Nintendo driver, Family 1B.  Overworld: bright square lead, staccato
    # triangle bass, crisp noise drum hits (length-counter silenced per
    # architecture.md Rule 32).
    "Super_Mario_Bros": {
        "title": "Super Mario Bros Overworld - Live Keyboard",
        "p1":    {"duty": 2, "vol": 15, "atk": 0, "dec":  40, "sus": 11, "rel":  60},
        "p2":    {"duty": 1, "vol": 15, "atk": 0, "dec":  30, "sus":  9, "rel":  50},
        "tri":   {"atk": 0, "rel":  30},
        "noi":   {"atk": 0, "dec":  80},
        "enh":   0.5,
        "enh_ms": 20,
        "keysw": 24,
    },
    # Nintendo driver, Family 1B.  Dungeon: sustained darker mood, longer
    # release, triangle pad-like, noise as sparse atmospheric hits.
    "Legend_of_Zelda_The": {
        "title": "Legend of Zelda Dungeon - Live Keyboard",
        "p1":    {"duty": 2, "vol": 15, "atk": 0, "dec": 120, "sus": 10, "rel": 180},
        "p2":    {"duty": 2, "vol": 15, "atk": 0, "dec": 150, "sus":  8, "rel": 180},
        "tri":   {"atk": 0, "rel": 120},
        "noi":   {"atk": 0, "dec": 150},
        "enh":   0.3,
        "enh_ms": 25,
        "keysw": 24,
    },
    # Rare driver, Family 1A.  Marble Madness Stage 1 (Brad Fuller / Hal
    # Canon): plucky 25% duty, hardware decay from full vol to zero with no
    # sustain -- classic Rare "bouncy" sound.  Envelope mimics HW-only decay.
    "Marble_Madness": {
        "title": "Marble Madness Stage 1 - Live Keyboard",
        "p1":    {"duty": 1, "vol": 15, "atk": 0, "dec": 250, "sus":  0, "rel":  30},
        "p2":    {"duty": 1, "vol": 15, "atk": 0, "dec": 250, "sus":  0, "rel":  30},
        "tri":   {"atk": 0, "rel":  80},
        "noi":   {"atk": 0, "dec": 100},
        "enh":   0.6,
        "enh_ms": 15,
        "keysw": 24,
    },
}


def v2_sliders(preset: dict, channel: str) -> list[float]:
    """Build a 22-slot slider list for ReapNES_APU2_v2 with the given preset."""
    p1, p2, tri, noi = preset["p1"], preset["p2"], preset["tri"], preset["noi"]
    vals = [
        CH_MODE[channel],          # 0  ch_mode
        1,                         # 1  kb_mode ON
        p1["duty"], p1["vol"], p1["atk"], p1["dec"], p1["sus"], p1["rel"],  # 2-7
        p2["duty"], p2["vol"], p2["atk"], p2["dec"], p2["sus"], p2["rel"],  # 8-13
        tri["atk"], tri["rel"],    # 14-15
        noi["atk"], noi["dec"],    # 16-17
        0.2,                       # 18 master gain (keyboard-safe)
        preset["enh"],             # 19 attack enhancer
        preset["enh_ms"],          # 20 enhancer decay ms
        preset["keysw"],           # 21 keyswitch note
    ]
    return vals


TRACK_COLORS = {
    "pulse1":   0x01C0C0FF,  # cyan
    "pulse2":   0x01FFC000,  # amber
    "triangle": 0x01FF40FF,  # magenta
    "noise":    0x01808080,  # gray
}

TRACK_NAMES = {
    "pulse1":   "P1 Lead (Pulse 1)",
    "pulse2":   "P2 Harmony (Pulse 2)",
    "triangle": "Tri Bass (Triangle)",
    "noise":    "Noise / Drums",
}


def build_project(game_slug: str, preset: dict) -> str:
    """Assemble the full RPP text for one game."""
    parts = [rpp_header(tempo=120.0, title=preset["title"])]
    for i, ch in enumerate(("pulse1", "pulse2", "triangle", "noise")):
        vals = v2_sliders(preset, ch)
        parts.append(rpp_track(
            name=TRACK_NAMES[ch],
            color=TRACK_COLORS[ch],
            slider_values=vals,
            armed=True,
            selected=(i == 0),
            jsfx_plugin=V2_PLUGIN,
        ))
    parts.append(">\n")
    return "\n".join(parts)


def main() -> int:
    out_root = Path("test_projects")
    out_root.mkdir(exist_ok=True)
    for slug, preset in PRESETS.items():
        game_dir = out_root / f"live_{slug}"
        game_dir.mkdir(exist_ok=True)
        rpp_path = game_dir / f"{slug}_live.rpp"
        rpp_path.write_text(build_project(slug, preset), encoding="ascii")
        print(f"[+] {rpp_path}")
    print("\nDone.  Load any .rpp in REAPER, arm one or more tracks,")
    print("play keyboard.  Mod wheel -> duty, aftertouch -> vibrato,")
    print("low C (MIDI 24) -> phase-reset tick.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
