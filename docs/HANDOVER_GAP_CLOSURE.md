# Session Handover: Gap Closure Implementation

## What Happened This Session (2026-04-13)

A full research sprint covering the NES music extraction ecosystem,
followed by infrastructure updates and a comprehensive gap analysis.

### Research Completed

1. **Web research** across 4 domains: ROM hacking archives (joshw.info,
   Zophar, VGMRips), NESDev wiki/forums, VGMPF sound driver database,
   and romhacking.net format documents. Results in `docs/research/`.

2. **FamiTracker source analysis** (github.com/HertzDevil/famitracker-all):
   APU emulation, non-linear mixing formulas, 5-sequence instrument model,
   period tables, noise inversion, NSF import approach. Confirmed our
   pipeline's fundamental approach matches the reference implementation.

3. **Gap analysis** across 8 research axes: expansion audio, DPCM/DAC,
   NSF divergence, driver patterns, APU event coverage, validation sources,
   ROM parsing coverage, mixing model. Output: `docs/NES_AUDIO_GAPS_AND_NEXT_STEPS.md`.

4. **Driver family report**: 5 families (renamed from original survey labels)
   with 30 game profiles. Output: `docs/DRIVER_FAMILIES_AND_GAMES.md` (2529 lines).

### Code Built or Updated

| File | What Changed |
|------|-------------|
| `scripts/driver_survey.py` | Renamed families, added FAMILY_BEHAVIOR dict, CC-density-based classification |
| `scripts/vgm_to_frame_state.py` | NEW — VGM/VGZ parser, frame state converter, NSF cross-validation |
| `scripts/nsfe_metadata.py` | NEW — NSFE metadata parser, M3U generator, pipeline merger |
| `extraction/drivers/konami/frame_ir.py` | Extended FrameState with event_type, dac, sweep, noise_mode, const_vol fields |
| `.claude/rules/architecture.md` | Added Rules 18-25 (families, validation axes, mixing, DPCM, expansion, NSF trust) |
| `.claude/rules/synth_fidelity.md` | Added Rules 7-9 (non-linear mixing, family presets, noise inversion) |
| `.claude/rules/session_protocol.md` | Added driver family step, VGM validation axis, family-aware validation table |
| `CLAUDE.md` | Added driver families table, gap summary, Hiro plan layers, new tools |

### Plan Produced

A 7-layer Hiro Plantagenet decomposition for closing all identified gaps.
Layers are ordered by dependency, with parallelism possible between
Layers 3-5. See CLAUDE.md "Implementation Plan" table.

---

## What Needs to Happen Next

### Layer 1: Audit & Schema (START HERE)

**Goal:** Quantify expansion audio scope, design multi-chip Frame IR schema.

**Tasks:**
1. Build `scripts/expansion_detect.py` — scan all 1577 NSFs for expansion
   byte at header offset $07B. Output JSON: per-chip game counts and lists.
2. Write `docs/MULTI_CHIP_SCHEMA.md` — unified Frame IR schema covering
   all 6 expansion chips + DPCM events. Define MIDI channel assignments.

**Gate:** Schema reviewed, expansion audit complete with counts.

**Key data already gathered:**
- VRC6 registers: $9000-$B002 (2 pulse + 1 saw)
- FDS registers: $4040-$408A (1 wavetable + modulation)
- MMC5 registers: $5000-$5015 (2 pulse + 1 PCM, mirrors APU)
- N163: internal RAM at $4800 (1-8 wavetable channels)
- 5B: $C000/$E000 mapped to YM2149 (3 square + noise + envelope)
- VRC7: $9010/$9030 mapped to OPLL (6 FM channels)
- Full register specs in gap analysis Section 2.1

### Layer 2: Frame IR Extensions

**Goal:** Implement all missing event types and multi-chip channels.

**Tasks:**
1. Add `EventType` enum covering all event types from schema
2. Extend `FrameState` with remaining fields (some already added this session)
3. Add expansion chip channel types to `ChannelIR`
4. Consider refactoring `extraction/drivers/konami/frame_ir.py` to
   `extraction/frame_ir.py` if scope grows beyond Konami

**Constraint:** All new fields must default to None/0/False — existing
pipeline must produce identical output.

### Layer 3: Capture Pipeline Extensions

**Goal:** Update nsf_to_reaper.py to capture expansion + DPCM + phase resets.

**Tasks:**
1. Intercept expansion chip register writes in 6502 emulator
2. Track $4003/$4007 writes as phase_reset events
3. Distinguish $4010-$4013 (DPCM trigger) from $4011 (direct DAC)
4. Track $4015 channel enable/disable writes
5. Map expansion channels to MIDI channels 5-11

**Critical constraint:** Running on standard APU games (CV1) must produce
bit-identical MIDI output.

### Layer 4: Validation Infrastructure

**Goal:** Automated cross-validation and trust scoring.

**Tasks:**
1. Build `scripts/cross_validate.py` (NSF vs VGM vs NES-MDB comparison)
2. Build `scripts/nsf_trust_scorer.py` (per-game trust classification)
3. Run comparison report for top 30 games

### Layer 5: ROM Parsers (PARALLEL with 3-4)

**Goal:** Capcom 6C80 parser (30+ games) + Sunsoft parser.

**Research gates:**
- Download and read romhacking.net #274 (Capcom 6C80) BEFORE writing code
- Download and read romhacking.net #665 (Sunsoft) BEFORE writing code
- If docs are incomplete, stop and reassess

### Layer 6: Synth Fidelity

**Goal:** Non-linear mixing + expansion audio rendering in JSFX.

### Layer 7: Classification Refinement

**Goal:** Sub-family patterns, secondary metrics.

---

## Files to Read First

In this order:

1. `CLAUDE.md` — project overview, invariants, gap summary, plan layers
2. `.claude/rules/architecture.md` — 25 rules including new ones (18-25)
3. `.claude/rules/session_protocol.md` — workflow, validation ladder, family-aware validation
4. `docs/NES_AUDIO_GAPS_AND_NEXT_STEPS.md` — full gap analysis (858 lines)
5. `docs/DRIVER_FAMILIES_AND_GAMES.md` — 5 family profiles + 30 game profiles
6. `docs/MISTAKEBAKED.md` — mistake prevention system
7. `.claude/rules/synth_fidelity.md` — channel behavior, mixing, presets

## Files NOT to Read (unless needed)

- `docs/research/*` — raw research. Findings already synthesized into gap analysis.
- `docs/HANDOVER_TO_NSFRIPPER.md` — obsolete handover from repo split.
- `docs/HANDOVER_BATTLETOADS.md` — Battletoads-specific, only relevant if working on that game.

---

## Critical Context

- **The pipeline works.** 1577 games processed, 65 surveyed, 5 at Rung 2+.
  Don't re-derive the baseline.
- **CC11/CC12 model is validated.** Maps to $4000/$4004 volume/duty registers.
  5 driver families confirmed against VGMPF attribution.
- **Frame IR is mandatory.** Never skip it between trace and MIDI.
  Raw register replay produces artifacts (proven by Battletoads v3-v5).
- **Expansion audio is the biggest gap.** ~250 games silently losing channels.
  Start with Layer 1 (audit: how many games, which chips?).
- **Capcom 6C80 is highest-ROI ROM parser.** Format doc exists, 30+ games,
  all Family 1 (simplest to validate). Don't attempt without reading doc #274 first.
- **Non-linear mixing matters.** `95.88/((8128/(sq1+sq2))+100)` for pulses.
  Two pulses at max = 0.278, not 0.368. Linear mixing is wrong by up to 15%.
- **NSF trust is family-dependent.** Families 1-3 = trust NSF. Families 4-5 = seek
  cross-validation. Known-divergent: SMB, Battletoads, Gradius.

## Suggested Opening Move

```
Start Layer 1: Audit & Schema.
1. Build expansion_detect.py — scan all NSFs, report expansion chip usage.
2. Draft MULTI_CHIP_SCHEMA.md — unified Frame IR for all chips.
This gives us the numbers we need to prioritize and the schema
that all subsequent layers depend on.
```
