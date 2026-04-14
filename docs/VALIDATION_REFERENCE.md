# Validation Reference (Extended Protocol)

ROM-parsing gates, validation ladder, execution semantics checklist,
and detailed delivery requirements. Read this file when doing ROM
parsing, trace validation, or preparing deliveries.

Core protocol (always loaded): `.claude/rules/session_protocol.md`

---

## Three Validation Axes (triangulation)

1. **Mesen trace** — APU register dumps from gameplay. Frame-level. Highest fidelity.
2. **VGM logs** — timestamped register writes from VGMRips.
   Tool: `scripts/vgm_to_frame_state.py --compare <nsf_midi>`.
   Caveat: NSF-logged VGMs inherit NSF errors.
3. **NES-MDB** — Stanford dataset, 5278 songs, 24 Hz resolution.

When two agree and one disagrees → systemic issue in the disagreeing source.
When all three disagree → genuine NSF-vs-ROM divergence.

## Driver Family-Aware Validation

| Family | Trust NSF? | Validation | Key Risks |
|--------|-----------|------------|-----------|
| 1: Hardware Envelope | Yes | Basic | Little to go wrong |
| 2: Standard Envelope | Yes | Standard | Check CC11 shape |
| 3: Duty Animators | Yes | Standard | Check CC12 animation |
| 4: Dense Automators | Maybe | Thorough | MIDI size explosion |
| 5: Full Animation | Maybe | Thorough | Both axes dense |

Families 4-5: prefer Mesen trace or VGM cross-validation.

## ROM Parsing Pipeline Gates

### Gate 1: Parser Alignment (STRUCTURAL)

- All command boundaries align with zero desync
- Subroutine calls nest correctly, loops detected
- This is structural only. Parser output is a hypothesis.

### Gate 2: Execution Semantics Validation (SEMANTIC)

Simulate the driver frame by frame:
1. Tempo accumulator (8-bit overflow)
2. Duration counters per channel
3. Pitch modulation (arpeggio, vibrato, sweep)
4. Volume envelopes
5. Duty cycle state

Passes when:
- Period matches trace on 90%+ of sounding frames
- Volume matches trace on 80%+ of frames
- Note boundaries within ±1 frame

Required artifacts: parsed event stream, simulated frame-state,
comparison report, mismatch taxonomy.

### Gate 3: Frame IR + Projection

Only after Gate 2: generate Frame IR → project to MIDI/REAPER → ear-check.

## Validation Ladder

| Rung | Name | Proves | May Claim |
|------|------|--------|-----------|
| 0 | Unexamined | Nothing | Nothing |
| 1 | Parser-aligned | Byte structure | "boundaries identified" |
| 2 | Internal semantics | Sim matches NSF | "simulator agrees with emulator" |
| 3 | External trace | Sim matches Mesen | "validated against hardware" |
| 4 | Trusted projection | Rung 3 + IR + ear | "trusted output for [scope]" |
| 5 | Full-game trusted | All songs/channels | "complete validated extraction" |

Partial trust is normal. Noise documented separately. Always state scope.

## Delivery Gate (full)

- kitchen_sink.py ran successfully
- At least one fidelity route passed all blocking validations
- Report artifacts produced, route assumptions explicit
- SysEx/APU2 evaluated, Frame IR inspected
- ROM-parsing: execution semantics validation passed (Gate 2)
- Parser alignment alone (Gate 1) NOT sufficient
- Every artifact labeled with Validation Ladder rung
- Below Rung 3 = "hypothesis output"
- Noise status documented separately
- Per-game validation record updated
- session_startup_check.py + sync_jsfx.py run

### Trust labeling

Always state: rung, channels/songs validated, "trusted" vs "hypothesis output", scope.
Never say "done" or "correct" for hypothesis output.

## Execution Semantics Checklist

```
[ ] 1. Parser alignment — zero desync all channels
[ ] 2. Command semantics verified — param counts, effects
[ ] 3. Frame simulator built — tempo, duration, modulation
[ ] 4. Tempo/tick validated — accumulator overflow matches trace
[ ] 5. Duration boundaries validated — attacks align with trace
[ ] 6. Modulation/arpeggio modeled — per-frame offsets correct
[ ] 7. Envelope/volume modeled — per-frame volume matches trace
[ ] 8. Simulated vs trace comparison — mismatch report produced
[ ] 9. Mismatch categories explained — no unexplained divergences
[ ] 10. Only THEN: export MIDI / generate REAPER project
```

## Data Tier Rules

- SQLite (data/pipeline.db): operational truth
- JSON: config, game profiles, route learnings
- Markdown: reasoning, postmortems
- Raw files (CSV, ROM, NSF): on disk, indexed by DB
- Frame IR (frame_ir.json): per-run interpretation artifact
