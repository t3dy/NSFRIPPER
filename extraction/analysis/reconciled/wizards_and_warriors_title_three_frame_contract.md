# Wizards & Warriors Title Three-Frame Contract

## Purpose

This note freezes the strongest current interpretation of the disputed title
phrase around frames `928 / 960 / 976` using only:

- ROM/parser event boundaries
- direct NSF / emulator write behavior
- hidden-state APU semantics
- aligned reference-audio measurements

It is intentionally **not** a synth-tuning note.
It exists to prevent the phrase from being flattened into a generic
"triangle sustain" problem.

## The Narrow Question

What does the hardware-backed evidence actually support for the three key
phrase frames?

## Proven Per-Frame Facts

### Frame 928

Parser / event side:

- `pulse1`: fresh same-pitch event at period `508`
- `triangle`: fresh event at period `253`, duration `32`

Write side:

- `pulse1`: `$4000/$4002/$4003` rewritten
- `triangle`: `$4008=0x81`, `$400A=0xFD`, `$400B=0x10`

Audible-state classification:

- `pulse1`: `hidden_retrigger`
- `triangle`: `period_attack`
- `composite_attack`: `False`

Reference-audio shape:

- high-band attack is present
- low-band body is very strong

Release IR class:

- `fresh_full_body`

Conclusion:

- frame `928` is a real fresh bass-body onset
- both channels contribute meaningful new material

### Frame 960

Parser / event side:

- `pulse1`: fresh same-pitch event at period `508`
- `triangle`: `CMD 07 [16]`, then fresh same-pitch event at period `253`,
  duration `16`

Write side:

- `pulse1`: `$4000/$4002/$4003` rewritten
- `triangle`: `$4008=0x81`, `$400A=0xFD`, `$400B=0x10`

Critical hardware nuance:

- `triangle` period does **not** change from frame `928`
- `$400B` sets the triangle linear-counter reload flag and timer high
- unlike pulse timer-high writes, this does **not** by itself prove a bright
  waveform-phase restart
- `$4008=0x81` means control flag `1`, reload `1`
- under standard triangle semantics, that keeps the triangle logically armed;
  it is not direct evidence of a short hardware cutoff

Audible-state classification:

- `pulse1`: `hidden_retrigger`
- `triangle`: `hidden_retrigger`
- `composite_attack`: `True`

Reference-audio shape:

- strongest high-band onset in the phrase window
- low-band body much weaker than at `928` or `976`

Release IR class:

- `fresh_attack_damped_body`

Conclusion:

- frame `960` is a real fresh event
- but it is **not** best modeled as a full renewed triangle bass onset
- the strongest evidence-backed reading is:
  - fresh pulse-led attack
  - reduced low-body support
  - composite articulation rather than ordinary triangle restart

### Frame 976

Parser / event side:

- `pulse1`: fresh event at period `570`
- `triangle`: fresh event at period `284`, duration `16`

Write side:

- `pulse1`: rewritten with changed period
- `triangle`: `$4008=0x81`, `$400A=0x1C`, `$400B=0x11`

Audible-state classification:

- `pulse1`: `period_attack`
- `triangle`: `period_attack`
- `composite_attack`: `False`

Reference-audio shape:

- low-band body rebounds strongly

Release IR class:

- `fresh_full_body`

Conclusion:

- frame `976` is the next true full-bodied bass onset

## Contract

The evidence currently supports this playback-facing contract:

1. `pulse1` carries real attack responsibility at `928`, `960`, and `976`.
2. `triangle` carries full-body bass authority at `928` and `976`.
3. `triangle` does **not** carry equivalent full-body authority at `960`.
4. Frame `960` should therefore not be rendered as:
   - ordinary triangle sustain
   - or ordinary full triangle reattack
5. Frame `960` is best represented as:
   - `composite_pulse_led = true`
   - `triangle_full_body = false`
   - `triangle_support_only = true`

## What This Does Not Prove

This note does **not** prove:

- a dedicated ROM command for "short triangle sustain"
- a hidden `$4015` mute in the phrase
- a triangle-specific ADSR-style release parameter

There is still no phrase-local `$4015` evidence, and `$4008=0x81` does not by
itself imply a short hardware cutoff.

## Why This Matters

If the phrase still sounds like "triangle sustaining too long," that symptom
should not automatically be translated into:

- "find the sustain knob"
- "shorten triangle note length"
- "invent a triangle release command"

The stronger evidence-backed diagnosis is:

- the current playback is still mis-weighting the `960` event
- the phrase is being flattened away from its true pulse-led composite reading

## Recommended Use

Use this note as a guardrail for future work:

- any playback change should preserve `928` and `976` as full-body events
- any playback change should keep `960` distinct from those two
- no future patch should claim ROM proof of a triangle cutoff unless new
  hardware evidence appears
