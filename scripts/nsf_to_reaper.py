"""
NSF to MIDI + REAPER Project converter.

Runs the NSF driver via 6502 emulation, captures APU register writes,
and produces:
- 4-track MIDI with CC11 (volume), CC12 (duty cycle), note events
- REAPER .rpp project with ReapNES_APU.jsfx synth loaded per channel
- WAV preview render

Usage:
    python scripts/nsf_to_reaper.py <nsf_file> <song#> <seconds> -o <output_dir>
    python scripts/nsf_to_reaper.py <nsf_file> --all -o <output_dir>
    python scripts/nsf_to_reaper.py <nsf_file> --all -o <output_dir> --names "Stage Select,Enemy Chosen,Cut Man,..."
"""

import sys
import os
import math
import json
import wave
import struct
import argparse
import numpy as np
import mido
from pathlib import Path

# Pipeline hooks — evidence recording after each song extraction
try:
    from ANTIRIPPER.scripts.pipeline_hooks_v2 import PipelineHooks
    _hooks = PipelineHooks()
except Exception:
    _hooks = None
from py65.devices.mpu6502 import MPU

# Fix Windows cp1252 encoding errors with non-ASCII NSF metadata
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SAMPLE_RATE = 44100
SPF = SAMPLE_RATE // 60
TICKS_PER_BEAT = 480
TICKS_PER_FRAME = 16  # at our tempo mapping

REPO_ROOT = Path(__file__).resolve().parent.parent
JSFX_PATH = REPO_ROOT / "studio" / "jsfx" / "ReapNES_APU.jsfx"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class NsfEmulator:
    """Run NSF driver and capture APU register writes."""

    def __init__(self, nsf_path):
        self.nsf_path = str(nsf_path)
        with open(nsf_path, 'rb') as f:
            self.nsf_data = f.read()

        self.total_songs = self.nsf_data[6]
        self.starting_song = self.nsf_data[7]
        self.load_addr = self.nsf_data[8] | (self.nsf_data[9] << 8)
        self.init_addr = self.nsf_data[10] | (self.nsf_data[11] << 8)
        self.play_addr = self.nsf_data[12] | (self.nsf_data[13] << 8)
        self.title = self.nsf_data[14:46].decode('ascii', errors='replace').rstrip('\x00')
        self.artist = self.nsf_data[46:78].decode('ascii', errors='replace').rstrip('\x00')
        self.bankswitch = list(self.nsf_data[0x70:0x78])
        self.uses_bankswitch = any(b != 0 for b in self.bankswitch)
        self.rom_data = self.nsf_data[128:]

        # Expansion audio flags (NSF header byte $7B)
        self.expansion_flags = self.nsf_data[0x7B] if len(self.nsf_data) > 0x7B else 0
        self.has_vrc6 = bool(self.expansion_flags & 0x01)
        self.has_vrc7 = bool(self.expansion_flags & 0x02)
        self.has_fds = bool(self.expansion_flags & 0x04)
        self.has_mmc5 = bool(self.expansion_flags & 0x08)
        self.has_n163 = bool(self.expansion_flags & 0x10)
        self.has_5b = bool(self.expansion_flags & 0x20)
        self.expansion_chips = []
        if self.has_vrc6: self.expansion_chips.append("vrc6")
        if self.has_vrc7: self.expansion_chips.append("vrc7")
        if self.has_fds: self.expansion_chips.append("fds")
        if self.has_mmc5: self.expansion_chips.append("mmc5")
        if self.has_n163: self.expansion_chips.append("n163")
        if self.has_5b: self.expansion_chips.append("5b")

    def _load_rom(self, cpu):
        """Load ROM data into CPU memory, handling bankswitch if needed."""
        if not self.uses_bankswitch:
            # Linear loading — original behavior
            for i, byte in enumerate(self.rom_data):
                addr = self.load_addr + i
                if addr < 0x10000:
                    cpu.memory[addr] = byte
        else:
            # Bankswitched NSF: ROM data is organized as 4KB pages.
            #
            # CRITICAL: The ROM data in the file starts at load_addr, NOT at
            # the page boundary. For non-page-aligned load addresses (e.g.
            # $FC00, $8D60), there is an implicit padding of (load_addr & $FFF)
            # bytes before the actual data within bank 0. The file does NOT
            # contain this padding — bank boundaries must be offset.
            #
            # Bank N data in rom_data starts at: N * 4096 - padding
            # (with bank 0 having its first `padding` bytes as implicit zeros)
            page_size = 0x1000  # 4KB
            padding = self.load_addr & 0xFFF
            # Total virtual size = padding + actual data
            virtual_size = padding + len(self.rom_data)
            num_pages = (virtual_size + page_size - 1) // page_size
            # Precompute: store pages as a flat virtual array with padding
            self._bank_pages = bytearray(num_pages * page_size)
            self._bank_pages[padding:padding + len(self.rom_data)] = self.rom_data
            self._num_pages = num_pages
            # Determine base address: $6000 if load_addr < $8000, else $8000
            base_addr = 0x6000 if self.load_addr < 0x8000 else 0x8000
            for slot in range(8):
                page_num = self.bankswitch[slot]
                if page_num >= num_pages:
                    continue
                dest_addr = base_addr + slot * page_size
                if dest_addr >= 0x10000:
                    continue
                src_offset = page_num * page_size
                for i in range(page_size):
                    cpu.memory[dest_addr + i] = self._bank_pages[src_offset + i]

    def _install_bankswitch_handler(self, cpu):
        """Install write handler for NSF bankswitch registers $5FF6-$5FFF.

        The full NSF bankswitch range:
          $5FF6 → $6000-$6FFF (work RAM / FDS)
          $5FF7 → $7000-$7FFF (work RAM / FDS)
          $5FF8 → $8000-$8FFF
          ...
          $5FFF → $F000-$FFFF

        Many drivers bankswitch music data into $6000-$7FFF at runtime,
        even for standard (non-FDS) NSFs. Missing $5FF6-$5FF7 caused
        39 bankswitched games to hang.
        """
        if not self.uses_bankswitch:
            return

        page_size = 0x1000
        bank_pages = self._bank_pages
        num_pages = self._num_pages

        # py65 doesn't have write hooks, so we override the __setitem__
        # on the memory object to intercept bankswitch writes.
        original_memory = cpu.memory

        class BankswitchMemory:
            """Memory wrapper that intercepts writes to $5FF6-$5FFF."""
            def __init__(self, mem):
                self._mem = mem

            def __getitem__(self, key):
                return self._mem[key]

            def __setitem__(self, key, value):
                self._mem[key] = value
                if 0x5FF6 <= key <= 0x5FFF:
                    # $5FF6 → $6000, $5FF7 → $7000, $5FF8 → $8000, etc.
                    dest = 0x6000 + (key - 0x5FF6) * page_size
                    page_num = value
                    if page_num < num_pages and dest + page_size <= 0x10000:
                        src = page_num * page_size
                        for i in range(page_size):
                            self._mem[dest + i] = bank_pages[src + i]

            def __len__(self):
                return len(self._mem)

            def __iter__(self):
                return iter(self._mem)

        cpu.memory = BankswitchMemory(original_memory)

    def play_song(self, song_num, duration_frames):
        """Run the driver and return per-frame APU writes.

        Each frame preserves the ordered APU register writes that occurred
        during that play-call, including same-value rewrites. Those rewrites
        carry real hardware meaning for attack/retrigger cases such as the
        Wizards & Warriors title triangle phrase.
        """
        cpu = MPU()
        for i in range(0x10000):
            cpu.memory[i] = 0
        self._load_rom(cpu)
        self._install_bankswitch_handler(cpu)
        cpu.memory[0x4700] = 0x60  # RTS sentinel

        base_memory = cpu.memory

        # Build capture ranges based on expansion flags
        capture_ranges = [(0x4000, 0x4017)]  # Standard APU always captured
        if self.has_vrc6:
            capture_ranges.extend([(0x9000, 0x9002), (0xA000, 0xA002), (0xB000, 0xB002)])
        if self.has_vrc7:
            capture_ranges.extend([(0x9010, 0x9010), (0x9030, 0x9030)])
        if self.has_fds:
            capture_ranges.append((0x4040, 0x408A))
        if self.has_mmc5:
            capture_ranges.append((0x5000, 0x5015))
        if self.has_n163:
            capture_ranges.extend([(0x4800, 0x4800), (0xF800, 0xF800)])
        if self.has_5b:
            capture_ranges.extend([(0xC000, 0xC000), (0xE000, 0xE000)])

        class CaptureMemory:
            """Memory wrapper that preserves ordered APU/expansion writes per frame."""

            def __init__(self, mem, ranges):
                self._mem = mem
                self._ranges = ranges
                self.current_writes = []

            def __getitem__(self, key):
                return self._mem[key]

            def __setitem__(self, key, value):
                self._mem[key] = value
                for lo, hi in self._ranges:
                    if lo <= key <= hi:
                        self.current_writes.append((key, value))
                        break

            def __len__(self):
                return len(self._mem)

            def __iter__(self):
                return iter(self._mem)

        cpu.memory = CaptureMemory(base_memory, capture_ranges)

        def call(addr, a=0, max_cyc=50000):
            cpu.sp = 0xFD
            cpu.stPushWord(0x46FE)
            cpu.a = a; cpu.x = 0; cpu.y = 0; cpu.pc = addr; cpu.p = 0x04
            cyc = 0
            while cyc < max_cyc and cpu.pc not in (0x46FF, 0x4700):
                cpu.step(); cyc += 1
            return cyc < max_cyc  # True = returned normally, False = hit cycle limit

        # INIT
        call(self.init_addr, a=song_num - 1)

        # PLAY each frame, capture APU state
        frames = []
        silence_count = 0
        stuck_count = 0
        SILENCE_THRESHOLD = 120  # 2 seconds of no APU activity = song ended
        STUCK_THRESHOLD = 30     # 30 consecutive max-cyc calls = driver stuck
        for frame in range(duration_frames):
            cpu.memory.current_writes = []
            completed = call(self.play_addr, max_cyc=30000)
            writes = list(cpu.memory.current_writes)

            # Detect stuck driver: play routine didn't return normally
            if not completed:
                stuck_count += 1
                if stuck_count >= STUCK_THRESHOLD:
                    break  # driver is in an infinite loop
            else:
                stuck_count = 0
            if frame == 0:
                existing = {reg for reg, _ in writes}
                for reg in range(0x4000, 0x4018):
                    if reg not in existing:
                        writes.append((reg, cpu.memory[reg]))
            frames.append({"writes": writes})

            # Early exit: if no APU writes for SILENCE_THRESHOLD consecutive
            # frames, the song has ended or the driver is stuck in a loop.
            # This prevents py65 from burning CPU on silent/crashed songs.
            if len(writes) == 0:
                silence_count += 1
                if silence_count >= SILENCE_THRESHOLD and frame > 60:
                    break
            else:
                silence_count = 0

        return frames


def frames_to_channel_data(frames, expansion_chips=None):
    """Convert per-frame APU state to per-channel note/volume/duty data.

    Args:
        frames: list of {"writes": [(reg, val), ...]} per frame
        expansion_chips: list of chip names (e.g. ["vrc6", "fds"]) or None
    """
    expansion_chips = expansion_chips or []
    channels = {
        "pulse1": {"period": 0, "vol": 0, "duty": 1, "const_vol": 0, "env_loop": 0, "env_period": 0, "notes": []},
        "pulse2": {"period": 0, "vol": 0, "duty": 1, "const_vol": 0, "env_loop": 0, "env_period": 0, "notes": []},
        "triangle": {"period": 0, "linear": 0, "linear_reload": 0, "linear_control": 0, "notes": []},
        "noise": {"vol": 0, "period": 0, "mode": 0, "notes": []},
    }
    # Add expansion channel state
    if "vrc6" in expansion_chips:
        channels["vrc6_pulse1"] = {"period": 0, "vol": 0, "duty": 0, "enable": 0, "notes": []}
        channels["vrc6_pulse2"] = {"period": 0, "vol": 0, "duty": 0, "enable": 0, "notes": []}
        channels["vrc6_saw"] = {"period": 0, "accum_rate": 0, "enable": 0, "notes": []}
    if "fds" in expansion_chips:
        channels["fds_wave"] = {"period": 0, "vol_gain": 0, "master_vol": 0, "mod_freq": 0, "notes": []}

    for frame_idx, frame_packet in enumerate(frames):
        state = frame_packet["writes"]
        # Update pulse 1
        for reg, value in state:
            if reg == 0x4000:
                channels["pulse1"]["duty"] = (value >> 6) & 3
                channels["pulse1"]["env_loop"] = (value >> 5) & 1
                channels["pulse1"]["const_vol"] = (value >> 4) & 1
                channels["pulse1"]["env_period"] = value & 0x0F
                channels["pulse1"]["vol"] = value & 0x0F
            elif reg == 0x4002:
                channels["pulse1"]["period"] = (channels["pulse1"]["period"] & 0x700) | value
            elif reg == 0x4003:
                channels["pulse1"]["period"] = (channels["pulse1"]["period"] & 0xFF) | ((value & 7) << 8)
            elif reg == 0x4004:
                channels["pulse2"]["duty"] = (value >> 6) & 3
                channels["pulse2"]["env_loop"] = (value >> 5) & 1
                channels["pulse2"]["const_vol"] = (value >> 4) & 1
                channels["pulse2"]["env_period"] = value & 0x0F
                channels["pulse2"]["vol"] = value & 0x0F
            elif reg == 0x4006:
                channels["pulse2"]["period"] = (channels["pulse2"]["period"] & 0x700) | value
            elif reg == 0x4007:
                channels["pulse2"]["period"] = (channels["pulse2"]["period"] & 0xFF) | ((value & 7) << 8)
            elif reg == 0x4008:
                channels["triangle"]["linear_control"] = (value >> 7) & 1
                channels["triangle"]["linear_reload"] = value & 0x7F
                channels["triangle"]["linear"] = value & 0x7F
            elif reg == 0x400A:
                channels["triangle"]["period"] = (channels["triangle"].get("period", 0) & 0x700) | value
            elif reg == 0x400B:
                channels["triangle"]["period"] = (channels["triangle"].get("period", 0) & 0xFF) | ((value & 7) << 8)
            elif reg == 0x400C:
                channels["noise"]["vol"] = value & 0x0F
            elif reg == 0x400E:
                channels["noise"]["period"] = value & 0x0F
                channels["noise"]["mode"] = (value >> 7) & 1
            # VRC6 registers
            elif reg == 0x9000 and "vrc6_pulse1" in channels:
                channels["vrc6_pulse1"]["duty"] = (value >> 4) & 0x07
                channels["vrc6_pulse1"]["vol"] = value & 0x0F
                channels["vrc6_pulse1"]["enable"] = (value >> 7) & 1
            elif reg == 0x9001 and "vrc6_pulse1" in channels:
                channels["vrc6_pulse1"]["period"] = (channels["vrc6_pulse1"]["period"] & 0xF00) | value
            elif reg == 0x9002 and "vrc6_pulse1" in channels:
                channels["vrc6_pulse1"]["period"] = (channels["vrc6_pulse1"]["period"] & 0xFF) | ((value & 0x0F) << 8)
                channels["vrc6_pulse1"]["enable"] = (value >> 7) & 1
            elif reg == 0xA000 and "vrc6_pulse2" in channels:
                channels["vrc6_pulse2"]["duty"] = (value >> 4) & 0x07
                channels["vrc6_pulse2"]["vol"] = value & 0x0F
                channels["vrc6_pulse2"]["enable"] = (value >> 7) & 1
            elif reg == 0xA001 and "vrc6_pulse2" in channels:
                channels["vrc6_pulse2"]["period"] = (channels["vrc6_pulse2"]["period"] & 0xF00) | value
            elif reg == 0xA002 and "vrc6_pulse2" in channels:
                channels["vrc6_pulse2"]["period"] = (channels["vrc6_pulse2"]["period"] & 0xFF) | ((value & 0x0F) << 8)
                channels["vrc6_pulse2"]["enable"] = (value >> 7) & 1
            elif reg == 0xB000 and "vrc6_saw" in channels:
                channels["vrc6_saw"]["accum_rate"] = value & 0x3F
            elif reg == 0xB001 and "vrc6_saw" in channels:
                channels["vrc6_saw"]["period"] = (channels["vrc6_saw"]["period"] & 0xF00) | value
            elif reg == 0xB002 and "vrc6_saw" in channels:
                channels["vrc6_saw"]["period"] = (channels["vrc6_saw"]["period"] & 0xFF) | ((value & 0x0F) << 8)
                channels["vrc6_saw"]["enable"] = (value >> 7) & 1
            # FDS registers
            elif reg == 0x4080 and "fds_wave" in channels:
                channels["fds_wave"]["vol_gain"] = value & 0x3F
            elif reg == 0x4082 and "fds_wave" in channels:
                channels["fds_wave"]["period"] = (channels["fds_wave"].get("period", 0) & 0xF00) | value
            elif reg == 0x4083 and "fds_wave" in channels:
                channels["fds_wave"]["period"] = (channels["fds_wave"].get("period", 0) & 0xFF) | ((value & 0x0F) << 8)
            elif reg == 0x4084 and "fds_wave" in channels:
                channels["fds_wave"]["mod_freq"] = (channels["fds_wave"].get("mod_freq", 0) & 0xF00) | value
            elif reg == 0x4085 and "fds_wave" in channels:
                channels["fds_wave"]["mod_freq"] = (channels["fds_wave"].get("mod_freq", 0) & 0xFF) | ((value & 0x0F) << 8)
            elif reg == 0x4089 and "fds_wave" in channels:
                channels["fds_wave"]["master_vol"] = value & 0x03

        # Record per-frame state for each channel
        for ch_name in ["pulse1", "pulse2"]:
            ch = channels[ch_name]
            ch["notes"].append({
                "frame": frame_idx,
                "period": ch["period"],
                "vol": ch["vol"],
                "duty": ch["duty"],
                "const_vol": ch["const_vol"],
                "env_loop": ch["env_loop"],
                "env_period": ch["env_period"],
            })

        ch = channels["triangle"]
        ch["notes"].append({
            "frame": frame_idx,
            "period": ch.get("period", 0),
            "linear": ch["linear"],
            "linear_reload": ch["linear_reload"],
            "linear_control": ch["linear_control"],
        })

        ch = channels["noise"]
        ch["notes"].append({
            "frame": frame_idx,
            "vol": ch["vol"],
            "period": ch["period"],
            "mode": ch["mode"],
        })

        # VRC6 per-frame state
        if "vrc6_pulse1" in channels:
            for ch_name in ["vrc6_pulse1", "vrc6_pulse2"]:
                ch = channels[ch_name]
                ch["notes"].append({
                    "frame": frame_idx,
                    "period": ch["period"],
                    "vol": ch["vol"],
                    "duty": ch["duty"],
                    "enable": ch["enable"],
                })
            ch = channels["vrc6_saw"]
            ch["notes"].append({
                "frame": frame_idx,
                "period": ch["period"],
                "accum_rate": ch["accum_rate"],
                "enable": ch["enable"],
            })

        # FDS per-frame state
        if "fds_wave" in channels:
            ch = channels["fds_wave"]
            ch["notes"].append({
                "frame": frame_idx,
                "period": ch.get("period", 0),
                "vol_gain": ch["vol_gain"],
                "master_vol": ch["master_vol"],
                "mod_freq": ch.get("mod_freq", 0),
            })

    return channels


def period_to_midi(period, is_tri=False, channel_type=None):
    """Convert NES period register to MIDI note number.

    Supports standard APU channels and expansion chips.
    channel_type: None (standard APU), "vrc6_pulse", "vrc6_saw", "fds_wave"
    """
    if channel_type == "vrc6_pulse":
        if period <= 8:
            return 0
        freq = 1789773 / (16 * (period + 1))
    elif channel_type == "vrc6_saw":
        if period <= 8:
            return 0
        freq = 1789773 / (14 * (period + 1))
    elif channel_type == "fds_wave":
        if period <= 2:
            return 0
        freq = 1789773 / (64 * (period + 1))
    else:
        # Standard APU
        if period <= (2 if is_tri else 8):
            return 0
        div = 32 if is_tri else 16
        freq = 1789773 / (div * (period + 1))
    midi = round(69 + 12 * math.log2(freq / 440))
    return max(0, min(127, midi))


def load_wizards_and_warriors_note_boundaries(nsf_path, song_num):
    """Return parsed event boundaries for Wizards & Warriors.

    The title phrase contains same-pitch re-attacks that do not show up as a
    period change in per-frame APU state. We recover those note starts from the
    ROM parser so MIDI export can retrigger them instead of merging them into a
    sustained note.
    """
    nsf_name = Path(nsf_path).name.lower()
    if "wizards & warriors" not in nsf_name:
        return {}

    from extraction.drivers.other.wizards_and_warriors_parser import (
        DirectNoteEvent,
        TableNoteEvent,
        WizardsAndWarriorsParser,
    )
    from extraction.drivers.other.wizards_and_warriors_simulator import get_song_tempo_scale

    parser = WizardsAndWarriorsParser(nsf_path)
    song = parser.extract_all_song_pointers()[song_num - 1]
    tempo_scale = get_song_tempo_scale(parser, song_num)
    boundaries = {}

    for channel in ("pulse1", "pulse2", "triangle", "noise"):
        parsed = parser.parse_channel(
            song.channel_pointers[channel],
            channel,
            max_events=4096,
            visit_limit=128,
        )
        frame = 0
        starts = []
        for evt in parsed.events:
            if isinstance(evt, (TableNoteEvent, DirectNoteEvent)):
                starts.append(frame)
                frame += (evt.duration or 0) * tempo_scale
        boundaries[channel] = set(starts)

    return boundaries


def build_midi(channels, game_title, song_name, song_num, frames=None,
               period_fn=None, source_text=None, note_boundaries=None):
    """Build a MIDI file matching the CV1 pipeline format.

    If frames (raw APU register snapshots) are provided, embeds per-frame
    SysEx messages carrying the raw register state for each channel.
    This enables hardware-accurate register-replay in the APU2 synth.

    Args:
        period_fn: Optional period-to-MIDI converter. Defaults to period_to_midi.
                   Trace-based pipelines can pass a custom converter when needed.
        source_text: Optional source description for MIDI metadata track.

    SysEx format per channel per frame:
        Register replay:
          F0 7D 02 <ch> <reg0> <reg1> <reg2> <reg3> <enable_bit> <write_mask> F7
        Audible-state sideband:
          F0 7D 03 <ch> <flags> <level> <release_class> F7

    Where ch=0-3, reg0-3 are the 4 APU register bytes for that channel,
    enable_bit is the channel's bit from $4015, and write_mask marks which
    of the four channel registers were written during that frame.
    Audible-state flags currently use:
      bit0 = parser boundary
      bit1 = hidden same-pitch retrigger
      bit2 = visible period attack
      bit3 = composite pulse1+triangle hidden attack
      bit4 = sounding
    Release classes currently use:
      0 = effectively_muted
      1 = sustain_body
      2 = ringing_decay
      3 = fresh_attack_damped_body
      4 = fresh_full_body
    All data bytes are 7-bit safe (register values 0-127 as-is,
    values 128-255 split into two 7-bit bytes: low7, high1).
    """
    if period_fn is None:
        period_fn = period_to_midi
    if source_text is None:
        source_text = 'NSF emulation (6502 + APU capture)'
    note_boundary_map = {}
    for ch_name in ("pulse1", "pulse2", "triangle", "noise"):
        note_boundary_map[ch_name] = set(note_boundaries.get(ch_name, set())) if note_boundaries is not None else set()
    # Expansion channels get empty boundary sets
    for ch_name in channels:
        if ch_name not in note_boundary_map:
            note_boundary_map[ch_name] = set()
    mid = mido.MidiFile(ticks_per_beat=TICKS_PER_BEAT)

    # Sanitize text for MIDI meta fields (mido uses latin-1 encoding)
    def _midi_safe(s):
        return s.encode('latin-1', errors='replace').decode('latin-1')

    # Track 0: metadata
    meta_track = mido.MidiTrack()
    meta_track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(128.6)))
    meta_track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4))
    meta_track.append(mido.MetaMessage('text', text=_midi_safe(f'Game: {game_title}')))
    meta_track.append(mido.MetaMessage('text', text=_midi_safe(f'Song: {song_name}')))
    meta_track.append(mido.MetaMessage('text', text=f'Source: {source_text}'))
    meta_track.append(mido.MetaMessage('text', text=f'Track: {song_num}'))
    mid.tracks.append(meta_track)

    # Channel tracks
    track_configs = [
        ("pulse1", "Square 1 [lead]", 0, 80),
        ("pulse2", "Square 2 [harmony]", 1, 81),
        ("triangle", "Triangle [bass]", 2, 38),
        ("noise", "Noise [drums]", 3, 0),
    ]
    # Expansion track configs (only added when channels exist in data)
    if "vrc6_pulse1" in channels:
        track_configs.append(("vrc6_pulse1", "VRC6 Pulse 1", 5, 80))
        track_configs.append(("vrc6_pulse2", "VRC6 Pulse 2", 6, 81))
        track_configs.append(("vrc6_saw", "VRC6 Sawtooth", 7, 82))
    if "fds_wave" in channels:
        track_configs.append(("fds_wave", "FDS Wavetable", 7, 46))

    for ch_name, label, midi_ch, program in track_configs:
        track = mido.MidiTrack()
        track.append(mido.MetaMessage('track_name', name=label))
        if program > 0:
            track.append(mido.Message('program_change', channel=midi_ch, program=program))

        ch_frames = channels[ch_name]["notes"]
        prev_midi = 0
        prev_vol = -1
        prev_duty = -1
        ticks = 0
        boundary_frames = note_boundary_map[ch_name]

        for frame_idx, frame_data in enumerate(ch_frames):
            if ch_name in ("pulse1", "pulse2"):
                period = frame_data["period"]
                vol = frame_data["vol"]
                duty = frame_data["duty"]
                midi_note = period_fn(period) if period > 8 and vol > 0 else 0
                force_retrigger = (
                    frame_idx in boundary_frames
                    and frame_idx > 0
                    and midi_note > 0
                    and prev_midi == midi_note
                )

                # CC12: duty cycle change
                if duty != prev_duty and midi_note > 0:
                    cc_duty = [16, 32, 64, 96][duty]  # map 0-3 to CC range
                    track.append(mido.Message('control_change', channel=midi_ch,
                                             control=12, value=cc_duty, time=ticks))
                    ticks = 0
                    prev_duty = duty

                # CC11: volume envelope
                if vol != prev_vol and midi_note > 0:
                    cc_vol = min(127, vol * 8)
                    track.append(mido.Message('control_change', channel=midi_ch,
                                             control=11, value=cc_vol, time=ticks))
                    ticks = 0
                    prev_vol = vol

                # Note changes, including same-pitch parser boundaries that
                # would otherwise flatten a real re-attack into one sustain.
                if force_retrigger and prev_midi > 0:
                    track.append(mido.Message('note_off', note=prev_midi,
                                              velocity=0, channel=midi_ch, time=ticks))
                    ticks = 0
                    cc_vol = min(127, vol * 8)
                    track.append(mido.Message('control_change', channel=midi_ch,
                                              control=11, value=cc_vol, time=ticks))
                    ticks = 0
                    vel = min(127, vol * 8)
                    track.append(mido.Message('note_on', note=midi_note,
                                              velocity=vel, channel=midi_ch, time=ticks))
                    ticks = 0
                elif midi_note != prev_midi:
                    if prev_midi > 0:
                        track.append(mido.Message('note_off', note=prev_midi,
                                                  velocity=0, channel=midi_ch, time=ticks))
                        ticks = 0
                    if midi_note > 0:
                        vel = min(127, vol * 8)
                        track.append(mido.Message('note_on', note=midi_note,
                                                  velocity=vel, channel=midi_ch, time=ticks))
                        ticks = 0
                    prev_midi = midi_note

            elif ch_name == "triangle":
                period = frame_data["period"]
                linear = frame_data["linear"]
                midi_note = period_fn(period, is_tri=True) if period > 2 and linear > 0 else 0
                force_retrigger = (
                    frame_idx in boundary_frames
                    and frame_idx > 0
                    and midi_note > 0
                    and prev_midi == midi_note
                )

                if force_retrigger and prev_midi > 0:
                    track.append(mido.Message('note_off', note=prev_midi,
                                              velocity=0, channel=midi_ch, time=ticks))
                    ticks = 0
                    track.append(mido.Message('control_change', channel=midi_ch,
                                              control=11, value=127, time=ticks))
                    ticks = 0
                    track.append(mido.Message('note_on', note=midi_note,
                                              velocity=127, channel=midi_ch, time=ticks))
                    ticks = 0
                elif midi_note != prev_midi:
                    if prev_midi > 0:
                        track.append(mido.Message('note_off', note=prev_midi,
                                                  velocity=0, channel=midi_ch, time=ticks))
                        ticks = 0
                    if midi_note > 0:
                        track.append(mido.Message('control_change', channel=midi_ch,
                                                  control=11, value=127, time=ticks))
                        ticks = 0
                        track.append(mido.Message('note_on', note=midi_note,
                                                  velocity=127, channel=midi_ch, time=ticks))
                        ticks = 0
                    prev_midi = midi_note

            elif ch_name == "noise":
                vol = frame_data["vol"]
                period = frame_data["period"]
                mode = frame_data["mode"]

                # Track drum hit state for duration capping
                if not hasattr(frame_data, '_noise_init'):
                    # Use closure vars instead
                    pass

                if vol > 0 and prev_vol <= 0:
                    # New drum hit: map noise period to GM drum note
                    if period <= 4:
                        drum_note = 42  # closed hi-hat
                    elif period <= 8:
                        drum_note = 38  # snare
                    else:
                        drum_note = 36  # kick
                    vel = min(127, vol * 8)
                    track.append(mido.Message('note_on', note=drum_note,
                                             velocity=vel, channel=midi_ch, time=ticks))
                    ticks = 0
                    noise_hit_vol = vol  # remember initial hit volume
                    noise_hit_age = 0   # frames since hit
                elif vol > 0 and prev_vol > 0 and prev_midi > 0:
                    # Drum still sounding — check if it should end
                    noise_hit_age += 1
                    # End drum if: volume dropped to <25% of hit, or >12 frames old
                    if vol <= max(1, noise_hit_vol // 4) or noise_hit_age > 12:
                        track.append(mido.Message('note_off', note=prev_midi,
                                                 velocity=0, channel=midi_ch, time=ticks))
                        ticks = 0
                        prev_midi = 0
                elif vol <= 0 and prev_vol > 0:
                    if prev_midi > 0:
                        track.append(mido.Message('note_off', note=prev_midi,
                                                 velocity=0, channel=midi_ch, time=ticks))
                        ticks = 0
                    prev_midi = 0

                if vol > 0 and prev_midi == 0:
                    prev_midi = drum_note if 'drum_note' in dir() else 42
                prev_vol = vol

            elif ch_name in ("vrc6_pulse1", "vrc6_pulse2"):
                period = frame_data["period"]
                vol = frame_data["vol"]
                duty = frame_data["duty"]
                enable = frame_data.get("enable", 0)
                midi_note = period_fn(period, channel_type="vrc6_pulse") if period > 8 and vol > 0 and enable else 0

                # CC12: VRC6 has 8 duty values (0-7), map to 0-127
                if duty != prev_duty and midi_note > 0:
                    cc_duty = min(127, duty * 16)
                    track.append(mido.Message('control_change', channel=midi_ch,
                                             control=12, value=cc_duty, time=ticks))
                    ticks = 0
                    prev_duty = duty

                # CC11: volume (same 4-bit range as APU pulse)
                if vol != prev_vol and midi_note > 0:
                    cc_vol = min(127, vol * 8)
                    track.append(mido.Message('control_change', channel=midi_ch,
                                             control=11, value=cc_vol, time=ticks))
                    ticks = 0
                    prev_vol = vol

                if midi_note != prev_midi:
                    if prev_midi > 0:
                        track.append(mido.Message('note_off', note=prev_midi,
                                                  velocity=0, channel=midi_ch, time=ticks))
                        ticks = 0
                    if midi_note > 0:
                        vel = min(127, vol * 8)
                        track.append(mido.Message('note_on', note=midi_note,
                                                  velocity=vel, channel=midi_ch, time=ticks))
                        ticks = 0
                    prev_midi = midi_note

            elif ch_name == "vrc6_saw":
                period = frame_data["period"]
                accum_rate = frame_data["accum_rate"]
                enable = frame_data.get("enable", 0)
                midi_note = period_fn(period, channel_type="vrc6_saw") if period > 8 and accum_rate > 0 and enable else 0

                # CC11: accum_rate (6-bit 0-63) scaled to 0-127
                if accum_rate != prev_vol and midi_note > 0:
                    cc_vol = min(127, accum_rate * 2)
                    track.append(mido.Message('control_change', channel=midi_ch,
                                             control=11, value=cc_vol, time=ticks))
                    ticks = 0
                    prev_vol = accum_rate

                if midi_note != prev_midi:
                    if prev_midi > 0:
                        track.append(mido.Message('note_off', note=prev_midi,
                                                  velocity=0, channel=midi_ch, time=ticks))
                        ticks = 0
                    if midi_note > 0:
                        vel = min(127, accum_rate * 2)
                        track.append(mido.Message('note_on', note=midi_note,
                                                  velocity=vel, channel=midi_ch, time=ticks))
                        ticks = 0
                    prev_midi = midi_note

            elif ch_name == "fds_wave":
                period = frame_data.get("period", 0)
                vol_gain = frame_data["vol_gain"]
                master_vol = frame_data.get("master_vol", 0)
                # FDS master volume: 0=1.0, 1=2/3, 2=1/2, 3=2/5
                master_frac = [1.0, 2/3, 1/2, 2/5][min(master_vol, 3)]
                # FDS vol_gain 0-63 (clamped at 32 on HW), scale to CC range
                effective_vol = min(32, vol_gain) * master_frac
                midi_note = period_fn(period, channel_type="fds_wave") if period > 2 and vol_gain > 0 else 0

                # CC11: volume
                cc_vol = min(127, int(effective_vol * 4))
                if cc_vol != prev_vol and midi_note > 0:
                    track.append(mido.Message('control_change', channel=midi_ch,
                                             control=11, value=cc_vol, time=ticks))
                    ticks = 0
                    prev_vol = cc_vol

                if midi_note != prev_midi:
                    if prev_midi > 0:
                        track.append(mido.Message('note_off', note=prev_midi,
                                                  velocity=0, channel=midi_ch, time=ticks))
                        ticks = 0
                    if midi_note > 0:
                        vel = max(1, cc_vol)
                        track.append(mido.Message('note_on', note=midi_note,
                                                  velocity=vel, channel=midi_ch, time=ticks))
                        ticks = 0
                    prev_midi = midi_note

            ticks += TICKS_PER_FRAME

        # Final note off
        if prev_midi > 0:
            track.append(mido.Message('note_off', note=prev_midi,
                                      velocity=0, channel=midi_ch, time=ticks))

        mid.tracks.append(track)

    # Track 5: APU register SysEx stream + audible-state sideband
    if frames is not None:
        sysex_track = mido.MidiTrack()
        sysex_track.append(mido.MetaMessage('track_name', name='APU Registers'))

        # Channel register base addresses
        ch_regs = [
            (0x4000, 0x4001, 0x4002, 0x4003),  # Pulse 1
            (0x4004, 0x4005, 0x4006, 0x4007),  # Pulse 2
            (0x4008, 0x4009, 0x400A, 0x400B),  # Triangle
            (0x400C, 0x400D, 0x400E, 0x400F),  # Noise
        ]

        release_ir_map = {}
        if game_title.lower() == "wizards & warriors" and song_num == 1:
            release_ir_path = (
                REPO_ROOT
                / "extraction"
                / "analysis"
                / "reconciled"
                / "wizards_and_warriors_title_release_ir.json"
            )
            if release_ir_path.exists():
                try:
                    release_ir = json.loads(release_ir_path.read_text(encoding="utf-8"))
                    release_ir_map = {
                        int(row["frame"]): row
                        for row in release_ir.get("frames", [])
                    }
                except Exception:
                    release_ir_map = {}

        release_class_codes = {
            "effectively_muted": 0,
            "sustain_body": 1,
            "ringing_decay": 2,
            "fresh_attack_damped_body": 3,
            "fresh_full_body": 4,
        }

        pulse_env_levels = {"pulse1": 0.0, "pulse2": 0.0}
        pulse_env_step_frames = {"pulse1": 1.0, "pulse2": 1.0}
        pulse_env_time_to_step = {"pulse1": 1.0, "pulse2": 1.0}

        # Build full register state (not just deltas)
        full_state = {}
        for r in range(0x4000, 0x4018):
            full_state[r] = 0
        # Expansion register state
        if "vrc6_pulse1" in channels:
            for r in [0x9000, 0x9001, 0x9002, 0xA000, 0xA001, 0xA002, 0xB000, 0xB001, 0xB002]:
                full_state[r] = 0
        if "fds_wave" in channels:
            for r in [0x4080, 0x4082, 0x4083, 0x4089]:
                full_state[r] = 0

        def channel_period_and_level(ch_name):
            frame_note = channels[ch_name]["notes"][frame_idx]
            if ch_name == "triangle":
                return frame_note["period"], frame_note["linear"]
            if ch_name == "noise":
                return frame_note["period"], frame_note["vol"]
            return frame_note["period"], frame_note["vol"]

        def classify_release(ch_name, frame_idx, period, level, prev_period, prev_level, parser_boundary, hidden_retrigger, visible_period_attack, sounding, prev_sounding):
            title_row = release_ir_map.get(frame_idx)
            if title_row:
                if ch_name == "triangle":
                    return release_class_codes.get(title_row.get("release_class", "sustain_body"), 1)
                if ch_name == "pulse1" and title_row.get("composite_attack"):
                    return release_class_codes["fresh_attack_damped_body"]
            if not sounding:
                return release_class_codes["effectively_muted"]
            if visible_period_attack or (parser_boundary and period != prev_period):
                return release_class_codes["fresh_full_body"]
            if hidden_retrigger:
                return release_class_codes["fresh_attack_damped_body"]
            if prev_sounding and level < prev_level:
                return release_class_codes["ringing_decay"]
            return release_class_codes["sustain_body"]

        def effective_art_level(ch_name, raw_level, sounding, write_mask):
            if ch_name not in ("pulse1", "pulse2"):
                return raw_level
            r0 = full_state[0x4000 if ch_name == "pulse1" else 0x4004]
            const_vol = (r0 >> 4) & 0x01
            env_loop = (r0 >> 5) & 0x01
            env_period = r0 & 0x0F
            if const_vol:
                pulse_env_levels[ch_name] = float(raw_level)
                return raw_level
            step_frames = max(0.25, (env_period + 1) / 4.0)
            pulse_env_step_frames[ch_name] = step_frames
            if write_mask & 0x08:
                pulse_env_levels[ch_name] = 15.0
                pulse_env_time_to_step[ch_name] = step_frames
            elif sounding and pulse_env_levels[ch_name] > 0:
                pulse_env_time_to_step[ch_name] -= 1.0
                while pulse_env_time_to_step[ch_name] <= 0:
                    if pulse_env_levels[ch_name] > 0:
                        pulse_env_levels[ch_name] -= 1.0
                    elif env_loop:
                        pulse_env_levels[ch_name] = 15.0
                    pulse_env_time_to_step[ch_name] += step_frames
            elif not sounding:
                pulse_env_levels[ch_name] = 0.0
                pulse_env_time_to_step[ch_name] = step_frames
            return max(0, min(15, int(round(pulse_env_levels[ch_name]))))

        sysex_count = 0
        frame_count = 0
        for frame_idx, frame_packet in enumerate(frames):
            state = frame_packet["writes"]
            # Update full state with this frame's changes
            for r, v in state:
                full_state[r] = v
            written_regs = {reg for reg, _ in state}

            # $4015 is write-only on real hardware; py65 flat memory often
            # reads back 0x00. Derive enable from volume/period instead:
            # a channel is "enabled" if it has non-zero volume (pulse/noise)
            # or non-zero linear counter (triangle).
            enable = 0
            if (full_state[0x4000] & 0x0F) > 0:  # Pulse 1 vol > 0
                enable |= 1
            if (full_state[0x4004] & 0x0F) > 0:  # Pulse 2 vol > 0
                enable |= 2
            if (full_state[0x4008] & 0x7F) > 0:  # Triangle linear > 0
                enable |= 4
            if (full_state[0x400C] & 0x0F) > 0:  # Noise vol > 0
                enable |= 8

            # Build frame-level articulation flags from note boundaries plus
            # write-aware hidden re-attacks. This is the first playback-facing
            # audible-state layer above raw register replay.
            art_flags = {}
            hidden_channels = set()
            channel_names = ("pulse1", "pulse2", "triangle", "noise")
            for ch_name, regs in zip(channel_names, ch_regs):
                period, level = channel_period_and_level(ch_name)
                prev_period, prev_level = period, level
                if frame_idx > 0:
                    prev_period, prev_level = (
                        channels[ch_name]["notes"][frame_idx - 1]["period"],
                        channels[ch_name]["notes"][frame_idx - 1]["linear"] if ch_name == "triangle" else channels[ch_name]["notes"][frame_idx - 1]["vol"],
                    )
                sounding = (period > 2 and level > 0) if ch_name == "triangle" else (period > 0 and level > 0)
                prev_sounding = (prev_period > 2 and prev_level > 0) if ch_name == "triangle" else (prev_period > 0 and prev_level > 0)
                parser_boundary = frame_idx in note_boundary_map[ch_name]
                visible_period_attack = sounding and prev_sounding and period != prev_period
                write_mask = 0
                for bit_idx, reg in enumerate(regs):
                    if reg in written_regs:
                        write_mask |= (1 << bit_idx)
                art_level = effective_art_level(ch_name, level, sounding, write_mask)
                hidden_retrigger = (
                    frame_idx > 0
                    and parser_boundary
                    and sounding
                    and prev_sounding
                    and period == prev_period
                    and write_mask != 0
                )
                hidden_retrigger and hidden_channels.add(ch_name)
                flags = 0
                if parser_boundary:
                    flags |= 0x01
                if hidden_retrigger:
                    flags |= 0x02
                if visible_period_attack:
                    flags |= 0x04
                if sounding:
                    flags |= 0x10
                release_class = classify_release(
                    ch_name,
                    frame_idx,
                    period,
                    level,
                    prev_period,
                    prev_level,
                    parser_boundary,
                    hidden_retrigger,
                    visible_period_attack,
                    sounding,
                    prev_sounding,
                )
                art_flags[ch_name] = (flags, art_level, write_mask, release_class)

            composite_hidden_attack = (
                "pulse1" in hidden_channels and "triangle" in hidden_channels
            )
            if composite_hidden_attack:
                for ch_name in ("pulse1", "triangle"):
                    flags, level, write_mask, release_class = art_flags[ch_name]
                    art_flags[ch_name] = (flags | 0x08, level, write_mask, release_class)

            # Emit SysEx for each channel
            # Format: F0 7D 01 ch r0_lo r0_hi r1_lo r1_hi r2_lo r2_hi r3_lo r3_hi en F7
            # Each register byte split into two 7-bit values: (val & 0x7F), ((val >> 7) & 0x01)
            first_ch = True
            for ch_idx, regs in enumerate(ch_regs):
                r0 = full_state[regs[0]]
                r1 = full_state[regs[1]]
                r2 = full_state[regs[2]]
                r3 = full_state[regs[3]]
                en = (enable >> ch_idx) & 1
                write_mask = 0
                for bit_idx, reg in enumerate(regs):
                    if reg in written_regs:
                        write_mask |= (1 << bit_idx)

                # SysEx data (after F0, before F7) — all bytes must be 0-127
                data = [
                    0x7D,       # Non-commercial SysEx ID
                    0x02,       # Message type: APU frame + write mask
                    ch_idx,     # Channel 0-3
                    r0 & 0x7F, (r0 >> 7) & 0x01,
                    r1 & 0x7F, (r1 >> 7) & 0x01,
                    r2 & 0x7F, (r2 >> 7) & 0x01,
                    r3 & 0x7F, (r3 >> 7) & 0x01,
                    en,         # Channel enable bit
                    write_mask, # Registers written this frame
                ]

                # Time: first SysEx in frame gets TICKS_PER_FRAME delta,
                # subsequent channels in same frame get delta=0
                if first_ch:
                    delta = TICKS_PER_FRAME
                    first_ch = False
                else:
                    delta = 0

                sysex_track.append(mido.Message('sysex', data=data, time=delta))
                sysex_count += 1

                flags, level, _, release_class = art_flags[channel_names[ch_idx]]
                art_data = [
                    0x7D,
                    0x03,
                    ch_idx,
                    flags & 0x7F,
                    int(level) & 0x7F,
                    int(release_class) & 0x7F,
                ]
                sysex_track.append(mido.Message('sysex', data=art_data, time=0))
                sysex_count += 1

            # Expansion chip SysEx (type 0x04)
            exp_ch_regs = []
            if "vrc6_pulse1" in channels:
                exp_ch_regs.extend([
                    (4, [0x9000, 0x9001, 0x9002]),
                    (5, [0xA000, 0xA001, 0xA002]),
                    (6, [0xB000, 0xB001, 0xB002]),
                ])
            if "fds_wave" in channels:
                exp_ch_regs.append(
                    (7, [0x4080, 0x4082, 0x4083, 0x4089])
                )
            for exp_ch, exp_regs in exp_ch_regs:
                exp_data = [0x7D, 0x04, exp_ch]
                exp_write_mask = 0
                for bit_idx, reg in enumerate(exp_regs):
                    val = full_state.get(reg, 0)
                    exp_data.extend([val & 0x7F, (val >> 7) & 0x01])
                    if reg in written_regs:
                        exp_write_mask |= (1 << bit_idx)
                # Pad to consistent length if fewer than 4 registers
                while len(exp_regs) < 4:
                    exp_data.extend([0, 0])
                    exp_regs = list(exp_regs) + [0]
                exp_data.append(exp_write_mask)
                sysex_track.append(mido.Message('sysex', data=exp_data, time=0))
                sysex_count += 1

            frame_count += 1

        mid.tracks.append(sysex_track)
        print(f"    SysEx: {sysex_count} messages ({frame_count} frames)")

    return mid


def build_rpp(midi_path, song_name, duration_sec):
    """Generate a REAPER project file with ReapNES_APU.jsfx."""
    midi_abs = str(Path(midi_path).resolve())
    jsfx_rel = str(JSFX_PATH.relative_to(REPO_ROOT)) if JSFX_PATH.exists() else "studio/jsfx/ReapNES_APU.jsfx"

    tracks = [
        ("NES - Pulse 1", 0, 16576606),
        ("NES - Pulse 2", 1, 10092441),
        ("NES - Triangle", 2, 16744192),
        ("NES - Noise / Drums", 3, 11184810),
    ]

    rpp_lines = [
        '<REAPER_PROJECT 0.1 "7.0"',
        f'  TEMPO 128.6 4 4',
    ]

    for track_name, midi_ch, color in tracks:
        rpp_lines.extend([
            '  <TRACK',
            f'    NAME "{track_name}"',
            f'    PEAKCOL {color}',
            '    <ITEM',
            f'      POSITION 0',
            f'      LENGTH {duration_sec:.6f}',
            '      <SOURCE MIDI',
            f'        FILE "{midi_abs}"',
            '      >',
            '    >',
            '  >',
        ])

    rpp_lines.append('>')
    return '\n'.join(rpp_lines)


def _apu_nonlinear_mix(sq1, sq2, tri, noise, dpcm=0):
    """NES APU non-linear mixing (from NESDev wiki / FamiTracker source).

    The NES DAC uses impedance-based mixing where channels on the same
    output pin interact non-linearly:
      Pulse output:  95.88 / ((8128.0 / (sq1 + sq2)) + 100.0)
      TND output:    159.79 / ((1.0 / (tri/8227 + noise/12241 + dpcm/22638)) + 100.0)

    sq1/sq2 are 0-15, tri is 0-15, noise is 0-15, dpcm is 0-127.
    Output range is approximately 0.0 to 1.0.
    """
    # Pulse pin: two pulse channels share one DAC
    sq_sum = sq1 + sq2
    if sq_sum > 0:
        pulse_out = 95.88 / ((8128.0 / sq_sum) + 100.0)
    else:
        pulse_out = 0.0

    # TND pin: triangle, noise, DPCM share another DAC
    tnd_denom = 0.0
    if tri > 0:
        tnd_denom += tri / 8227.0
    if noise > 0:
        tnd_denom += noise / 12241.0
    if dpcm > 0:
        tnd_denom += dpcm / 22638.0
    if tnd_denom > 0:
        tnd_out = 159.79 / ((1.0 / tnd_denom) + 100.0)
    else:
        tnd_out = 0.0

    return pulse_out + tnd_out


def render_wav(channels, output_path, num_frames):
    """Render WAV from channel data using hardware-accurate non-linear mixing."""
    # Clamp to actual captured frames (may be shorter due to silence detection)
    actual_frames = len(channels["pulse1"]["notes"])
    num_frames = min(num_frames, actual_frames)
    total_samples = num_frames * SPF
    mix = np.zeros(total_samples, dtype=np.float64)
    phase = {"p1": 0.0, "p2": 0.0, "tri": 0.0}

    for frame in range(num_frames):
        s = frame * SPF
        e = s + SPF

        # Generate per-channel waveforms as amplitude values (0-15 scale)
        p1_wave = np.zeros(SPF)
        p2_wave = np.zeros(SPF)
        tri_wave = np.zeros(SPF)
        noise_wave = np.zeros(SPF)

        for ch_name, ph_key, out_arr in [
            ("pulse1", "p1", p1_wave), ("pulse2", "p2", p2_wave)
        ]:
            fd = channels[ch_name]["notes"][frame]
            p, v, d = fd["period"], fd["vol"], fd["duty"]
            if p >= 8 and v > 0:
                freq = 1789773 / (16 * (p + 1))
                dv = [0.125, 0.25, 0.5, 0.75][d]
                pa = (np.arange(SPF) * freq / SAMPLE_RATE + phase[ph_key]) % 1.0
                # Pulse output: v when high, 0 when low (NES pulse is unipolar 0-15)
                out_arr[:] = np.where(pa < dv, v, 0)
                phase[ph_key] = (phase[ph_key] + SPF * freq / SAMPLE_RATE) % 1.0

        fd = channels["triangle"]["notes"][frame]
        p = fd["period"]
        lin = fd["linear"]
        if p >= 2 and lin > 0:
            freq = 1789773 / (32 * (p + 1))
            pa = (np.arange(SPF) * freq / SAMPLE_RATE + phase["tri"]) % 1.0
            # Triangle output: 0-15 ramp up, 15-0 ramp down (unipolar)
            tri_wave[:] = np.where(pa < 0.5, pa * 30, (1.0 - pa) * 30)
            phase["tri"] = (phase["tri"] + SPF * freq / SAMPLE_RATE) % 1.0

        fd = channels["noise"]["notes"][frame]
        nv = fd["vol"]
        if nv > 0:
            noise_wave[:] = np.random.uniform(0, nv, SPF)

        # Apply non-linear mixing per sample
        for i in range(SPF):
            mix[s + i] = _apu_nonlinear_mix(
                p1_wave[i], p2_wave[i], tri_wave[i], noise_wave[i]
            )

    # Center around zero (NES output is 0-1, audio needs AC coupling)
    mix -= np.mean(mix)
    pk = np.max(np.abs(mix))
    if pk > 0:
        mix = mix / pk * 0.9
    audio = (mix * 32767).astype(np.int16)

    with wave.open(output_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    return len(audio) / SAMPLE_RATE


def process_song(emu, song_num, song_name, duration_sec, output_dir, skip_wav=False):
    """Process one song: emulate, extract MIDI, build REAPER project, optionally render WAV."""
    # Sanitize for Windows filenames: strip all illegal/control chars + Unicode replacement char
    _ctrl = ''.join(chr(c) for c in range(32))  # all control chars (0x00-0x1F)
    _bad = str.maketrans('', '', '[]:\ufffd?*"<>|/\\' + _ctrl)
    game_slug = emu.title.replace(' ', '_').translate(_bad)
    song_slug = song_name.replace(' ', '_').translate(_bad).replace("'", "")

    duration_frames = int(duration_sec * 60)
    print(f"  Emulating ({duration_frames} frames)...", end="", flush=True)
    frames = emu.play_song(song_num, duration_frames)
    print(f" done")

    print(f"  Extracting channel data...", end="", flush=True)
    channels = frames_to_channel_data(frames, expansion_chips=emu.expansion_chips)
    print(f" done")

    # MIDI
    midi_dir = os.path.join(output_dir, "midi")
    os.makedirs(midi_dir, exist_ok=True)
    note_boundaries = load_wizards_and_warriors_note_boundaries(emu.nsf_path, song_num)
    mid = build_midi(channels, emu.title, song_name, song_num, frames=frames, note_boundaries=note_boundaries)
    midi_path = os.path.join(midi_dir, f"{game_slug}_{song_num:02d}_{song_slug}_v1.mid")
    mid.save(midi_path)

    note_counts = [sum(1 for m in t if m.type == 'note_on') for t in mid.tracks[1:]]
    cc_counts = [sum(1 for m in t if m.type == 'control_change') for t in mid.tracks[1:]]
    print(f"  MIDI: {midi_path}")
    print(f"    Notes: P1={note_counts[0]} P2={note_counts[1]} Tri={note_counts[2]} Noise={note_counts[3]}")
    print(f"    CCs:   P1={cc_counts[0]} P2={cc_counts[1]} Tri={cc_counts[2]}")

    # REAPER project (via generate_project.py — the canonical RPP builder)
    rpp_dir = os.path.join(output_dir, "reaper")
    os.makedirs(rpp_dir, exist_ok=True)
    rpp_path = os.path.join(rpp_dir, f"{game_slug}_{song_num:02d}_{song_slug}_v1.rpp")
    import subprocess
    gen_script = os.path.join(os.path.dirname(__file__), "generate_project.py")
    subprocess.run([
        sys.executable, gen_script,
        "--midi", midi_path, "--nes-native",
        "-o", rpp_path,
    ], check=True)
    print(f"  REAPER: {rpp_path}")

    # WAV preview (optional — skip in batch mode for speed)
    wav_path = None
    if not skip_wav:
        wav_dir = os.path.join(output_dir, "wav")
        os.makedirs(wav_dir, exist_ok=True)
        wav_path = os.path.join(wav_dir, f"{game_slug}_{song_num:02d}_{song_slug}_v1.wav")
        dur = render_wav(channels, wav_path, duration_frames)
        print(f"  WAV: {wav_path} ({dur:.1f}s)")

    # Pipeline hook: record evidence for this song
    if _hooks:
        _bad_slug = str.maketrans('', '', '[]:\ufffd?*"<>|/\\' + _ctrl)
        _hooks.on_song_extracted(
            game_slug=game_slug,
            song_num=song_num,
            midi_path=midi_path,
            note_counts=note_counts,
            cc_counts=cc_counts,
            frame_count=len(frames),
            expansion_chips=emu.expansion_chips if emu.expansion_chips else None,
        )

    return midi_path, rpp_path, wav_path


def main():
    parser = argparse.ArgumentParser(description='NSF to MIDI + REAPER converter')
    parser.add_argument('nsf', help='Path to NSF file')
    parser.add_argument('song', nargs='?', help='Song number or --all')
    parser.add_argument('seconds', nargs='?', type=float, default=90, help='Duration in seconds')
    parser.add_argument('-o', '--output', default='output', help='Output directory')
    parser.add_argument('--all', action='store_true', help='Process all songs')
    parser.add_argument('--names', help='Comma-separated track names')
    parser.add_argument('--names-json', help='Path to JSON file with track names array')
    parser.add_argument('--skip-wav', action='store_true', help='Skip WAV preview render (faster batch)')
    args = parser.parse_args()

    emu = NsfEmulator(args.nsf)
    print(f"NSF: {emu.title} by {emu.artist}")
    print(f"Songs: {emu.total_songs}")
    if emu.expansion_chips:
        print(f"Expansion: {', '.join(emu.expansion_chips)} (0x{emu.expansion_flags:02x})")

    if args.all or args.song == '--all':
        if args.names_json:
            with open(args.names_json, 'r', encoding='utf-8') as f:
                names = json.load(f)
        elif args.names:
            names = args.names.split(',')
        else:
            names = [f"Song {i}" for i in range(1, emu.total_songs + 1)]

        for i in range(emu.total_songs):
            song_num = i + 1
            name = names[i].strip() if i < len(names) else f"Song {song_num}"
            dur = args.seconds

            print(f"\n=== Song {song_num}: {name} ===")
            process_song(emu, song_num, name, dur, args.output, skip_wav=args.skip_wav)
    else:
        song_num = int(args.song)
        name = f"Song {song_num}"
        print(f"\n=== Song {song_num} ===")
        process_song(emu, song_num, name, args.seconds, args.output)


if __name__ == "__main__":
    main()
