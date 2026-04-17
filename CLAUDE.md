# NES Music Studio

NSF/ROM → MIDI → REAPER/WAV/MP4 → YouTube.

## The Product

**ReapNES Studio** is a single unified JSFX synthesizer plugin for REAPER that:
1. Plays NES game music from MIDI files at ROM-level accuracy (via SysEx register replay)
2. Works with a MIDI keyboard for modern composers (via ADSR envelopes)
3. Has a vintage analog synth console UI — knobs, sliders, oscilloscope
4. Shows parameter changes in real time for video recording (YouTube)
5. Makes game-to-game timbral differences visible through knob positions

**One synth, not many.** All functionality lives in one plugin. The synth
auto-detects its input: SysEx → hardware replay, CC11/CC12 → envelope
playback, keyboard only → ADSR mode. See `docs/SYNTHMERGE.md` for the
full design and `docs/SOLVINGTHECHIPTUNEVSMIDIPROBLEM.md` for the
architecture.

## Priority: Production Pipeline

The primary goal is producing REAPER projects and YouTube videos for all
games in the library. Maximize deterministic scripting; minimize LLM involvement.

### Layer 1: Batch Production (DETERMINISTIC — no LLM)

For games with NSF files, the entire pipeline is automated:

```bash
python scripts/batch_nsf_all.py                           # all unprocessed games
python scripts/nsf_to_reaper.py <nsf> --all -o output/X/  # single game
python scripts/generate_project.py --midi <f> --nes-native -o <out>  # REAPER from MIDI
```

Output per game: `output/<Game>/midi/`, `output/<Game>/reaper/`, `output/<Game>/wav/`

### Layer 2: Quality Validation (HUMAN — ear-check)

After batch production, user listens to output and flags issues.
Not every game needs trace-level validation. NSF emulation is ground truth.

### Layer 3: ROM Reverse Engineering (LLM-ASSISTED — only when needed)

For games where NSF output is inadequate or deeper fidelity is required:

1. **Identify** — `PYTHONPATH=. python scripts/rom_identify.py <rom>`
2. **Check manifest** — `extraction/manifests/*.json`
3. **Find disassembly** — check `references/`
4. **Parse one track, listen** — gate before batch
5. **Iterate on fidelity** — trace_compare.py

### Layer 4: Website & Distribution (DETERMINISTIC)

```bash
python scripts/generate_site.py          # regenerate per-game pages from output/
```

Site: https://t3dy.github.io/NSFRIPPER/

## Hard Invariants

- **NSF emulation is ground truth** for games without custom ROM parsers.
- **Trace is ground truth** for games with ROM parsers (CV1, Contra, W&W).
- **CC11/CC12 in MIDI files is ground truth for volume/duty envelopes.**
  NSF extraction captures per-frame APU register state as CC automation.
  The synth MUST play these back faithfully, not override with ADSR.
- **Triangle is 1 octave lower than pulse** (hardware fact).
- **Version output files** (v1, v2...). Never overwrite a tested file.
- **Same opcode ≠ same semantics** across drivers. Check manifest.
- **generate_project.py is the only way to make RPP files.** Never write RPP by hand.
- **One synth plugin (ReapNES Studio).** Not multiple JSFX files.
  All playback modes live in one plugin with a three-priority input cascade:
  Priority 1: SysEx register replay (hardware-exact).
  Priority 2: CC11/CC12 automation (file playback).
  Priority 3: ADSR keyboard (live composing).
  Auto-detects from incoming data. See docs/SYNTHMERGE.md.
- **Projects must work with zero manual REAPER configuration.** Keyboard,
  MIDI routing, synth settings — everything baked into the RPP file.
- **Parser output is hypothesis, not music.** Structural parsing gives
  event structure. Trusted musical output requires execution semantics
  validation against ground truth. See `docs/ARCHITECTURE_REFERENCE.md` Rules 13-16,
  `.claude/rules/architecture.md` Rule 17.
- **Noise is a separate semantic domain.** Do not force noise channels
  through melodic assumptions. Noise has different encoding, validation
  criteria, and runtime behavior. Document noise status separately.

## Fidelity Hierarchy

Truth flows downhill. Never let a lower layer override a higher one.

1. **Mesen Trace** — APU register dumps from real gameplay. Frame-level ground truth.
   NSF may diverge from actual game audio (proven: Battletoads, Mario).
   When Mesen trace and NSF disagree, Mesen wins.
2. **SysEx in MIDI** — Lossless register state encoding. Synth replays hardware.
3. **NSF emulation** — 6502 CPU runs the sound driver. Per-frame CC11/CC12.
   Convenient but not always faithful to in-game audio.
4. **CC11/CC12 in MIDI** — Volume + duty envelope. Loses sweep, noise mode, phase.
5. **ADSR approximation** — Only for live keyboard when no file data exists.

Per-game route decision: if NSF fidelity score (via trace_compare) < 80%,
use trace pipeline. Battletoads and Mario are confirmed trace-required games.

## Deckard Boundary (deterministic vs LLM)

| Deterministic (code) | LLM-appropriate |
|----------------------|-----------------|
| NSF emulation, MIDI export, RPP generation | Driver identification from unknown ROMs |
| WAV rendering, MP4 creation, site generation | Command format reverse engineering |
| Trace validation, batch processing | Manifest hypothesis authoring |
| CC11/CC12 playback in synth (frame-accurate) | Game-specific ADSR tuning for keyboard |
| Channel auto-mapping, Bach mashup matrix | Track naming for games without M3U |

## State

- Per-game output: `output/<Game>/` — midi, reaper, wav, nsf
- Manifests: `extraction/manifests/*.json`
- Driver families: `docs/DRIVER_FAMILIES_AND_GAMES.md` (5 families, 30 game profiles)
- Web research: `docs/research/` (ARCHIVES, NESDEV, ENGINES, RIPPING_STATE_OF_ART)
- Priorities: this file
- Mistake narratives: @docs/MISTAKEBAKED.md
- Oracle knowledge base: `ANTIRIPPER/antiripper_v2.db` via `docs/AGENT_ORACLE.md`
- Oracle API: `ANTIRIPPER/ORACLE_API.md` (cheatsheet)
- Handover archive: `docs/HANDOVER_2026_04_14_FINAL.md` (latest)

## Driver Families (CC11/CC12 density classification)

Revised 2026-04-14 based on 271-game census. Family 5 eliminated (zero members).
See `docs/NEWDRIVERFAMILIES414.md` for full analysis.

| Family | CC11/note | CC12/note | Envelope Mode | NSF Trust | Count | Example Games |
|--------|-----------|-----------|---------------|-----------|-------|---------------|
| 1: Sparse Envelope | 0.0-2.8 | < 0.7 | HW decay / set-once | High | 156 | Mega Man, DuckTales, W&W |
| 1A *(sub)* | 0.0-0.5 | < 0.3 | Truly HW-only | High | 53 | Marble Madness, Section Z, Trojan |
| 1B *(sub)* | 0.5-2.8 | < 0.3 | Occasional SW vol | High | 103 | Mega Man 3, Castlevania, Battletoads |
| 2: Active Envelope | 2.8-5.6 | < 0.7 | SW per-frame | High | 79 | Contra, Ninja Gaiden, Zelda II |
| 3: Duty Animators | any | >= 0.7 | SW vol+duty | High | 20 | SMB3, Konami Hyper Soccer, Snakes Revenge |
| 4: Dense Automators | > 5.6 | < 0.7 | SW obsessive | Medium | 16 | Metroid, Kid Icarus, Rad Racer II |

Fuzzy zone: 13 games with CC12 0.3-0.7 need ear-check classification.

Classify at ingest: `python scripts/driver_survey.py --game <slug>`
Full census: `python scripts/family_census.py` (data in `data/family_census_v2.json`)

## New Tools (2026-04-13/14 research sprints)

| Tool | Purpose |
|------|---------|
| `scripts/vgm_to_frame_state.py` | VGM → per-frame APU state, cross-validate vs NSF MIDI |
| `scripts/nsfe_metadata.py` | Parse NSFE files for track names, durations, composer |
| `scripts/driver_survey.py` | Classify games into driver families (revised 4-family model) |
| `scripts/family_census.py` | Fast CC density census across all games (271-game dataset) |

## Game Extraction Status

| Game | Ladder Rung | Melodic | Noise | Notes |
|------|-------------|---------|-------|-------|
| Castlevania 1 | 4 (trusted) | Validated | Validated | Proven pipeline. 0 pitch mismatches. |
| Contra | 4 (trusted) | Validated | Validated | Proven pipeline. |
| Wizards & Warriors | 2-3 (partial) | Rung 2 all 16 songs (512f), Rung 3 title (2169f) | Rung 1 (structural) + partial Rung 2 (3 active songs) | Strong milestone, not final. See W&W validation record. |
| Battletoads | 1 (parser-aligned) | Structural only | Structural only | Execution semantics validation in progress. |
| Super Mario Bros | NSF only | N/A | N/A | NSF pipeline, no ROM parser. Known NSF/trace divergence — trace-required for fidelity but no parser built. |

Existing MIDI/RPP output for games below Rung 3 is **hypothesis output** —
usable for practical work (listening, arrangement) but not claimable as
verified or trusted.

## Rules & Validation

See `.claude/rules/architecture.md` for the core architectural rules (Rules 1-12, 17-18, 22, 26 in rules file; Rules 13-16, 19-21, 23-25 in `docs/ARCHITECTURE_REFERENCE.md`).
See `.claude/rules/session_protocol.md` for workflow, validation ladder, and delivery gates.
See `docs/DRIVER_FAMILIES_AND_GAMES.md` for 30 game profiles and 5 driver family specs.

Key principles (details in rules files):
- **Never skip Frame IR** between trace and MIDI (architecture.md Rule 9)
- **Zero parse errors ≠ musical correctness** — execution semantics validation required (Rules 13-14)
- **Different ROMs use different music engines** — no universal decoder (Rule 10)
- **Driver family is first-class infrastructure** — classify at ingest, drives downstream behavior (Rule 18)
- **Three validation axes** — Mesen trace + VGM logs + NES-MDB for triangulation (Rule 19)
- **Non-linear APU mixing** — pulse channels compress each other (Rule 20)
- **Non-note sound events** — DAC writes, sweep, noise mode need explicit IR types (Rule 21)
- **Three layers: Observed → Intent → Projection** — never conflate (Rule 12)

## Known Gaps (updated 2026-04-14)

See `docs/NES_AUDIO_GAPS_AND_NEXT_STEPS.md` for full analysis.

| Gap | Impact | Status |
|-----|--------|--------|
| Bankswitch emulation | 39 games failed extraction | **FIXED** (Rule 26, session 415) |
| Pipeline hooks not wired | 47% of games had no DB records | **FIXED** (docs/PIPELINEHOOKS.md) |
| Expansion audio: VRC6 + FDS | 35 games, 768 songs recovered | **DONE** (2026-04-16, architecture.md Rule 28 adjacent) |
| Expansion audio: VRC7 + 5B | 4 games (FM synth + YM2149) | Register capture done, parsing/MIDI TBD |
| DPCM/DAC conflation ($4011) | Battletoads drums, Sunsoft bass misrepresented | **DONE** (2026-04-16, architecture.md Rule 28) |
| Non-linear APU mixing | All games too loud in multi-channel | **DONE** (2026-04-15, architecture.md Rule 27) |
| Missing APU events (phase reset, $4015, sweep) | Same-pitch retriggers merge, unexplained silences | Schema designed, not implemented |
| No cross-validation pipeline | Can't auto-compare NSF vs VGM vs NES-MDB | vgm_to_frame_state.py built, cross_validate.py not |
| ROM parsing coverage (~80 games vs 1577) | Capcom 6C80 is highest-ROI next parser | Format doc exists (RH #274), parser not built |
| 140/321 games unclassified by driver survey | CC density unknown for batch | Run: `python scripts/driver_survey.py --report --json` |

### Implementation Plan (Hiro Plantagenet 7-Layer)

| Layer | Purpose | Depends On | Status |
|-------|---------|-----------|--------|
| 1: Audit & Schema | Scan expansion flags, design multi-chip Frame IR | None | **Complete** (297 NSFs, 35 expansion) |
| 2: Frame IR Extensions | Implement all missing event types + chip types | Layer 1 | **Complete** (38 tests, all chips) |
| 3: Capture Pipeline | Update nsf_to_reaper.py for expansion + DPCM + phase reset | Layer 2 | **Mostly done** (VRC6/FDS/DMC done 2026-04-16; phase reset, $4015, sweep still TBD; VRC7/5B still TBD) |
| 4: Validation Infrastructure | cross_validate.py + nsf_trust_scorer.py | Layer 3 | Not started |
| 5: ROM Parsers | Capcom 6C80 + Sunsoft (parallel with 3-4) | Layer 2 | Not started |
| 6: Synth Fidelity | Non-linear mixing + expansion audio in JSFX | Layer 3 | **Partial** (non-linear mixing done 2026-04-15; expansion synth playback TBD) |
| 7: Classification Refinement | Sub-family patterns, secondary metrics | Layer 4 | Not started |

## Key Commands

```bash
# BATCH: extract all games with NSF files (skip-wav, early-exit, scaled timeouts)
python scripts/batch_nsf_all.py                                    # all unprocessed games
python scripts/batch_nsf_all.py --force                            # re-process everything

# SINGLE GAME: NSF emulation pipeline
python scripts/nsf_to_reaper.py <nsf> --all -o output/X/          # all tracks
python scripts/nsf_to_reaper.py <nsf> 2 90 -o output/X/           # single track

# TRACE PIPELINE: ROM-parsed games (CV1, Contra, W&W)
python scripts/trace_to_midi.py <capture.csv> -o output/X/ --auto-segment

# REAPER: generate project from MIDI
python scripts/generate_project.py --midi <f> --nes-native -o <out>

# VALIDATION + CLASSIFICATION
PYTHONPATH=. python scripts/trace_compare.py --frames 1792         # validate parser
python scripts/driver_survey.py --report --json                    # classify all games
python scripts/expansion_detect.py --json -o data/expansion_audit.json

# ORACLE: game inventory before starting work
python -c "from ANTIRIPPER.agent_oracle import AgentOracle; print(AgentOracle().get_game_inventory('Game_Name'))"

# ORACLE: preflight before any serious work
python -c "from ANTIRIPPER.agent_oracle import AgentOracle; o=AgentOracle(); print(o.get_preflight_context('Game_Name', 'nsf_extraction'))"

# SITE
python scripts/generate_site.py                                     # rebuild website
```

## Knowledge Hardening (NON-NEGOTIABLE)

A discovery is NOT baked into the system until it appears in ALL of:
1. **Code** — the fix is implemented and tested
2. **Rule/reference file** — a future session can find it without reading code
3. **Oracle-facing record** — the knowledge is queryable via `get_preflight_context`

Code patches alone are not enough. A fix that lives only in code comments
or handover docs will be invisible to future sessions and WILL be rediscovered
at cost. The bankswitch fix (Rule 26) is the model: it was a 2-line code
change that recovered 233 songs across 16 games, but without the architecture
rule and prevention pattern, a future session could break it or fail to
apply the same principle to a new emulator edge case.

### When a session makes an important discovery, it must:

1. **Fix the code** (the immediate patch)
2. **Add or update a rule** in the appropriate file:
   - Hardware behavior → `.claude/rules/architecture.md` or `synth_fidelity.md`
   - Validation/gate change → `docs/VALIDATION_REFERENCE.md`
   - Emulation behavior → `.claude/rules/architecture.md` (see Rule 26)
   - Parser pattern → `extraction/CLAUDE_EXTRACTION.md`
3. **Record in the oracle** via one or more of:
   - `record_attempt` + `record_outcome` (what was tried, what happened)
   - `propose_claim` (if the finding is game-specific or provisional)
   - `log_decision` (if it changes extraction route or trust level)
   - Prevention pattern (if it's a repeatable failure mode — requires human review)
4. **Update MISTAKEBAKED.md** if the discovery cost 2+ prompts to reach

### Discovery Promotion Pathway

| Discovery Type | Rule/Reference Target | Oracle Target |
|----------------|----------------------|---------------|
| Hardware fact (e.g. triangle octave) | architecture.md (immutable rule) | `hardware_facts` (locked) |
| Recurring failure mode (e.g. bankswitch page offset) | architecture.md + MISTAKEBAKED.md | `prevention_patterns` |
| Route/trust rationale (e.g. NSF diverges from trace) | session_protocol.md fidelity hierarchy | `decision_records` via `log_decision` |
| Provisional interpretation (e.g. driver uses DX=3 bytes) | extraction manifest (hypothesis) | `claims` via `propose_claim` |
| Game/family behavior (e.g. new CC density pattern) | DRIVER_FAMILIES_AND_GAMES.md | `driver_families` + `evidence_items` |
| Emulator bug/fix (e.g. bankswitch range) | architecture.md rule | `prevention_patterns` + `record_outcome` |

### Example: Bankswitch Fix Promotion (2026-04-14)

This is how a discovery should flow through the system:

1. **Code fix**: `nsf_to_reaper.py` — virtual padded bank array + $5FF6-$5FFF range
2. **Architecture rule**: Rule 26 in `.claude/rules/architecture.md` — explains both bugs,
   lists affected games, states impact (233/240 songs recovered)
3. **Prevention pattern**: in oracle DB — "NSF bankswitch: always handle $5FF6-$5FFF,
   always account for load_addr page offset"
4. **Decision record**: extraction route for 16 games changed from "partial/failed" to
   "NSF emulation (bankswitched)"
5. **Mistake narrative**: in MISTAKEBAKED.md — cost, root cause, where warnings now live

## Oracle Workflow (Mandatory for Serious Work)

The oracle at `ANTIRIPPER/antiripper_v2.db` is the project's institutional
memory. It is not optional tooling — it is how discoveries become reusable
across sessions. See `docs/AGENT_ORACLE.md` for the full API.

### Before starting work on any game:

```python
from ANTIRIPPER.agent_oracle import AgentOracle
oracle = AgentOracle()

# 1. Preflight: what do we already know?
ctx = oracle.get_preflight_context("game_slug", "nsf_extraction")
# Returns: driver_family, prevention_patterns, hardware_facts, claims, decisions

# 2. Inventory: what output already exists?
print(oracle.get_game_inventory("game_slug"))
# Returns: all directories, versions, MIDI counts, best version recommendation
```

### Before making risky code changes:

```python
# 3. Record intent BEFORE the change
attempt_id = oracle.record_attempt(
    "game_slug", "nsf_extraction",
    hypothesis="Bankswitch handler missing $5FF6-$5FF7 range",
    planned_change="Extend range to $5FF6-$5FFF, add page offset",
)

# 4. Check guardrails for the subsystem you're editing
guards = oracle.get_edit_guardrails("routing")
```

### After completing work:

```python
# 5. Record what happened
oracle.record_outcome(
    attempt_id, result="success",
    evidence_refs=["output/Ninja_Gaiden/midi/"],
    lessons="Non-page-aligned load_addr shifts all bank boundaries. $5FF6-$5FF7 must be handled.",
)

# 6. Log the decision if it changes a game's extraction route
oracle.log_decision(
    "ninja_gaiden", "extraction_route",
    rationale="Bankswitch fix recovered all 65 tracks via NSF emulation",
    outcome="nsf_emulation_bankswitched",
)
```

### What the oracle tables are for:

| Table | Contains | When to write |
|-------|----------|---------------|
| `hardware_facts` | Immutable APU/NES behavior | Never (human-curated, locked) |
| `prevention_patterns` | Learned failure modes | After a mistake costs 2+ prompts |
| `driver_families` | CC11/CC12 classification | At ingest via driver_survey.py |
| `evidence_items` | File paths, metrics, observations | Pipeline hooks (auto) or manual |
| `claims` | Provisional hypotheses | When a finding is game-specific |
| `decision_records` | Route/trust/method choices | After resolving extraction route |
| `attempts` | What was tried and why | Before risky changes |

### Current gaps (from 2026-04-14 audit):

- 105/225 BESTOUTPUT games have no decision record (47%)
- attempts/claims tables are empty (pipeline hooks not wired)
- 140/321 games unclassified by driver survey

## Where to Find Things (Cross-Reference Index)

| What you need | Where to look |
|---------------|---------------|
| Core architecture rules (1-12, 17-18, 22, 26) | `.claude/rules/architecture.md` |
| Extended rules (13-16, 19-25) | `docs/ARCHITECTURE_REFERENCE.md` |
| Session workflow, fix order, debug order | `.claude/rules/session_protocol.md` |
| Gate checklists (A-F) | `docs/VALIDATION.md` |
| Validation ladder, execution semantics | `docs/VALIDATION_REFERENCE.md` |
| Synth fidelity, CC semantics, mixing | `.claude/rules/synth_fidelity.md` |
| RPP generation rules | `.claude/rules/reaper_projects.md` |
| JSFX deployment, pre-delivery | `.claude/rules/jsfx_deploy.md` |
| Driver families (5 families, 30+ profiles) | `docs/DRIVER_FAMILIES_AND_GAMES.md` |
| Oracle API (full) | `docs/AGENT_ORACLE.md` |
| Oracle API (cheatsheet) | `ANTIRIPPER/ORACLE_API.md` |
| Mistake inventory (what burned prompts) | `docs/MISTAKEBAKED.md` |
| Pipeline hooks (auto evidence/decisions) | `docs/PIPELINEHOOKS.md` |
| Expansion audio schema | `docs/MULTI_CHIP_SCHEMA.md` |
| Known gaps + Hiro Plantagenet layers | This file (Known Gaps section) |
