"""Rare NES music driver parser.

Parses music data from Battletoads and other Rare NES ROMs.
Decodes the Rare custom driver command stream, tracks transposition,
follows subroutine calls, and produces note events with correct pitches.

The Rare driver has a dual-mode duration system:
  - Inline mode ($0351,X == 0): each note is followed by a duration byte
  - Persistent mode ($0351,X != 0): CMD 0x06 sets duration for all notes

Usage:
    from extraction.drivers.rare.parser import RareParser

    parser = RareParser("path/to/Battletoads (U) [!].nes")
    result = parser.parse_channel(0xA2CF, "pulse2")
    for event in result.events:
        print(event)
"""
# ---------------------------------------------------------------
# STATUS: IN_PROGRESS
# SCOPE: Battletoads, adaptable to other Rare driver games
# VALIDATED: not yet
# LAYER: static_analysis (ROM parsing)
# ---------------------------------------------------------------

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# iNES header
INES_HEADER_SIZE = 16

# Battletoads: Bank 3, CPU $8000-$FFFF = PRG 0x18000-0x1FFFF
SOUND_BANK_PRG_OFFSET = 0x18000
SOUND_BANK_CPU_BASE = 0x8000

# Period table
PERIOD_TABLE_CPU = 0x8E22
PERIOD_TABLE_ENTRIES = 60

# Note encoding
NOTE_BASE = 0x81   # bytes >= 0x81 are notes
REST_BYTE = 0x80   # 0x80 = rest
# bytes 0x00-0x7F = commands

# NTSC NES CPU clock
NTSC_CPU_CLOCK = 1789773.0

# Standard note names
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Command parameter counts (verified from 6502 disassembly)
# Key: command byte. Value: number of parameter bytes consumed.
CMD_PARAMS = {
    0x00: 0,   # channel off
    0x01: 2,   # absolute jump (addr_lo, addr_hi)
    0x02: 0,   # clear flag bit 0 of $0311,X
    0x03: 3,   # set envelope (3 params -> $0321, $0322, $0324)
    0x04: 0,   # return from subroutine (restores saved pointer)
    0x05: 0,   # loop decrement (dec $0343,X; if >0 re-enter loop)
    0x06: 1,   # set persistent duration ($0351,X = param)
    0x07: 0,   # clear persistent duration ($0351,X = 0, inline mode)
    0x08: 3,   # set instrument via $8CC4 subroutine (3 bytes)
    0x09: 0,   # clear $0361,X
    0x0A: 5,   # complex: $8D08 subroutine (4 bytes) + 1 byte
    0x0B: 5,   # complex: $8D08 subroutine (4 bytes) + 1 byte via $8CFC
    0x0C: 1,   # volume/envelope mode ($0393,X=0, param -> $0352)
    0x0D: 3,   # arpeggio/tremolo setup ($0393,X=1, 3 params)
    0x0E: 3,   # alternate arpeggio ($0393,X=2, 3 params)
    0x0F: 0,   # clear $0393,X (disable arpeggio)
    0x10: 1,   # set tempo (absolute: $33 = 0 + param)
    0x11: 1,   # add to tempo (relative: $33 = $33 + param)
    0x12: 1,   # set transposition absolute ($0354,X = param)
    0x13: 1,   # add to transposition relative ($0354,X += param)
    0x14: 1,   # set transposition ALL channels ($0354/58/5C/60 = param)
    0x15: 0,   # clear $0371,X
    0x16: 3,   # vibrato setup (falls through to $8D66/CMD 0x0D body)
    0x17: 4,   # set instrument via $8CC4 (3 bytes) + duty ($0364,X, 1 byte)
    0x18: 1,   # set $40 = $81, $3F = param
    0x19: 1,   # set $40 = $82, $3F = param (shares 0x18 body)
    0x1A: 1,   # set $40 = $83, $3F = param
    0x1B: 1,   # set $40 = $84, $3F = param
    0x1C: 3,   # set $42, $4F, call $855E (3 params)
    0x1D: 1,   # set $40 = $85, $3F = param
    0x1E: 3,   # subroutine call (loop_count, target_lo, target_hi)
    0x1F: 2,   # set $03A2,X and $03A3,X (2 params, DEY undoes 3rd INY)
    0x20: 0,   # clear $03A2,X (disable envelope override)
    0x21: 0,   # clear $0351,X + set $03A2,X (inline duration + flag)
    0x22: 0,   # set $03A2,X = $80 (enable note-has-envelope flag)
    0x23: 2,   # call subroutine (saves addr to $03A4/$03A8, target_lo, target_hi)
    0x24: 1,   # save address + param to $03AC/$03B0 area
    0x25: 0,   # restore address from $03A4/$03A8 area
    0x26: 0,   # restore address from $03AC/$03B0 area
}

# Max command byte
MAX_CMD = 0x26


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class NoteEvent:
    """A single note in the parsed output."""
    offset: int           # byte offset in ROM data
    raw_byte: int         # original note byte
    raw_index: int        # byte - NOTE_BASE
    transposition: int    # transposition register at time of note
    final_index: int      # raw_index + transposition
    period: int           # period table lookup result (0 if out of range)
    midi_note: int        # MIDI note number
    pitch_name: str       # e.g. "E2", "G4"
    duration: int         # duration counter value
    duration_source: str  # "inline" or "persistent"


@dataclass
class RestEvent:
    """A rest (silence)."""
    offset: int
    duration: int
    duration_source: str


@dataclass
class CommandEvent:
    """A driver command."""
    offset: int
    cmd: int
    params: list[int]
    description: str


@dataclass
class LoopPoint:
    """A loop-back jump (song repeat)."""
    offset: int
    target_cpu: int


@dataclass
class ParseResult:
    """Result of parsing one channel."""
    channel: str
    start_cpu: int
    events: list           # NoteEvent | RestEvent | CommandEvent | LoopPoint
    notes: list[NoteEvent]
    rests: list[RestEvent]
    commands: list[CommandEvent]
    errors: list[str]
    bytes_consumed: int


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class RareParser:
    """Parse Rare NES music driver data from ROM."""

    def __init__(self, rom_path: str | Path, bank_prg_offset: int = SOUND_BANK_PRG_OFFSET):
        self.rom_path = Path(rom_path)
        self.bank_prg_offset = bank_prg_offset

        with open(self.rom_path, 'rb') as f:
            self.rom = f.read()

        # Load period table
        self.period_table = self._load_period_table()

    def _cpu_to_file(self, cpu_addr: int) -> int:
        """Convert CPU address to file offset."""
        return (cpu_addr - SOUND_BANK_CPU_BASE) + self.bank_prg_offset + INES_HEADER_SIZE

    def _load_period_table(self) -> list[int]:
        """Load the period table from ROM.

        Reads 128 entries (not just 60) to handle extended range notes
        that the driver accesses by reading past the table boundary.
        """
        offset = self._cpu_to_file(PERIOD_TABLE_CPU)
        table = []
        for i in range(128):
            lo = self.rom[offset + i * 2]
            hi = self.rom[offset + i * 2 + 1]
            table.append((hi << 8) | lo)
        return table

    def _period_to_midi(self, period: int, is_triangle: bool = False) -> int:
        """Convert NES period to MIDI note number."""
        if period <= 0:
            return 0
        freq = NTSC_CPU_CLOCK / (16.0 * (period + 1))
        if is_triangle:
            freq /= 2.0  # triangle is 1 octave lower
        # MIDI note = 69 + 12 * log2(freq / 440)
        import math
        if freq <= 0:
            return 0
        midi = 69 + 12 * math.log2(freq / 440.0)
        return max(0, min(127, round(midi)))

    def _index_to_pitch_name(self, index: int) -> str:
        """Convert period table index to pitch name."""
        if index < 0:
            return f"?{index}"
        octave = 2 + index // 12
        note = NOTE_NAMES[index % 12]
        return f"{note}{octave}"

    def read_byte(self, cpu_addr: int) -> int:
        """Read one byte at a CPU address."""
        return self.rom[self._cpu_to_file(cpu_addr)]

    def parse_channel(
        self,
        start_cpu: int,
        channel: str = "unknown",
        is_triangle: bool = False,
        max_bytes: int = 4096,
        max_events: int = 2000,
    ) -> ParseResult:
        """Parse one channel's song data starting at the given CPU address.

        Follows subroutine calls (CMD 0x1E), tracks transposition (CMD 0x12/0x13),
        handles dual-mode duration (CMD 0x06/0x07), and detects loop points (CMD 0x01).
        """
        events = []
        notes = []
        rests = []
        commands = []
        errors = []

        # Driver state
        transposition = 0
        persistent_duration = 0  # 0 = inline mode
        envelope_override = False  # when True, each note has an extra byte
        call_stack = []          # (kind, return_cpu_addr, loop_count)
        visited_addrs = set()    # for loop detection

        ptr = start_cpu
        bytes_read = 0

        while bytes_read < max_bytes and len(events) < max_events:
            if ptr in visited_addrs and not call_stack:
                # We've been here before at the top level = loop point
                events.append(LoopPoint(offset=ptr, target_cpu=ptr))
                break

            visited_addrs.add(ptr)
            file_off = self._cpu_to_file(ptr)
            byte = self.rom[file_off]
            bytes_read += 1

            if byte >= NOTE_BASE:
                # --- NOTE ---
                raw_index = byte - NOTE_BASE
                final_index = raw_index + transposition

                if 0 <= final_index < len(self.period_table):
                    period = self.period_table[final_index]
                    midi = self._period_to_midi(period, is_triangle)
                    pitch = self._index_to_pitch_name(final_index)
                else:
                    period = 0
                    midi = 0
                    pitch = f"OOR({final_index})"
                    errors.append(f"Note index {final_index} out of range at ${ptr:04X}")

                # Consume envelope override byte if flag is set
                env_byte = None
                if envelope_override:
                    ptr += 1
                    env_byte = self.rom[self._cpu_to_file(ptr)]
                    bytes_read += 1

                # Read duration
                if persistent_duration != 0:
                    dur = persistent_duration
                    dur_src = "persistent"
                    ptr += 1
                else:
                    ptr += 1
                    dur = self.rom[self._cpu_to_file(ptr)]
                    dur_src = "inline"
                    bytes_read += 1
                    ptr += 1

                evt = NoteEvent(
                    offset=file_off,
                    raw_byte=byte,
                    raw_index=raw_index,
                    transposition=transposition,
                    final_index=final_index,
                    period=period,
                    midi_note=midi,
                    pitch_name=pitch,
                    duration=dur,
                    duration_source=dur_src,
                )
                events.append(evt)
                notes.append(evt)

            elif byte == REST_BYTE:
                # --- REST ---
                # Envelope override byte may also apply to rests
                if envelope_override:
                    ptr += 1
                    bytes_read += 1  # skip envelope byte for rest

                if persistent_duration != 0:
                    dur = persistent_duration
                    dur_src = "persistent"
                    ptr += 1
                else:
                    ptr += 1
                    dur = self.rom[self._cpu_to_file(ptr)]
                    dur_src = "inline"
                    bytes_read += 1
                    ptr += 1

                evt = RestEvent(offset=file_off, duration=dur, duration_source=dur_src)
                events.append(evt)
                rests.append(evt)

            elif byte <= MAX_CMD:
                # --- COMMAND ---
                cmd = byte
                param_count = CMD_PARAMS.get(cmd, 0)

                # Read parameters
                params = []
                for i in range(param_count):
                    ptr += 1
                    bytes_read += 1
                    params.append(self.rom[self._cpu_to_file(ptr)])

                desc = self._describe_command(cmd, params)
                cmd_evt = CommandEvent(offset=file_off, cmd=cmd, params=params, description=desc)
                events.append(cmd_evt)
                commands.append(cmd_evt)

                # Handle state-modifying commands
                if cmd == 0x00:
                    # Channel off — stop parsing
                    break

                elif cmd == 0x01:
                    # Absolute jump
                    target = params[0] | (params[1] << 8)
                    if target <= start_cpu or target == ptr - 2:
                        # Jump backwards = loop point
                        events.append(LoopPoint(offset=file_off, target_cpu=target))
                        break
                    else:
                        ptr = target
                        continue  # skip the ptr += 1 at bottom

                elif cmd == 0x04:
                    # In the 6502 driver, CMD 0x04 saves current position
                    # to $0313/$0314 and does RTS (exits frame handler).
                    # For our static parser, treat it as "continue" since
                    # we parse the whole song in one pass. But if there's
                    # a call23 on the stack, pop and return.
                    call23_entry = None
                    for i in range(len(call_stack) - 1, -1, -1):
                        if call_stack[i][0] == 'call23':
                            call23_entry = i
                            break
                    if call23_entry is not None:
                        _, return_addr, _ = call_stack.pop(call23_entry)
                        ptr = return_addr
                        continue

                elif cmd == 0x05:
                    # Loop decrement — only for CMD 0x1E loops
                    loop_entry = None
                    for i in range(len(call_stack) - 1, -1, -1):
                        if call_stack[i][0] == 'loop':
                            loop_entry = i
                            break
                    if loop_entry is not None:
                        kind, return_addr, remaining = call_stack[loop_entry]
                        remaining -= 1
                        if remaining > 0:
                            call_stack[loop_entry] = (kind, return_addr, remaining)
                            tgt_lo = self.rom[self._cpu_to_file(return_addr)]
                            tgt_hi = self.rom[self._cpu_to_file(return_addr + 1)]
                            target = tgt_lo | (tgt_hi << 8)
                            ptr = target
                            continue
                        else:
                            call_stack.pop(loop_entry)
                            ptr = return_addr + 2
                            continue
                    else:
                        errors.append(f"CMD 0x05 loop dec with no loop on stack at ${ptr:04X}")

                elif cmd == 0x06:
                    # Set persistent duration
                    persistent_duration = params[0]

                elif cmd == 0x07:
                    # Clear persistent duration (inline mode)
                    persistent_duration = 0

                elif cmd == 0x12:
                    # Set transposition absolute
                    transposition = params[0]

                elif cmd == 0x13:
                    # Add to transposition (signed)
                    val = params[0]
                    if val >= 128:
                        val -= 256  # signed byte
                    transposition += val

                elif cmd == 0x14:
                    # Set transposition all channels
                    transposition = params[0]

                elif cmd == 0x1E:
                    # Subroutine call with loop count
                    loop_count = params[0]
                    target = params[1] | (params[2] << 8)

                    # Return address = position of target_lo byte
                    # (6502 saves ptr+Y after 2nd INY = target_lo position)
                    return_addr = ptr - 1  # ptr is at target_hi, -1 = target_lo

                    call_stack.append(('loop', return_addr, loop_count))
                    ptr = target
                    continue

                elif cmd == 0x1F:
                    # Set $03A2,X from param1 — bit 7 controls envelope override
                    envelope_override = (params[0] & 0x80) != 0

                elif cmd == 0x20:
                    # Clear $03A2,X — disable envelope override
                    envelope_override = False

                elif cmd == 0x21:
                    # Clear persistent duration AND envelope override
                    persistent_duration = 0
                    envelope_override = False

                elif cmd == 0x22:
                    # Set $03A2,X = $80 — enable envelope override
                    envelope_override = True

                elif cmd == 0x23:
                    # Call subroutine (no loop count, just jump with return)
                    target = params[0] | (params[1] << 8)
                    # Return address = byte after the target_hi param
                    return_addr = ptr + 1
                    call_stack.append(('call23', return_addr, 1))
                    ptr = target
                    continue

                ptr += 1

            else:
                # Unknown byte
                errors.append(f"Unknown byte 0x{byte:02X} at ${ptr:04X}")
                ptr += 1

        return ParseResult(
            channel=channel,
            start_cpu=start_cpu,
            events=events,
            notes=notes,
            rests=rests,
            commands=commands,
            errors=errors,
            bytes_consumed=bytes_read,
        )

    def _describe_command(self, cmd: int, params: list[int]) -> str:
        """Human-readable description of a command."""
        descs = {
            0x00: "channel off",
            0x01: f"jump to ${params[0] | (params[1] << 8):04X}" if len(params) >= 2 else "jump",
            0x02: "clear note-off flag",
            0x03: f"envelope({', '.join(f'${p:02X}' for p in params)})",
            0x04: "save position / frame end",
            0x05: "loop decrement",
            0x06: f"set duration={params[0]}" if params else "set duration",
            0x07: "inline duration mode",
            0x08: f"instrument({', '.join(f'${p:02X}' for p in params)})",
            0x09: "clear instrument",
            0x0A: f"complex_a({', '.join(f'${p:02X}' for p in params)})",
            0x0B: f"complex_b({', '.join(f'${p:02X}' for p in params)})",
            0x0C: f"vol_mode(${params[0]:02X})" if params else "vol_mode",
            0x0D: f"arpeggio({', '.join(f'${p:02X}' for p in params)})",
            0x0E: f"arpeggio2({', '.join(f'${p:02X}' for p in params)})",
            0x0F: "clear arpeggio",
            0x10: f"set tempo={params[0]}" if params else "set tempo",
            0x11: f"add tempo={params[0]}" if params else "add tempo",
            0x12: f"set transposition={params[0]}" if params else "set transposition",
            0x13: f"add transposition={params[0] if params[0] < 128 else params[0]-256}" if params else "add transpo",
            0x14: f"set all transposition={params[0]}" if params else "set all transpo",
            0x15: "clear vibrato",
            0x16: f"vibrato({', '.join(f'${p:02X}' for p in params)})",
            0x17: f"full_instrument({', '.join(f'${p:02X}' for p in params)})",
            0x18: f"sfx_a(${params[0]:02X})" if params else "sfx_a",
            0x19: f"sfx_b(${params[0]:02X})" if params else "sfx_b",
            0x1A: f"sfx_c(${params[0]:02X})" if params else "sfx_c",
            0x1B: f"sfx_d(${params[0]:02X})" if params else "sfx_d",
            0x1C: f"sfx_e({', '.join(f'${p:02X}' for p in params)})",
            0x1D: f"sfx_f(${params[0]:02X})" if params else "sfx_f",
            0x1E: f"call(count={params[0]}, target=${params[1] | (params[2] << 8):04X})" if len(params) >= 3 else "call",
            0x1F: f"env_override({', '.join(f'${p:02X}' for p in params)})",
            0x20: "clear env_override",
            0x21: "inline_dur + flag",
            0x22: "note_has_envelope",
            0x23: f"call23(target=${params[0] | (params[1] << 8):04X})" if len(params) >= 2 else "call23",
            0x24: f"save_addr(${params[0]:02X})" if params else "save_addr",
            0x25: "restore_addr_a",
            0x26: "restore_addr_b",
        }
        return descs.get(cmd, f"cmd_0x{cmd:02X}({', '.join(f'${p:02X}' for p in params)})")

    def parse_song(self, channel_pointers: dict[str, int]) -> dict[str, ParseResult]:
        """Parse all channels for a song.

        Args:
            channel_pointers: dict mapping channel name to CPU start address.
                e.g. {"pulse1": 0xA15E, "pulse2": 0xA2CF, ...}

        Returns:
            Dict mapping channel name to ParseResult.
        """
        results = {}
        for ch_name, addr in channel_pointers.items():
            is_tri = "tri" in ch_name.lower()
            results[ch_name] = self.parse_channel(addr, ch_name, is_triangle=is_tri)
        return results


def format_parse_result(result: ParseResult) -> str:
    """Format a parse result as human-readable text."""
    lines = []
    lines.append(f"=== {result.channel} (${result.start_cpu:04X}) ===")
    lines.append(f"Events: {len(result.events)} ({len(result.notes)} notes, "
                 f"{len(result.rests)} rests, {len(result.commands)} commands)")
    if result.errors:
        lines.append(f"ERRORS: {len(result.errors)}")
        for e in result.errors:
            lines.append(f"  ! {e}")
    lines.append("")

    for evt in result.events:
        if isinstance(evt, NoteEvent):
            lines.append(
                f"  NOTE {evt.pitch_name:>4s} (midi={evt.midi_note:3d}) "
                f"dur={evt.duration:3d}({evt.duration_source[0]}) "
                f"raw=${evt.raw_byte:02X} idx={evt.raw_index}+{evt.transposition}={evt.final_index}"
            )
        elif isinstance(evt, RestEvent):
            lines.append(f"  REST dur={evt.duration:3d}({evt.duration_source[0]})")
        elif isinstance(evt, CommandEvent):
            lines.append(f"  CMD  0x{evt.cmd:02X} {evt.description}")
        elif isinstance(evt, LoopPoint):
            lines.append(f"  LOOP -> ${evt.target_cpu:04X}")

    return "\n".join(lines)
