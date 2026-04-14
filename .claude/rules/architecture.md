---
description: Core architectural rules (always loaded). Task-specific rules in docs/ARCHITECTURE_REFERENCE.md.
globs:
  - "extraction/**"
  - "scripts/**"
---

# Architecture Rules (Core)

Universal invariants. For ROM-parsing rules (13-16), validation axes
(19), expansion/DPCM details (21-25), see `docs/ARCHITECTURE_REFERENCE.md`.

## 1. Parsers Emit Full-Duration Events

`duration_frames = tempo * (nibble + 1)`. No staccato or envelope
shaping in the parser. All temporal shaping is Frame IR's job.

## 2. Manifests Before Code

Every new game needs a manifest in `extraction/manifests/` BEFORE
parser code. Declares mapper, pointer table, command format, facts vs hypotheses.

## 3. DriverCapability Dispatches Envelope Strategy

`driver.volume_model == "lookup_table"` — never `isinstance(parser, X)`.

## 4. Status Labels Are Mandatory

Every driver module: STATUS comment block after docstring.

## 5. Triangle Is Always 1 Octave Lower

32-step vs 16-step sequencer. `pitch_to_midi` subtracts 12 for triangle. Hardware fact.

## 6. Trace Is Ground Truth

After parser/frame_ir changes: `PYTHONPATH=. python scripts/trace_compare.py --frames 1792` → 0 mismatches.

## 7. Derived Timing Must Be Clamped

`max()` / `min()` on all computed timing. Example: `phase2_start = max(1, duration - fade_step)`.

## 8. Same Opcode ≠ Same Semantics

DX reads 2 bytes in CV1, 3/1 in Contra. Never copy command handling without checking.

## 9. Frame IR Is Mandatory (NON-NEGOTIABLE)

Trace → frame state → Frame IR → MIDI. No shortcuts. Direct period-to-note is a known failure mode.

## 10. Different ROMs Use Different Music Engines

Per-game profiles. No universal decoder. Record which assumptions succeeded/failed.

## 11. Snap Trace Periods to ROM Period Table

Interpretation decision belongs in Frame IR, not MIDI builder.

## 12. Three Layers Must Never Be Conflated

1. **Observed** (ground truth): raw APU registers. Authoritative.
2. **Intent** (parser interpretation): Frame IR. HYPOTHESIS until validated.
3. **Projection** (output): MIDI, RPP. PROVISIONAL until Intent passes gate.

## 17. Artifacts Must Carry Trust Labels

**Hypothesis output** (not validated) vs **Trusted output** (validated against ground truth). State scope.

## 18. Driver Family Is First-Class Infrastructure

Classify at ingest via CC11/CC12 density. 5 families drive validation depth, synth mode, NSF trust.
Run `scripts/driver_survey.py --game <slug>`. See CLAUDE.md for family table.

## 22. Period-to-Note Formula

Pulse: `CPU / (16 × (P+1))`. Triangle: `CPU / (32 × (P+1))`. CPU = 1,789,773 Hz.
Triangle octave offset is hardware, not convention.
