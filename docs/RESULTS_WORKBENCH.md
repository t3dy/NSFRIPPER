# Results — the workbench is built

Summary of what was produced in response to the prompt:

> "remember that my main problem I want to solve extracting game synth
> sounds is I want to play with them using a midi keyboard create a
> subfolder with a special database for working on this problem"

## What was delivered

A new dedicated subfolder: `keyboard_lab/`

```
keyboard_lab/
├── approaches/       One dir per approach we evaluate (future artifacts)
├── db/               SQLite DB + init script (built this turn)
│   ├── init_keyboard_db.py
│   └── keyboard.db   (produced when init script runs)
├── docs/             Per-topic deep dives (first one shipped)
│   └── THE_LIVE_PERFORMANCE_PROBLEM.md
├── evaluations/      Ear-test notes (one file per session)
└── projects/         REAPER projects set up per-approach per-game
```

## The database (keyboard_lab/db/keyboard.db)

Six tables, purpose-built for the live-play problem (not reused from
the existing ANTIRIPPER oracle DB because the use case is different
and mixing would muddy both).

| Table | What it tracks |
|-------|----------------|
| `approaches` | Which synth/plugin/hardware we're evaluating.  10 seeded rows. |
| `presets` | Per-approach per-driver-family slider calibrations. |
| `game_refs` | Canonical reference games with character notes. 10 seeded. |
| `keyboards` | Physical MIDI keyboards tested (latency/CC-knob count matters). |
| `experiments` | A single ear-test session tying approach × preset × keyboard × game. |
| `findings` | Structured observations tagged by dimension (latency, accuracy, playability). |

Seeded with 10 approaches and 10 reference games across driver
families (Rare, Konami, Capcom early/late, Nintendo, Sunsoft,
Square, Tecmo).

## How to use it

```
cd keyboard_lab/db
python init_keyboard_db.py     # one-time setup
sqlite3 keyboard.db             # interactive queries
# or python + sqlite3 for programmatic use
```

Future per-experiment flow:
1. Pick an approach row (or insert new one).
2. Pick a game_refs row.
3. Set up a REAPER project in `keyboard_lab/projects/<approach>/<game>/`.
4. Play MIDI keyboard through the approach; take notes.
5. Insert an experiments row with overall rating + notes.
6. Insert one findings row per dimension you rated.
7. Next time you run `audit`, the DB will tell you which approaches
   cover which driver families.

## Scope choice

I deliberately kept this database **separate from the ANTIRIPPER
oracle DB**.  Reason: ANTIRIPPER is for extraction fidelity and
driver-family classification; keyboard_lab is for live-play
evaluation.  They share game names but the axes of interest are
different.  Joining later is a `JOIN` across two databases on the
game slug — cheap — whereas un-mixing later is expensive.

## What this doesn't have yet

- No experiments are recorded.  That happens when you do real
  ear-tests and paste findings into the DB.
- No REAPER project templates in `projects/` yet.  Those get built
  per-approach as we work through Tier 1 of `docs/APPROACHES_PLAN.md`.
- No audit/report tool yet.  Easy to add once the first ~5
  experiments are in (we'll know what queries are useful).

## First two docs shipped in this lab

1. `keyboard_lab/docs/THE_LIVE_PERFORMANCE_PROBLEM.md` — the full
   analysis of why ROM-to-live-MIDI-keyboard is lossy and how our
   JSFX synth partitions the problem.  Answers the core design
   question.
2. This summary (`docs/RESULTS_WORKBENCH.md`) — what the folder
   contains and how to use it.

## Next

Load the DB with your actual MIDI keyboard as a `keyboards` row,
pick one approach from `APPROACHES_PLAN.md` Tier 1, and run the
first experiment.  One hour, one row per table added, one clear
verdict.
