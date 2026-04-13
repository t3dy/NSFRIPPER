# Wizards & Warriors Title Triangle First-Principles Audit

## Scope

This audit resets the title triangle interpretation from first principles.
It treats the prior title triangle theory as untrusted and uses four evidence
sources together:

1. ROM parser events
2. simulator / direct NSF frame-state
3. direct emulator APU write behavior
4. reference MP3 macro shape

Goal:

- explain what hardware behavior produces the heard title triangle phrase
- identify the missing articulation layer
- decide the export architecture before regenerating title outputs

## Fresh Audit

### 1. Parser Events

Title triangle stream start: `0xF1A3`

Fresh event walk for the disputed phrase:

- frame `512`: `CMD 04 [129,135,18]`
- frame `512`: `CMD 07 [32]`
- frame `896`: note `0x96`, period `508`, duration `32`
- frame `928`: note `0xA2`, period `253`, duration `32`
- frame `960`: `CMD 07 [16]`
- frame `960`: note `0xA2`, period `253`, duration `16`
- frame `976`: note `0xA0`, period `284`, duration `16`
- frame `992`: note `0x9E`, period `319`, duration `16`
- frame `1008`: note `0x9D`, period `338`, duration `16`

Result:

- the stream already encodes one longer note followed by shorter notes
- the `928 -> 960` same-pitch pair is a fresh event boundary, not a tie

### 2. Direct NSF Latched Frame-State

Direct per-frame NSF state shows:

- frame `929`: period `253`, linear `1`
- frame `961`: period `253`, linear `1`
- frame `977`: period `284`, linear `1`
- frame `993`: period `319`, linear `1`
- frame `1009`: period `338`, linear `1`

Result:

- latched state alone does not expose the frame `961` re-attack
- a state-only transport collapses the first short note into continuation

### 3. Direct Emulator Write Behavior

Write-level capture for the same phrase:

- frame `929`: `$4008=0x81`, `$400A=0xFD`, `$400B=0x10`
- frame `961`: `$4008=0x81`, `$400A=0xFD`, `$400B=0x10`
- frame `977`: `$4008=0x81`, `$400A=0x1C`, `$400B=0x11`

Critical fact:

- frame `961` performs a fresh write sequence even though the timer value is
  unchanged

This is the missing articulation evidence.

The previous exporter captured only value changes, so frame `961` vanished from
both:

- note-centric MIDI segmentation
- the old SysEx register-state replay path

### 4. MP3 Falsification

Reference title MP3 duration:

- `37.117098s`

The heard phrase is:

- one longer bass note
- then a clearly articulated first short note
- then the descending short-note run

Any model that turns `928 + 960` into one uninterrupted sustain fails the
reference MP3's macro phrase shape even if local period slices match.

## What The Hardware Is Actually Doing

Best current interpretation:

1. The driver rewrites triangle control/timer registers at each note boundary.
2. The frame `960/961` same-pitch note is articulated by write behavior, not by
   a changed latched period.
3. The articulation-relevant truth is therefore not just "current register
   state"; it is "current register state plus which registers were written on
   this frame."

This is enough to reject the previous state-only export theory.

## Ranked Hypotheses For The Missing Articulation Layer

### 1. Most likely: write-aware retrigger semantics

The missing layer is per-frame write identity:

- same-value rewrites to `$4008/$400A/$400B`
- especially timer-high / gate-relevant writes at note boundaries

Why this ranks first:

- directly observed at frame `961`
- exactly matches the audible contradiction
- explains why parser + state snapshot both looked locally consistent while the
  heard result stayed wrong

### 2. Plausible: timer / phase restart is part of the attack

Same-pitch note articulation may depend on timer restart or phase-sensitive
behavior triggered by write order, not only by "gate on/off" state.

Why this ranks second:

- it is consistent with the write evidence
- the current synth path previously ignored same-value timer writes
- it would make the first short note more audible without inventing a
  title-only duration patch

### 3. Lower priority: extra triangle gate nuance beyond the write mask

There may still be a finer driver/hardware detail around triangle gate reload,
but current evidence does not require that to explain the opening phrase.

Why this ranks lower:

- we already have a concrete lost signal at frame `961`
- do not add a second missing layer until the write-aware path is tested

## Architecture Decision

## Is Plain MIDI Too Lossy?

Yes, plain MIDI note-on / note-off is too lossy for this articulation.

Reason:

- the title phrase contains a same-pitch fresh triangle attack with no pitch
  change and no latched register-state change
- plain MIDI note data only recovers it if we add a parser-driven retrigger
  heuristic
- that heuristic is useful for note view, but it is still not the real
  hardware behavior

## Is State-Only SysEx Enough?

No.

The old SysEx path encoded only latched register values. It dropped same-value
rewrites, so it also lost the title triangle re-attack.

Therefore the needed middle layer is richer than both:

- plain MIDI notes
- frame-state snapshots without write identity

## Recommended Middle Layer

Use a canonical **frame-write IR**:

- full per-frame channel register state
- plus per-frame per-channel write mask
- optionally preserve ordered writes as a future extension

Projection from that IR:

- `MIDI notes + CC`: editorial view only
- `write-aware SysEx`: playback truth path
- `REAPER/APU2`: consume write-aware SysEx

## Recommended Playback Architecture

1. Canonical truth layer: frame-write IR
2. Truth playback: `ReapNES_APU2.jsfx` consuming write-aware SysEx
3. Editorial layer: conventional MIDI note tracks, still useful for arranging
4. REAPER project: prefer APU2 project for fidelity checks; keep Console
   project only as an editable approximation

This keeps one plugin family and avoids title-specific engine hacks.

## Concrete Implementation Plan

### Done in this pass

1. Exporter now preserves ordered APU writes per frame instead of only value
   changes.
2. SysEx transport upgraded to include a per-channel write mask.
3. `ReapNES_APU2.jsfx` now treats write-aware timer/gate events as real
   retrigger signals, including same-value rewrites.

### Next validation steps

1. Regenerate title MIDI with write-aware SysEx.
2. Regenerate title APU2 REAPER project from that MIDI.
3. Ear-check the title phrase against the MP3:
   - first short note must speak clearly
   - bass note lengths must stop feeling over-held
4. If still wrong, test only the next-ranked hypothesis:
   - ordered write replay inside the frame, not just write mask

## Revised Output Rule

For `Wizards & Warriors` title triangle:

- do not trust note-only playback as the truth path
- use write-aware SysEx / APU2 for fidelity judgment
- keep note MIDI as an editable projection, not the final authority
