"""Chip-agnostic Frame IR: core data structures for all NES audio hardware.

The canonical time model is NES frames (1/60s NTSC). Every event has an
absolute frame number. This IR can be compared directly against emulator
APU trace data.

Covers: standard 2A03 APU + VRC6 + VRC7 + FDS + MMC5 + N163 + 5B.
All expansion fields default to None/zero/False so existing 2A03-only
code produces identical output without changes.

Design doc: docs/MULTI_CHIP_SCHEMA.md (Layer 1 of Hiro Plantagenet plan)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

CPU_CLK = 1789773


# ---------------------------------------------------------------------------
# Period/frequency utilities (chip-agnostic)
# ---------------------------------------------------------------------------

def period_to_freq(period: int, channel: str = "pulse") -> float:
    """Convert NES timer period to frequency in Hz.

    Supports all chip types via the channel parameter:
        pulse, triangle, vrc6_pulse, vrc6_saw, fds_wave, mmc5_pulse,
        5b_square, n163_wave (requires extra params via dedicated fn)
    """
    if channel == "5b_square":
        # 5B has NO +1 in the formula: freq = CPU / (32 * period)
        # Period 0 behaves as period 1
        return CPU_CLK / (32 * max(1, period))
    if period < 2:
        return 0.0
    if channel in ("pulse", "vrc6_pulse", "mmc5_pulse"):
        return CPU_CLK / (16 * (period + 1))
    elif channel == "triangle":
        return CPU_CLK / (32 * (period + 1))
    elif channel == "vrc6_saw":
        return CPU_CLK / (14 * (period + 1))
    elif channel == "fds_wave":
        return CPU_CLK / (64 * (period + 1))
    else:
        # Default to pulse formula
        return CPU_CLK / (16 * (period + 1))


def freq_to_midi_note(freq: float, octave_offset: int = 0) -> int:
    """Convert frequency to nearest MIDI note.

    octave_offset: additional semitones to add. Use +12 for pulse channels
    to match the Konami driver's MIDI mapping convention (BASE_MIDI_OCTAVE4
    = 36). Triangle does NOT get the offset because the 32-step sequencer
    already produces the correct octave.
    """
    if freq < 20:
        return 0
    m = round(69 + 12 * math.log2(freq / 440)) + octave_offset
    return m if 21 <= m <= 120 else 0


# ---------------------------------------------------------------------------
# Frame-level data structures (all chips)
# ---------------------------------------------------------------------------

@dataclass
class FrameState:
    """State of one channel at one frame -- all NES audio chips.

    Extended from the original 2A03-only FrameState to support all 6
    expansion chips + complete DPCM model. All new fields default to
    None/zero/False for backward compatibility.

    See docs/MULTI_CHIP_SCHEMA.md Section 4 for field semantics.
    """
    frame: int

    # --- Chip and channel identity ---
    chip: str = "2a03"              # "2a03"|"vrc6"|"vrc7"|"fds"|"mmc5"|"n163"|"5b"
    # channel_type is on ChannelIR, not duplicated per frame

    # --- Universal fields (all chips) ---
    period: int = 0                 # timer period (0 = silent for most chips)
    midi_note: int = 0              # MIDI note number (0 = silent)
    volume: int = 0                 # volume (interpretation varies by chip)
    sounding: bool = False          # whether audio is being produced
    event_type: str = "note"        # note|envelope|duty|dac|sweep|noise_mode|
                                    # dpcm_trigger|dac_write|dac_ramp|
                                    # fm_key_on|fm_key_off|wave_update

    # --- Pulse-family fields (2a03, vrc6, mmc5) ---
    duty: int = 0                   # duty cycle index
                                    # 2a03/mmc5: 0-3 (12.5%, 25%, 50%, 75%)
                                    # vrc6: 0-7 (6.25% to 50%)
    const_vol: bool = True          # $4000 bit 4 (2a03 only)

    # --- Sweep fields (2a03 pulse only) ---
    sweep_enabled: bool = False     # $4001/$4005 bit 7
    sweep_period: int = 0           # sweep divider period
    sweep_negate: bool = False      # sweep direction
    sweep_shift: int = 0            # sweep shift count

    # --- Noise fields (2a03, 5b) ---
    noise_mode: int = 0             # 0=long LFSR (hissy), 1=short/tonal
    noise_period_index: int = 0     # 0-15 (pre-inversion for 2a03)

    # --- DPCM fields (2a03 DMC) ---
    dac_value: int | None = None            # $4011 current value (0-127)
    dpcm_rate_index: int | None = None      # 0-15 sample rate
    dpcm_address: int | None = None         # sample ROM address
    dpcm_length: int | None = None          # sample byte length
    dpcm_loop: bool = False                 # sample looping

    # --- VRC6 sawtooth fields ---
    saw_accum_rate: int = 0         # 6-bit accumulator rate (0-63)

    # --- VRC7 FM fields ---
    fm_instrument: int = 0          # 0-15 (0=custom, 1-15=ROM preset)
    fm_octave: int = 0              # 0-7
    fm_fnum: int = 0                # 9-bit F-number
    fm_key_on: bool = False         # key on/off state
    fm_sustain: bool = False        # sustain flag
    fm_volume: int = 0              # 4-bit INVERTED (0=max, 15=silent)
    fm_custom_patch: bytes | None = None    # 8-byte patch def (instrument==0)

    # --- FDS wavetable fields ---
    fds_wave_data: bytes | None = None      # 64 x 6-bit samples
    fds_mod_table: bytes | None = None      # 32 x 3-bit mod values
    fds_mod_freq: int = 0                   # modulation frequency (12-bit)
    fds_mod_depth: int = 0                  # modulation depth (6-bit)
    fds_volume_gain: int = 0                # 6-bit gain (0-63, clamped at 32)
    fds_master_volume: int = 0              # 2-bit (0-3: 1.0, 2/3, 1/2, 2/5)

    # --- N163 wavetable fields ---
    n163_wave_addr: int = 0         # wave data address in internal RAM
    n163_wave_length: int = 0       # waveform length (4-32 samples)
    n163_wave_data: bytes | None = None     # 4-bit samples, packed
    n163_num_channels: int = 1      # 1-8 (affects update rate)

    # --- 5B PSG fields ---
    tone_enable: bool = True        # per-channel tone on/off
    noise_enable: bool = False      # per-channel noise on/off
    env_enable: bool = False        # use HW envelope instead of volume
    env_shape: int = 0              # 0-15 envelope shape
    env_period: int = 0             # 16-bit envelope period


@dataclass
class ChannelIR:
    """Frame-accurate representation of one channel."""
    name: str
    channel_type: str       # "pulse1","pulse2","triangle","noise","dmc",
                            # "vrc6_pulse1","vrc6_pulse2","vrc6_saw",
                            # "vrc7_fm","fds_wave","mmc5_pulse1","mmc5_pulse2",
                            # "mmc5_pcm","n163_wave","5b_square","5b_noise"
    chip: str = "2a03"      # chip family for this channel
    frames: dict[int, FrameState] = field(default_factory=dict)

    def get_frame(self, f: int) -> FrameState:
        return self.frames.get(f, FrameState(frame=f, chip=self.chip))

    @property
    def total_frames(self) -> int:
        return max(self.frames.keys()) + 1 if self.frames else 0

    @property
    def sounding_frames(self) -> int:
        return sum(1 for fs in self.frames.values() if fs.sounding)


@dataclass
class SongIR:
    """Frame-accurate representation of the entire song."""
    track_number: int
    channels: list[ChannelIR] = field(default_factory=list)

    @property
    def total_frames(self) -> int:
        return max(ch.total_frames for ch in self.channels) if self.channels else 0


# ---------------------------------------------------------------------------
# MIDI channel assignment table (from MULTI_CHIP_SCHEMA.md Section 5)
# ---------------------------------------------------------------------------

MIDI_CHANNEL_MAP: dict[str, int] = {
    "pulse1": 0,
    "pulse2": 1,
    "triangle": 2,
    "noise": 3,
    "dmc": 4,
    "vrc6_pulse1": 5, "mmc5_pulse1": 5, "5b_square1": 5,
    "vrc6_pulse2": 6, "mmc5_pulse2": 6, "5b_square2": 6,
    "vrc6_saw": 7, "fds_wave": 7, "5b_square3": 7,
    "mmc5_pcm": 11, "5b_noise": 11,
}
# VRC7 and N163 multi-channel: assigned dynamically (8, 10, 12-15)
