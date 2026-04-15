# 414 Session Update + Pipeline Critique

## Current Numbers

| Metric | Value | Session Start | Delta |
|--------|-------|---------------|-------|
| Game directories | 850 | 850 | -- |
| Games with MIDI | 321 | 231 | **+90** |
| Total MIDI files | 8,951 | ~5,000 | **+3,951** |
| REAPER projects | 278 | 184 | +94 |
| Fully extracted (100%) | 249 | ~130 | **+119** |
| Partially extracted (<100%) | 47 | ~100 | improved |
| NSF-only (no MIDI) | 0 | 90 | **cleared** |
| Driver survey coverage | 181 | 181 | -- |
| ANTIRIPPER evidence items | 1,162 | -- | new |
| ANTIRIPPER decision records | 181 | -- | new |

## What Got Done (9 commits)

1. **Hiro Layer 1 complete** -- expansion audit found 35 games with expansion
   audio (30 FDS, 5 VRC6, 3 VRC7, 1 5B). Multi-chip Frame IR schema designed.
2. **Hiro Layer 2 complete** -- chip-agnostic `extraction/frame_ir.py` with
   fields for all 6 expansion chips + DPCM. 38 tests. Konami module re-exports.
3. **Hiro Layer 3 partial** -- emulator now captures expansion register writes
   (verified FDS + VRC6). Channel parsing for VRC6 + FDS added. MIDI export TBD.
4. **Batch extraction** -- 63 new games processed, 25 timed out, 45 now being
   retried with scaled timeouts (60s/track, max 3600s).
5. **ANTIRIPPER oracle rebuilt** -- preflight/attempt/outcome workflow, 24 tests,
   v2 DB with 16 hardware facts, 5 driver families, 14 prevention patterns.
6. **Token optimization** -- rules/ slimmed 50%, settings.local.json 96% reduction
   (33KB to 1.5KB).
7. **Bug fixes** -- control chars in NSF titles, NSF header fallback for batch.

## Background Tasks Still Running

- **45-game retry batch**: scaled timeouts, 1/45 complete so far
- **Driver survey refresh**: processing all 321 games (slow, I/O intensive)

---

## Pipeline Critique

### What's Working Well

**NSF emulation pipeline is solid.** The py65-based emulator correctly runs
NSF drivers and captures APU register writes. 249 games fully extracted with
zero manual intervention. The pipeline is deterministic and reproducible.

**Frame IR architecture is clean.** Three-layer separation (Observed -> Intent
-> Projection) is maintained. The new chip-agnostic module extends without
breaking existing code. 38 tests verify backward compatibility.

**Batch automation works.** batch_nsf_all.py processes the entire library
automatically. The improved version reads NSF headers for song counts and
scales timeouts appropriately.

### What's Not Working / Gaps

**1. Driver survey covers 181/321 games (56%)**

The driver survey was last run on the 181 games available at that time.
140 newly-extracted games have MIDI but no CC11/CC12 classification. This
means:
- No family assignment for new games
- Decision records only exist for the original 181
- The ANTIRIPPER oracle has blind spots for 140 games

**Fix:** Re-run `driver_survey.py --report --json` (already running in
background). Then re-run `ANTIRIPPER/scripts/ingest_all.py` to refresh the DB.

**2. ANTIRIPPER decision records lag evidence (181 vs 846)**

Evidence items cover 846 games (NSF + trace + metric records), but decision
records only cover 181. That means 665 games have evidence in the DB but
no extraction route recommendation. The oracle can't advise on these games.

**Fix:** ingest_all.py needs to generate decision records for all games with
evidence, not just the 181 from the survey. This requires the survey to run
first (dependency chain: extraction -> survey -> ingest -> decisions).

**3. Zero claims and zero attempts in the DB**

The claims and attempts tables are empty. These are the core of the oracle's
learning loop -- recording what was tried, what worked, what failed. Without
this data, the oracle has no project-specific learning. It can serve static
hardware facts and prevention patterns, but can't do "last time we tried X
on this game, it failed because Y."

**Fix:** Wire pipeline hooks into the extraction scripts. The V2PipelineHook
class exists at `ANTIRIPPER/scripts/pipeline_hooks_v2.py` but isn't integrated.

**4. Expansion audio captured but not exported**

The emulator now captures VRC6 and FDS register writes, and
`frames_to_channel_data()` parses them into per-frame state. But the MIDI
builder still only exports standard APU channels (0-3). Expansion channels
are captured, parsed, and then discarded at the MIDI export step.

**Fix:** Extend the MIDI builder to create tracks on channels 5-11 per the
MULTI_CHIP_SCHEMA.md. This is Layer 3 completion work.

**5. 47 games still partially extracted**

These timed out during the first batch because the timeout was flat 600s
regardless of game size. The retry batch (running now) has scaled timeouts.
But some games genuinely crash the py65 emulator -- the 6502 emulation hits
an infinite loop or illegal opcode and burns CPU forever.

**Fix needed:** Add an early-exit heuristic to the emulator. If N consecutive
frames produce identical APU state (all registers unchanged), the song has
ended or looped. Stop emulating instead of burning the full duration.

**6. py65 emulation is slow**

The main bottleneck is py65 -- a pure-Python 6502 emulator. Each frame runs
~30,000 CPU cycles of interpreted Python. For a 90-second song at 60fps,
that's 5,400 frames x 30,000 cycles = 162 million interpreted instructions.
A single game with 40 songs takes ~40 minutes.

This is the #1 reason batch extraction is slow. Alternative approaches:
- Use a C-based 6502 emulator (libgme, Mesen headless) via subprocess
- Use ctypes/cffi wrapper around a compiled 6502 core
- Pre-filter songs: skip silent tracks (NSF header song count includes SFX)

Not critical for correctness, but would turn a multi-hour batch into minutes.

**7. WAV rendering is wasted work for batch**

Every extracted song gets a WAV preview rendered via numpy synthesis. This
adds ~30% to extraction time per song. For batch production where the goal
is MIDI + REAPER, the WAV is unnecessary. The WAV render is useful for
quality-checking individual songs but wasteful at scale.

**Fix:** Add a `--skip-wav` flag to nsf_to_reaper.py and use it in batch mode.

### What Should Change Next (Priority Order)

1. **Run driver survey + re-ingest** -- closes the 140-game classification gap
2. **Wire pipeline hooks** -- starts populating claims/attempts tables
3. **Add early-exit heuristic** -- fixes most timeout failures
4. **Add --skip-wav flag** -- 30% batch speed improvement
5. **Layer 3 MIDI export for expansion** -- unlocks VRC6/FDS in REAPER projects
6. **Layer 4 validation infrastructure** -- cross_validate.py for trust scoring

### What's Efficient and Should Stay

- Frame IR as intermediate representation (never bypass it)
- Per-frame APU capture (lossless, matches hardware timing)
- Batch-first workflow (no LLM in the extraction loop)
- Version suffixes on all output files
- Driver family classification driving downstream decisions
- settings.local.json now lean (50 broad patterns vs 400 one-offs)

---

## DB Health Summary

| Table | Rows | Coverage | Status |
|-------|------|----------|--------|
| hardware_facts | 16 | Complete | Good -- tagged with subsystems |
| driver_families | 5 | Complete | Good -- matches CLAUDE.md spec |
| prevention_patterns | 14 | Complete | Good -- derived from MISTAKEBAKED.md |
| concept_bridges | 17 | Complete | Good |
| evidence_items | 1,162 | 846 games | Partial -- needs expansion data |
| decision_records | 181 | 181 games | **Gap: 665 games missing** |
| claims | 0 | None | **Empty -- hooks not wired** |
| attempts | 0 | None | **Empty -- hooks not wired** |

The DB is structurally sound but operationally incomplete. The static knowledge
(hardware facts, families, patterns) is solid. The dynamic knowledge (claims,
attempts, decisions for new games) hasn't started flowing yet because the
pipeline hooks aren't integrated.

---

## Session Commits

```
cdc1fe43 Update handover, Adventures_in_the_Magic_Kingdom retry complete
6e29d28a Batch complete: 321 games with MIDI (8936 tracks), Layer 3 expansion parsing
8273037a Session handover doc, Captain_Tsubasa_II 36/41 tracks
f8f835f6 Improve batch extractor: NSF header fallback, scaled timeouts
930af382 Update Hiro plan status, add Captain_Tsubasa_II + Cosmic_Wars extractions
d8955847 Layer 3: expansion audio capture, Cleopatra extraction, expansion logging
b02a7d90 Layer 2: chip-agnostic Frame IR, expansion fields for all 6 chips + DPCM
44a762e4 Batch extraction: ~150 new games, expanded Batman + Ghosts'n'Goblins tracks
057db2e1 Hiro Layer 1: expansion audit, multi-chip schema, ANTIRIPPER oracle rebuild
```
