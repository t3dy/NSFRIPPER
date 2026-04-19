# Variant C — "Ditto Head"

The placeholder.  Today `outputv6_C/` is an identical copy of
`outputv6_B/` — same MIDI + JSFX setup, same sound.  What it's SLATED
to be is the one variant where what you hear live and what the stems
contain are bit-identical: stems rendered by the JSFX itself, offline,
via REAPER's ReaScript automation.

Location: `outputv6_C/<Game>/reaper/<song>.rpp` (identical to B
today; different after the render lands).

## Why it exists separately

We could have skipped it and just declared "when ReaScript lands,
variants will update in place."  Instead we pre-create the folder so
its eventual existence is signaled — the ear-test you do on B today
transfers to C tomorrow once the offline render runs.

## What C WILL be when finished

The ReaScript automation does this for each game:

1. Open the B variant in REAPER headlessly.
2. Render the project to one mixed WAV, or to per-channel stems
   (soloing each JSFX track in turn).
3. Save those WAVs into `outputv6_C/<Game>/stems/<song>/`.
4. Rewrite the C RPP to reference those WAVs as audio tracks
   (instead of referencing MIDI+JSFX).

The net result: Variant C looks EXACTLY like Variant A visually
(audio tracks playing pre-rendered stems), but the stems in C were
rendered by the JSFX plugin — not Python.  So hearing the C project
plays the same audio you'd hear during live playback of B.

## Why bother

Two reasons:

1. **Bit-identity.**  You can record a YouTube video of the JSFX
   playing live (B) and know the resulting audio will match what's
   in the stems (C) — useful for e.g. cutting a live recording into
   a playlist without surprises.

2. **Two performance profiles.**  B requires the JSFX to be resident
   on every track and running live — CPU-bound per REAPER instance.
   C is pre-rendered WAV audio — essentially zero CPU during
   playback.  If you want to load 20 game projects at once to mash
   them up, C is more efficient.

## What blocks C today

The REAPER automation.  Three options for implementing it:

1. **`reaper --renderproject` CLI flag** (if your REAPER version
   supports it).  Cleanest — ~50 lines of shell around a loop.
2. **ReaScript (Python inside REAPER)** running as a one-shot script
   that opens each B project, renders solo-per-track to WAV, writes
   the stems folder, generates a matching RPP.  ~200 lines of
   ReaScript.  Requires REAPER to be installed and the script to be
   launched by hand once.
3. **Batch via REAPER GUI** — open each project, hit render, script
   moves files.  Not automated but reliable.

Option 2 is the right answer for a polished product.  Option 3 is
what I'd do if you want 10 games' worth of C today and I'm the one
hand-driving REAPER.

## Current state

C folder exists with 10 games' placeholder RPPs, identical to B.
Once the main rebuild completes, the full 150-game C placeholder
will be there (re-runs automatically).

The offline render is NOT wired up yet.  If you open `outputv6_C/
Castlevania/reaper/02_Song_02.rpp` today, it plays as if it were B.

## When C would be the right final answer

- You've ear-tested B and confirmed JSFX is good enough for the
  product.
- You want mixed-in (pre-rendered) stems for efficiency or
  archival, but you want those stems to come from the JSFX, not
  Python (so they're "what the plugin produces").
- You'd rather not maintain two different DSP implementations
  (Python stems + JSFX).

In that case, we:
1. Delete the Python stems pipeline entirely.
2. Delete `outputv6/stems/` (the Python-rendered stems).
3. Implement the JSFX offline render.
4. Variant C becomes the archival path.
5. Variant A stops making sense (there's no Python stems to pair
   with JSFX) — we delete it too.

Final product is just B (live) + C (stems from B).  Simplest possible.

## When C is overkill

If after ear-testing you decide JSFX + stems together (Variant A)
is the best-sounding combination, there's no reason to build C.  The
Python stems ARE the archival path, the JSFX is the live path, and
they coexist because each is better at its own job.

## First game to try

Same as B — currently `outputv6_C/Balloon_Fight/reaper/01_Song_01.rpp`
sounds identical to the B version.  When C is wired up properly,
that same project will play JSFX-rendered stems instead.

The value of "test C now" is mostly ensuring the folder/project
structure works on your system.  The sound-quality evaluation
happens against B until the offline render lands.
