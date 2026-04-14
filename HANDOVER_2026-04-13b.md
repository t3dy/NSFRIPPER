# Session Handover — 2026-04-13 (Session B)

## What This Session Accomplished

### 1. Fixed 4 extraction bugs
- **M3U escaped comma parsing**: `\,` in track names caused backslashes in filenames, breaking `mid.save()`. Fixed with null-byte placeholder round-trip.
- **UTF-8/cp1252 encoding**: Windows console choked on non-ASCII NSF metadata. Added `sys.stdout.reconfigure(encoding='utf-8')` to both scripts.
- **MIDI latin-1 encoding**: `mido` library requires latin-1 for meta fields. Added `_midi_safe()` sanitizer.
- **Null byte in filenames**: Dead Zone NSF title contains `\x00`. Added to forbidden char set.

### 2. Built extraction infrastructure
- **`--publisher` flag** on `fetch_and_extract.py` — filter by publisher name in joshw index
- **`collection_state.py`** — control plane scanning 1980 games with extraction status, driver family, publisher, cost estimates, MIDI validity checks
- **`extract_scheduler.py`** — smart scheduler with dynamic timeouts (base + per-song), cost estimation, track-level checkpointing, driver-family-aware prioritization
- **`--names-json`** flag on `nsf_to_reaper.py` — JSON track name transport, eliminates comma delimiter collision
- **Subprocess timeout**: 600s → 3600s (games with 100+ songs need 30+ minutes)

### 3. Ran publisher batch extractions
Went from **25 → 157+ games with MIDI output** (batches still running):

| Publisher | Status | Notes |
|-----------|--------|-------|
| Capcom | 44/50 success, retrying 6 timeouts | Darkwing Duck (64 songs), Mighty Final Fight (54), Sweet Home (72) all extracted |
| Sunsoft | 42/48 success, retrying 6 errors | Batman (11), Fantasy Zone (29+54), Fester's Quest (9) all extracted |
| Konami | ~4 done, 117 total, STILL RUNNING | bgw39emif — Boku Dracula-kun (138 songs) blocking |
| Rare | ~6 done, 38 total, STILL RUNNING | b04picm35 — Battletoads&DD 404'd (URL encoding) |
| Tecmo | STILL RUNNING | bhzxd23mq |
| Square | STILL RUNNING | bzkciz77j |
| Natsume | ~3 done, STILL RUNNING | bp84ekmnr |
| Capcom retry | ~13 done, STILL RUNNING | busguxehp — re-running with 3600s timeout |
| Sunsoft retry | ~3 done, STILL RUNNING | b3drd076x — re-running with fixes |

### 4. User added architecture rules 18-22
While I worked on extraction, the user added:
- **Rule 18**: Driver family is first-class infrastructure
- **Rule 19**: Three validation axes (Mesen/VGM/NES-MDB)
- **Rule 20**: Non-linear APU mixing formulas
- **Rule 21**: Non-note sound events ($4011 DAC, sweep, noise mode)
- **Rule 22**: Period-to-note canonical formula

Plus synth fidelity rules 7-9 (non-linear mixing, driver presets, noise period inversion).

## Pending / In-Flight

### 1. Background batches STILL RUNNING
7 background tasks were started and may or may not have finished by the time you read this. Check if they completed:
```bash
# Quick check — count MIDI folders
ls -d output/*/midi/ | wc -l
# Detailed status
python scripts/collection_state.py --save --summary
```

### 2. Re-run driver survey (CRITICAL)
The survey only covers 65 games. With 157+ now extracted, re-running will:
- Classify all new games into the 5 driver families
- Validate whether Capcom/Konami/Sunsoft patterns hold across the full catalog
- Update `data/driver_survey.json` and `docs/DRIVER_SURVEY.md`
```bash
python scripts/driver_survey.py --report --json
```

### 3. Known failures to investigate
- **Battletoads & Double Dragon**: 404 from joshw.info (URL has `&amp;` encoding issue)
- **Dead Zone**: null byte in NSF title (fixed in code, needs re-extraction)
- **Gimmick!**: 106 songs, timed out even at 600s. Now has 3600s timeout.
- **Several Capcom/Sunsoft games**: timed out at 600s, should succeed with 3600s

### 4. Collection state vs batch output mismatch
`collection_state.py` slug generation doesn't match all batch output folder names. Some games extracted successfully but aren't counted as "complete" because the slug differs. Need to improve slug matching or use the actual output folder scan.

### 5. User's structural request (partially addressed)
User asked for a scheduler layer, metadata normalization, and corpus system thinking. Built `collection_state.py` + `extract_scheduler.py` but these are v1. User specifically wants:
- **Driver-family batches** (not just publisher batches) — the scheduler supports `--family` flag but hasn't been used yet
- **Completion criteria beyond "MIDIs exist"** — validity checks added but fidelity checks need the driver survey
- **State table** as the control plane — built but slug matching needs refinement

## Key Files Created/Modified This Session

| File | Purpose |
|------|---------|
| `scripts/collection_state.py` | Control plane: status of all 1980 games |
| `scripts/extract_scheduler.py` | Smart scheduler with dynamic timeouts |
| `data/collection_state.json` | Serialized collection state |
| `scripts/fetch_and_extract.py` | Bug fixes + --publisher flag |
| `scripts/nsf_to_reaper.py` | Bug fixes + --names-json flag |
| `.claude/rules/architecture.md` | Rules 18-22 added by user |
| `.claude/rules/synth_fidelity.md` | Rules 7-9 added by user |
| `.claude/rules/session_protocol.md` | Driver family step added by user |

## Git Log This Session

```
97bde6e Update infrastructure: rules 18-22, collection state refresh
dd98706 Add collection state control plane and smart extraction scheduler
8fe7f1b Fix null byte in filenames, increase timeout to 3600s
ab1cd5c Fix M3U comma parsing, UTF-8 encoding, MIDI latin-1 bugs + --publisher flag
```
