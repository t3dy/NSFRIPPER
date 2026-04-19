# Integrated approaches to the keyboard-input problem

Every technique the project has touched, combined into a single menu of
architectures for "MIDI keyboard → NES-like audio in REAPER."  Some
are what we already ship; some are what we've researched but not
built; some bridge the stems pipeline and the live synth.  All are
listed so you can pick which to try next.

The problem this doc answers:

> "We should have approaches to the keyboard input that integrate or
> experiment with all the methods and goals we've had expressed in my
> descriptions of the project.  Give me a list of approaches to the
> keyboard input problem with different ways to design a synthesizer
> and MIDI combo or other ways of bringing the game data into REAPER
> plugin translations like the Python method we explored."

## The pieces the project has produced

Before listing approaches, inventory the assets that can be recombined:

- **Per-frame register state extraction** (py65 NSF emulator →
  Frame IR).
- **MIDI with CC11/CC12 + SysEx** (our NSF-extraction format).
- **ROM parsers** (CV1, Contra, W&W — trace-validated extraction).
- **Python stems DSP** (bandlimited pulse, non-linear mix, LP +
  DC blocker; see Rules 27-35).
- **JSFX synth** (`ReapNES_APU2_v2.jsfx`, real-time, 3-priority
  input cascade).
- **Driver family presets** per game's characteristic sound.
- **Oracle DB** of hardware facts, driver families, decision records.
- **Audit / naming pipeline** (sidecar JSON, deterministic rename,
  truncation detection).

Each approach below picks a subset and composes them in a specific
way for the live-keyboard use case.

## The 12 approaches

### Approach A — Current design: JSFX three-priority cascade

**What**: the existing `ReapNES_APU2_v2.jsfx`.  P1 SysEx / P2 CC /
P3 ADSR.

**Live MIDI keyboard path**: hit a key → P3 ADSR mode → preset-
driven sound.

**Strengths**: already works; zero new code; integrates with file
playback.

**Gaps**: JSFX P3 sound not yet at Python-stem quality (missing
Rules 30/33/35 ports).

**How to improve**: port Rules 34-35 to JSFX (the
`keyboard_lab/docs/PERFORMANCE_MAPPINGS.md` mapping #7 path).

**Time to ship**: already shipped.  5 hours to port remaining DSP.

### Approach B — Replace JSFX P3 with Plogue chipsounds or similar commercial VSTi

**What**: keep the SysEx/CC file-playback path; replace the ADSR
live path with a commercial NES VSTi (Plogue chipsounds, Triforce,
or similar).

**Live MIDI keyboard path**: MIDI → commercial VSTi → sound.  Use
our JSFX only for file-driven SysEx replay.

**Strengths**: likely better live sound out of the box; zero DSP
writing.

**Gaps**: requires paid plugin ($95 chipsounds); two different
plugins means two different sound profiles; routing SysEx to the
commercial VSTi is unlikely to work (they don't parse our custom
SysEx).

**Time to ship**: 1-2 hours to set up, test.

### Approach C — Python live daemon: NES emulation as a live synth

**What**: run py65 emulation in a Python daemon that accepts live
MIDI and emits audio through PyAudio.  Essentially turn our NSF
emulator into a real-time synth.

**Live MIDI keyboard path**: keyboard → MIDI → Python daemon →
py65 PLAY(note) → register state → Python DSP → audio out → REAPER
sees it as an audio input.

**Strengths**: same exact DSP as stems — bit-identical live + stems.
Exotic but intriguing.

**Gaps**: py65 is ~3-6x too slow for real-time.  Requires either a
py65 rewrite (Rust + pyo3) or a fundamentally different emulator
backend.

**Time to ship**: 2-4 weeks.  Gated on emulator speed.

### Approach D — FamiStudio as the live backend

**What**: FamiStudio (open-source NES music tracker) has a VST or
standalone mode.  Route live MIDI to it.  Use our extracted MIDI as
FamiStudio input.

**Live MIDI keyboard path**: keyboard → FamiStudio VST → audio.

**Strengths**: FamiStudio's DSP is battle-tested and community-
maintained.  Likely reference-grade sound.

**Gaps**: may not support arbitrary MIDI input (it's a tracker,
not a general synth).  MIDI ↔ FamiStudio FTM translation is
non-trivial.

**Time to ship**: 2-3 days (research + integration).

### Approach E — Sample-based: multi-sample library from Python stems

**What**: use our Python-rendered stems to build a SoundFont or
Kontakt instrument.  Record every channel × pitch × duty × volume
combination.  Keyboard plays the pre-rendered samples through a
standard sampler.

**Live MIDI keyboard path**: keyboard → MIDI → sampler → pitch-
shifted pre-rendered sample.

**Strengths**: samples are literally the Python DSP output.  Live
and stems sound identical by construction.  Works with any DAW, not
just REAPER.

**Gaps**: dense sample grid required (4 duties × 60 notes × 16
volumes = ~4000 samples just for pulse).  Pitch-shifting between
samples introduces crossfade artifacts.  Can't animate duty without
per-sample selection.

**Time to ship**: 2-3 days for grid generation + sampler mapping.

### Approach F — Hardware bridge: MIDINES cartridge

**What**: buy a MIDINES cartridge ($150) that turns a real NES into
a live MIDI synth.  Capture its RCA out via audio interface.

**Live MIDI keyboard path**: keyboard → USB MIDI → MIDINES cartridge
→ real NES → RCA out → audio interface → REAPER.

**Strengths**: actual hardware.  Maximum fidelity by definition —
the real NES is synthesizing the audio.

**Gaps**: hardware cost; latency of ~20-40 ms round trip; requires
real NES console.  MIDI → NES command translation is MIDINES's
proprietary tech, limited expressiveness.

**Time to ship**: 1-2 days after hardware arrives.

### Approach G — Python stems as fallback, JSFX as primary

**What**: in the live REAPER project, load BOTH the JSFX (for live
play) AND the pre-rendered stems (as muted reference tracks).  User
plays JSFX live; when they want to compare, they unmute stems.

**Live MIDI keyboard path**: keyboard → JSFX → audio.  Stems are
just available as a reference.

**Strengths**: what our current Variant A does.  Unambiguous.

**Gaps**: stems vs JSFX sound different.  User has to know this.

**Time to ship**: already shipped as Variant A.

### Approach H — Python-rendered stems triggered by MIDI (sample & hold)

**What**: each stem WAV is associated with a specific NSF track.
MIDI keyboard triggers the whole stem as one sample (like loading
a song into a sampler).  Hit C4, plays that song's pulse1 stem.

**Live MIDI keyboard path**: keyboard key → sample triggered →
stem plays from start.

**Strengths**: instant "play the game's music" trigger; useful for
mashups.

**Gaps**: not actually a synth.  You're triggering pre-recorded
tracks.  Not performable in any traditional sense.

**Time to ship**: 4 hours.  Useful for DJ-style live sets; not for
musical composition.

### Approach I — Hybrid: JSFX for pulse/triangle, samples for DMC/noise

**What**: use JSFX for pulse/triangle (where live synthesis is
straightforward), use pre-sampled DMC and noise drums from Python
stems.  MIDI keyboard drives both.

**Live MIDI keyboard path**: keyboard notes on pitched channels →
JSFX; keyboard pads on low range → triggered DMC/noise samples.

**Strengths**: plays to each technology's strength.  Pitched
content synthesized; percussive content sampled for realism.

**Gaps**: requires splitting MIDI routing by keyboard zone.  Not
hard but needs setup.

**Time to ship**: 1 day.

### Approach J — ReaScript offline render (Option C of our variants)

**What**: render JSFX output to WAV stems via REAPER's offline
render path.  Each game gets pre-rendered JSFX stems.  Live
playback uses JSFX; recorded playback uses the JSFX-rendered
stems.

**Live MIDI keyboard path**: same as Approach A (JSFX live).  The
JSFX-rendered stems are the archival companion.

**Strengths**: live + archival are bit-identical.  Clean story.

**Gaps**: requires REAPER ReaScript automation to make useful.

**Time to ship**: 1-2 days for the ReaScript layer.

### Approach K — Convolution-enhanced JSFX

**What**: capture a real NES's RCA output impulse response.
Convolve JSFX output with it to add the analog stage coloration.

**Live MIDI keyboard path**: keyboard → JSFX → IR convolution →
audio out.

**Strengths**: adds the missing "analog" character that makes NES
audio feel warmer than pure digital synthesis.

**Gaps**: need to capture the IR (or find one).  Adds CPU for
convolution.

**Time to ship**: 4-8 hours (or 1-2 days if we capture our own IR).

### Approach L — SysEx-authoring keyboard controller

**What**: build a custom hardware controller that emits our NES
SysEx messages (e.g. knobs mapped to `$4000`-style register
values).  Effectively gives a live keyboard access to Priority 1
SysEx mode.

**Live MIDI keyboard path**: controller → MIDI SysEx stream → our
JSFX priority-1 → bit-accurate hardware emulation.

**Strengths**: transforms the live keyboard into the actual NES
driver.  Maximum expressivity.

**Gaps**: requires custom hardware (MIDI controller with 20+ knobs
mapped to NES register fields).  Or software MIDI controller app.
Steep learning curve.

**Time to ship**: hardware route = 2-3 weeks.  Software app (e.g.
TouchOSC layout) = 1 day.

## Matrix: which approach wins on which axis

| Approach | Live play | Sound fidelity | Setup time | Cost |
|----------|-----------|----------------|------------|------|
| A JSFX P3 | Yes | Medium | Zero | Free |
| B Chipsounds | Yes | High | 2 h | $95 |
| C Python daemon | Yes (if fast enough) | Highest | Weeks | Free |
| D FamiStudio VST | Yes | High | 2-3 days | Free |
| E Multi-sample library | Yes | Very high | 2-3 days | Free |
| F MIDINES hardware | Yes | Reference | 1-2 days | $150+hw |
| G Hybrid stems+JSFX | Yes | Mixed | Zero | Free |
| H Stem triggers | "Live" sample play | N/A (archival) | 4 h | Free |
| I Split JSFX/samples | Yes | High | 1 day | Free |
| J ReaScript render | Yes (JSFX) | Medium (JSFX DSP) | 1-2 days | Free |
| K Convolution enhance | Yes (JSFX) | Very high | 4-8 h | Free |
| L SysEx controller | Yes | Maximum | 1-21 days | $0-$500 |

## Recommended sequence

For the "I want to play NES games live with a MIDI keyboard" goal,
ordered by expected ROI:

1. **Approach A + port Rule 34/35/30 to JSFX** (~5 hours).  Baseline.
2. **Approach I (hybrid JSFX + DMC samples)** (~1 day).  Adds drum
   realism.
3. **Approach K (convolution enhancement)** (~4-8 hours).  Analog
   character.
4. **Approach B (evaluate chipsounds demo)** (~2 hours).  Compare
   against the upgraded JSFX.  If chipsounds wins, license it.
5. **Approach D (FamiStudio VST)** if it exists (~2 days).  Free
   alternative to chipsounds.
6. **Approach F (MIDINES)** if you can justify the hardware
   investment.  Reference-grade.

Approaches C, E, H, J, L are specialized and should only be pursued
if the top 6 leave a specific gap.

## How each approach integrates with project methods

- All approaches reuse our **extracted MIDI with CC + SysEx** for
  file playback.
- Approaches A, B, D, K use the **three-priority input cascade** for
  live play.
- Approach C is the Python DSP brought directly to live; depends on
  our **Frame IR + stems pipeline** unmodified.
- Approaches E and H treat the **Python stems** as reusable sample
  material.
- Approaches G, I, J, K use JSFX as the live core and add layers.
- Approach F sidesteps our synth entirely; uses real hardware.
- Approach L inverts the relationship — the keyboard becomes the
  driver, driving our JSFX's Priority 1 mode.

## The underlying point

All 12 approaches share one invariant: **a MIDI keyboard's live input
is too low-bandwidth to recreate per-frame NES driver behavior.**
Each approach handles that gap differently — by substituting a
preset, sampling a pre-render, running the real driver in live
mode, or adding a hardware bridge.

Your job is to pick which substitution feels best for the music you
actually want to make.  That's an ear-test question.  The
`keyboard_lab/db/keyboard.db` schema supports tracking ear-test
results per approach, so you can iterate empirically rather than
debate in the abstract.
