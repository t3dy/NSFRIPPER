# Ear Lab — report card template

Fill in the blanks and paste back at me.  I'll know what to build
next.  The three core questions are at the end; everything before is
evidence-gathering.

---

## A. Per-game findings

For each game you listened to, one row.  Variant column is A / B / C
(or multiples if you compared).

| Game | Variant(s) | Sounds right? | Distinguishing issue |
|------|-----------|---------------|----------------------|
| Castlevania Vampire Killer | A vs B | _yes/no_ | _eg "JSFX triangle pops, stems clean" or "both sound good"_ |
| Battletoads pause theme | B | _yes/no_ | |
| Balloon_Fight opener | B | _yes/no_ | |
| (add rows as you test) | | | |

Key shorthand for "distinguishing issue":

- **pulse grit** — fuzzy / rough on high sustained pulses (Rule 35
  not in JSFX)
- **noise wash** — drums sound continuous instead of percussive
  (Rule 30 not in JSFX)
- **triangle pop** — vinyl clicks at bass note boundaries
  (should be gone in both)
- **too bright** — missing analog LP (Rule 33 not in JSFX)
- **off-key / wrong notes** — something broken, tell me exactly what
- **sounds identical** — A and B are indistinguishable (ideal)

## B. Live keyboard check

Opened `outputv6_B/<game>/reaper/<song>.rpp` with a MIDI keyboard
plugged in?  If yes:

- Did the JSFX respond to key presses?  ☐ yes  ☐ no
- Was there noticeable latency?  ☐ imperceptible  ☐ slight  ☐ bad
- Did changing the "Channel Mode" slider work live?  ☐ yes  ☐ no
- Could you layer your keyboard over playing MIDI and hear both?
  ☐ yes  ☐ no
- Would you feel comfortable recording a performance through this?
  ☐ yes  ☐ no

If yes to all or most, the live-keyboard path is real.  If no to most,
there's a wiring or REAPER-config issue worth debugging.

## C. Video-recording fitness

One of the product goals is video recording (knobs animating, scope
flickering, etc. per docs/SYNTHMERGE.md).  Open any B variant:

- Are the JSFX slider animations visible / useful?  ☐ yes  ☐ no
  ☐ can't tell — UI stale
- Does the JSFX's UI match what you'd want on screen for a video?
  ☐ yes  ☐ close  ☐ no — needs work
- What would you want ADDED to the JSFX UI for video recording?
  (your free answer)

## D. Per-variant verdict

After listening to at least 3 games in each of A, B, C:

### Variant A — "Double Dose" (stems + JSFX)
- Would you ship this?  ☐ yes  ☐ no  ☐ only for some games
- Best thing about it: _________
- Worst thing about it: _________

### Variant B — "Live Wire" (pure JSFX)
- Would you ship this?  ☐ yes  ☐ no  ☐ only for some games
- Best thing about it: _________
- Worst thing about it: _________

### Variant C — "Ditto Head" (currently stub = B)
- When fully wired, would you ship this?  ☐ yes  ☐ no  ☐ unsure
- Is bit-identity stems-vs-live important to you?  ☐ yes  ☐ no

## E. The three decisions that drive everything else

Answer these three and I know what to do next.

### E.1 — Is JSFX-alone (Variant B) acceptable for your primary product?

☐ **Yes, B is enough.**  I'll kill Python stems, delete A and C, ship
the JSFX.  Simplest possible product.

☐ **No, I need the Python stems quality.**  A is my archival path; B
is my live path.  Keep both.

☐ **Almost — B needs one more thing.**  Tell me what:
  ☐ Bandlimited pulse (Rule 35 port)
  ☐ Noise gate (Rule 30 port)
  ☐ Analog LP + DC blocker (Rule 33 port)
  ☐ Something else: _________

### E.2 — Do you want Variant C (JSFX-rendered stems)?

☐ **Yes, build the ReaScript offline render.**  I'll wire it up so C
becomes bit-identical to live JSFX output.  Estimate 1-2 days.

☐ **No.  A and B cover everything I need.**  C stays as a folder
placeholder indefinitely or we delete it.

☐ **Only if you also do E.1's "almost" item.**

### E.3 — What's the biggest remaining audio issue you want fixed?

In priority order, tell me 1-3 things:

1. _________
2. _________
3. _________

---

## Paste-back template

When you're ready, copy the lines between the `=====` below into
chat.  I'll parse it:

```
=====
EAR LAB REPORT

Games tested: <N>
B acceptable alone: YES / NO / ALMOST
Port request: NONE / RULE_35 / RULE_30 / RULE_33 / OTHER=<...>
C wanted: YES / NO
Top priority issue: <one line>

Notes:
<freeform text>
=====
```

That single paste is enough to drive the next 2-5 days of work.
