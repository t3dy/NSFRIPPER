# Pipeline Hooks

Automatic evidence and decision recording that fires during extraction.
Every song produces an evidence record. Every game produces a decision record.
Batch runs produce a summary record. All stored in `ANTIRIPPER/antiripper_v2.db`.

## Why This Exists

The ANTIRIPPER oracle DB was designed to capture extraction knowledge, but
the pipeline hooks were never wired in. Result: 47% of BESTOUTPUT games
had no decision records. The `attempts`, `claims`, and `evidence_items`
tables were mostly empty. Knowledge from extraction runs was lost.

Pipeline hooks close this gap automatically. No manual oracle calls needed
for routine extraction — the hooks fire on every run.

## What Gets Recorded

### Per-Song: Evidence Items

Every successful `process_song()` call in `nsf_to_reaper.py` records:

| Field | Value |
|-------|-------|
| `game_slug` | Game name from NSF title |
| `type` | `"nsf_midi_extraction"` |
| `source_path` | Path to the generated MIDI file |
| `metrics_json` | Note counts (per channel), CC counts, frame count, expansion chips |

This means every MIDI file in the library has a corresponding DB record
with its extraction metrics. Future sessions can query:
- How many notes per channel?
- What's the CC density?
- Did the game use expansion chips?
- When was it last extracted?

### Per-Game: Decision Records

Every game in `batch_nsf_all.py` records:

**On success:**

| Field | Value |
|-------|-------|
| `game_slug` | Game directory name |
| `decision_type` | `"extraction_route"` |
| `rationale` | `"45/45 tracks extracted via nsf_emulation_bankswitched"` |
| `outcome` | `"complete"` or `"partial"` |

**On failure:**

| Field | Value |
|-------|-------|
| `outcome` | `"failed"` |
| `rationale` | `"NSF extraction failed: process_game returned False"` |

This means every batch run populates decision records for all games.
The oracle's `explain_route_choice()` and `get_preflight_context()` will
return these records to future sessions.

### Per-Batch: Summary Evidence

One record at the end of each batch run:

| Field | Value |
|-------|-------|
| `game_slug` | `"_batch"` (sentinel) |
| `type` | `"batch_run_summary"` |
| `metrics_json` | `{ok_count, fail_count, ok_games, fail_games}` |

## Where the Hooks Fire

```
batch_nsf_all.py
  └── for each game:
        ├── process_game()
        │     └── nsf_to_reaper.py (subprocess)
        │           └── for each song:
        │                 ├── process_song()
        │                 └── hooks.on_song_extracted()  ← evidence
        ├── hooks.on_game_completed()  ← decision (success)
        └── hooks.on_game_failed()     ← decision (failure)
  └── hooks.on_batch_summary()         ← batch evidence
```

Note: `nsf_to_reaper.py` runs as a subprocess from `batch_nsf_all.py`.
The per-song hooks fire inside that subprocess. The per-game and batch
hooks fire in the parent process.

## Hook API

```python
from ANTIRIPPER.scripts.pipeline_hooks_v2 import PipelineHooks

hooks = PipelineHooks()  # uses ANTIRIPPER/antiripper_v2.db

# After extracting a song
hooks.on_song_extracted(
    game_slug="ninja_gaiden",
    song_num=1,
    midi_path="output/Ninja_Gaiden/midi/Ninja_Gaiden_01_Act_1_v1.mid",
    note_counts=[309, 280, 150, 45],  # P1, P2, Tri, Noise
    cc_counts=[1200, 1100, 150],       # P1, P2, Tri CC events
    frame_count=5400,
    expansion_chips=None,
)

# After a game completes extraction
hooks.on_game_completed(
    game_slug="Ninja_Gaiden",
    success_count=65,
    total_count=65,
    route="nsf_emulation",
    bankswitched=True,
    expansion_chips=None,
)

# After a game fails
hooks.on_game_failed(
    game_slug="Problem_Game",
    reason="PLAY hangs on all tracks (bankswitch failure?)",
)

# End of batch
hooks.on_batch_summary(
    ok_count=280,
    fail_count=17,
    ok_games=["Ninja_Gaiden", "Zelda", ...],
    fail_games=["Problem_Game", ...],
)
```

## Safety

- Hook failures never crash the pipeline. All methods catch exceptions
  and print a warning.
- If the DB file doesn't exist, hooks silently disable themselves.
- Hooks are append-only. They never modify or delete existing records.
- The hooks import is wrapped in try/except in both scripts — if the
  ANTIRIPPER module isn't available, extraction still works.

## How This Feeds the Oracle

The records created by pipeline hooks are directly queryable by the
oracle's `get_preflight_context()`:

```python
from ANTIRIPPER.agent_oracle import AgentOracle
oracle = AgentOracle()

# This now returns evidence from pipeline hooks
ctx = oracle.get_preflight_context("ninja_gaiden", "nsf_extraction")
# ctx["decisions"] includes the extraction_route record
# ctx["evidence"] includes per-song metrics
```

Future sessions get automatic context about what was tried, what worked,
and what the extraction metrics looked like — without anyone having to
manually call oracle methods.

## Manual Oracle Calls (Still Needed For)

Pipeline hooks handle routine extraction recording. But these still
require explicit oracle calls (see `docs/AGENT_ORACLE.md`):

| Situation | Oracle Call |
|-----------|-----------|
| Before risky code changes | `oracle.record_attempt()` |
| After discovering something important | `oracle.record_outcome()` with lessons |
| Proposing a hypothesis about a game | `oracle.propose_claim()` |
| Learning from past mistakes before work | `oracle.get_preflight_context()` |
| Checking what's already been tried | `oracle.list_recent_failures()` |

## Files

| File | Role |
|------|------|
| `ANTIRIPPER/scripts/pipeline_hooks_v2.py` | Hook implementation |
| `scripts/nsf_to_reaper.py` | Calls `on_song_extracted()` after each song |
| `scripts/batch_nsf_all.py` | Calls `on_game_completed/failed()` + `on_batch_summary()` |
| `ANTIRIPPER/antiripper_v2.db` | Target database |
| `docs/AGENT_ORACLE.md` | Oracle API (manual calls) |
| `ANTIRIPPER/ORACLE_API.md` | Oracle cheatsheet |
