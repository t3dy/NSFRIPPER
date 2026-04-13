"""Wizards & Warriors NSF/ROM music-driver inspector and structural parser.

This module is intentionally game-specific and discovery-stage.
It codifies only the behavior that has been directly observed from the
Wizards & Warriors NSF image so far:

- NSF init/play entry points
- song -> 4 channel pointers via init emulation
- command dispatch for bytes < 0x10
- two note forms observed in the title music:
  * table-note  (bit 7 set)
  * direct-note (0x10-0x7F)

It does NOT claim execution-semantics validation yet.
The goal is to make discoveries reproducible and keep hypotheses explicit.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from py65.devices.mpu6502 import MPU


NSF_LOAD_ADDR = 0x8000
NSF_INIT_ADDR = 0xFFC0
NSF_PLAY_ADDR = 0xEE55

TITLE_TRACK_NUMBER = 1

CHANNEL_NAMES = ("pulse1", "pulse2", "triangle", "noise")
CHANNEL_BASES = (0x00, 0x04, 0x08, 0x0C)

# Observed tables from disassembly of the NSF image.
SONG_POINTER_TABLE_ADDR = 0xEC6F
SONG_SELECTOR_TABLE_ADDR = 0xFFD0
TABLE_NOTE_PERIOD_ADDR = 0xEFD9
DIRECT_PERIOD_TABLE_ADDR = 0xF000
COMMAND_DISPATCH_ADDR = 0xEEEE

# Provisional command handler map recovered from $EEEE.
COMMAND_HANDLERS = {
    0x00: 0xEF04,
    0x01: 0xEF74,
    0x02: 0xEF27,
    0x03: 0xEF33,
    0x04: 0xEF5E,
    0x05: 0xEF8C,
    0x06: 0xEFBF,
    0x07: 0xEF4A,
    0x08: 0xEF41,
    0x09: 0xEF37,
    0x0A: 0xEF54,
}


@dataclass
class CommandEvent:
    offset_cpu: int
    command: int
    params: list[int]
    description: str


@dataclass
class TableNoteEvent:
    offset_cpu: int
    raw_byte: int
    note_index: int
    period: int
    duration: int | None


@dataclass
class DirectNoteEvent:
    offset_cpu: int
    control_byte: int
    volume_nibble: int
    period_high_bits: int
    period_low_byte: int
    period: int
    duration: int | None


@dataclass
class ChannelInitEvent:
    offset_cpu: int
    reg_4000_or_4004: int
    reg_4001_or_4005: int
    reg_4003_or_4007: int


@dataclass
class StopEvent:
    offset_cpu: int


@dataclass
class JumpEvent:
    offset_cpu: int
    target_cpu: int


@dataclass
class LoopCallEvent:
    offset_cpu: int
    loop_count: int
    target_cpu: int


@dataclass
class LoopReturnEvent:
    offset_cpu: int


@dataclass
class ParsedChannel:
    channel: str
    start_cpu: int
    events: list[object]
    bytes_consumed: int
    ended_by_loop: bool


@dataclass
class SongPointers:
    song_number: int
    channel_pointers: dict[str, int]
    channel_flags: dict[str, int]


@dataclass
class ChannelSummary:
    channel: str
    start_cpu: int
    event_count: int
    bytes_consumed: int
    terminal_event: str
    ended_by_loop: bool


@dataclass
class SongSummary:
    song_number: int
    channels: dict[str, ChannelSummary]


class WizardsAndWarriorsParser:
    """Discovery-stage parser for Wizards & Warriors."""

    def __init__(self, image_path: str | Path):
        self.path = Path(image_path)
        data = self.path.read_bytes()
        self.is_nsf = data[:5] == b"NESM\x1a"
        self.image = data[128:] if self.is_nsf else data[16:]
        self.load_addr = NSF_LOAD_ADDR if self.is_nsf else NSF_LOAD_ADDR

        self.table_note_periods = self._read_word_table_le(TABLE_NOTE_PERIOD_ADDR, 64)
        self.direct_periods = self._read_word_table_be(DIRECT_PERIOD_TABLE_ADDR, 32)

    def _cpu_to_offset(self, cpu_addr: int) -> int:
        return cpu_addr - self.load_addr

    def read_byte(self, cpu_addr: int) -> int:
        return self.image[self._cpu_to_offset(cpu_addr)]

    def read_word(self, cpu_addr: int) -> int:
        off = self._cpu_to_offset(cpu_addr)
        lo = self.image[off]
        hi = self.image[off + 1]
        return (hi << 8) | lo

    def _read_word_table_le(self, start_cpu: int, count: int) -> list[int]:
        values = []
        for i in range(count):
            values.append(self.read_word(start_cpu + i * 2))
        return values

    def _read_word_table_be(self, start_cpu: int, count: int) -> list[int]:
        values = []
        for i in range(count):
            off = self._cpu_to_offset(start_cpu + i * 2)
            hi = self.image[off]
            lo = self.image[off + 1]
            values.append((hi << 8) | lo)
        return values

    def emulate_song_init(self, song_index_zero_based: int) -> SongPointers:
        """Run the NSF init routine and recover the active song's 4 channel pointers."""
        cpu = MPU()
        for i in range(0x10000):
            cpu.memory[i] = 0
        for i, byte in enumerate(self.image):
            addr = self.load_addr + i
            if addr < 0x10000:
                cpu.memory[addr] = byte

        cpu.memory[0x4700] = 0x60  # RTS sentinel
        cpu.sp = 0xFD
        cpu.stPushWord(0x46FE)
        cpu.a = song_index_zero_based
        cpu.x = 0
        cpu.y = 0
        cpu.pc = NSF_INIT_ADDR
        cpu.p = 0x04

        cycles = 0
        while cycles < 200000 and cpu.pc not in (0x46FF, 0x4700):
            cpu.step()
            cycles += 1

        channel_pointers = {}
        channel_flags = {}
        for name, base in zip(CHANNEL_NAMES, CHANNEL_BASES):
            lo = cpu.memory[0x0782 + base]
            hi = cpu.memory[0x0783 + base]
            channel_pointers[name] = (hi << 8) | lo
            channel_flags[name] = cpu.memory[0x0780 + base]

        return SongPointers(
            song_number=song_index_zero_based + 1,
            channel_pointers=channel_pointers,
            channel_flags=channel_flags,
        )

    def extract_all_song_pointers(self, total_songs: int = 16) -> list[SongPointers]:
        return [self.emulate_song_init(i) for i in range(total_songs)]

    def summarize_song(self, song_number: int, *, max_events: int = 512) -> SongSummary:
        pointers = self.emulate_song_init(song_number - 1)
        channels: dict[str, ChannelSummary] = {}
        for channel, start_cpu in pointers.channel_pointers.items():
            parsed = self.parse_channel(start_cpu, channel, max_events=max_events)
            terminal = type(parsed.events[-1]).__name__ if parsed.events else "None"
            channels[channel] = ChannelSummary(
                channel=channel,
                start_cpu=start_cpu,
                event_count=len(parsed.events),
                bytes_consumed=parsed.bytes_consumed,
                terminal_event=terminal,
                ended_by_loop=parsed.ended_by_loop,
            )
        return SongSummary(song_number=song_number, channels=channels)

    def summarize_all_songs(self, total_songs: int = 16, *, max_events: int = 512) -> list[SongSummary]:
        return [self.summarize_song(song_number, max_events=max_events) for song_number in range(1, total_songs + 1)]

    def parse_channel(
        self,
        start_cpu: int,
        channel: str,
        *,
        max_events: int = 512,
        visit_limit: int = 4,
    ) -> ParsedChannel:
        """Parse one channel stream using the currently observed structural rules.

        This is a structural parse only. It is useful for:
        - byte-stream alignment
        - command inventory
        - note-form classification
        - pointer/loop tracing
        """
        ptr = start_cpu
        events: list[object] = []
        bytes_consumed = 0
        ended_by_loop = False
        persistent_duration: int | None = None
        call_stack: list[tuple[int, int, int]] = []
        visits: dict[int, int] = {}

        init_regs = [self.read_byte(ptr), self.read_byte(ptr + 1), self.read_byte(ptr + 2)]
        events.append(ChannelInitEvent(ptr, init_regs[0], init_regs[1], init_regs[2]))
        ptr += 3
        bytes_consumed += 3

        for _ in range(max_events):
            visits[ptr] = visits.get(ptr, 0) + 1
            if visits[ptr] > visit_limit:
                ended_by_loop = True
                break

            opcode = self.read_byte(ptr)

            if opcode < 0x10:
                if opcode == 0x00:
                    events.append(StopEvent(offset_cpu=ptr))
                    bytes_consumed += 1
                    break

                if opcode == 0x01:
                    target = self.read_word(ptr + 1)
                    events.append(JumpEvent(offset_cpu=ptr, target_cpu=target))
                    bytes_consumed += 3
                    ptr = target
                    continue

                if opcode == 0x02:
                    events.append(CommandEvent(ptr, opcode, [], "clear flag bit 0 and continue"))
                    ptr += 1
                    bytes_consumed += 1
                    continue

                if opcode == 0x03:
                    arg = self.read_byte(ptr + 1)
                    events.append(CommandEvent(ptr, opcode, [arg], "skip one parameter byte and continue"))
                    ptr += 2
                    bytes_consumed += 2
                    continue

                if opcode == 0x04:
                    params = [self.read_byte(ptr + 1), self.read_byte(ptr + 2), self.read_byte(ptr + 3)]
                    events.append(CommandEvent(ptr, opcode, params, "load 3-byte channel register shadow"))
                    ptr += 4
                    bytes_consumed += 4
                    continue

                if opcode == 0x05:
                    loop_count = self.read_byte(ptr + 1)
                    target = self.read_word(ptr + 2)
                    call_stack.append((ptr + 4, loop_count, target))
                    events.append(LoopCallEvent(ptr, loop_count, target))
                    ptr = target
                    bytes_consumed += 4
                    continue

                if opcode == 0x06:
                    events.append(LoopReturnEvent(offset_cpu=ptr))
                    bytes_consumed += 1
                    if call_stack:
                        return_ptr, remaining, target = call_stack[-1]
                        if remaining > 1:
                            call_stack[-1] = (return_ptr, remaining - 1, target)
                            ptr = target
                        else:
                            call_stack.pop()
                            ptr = return_ptr
                        continue
                    ptr += 1
                    continue

                if opcode == 0x07:
                    arg = self.read_byte(ptr + 1)
                    persistent_duration = arg
                    events.append(CommandEvent(ptr, opcode, [arg], "set per-channel duration mode byte"))
                    ptr += 2
                    bytes_consumed += 2
                    continue

                if opcode == 0x08:
                    persistent_duration = None
                    events.append(CommandEvent(ptr, opcode, [], "force inline-duration sentinel"))
                    ptr += 1
                    bytes_consumed += 1
                    continue

                if opcode == 0x09:
                    arg = self.read_byte(ptr + 1)
                    events.append(CommandEvent(ptr, opcode, [arg], "set global frame-delay reload"))
                    ptr += 2
                    bytes_consumed += 2
                    continue

                if opcode == 0x0A:
                    arg = self.read_byte(ptr + 1)
                    events.append(CommandEvent(ptr, opcode, [arg], "write single channel control-shadow byte"))
                    ptr += 2
                    bytes_consumed += 2
                    continue

                events.append(CommandEvent(ptr, opcode, [], "unknown command below 0x10"))
                bytes_consumed += 1
                break

            if opcode & 0x80:
                note_index = opcode & 0x7F
                period = self.table_note_periods[note_index] if note_index < len(self.table_note_periods) else 0
                if persistent_duration is None:
                    duration = self.read_byte(ptr + 1)
                    consumed = 2
                else:
                    duration = persistent_duration
                    consumed = 1
                events.append(
                    TableNoteEvent(
                        offset_cpu=ptr,
                        raw_byte=opcode,
                        note_index=note_index,
                        period=period,
                        duration=duration,
                    )
                )
                ptr += consumed
                bytes_consumed += consumed
                continue

            volume_nibble = (opcode >> 4) & 0x0F
            period_high_bits = opcode & 0x07
            period_low_byte = self.read_byte(ptr + 1)
            period = (period_high_bits << 8) | period_low_byte
            duration = persistent_duration
            events.append(
                DirectNoteEvent(
                    offset_cpu=ptr,
                    control_byte=opcode,
                    volume_nibble=volume_nibble,
                    period_high_bits=period_high_bits,
                    period_low_byte=period_low_byte,
                    period=period,
                    duration=duration,
                )
            )
            consumed = 2
            ptr += consumed
            bytes_consumed += consumed

        return ParsedChannel(
            channel=channel,
            start_cpu=start_cpu,
            events=events,
            bytes_consumed=bytes_consumed,
            ended_by_loop=ended_by_loop,
        )


def load_default_parser() -> WizardsAndWarriorsParser:
    """Convenience loader for the repo's current Wizards & Warriors NSF reference."""
    return WizardsAndWarriorsParser(
        Path("C:/Dev/NSFRIPPER/state/ww_ref/Wizards & Warriors [Densetsu no Kishi - Elrond] (1987-12)(Rare)(Acclaim).nsf")
    )
