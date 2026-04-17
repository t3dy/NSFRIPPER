# NES Audio: Gaps, Failure Modes, and Next Steps

Gap analysis of the ReapNES Studio extraction pipeline. Identifies everything
the current model does NOT explain or cannot yet handle, and designs concrete
paths to incorporate those behaviors.

**Research date:** 2026-04-13
**Baseline:** 5 driver families, Frame IR, NSF emulation + partial Mesen trace,
CC11/CC12 density classification, 65-game survey, 30 game profiles.

---

## 1. Confirmed Model Coverage (What Is Solid)

These are not gaps. Do not re-derive.

| Capability | Status | Evidence |
|-----------|--------|----------|
| Standard APU (pulse, triangle, noise) | Solid | CV1/Contra at Rung 4, 0 pitch mismatches |
| CC11 as per-frame volume | Solid | Maps directly to $4000/$4004 bits 0-3 |
| CC12 as per-frame duty | Solid | Maps directly to $4000/$4004 bits 6-7 |
| Period-to-note conversion | Solid | Matches FamiTracker formula and NESDev wiki |
| Triangle octave offset | Solid | Hardware fact (32-step vs 16-step), -12 semitones |
| 5 driver families by CC density | Solid | Cross-validated against VGMPF attribution |
| NSF emulation pipeline | Solid | 1577 games processed, 65 surveyed |
| Frame IR for Konami games | Solid | CV1/Contra proven, W&W partial |
| SysEx register replay in MIDI | Solid | Lossless APU state encoding |
| REAPER project generation | Solid | Fully automated via generate_project.py |

---

## 2. Identified Gaps

### 2.1 Expansion Audio (CRITICAL — ~250+ games affected)

The pipeline handles ONLY the standard 2A03 APU. Six expansion audio chips
exist, affecting ~250+ Famicom titles. Our pipeline silently discards their
audio when processing NSFs with expansion flags.

#### VRC6 (Konami) — ~24 games

Two pulse channels (8 duty settings vs standard 4) plus sawtooth.
Registers at $9000-$9002, $A000-$A002, $B000-$B002.

**Model impact:**
- CC11 generalizes: VRC6 has 4-bit volume per pulse, same as APU
- CC12 BREAKS: VRC6 has 3-bit duty (8 settings), not 2-bit (4 settings).
  CC12 encoding (0-3 mapped from 0-127) cannot represent 8 duty values.
- Sawtooth has NO duty equivalent — it's a fundamentally different waveform.
  6-bit accumulator rate, not duty-cycle modulation.
- Frame IR needs: `channel_type: "vrc6_pulse" | "vrc6_saw"` with extended
  duty range and accumulator rate field

**Games affected:** Akumajou Densetsu (CV3 JP), Esper Dream 2, Madara,
and ~21 other Konami Famicom titles. These are among the most musically
sophisticated NES games — high priority.

#### VRC7 (Konami) — 1 game (Lagrange Point)

6-channel FM synthesis based on YM2413/OPLL. Two-operator FM with
15 preset instruments + 1 custom. Registers via $9010/$9030.

**Model impact:**
- CC11/CC12 model COMPLETELY BREAKS. FM synthesis uses modulator/carrier
  architecture with per-operator ADSR, key-level scaling, frequency
  multipliers, feedback, and waveform selection.
- Frame IR cannot represent FM parameters. Would need:
  `fm_instrument`, `fm_volume` (inverted 4-bit, 3dB steps),
  `fm_key_on`, `fm_octave`, `fm_freq`
- MIDI representation: could map to standard note+velocity since VRC7
  has built-in envelopes, but timbral information (instrument select)
  needs a CC or program change.

**Priority:** Low (1 game). But architecturally interesting — tests
whether our model can handle non-APU synthesis.

#### FDS (Famicom Disk System) — ~200 games

64-sample, 6-bit wavetable channel with hardware frequency modulation
(vibrato/tremolo). Registers at $4040-$407F (wave RAM), $4080-$408A.

**Model impact:**
- CC11 partially applies: FDS has volume gain (0-63, clamped at 32).
  Maps to CC11 but with 6-bit precision, not 4-bit.
- CC12 DOES NOT APPLY: no duty cycle. Timbre comes from wavetable shape
  (64 samples × 6 bits), not duty selection.
- Modulation unit is unique: frequency modulation via 32-entry mod table
  with its own frequency and counter. Produces vibrato/tremolo effects
  that have no APU equivalent.
- Frame IR needs: `channel_type: "fds"` with `wave_table[64]`,
  `mod_table[32]`, `mod_freq`, `mod_counter`, `volume_gain`
- Output is ~2.4x louder than a single APU pulse — mixing implications.

**Games affected:** Zelda, Metroid, Kid Icarus, Doki Doki Panic,
Akumajou Dracula (CV1 JP), and ~195 other FDS titles. MAJOR gap
since these include some of the most iconic Nintendo soundtracks.

**Caveat:** FDS games are Famicom-only. NES cartridge versions lack
FDS audio. Our joshw.info NSFs may contain FDS audio if the NSF has
the expansion flag set, but our synth cannot play it.

#### MMC5 — ~20 games (3 use audio)

Two pulse channels (identical to APU pulse but no sweep unit) plus
8-bit PCM. Registers at $5000-$5015 mirror APU layout.

**Model impact:**
- CC11/CC12 model APPLIES DIRECTLY for the pulse channels.
  Same duty, same volume, same period formula.
- Only difference: no sweep unit, inverted output polarity.
- PCM channel ($5011) is an 8-bit DAC — similar to $4011 but higher resolution.
- Frame IR: `channel_type: "mmc5_pulse"` (trivial extension of APU pulse)

**Priority:** Low (only 3 games use music: Just Breed, Metal Slader Glory,
Shin 4 Nin Uchi Mahjong).

#### Namco 163 — ~19 games

1-8 wavetable channels sharing 128-byte internal RAM. 4-bit samples,
configurable waveform length and address. Volume 0-15 per channel.

**Model impact:**
- CC11 generalizes: 4-bit volume like APU.
- CC12 DOES NOT APPLY: timbre from wavetable shape, not duty.
- Unique constraint: more channels = lower sample rate per channel.
  8 channels → ~14.9 kHz update rate → audible aliasing noise.
- Frame IR needs: `channel_type: "n163"` with `wave_addr`, `wave_len`,
  `wave_data[]`, `num_channels`
- RAM layout conflict: waveform data and channel registers share the
  same 128-byte space. Reducing channels frees RAM for longer waveforms.

**Priority:** Medium (19 games, mostly Namco-published Japanese titles).

#### Sunsoft 5B (YM2149F) — 1 game (Gimmick!)

3 square channels + noise generator + hardware envelope generator.
Registers via $C000/$E000 mapped to YM2149 internals (16 registers).

**Model impact:**
- CC11 generalizes: 4-bit volume per channel.
- CC12 DOES NOT APPLY: no duty cycle. Square wave only.
- Has HARDWARE envelope generator with 16 shapes (ramp, triangle,
  sawtooth, hold). Produces 5-bit volume output at configurable rate.
  No APU equivalent — this is a dedicated envelope chip.
- Mixer register ($07) enables/disables tone and noise per channel
  independently. Both enabled = logical AND.
- Period formula differs: `f = CPU_CLK / (32 * period)` with NO +1.
  Period 0 = period 1 behavior.
- Frame IR needs: `channel_type: "5b"` with `tone_enable`, `noise_enable`,
  `envelope_enable`, `envelope_shape`, `envelope_period`

**Priority:** Low (1 game). But Gimmick! is musically exceptional and
a preservation target.

#### Proposed Unified Multi-Chip Abstraction

```
FrameState:
  chip: "2a03" | "vrc6" | "vrc7" | "fds" | "mmc5" | "n163" | "5b"
  channel_type: "pulse" | "triangle" | "noise" | "dmc" |
                "vrc6_pulse" | "vrc6_saw" |
                "vrc7_fm" |
                "fds_wave" |
                "mmc5_pulse" | "mmc5_pcm" |
                "n163_wave" |
                "5b_square"
  # Standard fields (all chips)
  period: int
  volume: int
  sounding: bool
  
  # Pulse-family fields (2a03, vrc6, mmc5)
  duty: int           # 0-3 (2a03/mmc5) or 0-7 (vrc6)
  sweep: SweepState   # 2a03 only
  
  # Wavetable fields (fds, n163)
  wave_data: bytes    # waveform samples
  wave_length: int
  
  # FM fields (vrc7)
  fm_instrument: int  # 0-15
  fm_octave: int
  fm_key_on: bool
  
  # PSG fields (5b)
  tone_enable: bool
  noise_enable: bool
  envelope_enable: bool
  envelope_shape: int
  
  # Accumulator fields (vrc6 saw)
  accum_rate: int     # 0-63
```

### 2.2 DPCM/DAC ($4011) — IMPLEMENTED (2026-04-16)

Status: DONE for NSF→MIDI extraction. The pipeline now distinguishes
`dpcm_trigger` (sample playback via $4012/$4013) from `dac_write`
(direct $4011 writes). Both map to MIDI track 5 on channel 4. See
`architecture.md` Rule 28 and `MULTI_CHIP_SCHEMA.md` Section 3.

Historical context (pre-2026-04-16):
The DMC channel was the pipeline's weakest point. Register writes were
captured via SysEx but never interpreted in Frame IR or CC encoding —
Sunsoft bass, Battletoads algorithmic drums, and all sample-based
percussion were silently dropped from MIDI/RPP output.

#### Two distinct mechanisms conflated

1. **DPCM sample playback** ($4010-$4013):
   - Set rate ($4010 bits 0-3, 16 rates from 4182-33144 Hz)
   - Set address ($4012 → $C000 + A×64) and length ($4013 → L×16+1 bytes)
   - Enable via $4015 bit 4
   - DMA fetches sample bytes, each bit shifts 7-bit output ±2
   - Used for: drum samples, vocal clips, sound effects

2. **Direct DAC writes** ($4011):
   - Write 7-bit value directly to output level, no DMA
   - Used for: algorithmic synthesis (Battletoads drums), crude waveforms,
     speech synthesis, mixing bias adjustment

**Current pipeline behavior:** Both mechanisms produce the same
$4011 output in APU state captures. The pipeline cannot distinguish
between "DPCM sample is playing" and "driver is writing computed values."

#### Known techniques requiring modeling

**Sunsoft DPCM bass:**
- 5 pre-recorded samples (A#, B, C, C#, D) from AKAI S700 sampler
- Mapped across bass range via rate selection
- Frees triangle channel for melody
- Games: Blaster Master, Batman, Journey to Silius, Gremlins 2
- Event model: `sample_trigger(address, length, rate, note)`

**Battletoads algorithmic drums:**
- No stored samples. Driver computes ramp waveforms and writes to $4011
- Variable speed/length creates kick, snare, hi-hat
- Event model: `dac_ramp(start_value, end_value, rate, duration)`
- Cannot be represented as DPCM sample playback

**$4011 mixing bias:**
- Non-zero $4011 value affects triangle/noise perception through
  non-linear TND mixer formula
- Some games deliberately set $4011 to adjust mix balance
- This is a side effect, not an intended audio event

#### Required Frame IR extensions

```
event_type: "dpcm_trigger" | "dac_write" | "dac_ramp"

# For DPCM sample playback
dpcm_rate_index: int     # 0-15 (maps to Hz via rate table)
dpcm_address: int        # sample start ($C000 + offset)
dpcm_length: int         # sample length in bytes
dpcm_loop: bool

# For direct DAC
dac_value: int           # 0-127 (7-bit)

# For algorithmic synthesis (Battletoads-style)
dac_ramp_start: int
dac_ramp_end: int
dac_ramp_frames: int
```

#### MIDI representation problem

DPCM has no natural MIDI equivalent:
- Sample playback → could map to MIDI note-on with sample index
- Algorithmic DAC → no MIDI representation. Would need SysEx.
- Sunsoft bass → could map to MIDI notes on a dedicated channel
  with sample rate encoded as CC

**Proposed:** Add MIDI channel 5 (index 4) for DPCM, with:
- Note number = sample index or pitch
- Velocity = initial volume (from $4011 value)
- CC13 = DPCM rate index (0-15)
- SysEx for raw $4011 sequences (algorithmic synthesis)

### 2.3 NSF vs In-Game Divergence

The pipeline trusts NSF as ground truth for most games. This is sometimes
wrong. Categories of divergence:

#### Category 1: Frame counter ($4017) differences

NSF players typically write $4017 = $40 (4-step mode, no IRQ) before
calling PLAY. But some games use 5-step mode ($4017 = $80) or expect
specific $4017 state. This affects:
- Envelope timing (240 Hz vs 192 Hz effective rate)
- Sweep timing
- Length counter behavior

**Detection:** Compare $4017 writes in NSF emulation vs Mesen trace.
If the game writes $4017 every frame, the NSF player's initial write
is overridden and doesn't matter. If the game never writes $4017,
the NSF player's assumption determines timing.

#### Category 2: Initialization differences

NSF INIT is called once with song number in A register. Some games:
- Initialize audio over multiple frames (not one call)
- Depend on game state (memory layout, bank configuration)
- Use non-returning INIT (NSF2 paradigm: INIT runs continuously,
  PLAY arrives as NMI)

**Affected games:** Rollerblade Racer (confirmed NSF2-required).
Any game with complex sound driver initialization.

#### Category 3: Game-state-dependent music

Some games modify music based on gameplay:
- Health-dependent tempo (low health = faster music)
- Dynamic channel muting (cutscenes, transitions)
- Adaptive mixing (more action = louder percussion)
- Cross-fade between tracks

NSF captures a static version — no gameplay context.

**Affected games:** Most RPGs (battle transitions), action games with
adaptive music, games with dynamic sound effects competing for channels.

#### Category 4: DMA timing conflicts

DPCM DMA steals 1-4 CPU cycles per byte fetched. This can:
- Cause timing jitter in the sound driver
- Corrupt controller reads ($4016/$4017)
- Affect APU register write timing

In NSF playback, DPCM DMA occurs but the timing impact differs because
there's no game code competing for CPU time.

#### Category 5: Proven divergent games

| Game | Divergence Type | Evidence |
|------|----------------|---------|
| Super Mario Bros | Tempo/timing | Our own comparison, confirmed by community |
| Battletoads | Multiple | Complex driver state, algorithmic PCM timing |
| Contra | Minor | DMA timing differences in DPCM-heavy sections |
| Gradius | Data anomaly | CC11/note of 26.2 — likely extraction artifact |

#### Trust Classification

| Trust Level | Criteria | Family Correlation |
|------------|---------|-------------------|
| **High** | Simple driver, no DPCM, no game-state deps | Families 1-3, most games |
| **Suspect** | Dense automation, DPCM usage, complex driver | Family 4, some Family 2 |
| **Unusable** | Requires NSF2, broken rip, game-state-critical | Rare cases |

**Detection heuristic:** Run driver_survey.py. If CC11/note > 10 AND
the game uses DPCM (NSF header expansion byte), flag as suspect.
Cross-validate with VGM if available.

### 2.4 Incomplete APU Event Coverage in Frame IR

Current Frame IR captures: period, volume, duty, sounding, plus recently
added sweep/noise_mode/dac/const_vol fields. What's still missing:

#### Phase reset events

Writing $4003/$4007 resets the pulse phase sequencer. This causes an
audible click/pop, especially when re-triggering at the same pitch.
The click is intentional in some games (percussive attack) and a
bug in others.

**Impact:** Same-pitch retriggers are invisible in period-only tracking.
The W&W ROM parser already handles this via `note_boundaries`, but
the Frame IR doesn't have a first-class `phase_reset` event.

#### Length counter state

The APU length counter gates channel output after a set duration.
Writing $4003/$4007 loads the counter from a lookup table (32 entries).
When the counter reaches 0 and length counter halt bit is 0, the
channel silences.

**Impact:** Some games use length counters for note duration instead of
explicit volume-to-zero writes. The Frame IR doesn't track whether a
channel was silenced by the driver or by the length counter expiring.

#### Envelope divider state

When const_vol = 0 ($4000 bit 4), the APU's internal envelope unit
produces a linear decay from 15 to 0 at a rate determined by bits 0-3.
The current Frame IR captures the result (volume) but not the mechanism
(hardware decay vs software write). The `const_vol` field was recently
added but not yet used in any pipeline stage.

#### $4015 channel enable/disable

Writing to $4015 can instantly silence or re-enable channels. A game
that writes $4015 = $00 silences everything; $4015 = $0F enables all
melodic channels. The Frame IR doesn't track $4015 writes.

**Impact:** Channel enable/disable events can explain sudden silences
that are not accompanied by volume-to-zero writes.

#### Complete proposed event taxonomy

```
# Core events (currently captured)
note_on          # period change + sounding = true
note_off         # volume = 0 or sounding = false
envelope_change  # volume change within a note
duty_change      # duty cycle change within a note

# Extended events (partially captured, need completion)
phase_reset      # $4003/$4007 write (click/retrigger)
sweep_config     # $4001/$4005 write (enable/parameters)
sweep_tick       # period adjusted by sweep unit (auto-generated)
noise_mode       # $400E bit 7 change (tonal vs hissy)
channel_enable   # $4015 write enabling channel
channel_disable  # $4015 write disabling channel

# DPCM events (new)
dpcm_trigger     # $4015 bit 4 set with loaded address/length
dpcm_stop        # $4015 bit 4 cleared or sample exhausted
dac_write        # $4011 direct value write

# Frame counter (new)
frame_counter_mode  # $4017 write (4-step vs 5-step)

# Expansion events (new, per-chip)
vrc6_duty_change # 3-bit duty (0-7) for VRC6 pulse
fds_wave_load    # wavetable RAM update
fds_mod_change   # modulation parameter change
n163_wave_select # waveform address/length change
vrc7_key_event   # FM key on/off + instrument select
```

### 2.5 Driver Sub-Families and Secondary Classification

CC11/CC12 density identifies 5 families. But within each family,
games exhibit distinct sub-patterns that CC density alone doesn't capture.

#### Within Family 1 (Hardware Envelope)

| Sub-pattern | CC11/note | Distinguishing Feature |
|-------------|-----------|----------------------|
| True minimal | < 0.5 | Driver writes volume ONCE, never updates |
| Light automation | 0.5-2.8 | Occasional per-note volume adjustment |

True minimal games (W&W at 0.1, MM1 at 0.2) rely entirely on $4000
bit 5 = 0 (hardware decay). Light automation games (MM3 at 3.7, Strider
at 1.0) use constant volume mode with sparse manual writes.

**Distinguishing metric:** Check $4000 bit 4 (const_vol). If mostly 0
across a game → true hardware envelope. If mostly 1 → software-controlled
but sparse.

#### Within Family 2 (Standard Envelope)

| Sub-pattern | Envelope Shape | Example |
|-------------|---------------|---------|
| Punch-decay | Vol 15 → rapid decay → sustain 4-8 | CV1, Contra |
| Fade-out | Gradual linear decay to 0 | Ninja Gaiden |
| Tremolo | Oscillating volume during sustain | Some Tecmo games |

**Distinguishing metric:** Analyze the CC11 value sequence after each
note_on. Compute the variance of CC11 values within the sustain portion
(frames 4+ after attack). High variance = tremolo. Low variance with
final value > 0 = punch-decay. Final value = 0 = fade-out.

#### Within Family 4 (Dense Automators)

| Sub-pattern | CC11/note | Distinguishing Feature |
|-------------|-----------|----------------------|
| Sunsoft-style | 7-12 | Per-frame volume with DPCM bass |
| Square-style | 12-15 | Obsessive volume, NO DPCM, static duty |
| Multi-update | > 10 | Multiple $4000 writes per frame |

**Distinguishing metric:** DPCM usage (present/absent) + CC12 density.
Sunsoft games use DPCM bass, Square games don't. Both are dense on CC11
but for different musical reasons.

#### Proposed secondary features

Beyond CC11/CC12, these metrics distinguish driver behavior:
1. **Note density** (notes/second): sparse (< 5) vs dense (> 15)
2. **Arpeggio index** (period changes within 2-frame windows)
3. **Duty diversity** (how many distinct duty values per song)
4. **Channel utilization** (% of frames with all 4 channels active)
5. **Rest ratio** (% of frames with volume = 0)
6. **DPCM activity** ($4015 bit 4 toggle rate)

### 2.6 ROM-Level Parsing Priority

Current ROM parsers: Konami (CV1, Contra), Rare (W&W, Battletoads).
Covers ~10 games. Strategy for expanding coverage:

#### Priority 1: Capcom 6C80 Engine (~30 games)

Romhacking.net document #274 provides complete byte-level specification
for Mega Man 3+, DuckTales, Darkwing Duck, Chip 'n Dale, Little Mermaid,
Mighty Final Fight, and ~20 more.

**Why highest priority:**
- All Capcom games are Family 1 (Hardware Envelope) — simplest to validate
- One parser covers 30+ games — best coverage-to-effort ratio
- Byte-level format doc already exists — no reverse engineering needed
- Low CC11 density → fewer edge cases in execution semantics

**Estimated effort:** Medium. The format doc is thorough. Main work is
implementing the command parser and connecting to our manifest/Frame IR
infrastructure.

**A separate "Sound Engine 1" doc (romhacking.net #875) covers earlier
Capcom titles (MM1-2, 1942, Commando). Combined: ~35 games.**

#### Priority 2: Sunsoft Engine (~15 games)

Romhacking.net document #665 provides analysis of Sunsoft audio engines.

**Why high priority:**
- Sunsoft games are Family 4 (Dense Automators) — the family most
  likely to have NSF divergence issues
- DPCM bass technique needs ROM-level understanding to model correctly
- Direct ROM parsing would let us extract sample data for the synth

#### Priority 3: Nintendo Internal Engines (~40 games)

No published format documentation. Would require reverse engineering
from disassemblies. The cyneprepou4uk/NES-Games-Disassembly repo has
26 games including Zelda.

**Why medium priority:**
- Nintendo games span Families 3-5 — diverse and complex
- Multiple internal driver variants (Kondo, Tanaka, Kaneoka)
- No single parser would cover all Nintendo games

#### Priority 4: Tecmo "Super Sound Machine" (~15 games)

No published documentation. Ninja Gaiden series, Rygar, Tecmo Bowl.

#### Coverage Estimate

| Engine | Games | Difficulty | Doc Available? | Priority |
|--------|-------|-----------|---------------|----------|
| Capcom 6C80 + SE1 | ~35 | Medium | Yes (RH #274, #875) | 1 |
| Sunsoft | ~15 | Medium | Partial (RH #665) | 2 |
| Konami (existing) | ~30 | Done/Hard | Partial | Done |
| Rare (existing) | ~48 | Done/Hard | No | Done |
| Nintendo | ~40 | Hard | No (disassemblies) | 3 |
| Tecmo | ~15 | Hard | No | 4 |
| HAL Laboratory | ~10 | Hard | No | 5 |
| Square | ~5 | Hard | No | 6 |

**Combined with NSF fallback:** ROM parsers for Priority 1-2 would
give us validated ROM-level extraction for ~80 games + NSF emulation
for all 1577. The NSF pipeline already handles all games — ROM parsing
adds fidelity, not coverage.

### 2.7 Mixing Model (IMPLEMENTED 2026-04-15)

Real NES uses non-linear impedance-based mixing. This is now
implemented in all three renderers (render_wav, ReapNES_Console.jsfx,
ReapNES_APU2.jsfx). Formulas documented below for reference.

#### Pulse pin (confirmed from FamiTracker source + NESDev wiki)

```
pulse_out = 95.88 / ((8128.0 / (pulse1 + pulse2)) + 100.0)
```

Key behaviors:
- One pulse at 15: output ~0.184
- Both at 15: output ~0.278 (not 0.368 = 2 × 0.184)
- Adding second pulse REDUCES first's effective contribution
- Compression is most audible when both channels are loud

#### TND pin

```
tnd_out = 159.79 / ((1.0 / (tri/8227.0 + noise/12241.0 + dmc/22638.0)) + 100.0)
```

Key behaviors:
- DPCM output level ($4011) affects triangle/noise perception
  even when no sample is playing
- Non-zero $4011 default shifts the TND mix baseline
- Triangle at max (15) + noise at max (15) ≠ 2× either alone

#### Lookup table approach (from NESDev wiki)

```
pulse_table[n] = 95.52 / (8128.0 / n + 100)    # n = p1 + p2, 0-30
tnd_table[n] = 163.67 / (24329.0 / n + 100)    # n = 3*tri + 2*noise + dmc
```

Approximates within 4% of exact formulas. 31 + 203 = 234 table entries.

#### Linear approximation (current JSFX approach)

```
pulse_out ≈ 0.00752 * (pulse1 + pulse2)
tnd_out ≈ 0.00851 * tri + 0.00494 * noise + 0.00335 * dmc
```

**Error:** Up to ~15% at high amplitudes. Most audible on tracks with
both pulses at high volume simultaneously (common in Castlevania,
Mega Man melodic sections).

#### Hardware filters (not modeled)

The NES has analog filters on the audio output path:
- High-pass ~37 Hz (removes DC offset)
- High-pass ~14 Hz (coupling capacitor)
- Low-pass ~14 kHz (anti-aliasing)

These affect bass response and high-frequency content. Currently
not modeled in the JSFX synth.

#### Expansion chip mixing

Each expansion chip mixes with the base APU through the Famicom
cartridge connector's expansion audio pin. The mixing ratios are
chip-dependent and not standardized:
- VRC6: ~6 dB below base APU
- VRC7: separate 3.58 MHz clock, ~3 dB below
- FDS: ~2.4× louder than single APU pulse
- MMC5: approximately equal to base APU (inverted polarity)
- N163: +11 to +19.5 dB louder (submapper-dependent)
- 5B: YM2149 external output

**Impact on synth:** Each expansion chip needs its own volume scaling
relative to the base APU. The non-linear mixing formulas only apply
within the base APU — expansion chips mix linearly with the combined
APU output.

### 2.8 Validation Strategy Gaps

#### Current validation coverage

| Source | Resolution | Games | Independence |
|--------|-----------|-------|-------------|
| NSF emulation | 60 Hz | All 1577 | N/A (is the pipeline) |
| Mesen trace | 60 Hz (frame) | ~5 | Fully independent |
| VGM (new tool) | 44100 Hz | Hundreds | Partially (NSF-sourced VGMs inherit NSF issues) |
| NES-MDB | 24 Hz | 397 | Fully independent (assembly-parsed) |

#### Missing: systematic cross-validation

The pipeline has tools for each source but no automated cross-validation
workflow. Needed:

1. **Temporal alignment** — different frame rates (60 Hz, 44100 Hz, 24 Hz)
   must be aligned to a common timeline before comparison
2. **Disagreement classification** — when sources disagree, automatically
   categorize: timing offset, missing events, value mismatch, structural
3. **Confidence scoring** — per-game confidence based on source agreement
4. **Batch comparison** — run across all 397 NES-MDB games automatically

#### Missing: VGM provenance tracking

VGMRips packs don't always document whether the VGM was logged from:
- NSF emulation (inherits NSF inaccuracies)
- MAME/gameplay (fully independent)
- Modified ROM (may have hacks)

Without provenance, VGM cross-validation can give false confidence
(comparing NSF output against NSF-derived VGM).

---

## 3. Failure Case Catalog

Specific games or behaviors where the current model fails or produces
incorrect output.

| Game | Failure | Root Cause | Fix Path |
|------|---------|-----------|----------|
| Akumajou Densetsu (CV3 JP) | VRC6 channels silently dropped | No expansion audio support | Implement VRC6 in Frame IR + synth |
| Gimmick! | 5B channels silently dropped | No expansion audio support | Implement 5B in Frame IR + synth |
| Lagrange Point | VRC7 channels silently dropped | No expansion audio support | Implement VRC7 in Frame IR + synth |
| FDS games (~200) | FDS wavetable channel dropped | No expansion audio support | Implement FDS in Frame IR + synth |
| Battletoads | Drums misrepresented | $4011 algorithmic PCM not modeled | Add dac_ramp event type |
| Sunsoft games (4+) | Bass channel incomplete | DPCM sample playback not in Frame IR | Add dpcm_trigger event |
| Gradius | CC11/note = 26.2 (anomaly) | Likely extraction bug | Re-extract, validate against VGM |
| SMB1/SMB3 | NSF diverges from game | Frame counter and init differences | Cross-validate with Mesen trace |
| Final Fantasy | MIDI files very large | 14.9 CC11/note → massive CC stream | Consider CC thinning for Family 4 |
| Games with sweep | Pitch slides not captured | Sweep unit modifies period automatically | Track sweep state in Frame IR |
| Games with length counter | Unexpected silences | Length counter expires, no volume write | Track $4015 and length state |
| Same-pitch retriggers | Notes merged | Phase reset ($4003 write) not tracked | Add phase_reset event |

---

## 4. Required Model Extensions

### 4.1 Multi-Chip Audio State (Priority: HIGH)

Extend the pipeline to handle NSFs with expansion audio flags:
- Parse expansion byte from NSF header ($07B)
- Capture expansion chip register writes alongside APU
- Add channel types for each chip to Frame IR
- Extend MIDI format to include expansion channels (channels 5-12)
- Extend synth to render expansion audio (long-term)

### 4.2 DPCM Event Model (Priority: HIGH)

Add first-class DPCM handling:
- Distinguish sample playback from direct DAC writes
- Track $4012/$4013 (sample address/length) in capture
- Detect algorithmic PCM patterns ($4011 ramp sequences)
- Add MIDI channel 5 for DPCM events
- Model mixer interaction ($4011 affecting TND output)

### 4.3 Complete APU Event Coverage (Priority: MEDIUM)

Add missing event types to Frame IR:
- Phase reset (critical for same-pitch retriggers)
- Channel enable/disable ($4015)
- Length counter state
- Sweep unit state changes
- Frame counter mode ($4017)

### 4.4 Non-Linear Mixing in Synth — IMPLEMENTED (2026-04-15)

Status: DONE. Formulas (not lookup tables) implemented in three places:
- `scripts/nsf_to_reaper.py` — `_apu_nonlinear_mix()` function, per-sample mixing in `render_wav()`
- `studio/jsfx/ReapNES_Console.jsfx` lines 451-476 — replaced linear additive mixing
- `studio/jsfx/ReapNES_APU2.jsfx` lines 726-734 — already had this before

See `architecture.md` Rule 27 for the formulas and prevention guidance.
See `synth_fidelity.md` Rule 7 for implementation status and slider interaction.

Still open (lower priority):
- Per-chip volume scaling for expansion audio (VRC6/FDS loudness relative to APU)
- Hardware low-pass filter modeling

### 4.5 NSF Divergence Detection (Priority: LOW)

Automated heuristics to flag suspect NSFs:
- Check for $4017 writes in capture vs expected behavior
- Compare track duration vs expected from M3U
- Flag games with DPCM usage + dense automation
- Cross-reference against known-problematic games list

---

## 5. Required Tooling

| Tool | Purpose | Exists? | Priority |
|------|---------|---------|----------|
| `vgm_to_frame_state.py` | VGM → per-frame state for cross-validation | YES (built today) | Done |
| `nsfe_metadata.py` | Parse NSFE track names/durations | YES (built today) | Done |
| `driver_survey.py` | Classify games into families | YES (updated today) | Done |
| `expansion_detect.py` | Check NSF expansion flags, report missing coverage | NO | High |
| `dpcm_analyzer.py` | Detect DPCM vs DAC usage patterns in captures | NO | High |
| `cross_validate.py` | Align and compare NSF vs VGM vs NES-MDB output | NO | Medium |
| `capcom_parser.py` | ROM parser for Capcom 6C80 engine | NO | High |
| `sunsoft_parser.py` | ROM parser for Sunsoft engine | NO | Medium |
| `cc_thinner.py` | Reduce CC event density for Family 4 MIDI files | NO | Low |
| `nsf_trust_scorer.py` | Auto-score NSF trustworthiness per game | NO | Low |

---

## 6. Validation Strategy Upgrade

### Current (2-source)

```
NSF emulation → MIDI → ear check
Mesen trace → Frame IR → comparison (5 games only)
```

### Target (4-source triangulation)

```
NSF emulation ─┐
VGM logs ──────┼→ cross_validate.py → confidence score per game
NES-MDB ───────┤
Mesen trace ───┘ (when available)
```

**Workflow:**
1. Ingest game → run NSF pipeline → classify family
2. If VGM pack exists → run vgm_to_frame_state.py → compare
3. If NES-MDB entry exists → compare MIDI output
4. If Mesen trace exists → highest-fidelity comparison
5. Compute per-channel confidence score
6. Flag games where sources disagree → manual investigation

**Confidence tiers:**

| Tier | Sources Agreeing | Action |
|------|-----------------|--------|
| A | 3+ sources agree | Trusted output |
| B | 2 sources agree, 1 disagrees | Investigate the outlier |
| C | All disagree or only 1 source | Hypothesis output, needs manual check |
| D | No sources available | NSF-only, trust per family classification |

---

## 7. Roadmap (Ordered by Impact)

### Phase 1: Close critical gaps (immediate)

1. **Expansion audio detection** — Scan all 1577 NSFs for expansion
   flags. Report which games we're silently dropping audio from.
   Estimate: 1 day.

2. **DPCM event model** — Extend Frame IR with dpcm_trigger and
   dac_write events. Update nsf_to_reaper.py to capture $4010-$4013
   and $4011 writes distinctly. Estimate: 2 days.

3. **Phase reset tracking** — Add phase_reset event to Frame IR.
   Detect $4003/$4007 writes in capture. Critical for same-pitch
   retrigger accuracy. Estimate: 1 day.

### Phase 2: Expand ROM parsing (next sprint)

4. **Capcom 6C80 parser** — Build from romhacking.net #274 spec.
   Covers 30+ games. All Family 1 → straightforward validation.
   Estimate: 1 week.

5. **VGM cross-validation pipeline** — Build cross_validate.py
   for automated NSF vs VGM comparison across all overlapping games.
   Estimate: 3 days.

### Phase 3: Expansion audio support (medium-term)

6. **VRC6 support** — Implement VRC6 channel types in Frame IR +
   extend nsf_to_reaper.py capture. 24 games, including CV3 JP.
   Estimate: 1 week.

7. **FDS support** — Implement FDS wavetable channel. ~200 games
   affected but most are Japan-only. Estimate: 2 weeks (complex
   modulation unit).

8. **MMC5 support** — Trivial extension of APU pulse. 3 games.
   Estimate: 2 days.

### Phase 4: Synth fidelity (long-term)

9. **Non-linear mixing** — DONE 2026-04-15. Used formulas (not
   lookup tables) in render_wav, ReapNES_Console.jsfx, ReapNES_APU2.jsfx.
   See architecture.md Rule 27 and synth_fidelity.md Rule 7.

10. **Expansion audio in synth** — Render VRC6/FDS/5B/N163 waveforms
    in JSFX alongside APU channels. Estimate: 2 weeks per chip.

11. **Hardware filters** — Add high-pass (37 Hz, 14 Hz) and low-pass
    (14 kHz) filters to JSFX output. Estimate: 2 days.

### Phase 5: Model completeness (research)

12. **NES-MDB bulk comparison** — Compare our output against all 397
    overlapping games. Identify systematic errors. Estimate: 1 week.

13. **Sunsoft ROM parser** — Build from romhacking.net #665.
    Validates Family 4 extraction. Estimate: 1 week.

14. **Sub-family classification** — Implement secondary metrics
    (const_vol ratio, envelope shape, arpeggio index). Estimate: 3 days.

15. **VRC7 FM support** — Only 1 game, but architecturally the
    hardest expansion chip. Needs FM synthesis in JSFX. Estimate: 3 weeks.

---

## Sources

- NESDev Wiki: APU, APU_Mixer, APU_DMC, APU_Sweep, APU_Envelope,
  VRC6_audio, VRC7_audio, FDS_audio, MMC5_audio, Namco_163_audio,
  Sunsoft_5B_audio, NSF, NSF2, NSFe
- NESDev Forums: t=15586 (Battletoads PCM), t=6627 (NSF ripping),
  t=16630 (behind the scenes NSF ripping)
- VGMPF: Famicom/NES Sound Driver List, per-company driver pages
- Romhacking.net: #274 (Capcom 6C80), #875 (Capcom SE1), #665 (Sunsoft)
- FamiTracker source: APU.CPP, Mixer.cpp, Noise.cpp, DPCM.CPP,
  SoundGen.cpp, Channels2A03.cpp, Sequence.h
- NES-MDB: github.com/chrisdonahue/nesmdb, ISMIR 2018 paper
- VGMRips: VGM specification, NES ripping tutorial
