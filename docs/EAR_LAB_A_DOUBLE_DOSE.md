# Variant A — "Double Dose"

Both audio paths playing together at once.  The REAPER project has 8-9
tracks: 4-5 audio stems (Python pipeline, archival-quality rendering)
on top, and 4 MIDI-with-JSFX tracks underneath.  By default both
groups play.  You hear the mix of stems AND live JSFX.

Location: `outputv6_A/<Game>/reaper/<song>.rpp`

## Why it exists

Before you commit to one path or the other, Variant A lets you A/B
them in the same REAPER window without opening two files.  Mute the
audio tracks → hear pure JSFX.  Mute the MIDI tracks → hear pure
stems.  Soloing tracks lets you isolate a single NES channel's two
renderings side by side.

## Track layout

Top to bottom in REAPER's track panel:

```
[AUDIO]  NES - Pulse 1          <-- Python stem (archival)
[JSFX]   NES - Pulse 1          <-- MIDI + JSFX (live-playable)
[AUDIO]  NES - Pulse 2
[JSFX]   NES - Pulse 2
[AUDIO]  NES - Triangle
[JSFX]   NES - Triangle
[AUDIO]  NES - Noise
[JSFX]   NES - Noise
[AUDIO]  NES - DMC              (only present if the game uses DMC)
```

## Quick recipe for A/B isolation

1. Open any A variant.  Hit play.
2. You should hear both paths.  They will interfere slightly because
   they are NOT time-aligned at sample level — the JSFX has its own
   latency through REAPER's MIDI engine, the stems start at bar 1
   exactly.  That's expected.

3. To hear **Python stems alone**: select tracks 2, 4, 6, 8 (the
   JSFX ones — every other one) and mute them.  Now you're hearing
   the archival pipeline.

4. To hear **JSFX alone**: select tracks 1, 3, 5, 7 (the AUDIO stems)
   and mute them.  Now it's a pure live synth.

5. To isolate one channel's two renderings: solo tracks 1+2 (Pulse 1
   stem + Pulse 1 JSFX).  You'll hear both renderings of that channel
   only.  Good for pulse-grit comparison.

## What to listen for

### Pulse channels (tracks 1-4)

Stems track has the bandlimited pulse from Rule 35 (smoother,
especially at high pitch) AND the 4-pole LP at 14 kHz (Rule 33).  The
JSFX track has neither.  Expect JSFX to sound grittier on anything
with fast-changing or high-pitched pulses.

Good games to hear this on:
- Mega Man 1-4 (any) — dense pulse leads
- Castlevania 2 Simon's Quest — lots of middle-high pulse
- Little Mermaid — Mermaid Theme, bright pulses
- Gimmick! — Tim Follin's shredding pulse leads

If stems sound distinctly smoother, that's Rule 35 doing its job.
JSFX would need polyBLEP to match — a few hours of work.

### Triangle channel (tracks 5-6)

Both now have Rule 34 (gate-off DAC hold) — no more vinyl pops
from triangle staccato bass.  If you hear a pop in either, that's a
bug that slipped through.

Good games for triangle:
- Battletoads — fast triangle bass, rapid gating
- Castlevania — Vampire Killer bassline
- Dragon Warrior — overworld triangle drone

### Noise channel (tracks 7-8)

Stems use the `$4015` bit-3 gate (Rule 30) AND the hardware length
counter (Rule 32).  JSFX gates on vol > 0 only.  For most games
(Capcom, Konami) both sound correct because those drivers use vol=0
to silence noise.  But for Nintendo/Rare/late-Capcom games, the
Python stems silence drum hits more crisply while JSFX can sound
like a continuous "wash."

Listen here:
- Super Mario Bros Overworld — drum hits vs wash is very audible
- Metroid Brinstar — length-counter-based noise
- Kirby's Adventure — same pattern

### DMC channel (track 9, when present)

Both renderings use the same two-mechanism DMC handling (Rule 28
DPCM trigger vs DAC write).  Should sound the same in both.  If they
don't, it's a fidelity bug worth investigating.

Good DMC test cases:
- Super Mario Bros — drum samples
- Journey to Silius — bass via DMC DAC
- Gremlins 2 — voice samples
- Battletoads — algorithmic DMC bass

## When to prefer A

- You're doing critical listening and want to hear exactly how
  stems and JSFX diverge on this specific game.
- You want both options available in one project file without
  managing two folders.
- You'll ultimately mix the stems (authentic) for final audio and
  use JSFX (live) for video recording with animated knobs.

## When NOT to prefer A

- You want to play a MIDI keyboard live and just hear one clean
  synth.  Use B.  The stems in A are static — they'll keep playing
  while your keyboard input layers on top, making a muddy hybrid.
- You want minimum disk footprint.  Each A project references 5
  x 15 MB stems plus MIDI.  B is much smaller.

## First game to try

`outputv6_A/Castlevania/reaper/02_Song_02.rpp` (Vampire Killer).

- Stems track row: hear the Python-clean version.
- JSFX track row: hear the live synth.
- Compare pulse leads (Simon's theme) for grit.  Compare triangle
  bass for pop absence.  Compare noise drums for tightness.
