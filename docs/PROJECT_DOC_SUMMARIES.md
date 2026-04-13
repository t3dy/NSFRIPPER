# Project Documentation Summaries

This summary groups the most heavily documented project threads in the repo by
theme rather than by single file length. The rough documentation weight is based
on the combined size of closely related markdown files in `docs/`.

## 1. Core Pipeline Architecture

Approximate documentation weight: 127 KB across architecture and pipeline docs.

Key files:
- `docs/ARCHITECTURE_SPEC.md`
- `docs/DATAONTOLOGY.md`
- `docs/DATABASETAKEAWAYS.md`
- `docs/KITCHENSINKAUDIT.md`
- `docs/PIPELINEOVERHAUL42.md`
- `docs/SYNTHMERGE.md`
- `docs/NESMUSICTRANSLATEDTOMIDI.md`
- `docs/SOLVINGTHECHIPTUNEVSMIDIPROBLEM.md`

Summary:
- The repo's main project is an NES music extraction and playback pipeline that
  turns ROMs, NSFs, and Mesen traces into MIDI, REAPER projects, validation
  reports, and game-specific playback routes.
- The architectural center of gravity is "rules must become code." The docs push
  hard against prompt-only discipline and toward a deterministic orchestration
  kernel that runs all viable routes, validates them automatically, compares
  them, and refuses delivery when fidelity routes fail.
- A recurring design boundary is the separation between canonical observed data,
  inferred musical interpretation, and downstream DAW projection. The pipeline
  should preserve provenance at every stage and make route assumptions explicit.
- The core system is meant to support multiple extraction routes: NSF-derived,
  trace-derived, hybrid, and engine-specific adapters, with strong emphasis on
  cross-route comparison and evidence preservation for debugging.

## 2. Mario Fidelity Investigation

Approximate documentation weight: 78 KB across Mario-specific investigation and
repair notes.

Key files:
- `docs/MARIODISCOVERIES.md`
- `docs/FIXINGMARIO1.md`
- `docs/HIROPLANTAGENET_MARIO_FIDELITY.md`
- `docs/HACKINGMARIOWEB.md`
- `docs/WEBRESEARCHMARIOMUSIC.md`
- `docs/PROJECTMARIO1.md`
- `docs/THINGSWETRIED.md`
- `docs/REFINEMENT_PLAN.md`
- `docs/ROM_MUSIC_MYSTERIES.md`

Summary:
- Mario became a deep forensic project because the NSF extraction path produced
  pulse and triangle notes one octave too high relative to Mesen hardware
  captures, even though note intervals were correct.
- The docs frame Mario as both a bug hunt and a musical identity study: the
  target sound is a bright, fixed 50% duty pulse voice with a uniform 5-step
  staccato decay and highly regular pulse-note durations.
- Several Mario notes emphasize that playback fidelity currently depends less on
  note parsing than on honoring CC11 envelope automation in the synth. The MIDI
  data contains the right decay shape; the playback chain still needs to obey it.
- Mario also acts as a stress test for false assumption transfer. Same console
  hardware does not imply the same engine semantics as Konami titles, so the
  project repeatedly circles back to measured trace evidence instead of analogy.

## 3. Konami Driver Breakthroughs

Approximate documentation weight: 70 KB across Castlevania/Contra lessons and
generalized failure analysis.

Key files:
- `docs/PROJECTCASTLEVANIA.md`
- `docs/PROJECTCONTRA.md`
- `docs/WHATWORKEDWITHCONTRAANDCASTLEVANIA.md`
- `docs/FAILURE_MODES.md`
- `docs/INVARIANTS.md`
- `docs/HARDENING.md`

Summary:
- Castlevania and Contra are the repo's strongest proof that the methodology can
  reach near-ground-truth output when the driver is understood and each fix is
  tested against trace data.
- The documentation highlights specific reverse-engineering wins: correct period
  base, FE loop semantics, game-specific DX byte counts, table-driven Contra
  envelopes, and the separation of parser events from frame-level envelope
  shaping.
- These docs are as much about engineering discipline as about music extraction.
  "Dump trace before modeling," "read disassembly before guessing," and
  "cross-game validation" are treated as core workflow laws.
- Castlevania and Contra supply the reusable lessons that later become hardened
  architecture and anti-pattern catalogs.

## 4. Battletoads Trace Pipeline

Approximate documentation weight: 48 KB across Battletoads-specific failure,
handover, and validation docs.

Key files:
- `docs/VALIDATION_REPORT_BATTLETOADS_L1.md`
- `docs/WHYSUCHABADSTARTWITHBATTLETOADS.md`
- `docs/HANDOVER_BATTLETOADS.md`
- `docs/BATTLETOADS_SESSION_BLOOPERS.md`
- `docs/FRAMEBYFRAME.md`
- `docs/ANXIETY.md`
- `docs/BUILDINGTHEENVIRONMENT.md`
- `docs/FINDINGTRACKBOUNDARIES.md`

Summary:
- Battletoads is documented as the great cautionary tale: NSF extraction looked
  structurally valid but failed as a fidelity route, which forced a shift to
  trace-derived MIDI plus SysEx register replay.
- The Battletoads docs focus on preserving what makes the music feel alive:
  sweep-unit vibrato, dense per-frame register motion, loop-aware validation,
  and a more explicit distinction between "file exists" and "sounds right."
- The docs also show the repo maturing under pressure. Battletoads exposed weak
  assumptions, loose validation, and overconfidence in known-good paths from
  other games, then pushed the project toward more instrumented workflows.
- Compared with the Mario thread, Battletoads is less about one clean musical
  signature and more about handling a noisy, highly dynamic, trace-first case.

## Image Direction

The accompanying illustrations focus on these four documentation-heavy threads:
- core pipeline architecture
- Mario fidelity investigation
- Konami driver breakthroughs
- Battletoads trace pipeline

Each image is a cartoon workflow diagram rather than a literal screenshot. The
goal is to make the repo's documented thinking feel playful, legible, and easy
to scan at a glance.
