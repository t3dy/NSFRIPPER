# Battletoads click/pop/overdrive investigation — 2026-04-18 evening

User report: after the outputv6 pipeline fixes landed this afternoon, Battletoads
still has audible problems in REAPER playback:

- **Clicking / popping** (possibly aliasing)
- **Overdriven synth sound** on sustained notes
- **Vinyl-record-style pops** at specific moments

What follows is the diagnosis, the fixes attempted, and where things stand.

## 1. Three distinct problems, not one

Measuring sample-to-sample amplitude steps in each stem of
`outputv6/Battletoads/stems/01_Song_01/` (60-second render, post-fixes-of-
the-morning) revealed three separate click mechanisms, each with a different
acoustic signature:

| Channel | Peak | Worst single-sample step | Count of >10%-of-peak steps | Offset pattern |
|---------|------|--------------------------|------------------------------|----------------|
| pulse1  | 0.175 | 0.106 (61% of peak) | 2641 in 60s | scattered in-frame |
| pulse2  | 0.175 | 0.127 (73% of peak) | 1993 in 60s | scattered in-frame |
| triangle | 0.636 | **0.386 (61% of peak)** | 1292 in 60s | **always at frame boundary (offset 0)** |
| noise   | silent in s1 | — | — | — |
| dmc     | 0.070 | 0.022 | 0 | small sub-sample flips |

Two different problems jump out:
- **Triangle**: huge clicks, always at frame boundaries. Matches the
  "vinyl pop" symptom.
- **Pulses**: continuous small clicks everywhere. Matches the "overdriven
  hiss" symptom.

## 2. Triangle clicks → hardware gate behavior was wrong

Instrumenting the render showed **129 triangle gate transitions in 600
frames** (once every ~4-5 frames, ~14 Hz — the Battletoads bassline tempo).
The renderer was zeroing the triangle output during gate-off frames
(`tri_linear_live == 0`).

This is **not** what the NES hardware does. Per NESdev Wiki (APU_Triangle):

> If either the linear counter or the length counter is zero, the
> sequencer is held at its current position. The DAC keeps outputting
> the current step's value.

So hardware gate-off produces a held DC level — no step, no click. Our
code produced a 38%-scale step from the wave's current position down to 0,
which is exactly what the user perceived as "vinyl pops."

**Fix (shipped):** during gate-off, evaluate the triangle wave at the
current frozen phase and hold that value across the frame. Phase is *not*
advanced (matches HW sequencer pause). The DC blocker then resolves the
held level to silence over ~50 ms, without a step transient.

**Measured impact:** triangle max step 0.386 → **0.006** (98.4% reduction).
Steps > 10% of peak: 1292 → 0. All vinyl-pop clicks on the triangle
channel are eliminated.

## 3. Pulse clicks → edge aliasing from naive synthesis

The pulse stems were generated with naive point-sampling:

```python
p1_wave[:] = np.where(pa < dv, effective_vol, 0)
```

This produces a **step function with infinite bandwidth** at every
duty edge. Sampling this at 44.1 kHz aliases any frequency content above
Nyquist (22.05 kHz) back down into the audible range. A 2000 Hz pulse
has meaningful harmonics out to ~40 kHz, and the folded-back aliases land
near the fundamental as rough, inharmonic grit. This is the "overdrive"
the user reports on sustained pulse notes.

**Fix (shipped):** replace `np.where(pa < dv, vol, 0)` with an analytical
band-limited formula. For each sample window `[pa_start, pa_end)`, the
exact time-averaged pulse value is:

```
fraction_high = (H(pa_end) - H(pa_start)) / (pa_end - pa_start)
where H(x) = duty*floor(x) + min(x - floor(x), duty)
```

`H(x)` is the integral of `1{pa%1 < duty}` from 0 to x. This produces
a proper 3-level output at edges instead of 2-level, which is equivalent
to applying a rectangular-window anti-alias filter.

**Measured impact:** pulse1 steps > 10% dropped 2641 → 1682 (36% fewer).
Pulse2: 1993 → 1302. Average edge click magnitude roughly halved.

This fix helped but is not complete. A 3-level edge still has broadband
content; proper anti-aliasing would require polyBLEP (polynomial BLEP)
correction or N-times oversampling.

## 4. LP filter: trying to match hardware without ringing

The NES output has a multi-stage analog filter. The dominant pole is
a ~14 kHz RC filter (NESdev reference). Our model has a 2-pole
Butterworth at 14 kHz (added morning of 2026-04-18 to smooth edges).

Tried bumping to 4-pole Butterworth to attenuate aliasing harder
(24 dB/octave instead of 12). Result:

| LP order | pulse1 max_step | pulse1 steps>10% | pulse2 steps>10% |
|----------|-----------------|------------------|------------------|
| 2-pole (morning) | 0.106 | 2641 | 1993 |
| 2-pole + bandlim pulse | 0.119 | 1682 | 1302 |
| **4-pole + bandlim pulse** | **0.124** | **875** | **677** |

Steeper LP cuts the click **count** further (875 vs 1682), but
single-sample max step **increased** (0.124 vs 0.119). Diagnostic dump at
one click site showed the 4-pole filter **overshoots** on note-on steps:

```
silent ... 0.000, 0.000, 0.000,         <- last silent samples
0.037, 0.144, 0.219, 0.185, 0.163,       <- note-on, overshoot to 0.219
0.189, 0.185, 0.174, 0.182, 0.182, ...   <- settling
```

That 0.219 is a transient overshoot above the steady-state pulse level
(~0.18). Butterworth isn't critically damped; higher order = more ringing.
So 4-pole produces fewer clicks but larger worst-case overshoot.

## 5. What to try next

Neither 2-pole nor 4-pole Butterworth is ideal. Options on the table:

**A. 4-pole Bessel filter.** Bessel has near-critically-damped step
response (minimal overshoot). Trade-off: shallower transition band than
Butterworth, so less aliasing attenuation.

**B. 4x oversampled pulse synthesis + decimation.** Generate the
bandlimited pulse at 176.4 kHz, apply LP, then use `scipy.signal.decimate`
with a sharp anti-alias filter to bring it to 44.1 kHz. This is the
textbook anti-aliasing technique and fixes pulse aliasing properly. Cost:
4x memory and CPU in pulse synthesis. ~85 MB peak for a 60 s song. Fine.

**C. polyBLEP correction at edges.** Standard technique in modern soft
synths — adds a 2-sample polynomial correction at each detected edge.
Cheaper than 4x oversample, slightly more code complexity.

**D. Smooth note-on volume with a few-sample linear ramp.** Halves the
LP step magnitude, reducing ringing amplitude. Not hardware-accurate but
audibly cleaner. NES hardware *does* step instantly on note-on; the real
NES sounds "snappy" because of the analog filter's short time constant.
A 4-sample ramp at 44.1 kHz is ~0.1 ms — well below the perception
threshold, and still snappier than a ramp over 10+ ms.

**Current leaning:** try Option B (4x oversample for pulses only — triangle
is already smooth; noise and DMC have their own paths). That eliminates
aliasing cleanly. If CPU cost is too high, fall back to Option C (polyBLEP).

## 6. What's in the code right now

Commits in this session (to `scripts/render_channel_stems.py`):

1. **Triangle gate-hold** (line ~337 in `render_stem`): when
   `tri_linear_live == 0`, the renderer now outputs the held DAC value
   at the frozen phase instead of zeroing the wave. Phase not advanced.
2. **Bandlimited pulse synthesis** (`_bandlimited_pulse` helper): replaces
   naive `np.where` square-wave sampling with an analytical integral over
   each sample window.
3. **4-pole LP** (`_NES_LP_B/_A`): bumped from 2-pole to 4-pole. May
   revert if note-on overshoot is audible.

## 7. Don'ts confirmed during this investigation

- Don't revert to `tri_wave[:] = 0` on gate-off. Reintroduces 129 vinyl
  pops every 10 seconds on Battletoads (and similar amounts on every
  game using triangle staccato bass, which is most of the NES library).
- Don't revert the bandlimited pulse formula. The naive `np.where`
  version produces 57% more clicks per second on Battletoads pulses.
- Don't remove the LP filter entirely. Edges without any smoothing
  become painfully sharp in a DAW.

## 8. Pending user ear-test

The triangle gate-hold fix should kill the "vinyl pop" symptom
completely. Pulse clicks are reduced by ~65% but not gone; the
"overdrive" perception may still be audible depending on the specific
song's pulse pitch range. Next step is the user's ear on a re-rendered
Battletoads s1.

Nothing is claimed "fixed" until the user confirms by ear. Per the
existing feedback rule: shipped, awaiting ear-test.

## 9. Distortion vs click: what this session does and does not fix

These are two different problems:

- **Clicks and pops** are time-domain transients: sudden amplitude
  jumps between adjacent output samples.  Triangle gate transitions
  (vinyl pops) and pulse edge sampling (continuous low-level crackle)
  are both click mechanisms.
- **Distortion** is anything that makes the summed signal not match
  what the hardware would produce.  Sources include: aliasing content
  folded into the audible band (makes sustained notes sound "rough"),
  the non-linear DAC mixing formula not being applied correctly, and
  filter overshoot on note-on steps.

This session's fixes address:

| Mechanism | Before session | After session |
|-----------|---------------|---------------|
| Triangle gate vinyl pops | 0.386 per event | 0.006 |
| Pulse-edge aliasing (samples > 10%/peak per 60 s) | 2641 | 875 |
| Frame-boundary amplitude clicks | not addressed | same |
| **Non-linear DAC mix error** (per-stem) | **~15% overload** | **unchanged** |
| **Filter ringing on note-on** | 2-pole: small | 4-pole: larger |
| **DMC $4011 click** | hardware-authentic | hardware-authentic |

**What is NOT fixed in this session**:

1. The non-linear APU mixer is applied per-stem with only one channel
   active, so when REAPER sums 3-5 stems on its master bus, the sum is
   linear addition and over-adds when multiple channels play together.
   Two pulses simultaneously = +15% too loud, which sounds like mild
   distortion / overdrive on rich passages.  **This is the most likely
   residual "overdrive" source** after the aliasing fixes.  Solution:
   collapse to two bus stems (pulse pin + TND pin) each run through
   the non-linear formula before output.  See `RESEARCH_ANTIALIAS.md`
   section 6, option B.

2. Proper anti-aliasing (Blargg-style BLEP resampling).  Our current
   analytical-integration is a rectangular-window filter with ~13 dB
   stopband.  Proper BLEP is ~60 dB stopband.  Port target:
   `https://github.com/nesbox/blip-buf/blob/master/blip_buf.c`
   (~200 lines of C).  See `RESEARCH_ANTIALIAS.md` section 2-4.

3. Filter overshoot on note-on.  Butterworth 4-pole produces ~10%
   overshoot for 2-3 samples after a 0→full volume step.  This is a
   filter property, not a bug.  If audibly flagged, switch to 4-pole
   Bessel (critically-damped step response) or accept it as part of
   the "analog filter character".

## 10. Noise channel: what's going on in Battletoads

Orthogonal to the click problem, diagnosed this session:

Battletoads driver **never writes `$4015` bit 3 = 1** for the noise
channel.  Combined with Rule 30's noise gate (`vol > 0 AND enabled
AND length_counter > 0`), this silences the noise channel entirely.
Measured across all 12 Battletoads songs, 60 seconds each: 0 active
noise frames.  The `vol > 0` condition fires on 299/300 frames (vol
is written into `$400C`), but `enabled` is always 0.

**This is likely correct hardware behavior**: the NESDev wiki's APU
noise spec states the channel's output is `envelope × LFSR_bit ×
length_gate`, and `length_gate = length_counter > 0`.  The length
counter is only loaded when `$400F` is written AND `$4015` bit 3 is
set.  Battletoads never sets the bit, so on real hardware the noise
channel never produces output either.

Battletoads' drums appear to come from **DMC** (`$4011` DAC writes
and/or DPCM samples), not the noise channel.  Verified: DMC stem is
active (peak 0.07) while noise stem is silent.  Song 1 has 1
dpcm_trigger and no dac_writes in 10 s; other songs have similar
patterns.  This matches the common memory of Battletoads' drum
sound as sample-based, not LFSR-based.

**No fix needed**: the noise gating is hardware-accurate and the user
perceives the drums they expect because they come from DMC.

If a game IS expected to have noise drums but is silent in outputv6,
first step is to check $4015 writes and whether the driver loads the
noise length counter.  See `scripts/driver_survey.py` for CC11/CC12
classification; Family 1 (sparse envelope) games often manage noise
via length counter (SMB/Nintendo pattern in Rule 32), Family 2-4 vary.
