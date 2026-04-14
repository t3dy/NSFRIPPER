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

Site: https://t3dy.github.io/ReapNES/

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
  validation against ground truth. See `.claude/rules/architecture.md` Rules 13-17.
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
- Handover (legacy): @docs/HANDOVER.md

## Driver Families (CC11/CC12 density classification)

| Family | CC11/note | CC12/note | Envelope Mode | NSF Trust | Example Games |
|--------|-----------|-----------|---------------|-----------|---------------|
| 1: Hardware Envelope | 0.0-2.8 | < 0.5 | HW decay | High | Mega Man, DuckTales, W&W |
| 2: Standard Envelope | 2.8-5.6 | < 0.5 | SW per-frame | High | CV1, Contra, Battletoads |
| 3: Duty Animators | 3.7-4.9 | 0.7-1.0 | SW vol+duty | High | SMB1, CV3 US, Kirby |
| 4: Dense Automators | 5.1-14.9 | < 0.5 | SW obsessive | Medium | FF, Blaster Master, Batman |
| 5: Full Animation | > 7.0 | > 1.0 | SW both axes | Medium | SMB3 (sole member) |

Classify at ingest: `python scripts/driver_survey.py --game <slug>`

## New Tools (2026-04-13 research sprint)

| Tool | Purpose |
|------|---------|
| `scripts/vgm_to_frame_state.py` | VGM → per-frame APU state, cross-validate vs NSF MIDI |
| `scripts/nsfe_metadata.py` | Parse NSFE files for track names, durations, composer |
| `scripts/driver_survey.py` | Classify games into driver families (updated with new names) |

## Game Extraction Status

| Game | Ladder Rung | Melodic | Noise | Notes |
|------|-------------|---------|-------|-------|
| Castlevania 1 | 4 (trusted) | Validated | Validated | Proven pipeline. 0 pitch mismatches. |
| Contra | 4 (trusted) | Validated | Validated | Proven pipeline. |
| Wizards & Warriors | 2-3 (partial) | Rung 2 all 16 songs (512f), Rung 3 title (2169f) | Rung 1 (structural) + partial Rung 2 (3 active songs) | Strong milestone, not final. See W&W validation record. |
| Battletoads | 1 (parser-aligned) | Structural only | Structural only | Execution semantics validation in progress. |
| Super Mario Bros | NSF only | N/A | N/A | NSF pipeline, no ROM parser. |

Existing MIDI/RPP output for games below Rung 3 is **hypothesis output** —
usable for practical work (listening, arrangement) but not claimable as
verified or trusted.

## Rules & Validation

See `.claude/rules/architecture.md` for the 22 architectural rules.
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

## Known Gaps (from 2026-04-13 gap analysis)

See `docs/NES_AUDIO_GAPS_AND_NEXT_STEPS.md` for full analysis.

| Gap | Impact | Status |
|-----|--------|--------|
| Expansion audio (VRC6/FDS/5B/N163/VRC7/MMC5) | ~250 games silently losing channels | Not started |
| DPCM/DAC conflation ($4011) | Battletoads drums, Sunsoft bass misrepresented | Schema designed, not implemented |
| Missing APU events (phase reset, $4015, sweep) | Same-pitch retriggers merge, unexplained silences | Schema designed, not implemented |
| No cross-validation pipeline | Can't auto-compare NSF vs VGM vs NES-MDB | vgm_to_frame_state.py built, cross_validate.py not |
| ROM parsing coverage (~80 games vs 1577) | Capcom 6C80 is highest-ROI next parser | Format doc exists (RH #274), parser not built |

### Implementation Plan (Hiro Plantagenet 7-Layer)

| Layer | Purpose | Depends On | Status |
|-------|---------|-----------|--------|
| 1: Audit & Schema | Scan expansion flags, design multi-chip Frame IR | None | **Complete** (297 NSFs, 35 expansion) |
| 2: Frame IR Extensions | Implement all missing event types + chip types | Layer 1 | **Complete** (38 tests, all chips) |
| 3: Capture Pipeline | Update nsf_to_reaper.py for expansion + DPCM + phase reset | Layer 2 | **Partial** (capture done, processing TBD) |
| 4: Validation Infrastructure | cross_validate.py + nsf_trust_scorer.py | Layer 3 | Not started |
| 5: ROM Parsers | Capcom 6C80 + Sunsoft (parallel with 3-4) | Layer 2 | Not started |
| 6: Synth Fidelity | Non-linear mixing + expansion audio in JSFX | Layer 3 | Not started |
| 7: Classification Refinement | Sub-family patterns, secondary metrics | Layer 4 | Not started |

## Key Commands

```bash
# PRIMARY: kitchen_sink.py generates all routes, validates, compares, blocks on failure
python scripts/kitchen_sink.py \
  --capture <trace.csv> --game <Game> --name <Song> -o output/<Game>/

# Legacy single-route (being replaced by kitchen_sink.py):
python scripts/batch_nsf_all.py                                    # batch all games
python scripts/nsf_to_reaper.py <nsf> --all -o output/X/          # single game NSF pipeline
python scripts/trace_to_midi.py <capture.csv> -o output/X/ --auto-segment  # trace pipeline
python scripts/generate_project.py --midi <f> --nes-native -o <out>  # REAPER from MIDI
PYTHONPATH=. python scripts/trace_compare.py --frames 1792         # validate CV1 parser
python scripts/generate_site.py                                     # rebuild website
```
