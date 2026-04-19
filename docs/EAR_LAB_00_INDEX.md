# Ear Lab — index

You are the arbiter of what "sounds right" for 150 NES games across
seven driver families.  Three output variants now sit side-by-side:

```
outputv6/          canonical stems + MIDI + RPP (archival, what you had)
outputv6_A/        "Double Dose"   — stems + MIDI+JSFX together
outputv6_B/        "Live Wire"     — MIDI+JSFX only, no stems
outputv6_C/        "Ditto Head"    — placeholder for JSFX-rendered stems
```

Each game has the same songs available in each variant, so you can pop
the same `01_Song_01.rpp` open from three different folders and hear
three different architectures.

## Read first

1. **docs/EAR_LAB_00_INDEX.md** — this file.  Start here.
2. **docs/SYNTH_VS_SCRIPTS.md** — why the three variants exist at all.
3. **docs/NAMING_POLICY.md** — the deterministic rules behind filenames
   and sidecars, so you can trust what you're looking at.

## Per-variant deep dives

- **docs/EAR_LAB_A_DOUBLE_DOSE.md** — Variant A is both archival stems
  AND live JSFX, playing together by default.  Richest to compare with;
  lets you solo either path without leaving the project.
- **docs/EAR_LAB_B_LIVE_WIRE.md** — Variant B is the actual "playable
  synth" product.  Pure JSFX.  MIDI keyboard plugs in and works.
  This is the variant to keep if JSFX-only is good enough for you.
- **docs/EAR_LAB_C_DITTO_HEAD.md** — Variant C is a placeholder today
  but describes the offline-render path that would make stems and
  live audio bit-identical.

## Testing workflow

- **docs/EAR_LAB_FAMILY_TOUR.md** — 14 games, one per driver family,
  picked so you can hear each family's quirks through all three
  variants in about 45 minutes.
- **docs/EAR_LAB_REPORT_CARD.md** — fill-in-the-blanks for your
  findings.  Paste it back at me and I'll know what to port next.

## What the three variants decide

You have one big architectural question to answer by ear:

> Is JSFX-only (Variant B) good enough to be the product, or do you
> need the Python-stems quality (baked into Variant A, planned for
> Variant C)?

If you answer **"B is good enough"** → we simplify to one path, kill
the Python rendering pipeline, cut everything but the JSFX.  Simplest
product.  Ships fastest.

If you answer **"A or C is what I need"** → we keep Python stems as
the authoritative sound AND do the work to either (C) offline-render
JSFX to WAV so they match, or (A) keep the hybrid.  More plumbing,
better audio.

There is no wrong answer.  I can make either work.

## Current JSFX vs stems fidelity status

| Rule | Python stems | JSFX | Notes |
|------|--------------|------|-------|
| 27 non-linear mix | ✓ | ✓ | Both have it |
| 30 noise $4015 gate | ✓ | ✗ | JSFX intentionally uses vol-only gate |
| 33 14 kHz LP + DC block | ✓ | ✗ | JSFX optimized for libgme parity, not DAW listening |
| 34 triangle gate-off DAC hold | ✓ | ✓ (just ported) | No more triangle vinyl pops anywhere |
| 35 bandlimited pulse | ✓ | ✗ | Pulse grit more audible in JSFX at high pitch |

JSFX will sound SHARPER / BUZZIER than stems until Rule 35 ports.
That's the primary tell when A/B-comparing: if pulse-heavy tracks
(Mega Man, DuckTales lead) sound gritty in Variant B but smooth in
Variant A's stems tracks, that's the Rule 35 gap talking.

## Clever-name rosetta

| Variant | Clever name | Architecture |
|---------|-------------|--------------|
| A | "Double Dose" | Both paths active at once — you hear layered Python stems and live JSFX. |
| B | "Live Wire" | Just the JSFX plugin.  Fully live, MIDI-keyboard ready. |
| C | "Ditto Head" | Slated to copy B's output offline so stems and live are bit-identical.  Not yet wired. |

The archive vs performer vs clone metaphor — all three can coexist
on disk, and the ear-test is you deciding which serves your purpose.
