# Pipeline Architecture

## Objective

Eliminate the gap between declared rules and actual execution.
The pipeline should deterministically generate, validate, and compare
all viable representations of a game's music.

## Core Principles

1. Rules must become code, not comments or prompts.
2. Canonical observed data, inferred interpretation, and DAW projection
   are distinct layers — never conflate them.
3. Different ROMs use different music engines. No universal decoder.
4. The system must tag assumptions, record what worked, and adapt per-engine.

## Extraction Routes

| Route | Source | Output | Fidelity |
|-------|--------|--------|----------|
| NSF → CC MIDI | NSF emulation | CC11/CC12 volume+duty | Good (ground truth for most games) |
| Trace → CC MIDI | Mesen APU capture | CC11/CC12 volume+duty | Better (hardware state) |
| Trace → SysEx MIDI | Mesen APU capture | Raw register replay | Best (lossless) |
| ROM parse → Frame IR → MIDI | ROM disassembly | Interpreted events | Variable (requires validation) |

## Data Flow

```
Mesen Trace / NSF ──→ FrameState (canonical) ──→ Frame IR ──→ MIDI/SysEx ──→ RPP
                                                     ↑
                                              Interpretation
                                              decisions here
```

FrameState is the single source of truth for observed hardware behavior.
Frame IR is the interpretation layer. MIDI is a downstream projection.

## Validation

See `.claude/rules/architecture.md` Rules 13-17 and
`.claude/rules/session_protocol.md` for the full validation ladder.

## Previous Design

The full aspirational spec (777 lines, 12 implementation phases) is
archived at `docs/archive/ARCHITECTURE_SPEC_full_2026-04-06.md`.
It describes a `kitchen_sink.py` orchestrator that was never built.
