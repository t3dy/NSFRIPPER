# The live-performance problem

You correctly identified the core architectural tension of this whole
project: **a ROM file does not translate losslessly to live MIDI
performance, because MIDI cannot express everything NES hardware does.**
This doc explains exactly where each loss happens, what the synth
does about each one, and what remains unsolved.

## What's in a ROM that MIDI cannot express

The NES APU exposes register state across `$4000-$4017`.  When the
game's sound driver writes to these registers every frame, it encodes
musical events.  MIDI is an event protocol too — but with a much
smaller vocabulary.

### NES register behaviors and their MIDI equivalents

| NES register | What it controls | MIDI equivalent | Lossless? |
|--------------|------------------|-----------------|-----------|
| `$4000` bits 0-3 | Pulse1 volume / env period | CC11 (volume) | **Lossy** — CC11 has 128 levels, NES has 16 |
| `$4000` bits 4-5 | Pulse1 const_vol + env_loop flags | SysEx only | **Lossy in standard MIDI** |
| `$4000` bits 6-7 | Pulse1 duty cycle (4 values) | CC12 (duty) | Near-lossless |
| `$4001` | Pulse1 sweep (enable, period, negate, shift) | Pitch bend approximates | **Very lossy** — sweep is continuous pitch modulation in hardware; MIDI pitch-bend has coarser granularity and doesn't model the sweep's shift-based math |
| `$4002/$4003` | Pulse1 period low/high (11-bit) | MIDI note + channel aftertouch? | **Lossy** — MIDI notes are semitones, NES periods are 11-bit continuous |
| `$4003` write | Also resets pulse phase counter | SysEx (our impl) | Lossless only via SysEx |
| `$4008` | Triangle linear counter reload + ctrl | SysEx | Lossless only via SysEx |
| `$400A/$400B` | Triangle period low/high | MIDI note | **Lossy** — same as pulse periods |
| `$400B` write | Resets triangle linear counter | SysEx | Lossless only via SysEx |
| `$400C` | Noise envelope + volume + const_vol + env_loop | CC11 approximates | **Lossy** — envelope mode is not expressible in CC |
| `$400E` bit 7 | Noise mode (long LFSR vs short/tonal) | Not in MIDI | **Silent loss** |
| `$400E` bits 0-3 | Noise period index (16 distinct freqs) | MIDI note number | **Structurally wrong** — noise "pitch" is not semitonal |
| `$400F` write | Loads length counter | SysEx | Lossless only via SysEx |
| `$4010-$4013` | DMC rate, loop, sample addr, sample len | SysEx / CC + samplebank | **Lossy** — DMC requires separate sample handling |
| `$4015` bits 0-4 | Channel length-counter enable | SysEx | Lossless only via SysEx |
| `$4015` read | Channel-active flags + IRQ status | Not exposed | Irrelevant to playback |
| `$4017` | Frame counter mode (4-step / 5-step IRQ) | SysEx | Lossless only via SysEx |

That's ~30 distinct hardware behaviors; fewer than half survive a
round-trip through standard MIDI.  The rest require either SysEx
(which requires the synth to interpret NES-specific SysEx messages —
we do this) or are silently lost.

## What a live MIDI keyboard sends

When you hit a key, your keyboard sends:

- `note_on <channel> <pitch> <velocity>`
- `note_off <channel> <pitch> <velocity>`
- Maybe pitch-bend (modwheel), aftertouch, sustain pedal.

That's it.  No duty, no sweep, no noise mode, no LFSR seed.

So a live keyboard can only communicate the **note event** and a
coarse sense of dynamics.  Every other NES behavior has to come from
**preset state the synth already knows**.

## The synthesizer's answer (three-priority input cascade)

Per `docs/SYNTHMERGE.md`, our JSFX synthesizer resolves the
information gap by running three parallel input modes and picking
whichever has the most information available in any given moment.

### Priority 1 — SysEx register replay (maximum fidelity)

When the MIDI file contains our custom SysEx messages (`F0 7D 02 ch
r0lo r0hi r1lo r1hi r2lo r2hi r3lo r3hi en mask F7`), the synth
**ignores everything else and replays the exact NES register state**.
This gets everything — sweep, phase reset, noise mode, DMC, frame
counter — because we encoded every one of them as SysEx before shipping
the MIDI.

This is what NSF extraction produces for us.  `nsf_to_reaper.py`
embeds per-frame SysEx into every MIDI export (see the `SysEx` track
in each generated MIDI).  When you play this MIDI in REAPER, the
JSFX is effectively running the original driver.

**You can't play SysEx from a keyboard.**  A keyboard doesn't know
what `$4003 write + $4002 period-low` means.  So Priority 1 is a
file-playback fidelity mode, not a live-play mode.

### Priority 2 — CC11/CC12 automation (file-driven, simpler)

When MIDI notes have CC11 (volume) and CC12 (duty) automation but no
SysEx, the synth uses CC11 for volume and CC12 for duty.  Period
comes from the MIDI note number.

This is where a non-SysEx-aware MIDI file ends up.  It gets you about
70% of the way to hardware fidelity.  Loss: sweep, noise mode, phase
reset, DMC state.

**You can play keyboard over a CC-automated track**, though the
layering is limited because both the file's CC events and your
keyboard's note events compete for the same JSFX instance.

### Priority 3 — ADSR keyboard mode (live performance)

No file data arriving → the synth runs an **ADSR envelope** whose
parameters come from the JSFX's slider panel.  Each driver-family
preset (see `docs/SYNTHMERGE.md` "Driver Family Presets") sets these
sliders to match a specific game's characteristic sound.

Sliders map to NES behaviors we'd otherwise get from registers:

| Slider | NES concept it replaces |
|--------|-------------------------|
| Duty 0-3 | `$4000/$4004` duty bits |
| Volume 0-15 | `$4000/$4004` env period or fixed volume |
| Attack (ms) | fake — NES is essentially instant; we add this for musical feel |
| Decay (ms) | approximates hardware envelope linear decay |
| Sustain 0-15 | fake — NES envelope decays to 0; sustain holds for musical feel |
| Release (ms) | fake — NES drops instantly on gate close |
| Sweep enable / rate / depth | `$4001` approximation |

The keyboard sends note-on; the synth fires the ADSR; the slider
settings shape the timbre.  **This is live play.**

### Why this cascade gives you the best of both worlds

- **Playing the extracted MIDI file of Castlevania Vampire Killer**
  → Priority 1 (SysEx) kicks in → bit-accurate to the original
  hardware.
- **Playing the same file with the MIDI keyboard layered on top** (you
  mute the file's pulse1 track and play your own notes) → Priority 3
  (ADSR) on that track, Priority 1 still driving the other 3 channels.
  You get a live Castlevania duet.
- **Jamming freely with no file** → all tracks in Priority 3.  Load
  the "Castlevania" preset on pulse1 and "Battletoads" on pulse2;
  your two hands play two different driver families simultaneously.

## What this design does NOT solve

Honest list of remaining gaps.

### 1. Live keyboard cannot reproduce per-frame register manipulation

Rare's Battletoads driver modulates duty cycle per-frame during
sustained notes.  A standard MIDI keyboard sends only a note event;
CC12 is static unless you touch a modwheel-or-similar physical
control.

**Partial solution**: use a MIDI keyboard with CC-mappable knobs
(most do).  Dedicate one knob to CC12.  Move the knob while playing
to reproduce duty animation.  Still coarser than per-frame driver
code, but playable.

### 2. Noise channel has no pitch concept

Noise period is one of 16 discrete indices — not pitches.  A keyboard's
C major scale has no meaningful mapping to noise periods.

**Partial solution**: the JSFX maps keyboard notes to noise period
indices heuristically (lowest key = slowest period, highest key =
fastest).  You can play "noise drums" from a keyboard, but it's
invented, not game-accurate.

### 3. DMC needs sample data the keyboard can't provide

DMC plays arbitrary samples from the ROM.  A keyboard has no way to
send "play the SMB jump sound from address `$E000`."

**Partial solution**: the DMC track in our JSFX loads a small bank
of pre-extracted samples.  The keyboard triggers them at different
pitches.  Useful for reproducing a specific game's drum kit; not
game-general.

### 4. Exact bit-accurate playback requires pre-computed MIDI

Priority 1 (SysEx) needs MIDI events the keyboard doesn't produce.
For true hardware fidelity, you play the EXTRACTED MIDI, not an
improvised one.  Live keyboard can't reach Priority 1 alone.

**No partial solution.**  If your goal is "play a brand-new melody
that sounds exactly like the NES played it," you're stuck at
Priority 3 (ADSR) quality — good but not hardware-bit-identical.

## So: what's your realistic live-play experience?

With this design:

- **Quality tier**: 90-95% NES-like on a well-tuned preset.  The
  remaining 5-10% is the grit/animation from per-frame register
  manipulation that a human pianist can't replicate.
- **Latency**: REAPER + JSFX is ~5-15 ms end-to-end.  Fine for
  playing, not sample-accurate.
- **Multi-voice**: you can play all 4 NES channels at once from a
  single keyboard by splitting the range (Pulse1 in low register,
  Noise drums in top octave, etc.) and setting each JSFX instance's
  keyboard-mode to "On."
- **Video recording**: slider animations + scope visualizations
  make it record well.  Turn the sliders during the performance for
  on-camera "sound design."

## The final answer to your question

**How does the synthesizer design solve the ROM → live-performance
gap?**

It doesn't solve it — it *partitions* it.  Full hardware fidelity
lives in Priority 1 (SysEx-driven file playback).  Live playability
lives in Priority 3 (keyboard + ADSR preset).  The gap between them is
real, but both endpoints work well for their own use case.

The big UX win is that you can have both in the same project
simultaneously.  Your extracted Castlevania MIDI plays with
hardware-exact fidelity on four tracks; you mute one and play your
hand through the preset-tuned JSFX; your keyboard notes fit the
game's sound without you having to understand anything about
`$4003` phase resets.

This means: **your synthesizer's job isn't to make a live MIDI
keyboard sound exactly like the NES.  Its job is to give you ONE
interface where you can A) play back hardware-exact extractions and
B) perform live in the same characteristic sound, and these two use
cases coexist without conflict.**

That's the design answer.  Whether it's enough depends on what you
actually want to do with it — which we can answer by testing on
specific games and specific performance scenarios in this
`keyboard_lab/` subfolder.
