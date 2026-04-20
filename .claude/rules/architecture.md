---
description: Core architectural rules (always loaded). Task-specific rules in docs/ARCHITECTURE_REFERENCE.md.
globs:
  - "extraction/**"
  - "scripts/**"
---

# Architecture Rules (Core)

Universal invariants. For ROM-parsing rules (13-16), validation axes
(19), expansion/DPCM details (21-25), see `docs/ARCHITECTURE_REFERENCE.md`.
For gate checklists, see `docs/VALIDATION.md` (Gates A-F) and
`docs/VALIDATION_REFERENCE.md` (ladder, execution semantics).

## 1. Parsers Emit Full-Duration Events

`duration_frames = tempo * (nibble + 1)`. No staccato or envelope
shaping in the parser. All temporal shaping is Frame IR's job.

## 2. Manifests Before Code

Every new game needs a manifest in `extraction/manifests/` BEFORE
parser code. Declares mapper, pointer table, command format, facts vs hypotheses.

## 3. DriverCapability Dispatches Envelope Strategy

`driver.volume_model == "lookup_table"` — never `isinstance(parser, X)`.

## 4. Status Labels Are Mandatory

Every driver module: STATUS comment block after docstring.

## 5. Triangle Is Always 1 Octave Lower

32-step vs 16-step sequencer. `pitch_to_midi` subtracts 12 for triangle. Hardware fact.

## 6. Trace Is Ground Truth

After parser/frame_ir changes: `PYTHONPATH=. python scripts/trace_compare.py --frames 1792` → 0 mismatches.

## 7. Derived Timing Must Be Clamped

`max()` / `min()` on all computed timing. Example: `phase2_start = max(1, duration - fade_step)`.

## 8. Same Opcode ≠ Same Semantics

DX reads 2 bytes in CV1, 3/1 in Contra. Never copy command handling without checking.

## 9. Frame IR Is Mandatory (NON-NEGOTIABLE)

Trace → frame state → Frame IR → MIDI. No shortcuts. Direct period-to-note is a known failure mode.

## 10. Different ROMs Use Different Music Engines

Per-game profiles. No universal decoder. Record which assumptions succeeded/failed.

## 11. Snap Trace Periods to ROM Period Table

Interpretation decision belongs in Frame IR, not MIDI builder.

## 12. Three Layers Must Never Be Conflated

1. **Observed** (ground truth): raw APU registers. Authoritative.
2. **Intent** (parser interpretation): Frame IR. HYPOTHESIS until validated.
3. **Projection** (output): MIDI, RPP. PROVISIONAL until Intent passes gate.

## 17. Artifacts Must Carry Trust Labels

**Hypothesis output** (not validated) vs **Trusted output** (validated against ground truth). State scope.

## 18. Driver Family Is First-Class Infrastructure

Classify at ingest via CC11/CC12 density. 5 families drive validation depth, synth mode, NSF trust.
Run `scripts/driver_survey.py --game <slug>`. See CLAUDE.md for family table.

## 22. Period-to-Note Formula

Pulse: `CPU / (16 × (P+1))`. Triangle: `CPU / (32 × (P+1))`. CPU = 1,789,773 Hz.
Triangle octave offset is hardware, not convention.

## 26. NSF Bankswitch Emulation (Two Bugs, Both Proven)

The py65 NSF emulator must handle bankswitched NSFs correctly. Two bugs
burned an entire session before being caught (2026-04-14):

**Bug 1: Non-page-aligned load addresses shift bank boundaries.**
When `load_addr & 0xFFF != 0` (e.g. Ninja Gaiden $FC00, Zelda $8D60),
the ROM data is NOT padded to the page boundary. Bank N starts at
`rom_data[N * 4096 - padding]` where `padding = load_addr & 0xFFF`.
The emulator must build a virtual padded array before indexing banks.
Without this, higher bank numbers read past the end of ROM data into
zeros — INIT jumps to zeroed memory and hangs.

**Bug 2: $5FF6-$5FF7 bankswitch range.**
The full NSF bankswitch range is $5FF6-$5FFF, not just $5FF8-$5FFF.
$5FF6 → $6000-$6FFF, $5FF7 → $7000-$7FFF. Many drivers bankswitch
music data into $6000-$7FFF at runtime. Missing these writes caused
drivers to read zeros and hang.

**Impact:** Fixed 233/240 songs across 16 previously-failing games.
84% of NSF extraction failures were bankswitch-related.

Games proven affected: Ninja Gaiden (1→65), Zelda (2→37), CV3 (19→28),
Ninja Gaiden II/III, Zelda II, Captain Tsubasa, Lagrange Point,
Ganbare Goemon, Double Dribble, Kings Quest V, Mission Impossible.

## 27. Non-Linear APU Mixing Is Mandatory (Proven 2026-04-15)

The NES DAC uses impedance-based non-linear mixing. Linear mixing
(additive) is incorrect and makes simultaneous channels too loud.

**Two separate output pins with different transfer functions:**
- Pulse pin: `95.88 / ((8128.0 / (sq1 + sq2)) + 100.0)`
- TND pin: `159.79 / ((1.0 / (tri/8227 + noise/12241 + dpcm/22638)) + 100.0)`

**Key behavior:** Adding a second pulse compresses the first. Two pulses
at vol 15 produce ~0.278, not 2× one pulse (~0.184). This is not a
loudness cap — it's analog impedance interaction.

**Where implemented:**
- `render_wav()` via `_apu_nonlinear_mix()` — per-sample mixing
- `ReapNES_Console.jsfx` lines 451-471 — JSFX non-linear mixer
- `ReapNES_APU2.jsfx` lines 726-734 — already had this

**Prevention:** Never use `mix += channel_a + channel_b` for NES audio.
Always route through the non-linear formulas. If writing a new renderer,
the formulas are in `synth_fidelity.md` Rule 7.

## 28. DMC Is Two Mechanisms, Not One (Proven 2026-04-16)

The NES 2A03 DMC channel serves two distinct uses that must be
distinguished in the extraction pipeline:

**Mechanism 1: DPCM sample playback**
- Trigger registers: $4010 (rate+loop), $4012 (sample addr/64), $4013 (len/16+1)
- $4015 bit 4 enables
- Hardware DMA reads sample bytes from $C000+ and delta-decodes to 7-bit DAC
- Used for drum samples, speech clips, vocal effects

**Mechanism 2: Direct DAC writes**
- Software writes $4011 directly (7-bit value)
- No DMA, no sample
- Used for Sunsoft DPCM bass (Batman, Blaster Master, Journey to Silius,
  Gremlins 2), Battletoads algorithmic drums, and mixer bias adjustment

**Distinguishing rule** (implemented in `frames_to_channel_data`):
- If $4012 OR $4013 was written this frame → `event_type = "dpcm_trigger"`
- Else if $4011 was written this frame → `event_type = "dac_write"`
- Else → `event_type = "idle"`

**MIDI encoding** (MIDI channel 4 on track 5 "DMC [samples/DAC]"):
- dpcm_trigger: note_on at note 60 + rate_idx, velocity = DAC value
- dac_write: note_on at note 40 + (dac*60//127), re-triggered on DAC changes
- idle: any sustaining note is closed

**Impact when missing (prior state 2026-04-15):** All DPCM samples and
DAC-synthesized sounds silently dropped from MIDI and RPP output.
Sunsoft signature bass sound and Battletoads drums were absent.

**Prevention:** Any NSF extraction that reads $4000-$4017 must handle
$4010-$4013. The capture range already includes them — the bug is
forgetting to process them in `frames_to_channel_data()`. The `channels`
dict must include a `"dmc"` key and per-frame event_type classification.

See `docs/MULTI_CHIP_SCHEMA.md` Section 3 for the full event model.

## 29. Phase Reset, $4015, Sweep — Three Events Previously Dropped (Proven 2026-04-16)

Three APU behaviors the pipeline now captures that were previously lost:

**Phase reset** ($4003, $4007, $400B writes)
- Writing period-high for pulse1/pulse2 resets the pulse phase counter AND
  reloads the length counter. Same-pitch retriggers (arpeggios, staccato
  melodies) require this write to audibly re-attack.
- Writing $400B reloads the triangle linear counter and length counter.
- Without tracking this, same-pitch retriggers silently merge into one
  sustained MIDI note. W&W title theme had a game-specific workaround
  (`note_boundary_map`) that now generalizes via `phase_reset_frame`.

**$4015 channel enable**
- Bits 0-4 enable pulse1/pulse2/tri/noise/dmc length counters.
- Clearing a bit silences the channel — but most drivers (CV, Contra,
  Mega Man, many others) write $4015 once during init with $00 and rely
  on volume=0 for silencing. **Do NOT use $4015 as a per-note MIDI gate**
  — it will silence every frame on those drivers. Capture the bits in
  per-frame state for SysEx fidelity, but let volume-based gating drive
  MIDI note on/off.

**Pulse sweep unit** ($4001, $4005)
- Enable/period/negate/shift for pulse pitch modulation. Currently
  captured into per-frame state but not yet applied to MIDI pitch
  calculation. Future work: compute effective period per frame accounting
  for sweep shifts.

**Implementation rule**: Transient event flags (`phase_reset_frame`,
`dac_written_frame`, `trigger_frame`) MUST be reset to False after each
frame's state is recorded in the notes list. Forgetting the reset causes
every frame after the first event to be marked as an event frame.

**Prevention**: Any new frame-level event tracking follows the same
pattern: state dict has a flag, writes set it, recording reads it, reset
clears it. See `frames_to_channel_data()` for the canonical pattern.

**Impact**: Castlevania Vampire Killer triangle went from 139 → 163
naive notes (24 same-pitch retriggers recovered per 300 frames).
W&W title NSF extraction now matches trace-based ground truth within
a handful of notes — the generic phase_reset mechanism replaces the
game-specific note_boundary_map workaround.

## 30. Noise Channel $4015 Gate is NOT Optional (Proven 2026-04-18)

Unlike pulses and triangle (where most drivers rely on `vol=0` for
silencing and $4015 bits are written once at init), the **noise channel
in many games relies on $4015 bit 3** for active silencing.

- In W&W, noise bit 3 is NEVER set in any of the 16 songs, so hardware
  noise is completely silent. Without gating on `enabled`, the render
  generates continuous LFSR noise that does not exist in the Zophar
  reference. User feedback: "extremely noisy."
- SMB uses $4015 bit 3 briefly during drum hits; same behavior across
  many Nintendo/Capcom games.

**Rule:** In any rendering path (Python `render_wav`, JSFX plugin,
stems renderer), the noise channel's output MUST be gated by BOTH
`nv > 0` AND `fd["enabled"]`. Do not blanket-disable the enable check
the way we do for pulses/triangle.

See `scripts/render_channel_stems.py` keep=="noise" branch for the
canonical pattern. Do NOT apply this gate to pulses/triangle — those
still use `vol=0` for silencing across most drivers.

## 31. Audio Stems Are the Primary Deliverable Path (2026-04-18)

**Multi-track REAPER projects cannot reproduce the NES APU's non-linear
DAC mixing at the master-bus level.** Attempted solutions:
- Master-track FX block (REAPER syntax unreliable without live
  verification; broke multiple times)
- Bus track with AUXRECV + NES_MasterMixer JSFX (routing partially
  worked but bass was still +11 dB over reference)
- Per-channel attenuation + filter compensation (modest improvement,
  did not solve note-articulation issues)

**The stems approach supersedes these:** render per-channel audio via
`render_channel_stems.py`, load stems as audio tracks in REAPER,
keep MIDI tracks alongside for editing. This is the user-approved path.

**Rule:** When a user reports that a REAPER project "doesn't sound like
the game," the default response is not "fix the JSFX" but "render
hardware-accurate stems." The JSFX is useful for live keyboard play
only; it is not the primary audio path.

See `docs/STEMS_APPROACH.md` for the full architecture and
`scripts/batch_stems_project.py` for the per-game pipeline.

## 32. Noise Length Counter Is the Silencer for Many Drivers (Proven 2026-04-18)

Unlike pulses and triangle (where most drivers silence via `vol=0`), the
noise channel in a large class of drivers — Nintendo 1st-party (SMB, SMB2,
Zelda, Metroid, Kid Icarus), Capcom, many others — relies on the
**hardware length counter** to silence each drum hit, NOT on writing vol=0
and NOT on clearing $4015 bit 3.

Driver pattern:
- Write $400C once with const_vol=1 and vol=12 (env_loop=0 -> length counter enabled)
- For each drum hit: write $400E (period/mode) and $400F (length index)
- $400F load triggers: length_counter = LENGTH_TABLE[(val >> 3) & 0x1F]
- Length counter decrements twice per 60 Hz frame (two half-frame ticks)
- When length counter reaches 0, channel silenced

Without simulating this, SMB drums sound like "a wash of continuous
noise" because `vol > 0` and `$4015 bit 3 = 1` stay true for the whole
song.

**Capture rule** (implemented in `frames_to_channel_data()`):
- $400C bit 5 = env_loop (halts length counter when 1)
- $400F write: reload `length_counter` from LENGTH_TABLE if `enabled`
- $4015 bit 3 clear: force `length_counter = 0`
- Per frame AFTER recording: decrement by 2 unless halted or just-reloaded

**Render rule** (implemented in `render_channel_stems.py`):
- Noise gate: `nv > 0 AND enabled AND length_counter > 0`
- Fall back to the legacy 2-way gate when `length_counter` is missing
  (older captures — the field was added 2026-04-18).

**Impact**: SMB Overworld noise active frames dropped from 276/300 (92%,
continuous wash) to ~74/300 (25%, drum bursts with natural decay).

Generalizing to other channels: pulses and triangle also have length
counters, but most drivers set `env_loop=1` (halt) on them, so the counter
never decrements. Currently not simulated for those channels — add only
if a specific game reveals the bug.

## 33. Stems Need Analog LP + DC Blocker For DAW Playback (Proven 2026-04-18)

Raw hardware-accurate DAC output sounds correct on spectral metrics but
clicks audibly on every note when played in a DAW.  Two pipeline issues:

**Problem 1: Per-note click transients**
Instantaneous volume steps (vol 0 -> 15 in one sample on note-on) and
phase resets ($4003 write) produce hard amplitude steps.  Step functions
contain infinite-bandwidth content.  On the real NES, a ~14 kHz analog
RC filter smooths these.  libgme BLEP-synthesizes bandlimited waveforms
directly.  Our naive `np.where(pa < dv, vol, 0)` has neither.

**Fix**: 2-pole Butterworth LP at 14 kHz applied to each stem's DAC
output (`render_channel_stems.py::apply_nes_analog_lp`).  Measured effect
on Ghosts 'n Goblins s2: max sample-to-sample diff dropped from 0.563 to
0.356 (37% reduction in click magnitude).

**Problem 2: Silent regions biased off-zero**
`mix -= np.mean(mix)` DC-centers by subtracting the signal's mean.  When
the signal is asymmetric (e.g. drums on a noise stem - loud positive
transients, otherwise silent), silent regions end up at the negated-mean
offset, not at zero.  Every frame registers as "active" in a DAW even
when nothing should be playing.

**Fix**: proper 1-pole HP DC blocker at ~10 Hz
(`render_channel_stems.py::dc_block`).  Silent regions stay at true zero.

**Stem normalization scope**: the shared-scale pattern (one peak computed
from the sum of all stems, same factor applied to each) preserves
per-channel level proportions so noise doesn't dominate the mix.  Do not
revert to per-stem normalization.

## 34. Triangle Gate-Off Holds DAC Value (Proven 2026-04-18 evening)

When the triangle channel's linear counter OR length counter is zero, the
**hardware sequencer pauses at its current step and the DAC continues
outputting that step's value**.  This is NOT silence -- it is a held
DC level.  Per NESdev wiki (APU_Triangle):

> If either the linear counter or the length counter is zero, the
> sequencer is held at its current position.

Zeroing the wave on gate-off produces a step from the current sequencer
value (up to 15) down to 0, which -- combined with the non-linear TND
DAC -- creates a step of up to 0.26 in the raw output per gate transition.
Scaled by the shared-stem factor, this registers as a ~38% click that the
user perceives as a **vinyl-record-style pop**.

Battletoads song 1 produces 129 triangle gate transitions in 10 seconds
(triangle bassline staccato at ~14 Hz).  Game-wide, this is a recurring
artifact in any title whose driver uses linear-counter gating for
triangle bass articulation (most NES music).

**Render rule** (`render_channel_stems.py::render_stem`, `keep == "tri"`):
- When `tri_linear_live > 0`: render the wave as normal, advance phase.
- When `tri_linear_live == 0`: evaluate the wave at the CURRENT (frozen)
  phase and output that value for every sample of the frame.  Do NOT
  advance phase (matches HW sequencer pause).  The DC blocker then
  resolves the held level to silence over ~50 ms without any step.

**Measured impact**: triangle stem max single-sample step on
Battletoads s1 dropped 0.386 -> 0.006 (98.4% reduction).  Samples with
steps > 10% of peak: 1292 -> 0.  All triangle vinyl-pops eliminated.

**Prevention**: any new renderer path (JSFX, future C++ engines, etc.)
must hold the DAC on gate-off, not zero it.  Apply the same principle
to other channels if they ever need gating -- pulse/noise already
silence via `vol == 0` which is hardware-correct for those (pulse DAC
output = `seq_bit * vol` = 0 when vol = 0).

## 35. Bandlimited Pulse Synthesis Is Mandatory (Proven 2026-04-18 evening)

Naive point-sampling of a pulse wave (`np.where(pa < duty, vol, 0)`)
produces an infinite-bandwidth step function.  Content above Nyquist
(22.05 kHz at 44.1 kHz SR) folds back into the audible range as
**inharmonic grit** -- what the user perceived as "overdrive" on
sustained pulse notes.

A 2-pole Butterworth LP at 14 kHz (added in Rule 33) attenuates this
aliased content by only 12 dB/octave.  At high pulse pitches (>= 1 kHz),
residual aliased content is still -20 dBFS or louder -- clearly
audible as hiss/buzz.

**Render rule**: compute each sample's pulse value as the exact
time-averaged integral of the ideal pulse over the sample window:

```
fraction_high = (H(pa_end) - H(pa_start)) / (pa_end - pa_start)
where H(x) = duty * floor(x) + min(x - floor(x), duty)
```

`H(x)` is the antiderivative of `1{pa%1 < duty}` from 0 to x.  This
makes edges 3-level (0, partial, vol) instead of 2-level (0, vol),
which is equivalent to a rectangular-window anti-alias filter applied
analytically at the synthesis stage.

**Measured impact on Battletoads s1**:
- Pulse1 sample-steps > 10% of peak: 2641 -> 1682 (36% fewer).
- Pulse2 sample-steps > 10% of peak: 1993 -> 1302 (35% fewer).
- Clicks are no longer stacked at frame boundaries (0.4% at offset 0
  after fix vs 0% before fix -- redistribution, not concentration).

**Known limit**: 3-level edges still have broadband content.  Full
elimination of pulse aliasing requires either polyBLEP correction or
4x oversampling + decimation.  Current formula is the cheapest fix that
materially helps -- pursue oversampling if ear-tests still flag pulse grit.

**Triangle does NOT need this fix** -- the triangle wave
(`np.where(pa<0.5, pa*30, (1-pa)*30)`) is already continuous at all
phase points, so naive sampling does not produce step discontinuities
within the wave.  Only transitions into/out of gate need smoothing
(see Rule 34).

**LP order also bumped** in this session: 2-pole -> 4-pole Butterworth
at 14 kHz, giving 24 dB/octave rolloff instead of 12.  Note-on steps
now ring slightly (~10% overshoot for 2-3 samples after attack) which
is arguably part of the desired analog-filter character; if the
overshoot is audibly flagged, consider 4-pole Bessel (critically-damped
step response) as an alternative.

## 36. NSF Player Must Write $4015 = $0F Before INIT (Proven 2026-04-18 evening)

Per the NSF specification (nesdev.org/wiki/NSF), an NSF player is
required to **write `$4015 = $0F` and `$4017 = $40` before calling
INIT**.  The `$0F` enables all four standard APU channel length
counters (pulse1/pulse2/triangle/noise).  The `$40` disables frame
IRQ.  Every reference player does this (nsfplay, FamiTracker's GME
backend, libgme, FCEUX's NSF mode).

Our py65 NSF emulator was NOT doing this.  Memory was zeroed at reset
(line 196-197 of `nsf_to_reaper.py::play_song`), INIT was called
directly, and `$4015` read as `$00` at frame 0 via the memory-scan
fallback.  Result: `enabled = 0` for every channel in our captured
frame state, which under Rule 30's noise gate (`vol > 0 AND enabled
AND length_counter > 0`) silenced noise on **every driver that does
not re-enable $4015 itself**.

Drivers affected (confirmed silent noise before the fix, correct
noise activity after):

| Game | Before fix (active/1800) | After fix | Notes |
|------|-------------------------|-----------|-------|
| Castlevania | 0 | 573 (31%) | Vampire Killer drums restored |
| Kid Icarus | 0 | 193 (11%) | Sparse but correct |
| Wizards and Warriors | 0 | 790 (44%) | Major audible fix |
| Spy Hunter | 0 | 96 (11%) | Sunsoft driver |
| Battletoads | 0 | 449 (25%) | Layered drums with DMC |
| Kirby's Adventure | 0 | 504 (28%) | |
| Contra | 308 | 308 | Unchanged (driver writes $4015 itself) |
| Super Mario Bros | 280 | 280 | Unchanged (driver writes $4015 itself) |
| Gradius | 0 | 0 | Driver doesn't use noise in tested songs |
| Metroid | 0 | 0 | Same |

**Code location**: `scripts/nsf_to_reaper.py::NsfEmulator.play_song`,
immediately after `cpu.memory = CaptureMemory(...)` and before the
INIT `call(self.init_addr, ...)`:

```python
cpu.memory[0x4017] = 0x40
cpu.memory[0x4015] = 0x0F
```

These writes go through CaptureMemory so they appear in frame 0's
writes list, which is then processed by `frames_to_channel_data` to
set `enabled = 1` per channel.

**Prevention**: any new NSF player implementation (Python, JSFX, C++,
whatever) MUST write both registers before INIT.  Failing to do so
will silently break noise on ~30% of NES games and not flag any
errors because the NSF emulator "runs" fine -- the bug is just missing
audio output.

**Generalization**: NSF v2 also adds support for expansion chip init
regs ($4011, VRC6 $9000-$B002 status, etc.) that some players may
initialize.  For now we follow the strict v1 spec.  Expand this rule
if a game's expansion audio shows similar silencing patterns.

## 37. DPCM Trigger Requires $4015 Bit 4 Enabled (Proven 2026-04-18 late)

Hardware: writes to $4012 (sample address) and $4013 (sample length)
are **parameter latches only**.  They do NOT start DPCM playback.
Playback starts on the **rising edge of $4015 bit 4 (DMC enable)**
when sample_bytes_remaining is 0.

Prior behavior in `frames_to_channel_data()` fired
`trigger_frame=True` on any $4012/$4013 write, treating them as
sample-start events.  But most drivers **zero $4012/$4013 during
init** (housekeeping, not intent to play), producing one phantom
`dpcm_trigger` per song on frame 0 with default params
($4012=0 -> addr=$C000, $4013=0 -> len=1, rate_idx=0).

`render_dmc_stem()` then dutifully started a 1-byte DPCM playback
from $C000, reading whatever byte happens to be there (typically
non-zero), producing an audible DAC click on every track that opens
with a "really noisy" character on silent/quiet intros.

Games confirmed affected (all had phantom triggers before the fix):
Metroid (all 12 songs), likely Kid Icarus, and any game whose driver
zeroes DMC regs during init.

**Rule**: in `frames_to_channel_data`:
- $4012 write: update sample_addr; set `trigger_frame=True`
  **only if DMC is currently enabled** ($4015 bit 4 was last set to 1)
- $4013 write: same gating
- $4015 write: on rising edge of bit 4 (was 0, now 1),
  set `trigger_frame=True`.  On falling edge, DMC silences.

Unaffected channels:
- $4011 direct DAC writes (Rule 28 Mechanism 2, SMB/Battletoads drums)
  are **not** gated on enable — hardware allows direct DAC output
  regardless of bit 4.  Keep `dac_written_frame=True` on every $4011
  write.

Prevention: any future capture-layer handler for DMC-like chips
(VRC7 etc) must distinguish parameter latching from playback start.
Never fire a playback event on a register write alone — require an
explicit enable / trigger signal.

See `scripts/nsf_to_reaper.py::frames_to_channel_data` for the canonical
implementation.  Architecturally this supersedes Rule 28's
"$4012 OR $4013 written this frame -> event_type = dpcm_trigger"
with the enable-gated variant.

## 38. Disk Space Is a Hard Constraint (Proven 2026-04-18 + 2026-04-19)

**The project has filled C: drive to 100% TWICE.**  Once on
2026-04-18 (41 GB of outputv5 WAV/MP4 bloat), and again on
2026-04-19 when a 150-game rebuild at `--seconds 180` produced
138 GB of stems + 23 GB of SysEx-inlined RPPs + 25 GB of
`_nsf_extract/` intermediate artifacts.  Both incidents caused
mid-run failures, corrupted partial outputs, and required emergency
cleanup.

Disk space is not an abundant resource.  Treat it like a hard
budget.

**The three culprits**:

1. **Stem WAV size.**  5 stems × 180 s × 44.1 kHz × 2 bytes
   = ~16 MB per channel per song.  A full game with 20+ songs
   = 1.6 GB.  150 games = 240+ GB.  Render caps must be sized
   to budget.

2. **Intermediate `_nsf_extract/` artifacts.**  The sub-RPP that
   `nsf_to_reaper.py` produces for MIDI extraction can be 50+ MB
   per song because it inlines per-frame SysEx events (a 30-second
   song at 60 Hz produces ~18000 SysEx events, each a line in the
   RPP).  These sub-RPPs are NEVER opened by the user — only their
   `.mid` side-products are used.  They must be cleaned up after
   MIDI extraction, not kept.

3. **SysEx-inlined stems RPPs.**  `generate_stems_rpp.py` embeds
   all the MIDI's SysEx events directly in the RPP file instead
   of referencing the `.mid` file.  A 180-second 5-channel song's
   RPP ends up at 35 MB.  Across 150 games × 30 songs that's
   ~150 GB of RPP TEXT.

**Prevention rules** for any new batch-rendering code:

- **Estimate disk before starting.**  `render_all_nsfs.py` and
  `batch_stems_project.py` must print the expected disk footprint
  of the planned output and refuse to run if the estimate exceeds
  50% of free space.
- **Clean intermediates after use.**  Any helper tool that
  produces `_nsf_extract/`, `_scratch/`, or `_tmp/` artifacts must
  delete them after the derived final output is written.
- **Default to light output.**  `--wav-preview` flag on
  `nsf_to_reaper.py` is opt-in, not default (landed 2026-04-18).
  Any future render feature that produces WAV by default must be
  opt-in too.
- **Stems MUST reference not inline.**  `generate_stems_rpp.py`
  and any RPP generator that embeds SysEx must either reference
  the `.mid` file by path or emit SysEx in a format that doesn't
  multiply by every frame.  TODO: fix this.

**Pre-flight check** recommended before any batch render:

```python
import shutil
free_gb = shutil.disk_usage('.').free / (1024**3)
est_gb = estimated_output_size(games, seconds_per_song)
if est_gb > free_gb * 0.5:
    raise SystemExit(f"Need {est_gb:.1f} GB, only {free_gb:.1f} GB free. Halving.")
```

**Cleanup commands** for when it happens anyway:

```bash
# Remove all WAV stems (91 GB on 2026-04-19)
find . -name '*.wav' -type f -delete

# Remove intermediate sub-RPPs (25 GB on 2026-04-19)
find outputv6 -type d -name '_nsf_extract' -exec rm -rf {} +

# Remove SysEx-inlined stems RPPs (23 GB on 2026-04-19)
rm -rf outputv6/*/reaper

# Remove REAPER peak-cache files
find . -name '*.reapeaks' -delete
```

Disk incidents cost more than a few hours each time (aborted runs,
lost progress, emergency cleanup scripting, context window on
diagnosis).  Instrumenting pre-flight protects against recurrence
for 10-20 minutes of one-time code.

**Cross-references**: Rule 31 (stems are primary deliverable)
is the architectural origin of the disk-bloat class.  Future
`generate_rpp_variants.py`-style tools that ship Variant B
(MIDI+JSFX only, no stems) are the cheap path — 1 MB per RPP
vs 35 MB.
