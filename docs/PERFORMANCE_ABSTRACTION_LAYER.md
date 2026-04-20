# Performance abstraction layer (PAL)

**Canonical design doc.**  This is the authority for what the live-play
path does and does not attempt to reproduce about NES hardware.  Other
docs in the project (`keyboard_lab/docs/PERFORMANCE_MAPPINGS.md`,
`keyboard_lab/docs/THE_LIVE_PERFORMANCE_PROBLEM.md`) are catalog or
explanation companions; this doc defines the contract.

The abstraction sits between **NES hardware behavior** (captured by
our Frame IR and encoded in MIDI as notes + CC + SysEx) and the
**live human performer** (pressing a keyboard, turning a mod wheel,
holding aftertouch).  Neither end can fully match the other.  The
PAL picks a finite, consistent set of translations that make live
play musical without claiming hardware fidelity.

## Problem

A Frame IR sample (one 60 Hz frame of NES register state) contains
roughly 30 distinct hardware-behavior dimensions (see
`docs/UNDERSTANDING_THE_CHIP.md`).  A live MIDI keyboard produces
at most 4-6 control dimensions simultaneously (note events,
velocity, mod wheel, pitch bend, maybe aftertouch, maybe 1-2 CC
knobs).

So ~30 hardware behaviors must be compressed into ~6 performer
controls.  That's a 5-to-1 reduction.  This doc names which
behaviors survive the compression, which are handled by preset
state, and which are honestly out of reach.

**This is an information-theoretic limit, not a DSP problem.**  We
cannot solve it by better code; we can only pick WHICH lossy
compression maps best.  The PAL is that choice, made deliberately.

## Purpose

The PAL exists to:

1. **Name the classes of behavior** a live player can reach.
2. **Assign each NES behavior to a class** honestly.
3. **Define the control-reduction contract** from hardware →
   performable controls.
4. **Make the non-performable behaviors visible** instead of
   silently dropping them.

The PAL is not a new subsystem.  It's a structural layer over the
existing JSFX three-priority input cascade
(`docs/SYNTH_VS_SCRIPTS.md`, `keyboard_lab/docs/THE_LIVE_PERFORMANCE_PROBLEM.md`).
Specifically, the PAL defines what happens in Priority 3 (ADSR
keyboard) and how it relates to Priority 1 (SysEx file replay) and
Priority 2 (CC automation) when the performer is active.

## The four control classes

Every hardware behavior slots into exactly one of these classes.

### Class A — Direct live controls

**Contract**: the performer controls this behavior in real time via
a single keyboard-native gesture (note event, velocity, pitch bend,
mod wheel, aftertouch, or pedal).  Round-trip latency ≤20 ms.

**Typical mappings**: velocity → attack intensity, note → pitch,
mod wheel → duty.

**Information cost**: none beyond the gesture itself.  The player
is the source of truth.

### Class B — Macro / articulation triggers

**Contract**: the performer fires a time-limited pre-canned
behavior sequence via a discrete event (keyswitch, pad, program
change).  The macro runs for its duration regardless of subsequent
player input (or accepts limited modulation).

**Typical mappings**: low-range key → "Konami pulse stab" (fast
decay + duty flip sequence).  Pedal → phase-reset burst.

**Information cost**: macro state must be time-scheduled inside the
JSFX.  Macros are presets the performer TRIGGERS, not preset state
they select.

### Class C — Preset-only characteristics

**Contract**: the behavior is baked into per-preset slider state
before the performance begins.  The performer cannot modify it
live.  Different presets give different flavors; switching presets
mid-note may cause discontinuities.

**Typical mappings**: noise-mode selection, envelope-decay curve
shape, default duty cycle, sweep unit enable/disable, phase-reset-on-
note flag.

**Information cost**: stored as `preset.slider_json` in
keyboard_lab DB.  Per-driver-family presets ship with the product.

### Class D — Non-performable behaviors

**Contract**: the behavior cannot be reproduced live from a MIDI
keyboard with any meaningful fidelity.  Honestly declaring this is
more useful than pretending.  In live play, this behavior is
either omitted, substituted with a rough approximation, or
delegated to a file-playback path (Priority 1 SysEx).

**Typical mappings**: frame-perfect per-frame register
manipulation, DPCM sample-address selection, `$4015` frame-counter
mode, pulse sweep unit bitwise-shift exactness.

**Information cost**: documented as non-performable; the JSFX does
not attempt these in Priority 3 mode; the ear-test acknowledges
they won't match.

## The seventeen performable dimensions — classification

Exhaustive list of NES behaviors relevant to live performance and
their PAL class.  This is the contract.  Deviations from this table
should be treated as design changes, not bug fixes.

| # | NES behavior | Class | Keyboard gesture |
|---|--------------|-------|------------------|
| 1 | Note pitch (period register) | A | note_on pitch |
| 2 | Note timing (attack/release) | A | note_on/note_off |
| 3 | Volume amplitude | A | velocity (initial), aftertouch (held) |
| 4 | Duty cycle value (static) | C | preset slider |
| 5 | Duty cycle animation (per-frame) | B | pad / keyswitch (see §5) |
| 6 | Attack transient / phase reset | A | velocity (intensity), preset (enable) |
| 7 | Envelope decay curve shape | C | preset ADSR sliders |
| 8 | Envelope release | C | preset slider |
| 9 | Sweep unit pitch modulation | B | pitch bend (coarse) + preset (shape) |
| 10 | Vibrato (software tremolo) | A | aftertouch (depth) |
| 11 | Arpeggio / chord illusion | B | multi-note held + mod wheel (rate) |
| 12 | Noise period index (pitch) | A/C | note-range mapping (performance preset) |
| 13 | Noise mode (long/short LFSR) | C | preset |
| 14 | Noise length-counter silencing | B | velocity or pad → macro |
| 15 | DMC sample trigger | B | pad (per-sample keyswitch) |
| 16 | DMC DAC direct value | D | non-performable live; file SysEx only |
| 17 | Frame-accurate register sequencing | D | non-performable live; file SysEx only |

**Class distribution**: 6 × A, 5 × B, 4 × C, 2 × D.  Most dimensions
are at least partially reachable; two are honest non-performables.

## Non-performable honesty

The following things WILL sound different between an extracted-MIDI
file-playback (Priority 1 SysEx) and a live keyboard performance
(Priority 3 PAL).  This is not a bug to be fixed; it is the
information-theoretic limit:

- **Driver-specific per-frame duty animation**: Battletoads' pulse1
  duty changes every 1-3 frames during sustained notes.  A live
  player holding a note cannot produce this.
- **Sweep unit's exact bit-shift math**: hardware sweep uses
  `period >> shift` per half-frame.  Pitch bend approximates but
  doesn't match.
- **Phase-reset timing quirks**: some drivers delay phase reset
  from note-on by a specific frame count; can't do live.
- **`$4015` frame-IRQ and DMC-IRQ**: irrelevant to playback audio
  but affects timing for games that self-synchronize.
- **DPCM sample-address addressing**: live player cannot select
  sample addresses.

If any of these matters for a specific song, use Priority 1
(file playback via extracted SysEx).  The PAL is honest about
this: for those songs, live play is a different musical
experience, not a degraded one.

## Connection to the SysEx > CC > ADSR priority model

The existing synth design (`docs/SYNTHMERGE.md`, restated in
`keyboard_lab/docs/THE_LIVE_PERFORMANCE_PROBLEM.md`) defines a
three-priority input cascade.  The PAL fits as follows:

- **Priority 1** (SysEx): no PAL involvement.  Bit-accurate
  register replay overrides any performer input.  All 17
  dimensions from the table above come directly from the SysEx
  stream.
- **Priority 2** (CC11/CC12): partial PAL.  Volume and duty
  driven by file CC; other PAL dimensions still available to
  live performer (pitch bend, mod wheel, aftertouch) because
  those are orthogonal to CC11/CC12.
- **Priority 3** (ADSR keyboard): **full PAL**.  This is where
  the four control classes A-D operate as designed.

In a multi-track project, different tracks can be at different
priorities simultaneously.  A typical live-performance REAPER
project might have 3 JSFX instances: Pulse1 at P1 SysEx, Pulse2
at P1 SysEx, Triangle at P3 PAL (live bass).  The PAL only
governs P3 tracks; it does not interfere with P1/P2 tracks.

## Contradictions to note

Reading across existing docs, two contradictions surface.  This
doc resolves them:

### Contradiction 1 — Stems vs JSFX authoritative

`docs/STEMS_APPROACH.md` declares stems the primary deliverable
(Rule 31).  `docs/SYNTH_VS_SCRIPTS.md` and
`docs/COUNTERPOINT_IN_SQUARE_WAVES.md` identify stems as archival-
only.  The MEMORY.md entry `project_stems_default` says the same.

**Resolution**: stems are primary for **archival fidelity** (the
"sounds like the hardware" proof).  JSFX is primary for **live
performance**.  They coexist; neither is THE primary.  The PAL
is unambiguously on the JSFX live-play side.

The project needs to update the memory entry to reflect this
(action item).

### Contradiction 2 — Rule 31's "multi-track REAPER projects cannot reproduce non-linear DAC"

Rule 31 says this drove the pivot to stems.  But JSFX *can* do
non-linear DAC within a single instance in Full-APU mode
(`ch_mode == 4`).  The JSFX has non-linear mix math at lines
801-803 of ReapNES_APU2_v2.jsfx.

**Resolution**: Rule 31's constraint only applies when JSFX is
run per-channel on separate tracks.  In Full-APU mode, JSFX
handles the non-linear mix correctly.  The PAL's live-play
architecture can use Full-APU mode, sidestepping Rule 31's
concern.  Action item: document this clearly in the JSFX
deploy rules.

## What the PAL is NOT

- Not a replacement for the SysEx > CC > ADSR cascade.
- Not a new plugin.
- Not a rewrite of the JSFX.
- Not a claim that live play == hardware fidelity.
- Not a mandate to implement all 17 dimensions in the JSFX.
  (See Deliverable 4 for the actual implementation priority.)

## What comes next

Three follow-up documents exercise this layer:

1. `keyboard_lab/docs/LIVE_CONTROL_MAPPINGS.md` — the concrete
   controller-to-behavior wiring for a standard 88-key MIDI
   controller with mod wheel, pitch bend, aftertouch.
2. `keyboard_lab/db/schema.sql` (extension) — tracks which
   approaches support which PAL dimensions at which coverage
   level (exact / approximate / preset / unsupported).
3. `docs/JSFX_LIVE_PRIORITY.md` — the ranked list of JSFX
   changes needed to realize Class A + B dimensions that the
   current JSFX doesn't yet handle.

These three documents + this canonical one + the existing
catalog docs (`PERFORMANCE_MAPPINGS.md`, `INTEGRATED_APPROACHES.md`)
form the complete performance-abstraction layer.

## Status

- **Design**: this document.  Authoritative as of 2026-04-19.
- **Schema**: extension lands alongside.
- **Mapping doc**: lands alongside.
- **JSFX implementation**: partial — current JSFX implements Class A
  dimensions #1, #2, #3, #6, #10 (pitch, timing, velocity, transient,
  mod-wheel vibrato if enabled), Class C dimensions #4, #7, #8, #13,
  and Class D #16, #17 omitted as expected.  Missing: Class A #12
  fine-tuning, Class B dimensions #5, #9, #11, #14, #15.

## Open hypotheses (honestly flagged)

These are PAL-related claims we have NOT yet validated by ear-test:

- HYP-PAL-1: "attack transient at velocity-scaled 1-2 ms spike is
  the single highest-ROI live-play improvement."  Source:
  `keyboard_lab/docs/PERFORMANCE_MAPPINGS.md` §7.  Test: implement,
  ear-compare.
- HYP-PAL-2: "CC12-driven quantized duty on pulse tracks is
  sufficient to reproduce driver-family timbre signatures."
  Source: same doc §2.  Test: preset per family, ear-test.
- HYP-PAL-3: "Performance-macro single knob (envelope + duty +
  vibrato + detune combined) is more usable than per-axis knobs
  during live play."  Source: same §9.  Test: build macro,
  perform, compare to per-axis control.
- HYP-PAL-4: "60 Hz quantization of CC application is
  audibly preferable to smooth continuous CC."  Source: same §8.
  Test: A/B.

Each hypothesis is an experiment candidate for the
`keyboard_lab` DB.
