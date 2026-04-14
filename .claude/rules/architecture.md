---
description: Architectural rules for the extraction pipeline
globs:
  - "extraction/**"
  - "scripts/**"
---

# Architecture Rules

These rules enforce the engine/data/hardware separation and prevent
the structural bugs that cost the most debugging time.

## 1. Parsers Emit Full-Duration Events

Parser note events MUST have `duration_frames = tempo * (nibble + 1)`.
No staccato, envelope shaping, or volume-based truncation in the parser.
All temporal shaping is the frame IR's responsibility.

Validation: `ParsedSong.validate_full_duration()` must return empty.

Why: Contra v1-v4 had incorrect note splitting that prevented the
frame IR from applying correct envelope shaping. Moving all shaping
to the IR fixed both the volume model and the duration accuracy.

## 2. Manifests Before Code

Every new game MUST have a manifest JSON in `extraction/manifests/`
BEFORE any parser code is written. The manifest declares:
- mapper and ROM layout
- pointer table location and format
- command format (DX byte count, percussion type)
- known facts vs hypotheses

Why: Without a manifest, assumptions get baked into code. The
CV1-to-Contra transition wasted 3+ prompts because DX byte count
was assumed, not checked.

## 3. DriverCapability Dispatches Envelope Strategy

The frame IR uses `DriverCapability` to select the volume model.
Never use isinstance checks on game name or parser class to branch
envelope logic.

Correct: `driver.volume_model == "lookup_table"`
Wrong: `isinstance(parser, ContraParser)`

Why: Implicit branching creates hidden coupling.

## 4. Status Labels Are Mandatory

Every driver module must have a STATUS comment block after the
module docstring. See parser.py for the format.

## 5. Triangle Is Always 1 Octave Lower

For the same NES timer period, the triangle channel produces
frequency half that of pulse (32-step vs 16-step sequencer).
`pitch_to_midi` subtracts 12 for triangle. This is HARDWARE fact.

## 6. Trace Is Ground Truth

After any change to parser or frame_ir code:
`PYTHONPATH=. python scripts/trace_compare.py --frames 1792`
Must show 0 pitch mismatches on CV1 pulse.

## 7. Derived Timing Must Be Clamped

Any timing value computed from parameters must use explicit
`max()` / `min()` to prevent negative or overflow values.
Example: `phase2_start = max(1, duration - fade_step)`.

## 8. Same Opcode Does Not Mean Same Semantics

DX reads 2 bytes in CV1, 3/1 in Contra. E8 means different
things. EC is unused in CV1 but shifts pitch in Contra.
Never copy command handling without checking the target game.

## 9. Frame IR Is Mandatory (NON-NEGOTIABLE)

No trace -> MIDI conversion without Frame IR generation.
Trace-derived exports must follow:
  Trace -> canonical frame state -> Frame IR -> MIDI/CC/SysEx/project

Raw register changes are not yet musical events. Directly
opening a new MIDI note on every period change is a known
failure mode (Battletoads v3-v5 proved this). The Frame IR
layer interprets hardware behavior into stable musical events.

Anti-regression: any script that converts trace directly to
note events without Frame IR is a regression against the
proven CV1/Contra approach and must be rejected.

## 10. Different ROMs Use Different Music Engines

Do not hard-code one universal decoding model. Konami uses
Maezawa commands. Rare uses a dispatch table. Other engines
may be entirely different. The system must:
- Support per-game/per-engine profiles
- Attach route assumptions explicitly
- Record which assumptions succeeded or failed
- Allow adaptation without ad hoc improvisation

## 11. Snap Trace Periods to ROM Period Table

When the ROM period table is known, trace periods should be
snapped to the nearest table entry to determine the driver's
intended note. Raw trace periods include sweep unit modifications
and are typically 1-15 units off from the table value.

This is an interpretation decision that belongs in Frame IR,
not in the MIDI builder.

## 12. Three Architectural Layers Must Never Be Conflated

1. **Observed layer** (ground truth): raw APU register state from
   Mesen trace or NSF emulation. Authoritative.
2. **Intent layer** (parser-derived interpretation): parsed events,
   simulated driver state, Frame IR. HYPOTHESIS until validated
   against Layer 1.
3. **Projection layer** (generated output): MIDI, RPP, SysEx, WAV,
   musical claims. PROVISIONAL until Intent passes the execution
   semantics gate against Observed.

Execution semantics validation is the gate between Intent and Projection.
If the gate has not passed, Projection outputs are "hypothesis output."

Each layer has different semantics and different debugging needs.
Skipping a layer or merging two creates bugs that are invisible
until the user hears the output.

See `session_protocol.md` for the Validation Ladder and gate criteria.

## 13. Zero Parse Errors Is Not Musical Correctness (NON-NEGOTIABLE)

Parser alignment (zero desync, all command boundaries correct) proves
byte-stream structure only. It is a STRUCTURAL milestone, not a
SEMANTIC one. Parser output is a hypothesis until validated.

Zero parse errors does NOT prove:
- Pitches are correct (transposition, arpeggio may be unmodeled)
- Durations are correct (tempo accumulator, tick rate may be wrong)
- Envelopes are correct (envelope tables may be misinterpreted)
- The music sounds like the game

Why: Battletoads parser v3 achieved zero parse errors with 955 notes
while duration accounting was off by 1.52x and arpeggio system was
entirely unmodeled. "Zero errors" gave false confidence.

## 14. Execution Semantics Validation Is Mandatory

After parser alignment, the pipeline MUST include an execution
semantics validation phase before any output is labeled trusted:

1. Build a frame-level simulator from parsed events + driver semantics
2. Simulate tempo accumulator, duration counters, pitch modulation,
   volume envelopes, and channel state
3. Compare simulated per-frame output against Mesen trace
4. Classify mismatches by cause (tempo drift, duration error,
   arpeggio error, envelope error, transposition error, alignment)
5. Block promotion to MIDI/REAPER until comparison passes thresholds

Required artifacts:
- Parsed event stream (from parser)
- Simulated frame-state trace (from simulator)
- Comparison report against Mesen trace
- Mismatch taxonomy report

Acceptance criteria:
- Parse phase passes when command boundaries align with zero desync
- Execution semantics phase passes when simulated frame behavior
  matches trace within explicit thresholds (90%+ period match on
  sounding frames, 80%+ volume match, note boundaries within ±1 frame)
- Only after BOTH phases may outputs be labeled trusted

Anti-patterns this rule prevents:
- Claiming pitch correctness from parsed notes alone
- Claiming rhythm correctness from duration bytes alone
- Treating zero parse errors as a final success condition
- Direct ROM-event-to-MIDI conversion without semantics validation
- Collapsing base note, sounding note, and perceived note into one concept

## 15. Five Pipeline Layers Must Stay Distinct

For ROM-parsing routes, the pipeline must maintain five distinct layers:

1. **Parsed event stream** — ROM bytes decoded into commands, notes,
   durations, control flow. Structural hypothesis only.
2. **Simulated driver state** — frame-level execution of parsed events
   through driver model (tempo, counters, modulation, envelopes).
3. **Observed ground truth** — Mesen trace / NSF frame captures.
   The reference that layers 1-2 are validated against.
4. **Frame IR** — interpreted musical events (note boundaries,
   continuity, modulation classification). Reconciles layers 2 and 3.
5. **Downstream projection** — MIDI, CC, SysEx, RPP, synth.

No layer may be skipped. No two layers may be collapsed.

## 16. Noise Is a Separate Semantic Domain

Noise channels must not be forced through melodic assumptions.
Noise has:
- Period index (not frequency), mode bit (tonal vs noise)
- Different volume envelope model than melodic channels
- Hit detection semantics (gating patterns, not pitch contour)
- Different validation criteria than period-based channels

A game may have fully validated melodic channels while noise
remains partial or hypothesis-only. This is acceptable and must
be documented per-channel in the game's validation record.

Why: Wizards & Warriors proved that 48/48 melodic channel matches
can coexist with only partial noise semantics. Noise requires
separate investigation, not the same decoder path.

## 17. Artifacts Must Carry Trust Labels

Every output artifact (MIDI, RPP, WAV, musical claim in docs)
must be accompanied by its trust level from the Validation Ladder:

- **Hypothesis output**: parser-derived, not semantics-validated.
  Usable for practical work, not claimable as verified.
- **Trusted output**: semantics-validated against ground truth
  within defined thresholds, for a stated scope.

State the scope: which channels, which songs, which frame range.
Trust does not extend beyond validated scope.

See `session_protocol.md` for the Validation Ladder.

## 18. Driver Family Is First-Class Infrastructure (2026-04-13)

Every game must be classified into a driver family at ingest time.
Classification uses CC11/note and CC12/note density from the first
extraction pass. The family assignment drives downstream behavior:

| Family | CC11/note | CC12/note | Trust NSF? | MIDI Size | Synth Mode |
|--------|-----------|-----------|------------|-----------|------------|
| 1: Hardware Envelope | 0.0-2.8 | < 0.5 | Yes | Small | ADSR |
| 2: Standard Envelope | 2.8-5.6 | < 0.5 | Yes | Medium | CC11 |
| 3: Duty Animators | 3.7-4.9 | 0.7-1.0 | Yes | Medium | CC11+CC12 |
| 4: Dense Automators | 5.1-14.9 | < 0.5 | Maybe | Large | CC11 |
| 5: Full Animation | > 7.0 | > 1.0 | Maybe | Large | CC11+CC12 |

Family assignment is probabilistic — boundary games may shift with
re-extraction. Company attribution does NOT predict family (proven:
Rare spans 1-2, Konami spans 1-3, Tecmo spans 2-4).

Implementation: `scripts/driver_survey.py` classify_driver_family().

Why: The CC11 density metric measures something real about the
hardware — the ratio of software-driven frames ($4000 bit 5 = 1)
to hardware-envelope frames ($4000 bit 5 = 0) per note. This is
an architectural decision baked into each driver, not a statistical
artifact.

## 19. Three Independent Validation Axes

The pipeline supports three independent sources of ground truth:

1. **Mesen trace** — APU register dumps from gameplay. Frame-level.
   Highest fidelity. Limited to games we've manually captured.
2. **VGM logs** — timestamped register write logs from VGMRips.
   Independent of our pipeline. Covers hundreds of games.
   Caveat: VGMs logged from NSFs inherit NSF inaccuracies.
3. **NES-MDB** — Stanford dataset (5278 songs, assembly-parsed).
   Different methodology (static code parsing vs our emulation
   capture). Lower resolution (24 Hz vs our 60 Hz).

Cross-validation between these sources moves from "which is right?"
to "where do they disagree, and why?" — a research-grade pipeline.

Implementation: `scripts/vgm_to_frame_state.py` for VGM axis.

## 20. Non-Linear APU Mixing

The NES APU uses impedance-based non-linear mixing (from FamiTracker
source and NESDev wiki):

Pulse pin:   `95.88 / ((8128.0 / (sq1 + sq2)) + 100.0)`
TND pin:     `159.79 / ((1.0 / ((tri/8227) + (noise/12241) + (dpcm/22638))) + 100.0)`

Simultaneous pulse channels compress each other's effective volume.
Linear mixing (our current JSFX approach) makes simultaneous pulses
louder than real hardware. For ROM-accurate reproduction, the synth
should implement these formulas.

## 21. Non-Note Sound Events

Not all NES sound is note-triggered. The pipeline must handle:

- **$4011 DAC writes**: Algorithmic percussion (Battletoads drums
  are computed ramp waveforms, not stored DPCM samples — confirmed
  by NESDev forum thread t=15586)
- **Sweep unit**: Continuous pitch transforms on pulse channels
- **Noise mode bit**: Tonal vs noise LFSR mode ($400E bit 7)
- **Frame counter sync**: $4017 writes that reset the APU sequencer

These require event types beyond note/envelope/duty in the Frame IR.
Current schema only supports note-centric events. Extend with:
  event_type: note | envelope | duty | dac | sweep | noise_mode

## 22. Period-to-Note Canonical Formula

From FamiTracker source (confirmed against NESDev wiki):

```
BASE_FREQ = 32.7032 Hz  (C1)
NTSC_CLOCK = 1,789,773 Hz
period = round(NTSC_CLOCK / (16 * freq)) - 1   (pulse, 16-step)
period = round(NTSC_CLOCK / (32 * freq)) - 1   (triangle, 32-step)
```

Triangle produces frequency at half the rate of pulse for the same
period value (32-step vs 16-step sequencer). The octave offset is
inherent in hardware, not an explicit correction.

Our `pitch_to_midi()` correctly subtracts 12 for triangle. FamiTracker
shares the same period lookup table for both — composer is expected
to know triangle sounds one octave lower.
