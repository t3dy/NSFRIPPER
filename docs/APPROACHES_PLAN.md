# Plan: every approach to approximating NES game sound from MIDI

A survey of paths we haven't yet tried, ordered by priority.  Each
entry has an effort estimate, an expected audio outcome, and a first
actionable step.  The goal is breadth — try everything — then return
to whichever has the best ear-test result.

Some of these are already-known tools (Plogue chipsounds, Triforce,
FamiStudio VST); some are DSP techniques (convolution, supersampling,
neural models); some are hardware bridges (MIDINES).  All are viable
for "I have a MIDI file, make it sound like Nintendo."

## How to read this doc

| Field | Meaning |
|-------|---------|
| **Effort** | Hours or days to get a usable first result. |
| **Expected audio quality** | S = indistinguishable from real NES; A = excellent; B = acceptable but flawed; C = proof-of-concept. |
| **Cost** | Free / low / medium / high (tool cost). |
| **Priority** | P0 (next to try) → P3 (long-term research). |
| **What it beats** | Which of our current variants it might replace. |

## Tier 1 — Low effort, high upside (P0)

These are easy wins.  Each is ~1-4 hours of work to stand up and
compare against our current Variants A/B/C.

### 1.1 Plogue chipsounds (commercial)

A VSTi that accurately emulates NES, Commodore, Atari, and other 8/16-bit
systems via sample-modeled oscillators + period-accurate driver
simulation.  Widely considered the best commercial NES VSTi.

- **Effort**: 2 hours (install, set up MIDI mapping per channel, A/B
  one song against our variants).
- **Cost**: ~$95 one-time.
- **Expected audio quality**: S (reference-grade).
- **Priority**: **P0** — if this sounds great, we stop writing DSP.
- **First step**: Download demo (fully functional for 15 min
  sessions), load into REAPER, route our MIDI into it, compare
  Castlevania Vampire Killer.

### 1.2 Tweakbench Triforce (free)

A free VSTi designed specifically for NES-style synthesis.  Less
accurate than chipsounds but solid for melodic content.

- **Effort**: 1 hour.
- **Cost**: Free.
- **Expected audio quality**: A (strong NES-like character; less
  perfect on timbral animation like duty cycling).
- **Priority**: **P0** — free, quick test.
- **First step**: Download from tweakbench.com; run MIDI through it
  set to pulse duty 2.

### 1.3 FamiStudio VST export

FamiStudio is an open-source NES music tracker.  Recent versions
export rendered audio per-track.  Its DSP is well-maintained and
matches FamiTracker's output (another community gold standard).

- **Effort**: 2 hours.
- **Cost**: Free.
- **Expected audio quality**: S or A+ (author actively tracks
  FamiTracker and libgme).
- **Priority**: **P0** — likely the best free-tool option.
- **First step**: Install FamiStudio.  Convert one of our MIDI files
  to FamiStudio's FTM (manual or via intermediary script).  Export
  stems per channel.  Drop into REAPER; compare to Variants.
- **Open question**: FamiStudio may not have a real-time VST path.
  If so, it's a stems source, not a live synth.  Still useful as a
  quality reference.

### 1.4 ReaPack community JSFX search

ReaPack (the REAPER package manager) has hundreds of community JSFX.
Some target chiptune specifically.  Searching "chip", "nes", "8bit",
"square" would turn up half a dozen candidates.

- **Effort**: 2 hours.
- **Cost**: Free.
- **Expected audio quality**: B to A depending on author.
- **Priority**: **P0** — trivially cheap to survey.
- **First step**: Open ReaPack → Browse packages → search.  Install
  the top 5 chiptune JSFX, load into a test project, run Castlevania
  MIDI through each.

### 1.5 SoundFont / SFZ NES library

Several community-made SoundFont files specifically sample-map NES
channels.  REAPER can load SoundFonts via ReaSamplOmatic or SFZ via
sforzando (free).

- **Effort**: 2 hours.
- **Cost**: Free (community SoundFonts are widely shared).
- **Expected audio quality**: B — fine for melodic pulses, fake for
  noise drums and DMC.
- **Priority**: **P0** — worth a quick test as a fallback sound.
- **First step**: Search for "NES SoundFont SF2"; download a
  reputable one; load in sforzando in REAPER; route MIDI.

## Tier 2 — Medium effort, targeted wins (P1)

These are multi-hour DSP or tooling projects that would each
materially improve an existing Variant.

### 2.1 Blargg Blip_Buffer port to numpy (Python stems)

Already planned in `docs/RESEARCH_ANTIALIAS.md`.  Would eliminate
the remaining pulse-edge aliasing in Python stems (Rule 35 gap).

- **Effort**: 1 day.
- **Expected audio quality**: S for Variant A.  No change for
  Variant B.
- **Priority**: **P1** — concrete, well-defined, beats existing
  Python DSP.
- **First step**: Port `blip_buf.c` to `scripts/blip_buf.py`.
  Replace `_bandlimited_pulse` with the BLEP kernel.  Re-render one
  song.  Measure click reduction.

### 2.2 Convolution with real NES RCA impulse response

Record a real NES RCA output's impulse response (via a capture card
and a click pulse).  Convolve our cleanly-rendered stems with that
IR to add the analog-output character (TV amp coloration, RF
modulator tilt).

- **Effort**: 1-2 days (including hardware recording).
- **Expected audio quality**: A+ (the thing most NES-emulation misses
  is the analog output stage; convolution fixes that).
- **Priority**: **P1** — most distinctive upgrade we could make.
- **First step**: Find a high-quality NES RCA impulse response on
  Freesound or record one.  Apply via REAPER's ReaVerb to each
  stem.  A/B the result.

### 2.3 2-bus-stem architecture

Already designed in `docs/RESEARCH_ANTIALIAS.md` §6 option B.
Collapses the 5 per-channel stems into 2 "bus stems" (pulse pin,
TND pin) each rendered with full non-linear mix before summing.

- **Effort**: 2-3 hours.
- **Expected audio quality**: A (fixes the ~15% linear-sum overload
  in Variant A).
- **Priority**: **P1** — quickest architectural improvement.
- **First step**: Modify `render_channel_stems.py` to emit 2 stems
  instead of 5 when `--bus-mode` flag is set.

### 2.4 Port Rule 35 polyBLEP to JSFX

The real-time version of bandlimited pulse synthesis.  Brings
Variant B's live JSFX into near-parity with Variant A's Python DSP
on the pulse-grit front.

- **Effort**: 3-4 hours.
- **Expected audio quality**: Variant B goes from A- to A.
- **Priority**: **P1** — closes the biggest remaining JSFX gap.
- **First step**: Implement `poly_blep(t)` in JSFX per
  `docs/RESEARCH_ANTIALIAS.md`.  Apply at pulse-edge detection.
  Ear-test.

### 2.5 ReaScript offline render (Variant C)

Turn Variant B's JSFX output into stems via REAPER automation.
Result: bit-identical live-vs-stems audio.

- **Effort**: 1-2 days.
- **Expected audio quality**: Same as JSFX live (A- currently,
  could be A once 2.4 lands).
- **Priority**: **P1** — unblocks Variant C.
- **First step**: Write ReaScript (Python inside REAPER) that
  opens each B project, renders per-track with solos, saves WAVs to
  `outputv6_C/<game>/stems/`.

## Tier 3 — Creative / experimental (P2)

Longer-horizon ideas.  Some are moonshots; some are "interesting to
try once."

### 3.1 Multi-sample library from real NES hardware

Record every NES channel at every combination of pitch × duty × volume
through real hardware (or a confirmed-good emulator).  Build a
SoundFont or Kontakt instrument.  Then "play" our MIDI through that
sampled instrument.

- **Effort**: 3-5 days (huge sample-gathering session).
- **Expected audio quality**: S for pitch/duty/vol points in the
  sample grid; crossfading quality between grid points determines
  how S-tier this feels.
- **Priority**: **P2** — ultimate authenticity if done right.
- **First step**: Stand up a NES hardware capture rig, or use a
  Mesen-based scripted renderer to produce the ~4000-sample
  sample set.

### 3.2 Neural audio model (DDSP-style)

Train a neural network on pairs of (MIDI, real NES audio) to learn
the synthesis mapping.  Modern differentiable DSP (DDSP) makes this
tractable.

- **Effort**: 1-2 weeks (data prep + training + inference
  integration).
- **Expected audio quality**: B to A; depends on training set quality.
- **Priority**: **P2** — interesting research direction but overkill
  if chipsounds/FamiStudio covers 95% of the same ground.
- **First step**: Gather a corpus of MIDI/WAV pairs.  Start with
  Magenta's DDSP examples.

### 3.3 Hardware integration via MIDINES (or clone)

MIDINES is a hardware MIDI interface for the NES.  Plug USB-MIDI in,
NES RCA out.  Effectively turns the real NES into a live synth.

- **Effort**: 1-2 days (procurement + setup + REAPER integration).
- **Cost**: ~$150 for hardware.
- **Expected audio quality**: S (real hardware).
- **Priority**: **P2** — coolest option but hardware cost.  Excellent
  for video recording scenes.
- **First step**: Buy or borrow a MIDINES cartridge + NES console.
  Capture audio via RCA-to-line-in on your audio interface.  Route
  from REAPER via USB MIDI to the NES.

### 3.4 Expand ReapNES Studio into a full VSTi

Rewrite the JSFX chain as a C++ VST3 plugin.  Gains: cross-DAW
compatibility, better CPU efficiency, more sophisticated UI.

- **Effort**: 2-4 weeks.
- **Expected audio quality**: Depends on DSP parity with current JSFX.
- **Priority**: **P3** — big investment; only do if JSFX-in-REAPER
  proves insufficient as a product.
- **First step**: Pick a VST3 framework (JUCE, iPlug2) and port
  `ReapNES_APU2_v2.jsfx` logic.

### 3.5 Live MIDI piping to py65 → PyAudio stream

Build a Python daemon that receives MIDI in, runs py65 NSF emulation
in real time (if we can speed it up), streams audio out via PyAudio.
Registers as a virtual audio device.

- **Effort**: 1 week.
- **Expected audio quality**: S for hardware fidelity (it IS the
  NSF driver playing), but py65's ~3-6x too-slow speed makes this
  currently impractical.
- **Priority**: **P3** — blocked on py65 speedup.
- **First step**: Benchmark py65 on a typical PLAY call.  If >60 Hz
  is achievable, continue; else shelve until py65 is faster.

### 3.6 Cherry Audio / Vital wavetable with NES-style wavetables

Modern wavetable synths can load user wavetables.  Define wavetables
shaped like NES pulse (4 duties) + triangle + noise LFSR output.
Modulate the wavetable position per MIDI CC to simulate duty switching.

- **Effort**: 1 day (crafting wavetables + mapping CCs).
- **Cost**: Free (Vital is free; Cherry Audio has freebies).
- **Expected audio quality**: B to A (Vital will sound clean but
  might be TOO clean — the NES's grittiness is part of its charm).
- **Priority**: **P2** — interesting creative path; good for hybrid
  retro/modern sound design.
- **First step**: Download Vital.  Generate 4 pulse wavetables in
  Python.  Load into Vital.  Map CC12 to wavetable position.

## Tier 4 — Alternative tracker ecosystems (P2-P3)

Translating our MIDI into tracker formats to drive tracker-native
synthesis.

### 4.1 MIDI → FamiTracker (FTM)

Write a converter that emits a FamiTracker `.ftm` file from our
MIDI.  FamiTracker's DSP is battle-tested.  Render FTM to WAV.

- **Effort**: 3-4 days (FTM binary format + correct instrument
  mapping).
- **Expected audio quality**: S for single-instrument tracks; may
  lose nuance from CC-heavy envelope data.
- **Priority**: **P3** — FamiStudio covers this ground better.

### 4.2 MIDI → Furnace Tracker

Furnace is a modern open-source multi-system tracker (supports NES
natively).  Similar translation path, different synth.

- **Effort**: 3-4 days.
- **Expected audio quality**: A.
- **Priority**: **P3** — same niche as Furnace.

### 4.3 MIDI → BambooTracker with VST export

BambooTracker focuses on FM (YM2608) but has NES support in some
builds.  Niche.

- **Effort**: Similar to 4.1/4.2.
- **Priority**: **P3** — unless we want FM crossover.

## Priority summary

In order of "what I'd try first if I had a day":

1. **FamiStudio export** (P0 — free, likely very close to reference).
2. **Plogue chipsounds demo** (P0 — ~30 min to install and A/B).
3. **ReaPack JSFX survey** (P0 — might find a gem in <1 hour).
4. **Triforce VSTi** (P0 — free, quick test).
5. **Convolution with NES RCA IR** (P1 — biggest distinctive upgrade).
6. **2-bus-stem architecture** (P1 — small fix, large improvement).
7. **Port polyBLEP to JSFX** (P1 — closes Variant B's biggest gap).
8. **Blargg Blip_Buffer to numpy** (P1 — anti-aliasing in stems).
9. **ReaScript offline render** (P1 — enables Variant C).
10. **Multi-sample library from hardware** (P2 — ultimate archival).

Doing 1-4 in one evening is realistic.  5-9 is a week of focused
work.  10+ is R&D territory.

## Decision framework

Each tier-1 and tier-2 item will be evaluated after a quick A/B
against our current Variants:

- **Sounds better than B (JSFX) alone** → adopt as the live-play
  engine if licensing permits, else as a rendering path.
- **Sounds better than A (Python stems)** → adopt as archival path.
- **Sounds equivalent** → don't adopt (adds complexity without win).
- **Sounds worse** → discard but document why so we don't revisit.

Each evaluation should produce a note in `docs/APPROACHES_NOTES.md`
(create on first eval) with the specific song tested, the qualitative
verdict, and anything technically noteworthy.

## What to NOT waste time on

- **Building a custom waveshaper / saturator for "NES-like grit"**.
  The grit is aliasing from undersampled edges.  We already have a
  clean math definition (BLEP) for fixing it properly.  Adding
  saturation downstream hides but doesn't solve.
- **Writing our own VSTi from scratch** before trying the commercial
  and community options.  If chipsounds or FamiStudio covers 95% of
  the use case, writing a VSTi is mostly re-creating what already
  exists.
- **Multi-sample libraries captured from a generic NES emulator**.
  The whole point of a multi-sample is matching hardware; samples
  from an emulator are just samples of another synthesizer.
