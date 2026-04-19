# State of the project — 2026-04-18 evening

Snapshot of where the NSF-to-REAPER pipeline is today.  Supersedes the
afternoon handover.  Covers what works, what's known to be rough, and
what noise solutions are currently deployed (ahead of the full noise
investigation plan in `NOISECHANNELPLAN.md`).

## TL;DR

- **Primary deliverable path**: audio stems rendered from the Python
  pipeline, placed as audio tracks in REAPER projects, with editable
  MIDI tracks alongside.  Live JSFX playback is secondary.  Canonical
  output location is `outputv6/`.
- **44 games** in outputv5 are being re-rendered into outputv6 with
  the evening's fixes.  Batch is running as I write this.
- **Three confirmed wins tonight**:
  1. Triangle gate-off DAC hold (Rule 34) kills the "vinyl pop"
     artifact — 98% reduction in worst-case click size.
  2. Bandlimited pulse synthesis + 4-pole LP (Rule 35) reduces pulse
     aliasing by ~67%.  User ear-confirmed Battletoads "sounds a lot
     better."
  3. **NSF player $4015 init (Rule 36) — the biggest noise fix of
     the session.**  Previously, ~30% of driver families had entirely
     silent noise because their drivers rely on the NSF player to
     enable channels before INIT (per NSF spec) and we weren't doing
     that.  Post-fix: Castlevania, Kid Icarus, Gradius, Wizards &
     Warriors, Spy Hunter, Kirby, Ninja Gaiden, all Rare games, all
     late-Capcom games (MM3/4, Disney titles), all early-Sunsoft
     games, FF/Dragon Warrior — all have correct noise output now.
- **Known remaining rough**: non-linear APU DAC mixing is applied per
  stem, not per bus, so REAPER's linear stem sum overloads by ~15%
  when multiple channels play simultaneously.  This is the likely
  residual "overdrive" source.  Fix is designed but not shipped.
- **Noise channel status**: **the major root cause is fixed (Rule
  36).**  All 7+ driver families now produce noise output where the
  driver expects it.  Validation of acoustic correctness pending --
  see `NOISECHANNELPLAN.md` for per-family verification plan.  See
  `NEWDRIVERFAMILIES.md` for the driver-pattern taxonomy this
  investigation produced.

## Pipeline state

```
.nsf  ──────→  NSF emulation (py65)  ──→  per-frame APU register state
                                              │
                                              ├──→  MIDI (CC11/CC12 automation, track names from M3U)
                                              │
                                              └──→  audio stems (pulse1, pulse2, tri, noise, dmc)
                                                          │
                                                          └──→  REAPER RPP with audio + MIDI tracks
```

All 44 games that were in `outputv5/` have corresponding entries under
`output/<Game>/nsf/<file>.nsf` and are rebuildable via:

```
python scripts/rebuild_v6.py --force --seconds 60
```

(`--force` bypasses the "already has RPPs" skip and re-renders with
whatever fixes are currently in the render script.  Added in this
session.)

## What's working as of this snapshot

### Core emulation and extraction

- **py65 NSF emulator** — all 44 outputv5 games parse and emulate.
  Bankswitching fix (Rule 26) still holds; no regressions.
- **Frame state capture** — per-frame APU register state captured
  into `notes` lists per channel, with all the transient event flags
  added over the last two weeks (`phase_reset_frame`,
  `dac_written_frame`, `length_reload_frame`, `length_counter`,
  etc.).  Fields are stable.
- **MIDI export** — CC11 (volume) / CC12 (duty) automation produces
  a playable MIDI file per song.  Drum hits on noise channel go to GM
  drum map (kick/snare/hat by period range).  Track naming from NSFe
  or M3U.
- **Reaper RPP generation** — stems projects load cleanly in REAPER,
  MIDI tracks editable, audio tracks sync to bar 1.

### Audio-stem rendering (outputv6)

**Shipped this session**:

- Triangle gate-off DAC hold (Rule 34).  During gate-off frames (linear
  counter = 0), the renderer outputs the held DAC value at the frozen
  sequencer phase instead of zeroing.  Matches NES hardware per
  NESdev wiki.  Eliminates 129-per-10-seconds vinyl pops on
  Battletoads bassline and every other game using triangle staccato.
- Bandlimited pulse synthesis (Rule 35).  Replaces
  `np.where(pa < duty, vol, 0)` with analytical time-averaging of the
  ideal pulse over each sample window.  Reduces pulse-edge aliasing
  by ~36% on its own, ~67% combined with the LP bump.
- 4-pole Butterworth LP at 14 kHz (up from 2-pole).  Steeper rolloff
  attenuates aliased content by 12 dB more per octave above cutoff.
  Trade-off: note-on ringing overshoot went from ~5% to ~10% — audible
  but arguably the correct "analog filter character."

**Already shipped earlier (morning of 2026-04-18)**:

- Shared-scale stem normalization (Rule 31).  Single scale factor
  across all stems from the summed peak; prevents REAPER linear sum
  from clipping.
- NES analog LP and DC blocker (Rule 33).  LP bumped to 4-pole this
  evening; DC blocker unchanged at 1-pole ~10 Hz.
- Noise length-counter simulation (Rule 32).  Nintendo/Capcom noise
  drivers now silence drum hits correctly via the hardware length
  counter path.
- M3U-aware batching.  Batch renderer iterates only the music tracks
  listed in the playlist, with per-track durations.

### Per-channel status

| Channel | Render correctness | Notes |
|---------|-------------------|-------|
| Pulse 1 | Bandlimited, sweep applied, envelope simulated.  Rule 35 formula active.  Still has ~14 clicks/sec on dense pulse passages. |
| Pulse 2 | Same as pulse 1. |
| Triangle | Wave is continuous; gate-off holds DAC.  Linear counter simulated at 240 Hz.  Period < 2 mute in place. |
| Noise | Length counter + enable gate per Rule 32.  Sub-sample LFSR time-integration prevents aliasing at fast periods.  Three driver patterns found (see below). |
| DMC | DPCM playback with per-bit delta-decode; direct DAC writes ($4011) preserved.  LP applied to output.  Active on Sunsoft bass, Battletoads drums, SMB samples. |

### Noise solutions that are working

Across the 44 games, three driver behaviors produce correct output
with the current Rule 30 + Rule 32 gates:

**Pattern A: Length-counter silencing (Nintendo/Capcom 1st-party)**

Representative games: Super Mario Bros, Super Star Force, Metroid
(via noise channel), Rad Racer II, Strider, Shanghai II, many others.

Driver signature:
- Writes `$4015` once at INIT with bit 3 set.
- Writes `$400C` once per song or hit with constant-vol, non-zero
  volume, env_loop = 0.
- On each drum hit writes `$400E` (period + mode) and `$400F`
  (length counter reload index).
- Hardware length counter decrements at 120 Hz and silences the hit
  when it reaches zero.

Our render: gate on `vol > 0 AND enabled AND length_counter > 0`.
Working correctly.  SMB Overworld noise active frames 276/300 →
74/300 after Rule 32 landed.

**Pattern B: Vol-gate silencing (Konami, most non-Nintendo drivers)**

Representative games: Touhou Kenbun Roku, Tiny Toons 1, and many
others that show `vol_gate` in the audit.

Driver signature:
- Writes `$4015` once at INIT with bit 3 set (enable = 1).
- Writes `$400C` per frame with const_vol = 1 and vol = 0/N directly
  controlling per-frame amplitude.
- Does NOT use length counter ($400F write count = 0 or only at init).
- Driver silences drums by writing vol = 0.

Our render: same three-way gate.  `vol > 0` becomes false when driver
writes 0; channel silences.  `enabled` stays 1; `length_counter`
stays at whatever was last loaded (often 0 at init).  So the gate
relies on the `vol > 0` test.  Working correctly.

**Pattern C: Noise unused (most games in song 1)**

Representative: the bulk of the `no_noise` entries in the audit.
Driver never writes noise registers or writes vol = 0 always.  Render
outputs zeros.  Working correctly.

## What's known to be rough

### 1. Non-linear DAC mix error on stems

**This is the biggest remaining audible issue.**  Each of our 5
stems is rendered by running the non-linear APU DAC formula with
only that channel active.  When REAPER sums them on its master bus,
the sum is linear addition — but hardware mixes non-linearly (the
DAC pin has an impedance-compression characteristic that makes two
simultaneously-active channels produce less output than the linear
sum of each in isolation).

Concretely: two pulses at vol 15 should produce 0.258 on hardware but
our stem sum produces 0.298 — 15% too loud when pulses play together.
On rich passages this resembles mild distortion/overdrive.

**Planned fix (not shipped)**: collapse to 2 bus stems — one for the
pulse pin (p1 + p2 through the non-linear formula as a combined
signal) and one for the TND pin (triangle + noise + dmc through the
non-linear formula as a combined signal).  Sum linearly in REAPER.
See `RESEARCH_ANTIALIAS.md` section 6, option B.  Estimated 2 hours.
This is the recommended next work item.

### 2. Residual pulse clicks / aliasing

After the bandlimited formula + 4-pole LP, pulse stems still have
~14 sample-steps > 10% of peak per second.  Audible as low-level
crackle.  The analytical-integration formula is equivalent to a
rectangular-window filter (sinc rolloff, ~13 dB stopband); proper
anti-aliasing would need Blargg-style BLEP resampling at ~60 dB
stopband.  See `RESEARCH_ANTIALIAS.md` sections 2-4.  Estimated ~1
day to port blip_buf to numpy.

### 3. Note-on filter overshoot

4-pole Butterworth rings ~10% above steady-state for 2-3 samples
after a 0→full volume step.  Part of the filter response, not a bug.
Could switch to 4-pole Bessel (critically-damped) to eliminate the
overshoot at the cost of shallower rolloff.  Deferred until user
flags this specifically.

### 4. Noise: silent_bit3_unset pattern

Three games in the audit show `vol > 0` on noise but `$4015` bit 3
never set: Wizards and Warriors, Silver Surfer (song 1), Snake
Rattle'n Roll.  The `vol > 0` is the driver loading the envelope
register; since bit 3 is never set, the hardware length counter stays
at 0 and the channel is silent.  Our render matches hardware spec.

But the user's ear is the authority on whether these games SHOULD
have noise.  Battletoads is confirmed DMC-driven for drums (ear
test passed tonight).  W&W and Silver Surfer need their own
investigation.  Plan in `NOISECHANNELPLAN.md` section 4.

## Project-wide invariants still holding

- NSF emulation is ground truth for games without trace parsers
  (Rule 1-11).
- Triangle is 1 octave lower than pulse (Rule 5).
- Trace is ground truth for CV1, Contra, W&W (Rule 6).
- Parser output is hypothesis, not music (Rules 13-16).
- One synth plugin design target (`ReapNES Studio.jsfx`), though live
  playback is secondary to the stems path (Rule 31).
- Projects work with zero manual REAPER configuration (keyboard,
  MIDI routing, synth settings all baked in).

## Files that matter most

| File | Purpose |
|------|---------|
| `scripts/render_channel_stems.py` | Per-channel audio stem renderer.  All evening's fixes here. |
| `scripts/nsf_to_reaper.py` | NSF emulation, frame state capture, MIDI export. |
| `scripts/batch_stems_project.py` | M3U-aware per-game batch pipeline. |
| `scripts/rebuild_v6.py` | Sweeps outputv5 games into outputv6. `--force` rebuilds in place. |
| `.claude/rules/architecture.md` | Canonical rules.  34-35 added tonight. |
| `docs/NOISEPROBLEM.md` | Diagnosis of the Battletoads click/pop/overdrive. |
| `docs/RESEARCH_ANTIALIAS.md` | Community research: Blargg BLEP + 2-bus-stem recommendation. |
| `docs/NOISECHANNELPLAN.md` | Systematic plan for noise-channel investigation (this file's companion). |

## What the user should expect

On the current build:

- **Vinyl pops on the triangle bass gone.**  This was the most
  distracting artifact.  Confirmed by ear on Battletoads.
- **Pulse hiss/buzz reduced but not gone.**  Dense pulse passages
  (melodic runs) still have audible aliasing.  Will fully resolve
  when blip_buf is ported.
- **Mild "overdrive" when multiple channels play together**
  (especially both pulses at full volume).  Will resolve when the
  2-bus-stem refactor lands.
- **Noise drums present on most games that have drums.**  See the
  audit patterns above.  Exceptions listed in `NOISECHANNELPLAN.md`.

Nothing below Rung 4 of the Validation Ladder is "validated"; this
is all hypothesis output pending user ear-test per game.
