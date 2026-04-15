# Handover: NSFRIPPER session 2026-04-14 (FINAL)

## Paste This to Start Next Session

```
Handover: NSFRIPPER session 2026-04-14e

## What Was Done (14 commits)

### Hiro Plantagenet Layers 1-3
- Layer 1 COMPLETE: expansion_detect.py scanned 297 NSFs, found 35 with expansion audio. Schema at docs/MULTI_CHIP_SCHEMA.md.
- Layer 2 COMPLETE: extraction/frame_ir.py — chip-agnostic FrameState for all 6 expansion chips + DPCM. 38 tests pass. Konami module re-exports.
- Layer 3 PARTIAL: nsf_to_reaper.py now captures expansion register writes (VRC6 + FDS verified) and parses them in frames_to_channel_data(). MIDI export for expansion channels not yet implemented.

### Batch Extraction
- 321 games with MIDI (8,951 total MIDIs), 278 REAPER projects
- BESTOUTPUT/ folder: 224 fully-extracted games with MIDI + REAPER (4.8GB)
- Retry batch attempted 5/45 partial games (2 ok, 2 timeout, 1 interrupted)
- ~40 games still partially extracted (see unsolved.md for analysis)

### Emulator Improvements
- Early-exit heuristic: stops after 30 stuck frames or 120 silent frames. Turns 600s timeouts into 3s fails.
- --skip-wav flag: batch_nsf_all.py now skips WAV renders (30% faster)
- Control char fix: strips \n from NSF title fields (was breaking Cleopatra filenames)
- NSF header fallback: batch reads byte 6 for song count when no M3U exists
- Scaled timeouts: 60s/track, min 600s, max 3600s

### ANTIRIPPER Oracle
- Rebuilt agent_oracle.py with preflight/attempt/outcome workflow (24 tests)
- NEW: get_game_inventory(slug) — shows all directories, versions, MIDI counts, NSF info, DB records, best version recommendation
- DB populated: 1162 evidence, 181 decisions, 16 hardware facts, 5 families
- GAP: claims/attempts tables empty (pipeline hooks not wired yet)
- GAP: driver survey covers 181/321 games (140 new games unclassified)

### System File Cleanup
- settings.local.json: 33KB → 1.5KB (96% token reduction)
- Removed kitchen_sink.py phantom from CLAUDE.md, session_protocol.md, VALIDATION_REFERENCE.md
- Fixed architecture rule count, updated Key Commands with actual scripts
- Total context tax: ~22K → ~9.7K tokens/session (56% reduction)

## What Needs to Happen Next (Priority Order)

### 1. Fix Bankswitch Emulation (unlocks 39 games)
output/unsolved.md has the full analysis. 84% of failing games are bankswitch.
The py65 emulator handles simple bank layouts but fails on complex ones. Three approaches:
- Quick: audit memory wrapper chain in nsf_to_reaper.py (BankswitchMemory + CaptureMemory interaction)
- Medium: install libgme Python package as fallback emulator (renders audio, loses register data)
- Full: use Mesen headless for register-accurate capture of all NSFs

### 2. Run Driver Survey on All 321 Games
140 games have MIDI but no CC11/CC12 classification. Run:
```bash
python scripts/driver_survey.py --report --json
python ANTIRIPPER/scripts/ingest_all.py
```
This closes the 140-game classification gap and populates decision records.

### 3. Wire Pipeline Hooks
ANTIRIPPER/scripts/pipeline_hooks_v2.py has V2PipelineHook class. Integrate into nsf_to_reaper.py and batch_nsf_all.py so claims/attempts tables start populating automatically.

### 4. Re-run Retry Batch for Remaining 40 Partial Games
The retry was interrupted at 5/45. With early-exit heuristic the stuck games finish fast now. Run:
```bash
# Same command as before — will pick up where it left off
python -u scripts/batch_nsf_all.py --force
```
Or target just partial games (see output/414update.md for the list).

### 5. Layer 3 Completion: Expansion MIDI Export
frames_to_channel_data() now returns VRC6/FDS channel data, but the MIDI builder only exports standard APU (ch 0-3). Need to add MIDI tracks on ch 5-11 per docs/MULTI_CHIP_SCHEMA.md Section 5.

### 6. Consolidate Duplicate Output Directories
Contra has 7 dirs, Castlevania has 9. Use oracle.get_game_inventory(slug) to identify best version, archive the rest. BESTOUTPUT/ already has the clean versions.

## Key Files
- CLAUDE.md — updated with actual scripts, oracle inventory
- extraction/frame_ir.py — chip-agnostic core (Layer 2)
- scripts/nsf_to_reaper.py — emulator with expansion capture + early-exit + skip-wav
- scripts/batch_nsf_all.py — improved batch with NSF header fallback + scaled timeouts
- ANTIRIPPER/agent_oracle.py — oracle with get_game_inventory()
- output/unsolved.md — analysis of 46 failing games
- output/414update.md — session stats + pipeline critique
- output/414audit.md — system files audit
- docs/MULTI_CHIP_SCHEMA.md — expansion schema design
```
