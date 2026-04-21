# Hardware-Semantic Translation — New Approach

Parallel track to the existing stems pipeline and the ReapNES_Studio/APU2
JSFX line.  Not a replacement.

## Why a new approach

The existing pipeline evolved incrementally: MIDI extraction, then a
JSFX synth, then audio stems when multi-track JSFX couldn't do
non-linear mixing.  Each layer solved its immediate problem, but the
layers never shared a model.  The extractor invents "notes" that don't
exist in hardware; the plugin reconstructs hardware behavior from MIDI
that lost the original causality; the stems bypass the plugin entirely.

This approach treats the extractor, middle layer, MIDI projection, and
synth as **one continuous interpretive stack** with a shared IR -- the
Channel Behavior Graph (CBG).  Bugs found at any layer become visible
at the others.

## What this approach is for

- Editable REAPER projects that sound hardware-faithful
- Live MIDI keyboard play with game-specific instrument templates
- Round-trippable: import NSF -> edit -> re-render, without drift
- Single-track full-APU routing so non-linear mixing works inside the plugin

## What this approach is NOT for

- YouTube video audio rendering -- stems pipeline remains the canonical path
- Existing JSFX plugins (`ReapNES_Studio`, `ReapNES_APU2_v2`) -- unchanged
- Existing MIDI extractor (`scripts/nsf_to_reaper.py`) -- unchanged
- Replacing the outputv6 REAPER projects

## Reading order

1. `DESIGN.md` -- the 8-section design document (this is the main artifact)
2. Future: `IR_SPEC.md` -- formal CBG schema (appears during Phase 1)
3. Future: `ROADMAP.md` -- live phase/gate tracker (appears during Phase 1)

## Status

- **Phase 0** -- Design doc drafted, pending review.  No code yet.
- Reference games for validation: **Contra** (triangle ring-over) and
  **Wizards & Warriors** title + early stages (triangle ring-over AND
  drop-out, bidirectional failure).  W&W is the stronger validator
  because it fails in both directions -- any liveness model that works
  for W&W handles the general case.
