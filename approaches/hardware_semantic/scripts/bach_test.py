#!/usr/bin/env python3
"""Bach MIDIs through the three W&W Title synth instruments.

Each Bach voice is routed to one of the three W&W Title voicings
(pulse1 lead, pulse2 harmony, triangle bass).  Track names in the
REAPER mixer identify which instrument is playing which voice.

No audio stems -- the JSFX synth is the only sound source.  You can
tweak sliders live and play along on a MIDI keyboard (the plugin
drops to priority-3 ADSR mode when MIDI has no CC automation, which
is the case for these Bach MIDIs).

Output: approaches/hardware_semantic/output/bach_test/<slug>/reaper/<slug>.rpp

W&W Title instrument profiles are derived from the W&W Title MIDI
extracted in approaches/hardware_semantic/output/ww_test/01_title/:

  Pulse 1 (lead)     duty 25%, driver-driven envelope (peak 15 -> ~8 sustain)
  Pulse 2 (harmony)  duty 25%, same envelope shape as pulse 1
  Triangle (bass)    gate-only (triangle has no volume), 1 octave below pulses

For Bach playback, the pulse envelopes are ADSR-approximated because Bach
MIDIs have no CC11 automation (which is what drives per-frame volume in
the game MIDIs).  The ADSR values below match the CC11 range 8..120 that
W&W Title actually writes.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import uuid
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
from approaches.hardware_semantic.projection.ww_envelope import (  # noqa: E402
    inject_ww_envelope,
)


# ---------------------------------------------------------------------------
# W&W Title instrument profiles
# ---------------------------------------------------------------------------
# APU2 slider layout (0-indexed, matches APU2_DEFAULTS):
#   0: Channel Mode     (0=P1, 1=P2, 2=Tri, 3=Noise, 4=Full APU)
#   1: Keyboard Mode    (0=Off, 1=On)
#   2: P1 Duty          (0-3)
#   3: P1 Volume        (0-15)
#   4: P1 Attack (ms)
#   5: P1 Decay  (ms)
#   6: P1 Sustain       (0-15)
#   7: P1 Release(ms)
#   8: P2 Duty          (0-3)
#   9: P2 Volume        (0-15)
#   10: P2 Attack (ms)
#   11: P2 Decay  (ms)
#   12: P2 Sustain      (0-15)
#   13: P2 Release (ms)
#   14: Tri Attack (ms)
#   15: Tri Release(ms)
#   16: Noise Attack (ms)
#   17: Noise Decay  (ms)
#   18: Master Gain
#   19: Attack Enhancer (v2 addition)
#   20: Enhancer Decay (ms)

# Derived from W&W Title MIDI analysis (see docstring).
WW_TITLE_PROFILE = {
    "pulse1": {  # lead voice -- bright, fast-decay character
        "duty": 1,          # 25%
        "vol": 15,
        "atk": 0,           # instant attack
        "dec": 100,         # decay to sustain in 100 ms
        "sus": 8,           # mid sustain (matches CC11 median of 88 -> 11/15)
        "rel": 60,
        "display_name": "W&W Title Pulse 1 (lead, 25% duty)",
    },
    "pulse2": {  # harmony voice -- same character as pulse 1
        "duty": 1,          # 25% (W&W title uses 25% predominantly; one brief
                            # 50% excursion that we don't capture in ADSR)
        "vol": 15,
        "atk": 0,
        "dec": 100,
        "sus": 8,
        "rel": 60,
        "display_name": "W&W Title Pulse 2 (harmony, 25% duty)",
    },
    "triangle": {  # bass voice -- gate only, no volume envelope (HW limit)
        "atk": 0,
        "rel": 40,
        "display_name": "W&W Title Triangle (bass)",
    },
    "noise": {
        "atk": 0,
        "dec": 100,
        "display_name": "W&W Title Noise (drums)",
    },
}


def ww_slider_values(channel: str) -> list[float]:
    """Return W&W Title sliders for the named channel.

    Starts from APU2_DEFAULTS, overrides the channel-specific fields
    from WW_TITLE_PROFILE, and sets the Channel Mode so one plugin
    instance voices exactly one NES channel.

    Also forces slider20 (Attack Enhancer) to 0.  The plugin's default
    of 0.4 fires a velocity-scaled transient burst of up to 6 NES vol
    units over ~20 ms on every pulse note_on (lines 543/547 of
    ReapNES_APU2_v2.jsfx).  Designed as a 'tink' on CC11-quantized game
    MIDIs, but for Bach (hundreds of notes/minute, no frame-level CC11
    changes) it produces an audible pop per note.  The plugin's own
    header says: 'Set to 0 for pure hardware fidelity.'
    """
    vals = list(APU2_DEFAULTS)
    vals[0] = {"pulse1": 0, "pulse2": 1, "triangle": 2, "noise": 3}[channel]
    p = WW_TITLE_PROFILE[channel]

    if channel == "pulse1":
        vals[2] = p["duty"]
        vals[3] = p["vol"]
        vals[4] = p["atk"]
        vals[5] = p["dec"]
        vals[6] = p["sus"]
        vals[7] = p["rel"]
    elif channel == "pulse2":
        vals[8] = p["duty"]
        vals[9] = p["vol"]
        vals[10] = p["atk"]
        vals[11] = p["dec"]
        vals[12] = p["sus"]
        vals[13] = p["rel"]
    elif channel == "triangle":
        vals[14] = p["atk"]
        vals[15] = p["rel"]
    elif channel == "noise":
        vals[16] = p["atk"]
        vals[17] = p["dec"]

    # APU2_DEFAULTS is 19 entries long (slider1..slider19); extend to
    # 21 so we can explicitly set slider20 (Attack Enhancer) and
    # slider21 (Enhancer Decay).  Without this, slider20 falls back
    # to the plugin's own default of 0.4.
    while len(vals) < 21:
        vals.append(0)
    vals[19] = 0     # slider20: Attack Enhancer OFF
    vals[20] = 20    # slider21: Enhancer Decay (harmless when enhancer=0)

    return vals


# Per-channel PEAKCOL colors -- same palette the main pipeline uses.
TRACK_COLORS = {
    "pulse1":   16711680,  # red
    "pulse2":   65280,     # green
    "triangle": 255,       # blue
    "noise":    16776960,  # yellow
}


# ---------------------------------------------------------------------------
# Piece selection
# ---------------------------------------------------------------------------

DEFAULT_PICKS = [
    # (slug,                 source_dir_under_outputv6_bach,         notes)
    ("invent1_C_major",
     "invent1_Castlevania_VampireKiller",
     "Two-Part Invention No.1 in C (BWV 772), 2 voices (pulse1 + pulse2)."),
    ("invent4_D_minor",
     "invent4_Castlevania_NothingToLose",
     "Two-Part Invention No.4 in D minor (BWV 775), 2 voices."),
    ("fugue1_C_major",
     "Fugue1_Castlevania_VampireKiller",
     "WTC Book 1, Fugue No.1 in C major (BWV 846), 3 voices (pulse1 + pulse2 + triangle)."),
    ("fugue2_C_minor",
     "Fugue2_Castlevania_NothingToLose",
     "WTC Book 1, Fugue No.2 in C minor (BWV 847), 3 voices."),
]


# ---------------------------------------------------------------------------
# RPP builder -- MIDI + JSFX only, with labeled W&W Title instruments per track
# ---------------------------------------------------------------------------

def build_ww_title_rpp(midi_path: Path, out_path: Path) -> bool:
    """Build a Variant-B style RPP with W&W Title instruments per track.

    One track per active NES channel; the Channel Mode slider + instrument-
    name in the track header say exactly which instrument is playing.
    """
    info = analyze_midi(midi_path)
    stats = info["channel_stats"]
    tempo = info["tempo_bpm"]

    length = 60.0
    try:
        length = mido.MidiFile(str(midi_path)).length or 60.0
    except Exception:
        pass

    lines = [rpp_header(tempo=tempo,
                        title=f"{midi_path.stem} -- W&W Title instruments")]

    nes_ch = {"pulse1": 0, "pulse2": 1, "triangle": 2, "noise": 3}

    mid = mido.MidiFile(str(midi_path))
    built_any = False
    for role, ch_idx in nes_ch.items():
        if ch_idx not in stats or stats[ch_idx].get("note_count", 0) == 0:
            continue
        # Pull this channel's MIDI events
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
            name=WW_TITLE_PROFILE[role]["display_name"],
            color=TRACK_COLORS[role],
            slider_values=ww_slider_values(role),
            midi_length=length,
            armed=False,
            selected=not built_any,        # first track gets SEL 1
            jsfx_plugin=JSFX_PLUGIN_APU2,
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


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path,
                    default=APPROACH / "output" / "bach_test",
                    help="Output root (default: approaches/hardware_semantic/output/bach_test)")
    ap.add_argument("--bach-dir", type=Path,
                    default=REPO / "outputv6_bach",
                    help="Directory containing <pick>/<pick>.mid")
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    built = []
    for slug, src_dir, notes in DEFAULT_PICKS:
        src_midi = args.bach_dir / src_dir / f"{src_dir}.mid"
        if not src_midi.is_file():
            print(f"  SKIP  {slug}  (missing {src_midi})")
            continue

        piece_dir = args.out_dir / slug
        midi_dir = piece_dir / "midi"
        reaper_dir = piece_dir / "reaper"
        midi_dir.mkdir(parents=True, exist_ok=True)
        reaper_dir.mkdir(parents=True, exist_ok=True)

        bare_midi = midi_dir / f"{slug}_bare.mid"
        shutil.copy2(src_midi, bare_midi)

        # CC-automated variant (priority-2 mode, closer to W&W Title tone)
        auto_midi = midi_dir / f"{slug}_ww_cc.mid"
        stats = inject_ww_envelope(bare_midi, auto_midi)

        # Build two RPPs -- one ADSR-only (priority-3) and one CC-automated
        # (priority-2).  Same instrument settings on both; the only
        # difference is which MIDI is loaded.
        rpp_adsr = reaper_dir / f"{slug}_adsr.rpp"
        rpp_cc = reaper_dir / f"{slug}_ww_cc.rpp"
        ok_adsr = build_ww_title_rpp(bare_midi, rpp_adsr)
        ok_cc = build_ww_title_rpp(auto_midi, rpp_cc)
        if not (ok_adsr and ok_cc):
            print(f"  FAIL  {slug}")
            continue

        # Point rpp_path at the CC variant for the summary / default
        rpp_path = rpp_cc

        # Which channels ended up active
        mid = mido.MidiFile(str(bare_midi))
        active_channels = set()
        for t in mid.tracks:
            for msg in t:
                if msg.type == "note_on" and msg.velocity > 0:
                    active_channels.add(msg.channel)
        roles = []
        for ch in sorted(active_channels):
            role = {0: "pulse1", 1: "pulse2", 2: "triangle", 3: "noise"}.get(ch)
            if role:
                roles.append(role)
        print(f"  OK    {slug}  ({'+'.join(roles)})  "
              f"CC events: {stats['cc_events_inserted']} on {stats['notes_automated']} pulse notes, "
              f"triangle notes truncated: {stats['triangle_truncated']} "
              f"(cap {stats['triangle_max_ticks']} ticks)")
        print(f"        CC variant:   {rpp_cc.relative_to(REPO)}")
        print(f"        ADSR variant: {rpp_adsr.relative_to(REPO)}")
        built.append((slug, notes, rpp_cc, rpp_adsr, roles, stats))

    _write_readme(args.out_dir, built)
    print(f"\nBuilt {len(built)} Bach REAPER projects in {args.out_dir.relative_to(REPO)}/")
    print("Each track is labeled with its W&W Title instrument.")
    print("Open any reaper/*.rpp in REAPER; the JSFX synth is the only sound source.")


def _write_readme(out_root: Path, built):
    lines = [
        "# Bach through the W&W Title synth instruments",
        "",
        "Each Bach MIDI is delivered as **two REAPER projects**:",
        "",
        "- `<slug>_ww_cc.rpp` -- **priority-2 mode** (CC11 envelope injected per note).",
        "  Closest to the W&W Title tone: sharp attack at peak 120, linear",
        "  software decay by 4 CC11 units per frame, floor at 8.  Every held",
        "  note continues decaying, which is where the *plinkiness* comes from.",
        "- `<slug>_adsr.rpp` -- **priority-3 mode** (ADSR-only, no CC automation).",
        "  Smoother / more organ-like because ADSR sustain=8 holds after decay.",
        "  Useful for comparison; closer to how a MIDI keyboard through the plugin",
        "  would sound.",
        "",
        "Both projects have identical track setup + JSFX slider settings; the only",
        "difference is the MIDI file loaded.  Same rendering chain, same instruments --",
        "the tone difference is entirely the priority-2 CC envelope vs priority-3 ADSR.",
        "",
        "## W&W Title instrument profiles",
        "",
        "| NES voice | Duty | ADSR (atk/dec/sus/rel) | Role in the Title |",
        "|---|---|---|---|",
        f"| **Pulse 1 (lead)**    | 25% | 0 / 100 ms / 8 / 60 ms | Main melody |",
        f"| **Pulse 2 (harmony)** | 25% | 0 / 100 ms / 8 / 60 ms | Countermelody |",
        f"| **Triangle (bass)**   | n/a | 0 ms attack, 40 ms release | Bassline (gate-only) |",
        "",
        "ADSR numbers are derived from the CBG analysis of",
        "`approaches/hardware_semantic/output/ww_test/01_title/midi/01_title_cbg.mid`",
        "(pulse channels write duty 25% for ~100% of the song; CC11 ranges 8..120).",
        "",
        "## What the `_ww_cc.mid` pipeline does to each voice",
        "",
        "**Pulse 1 / Pulse 2 (lead + harmony):** inject a per-frame CC11",
        "decay envelope onto every note.  Starts at 120 on note_on, drops",
        "4 CC11 units per 60 Hz frame, floors at 8.  The JSFX plugin runs",
        "in priority-2 mode (CC-driven volume) and ignores ADSR.  Held",
        "notes decay toward silence instead of plateauing at sustain=8,",
        "which is where the *plinky* character comes from.",
        "",
        "```",
        "Frame 0:  note_on vel=120        (NES vol 15 -- attack)",
        "Frame 1:  CC11=116",
        "Frame 2:  CC11=112",
        "...",
        "Frame N:  CC11=max(8, 120 - 4*N)",
        "```",
        "",
        "Slope matches the W&W Title driver (~8 CC units per 2 frames,",
        "CC11 range 8..120 observed in the game MIDI).",
        "",
        "**Triangle (bass):** truncate any note longer than ~180 ms.  The",
        "plugin does NOT gate triangle on CC11 mid-note (triangle has no",
        "HW volume, so the CC path only flips CC-mode on/off).  In the real",
        "game, each triangle note rings for ~100-200 ms then the hardware",
        "linear counter decays to zero.  Without truncation, Bach bass",
        "notes (half / whole notes at 500 ms+) play their full length and",
        "the result sounds droning, not plinky.  Truncation mimics the",
        "linear counter decay while letting Bach's note timing drive the",
        "retriggers.",
        "",
        "Short notes (< 180 ms) pass through unchanged -- e.g., fugue1",
        "had 8 notes already under the cap and 136 that got truncated;",
        "the natural staccato character of Bach fugue bass lines is preserved.",
        "",
        "## Pieces",
        "",
    ]
    role_label = {
        "pulse1": "Pulse 1 (lead)",
        "pulse2": "Pulse 2 (harmony)",
        "triangle": "Triangle (bass)",
        "noise": "Noise (drums)",
    }
    for slug, notes, rpp_cc, rpp_adsr, roles, stats in built:
        role_list = ", ".join(role_label[r] for r in roles)
        lines.append(f"### {slug}")
        lines.append("")
        lines.append(notes)
        lines.append("")
        lines.append(f"- Instruments: **{role_list}**")
        lines.append(f"- CC events injected: {stats['cc_events_inserted']} across "
                     f"{stats['notes_automated']} pulse notes")
        lines.append(f"- Priority-2 (plinky): [{rpp_cc.name}]({rpp_cc.relative_to(out_root).as_posix()})")
        lines.append(f"- Priority-3 (ADSR):   [{rpp_adsr.name}]({rpp_adsr.relative_to(out_root).as_posix()})")
        lines.append("")
    lines.append("## Mixer labels")
    lines.append("")
    lines.append("Track names in REAPER:")
    lines.append("")
    lines.append("- `W&W Title Pulse 1 (lead, 25% duty)`")
    lines.append("- `W&W Title Pulse 2 (harmony, 25% duty)`")
    lines.append("- `W&W Title Triangle (bass)`")
    lines.append("")
    lines.append("## Tweaking the envelope")
    lines.append("")
    lines.append("If the `_ww_cc` version decays too fast or too slow for your ear:")
    lines.append("")
    lines.append("- Edit `approaches/hardware_semantic/projection/ww_envelope.py`:")
    lines.append("    - `CC_DECAY_PER_FRAME = 4` -- drop to 2 for slower/longer tail,")
    lines.append("      raise to 6-8 for snappier plink.")
    lines.append("    - `CC_DECAY_FLOOR = 8` -- lower to 4 or 2 for deeper fade-out,")
    lines.append("      raise to 12 for less decay (more sustain).")
    lines.append("    - `CC_DECAY_START = 120` -- lower to 104 or 96 for a softer attack.")
    lines.append("- Re-run `python approaches/hardware_semantic/scripts/bach_test.py`.")
    lines.append("")
    lines.append("## What to listen for")
    lines.append("")
    lines.append("- Compare the two RPPs for each piece: `_ww_cc` should sound *plinkier*,")
    lines.append("  `_adsr` should sound *smoother*.")
    lines.append("- Long held Bach notes are the strongest reveal: in `_ww_cc` they decay")
    lines.append("  audibly toward silence over half a second; in `_adsr` they plateau.")
    lines.append("- Same-pitch retriggers should click cleanly in both, no ring-over.")
    (out_root / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
