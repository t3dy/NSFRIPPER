# Wizards & Warriors Playback Missing Data Inventory

## Purpose

This note inventories likely information loss between:

1. ROM/parser/simulator facts
2. transport projection (`MIDI + SysEx`)
3. synth consumption (`Console`, `APU`, `APU2`)
4. heard musical result

It is written specifically to avoid reducing the title problem to a single
"triangle sustain" knob when the missing behavior may live elsewhere in the
stack.

## Working Rule

User descriptions such as "the bass line" or "the triangle" should be treated
as **audible symptom reports**, not as trusted channel attribution.

For this title phrase, the evidence already shows that what sounds like one
instrument may actually be a `pulse1 + triangle` composite.

## Representation Stack

### Layer A: ROM / parser / simulator facts

Currently available:

- parser note boundaries
- command boundaries
- same-pitch fresh events
- per-frame APU register writes
- write masks
- hidden-state reports
- title release / audible-state IR

### Layer B: Transport

Currently available in `nsf_to_reaper.py`:

- note tracks
- pulse CC11 / CC12
- raw register replay SysEx (`0x02`)
- audible-state sideband SysEx (`0x03`)

### Layer C: Synth programs

- `ReapNES_Console.jsfx`
- `ReapNES_APU.jsfx`
- `ReapNES_APU2.jsfx`

### Layer D: Heard musical identity

What the user evaluates:

- whether the phrase reads as a plucked/muted composite
- whether low support is too strong or too exposed
- whether a short event actually speaks

## Strong Missing-Data Candidates

## 1. Pulse envelope truth is still under-preserved in the fidelity path

Evidence:

- title pulse validation is strong
- pulse hidden-state report shows `$4000 = 0x45` is hardware envelope mode,
  not steady volume `5`
- frame `928 / 960 / 976` all rely on `pulse1` attack behavior

Current flattening:

- note tracks carry pulse note boundaries
- CC11 carries low-nibble-like level changes in the editable route
- committed `APU2` SysEx path still mostly treats pulse volume as the raw
  register nibble, not a live envelope state

Why this matters:

- if pulse attack is under-modeled, the phrase will sound too blob-like even
  if triangle is correct
- what sounds like "triangle ringing too long" may partly be "pulse attack is
  too weak to dominate the composite"

Status:

- **very likely missing**

## 2. Triangle full-body authority vs support-only authority is not explicit

Evidence:

- `928` and `976` classify as `fresh_full_body`
- `960` classifies as `fresh_attack_damped_body`
- triangle has a real boundary/write at `960`, but audio low-body is much
  weaker there than at `928` or `976`

Current flattening:

- transport preserves `release_class`
- committed `APU2` does not consume that distinction
- committed `Console` / `APU` do not know this distinction exists

Why this matters:

- the key phrase failure may not be "triangle off vs on"
- it may be "triangle foreground body vs background support"

Status:

- **very likely missing**

## 3. Same-pitch re-articulation is not one thing across channels

Evidence:

- `pulse1` same-pitch retriggers are strong attack cues
- `triangle` same-pitch retriggers do not automatically imply the same audible
  kind of restart
- frame `960` is the clearest mismatch case

Current flattening:

- note projection often collapses same-pitch events
- write-aware IR detects hidden retriggers
- but a generic `retrigger = true` idea is still too coarse musically

Why this matters:

- a pulse hidden retrigger and a triangle hidden retrigger are not guaranteed
  to be equivalent onset events

Status:

- **likely missing**

## 4. Ordered writes inside a frame may still matter

Evidence:

- current transport preserves write mask, not full ordered write sequence as a
  playback-facing contract
- the phrase may depend on attack dominance emerging inside the frame, not just
  on the final latched state

Current flattening:

- `0x02` preserves per-frame final register state and a 4-bit write mask
- it does not preserve write ordering as a first-class playback datum

Why this matters:

- if `pulse1` attack is perceptually established before triangle support
  stabilizes, the phrase may read plucked without requiring a literal triangle
  mute

Status:

- **plausibly missing**

## 5. Effective triangle live state is not the same as `$4008` latched value

Evidence:

- hidden-state report explicitly notes that `$4008 = 0x81` should not be read
  as live linear counter `1`
- NESdev semantics say `$4008` is reload/control setup, not direct audible
  amplitude

Current flattening:

- transport sideband currently uses a `level` field derived from current
  channel snapshots
- triangle playback in committed `APU2` still effectively gates from raw
  linear-reload visibility

Why this matters:

- triangle body may be overstated because the current route mistakes
  "reload/control remains armed" for "full audible body should continue"

Status:

- **very likely missing**

## 6. Mixer-level identity may be wrong even if channel-local facts are right

Evidence:

- the user hears one musical object, not isolated channels
- the phrase is likely composite
- APU pulse path and TND path interact nonlinearly in the hardware mixer

Current flattening:

- `Console` uses ad hoc channel mixes
- committed `APU2` uses hardware mixer math, but without the richer
  phrase-local articulation inputs
- current analysis often talks channel-by-channel when the musical target is
  the combined object

Why this matters:

- "triangle too long" may really mean "triangle too exposed in the mixed
  identity after pulse attack"

Status:

- **likely missing**

## 7. The editable synths are not fidelity synths

### `ReapNES_Console.jsfx`

Main behavior:

- generic ADSR instrument
- live patch logic
- triangle behaves like note-gated waveform with a user release

Consequence:

- excellent editorial instrument
- not a trustworthy source for phrase-level hardware truth

### `ReapNES_APU.jsfx`

Main behavior:

- closer NES-ish route
- still centered on generic channel-level playback, not title-specific
  articulation classes

Consequence:

- better than pure console-style ADSR
- still not rich enough for hidden-state / composite interpretation

### committed `ReapNES_APU2.jsfx`

Main behavior:

- raw `0x01` SysEx register replay only
- no current consumption of write-aware `0x02` / audible-state `0x03`

Consequence:

- the committed file is hardware-oriented but still too coarse for the title
  articulation problem

## Current Best Diagnosis

The most likely missing pieces are not:

- one triangle sustain slider
- one shorter note length
- one secret cutoff opcode

The most likely missing pieces are:

1. live pulse envelope meaning
2. triangle body-authority classification
3. channel-specific retrigger semantics
4. possibly ordered intra-frame composite behavior
5. mixed-object interpretation rather than isolated-channel interpretation

## What To Preserve Going Forward

Any next playback-facing contract should distinguish at least:

- `pulse_attack_strength`
- `triangle_body_authority`
- `triangle_support_only`
- `composite_pulse_led`
- `full_body_onset`
- `write_mask`
- `same_pitch_retrigger`
- `phase_reset_if_known`

## Bottom Line

The title phrase may not be failing because "triangle sustain is wrong."

It may be failing because the current stack still does not preserve the
difference between:

- a pulse-led composite pluck with reduced low support
- and a normal triangle note event

That is a representation problem before it is a parameter problem.
