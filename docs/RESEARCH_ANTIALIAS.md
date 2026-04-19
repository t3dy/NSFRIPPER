# Research: NES APU audio rendering in the community

Companion to `NOISEPROBLEM.md`.  Where NOISEPROBLEM describes what I
found in our Battletoads render, this file documents what the NES
emulator / chiptune community has already figured out, so the next
work item can start from their shoulders instead of reinventing things.

Compiled 2026-04-18 evening from web research against:
Nestopia, FCEUX, Mesen, higan/ares, puNES, libgme, FamiTracker,
0CC-FamiTracker, FamiStudio, NESDev wiki, NESDev forums.

## 1. Everyone uses Blargg's Blip_Buffer

Blargg (Shay Green) wrote `Blip_Buffer` / `Nes_Snd_Emu` ~2005.  It is
the de-facto standard for NES audio in accurate emulators and trackers:

| Project | Audio engine |
|---------|--------------|
| libgme (Nes_Apu.cpp / Nes_Dmc.cpp) | Blip_Buffer |
| Mesen | Blargg-derived |
| FCEUX | Blip_Buffer |
| Nestopia UE | Blargg-derived |
| puNES | Uses Blargg's emu directly |
| higan / ares | Band-limited technique inspired by Blip_Buffer |
| FamiTracker | Ships blip_buffer 0.4.0 |
| 0CC-FamiTracker | Inherits FamiTracker's blip_buffer |
| FamiStudio | Ports `blip_buf` to C# |

The entire chiptune ecosystem converges on the same algorithm.  Not
polyBLEP, not supersampling with scipy decimate -- Blargg's delta-based
BLEP resampling.

## 2. How Blip_Buffer works (so we can port it)

Core idea: don't sample a waveform at output rate and try to
anti-alias after.  Instead, record **amplitude deltas at the source
clock rate** (NES runs at 1,789,773 Hz -- about 40x the audio output
rate of 44.1 kHz).  Every time a pulse edge happens, a `$4003` phase
reset fires, a DMC DAC value changes, etc., push a (sample_time,
delta_amplitude) pair into the buffer.

At output time, each delta "stamps" a precomputed band-limited step
kernel (BLEP) into a ring buffer at the correct sub-sample phase
offset.  The kernel is a windowed-sinc step response.  When the
buffer is read, the stamped steps sum correctly to produce an alias-
free reconstructed waveform at any output rate.

Key Blip_Buffer parameters (from `blip_buf.c`, ~200 lines of C):
- 32 sub-sample phases (`phase_bits = 5`).  Temporal resolution of
  deltas is `output_period / 32` = ~0.7 µs at 44.1 kHz.
- 16-tap FIR (8 samples each side of the edge).  Generated once by
  Blargg's `Sinc_Generator(0.9, 0.55, 4.5)` -- a Kaiser/Blackman-
  windowed sinc with cutoff at ~45% of Nyquist.
- DC blocker: `sum -= s >> 9` -- equivalent to 1-pole HP at ~10 Hz
  (same ballpark as our Rule 33 DC blocker).

**CPU cost**: one FIR multiply-add per delta, not per sample.  For
NES, ~200 deltas per frame per channel -> ~12000 multiplies per frame.
At 60 Hz frame rate, ~720K ops/sec.  Negligible.

## 3. Why polyBLEP is wrong for our pipeline

polyBLEP is a 2-sample polynomial approximation of the BLEP impulse.
It was designed for VA synth plugins that synthesize pulse/saw **at
native output rate** where a full FIR convolution is too expensive.
In those cases you replace each edge with a cheap second-order
correction.

We do not have that constraint: our NSF emulator already runs at
CPU clock rate (1.789 MHz).  We are already oversampled ~40x relative
to output.  The remaining problem is downsampling to 44.1 kHz
without aliasing, which is exactly what Blargg's BLEP resampling
solves.  polyBLEP would be strictly worse:

| | polyBLEP | Blargg BLEP |
|---|----------|-------------|
| Kernel | 2 samples, polynomial | 16 samples, windowed sinc |
| Stopband (above Nyquist) | ~13 dB | ~60 dB |
| Typical usage | native-rate synth | oversampled source |
| Code size | trivial | ~200 lines |

## 4. Our analytical-integration pulse was better than nothing but insufficient

What I implemented today
(`render_channel_stems.py::_bandlimited_pulse`) integrates the ideal
pulse over each sample window:

```
fraction_high = (H(pa_end) - H(pa_start)) / (pa_end - pa_start)
```

This is equivalent to a **rectangular-window anti-alias filter**.  In
the frequency domain it's a `sinc(f/SR)` -- the first null is AT
Nyquist and the stopband attenuation is only ~13 dB.  Better than
naive point-sampling but nowhere near Blargg's ~60 dB stopband.

Measured impact on Battletoads pulse1:
- Naive: 2641 sample-steps > 10% of peak in 60 s
- Analytical integration: 1682 (36% fewer)
- + 4-pole Butterworth LP: 875 (67% fewer vs naive)
- Estimated Blargg BLEP: < 100 (remaining clicks would be real
  hardware steps like note-on, not aliasing artifacts)

## 5. Mesen has documented fixes we are missing

From `mesen.ca/docs/configuration/audio.html`, two optional audio
accuracy switches:

**Mute ultrasonic triangle**.  When the triangle period register is
< 2, the channel emits ultrasonic frequencies that alias into the
audible range as a whine.  Mega Man 2's `$4008=0 / $400B=X / $400A=0`
trick deliberately produces this.  Mesen's option silences the
channel when `period < 2`.  We should add this option.  Our current
gate is `p >= 2 AND tri_linear_live > 0`.  The `p >= 2` part already
handles this -- but only in the stems renderer.  Need to verify the
Python WAV render (`nsf_to_reaper.py::render_wav`) does the same.

**DMC popping reduction**.  Writes to `$4011` produce clicks because
the DAC value steps instantly.  Some drivers (Sunsoft bass, Battletoads
algorithmic drums) rely on these clicks as part of the sound.  Mesen's
option clamps `|Δdac| ≤ K` per output sample, producing a slew-rate-
limited version that trades authenticity for listenability.

**Gotcha from the community**: libgme does NOT special-case `$4011`
writes -- it passes them through BLEP and lets the kernel handle HF
content.  Mesen's clamp is a non-accuracy convenience option.  For our
YouTube output where listenability matters, the clamp may be worth
having as a flag (default off).

## 6. The non-linear DAC cannot be correctly stemmed per-channel

This is the load-bearing finding for our stems architecture
(Rule 31 in `architecture.md`).  NESDev wiki (`APU_Mixer`):

```
pulse_out = 95.88 / ((8128 / (pulse1 + pulse2)) + 100)
tnd_out   = 159.79 / ((1 / (triangle/8227 + noise/12241 + dmc/22638)) + 100)
```

These formulas are **not separable**.  `f(p1 + p2) ≠ f(p1) + f(p2)`.
Our current stems pipeline runs each channel through the non-linear
formula with only that channel active, then REAPER sums them
linearly on the master bus.  This over-sums simultaneous channels:

- Two pulses at vol 15 simultaneously:
  - Correct hardware output: `95.88*30/(8128 + 3000) = 0.258`
  - Our linear sum of stems: `2 * 95.88*15/(8128 + 1500) = 0.298`
  - **+15% too loud when both pulses active**.  Audible as
    "overdrive" on rich harmonic passages.

Every major chiptune tool in the community punts on this same problem.
Three known options:

**(A) Linear approximation, accept the error.**  What FamiTracker,
libgme, FamiStudio all do for per-channel exports.  Apply:

```
pulse_out_linear ≈ 0.00752 * (p1 + p2)
tnd_out_linear   ≈ 0.00851*tri + 0.00494*noise + 0.00335*dmc
```

Per-channel stems sum linearly and are within 1-2 dB of the non-
linear result.  Simplest, and ear tests generally pass.

**(B) Two bus stems -- pulse pin + TND pin.**  Render one stem for
the combined pulse pin (p1 + p2 through the non-linear formula as one
signal) and a second for the combined TND pin (tri + noise + dmc
through the non-linear formula as one signal).  REAPER sums these
two stems linearly on master, which matches hardware (the two pins
DO sum linearly at the analog output).  You lose per-channel mute /
solo / fader, but you keep cross-channel compression within each pin.

This is my recommendation.  Reasoning: user's primary goal (per
MEMORY.md) is "sounds like the game".  Non-linear compression is
part of the NES sound.  Two bus stems keep that intact while still
exposing editable MIDI tracks per channel (for arrangement /
visualization / score export).  Five audio stems would be nice but
don't match hardware.

**(C) Full mix + channel solos.**  Render the full mix once and
provide separate `_solo_p1`, `_solo_p2`, etc. files each rendered
with only that channel active.  Stems do NOT sum to the master.
Useful for A/B listening but confusing for DAW mixing.

## 7. Action items ordered by impact

**Priority 1: Two-bus-stem architecture (option B above).**
Directly addresses the non-linear mix distortion that the user
perceived as "overdrive on sustained pulse notes".  Estimated ~2 hours
of work.  Refactor `render_channel_stems.py::main` to render only two
audio stems, but keep MIDI tracks per-channel in the RPP.  Update
Rule 31 in `architecture.md` as a refinement.

**Priority 2: Port blip_buf to numpy.**
Replaces analytical-integration pulse with proper BLEP anti-aliasing.
Eliminates the remaining 875 pulse clicks/minute on Battletoads s1.
Estimated ~1 day of work (200-line C port, plus test fixtures).
Affects pulse + triangle + noise + DMC.  Single-file module that
render_channel_stems.py imports.

**Priority 3: Triangle period < 2 mute.**
Verify `p >= 2` gate is applied uniformly across all renderers
(stems, WAV, JSFX).  Currently only in stems.

**Priority 4: DMC $4011 slew-rate clamp (optional).**
Flag-gated.  For games that use $4011 drums heavily (Battletoads,
Sunsoft titles), offer a knob to soften clicks at the cost of
authenticity.

## 8. Primary sources

- **NESDev APU Mixer**: `https://www.nesdev.org/wiki/APU_Mixer`
  Canonical non-linear formulas and the linear approximation.
- **Blargg's audio libs**: `https://www.slack.net/~ant/libs/audio.html`
  Blip_Buffer, Nes_Snd_Emu, tech notes.
- **libgme on GitHub**: `https://github.com/libgme/game-music-emu`
  Production reference.  `gme/Nes_Apu.cpp`, `gme/Nes_Dmc.cpp`,
  `gme/Blip_Buffer.h`.
- **blip-buf single-file C**: `https://github.com/nesbox/blip-buf/blob/master/blip_buf.c`
  Cleanest read.  ~200 lines.  Direct port target.
- **NESDev forum: bandlimited pulse**:
  `https://forums.nesdev.org/viewtopic.php?t=10983`
  Blargg himself explaining delta synthesis with code.
- **NESDev forum: Blip_Buffer filters**:
  `https://forums.nesdev.org/viewtopic.php?t=16709`
  Filter parameters and trade-offs.
- **NESDev forum: Gibbs & bandlimited synthesis**:
  `https://forums.nesdev.org/viewtopic.php?t=10723`
  Gotcha: FIR ringing is a property, not a bug.  Choose sigma/
  raised-cosine window if you want less overshoot.
- **Mesen audio docs**: `https://mesen.ca/docs/configuration/audio.html`
  Ultrasonic triangle mute + DMC popping reduction flags.
- **Martin Finke polyBLEP article**:
  `https://www.martin-finke.de/articles/audio-plugins-018-polyblep-oscillator/`
  Reference polyBLEP formula.  Included for comparison; **not**
  recommended for our pipeline.
- **FamiTracker source on GitHub**:
  `https://github.com/HertzDevil/famitracker-all`
  Confirms `blip_buffer 0.4.0` usage.

## 9. What not to do

- **Don't port polyBLEP.**  It's a polynomial for native-rate synth.
  For our 40x-oversampled NSF source, a proper FIR BLEP is both
  cleaner and well within CPU budget.
- **Don't render 5 separate stems through the full non-linear
  formula.**  They sum linearly in REAPER which produces the 15%
  overloud error.  Use 2 bus stems instead.
- **Don't try to "fix" Gibbs phenomenon overshoot** around BLEP
  edges.  It's not a bug -- it's what band-limited reconstruction
  looks like.  Use a sigma window or raised-cosine if the overshoot
  is audibly objectionable; don't add DC restoration or time-domain
  clipping.
- **Don't revert the triangle gate-off DAC hold.**  That was a real
  bug and the fix matches hardware + libgme + every reference
  implementation.
