# 414 System Files Audit

## What Was Checked

All files that load into context every session: CLAUDE.md, .claude/rules/*.md,
docs/MISTAKEBAKED.md, docs/VALIDATION_REFERENCE.md. These files consume tokens
on every conversation start, so stale content is a direct tax on productivity.

## Critical Issues Found + Fixed

### 1. `kitchen_sink.py` phantom (FIXED)

**Problem:** CLAUDE.md Key Commands, session_protocol.md Working Order (step 6),
and VALIDATION_REFERENCE.md Delivery Gate all referenced `kitchen_sink.py` — a
script that was designed in early sessions but never implemented. Every session,
Claude read these references and might try to use a non-existent script.

**Fix:** Replaced all references with actual scripts: `nsf_to_reaper.py`,
`batch_nsf_all.py`, `driver_survey.py`. Added oracle inventory to key commands.
Session protocol now points to oracle inventory as step 6 ("check what's been
tried before touching the game").

### 2. Architecture rule count wrong (FIXED)

**Problem:** CLAUDE.md claimed "22 architectural rules" but architecture.md
only has 15 (rules 1-12, 17-18, 22). Rules 13-16 and 19-21 were moved to
`docs/ARCHITECTURE_REFERENCE.md` during token optimization but the count
wasn't updated.

**Fix:** Updated to reference both files with accurate description.

### 3. Key Commands section outdated (FIXED)

**Problem:** Key Commands showed kitchen_sink.py as PRIMARY with all actual
scripts labeled "Legacy." The actual primary workflow (batch_nsf_all.py +
nsf_to_reaper.py) was second-class.

**Fix:** Reorganized into clear sections: BATCH, SINGLE GAME, TRACE PIPELINE,
REAPER, VALIDATION + CLASSIFICATION, ORACLE, SITE. All scripts verified to exist.

## Issues Found But Not Fixed (Low Priority)

### synth_fidelity.md references future unified synth

References `ReapNES_Studio.jsfx` which doesn't exist yet. Current plugin is
`ReapNES_Console.jsfx`. This is aspirational (the merge is planned), so it's
flagged but left as-is. The `reaper_projects.md` rules file already says
"Until the merge is complete, use ReapNES_Console.jsfx."

### reaper_projects.md references missing template

References `Console_Test.rpp` as a "known-good" template but the file wasn't
found. The RPP structure documentation in the file is still accurate and
valuable for generate_project.py development.

### docs/KITCHENSINKAUDIT.md still exists

A 260-line design doc for the never-built kitchen_sink.py. Not loaded into
context (not in rules/), so it's not wasting tokens. Could be archived.

## What's Clean and Should Stay

| File | Status | Notes |
|------|--------|-------|
| architecture.md | Good | 15 core rules, concise after token optimization |
| session_protocol.md | Good (just fixed) | Working order is accurate now |
| synth_fidelity.md | Good | Detailed CC/ADSR spec, valuable for synth work |
| jsfx_deploy.md | Good | sync_jsfx.py and session_startup_check.py both exist |
| debugging-protocol.md | Good | 5-step order still relevant |
| new-game-parser.md | Good | 13-step checklist well-integrated |
| output-versioning.md | Good | v1/v2 pattern observed in practice |
| MISTAKEBAKED.md | Good | 8 incident-based rules all still valid |

## Token Budget After Fixes

| Source | Before | After | Change |
|--------|--------|-------|--------|
| .claude/rules/*.md | ~4800 | ~4800 | -- (content fixes, not reduction) |
| settings.local.json | ~13000 | ~500 | -96% (earlier this session) |
| CLAUDE.md | ~3200 | ~3200 | -- (content fixes, not reduction) |
| MISTAKEBAKED.md | ~1200 | ~1200 | -- |
| **Total context tax** | **~22200** | **~9700** | **-56%** |

The settings.local.json reduction from earlier this session was the biggest win.
The content fixes ensure the remaining tokens carry accurate information.
