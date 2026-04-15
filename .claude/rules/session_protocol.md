# Session Protocol (Core)

ROM-parsing gates, validation ladder, execution semantics checklist:
see `docs/VALIDATION_REFERENCE.md`. Gate checklists: `docs/VALIDATION.md`.
Oracle API: `docs/AGENT_ORACLE.md`.

## Working Order (mandatory)

1. Environment validity (session_startup_check.py)
2. **Oracle preflight** (NON-NEGOTIABLE for serious work):
   ```python
   from ANTIRIPPER.agent_oracle import AgentOracle
   oracle = AgentOracle()
   ctx = oracle.get_preflight_context("game_slug", "nsf_extraction")
   print(oracle.get_game_inventory("game_slug"))
   ```
   This returns: driver family, prevention patterns, hardware facts,
   claims, prior decisions, what output already exists.
3. Source identity and track mapping (DB + track_names)
4. **Driver family classification** (run driver_survey.py --game <slug>)
5. Ground-truth comparison (Mesen vs NSF vs VGM if available)
6. Route choice (nsf / trace / hybrid / apu2_sysex), informed by family
7. Extract: `nsf_to_reaper.py` (NSF) or `trace_to_midi.py` (trace)
8. If fidelity route sounds wrong: inspect Frame IR, then raw frame state
9. If fidelity route sounds right: compare CC/Console route for playability
10. Batch build (only after one song passes all gates)

Do not skip ahead. Do not change multiple layers at once.

## NON-NEGOTIABLE: Never Skip Frame IR

Trace → frame state → Frame IR → MIDI. No shortcuts.

## Fix Order (mandatory)

pitch → timing → volume → timbre. One hypothesis per test cycle.

## Debugging Order (mandatory)

1. Check SysEx/register replay first
2. SysEx correct → problem is CC encoding / projection
3. SysEx wrong → problem is source extraction or synth
4. NEVER debug MIDI before confirming FrameState is correct
5. Inspect Frame IR decisions before MIDI note events

## Canonical Representation

Dense per-frame APU state is truth. Frame IR is interpretation.
MIDI is downstream projection. Debug frame state, not MIDI.

## Three Layers (never conflate)

1. **Observed** (ground truth): raw registers. Authoritative.
2. **Intent** (interpretation): parsed events, Frame IR. HYPOTHESIS.
3. **Projection** (output): MIDI, RPP, synth. PROVISIONAL.

## Three Use-Cases (never collapse)

1. Archival fidelity (SysEx replay)
2. Editable project (CC-driven REAPER)
3. Live keyboard (ADSR synth)

## Ground Truth Priority

1. Mesen trace > 2. ROM music data > 3. NSF extraction > 4. Frame IR > 5. MIDI/CC > 6. Synth

## Oracle Recording (mandatory for significant work)

Before risky code changes or analysis:
```python
attempt_id = oracle.record_attempt("slug", "task_type", "hypothesis", "planned_change")
```

After completing work:
```python
oracle.record_outcome(attempt_id, "success|failure", evidence_refs=[...], lessons="...")
oracle.log_decision("slug", "extraction_route", rationale="...", outcome="...")
```

Important discoveries must be promoted (see CLAUDE.md "Knowledge Hardening"):
- Code fix alone is not enough
- Add/update a rule file
- Record in oracle (attempt/outcome, decision, claim, or prevention pattern)
- Update MISTAKEBAKED.md if the mistake cost 2+ prompts

## Delivery Gate (summary)

Nothing is "ready to test" unless:
- Extraction pipeline ran successfully (nsf_to_reaper.py or trace_to_midi.py)
- At least one fidelity route passed blocking validations
- SysEx/APU2 route evaluated, Frame IR inspected
- Every artifact labeled with Validation Ladder rung
- Below Rung 3 = "hypothesis output"
- Run session_startup_check.py + sync_jsfx.py before delivery
- Decision record logged via oracle for new or changed extraction routes

Full delivery checklist and validation ladder: `docs/VALIDATION_REFERENCE.md`
Gate checklists (A-F): `docs/VALIDATION.md`
