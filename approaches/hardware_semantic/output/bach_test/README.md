# Bach through the W&W Title synth instruments

Each Bach MIDI is delivered as **two REAPER projects**:

- `<slug>_ww_cc.rpp` -- **priority-2 mode** (CC11 envelope injected per note).
  Closest to the W&W Title tone: sharp attack at peak 120, linear
  software decay by 4 CC11 units per frame, floor at 8.  Every held
  note continues decaying, which is where the *plinkiness* comes from.
- `<slug>_adsr.rpp` -- **priority-3 mode** (ADSR-only, no CC automation).
  Smoother / more organ-like because ADSR sustain=8 holds after decay.
  Useful for comparison; closer to how a MIDI keyboard through the plugin
  would sound.

Both projects have identical track setup + JSFX slider settings; the only
difference is the MIDI file loaded.  Same rendering chain, same instruments --
the tone difference is entirely the priority-2 CC envelope vs priority-3 ADSR.

## W&W Title instrument profiles

| NES voice | Duty | ADSR (atk/dec/sus/rel) | Role in the Title |
|---|---|---|---|
| **Pulse 1 (lead)**    | 25% | 0 / 100 ms / 8 / 60 ms | Main melody |
| **Pulse 2 (harmony)** | 25% | 0 / 100 ms / 8 / 60 ms | Countermelody |
| **Triangle (bass)**   | n/a | 0 ms attack, 40 ms release | Bassline (gate-only) |

ADSR numbers are derived from the CBG analysis of
`approaches/hardware_semantic/output/ww_test/01_title/midi/01_title_cbg.mid`
(pulse channels write duty 25% for ~100% of the song; CC11 ranges 8..120).

## What the `_ww_cc.mid` pipeline does to each voice

**Pulse 1 / Pulse 2 (lead + harmony):** inject a per-frame CC11
decay envelope onto every note.  Starts at 120 on note_on, drops
4 CC11 units per 60 Hz frame, floors at 8.  The JSFX plugin runs
in priority-2 mode (CC-driven volume) and ignores ADSR.  Held
notes decay toward silence instead of plateauing at sustain=8,
which is where the *plinky* character comes from.

```
Frame 0:  note_on vel=120        (NES vol 15 -- attack)
Frame 1:  CC11=116
Frame 2:  CC11=112
...
Frame N:  CC11=max(8, 120 - 4*N)
```

Slope matches the W&W Title driver (~8 CC units per 2 frames,
CC11 range 8..120 observed in the game MIDI).

**Triangle (bass):** truncate any note longer than ~180 ms.  The
plugin does NOT gate triangle on CC11 mid-note (triangle has no
HW volume, so the CC path only flips CC-mode on/off).  In the real
game, each triangle note rings for ~100-200 ms then the hardware
linear counter decays to zero.  Without truncation, Bach bass
notes (half / whole notes at 500 ms+) play their full length and
the result sounds droning, not plinky.  Truncation mimics the
linear counter decay while letting Bach's note timing drive the
retriggers.

Short notes (< 180 ms) pass through unchanged -- e.g., fugue1
had 8 notes already under the cap and 136 that got truncated;
the natural staccato character of Bach fugue bass lines is preserved.

## Pieces

### invent1_C_major

Two-Part Invention No.1 in C (BWV 772), 2 voices (pulse1 + pulse2).

- Instruments: **Pulse 1 (lead), Pulse 2 (harmony)**
- CC events injected: 6522 across 471 pulse notes
- Priority-2 (plinky): [invent1_C_major_ww_cc.rpp](invent1_C_major/reaper/invent1_C_major_ww_cc.rpp)
- Priority-3 (ADSR):   [invent1_C_major_adsr.rpp](invent1_C_major/reaper/invent1_C_major_adsr.rpp)

### invent4_D_minor

Two-Part Invention No.4 in D minor (BWV 775), 2 voices.

- Instruments: **Pulse 1 (lead), Pulse 2 (harmony)**
- CC events injected: 4962 across 543 pulse notes
- Priority-2 (plinky): [invent4_D_minor_ww_cc.rpp](invent4_D_minor/reaper/invent4_D_minor_ww_cc.rpp)
- Priority-3 (ADSR):   [invent4_D_minor_adsr.rpp](invent4_D_minor/reaper/invent4_D_minor_adsr.rpp)

### fugue1_C_major

WTC Book 1, Fugue No.1 in C major (BWV 846), 3 voices (pulse1 + pulse2 + triangle).

- Instruments: **Pulse 1 (lead), Pulse 2 (harmony), Triangle (bass)**
- CC events injected: 15286 across 605 pulse notes
- Priority-2 (plinky): [fugue1_C_major_ww_cc.rpp](fugue1_C_major/reaper/fugue1_C_major_ww_cc.rpp)
- Priority-3 (ADSR):   [fugue1_C_major_adsr.rpp](fugue1_C_major/reaper/fugue1_C_major_adsr.rpp)

### fugue2_C_minor

WTC Book 1, Fugue No.2 in C minor (BWV 847), 3 voices.

- Instruments: **Pulse 1 (lead), Pulse 2 (harmony), Triangle (bass)**
- CC events injected: 12535 across 518 pulse notes
- Priority-2 (plinky): [fugue2_C_minor_ww_cc.rpp](fugue2_C_minor/reaper/fugue2_C_minor_ww_cc.rpp)
- Priority-3 (ADSR):   [fugue2_C_minor_adsr.rpp](fugue2_C_minor/reaper/fugue2_C_minor_adsr.rpp)

## Mixer labels

Track names in REAPER:

- `W&W Title Pulse 1 (lead, 25% duty)`
- `W&W Title Pulse 2 (harmony, 25% duty)`
- `W&W Title Triangle (bass)`

## Tweaking the envelope

If the `_ww_cc` version decays too fast or too slow for your ear:

- Edit `approaches/hardware_semantic/projection/ww_envelope.py`:
    - `CC_DECAY_PER_FRAME = 4` -- drop to 2 for slower/longer tail,
      raise to 6-8 for snappier plink.
    - `CC_DECAY_FLOOR = 8` -- lower to 4 or 2 for deeper fade-out,
      raise to 12 for less decay (more sustain).
    - `CC_DECAY_START = 120` -- lower to 104 or 96 for a softer attack.
- Re-run `python approaches/hardware_semantic/scripts/bach_test.py`.

## What to listen for

- Compare the two RPPs for each piece: `_ww_cc` should sound *plinkier*,
  `_adsr` should sound *smoother*.
- Long held Bach notes are the strongest reveal: in `_ww_cc` they decay
  audibly toward silence over half a second; in `_adsr` they plateau.
- Same-pitch retriggers should click cleanly in both, no ring-over.