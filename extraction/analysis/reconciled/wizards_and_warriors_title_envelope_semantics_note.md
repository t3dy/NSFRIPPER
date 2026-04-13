# Wizards & Warriors Title Envelope Semantics Note

## Purpose

This note answers a focused question for the title phrase:

Is the missing articulation likely explained by an undiscovered
**software-side envelope program** in the driver, or by **hardware-envelope /
hardware-state behavior** that the current playback path still flattens?

## Current Best Answer

For the disputed title phrase, the evidence currently favors:

- **no additional title-local software volume envelope layer has been found**
- the main missing pulse articulation is more likely **hardware envelope
  behavior after retrigger**
- the main missing triangle articulation is more likely **effective body/gate
  interpretation**, not a hidden per-frame software envelope script

## Evidence

### 1. Pulse and triangle trace agreement is already exact at the raw register layer

Running the current comparison helpers:

- `compare_title_pulse("pulse1")`
- `compare_title_pulse("pulse2")`
- `compare_title_triangle()`

shows:

- exact scaled-period matches across the full title window
- exact sounding agreement for triangle
- only one sounding disagreement for each pulse channel

This means the parser + simulator already explains the observed register-level
period and coarse level state very well.

If a hidden software envelope were actively changing title-note loudness in a
way not reflected by the parser model, we would expect more register-level
disagreement.

### 2. The control-byte docs point to direct hardware shadow writes, not a hidden envelope command

Current control-byte findings show:

- `$07C0,X` is the APU control-byte shadow copied to `$4000/$4004`
- command `0x0A` updates that shadow
- in pulse channels this means:
  - duty
  - loop/halt
  - constant-volume bit
  - low nibble intensity / envelope-period field

For the title problem specifically:

- the title phrase does not use `0x0A` as the missing explanation
- command `0x07` is duration mode, not articulation
- command `0x03` is not an envelope command

So the currently known command vocabulary does not provide a title-local
"secret pulse or triangle envelope script" explanation.

### 3. Pulse title control state points to hardware envelope mode

At the key pulse1 frames (`928`, `960`, `976`):

- `$4000 = 0x45`
- `const_vol = 0`
- envelope period nibble = `5`

That is hardware envelope mode, not constant volume.

The hidden-state report also says:

- nibble `5` should not be read as effective loudness `5`
- effective pulse loudness should start high and fall after each timer-high
  retrigger

So the pulse pluck is already explainable by known APU semantics.

### 4. Triangle title control state does not show a separate software envelope pattern

For the disputed phrase:

- triangle repeatedly uses `$4008 = 0x81`
- fresh writes occur at note boundaries
- there are no phrase-local `$4015` mute writes

This does not reveal a distinct per-frame software envelope program.
What it reveals is that raw `$4008` visibility is not enough to explain the
heard body differences.

So the triangle problem remains:

- effective body/gate interpretation
- not proven hidden software envelope sequencing

## What This Means

The most defensible current reading is:

1. The title phrase does **not** appear to depend on an undiscovered
   software-driven per-frame volume envelope in the driver.
2. Pulse articulation is more likely being lost because playback ignores
   hardware-envelope semantics.
3. Triangle articulation is more likely being lost because playback treats
   latched `$4008` state as too direct a measure of audible body.

## Practical Consequence

The next fidelity work should focus on:

- reconstructing pulse envelope behavior from known `$4000` semantics plus
  retrigger timing
- consuming the existing articulation sideband for triangle body authority
- avoiding new speculative command hunts unless fresh ROM evidence appears

## Bottom Line

The missing layer is still real, but the best current evidence says it lives in
**playback interpretation of known hardware behavior**, not in a newly missing
title-only software envelope command.
