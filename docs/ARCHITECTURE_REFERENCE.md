# Architecture Reference (Extended Rules)

Task-specific rules not loaded into every session. Read this file
when working on ROM parsing, validation, expansion audio, or DPCM.

Core rules (always loaded): `.claude/rules/architecture.md`

---

## 13. Zero Parse Errors Is Not Musical Correctness (NON-NEGOTIABLE)

Parser alignment (zero desync) proves byte-stream structure only.
It is STRUCTURAL, not SEMANTIC. Parser output is a hypothesis.

Zero parse errors does NOT prove:
- Pitches are correct (transposition, arpeggio may be unmodeled)
- Durations are correct (tempo accumulator, tick rate may be wrong)
- Envelopes are correct (envelope tables may be misinterpreted)
- The music sounds like the game

Why: Battletoads parser v3 achieved zero parse errors with 955 notes
while duration accounting was off by 1.52x and arpeggio system was
entirely unmodeled.

## 14. Execution Semantics Validation Is Mandatory

After parser alignment:
1. Build frame-level simulator from parsed events + driver semantics
2. Simulate tempo accumulator, duration counters, pitch modulation, volume envelopes
3. Compare simulated per-frame output against Mesen trace
4. Classify mismatches by cause
5. Block promotion to MIDI/REAPER until comparison passes thresholds

Acceptance criteria:
- 90%+ period match on sounding frames
- 80%+ volume match
- Note boundaries within ±1 frame of trace attacks
- Both parse phase AND execution semantics phase must pass

## 15. Five Pipeline Layers Must Stay Distinct

1. **Parsed event stream** — structural hypothesis only
2. **Simulated driver state** — frame-level execution
3. **Observed ground truth** — Mesen trace / NSF captures
4. **Frame IR** — interpreted musical events
5. **Downstream projection** — MIDI, CC, SysEx, RPP

No layer may be skipped. No two layers may be collapsed.

## 16. Noise Is a Separate Semantic Domain

Noise has period index (not frequency), mode bit, hit detection semantics.
Different validation criteria. A game may have validated melodic channels
while noise remains hypothesis-only.

## 19. Three Independent Validation Axes

1. **Mesen trace** — APU register dumps, frame-level, highest fidelity
2. **VGM logs** — timestamped register writes from VGMRips (caveat: NSF-logged VGMs inherit NSF errors)
3. **NES-MDB** — Stanford dataset (5278 songs, 24 Hz resolution)

Cross-validation: "where do they disagree, and why?"

## 20. Non-Linear APU Mixing

Pulse: `95.88 / ((8128.0 / (sq1 + sq2)) + 100.0)`
TND: `159.79 / ((1.0 / ((tri/8227) + (noise/12241) + (dpcm/22638))) + 100.0)`

Two pulses at max = 0.278, not 0.368. Linear mixing is wrong by up to 15%.

## 21. Non-Note Sound Events

Pipeline must handle: $4011 DAC writes, sweep unit, noise mode bit, frame counter sync.
Frame IR event_type: note | envelope | duty | dac | sweep | noise_mode

## 23. Expansion Audio Is a Known Gap

6 chips (VRC6, VRC7, FDS, MMC5, N163, 5B) affecting ~250+ games.
Pipeline silently discards expansion audio. Check NSF header byte $07B.
See `docs/MULTI_CHIP_SCHEMA.md` for full register specs and schema.

## 24. DPCM Sample Playback vs Direct DAC Are Distinct

DPCM ($4010-$4013 + $4015 bit 4): DMA from ROM samples.
Direct DAC ($4011 alone): software-computed values.
Detection: $4012/$4013 written → DPCM; rapid $4011 alone → algorithmic.

## 25. NSF Trust Is Not Binary

| Trust Level | Criteria | Action |
|------------|---------|--------|
| High | Family 1-3, no DPCM, no known issues | NSF is ground truth |
| Suspect | Family 4-5 OR DPCM OR known-divergent | Seek cross-validation |
| Unusable | NSF2-required, broken rip, game-state-critical | Cannot use NSF |

Known divergent: Super Mario Bros, Battletoads, Gradius.
