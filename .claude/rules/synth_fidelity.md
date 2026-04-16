---
description: Synth plugin fidelity rules — CC automation, ADSR, dual-mode contract
globs:
  - "studio/jsfx/**"
  - "scripts/generate_project.py"
---

# Synth Fidelity Rules

The goal is note-accurate reproduction of original NES game music.
Every design decision serves this goal.

## 0. One Synth Plugin (ReapNES Studio)

All functionality lives in ONE JSFX file. Not multiple plugins for
different modes. The user opens one synth, it auto-detects what to do.
See docs/SYNTHMERGE.md for the full design.

## 1. Three-Priority Input Cascade

The synth operates in three modes per channel, auto-selected by
incoming data (highest available priority wins):

**Priority 1: SysEx register replay** (maximum fidelity):
- SysEx F0 7D 01 arrives → raw APU register state drives waveform
- All NES behaviors reproduced: sweep, phase reset, noise mode
- Volume, duty, period come from register bytes, not MIDI
- This IS the NES hardware running in software

**Priority 2: CC-driven mode** (file playback, no SysEx):
- CC11 arrives → volume from CC11, ADSR bypassed
- CC12 arrives → duty from CC12
- Period from MIDI note number (semitone-quantized)
- Misses: sweep vibrato, sub-semitone pitch, noise mode, phase reset

**Priority 3: ADSR keyboard mode** (live composing):
- No file data received → ADSR envelope shapes note
- Sweep, vibrato, duty from knob/slider positions
- Game-specific presets capture each game's characteristic sound
- CC123 or CC121 resets back to this mode

Why: SysEx register replay bypasses all MIDI encoding limitations.
CC mode is a fallback for files without SysEx. ADSR is for live play.
The cascade ensures the best available data always drives the sound.

## 2. CC11 = Volume (Expression)

- MIDI CC11 maps to NES volume: `nes_vol = floor(msg3 * 15 / 127)`
- Applied directly to channel output level
- Typical: 4-5 CC11 changes per note (per-frame updates from NSF)
- Pulse channels: full 0-15 range with decay/release ramps
- Triangle: always 127 (gate signal — triangle has no hardware volume)
- Noise: no CC11 (velocity-driven)

## 3. CC12 = Duty Cycle (Timbre)

- MIDI CC12 maps to NES duty: values 0-3 (12.5%, 25%, 50%, 75%)
- Mapping: 0-31→0, 32-63→1, 64-95→2, 96-127→3
- Applied to pulse waveform lookup table index
- Changes per-frame alongside CC11 (synchronized by NSF extraction)
- Only applies to pulse channels (triangle/noise have no duty)

## 4. Note Duration = Period Change

In NSF-extracted MIDIs, note boundaries are NOT arbitrary MIDI decisions.
They occur when the NES APU period register changes value:

- Period changes from X to Y → note_off for old, note_on for new
- Duration = number of frames the driver held the period constant
- Minimum: 32-48 ticks (2-3 frames, ~33-50ms)
- Typical: 96-200 ticks (6-12 frames, ~100-200ms)
- Maximum: 1344+ ticks (84+ frames, ~1.4s)
- Granularity: 16 ticks per frame (TICKS_PER_FRAME = 16 at 128.6 BPM)

The MIDI note duration and CC11 envelope are independent:
- Duration = when period changes (pitch boundary)
- CC11 = volume shape within that duration (amplitude envelope)

A note can be "silent" for its last N frames if CC11 decays to 0
before the period changes. This is correct NES behavior.

## 5. What Each Channel Sounds Like (CV1/Contra reference)

**Pulse 1 (lead melody):**
- ~309 notes in Vampire Killer, ~4 CC11 updates per note
- Typical pattern: attack at vol 15, decay over 3-4 frames, sustain at vol 4-8
- Duty shifts during attack phase (brighter attack, mellower sustain)

**Pulse 2 (harmony/countermelody):**
- Similar density to Pulse 1 but slightly different envelope shape
- Castlevania uses duty=2 (50%) for Pulse 2 vs duty=1 (25%) for Pulse 1

**Triangle (bass):**
- CC11 = 127 always (no hardware volume control, only gate on/off)
- Duration alone controls articulation (staccato = short note, legato = long)
- 1 octave lower than pulse for same period value (32-step sequencer)

**Noise (drums):**
- No CC11. Velocity on note_on sets initial volume.
- Self-decaying: drums decay naturally via the ADSR in keyboard mode
- Note mapping: kick=36, snare=38, hi-hat=42, etc.

## 6. Never Do This

- Override CC11 volume with ADSR when CC data is present
- Use ADSR envelopes for file playback (that's what CC automation is for)
- Assume all games have the same envelope shape (CV1 ≠ Contra ≠ Mega Man)
- Ignore CC12 duty changes (they contribute to the per-frame timbre)
- Truncate notes based on volume (duration = period change, not volume=0)
- Use a flat synth (no envelope) for keyboard play (sounds lifeless)
- Use linear mixing when non-linear mixing is achievable (see Rule 7)

## 7. Non-Linear APU Mixing (from FamiTracker source, NESDev wiki)

The NES APU uses impedance-based non-linear mixing:

```
Pulse output:  95.88 / ((8128.0 / (sq1 + sq2)) + 100.0)
TND output:    159.79 / ((1.0 / ((tri/8227) + (noise/12241) + (dpcm/22638))) + 100.0)
```

Where sq1/sq2 are pulse channel amplitudes (0-15), tri is triangle
amplitude (0-15), noise is noise amplitude (0-15), dpcm is DMC
output (0-127).

Key implications:
- Two pulses at max volume (15+15) produce ~0.278, not 2× one pulse
- Adding a second pulse at volume 15 reduces the first from ~0.184 to ~0.148
- Triangle/noise/DPCM interact similarly on the TND pin
- Linear mixing makes simultaneous channels too loud (was the Console
  default before 2026-04-15; APU2 already had non-linear)

**Implementation status (2026-04-15):**
- `ReapNES_Console.jsfx`: non-linear mixing implemented (was linear)
- `ReapNES_APU2.jsfx`: non-linear mixing already present
- `render_wav()` in `nsf_to_reaper.py`: non-linear mixing implemented
  via `_apu_nonlinear_mix()` function (was linear additive)
- Mix slider knobs in Console scale per-channel amplitude BEFORE the
  non-linear stage, preserving hardware interaction behavior

## 8. Driver Family Presets for Keyboard Mode (ADSR)

Revised 2026-04-14: 4-family model (Family 5 eliminated, zero members).
See `docs/NEWDRIVERFAMILIES414.md` for census methodology.

The NES APU has two envelope modes ($4000 bit 5):
- Bit 5 = 0: Hardware envelope (linear decay from max to zero)
- Bit 5 = 1: Constant volume (driver writes volume every frame)

The ADSR keyboard mode should offer presets matching all four families:

**Sparse Envelope preset** (Family 1: 156 games):
- Sub-group 1A (CC11 <= 0.5, 53 games): pure HW decay or constant vol
  - Attack: instant (1 frame)
  - Decay: linear to zero over 8-15 frames
  - Sustain: 0 (no sustain — decays completely)
  - Release: immediate
  - Sounds like: Mega Man 1, Marble Madness, Section Z, early Capcom
- Sub-group 1B (CC11 0.5-2.8, 103 games): occasional SW volume writes
  - Attack: instant (1 frame)
  - Decay: 4-6 frames to sustain level
  - Sustain: vol 3-6
  - Release: 2-3 frames
  - Sounds like: Mega Man 2-3, Castlevania, DuckTales, Battletoads

**Active Envelope preset** (Family 2: 79 games):
- Attack: instant at vol 15
- Decay: 3-4 frames to sustain level
- Sustain: vol 4-8 (game-specific)
- Release: 2-3 frames to zero
- Sounds like: Contra, Ninja Gaiden, Zelda II, TaleSpin

**Duty Animator preset** (Family 3: 20 games):
- Same ADSR as Active Envelope for volume
- Additionally: duty cycle animates per-frame (12.5% → 25% → 50% typical)
- CC12 changes produce timbral sweep within each note
- Sounds like: Super Mario Bros 3, Konami Hyper Soccer, Snakes Revenge

**Dense Envelope preset** (Family 4: 16 games):
- Per-frame volume table with tremolo/vibrato character
- Multiple volume updates per note (6-16 CC11 events per note)
- Often has characteristic "shimmer" or "throb" from rapid vol changes
- Sounds like: Metroid, Kid Icarus, Rad Racer II, Maharaja

## 9. Noise Channel Period Inversion (from FamiTracker source)

Noise period index is inverted before writing to APU register $400E:
the index is XORed with 0x0F. This means:
- Period index 0 → longest period (lowest pitch noise)
- Period index 15 → shortest period (highest pitch noise)

This is the opposite convention from melodic channels where lower
period = higher pitch. MIDI note mapping for noise should account
for this inversion.

NTSC noise periods (16 entries):
4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068

Noise mode bit ($400E bit 7): 0 = long LFSR (hissy), 1 = short (tonal/metallic).
