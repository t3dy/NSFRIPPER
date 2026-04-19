# The data problem of understanding the Nintendo music chip

The core difficulty of this entire project, stated honestly.  You
cannot know "what the NES is doing" by looking at any single artifact
— a ROM, an NSF, a MIDI, an audio recording.  Each is a different
projection of the underlying hardware state, and each projection
loses or transforms different information.  The data problem is
choosing which projection to work from and knowing what you've given
up in that choice.

## What "the chip" actually is

The RP2A03 / 2A07 is not one thing:

1. **Physical hardware** — transistors, capacitors, a 7-bit DAC,
   analog output stage through an RF modulator.  Runs at 1.789 MHz.
2. **Register state** — 24 bytes at `$4000-$4017` that represent the
   chip's instantaneous intent.
3. **Register WRITE sequence** — ordered stream of (time, reg, value)
   tuples driven by the game's sound driver at CPU speed.
4. **Per-frame register snapshot** — the state at each 60 Hz VBlank.
5. **Per-channel output** — 4 digital streams (pulse1, pulse2,
   triangle, noise) plus DMC delta-PCM.
6. **Analog sum** — the two output pins (pulse pin, TND pin) after
   the non-linear DAC, before the RC filter.
7. **Analog-filtered sum** — the 14 kHz RC filter output, as sent
   to the TV.

Every layer is "the chip."  Every layer is a valid place to reason
about behavior.  Every layer has constraints the others don't.

## The projection problem

| Artifact type | What it preserves | What it loses |
|---------------|--------------------|---------------|
| **ROM file** | The driver code + song data.  Everything. | Runtime information — you need to execute it. |
| **NSF file** | The driver code + song data + metadata. | Same as ROM. Still needs execution. |
| **Mesen APU trace** | Actual register writes during a real run.  Ground truth for THAT run. | One specific play-through only.  A game with random SFX or player-controlled channels diverges. |
| **NSF emulation log** | Register writes from our py65 emulator. | Subject to emulator bugs (bankswitch, $4015 init, stuck-count, etc. — all of which we fixed this week). |
| **MIDI with SysEx + CC** | The register writes in a portable format. | Sub-frame timing; whether sweep or phase-reset was intentional; DPCM sample content. |
| **MIDI with CC only** | Note events + volume/duty curves. | SysEx-only behaviors (sweep, noise mode, phase reset, DMC). |
| **MIDI with notes only** | Note events. | Everything timbral. |
| **Rendered WAV** | The analog sum at a specific sample rate. | You can't get back to register state from audio. |
| **YouTube recording** | Final TV analog output. | Everything upstream. |

Every MIDI export is a projection.  Every render is another projection
on top.  The data problem is tracking where you are in this stack and
where you need to be for any given task.

## What each task needs

| Task | Needed minimum | What breaks if you have less |
|------|----------------|------------------------------|
| Archival quality audio | Mesen trace OR very good NSF emulation | Audio sounds "almost right but not quite" |
| Editable score | Note events + tempo | Editing introduces non-game-accurate timing |
| MIDI keyboard playing | Slider presets per driver family | You get generic synth, not NES character |
| Driver family research | Register write patterns + code identity | You misclassify games |
| Video with animated UI | Real-time register stream → slider positions | UI animation looks pre-rendered |
| Fidelity validation | Mesen trace AND our render | You can't prove correctness |

The project's data shape must support all of these simultaneously,
which is why we maintain:

- **Frame IR** (per-frame register state as the canonical form).
- **MIDI with SysEx + CC + notes** (downstream).
- **Stems WAVs** (further-downstream projection for REAPER).
- **RPP + JSFX** (live-play projection that can go back up the
  stack via SysEx).

## Why linear audio understanding isn't enough

If you only had WAV files, you couldn't:
- Retune a note without re-synthesizing.
- Change duty cycle mid-song.
- Swap one game's drum kit for another's.
- Analyze which driver family a game uses.
- Diagnose "is this NSF broken or is our emulator broken?"

If you only had MIDI, you couldn't:
- Reproduce sweep modulation.
- Hear DPCM samples.
- Replay exact register state.

If you only had register traces, you couldn't:
- Edit anything musically — notes are implicit.
- Transpose a song.
- Play a keyboard "in the style of" this game.

The answer is **keep all three representations, know which to use
for what**.  That's the Frame IR doctrine (architecture.md Rule 9 /
12): Trace → Frame IR → MIDI → projection.  Never skip layers.

## The specific data traps we've hit

### Trap 1 — Treating NSF emulation as ground truth

For games like Battletoads and Super Mario Bros, our NSF emulation
produces audibly different output from real hardware.  Solution:
`docs/STATEOFTHEPROJECT.md` fidelity hierarchy — Mesen trace > NSF
for games we have traces for.

### Trap 2 — Trusting M3U labels over audio

Zophar-ripped M3Us are community-made and sometimes wrong (Ghosts
'n Goblins "Stage 1" is actually Stage 3's audio in some rips).
Our `audit_names.py` flags the mismatch but can't resolve it without
ear-testing — because the audio projection can't tell you what was
meant semantically.

### Trap 3 — The CC-encoding approximation

Writing CC11 for volume loses the distinction between "hardware
envelope decay" and "software writes vol=0 then vol=N each frame."
Both look like the same CC11 curve.  But the JSFX needs to handle
them differently for timbre.  Fix: capture `$4015` + const_vol flag
as SysEx.  Done.

### Trap 4 — Different hardware projections disagree

Hardware $4011 DAC write on real NES is instantaneous.  py65's
hierarchy (memory write → CaptureMemory handler → per-frame dict)
has its own quirks.  Fix: bake assumptions into architecture.md as
Rules.  Rules 27-36 are this week's additions.

## Where you should focus your attention, depending on goal

- **"I want archival audio"** → Frame IR + Python stems.  Your
  authority is Mesen trace where available, NSF emulation otherwise.
- **"I want to play live"** → JSFX + per-driver-family presets.
  Your authority is your ear.
- **"I want MIDI to edit"** → Frame IR → MIDI.  Your authority is
  the note-event semantics (which are hypothesis until ear-tested).
- **"I want research on driver families"** → raw register writes +
  INIT fingerprints.  Your authority is mass data over ~300 games.

Each purpose pulls data from different layers.  Conflating purposes
is the fastest way to get confused — one of the recurring failure
modes in the project's history.

## Why this is a context problem too

Given the projections-stack above, a long conversation about "the
NES sound chip" can drift through layers without the conversants
realizing.  You can be talking about the analog output one sentence
and the register state the next.  `docs/HYGIENE.md` covers that
angle explicitly.
