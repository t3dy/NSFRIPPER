"""Tests for chip-agnostic Frame IR (extraction/frame_ir.py).

Verifies:
1. All expansion fields default correctly (backward compat)
2. Chip-specific FrameState construction works
3. ChannelIR with chip parameter works
4. Period-to-frequency for all chip types
5. MIDI channel assignment table is consistent
"""
import math
import pytest

from extraction.frame_ir import (
    FrameState, ChannelIR, SongIR,
    CPU_CLK, period_to_freq, freq_to_midi_note,
    MIDI_CHANNEL_MAP,
)


class TestFrameStateDefaults:
    """All new fields must default to zero/None/False."""

    def test_2a03_defaults(self):
        fs = FrameState(frame=0)
        assert fs.chip == "2a03"
        assert fs.period == 0
        assert fs.volume == 0
        assert fs.duty == 0
        assert fs.sounding is False
        assert fs.event_type == "note"

    def test_expansion_fields_default_to_zero_or_none(self):
        fs = FrameState(frame=0)
        # VRC6
        assert fs.saw_accum_rate == 0
        # VRC7
        assert fs.fm_instrument == 0
        assert fs.fm_octave == 0
        assert fs.fm_fnum == 0
        assert fs.fm_key_on is False
        assert fs.fm_volume == 0
        assert fs.fm_custom_patch is None
        # FDS
        assert fs.fds_wave_data is None
        assert fs.fds_mod_table is None
        assert fs.fds_mod_freq == 0
        assert fs.fds_volume_gain == 0
        assert fs.fds_master_volume == 0
        # N163
        assert fs.n163_wave_addr == 0
        assert fs.n163_wave_length == 0
        assert fs.n163_wave_data is None
        assert fs.n163_num_channels == 1
        # 5B
        assert fs.tone_enable is True
        assert fs.noise_enable is False
        assert fs.env_enable is False
        assert fs.env_shape == 0
        assert fs.env_period == 0
        # DPCM
        assert fs.dac_value is None
        assert fs.dpcm_rate_index is None
        assert fs.dpcm_address is None
        assert fs.dpcm_length is None
        assert fs.dpcm_loop is False

    def test_backward_compat_construction(self):
        """Creating FrameState with only old fields still works."""
        fs = FrameState(
            frame=10, period=200, midi_note=60,
            volume=12, duty=1, sounding=True,
        )
        assert fs.chip == "2a03"
        assert fs.period == 200
        assert fs.midi_note == 60
        assert fs.fm_instrument == 0  # expansion default


class TestChipSpecificConstruction:
    """Test constructing FrameState for each expansion chip."""

    def test_vrc6_pulse(self):
        fs = FrameState(frame=0, chip="vrc6", duty=5, volume=12, sounding=True)
        assert fs.chip == "vrc6"
        assert fs.duty == 5  # VRC6 supports 0-7

    def test_vrc6_saw(self):
        fs = FrameState(frame=0, chip="vrc6", saw_accum_rate=42, sounding=True)
        assert fs.saw_accum_rate == 42

    def test_vrc7_fm(self):
        fs = FrameState(
            frame=0, chip="vrc7",
            fm_instrument=3, fm_octave=4, fm_fnum=256,
            fm_key_on=True, fm_volume=2,
        )
        assert fs.chip == "vrc7"
        assert fs.fm_instrument == 3
        assert fs.fm_volume == 2  # inverted: 0=max

    def test_fds_wave(self):
        wave = bytes(range(64))
        fs = FrameState(
            frame=0, chip="fds",
            fds_wave_data=wave, fds_volume_gain=32,
            fds_master_volume=0, fds_mod_freq=100,
        )
        assert fs.fds_wave_data == wave
        assert fs.fds_volume_gain == 32

    def test_n163_wave(self):
        fs = FrameState(
            frame=0, chip="n163",
            n163_wave_addr=0x40, n163_wave_length=16,
            n163_num_channels=4, volume=10,
        )
        assert fs.n163_num_channels == 4

    def test_5b_square(self):
        fs = FrameState(
            frame=0, chip="5b",
            tone_enable=True, noise_enable=True,
            env_enable=True, env_shape=14, env_period=2048,
        )
        assert fs.env_shape == 14

    def test_dpcm_trigger(self):
        fs = FrameState(
            frame=0, chip="2a03",
            event_type="dpcm_trigger",
            dpcm_rate_index=12, dpcm_address=0xC000,
            dpcm_length=256, dpcm_loop=False,
            dac_value=64,
        )
        assert fs.event_type == "dpcm_trigger"
        assert fs.dpcm_rate_index == 12


class TestChannelIR:
    def test_chip_field(self):
        ch = ChannelIR(name="VRC6 Pulse 1", channel_type="vrc6_pulse1", chip="vrc6")
        assert ch.chip == "vrc6"
        fs = ch.get_frame(0)
        assert fs.chip == "vrc6"

    def test_default_2a03(self):
        ch = ChannelIR(name="Pulse 1", channel_type="pulse1")
        assert ch.chip == "2a03"


class TestPeriodToFreq:
    """Verify period-to-frequency for all chip types."""

    def test_pulse(self):
        assert abs(period_to_freq(200, "pulse") - CPU_CLK / (16 * 201)) < 0.01

    def test_triangle(self):
        assert abs(period_to_freq(200, "triangle") - CPU_CLK / (32 * 201)) < 0.01

    def test_vrc6_pulse(self):
        assert abs(period_to_freq(200, "vrc6_pulse") - CPU_CLK / (16 * 201)) < 0.01

    def test_vrc6_saw(self):
        assert abs(period_to_freq(200, "vrc6_saw") - CPU_CLK / (14 * 201)) < 0.01

    def test_fds_wave(self):
        assert abs(period_to_freq(200, "fds_wave") - CPU_CLK / (64 * 201)) < 0.01

    def test_5b_square_no_plus_one(self):
        # 5B has NO +1: freq = CPU / (32 * period)
        assert abs(period_to_freq(200, "5b_square") - CPU_CLK / (32 * 200)) < 0.01

    def test_5b_period_zero_uses_one(self):
        # Period 0 behaves as period 1
        assert abs(period_to_freq(0, "5b_square") - CPU_CLK / 32) < 0.01

    def test_mmc5_same_as_pulse(self):
        assert period_to_freq(200, "mmc5_pulse") == period_to_freq(200, "pulse")

    def test_silent_periods(self):
        assert period_to_freq(0) == 0.0
        assert period_to_freq(1) == 0.0


class TestMidiChannelMap:
    def test_standard_channels(self):
        assert MIDI_CHANNEL_MAP["pulse1"] == 0
        assert MIDI_CHANNEL_MAP["pulse2"] == 1
        assert MIDI_CHANNEL_MAP["triangle"] == 2
        assert MIDI_CHANNEL_MAP["noise"] == 3
        assert MIDI_CHANNEL_MAP["dmc"] == 4

    def test_no_channel_9(self):
        """Channel 9 is reserved for GM percussion."""
        assert 9 not in MIDI_CHANNEL_MAP.values()

    def test_expansion_channels_above_4(self):
        for ch_type, midi_ch in MIDI_CHANNEL_MAP.items():
            if ch_type not in ("pulse1", "pulse2", "triangle", "noise", "dmc"):
                assert midi_ch >= 5, f"{ch_type} should be >= 5, got {midi_ch}"
