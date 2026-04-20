# Handover — 2026-04-19 PAL session

Copy the block below into a new Claude Code window at `C:\Dev\NSFRIPPER`.

---

## HANDOVER PROMPT

I'm continuing work on the NSFRIPPER project.  This session established
the Performance Abstraction Layer (PAL) — the design contract for how
NES hardware behavior compresses into live-keyboard-performable
controls, while keeping the archival stems path as a separate
authoritative fidelity path.

**Load these first**:

1. `docs/PERFORMANCE_ABSTRACTION_LAYER.md` — canonical design doc for the
   PAL.  Authoritative.
2. `keyboard_lab/docs/LIVE_CONTROL_MAPPINGS.md` — concrete keyboard ↔
   synth-behavior mapping.  Implementation guide for the JSFX
   performance interface.
3. `docs/JSFX_LIVE_PRIORITY.md` — the ranked list of JSFX code changes
   that realize PAL Class A + B.  Start with "Must-do now" items 1-3
   (~3.5 hours).
4. `keyboard_lab/db/README.md` — how to use the capability DB to track
   which approaches cover which PAL dimensions at which levels.
5. `docs/HANDOVER_2026_04_19_PAL.md` — this file.
6. `.claude/rules/architecture.md` Rules 34-38 — recent fixes (triangle
   gate-off, bandlimited pulse, NSF init, DPCM enable-gate, disk
   hygiene).
7. `MEMORY.md` — auto-loaded user preferences.  Note the contradiction
   with "stems_default" flagged in §Contradictions of the PAL doc.

## What got done this session

### Deliverable 1: canonical PAL design doc

`docs/PERFORMANCE_ABSTRACTION_LAYER.md`:
- Problem framing (information-theoretic limit, not DSP problem).
- Four control classes: A (direct live), B (macro/articulation),
  C (preset-only), D (non-performable).
- 17 NES hardware dimensions classified into these four classes.
- Connection to the existing SysEx > CC > ADSR priority cascade.
- Two contradictions in existing docs flagged and resolved:
  - Stems-primary vs JSFX-primary: both are primary, for different
    purposes.
  - Rule 31 non-linear-DAC claim: applies to multi-track JSFX, not
    to Full-APU-mode single-track JSFX.
- Four open hypotheses (HYP-PAL-1 through HYP-PAL-4) flagged for
  future ear-test.

### Deliverable 2: capability tracking in keyboard_lab DB

`keyboard_lab/db/extend_capabilities.py`:
- Adds `capabilities` table (17 PAL dimensions, seeded).
- Adds `approach_capabilities` table (per-approach coverage:
  exact / approximate / preset_only / unsupported).
- Seeds baseline coverage for the current JSFX Priority 3 ADSR
  approach (verified 2026-04-19).  Current baseline:
  - Class A: 2 exact, 3 approximate, 1 unsupported.
  - Class B: 0 covered, 5 unsupported (all awaiting implementation).
  - Class C: 4 preset_only (full coverage).
  - Class D: 2 unsupported (correctly — non-performable).

`keyboard_lab/db/README.md`: how to query.

### Deliverable 3: live control mappings

`keyboard_lab/docs/LIVE_CONTROL_MAPPINGS.md`:
- Target hardware profile (standard 49-88-key controller with mod
  wheel, pitch bend, aftertouch, sustain, 4 CC knobs, optional pads).
- Mapping table: velocity → volume + transient; mod wheel → duty;
  pitch bend → sweep proxy; aftertouch → vibrato depth + sustain
  press; sustain pedal → release extension.
- Four CC knobs: envelope length (CC74), Intensity macro (CC71),
  attack transient (CC73), arpeggio rate (CC75).
- Eight keyswitches (low-octave or pads): driver-family macros,
  drum kits, phase-reset burst, arpeggio toggle, emergency reset.
- Per-channel JSFX instance layout.
- Preset switching strategy (program-change between songs).
- Three open HYP-LCM hypotheses.

### Deliverable 4: JSFX priority list

`docs/JSFX_LIVE_PRIORITY.md`:
- **Must-do now** (3 items, ~3.5 hours): velocity → transient
  (30 min), CC1 → quantized duty (1 h), aftertouch → vibrato (2 h).
- **Should-do next** (4 items, ~15 hours): performance macro,
  arpeggio engine, stepped duty animation, phase-reset burst.
- **Later/optional** (4 items, ~1-2 days): keyswitch macro
  subsystem, sweep proxy, noise burst length, DMC samples.
- Non-goals explicitly declared (VST3 port, full DMC DAC live,
  ADSR overhaul).
- Each item has code location, effort estimate, and PAL dimension
  unlocked.

### Disk hygiene (related)

Rule 38 added to `architecture.md`: disk space is a hard constraint
after two C:-drive-full incidents this week.  `render_all_nsfs.py`
now has `preflight_disk_check()` that refuses to run if estimated
output > 50% of free space.  `--disk-override` to skip.  Rule 38
also documents cleanup commands for when it happens anyway.

## Core design decisions made this session

1. **The PAL is structural, not a new subsystem.**  It lives on
   top of the existing 3-priority input cascade.  Priority 3
   (keyboard) == PAL in effect.  Priority 1 (SysEx) bypasses
   PAL entirely.

2. **17 dimensions is the complete list**, not 30.  Compressed
   from `UNDERSTANDING_THE_CHIP.md`'s broader enumeration to just
   the live-play-relevant behaviors.

3. **Class D exists**.  We explicitly refuse to pretend we can
   reach every hardware behavior live.  Two dimensions (DMC DAC
   value, frame-accurate sequencing) are honestly non-performable.

4. **Stems path remains authoritative for fidelity**; PAL path
   is authoritative for live performance.  They serve different
   product goals.  No collapsing.

5. **CC71 "Intensity" macro is the single highest-leverage live
   control.**  One knob turns 4 behaviors up/down together in a
   preset-defined curve.

6. **The DB now tracks coverage per dimension per approach**.
   Enables objective comparison across plugins/techniques
   instead of "overall rating" only.

## Schema changes

keyboard_lab DB grew by 2 tables:

```sql
CREATE TABLE capabilities (
    id, code, name, pal_class, description
);
-- 17 rows, one per PAL dimension

CREATE TABLE approach_capabilities (
    approach_id, capability_id, coverage, notes, verified_date,
    PRIMARY KEY (approach_id, capability_id)
);
CHECK coverage IN ('exact', 'approximate', 'preset_only', 'unsupported')
```

See `keyboard_lab/db/extend_capabilities.py` for the full DDL and
seed data.

No changes to the ANTIRIPPER oracle DB this session.

## Files created this session

| File | Purpose |
|------|---------|
| `docs/PERFORMANCE_ABSTRACTION_LAYER.md` | Canonical PAL design |
| `docs/JSFX_LIVE_PRIORITY.md` | JSFX change roadmap |
| `docs/HANDOVER_2026_04_19_PAL.md` | This file |
| `keyboard_lab/db/extend_capabilities.py` | DB schema extension |
| `keyboard_lab/db/README.md` | DB usage guide |
| `keyboard_lab/docs/LIVE_CONTROL_MAPPINGS.md` | Performer interface spec |

## Files modified this session

| File | Change |
|------|--------|
| `.claude/rules/architecture.md` | Added Rule 38 (disk hygiene) |
| `scripts/render_all_nsfs.py` | Added `preflight_disk_check()` |

## The exact next coding task

**Implement JSFX Must-do #1**: wire velocity → attack transient
intensity.

Specifically, in `studio/jsfx/ReapNES_APU2_v2.jsfx`:

1. Find the `@block` or note-on handler near line 515.
2. Capture `vel = midi_buf[2]` on note_on.
3. Store `p1_vel_sx = vel / 127.0` (normalized velocity).
4. In the attack-enhancer block (where slider20 is applied), multiply
   the transient spike by `p1_vel_sx`.
5. Repeat for p2_vel_sx, tri_vel_sx (pulse2 and triangle channels).
6. Update DB: `UPDATE approach_capabilities SET coverage='exact',
   verified_date='YYYY-MM-DD' WHERE approach_id=(...) AND capability_id=
   (capability for 'attack_transient');`
7. Ear-test one song (Castlevania Vampire Killer is canonical).
8. If sounds right, commit.  If not, revert.

30 minutes of focused work.  Changes exactly one JSFX block.  First
step in the "Must-do now" tier.

## Status of background jobs

- **150-game rebuild**: crashed at ~115/150 on disk-full.  Cleanup
  done.  Can resume with `python scripts/render_all_nsfs.py --only
  <slug>` per game, but the rebuild is no longer the priority path
  — the product is now the live-play JSFX, which doesn't need
  stems.
- **Variant B regeneration**: running in background when this
  handover was written.  Produces MIDI+JSFX projects for each game
  without audio stems (no disk cost).  Should finish within an hour.
- **keyboard_lab DB extension**: already run and verified.  DB has
  the capability baseline.

## Current git state

At handover time, pushed commits:

- `9444fe08` — all session docs + keyboard_lab/
- `0f9775ce` — Rule 38 + disk preflight

Not yet committed at handover time:
- `docs/PERFORMANCE_ABSTRACTION_LAYER.md`
- `docs/JSFX_LIVE_PRIORITY.md`
- `docs/HANDOVER_2026_04_19_PAL.md`
- `keyboard_lab/db/extend_capabilities.py`
- `keyboard_lab/db/README.md`
- `keyboard_lab/docs/LIVE_CONTROL_MAPPINGS.md`
- `keyboard_lab/db/keyboard.db` (data change from extension)

Commit message draft:

    PAL: performance abstraction layer design + DB + controls + roadmap

    Design doc classifies 17 NES behaviors into 4 control classes
    (live / macro / preset / non-performable).  Extends keyboard_lab
    DB with capabilities + approach_capabilities tables seeded with
    the current JSFX baseline.  Live control mappings spec wires a
    standard MIDI controller to the PAL's Class A + B dimensions.
    JSFX priority list ranks ~10 hours of code work to realize the
    PAL in live play, starting with 3 Must-do items totalling 3.5
    hours.

    Files added:
      docs/PERFORMANCE_ABSTRACTION_LAYER.md
      docs/JSFX_LIVE_PRIORITY.md
      docs/HANDOVER_2026_04_19_PAL.md
      keyboard_lab/db/extend_capabilities.py
      keyboard_lab/db/README.md
      keyboard_lab/docs/LIVE_CONTROL_MAPPINGS.md

    Two contradictions in existing docs flagged and resolved in
    PERFORMANCE_ABSTRACTION_LAYER.md §Contradictions: stems-vs-JSFX
    primary designation, and Rule 31's non-linear-DAC claim scope.

## Do's and don'ts for next session

DO:
- Treat `PERFORMANCE_ABSTRACTION_LAYER.md` as authoritative.
- Update `approach_capabilities` rows as each JSFX change ships.
- Ear-test every change before committing.
- Keep archival stems path and live JSFX path distinct.

DO NOT:
- Merge stems pipeline and JSFX into one workflow.
- Implement Class D dimensions (DMC DAC live, frame-sequencing).
  Those are correctly non-performable.
- Rewrite the ADSR core.  Current is fine as baseline.
- Skip updating the DB when coverage changes.  The DB is how we
  keep track of what's real vs aspirational.

## First action in the new window

```bash
# 1. Commit this session's work
cd C:/Dev/NSFRIPPER
git add docs/PERFORMANCE_ABSTRACTION_LAYER.md \
        docs/JSFX_LIVE_PRIORITY.md \
        docs/HANDOVER_2026_04_19_PAL.md \
        keyboard_lab/db/extend_capabilities.py \
        keyboard_lab/db/README.md \
        keyboard_lab/docs/LIVE_CONTROL_MAPPINGS.md \
        keyboard_lab/db/keyboard.db
git commit -m "PAL: performance abstraction layer + DB + controls + roadmap"
git push

# 2. Read the handover in full
cat docs/HANDOVER_2026_04_19_PAL.md

# 3. Begin JSFX Must-do #1 per docs/JSFX_LIVE_PRIORITY.md
#    Wire velocity -> attack transient in ReapNES_APU2_v2.jsfx
```
