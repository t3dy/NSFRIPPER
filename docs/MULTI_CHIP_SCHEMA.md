# Multi-Chip Frame IR Schema

Unified schema for representing all NES audio hardware in the Frame IR
layer: standard 2A03 APU + 6 expansion chips + complete DPCM model.

**Status:** Design (Layer 1 of Hiro Plantagenet plan)
**Date:** 2026-04-13
**Depends on:** Expansion audit (data/expansion_audit.json)
**Feeds into:** Layer 2 (Frame IR extensions), Layer 3 (capture pipeline)

---

## 1. Scope from Expansion Audit

Scan of 297 NSF files in the current library:

| Chip | Games | Songs | CC12 Compatible | Priority |
|------|-------|-------|-----------------|----------|
| Standard 2A03 | 262 | — | Yes | Done |
| FDS | 30 | 563 | N/A (wavetable) | High |
| VRC6 | 5 | 205 | Breaks (8 duty) | High |
| VRC7 | 3 | 133 | Breaks (FM) | Medium |
| 5B | 1 | 106 | N/A (square) | Low |
| MMC5 | 0 | 0 | Yes (mirrors APU) | None yet |
| N163 | 0 | 0 | N/A (wavetable) | None yet |

Notes:
- 2 games (Platoon, Power Blade) report VRC6+VRC7+FDS simultaneously
  (expansion byte 0x07). This is almost certainly incorrect NSF metadata —
  no cartridge hardware supports all three. Treat as suspect.
- FDS is highest priority: 30 games including Kid Icarus, Zelda (FDS),
  Metroid (FDS), Gyruss, Esper Dream.
- VRC6 includes Castlevania 3 JP — musically important.
- As more games are downloaded (Nintendo, Hudson, Namco, Taito),
  expect MMC5, N163, and more FDS games to appear.

---

## 2. Channel Type Taxonomy

Every channel in the system has a unique type identifier and belongs
to a chip family. Channel types drive:
- Frame IR interpretation
- MIDI channel assignment
- CC encoding strategy
- Synth rendering path

### 2.1 Standard 2A03 APU (existing, no changes)

| Channel Type | Register Range | Volume | Duty/Timbre | Period Formula |
|-------------|---------------|--------|-------------|---------------|
| `pulse1` | $4000-$4003 | 4-bit (0-15) | 2-bit duty (0-3) | CPU/(16×(P+1)) |
| `pulse2` | $4004-$4007 | 4-bit (0-15) | 2-bit duty (0-3) | CPU/(16×(P+1)) |
| `triangle` | $4008-$400B | gate only | fixed waveform | CPU/(32×(P+1)) |
| `noise` | $400C-$400F | 4-bit (0-15) | mode bit (short/long) | LFSR rate table |
| `dmc` | $4010-$4013 | 7-bit DAC | N/A | DMA rate table |

### 2.2 VRC6 (Konami)

| Channel Type | Register Range | Volume | Duty/Timbre | Period Formula |
|-------------|---------------|--------|-------------|---------------|
| `vrc6_pulse1` | $9000-$9002 | 4-bit (0-15) | 3-bit duty (0-7) | CPU/(16×(P+1)) |
| `vrc6_pulse2` | $A000-$A002 | 4-bit (0-15) | 3-bit duty (0-7) | CPU/(16×(P+1)) |
| `vrc6_saw` | $B000-$B002 | 6-bit accum rate | N/A (sawtooth) | CPU/(14×(P+1)) |

VRC6 pulse: same period formula as APU pulse but 8 duty settings
instead of 4. The 3-bit duty field controls pulse width from 1/16
to 8/16 (6.25% to 50%).

VRC6 sawtooth: 6-bit accumulator rate added 2× per step, 7 steps
per cycle. Output is top 5 bits of accumulator. Rate 0 = silence.
Effective volume is (rate × 7) >> 3, clamped to 30 max output.

### 2.3 VRC7 (Konami — OPLL/YM2413)

| Channel Type | Register Range | Volume | Timbre | Period Formula |
|-------------|---------------|--------|--------|---------------|
| `vrc7_fm` ×6 | $9010/$9030 | 4-bit inverted (0=max) | instrument (0-15) | F-number + octave |

FM synthesis with 2-operator modulator/carrier. 15 preset instruments
(ROM patches) + 1 user-definable. Each channel has:
- F-number (9-bit frequency), octave (3-bit), key-on, sustain
- Volume is 4-bit INVERTED (0 = loudest, 15 = silent, 3dB per step)
- Built-in ADSR per operator — NOT software-driven like APU

This is fundamentally different from subtractive synthesis. The Frame IR
for VRC7 stores FM parameters, not waveform parameters.

### 2.4 FDS (Nintendo — Famicom Disk System)

| Channel Type | Register Range | Volume | Timbre | Period Formula |
|-------------|---------------|--------|--------|---------------|
| `fds_wave` | $4040-$408A | 6-bit gain (0-63, clamp 32) | 64-sample wavetable | CPU/(64×(P+1)) |

FDS has a single wavetable channel with hardware frequency modulation:
- Wave RAM: 64 entries × 6 bits at $4040-$407F
- Modulation table: 32 entries × 3 bits (7 values: -4 to +4)
- Mod frequency + counter produce vibrato/tremolo without software
- Volume envelope: 6-bit gain at $4080, with speed/direction bits
- Master volume: 2-bit at $4083 (1.0, 2/3, 1/2, 2/5)
- Output level is ~2.4× a single APU pulse at max gain

### 2.5 MMC5 (Nintendo)

| Channel Type | Register Range | Volume | Duty/Timbre | Period Formula |
|-------------|---------------|--------|-------------|---------------|
| `mmc5_pulse1` | $5000-$5003 | 4-bit (0-15) | 2-bit duty (0-3) | CPU/(16×(P+1)) |
| `mmc5_pulse2` | $5004-$5007 | 4-bit (0-15) | 2-bit duty (0-3) | CPU/(16×(P+1)) |
| `mmc5_pcm` | $5010-$5011 | 8-bit DAC | N/A | direct write |

MMC5 pulse channels are functionally identical to APU pulse except:
- No sweep unit
- Inverted output polarity (cancels with APU pulse at same settings)
- CC11/CC12 model applies directly

### 2.6 Namco 163

| Channel Type | Register Range | Volume | Timbre | Period Formula |
|-------------|---------------|--------|--------|---------------|
| `n163_wave` ×1-8 | $4800 (internal) | 4-bit (0-15) | configurable wavetable | CPU/(15×65536/P×C) |

N163 shares 128 bytes of internal RAM between channel registers and
waveform data. More channels = less waveform RAM = shorter waveforms
= lower fidelity per channel. Each channel has:
- Frequency (18-bit), waveform address (8-bit), waveform length (3-bit: 4-32 samples)
- Volume (4-bit per channel)
- Sample data: 4-bit values packed 2 per byte
- Update rate: CPU / (15 × num_channels) — with 8 channels, ~14.9 kHz

Channel count C (1-8) is configured at runtime.

### 2.7 Sunsoft 5B (YM2149F)

| Channel Type | Register Range | Volume | Timbre | Period Formula |
|-------------|---------------|--------|--------|---------------|
| `5b_square` ×3 | $C000/$E000 | 4-bit (0-15) or HW env | square wave | CPU/(32×P) |
| `5b_noise` | $C000/$E000 | — | noise LFSR | CPU/(32×P) |

5B features:
- 3 square channels, each independently mixable with tone and/or noise
- Mixer register ($07): per-channel tone enable + noise enable
- Hardware envelope generator: 16 shapes (ramp, triangle, sawtooth, hold)
  with configurable period. Produces 5-bit volume (0-31), overrides
  per-channel 4-bit volume when enabled.
- Period formula has NO +1: `freq = CPU / (32 × period)`. Period 0
  behaves as period 1.
- Noise is a single generator shared across channels, not per-channel

---

## 3. DPCM Event Model

The DMC channel ($4010-$4013, $4011, $4015 bit 4) serves two
fundamentally different purposes that require distinct event types.

### 3.1 DPCM Sample Playback

DMA-driven delta modulation from ROM samples. The CPU sets up address,
length, and rate, then the DMA engine fetches and plays.

```
Event: dpcm_trigger
Fields:
    rate_index: int       # 0-15 (maps to NTSC rate table below)
    sample_address: int   # byte address in ROM ($C000 + offset)
    sample_length: int    # length in bytes (L×16+1)
    loop: bool            # repeat sample
    initial_dac: int      # $4011 value at trigger (affects starting level)
```

NTSC DPCM rate table (Hz):
4181.7, 4709.9, 5264.0, 5593.0, 6257.7, 7046.3, 7919.4, 8363.4,
9419.9, 11186.1, 12604.0, 13982.6, 16884.6, 21306.8, 24858.0, 33143.9

Detection heuristic:
- $4012 and $4013 written, then $4015 bit 4 set → DPCM sample
- Known games: Sunsoft bass (Batman, Blaster Master, Journey to Silius),
  standard percussion (many games)

### 3.2 Direct DAC Writes

Software writes values directly to the $4011 output register, no DMA.
Used for algorithmic synthesis and mixing bias.

```
Event: dac_write
Fields:
    value: int            # 0-127 (7-bit DAC output)
```

For algorithmic synthesis patterns (multiple writes per frame):

```
Event: dac_ramp
Fields:
    start_value: int      # initial DAC level
    end_value: int        # final DAC level
    writes_per_frame: int # number of $4011 writes in this frame
```

Detection heuristic:
- Rapid $4011 writes without $4012/$4013 → direct DAC
- Multiple $4011 writes per frame → algorithmic synthesis
- Single $4011 write with no other DMC activity → mixing bias

### 3.3 Distinction Matters

| Property | DPCM Sample | Direct DAC |
|----------|------------|------------|
| Mechanism | DMA from ROM | CPU writes |
| CPU cost | Steals cycles | Proportional to rate |
| Pitch control | Rate register only | Software-determined |
| Quality | 1-bit delta | 7-bit absolute |
| MIDI mapping | Note + sample index | SysEx only |
| Known games | Most games with drums | Battletoads, some speech |

---

## 4. Unified FrameState Schema

Extension of the existing `FrameState` dataclass. All new fields
default to None or zero — existing pipeline produces identical output.

```python
@dataclass
class FrameState:
    """State of one channel at one frame — all chips."""
    frame: int

    # --- Chip and channel identity ---
    chip: str = "2a03"           # "2a03"|"vrc6"|"vrc7"|"fds"|"mmc5"|"n163"|"5b"
    channel_type: str = "pulse1" # see Section 2 for all types

    # --- Universal fields (all chips) ---
    period: int = 0              # timer period (0 = silent for most chips)
    midi_note: int = 0           # MIDI note number (0 = silent)
    volume: int = 0              # volume (interpretation varies by chip)
    sounding: bool = False       # whether audio is being produced
    event_type: str = "note"     # note|envelope|duty|dac|sweep|noise_mode|
                                 # dpcm_trigger|dac_write|dac_ramp|
                                 # fm_key_on|fm_key_off|wave_update

    # --- Pulse-family fields (2a03, vrc6, mmc5) ---
    duty: int = 0                # duty cycle index
                                 # 2a03/mmc5: 0-3 (12.5%, 25%, 50%, 75%)
                                 # vrc6: 0-7 (6.25% to 50%)
    const_vol: bool = True       # $4000 bit 4 (2a03 only)

    # --- Sweep fields (2a03 pulse only) ---
    sweep_enabled: bool = False
    sweep_period: int = 0
    sweep_negate: bool = False
    sweep_shift: int = 0

    # --- Noise fields (2a03, 5b) ---
    noise_mode: int = 0          # 0=long LFSR, 1=short/tonal
    noise_period_index: int = 0  # 0-15 (pre-inversion for 2a03)

    # --- DPCM fields (2a03 DMC) ---
    dac_value: int | None = None          # $4011 current value (0-127)
    dpcm_rate_index: int | None = None    # 0-15 sample rate
    dpcm_address: int | None = None       # sample ROM address
    dpcm_length: int | None = None        # sample byte length
    dpcm_loop: bool = False               # sample looping

    # --- VRC6 sawtooth fields ---
    saw_accum_rate: int = 0      # 6-bit accumulator rate (0-63)

    # --- VRC7 FM fields ---
    fm_instrument: int = 0       # 0-15 (0=custom, 1-15=ROM preset)
    fm_octave: int = 0           # 0-7
    fm_fnum: int = 0             # 9-bit F-number
    fm_key_on: bool = False      # key on/off state
    fm_sustain: bool = False     # sustain flag
    fm_volume: int = 0           # 4-bit INVERTED (0=max, 15=silent)
    # Custom instrument params (only when fm_instrument == 0):
    fm_custom_patch: bytes | None = None  # 8-byte patch definition

    # --- FDS wavetable fields ---
    fds_wave_data: bytes | None = None    # 64 × 6-bit samples
    fds_mod_table: bytes | None = None    # 32 × 3-bit mod values
    fds_mod_freq: int = 0                 # modulation frequency (12-bit)
    fds_mod_depth: int = 0                # modulation depth (6-bit)
    fds_volume_gain: int = 0              # 6-bit gain (0-63, clamped at 32)
    fds_master_volume: int = 0            # 2-bit (0-3: 1.0, 2/3, 1/2, 2/5)

    # --- N163 wavetable fields ---
    n163_wave_addr: int = 0      # wave data address in internal RAM
    n163_wave_length: int = 0    # waveform length (4-32 samples)
    n163_wave_data: bytes | None = None   # 4-bit samples, packed
    n163_num_channels: int = 1   # 1-8 (affects update rate)

    # --- 5B PSG fields ---
    tone_enable: bool = True     # per-channel tone on/off
    noise_enable: bool = False   # per-channel noise on/off
    env_enable: bool = False     # use HW envelope instead of volume
    env_shape: int = 0           # 0-15 envelope shape
    env_period: int = 0          # 16-bit envelope period
```

### Design Principles

1. **All new fields have zero/None/False defaults.** Existing code that
   creates `FrameState(frame=N, period=P, ...)` continues to work
   unchanged. This is non-negotiable for backward compatibility.

2. **`chip` + `channel_type` identify the source.** Downstream code
   (MIDI builder, synth, validation) dispatches on these two fields.
   No isinstance checks, no game-name branching.

3. **Volume semantics vary by chip.** `volume` is always present but
   means different things:
   - 2a03/VRC6/N163/5B: 4-bit (0-15), higher = louder
   - VRC7: 4-bit INVERTED (0 = loudest, 15 = silent)
   - FDS: stored in `fds_volume_gain` (6-bit, 0-63)
   - Normalization to CC11 (0-127) happens in the MIDI builder,
     not in Frame IR

4. **Wavetable data is stored once per change, not per frame.**
   FDS and N163 wave data only appears in the FrameState for frames
   where the waveform actually changes. Frames with no wave update
   inherit the previous waveform.

5. **FM parameters are stored as-is.** VRC7 registers are not
   converted to frequency/amplitude — the F-number, octave, and
   instrument index are stored directly. Conversion happens
   downstream.

---

## 5. MIDI Channel Assignments

Standard APU channels use MIDI channels 0-3. Expansion channels
use 4-11. Channel 9 is reserved (General MIDI percussion).

| MIDI Ch | Channel Type | Notes |
|---------|-------------|-------|
| 0 | `pulse1` | Standard APU Pulse 1 |
| 1 | `pulse2` | Standard APU Pulse 2 |
| 2 | `triangle` | Standard APU Triangle |
| 3 | `noise` | Standard APU Noise |
| 4 | `dmc` | DPCM samples / direct DAC |
| 5 | `vrc6_pulse1` or `mmc5_pulse1` or `5b_square1` | Expansion pulse/square 1 |
| 6 | `vrc6_pulse2` or `mmc5_pulse2` or `5b_square2` | Expansion pulse/square 2 |
| 7 | `vrc6_saw` or `fds_wave` or `5b_square3` | Expansion unique voice |
| 8 | `n163_wave` (ch 1-4) or `vrc7_fm` (ch 1-3) | Expansion multi-ch block A |
| 10 | `n163_wave` (ch 5-8) or `vrc7_fm` (ch 4-6) | Expansion multi-ch block B |
| 11 | `mmc5_pcm` or `5b_noise` | Expansion ancillary |

### Assignment Rules

1. **No game uses more than one expansion chip.** (Multi-chip NSF
   headers in our library are metadata errors.) So channels 5-11
   are reused per-chip without conflict.

2. **Channel 9 is never used.** General MIDI reserves ch 9 for
   percussion. Even though NES noise is drums, we keep it on ch 3
   to preserve the existing pipeline. External tools that interpret
   ch 9 as GM drums would mishandle NES noise.

3. **N163 and VRC7 have variable channel counts.** N163 can have 1-8
   channels; VRC7 always has 6. These overflow into the B block.
   If a game needs more than 6 expansion channels total (only N163
   at max), use channels 12-15.

4. **CC encoding per expansion channel:**

   | Channel Type | CC11 (volume) | CC12 (timbre) | Special CCs |
   |-------------|--------------|--------------|-------------|
   | vrc6_pulse | 4-bit → 0-127 | 3-bit duty → 0-127 (8 steps) | — |
   | vrc6_saw | accum rate → 0-127 | N/A (always 0) | — |
   | vrc7_fm | inverted 4-bit → 0-127 | instrument → CC14 (0-15) | CC15=sustain |
   | fds_wave | 6-bit gain → 0-127 | CC14=master vol (0-3) | CC15=mod depth |
   | mmc5_pulse | 4-bit → 0-127 | 2-bit duty → 0-127 | — |
   | n163_wave | 4-bit → 0-127 | N/A | CC14=wave addr |
   | 5b_square | 4-bit → 0-127 | N/A | CC14=env shape, CC15=mixer |

5. **SysEx is always available.** For any expansion channel, SysEx
   register replay (Priority 1 in the synth cascade) can encode
   the raw register state losslessly. CC encoding is a convenience
   fallback, not the primary path for expansion audio.

---

## 6. REAPER Track Layout

When generating RPP files for games with expansion audio:

```
Track 1: Square 1      (MIDI ch 0)  — ReapNES Studio, channel_mode=0
Track 2: Square 2      (MIDI ch 1)  — ReapNES Studio, channel_mode=1
Track 3: Triangle       (MIDI ch 2)  — ReapNES Studio, channel_mode=2
Track 4: Noise          (MIDI ch 3)  — ReapNES Studio, channel_mode=3
Track 5: DPCM           (MIDI ch 4)  — ReapNES Studio, channel_mode=4 (NEW)
Track 6+: Expansion     (MIDI ch 5+) — ReapNES Studio, expansion modes (NEW)
```

Expansion tracks require synth support (Layer 6). Until then,
expansion channels can be:
- Captured as SysEx in MIDI (lossless, unplayable without synth)
- Documented as "expansion audio present but not rendered"
- Flagged in the game's extraction report

---

## 7. Period-to-Note Formulas (All Chips)

All formulas use NTSC CPU clock = 1,789,773 Hz.

| Chip | Channel | Formula | Octave Offset |
|------|---------|---------|--------------|
| 2A03 | Pulse | CPU / (16 × (P+1)) | +12 (convention) |
| 2A03 | Triangle | CPU / (32 × (P+1)) | 0 (hardware -1 oct) |
| 2A03 | Noise | rate table lookup | N/A (not pitched) |
| VRC6 | Pulse | CPU / (16 × (P+1)) | +12 (same as APU) |
| VRC6 | Saw | CPU / (14 × (P+1)) | +12 |
| VRC7 | FM | 49716 × F / 2^(19-O) | per octave field |
| FDS | Wave | CPU / (64 × (P+1)) | 0 (already correct) |
| MMC5 | Pulse | CPU / (16 × (P+1)) | +12 (same as APU) |
| N163 | Wave | P × C / (15 × 65536) | 0 |
| 5B | Square | CPU / (32 × P) | 0 (no +1 in formula) |

Where P = period register, F = F-number, O = octave, C = num_channels.

---

## 8. Implementation Sequence

This schema feeds into subsequent Hiro Plantagenet layers:

### Layer 2: Frame IR Extensions
1. Add `chip` and `channel_type` fields to `FrameState`
2. Add expansion-specific fields (all defaulting to None/0/False)
3. Add DPCM event types to `event_type` enum
4. Move `frame_ir.py` from `extraction/drivers/konami/` to
   `extraction/frame_ir.py` (chip-agnostic)
5. Validate: existing CV1/Contra pipeline produces identical output

### Layer 3: Capture Pipeline
1. Read NSF expansion byte before emulation
2. Intercept expansion register writes in 6502 emulator
3. Map expansion channels to MIDI channels per Section 5
4. Distinguish DPCM sample from direct DAC (Section 3.3 heuristics)
5. Track $4003/$4007 phase reset writes
6. Validate: standard APU games produce bit-identical MIDI

### Layer 6: Synth Rendering
1. Add expansion channel modes to ReapNES Studio
2. Implement chip-specific waveform generation
3. Non-linear mixing for expansion channels
4. VRC7 FM synthesis (most complex — may use lookup tables)

---

## 9. Open Questions

1. **FDS wave RAM updates during playback.** Some games update the
   wavetable mid-note for timbral animation. How often does this
   happen? Do we need per-frame wave snapshots or is "store on change"
   sufficient? → Measure during Layer 3 implementation.

2. **N163 channel count changes.** Can a game change the number of
   active N163 channels during playback? If so, the MIDI channel
   assignment may need to be dynamic. → Check when N163 games are
   added to the library.

3. **VRC7 custom patch frequency.** How often do games change the
   custom instrument ($00) during playback? Lagrange Point likely
   does this. → Investigate during Lagrange Point extraction.

4. **$4011 mixing bias.** Should we capture all $4011 writes (even
   non-audible bias adjustments) or only those that produce
   intentional audio? → Conservative: capture all, filter in Frame IR.

5. **Multi-chip NSF headers.** Platoon and Power Blade report 0x07
   (VRC6+VRC7+FDS). Are these ripping errors, or do these games
   genuinely have complex expansion audio? → Verify against NES
   cartridge database or disassembly.
