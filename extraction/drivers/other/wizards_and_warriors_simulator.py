"""Discovery-stage execution simulator for Wizards & Warriors title pulses.

This is the first step from parser alignment toward execution semantics.
Scope is intentionally narrow:

- title track
- pulse channels only
- per-frame duration countdown
- persistent vs inline duration
- period register projection from parsed events

It compares against the clean second-pass Mesen title capture.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from py65.devices.mpu6502 import MPU

from extraction.drivers.other.wizards_and_warriors_parser import (
    ChannelInitEvent,
    CommandEvent,
    DirectNoteEvent,
    StopEvent,
    TableNoteEvent,
    WizardsAndWarriorsParser,
)


@dataclass
class PulseFrame:
    frame: int
    period: int
    scaled_trace_period: int
    volume: int
    source_event_index: int


@dataclass
class PulseSimResult:
    channel: str
    frames: list[PulseFrame]
    note_starts: list[int]


@dataclass
class TraceCompareResult:
    channel: str
    frames_compared: int
    exact_scaled_period_matches: int
    exact_scaled_period_mismatches: int
    sounding_agreement: int
    sounding_disagreement: int
    first_period_mismatch: int | None


@dataclass
class TriangleFrame:
    frame: int
    period: int
    linear_value: int
    source_event_index: int


@dataclass
class TriangleSimResult:
    frames: list[TriangleFrame]
    note_starts: list[int]


@dataclass
class NoiseRegisterFrame:
    frame: int
    volume: int
    period_index: int
    mode_bit: int
    length_counter_load: int


NOISE_TRIGGER_MAPS: dict[int, dict[int, tuple[int, int, int] | str]] = {
    2: {
        0x80: "hold",
        0xC1: (0, 0, 8),
    },
    6: {
        0x80: "hold",
        0xC3: (2, 0, 16),
    },
    16: {
        0x80: "hold",
        0x99: (11, 1, 17),
        0x8D: (6, 0, 19),
        0x8F: (9, 1, 18),
        0x90: (14, 1, 18),
        0x92: (0, 1, 18),
        0x93: (12, 0, 18),
        0x94: (10, 0, 18),
    },
}


CHANNEL_TO_POINTER_KEY = {
    "pulse1": "pulse1",
    "pulse2": "pulse2",
    "triangle": "triangle",
}


def get_song_tempo_scale(parser: WizardsAndWarriorsParser, song_number: int) -> int:
    """Recover the current best song-level duration scale.

    In songs like Ice Cave and Initial Registration, command 0x09 in pulse1
    scales note/rest durations across the melodic channels.
    """
    song = parser.extract_all_song_pointers()[song_number - 1]
    parsed = parser.parse_channel(song.channel_pointers["pulse1"], "pulse1", max_events=64, visit_limit=16)
    for evt in parsed.events:
        if isinstance(evt, CommandEvent) and evt.command == 0x09 and evt.params:
            return max(1, evt.params[0])
    return 1


def simulate_title_pulse_channel(channel: str) -> PulseSimResult:
    parser = WizardsAndWarriorsParser(
        Path("C:/Dev/NSFRIPPER/state/ww_ref/Wizards & Warriors [Densetsu no Kishi - Elrond] (1987-12)(Rare)(Acclaim).nsf")
    )
    title = parser.extract_all_song_pointers()[0]
    parsed = parser.parse_channel(title.channel_pointers[channel], channel, max_events=512)

    current_period = 0
    current_volume = 0
    counter = 0
    event_index = 0
    frames: list[PulseFrame] = []
    note_starts: list[int] = []

    while len(frames) < 2169 and event_index < len(parsed.events):
        if counter <= 0:
            while event_index < len(parsed.events):
                evt = parsed.events[event_index]
                event_index += 1

                if isinstance(evt, ChannelInitEvent):
                    current_volume = evt.reg_4000_or_4004 & 0x0F
                    continue

                if isinstance(evt, TableNoteEvent):
                    # In this driver, raw 0x80 behaves like "hold current state"
                    # when a note is already sounding, but acts like a rest/hold-zero
                    # at the start of a silent section.
                    if evt.raw_byte != 0x80:
                        current_period = evt.period
                    counter = evt.duration or 0
                    note_starts.append(len(frames) + 1)
                    break

                if isinstance(evt, DirectNoteEvent):
                    current_volume = evt.volume_nibble
                    current_period = evt.period
                    counter = evt.duration or 0
                    note_starts.append(len(frames) + 1)
                    break

            if counter <= 0 and current_period == 0:
                break

        frames.append(
            PulseFrame(
                frame=len(frames) + 1,
                period=current_period,
                scaled_trace_period=(current_period * 2 + 1) if current_period > 0 else 0,
                volume=current_volume,
                source_event_index=event_index,
            )
        )
        if counter > 0:
            counter -= 1

    return PulseSimResult(channel=channel, frames=frames, note_starts=note_starts)


def load_title_trace_channel(channel: str) -> tuple[list[int], list[int]]:
    path = Path("C:/Dev/NSFRIPPER/extraction/traces/wizards_and_warriors/title_capture.csv")
    start_frame = 2721
    end_frame = 4889

    period_param = "$4002_period" if channel == "pulse1" else "$4006_period"
    volume_param = "$4000_vol" if channel == "pulse1" else "$4004_vol"

    updates: dict[int, dict[str, int]] = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            frame = int(row["frame"])
            if frame < start_frame or frame > end_frame:
                continue
            updates.setdefault(frame, {})[row["parameter"]] = int(float(row["value"]))

    period = 0
    volume = 0
    periods = []
    volumes = []
    for frame in range(start_frame, end_frame + 1):
        if frame in updates:
            period = updates[frame].get(period_param, period)
            volume = updates[frame].get(volume_param, volume)
        periods.append(period)
        volumes.append(volume)
    return periods, volumes


def load_title_triangle_trace() -> tuple[list[int], list[int]]:
    path = Path("C:/Dev/NSFRIPPER/extraction/traces/wizards_and_warriors/title_capture.csv")
    start_frame = 2721
    end_frame = 4889

    updates: dict[int, dict[str, int]] = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            frame = int(row["frame"])
            if frame < start_frame or frame > end_frame:
                continue
            updates.setdefault(frame, {})[row["parameter"]] = int(float(row["value"]))

    period = 0
    linear = 0
    periods = []
    linear_values = []
    for frame in range(start_frame, end_frame + 1):
        if frame in updates:
            period = updates[frame].get("$400A_period", period)
            linear = updates[frame].get("$4008_linear", linear)
        periods.append(period)
        linear_values.append(linear)
    return periods, linear_values


def simulate_title_triangle() -> TriangleSimResult:
    parser = WizardsAndWarriorsParser(
        Path("C:/Dev/NSFRIPPER/state/ww_ref/Wizards & Warriors [Densetsu no Kishi - Elrond] (1987-12)(Rare)(Acclaim).nsf")
    )
    title = parser.extract_all_song_pointers()[0]
    parsed = parser.parse_channel(title.channel_pointers["triangle"], "triangle", max_events=512)

    current_period = 0
    current_linear = 0
    counter = 0
    release_remaining = 0
    release_used = False
    event_index = 0
    frames: list[TriangleFrame] = []
    note_starts: list[int] = []

    while len(frames) < 2169:
        if counter <= 0:
            if release_remaining > 0:
                current_linear = 15
                frames.append(
                    TriangleFrame(
                        frame=len(frames) + 1,
                        period=current_period,
                        linear_value=current_linear,
                        source_event_index=event_index,
                    )
                )
                release_remaining -= 1
                if release_remaining == 0:
                    current_linear = 0
                continue

            while event_index < len(parsed.events):
                evt = parsed.events[event_index]
                event_index += 1

                if isinstance(evt, ChannelInitEvent):
                    current_linear = 0
                    continue

                if isinstance(evt, CommandEvent):
                    if evt.command == 0x04 and len(evt.params) == 3:
                        current_linear = evt.params[0] & 0x7F
                    continue

                if isinstance(evt, TableNoteEvent):
                    if evt.raw_byte != 0x80:
                        current_period = evt.period
                    counter = evt.duration or 0
                    note_starts.append(len(frames) + 1)
                    break

                if isinstance(evt, DirectNoteEvent):
                    current_period = evt.period
                    counter = evt.duration or 0
                    note_starts.append(len(frames) + 1)
                    break

            if counter <= 0 and current_period > 0 and event_index >= len(parsed.events) and not release_used:
                release_remaining = 5
                release_used = True
                continue

            if counter <= 0 and current_period == 0 and event_index >= len(parsed.events):
                frames.append(
                    TriangleFrame(
                        frame=len(frames) + 1,
                        period=0,
                        linear_value=0,
                        source_event_index=event_index,
                    )
                )
                continue

        frames.append(
            TriangleFrame(
                frame=len(frames) + 1,
                period=current_period,
                linear_value=current_linear,
                source_event_index=event_index,
            )
        )
        if counter > 0:
            counter -= 1

    return TriangleSimResult(frames=frames, note_starts=note_starts)


def compare_title_noise_inactive() -> TraceCompareResult:
    path = Path("C:/Dev/NSFRIPPER/extraction/traces/wizards_and_warriors/title_capture.csv")
    start_frame = 2721
    end_frame = 4889

    updates: dict[int, dict[str, int]] = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            frame = int(row["frame"])
            if frame < start_frame or frame > end_frame:
                continue
            updates.setdefault(frame, {})[row["parameter"]] = int(float(row["value"]))

    vol = 0
    period = 0
    total = end_frame - start_frame + 1
    disagreements = 0
    first = None
    for i, frame in enumerate(range(start_frame, end_frame + 1), start=1):
        if frame in updates:
            vol = updates[frame].get("$400C_vol", vol)
            period = updates[frame].get("$400E_period", period)
        trace_sounding = vol > 0 or period > 0
        if trace_sounding:
            disagreements += 1
            if first is None:
                first = i

    return TraceCompareResult(
        channel="noise",
        frames_compared=total,
        exact_scaled_period_matches=total - disagreements,
        exact_scaled_period_mismatches=disagreements,
        sounding_agreement=total - disagreements,
        sounding_disagreement=disagreements,
        first_period_mismatch=first,
    )


def capture_nsf_song_channel(song_number: int, channel: str, num_frames: int) -> tuple[list[int], list[int]]:
    """Capture per-frame channel state directly from NSF emulation.

    Returns:
      periods, levels

    For pulse channels, levels are volume register values.
    For triangle, levels are linear-counter values.
    """
    path = Path("C:/Dev/NSFRIPPER/state/ww_ref/Wizards & Warriors [Densetsu no Kishi - Elrond] (1987-12)(Rare)(Acclaim).nsf")
    data = path.read_bytes()
    load = data[8] | (data[9] << 8)
    init = data[10] | (data[11] << 8)
    play = data[12] | (data[13] << 8)
    rom = data[128:]

    cpu = MPU()
    for i in range(0x10000):
        cpu.memory[i] = 0
    for i, byte in enumerate(rom):
        addr = load + i
        if addr < 0x10000:
            cpu.memory[addr] = byte
    cpu.memory[0x4700] = 0x60

    def call(addr: int, a: int = 0, max_cyc: int = 100000) -> None:
        cpu.sp = 0xFD
        cpu.stPushWord(0x46FE)
        cpu.a = a
        cpu.x = 0
        cpu.y = 0
        cpu.pc = addr
        cpu.p = 0x04
        cyc = 0
        while cyc < max_cyc and cpu.pc not in (0x46FF, 0x4700):
            cpu.step()
            cyc += 1

    call(init, a=song_number - 1)

    periods: list[int] = []
    levels: list[int] = []
    for _ in range(num_frames):
        call(play)
        if channel == "pulse1":
            periods.append(cpu.memory[0x4002] | ((cpu.memory[0x4003] & 0x07) << 8))
            levels.append(cpu.memory[0x4000] & 0x0F)
        elif channel == "pulse2":
            periods.append(cpu.memory[0x4006] | ((cpu.memory[0x4007] & 0x07) << 8))
            levels.append(cpu.memory[0x4004] & 0x0F)
        elif channel == "triangle":
            periods.append(cpu.memory[0x400A] | ((cpu.memory[0x400B] & 0x07) << 8))
            levels.append(cpu.memory[0x4008] & 0x7F)
        else:
            raise ValueError(f"Unsupported channel: {channel}")
    return periods, levels


def capture_nsf_noise_registers(song_number: int, num_frames: int) -> list[NoiseRegisterFrame]:
    """Capture per-frame noise register state directly from NSF emulation."""
    path = Path("C:/Dev/NSFRIPPER/state/ww_ref/Wizards & Warriors [Densetsu no Kishi - Elrond] (1987-12)(Rare)(Acclaim).nsf")
    data = path.read_bytes()
    load = data[8] | (data[9] << 8)
    init = data[10] | (data[11] << 8)
    play = data[12] | (data[13] << 8)
    rom = data[128:]

    cpu = MPU()
    for i in range(0x10000):
        cpu.memory[i] = 0
    for i, byte in enumerate(rom):
        addr = load + i
        if addr < 0x10000:
            cpu.memory[addr] = byte
    cpu.memory[0x4700] = 0x60

    def call(addr: int, a: int = 0, max_cyc: int = 100000) -> None:
        cpu.sp = 0xFD
        cpu.stPushWord(0x46FE)
        cpu.a = a
        cpu.x = 0
        cpu.y = 0
        cpu.pc = addr
        cpu.p = 0x04
        cyc = 0
        while cyc < max_cyc and cpu.pc not in (0x46FF, 0x4700):
            cpu.step()
            cyc += 1

    call(init, a=song_number - 1)

    frames: list[NoiseRegisterFrame] = []
    for frame in range(1, num_frames + 1):
        call(play)
        noise_period = cpu.memory[0x400E]
        frames.append(
            NoiseRegisterFrame(
                frame=frame,
                volume=cpu.memory[0x400C] & 0x0F,
                period_index=noise_period & 0x0F,
                mode_bit=(noise_period >> 7) & 0x01,
                length_counter_load=cpu.memory[0x400F],
            )
        )
    return frames


def simulate_song_channel(song_number: int, channel: str, num_frames: int) -> tuple[list[int], list[int]]:
    """Generic structural simulator for pulse/triangle channels.

    This reuses the title-discovered semantics and should be treated as
    provisional for non-title songs until compared against capture/emulation.
    """
    parser = WizardsAndWarriorsParser(
        Path("C:/Dev/NSFRIPPER/state/ww_ref/Wizards & Warriors [Densetsu no Kishi - Elrond] (1987-12)(Rare)(Acclaim).nsf")
    )
    song = parser.extract_all_song_pointers()[song_number - 1]
    tempo_scale = get_song_tempo_scale(parser, song_number)
    parsed = parser.parse_channel(
        song.channel_pointers[CHANNEL_TO_POINTER_KEY[channel]],
        channel,
        max_events=4096,
        visit_limit=128,
    )

    current_period = 0
    current_level = 0
    counter = 0
    release_remaining = 0
    release_used = False
    event_index = 0

    periods: list[int] = []
    levels: list[int] = []

    while len(periods) < num_frames:
        if counter <= 0:
            if channel == "triangle" and release_remaining > 0:
                current_level = 15
                periods.append(current_period)
                levels.append(current_level)
                release_remaining -= 1
                if release_remaining == 0:
                    current_level = 0
                continue

            while event_index < len(parsed.events):
                evt = parsed.events[event_index]
                event_index += 1

                if isinstance(evt, ChannelInitEvent):
                    if channel == "triangle":
                        # Non-title songs can begin with the triangle gate/linear
                        # already primed by the 3-byte init header.
                        current_level = evt.reg_4000_or_4004 & 0x7F
                    else:
                        current_level = evt.reg_4000_or_4004 & 0x0F
                    continue

                if isinstance(evt, CommandEvent):
                    if evt.command == 0x04 and len(evt.params) == 3:
                        if channel == "triangle":
                            current_level = evt.params[0] & 0x7F
                        else:
                            current_level = evt.params[0] & 0x0F
                    continue

                if isinstance(evt, StopEvent):
                    if channel != "triangle":
                        current_level = 0
                    counter = 0
                    event_index = len(parsed.events)
                    break

                if isinstance(evt, TableNoteEvent):
                    if evt.raw_byte != 0x80:
                        current_period = evt.period
                    counter = (evt.duration or 0) * tempo_scale
                    break

                if isinstance(evt, DirectNoteEvent):
                    current_period = evt.period
                    current_level = evt.volume_nibble if channel != "triangle" else current_level
                    counter = (evt.duration or 0) * tempo_scale
                    break

            if (
                channel == "triangle"
                and song_number == 1
                and counter <= 0
                and current_period > 0
                and event_index >= len(parsed.events)
                and not release_used
            ):
                release_remaining = 5
                release_used = True
                continue

            if counter <= 0 and event_index >= len(parsed.events) and current_period == 0:
                periods.append(0)
                levels.append(0)
                continue

        periods.append(current_period)
        levels.append(current_level)
        if counter > 0:
            counter -= 1

    return periods, levels


def compare_song_to_nsf(song_number: int, channel: str, num_frames: int) -> TraceCompareResult:
    sim_periods, sim_levels = simulate_song_channel(song_number, channel, num_frames)
    nsf_periods, nsf_levels = capture_nsf_song_channel(song_number, channel, num_frames)

    exact_matches = 0
    exact_mismatches = 0
    sounding_agreement = 0
    sounding_disagreement = 0
    first_period_mismatch = None

    for i in range(num_frames):
        sim_p = sim_periods[i]
        sim_l = sim_levels[i]
        nsf_p = nsf_periods[i]
        nsf_l = nsf_levels[i]

        if sim_p == nsf_p:
            exact_matches += 1
        else:
            exact_mismatches += 1
            if first_period_mismatch is None:
                first_period_mismatch = i + 1

        sim_sounding = sim_p > 0 and sim_l > 0
        nsf_sounding = nsf_p > 0 and nsf_l > 0
        if sim_sounding == nsf_sounding:
            sounding_agreement += 1
        else:
            sounding_disagreement += 1

    return TraceCompareResult(
        channel=channel,
        frames_compared=num_frames,
        exact_scaled_period_matches=exact_matches,
        exact_scaled_period_mismatches=exact_mismatches,
        sounding_agreement=sounding_agreement,
        sounding_disagreement=sounding_disagreement,
        first_period_mismatch=first_period_mismatch,
    )


def simulate_noise_song(song_number: int, num_frames: int) -> list[NoiseRegisterFrame]:
    """Provisional noise simulator for the currently decoded active songs."""
    parser = WizardsAndWarriorsParser(
        Path("C:/Dev/NSFRIPPER/state/ww_ref/Wizards & Warriors [Densetsu no Kishi - Elrond] (1987-12)(Rare)(Acclaim).nsf")
    )
    if song_number not in NOISE_TRIGGER_MAPS:
        raise ValueError(f"No decoded noise mapping for song {song_number}")

    tempo_scale = get_song_tempo_scale(parser, song_number)
    song = parser.extract_all_song_pointers()[song_number - 1]
    parsed = parser.parse_channel(
        song.channel_pointers["noise"],
        "noise",
        max_events=2048,
        visit_limit=128,
    )

    trigger_map = NOISE_TRIGGER_MAPS[song_number]
    current_volume = 0
    current_period_index = 0
    current_mode_bit = 0
    current_length_load = 0
    pending_volume = 0
    counter = 0
    event_index = 0
    frames: list[NoiseRegisterFrame] = []

    while len(frames) < num_frames:
        if counter <= 0:
            while event_index < len(parsed.events):
                evt = parsed.events[event_index]
                event_index += 1

                if isinstance(evt, ChannelInitEvent):
                    pending_volume = evt.reg_4000_or_4004 & 0x0F
                    continue

                if isinstance(evt, CommandEvent):
                    if evt.command == 0x04 and len(evt.params) == 3:
                        pending_volume = evt.params[0] & 0x0F
                    continue

                if isinstance(evt, StopEvent):
                    current_volume = 0
                    counter = 0
                    event_index = len(parsed.events)
                    break

                if isinstance(evt, TableNoteEvent):
                    mapping = trigger_map.get(evt.raw_byte)
                    if mapping != "hold":
                        current_volume = pending_volume
                    if isinstance(mapping, tuple):
                        current_period_index, current_mode_bit, current_length_load = mapping
                    counter = (evt.duration or 0) * tempo_scale
                    break

            if counter <= 0 and event_index >= len(parsed.events):
                frames.append(
                    NoiseRegisterFrame(
                        frame=len(frames) + 1,
                        volume=current_volume,
                        period_index=current_period_index,
                        mode_bit=current_mode_bit,
                        length_counter_load=current_length_load,
                    )
                )
                continue

        frames.append(
            NoiseRegisterFrame(
                frame=len(frames) + 1,
                volume=current_volume,
                period_index=current_period_index,
                mode_bit=current_mode_bit,
                length_counter_load=current_length_load,
            )
        )
        if counter > 0:
            counter -= 1

    return frames


def compare_noise_song_to_nsf(song_number: int, num_frames: int) -> tuple[int, int, int | None]:
    """Return (exact_matches, mismatches, first_mismatch_frame)."""
    sim = simulate_noise_song(song_number, num_frames)
    live = capture_nsf_noise_registers(song_number, num_frames)

    exact_matches = 0
    mismatches = 0
    first_mismatch = None
    for idx, (sim_frame, live_frame) in enumerate(zip(sim, live), start=1):
        sim_state = (
            sim_frame.volume,
            sim_frame.period_index,
            sim_frame.mode_bit,
            sim_frame.length_counter_load,
        )
        live_state = (
            live_frame.volume,
            live_frame.period_index,
            live_frame.mode_bit,
            live_frame.length_counter_load,
        )
        if sim_state == live_state:
            exact_matches += 1
        else:
            mismatches += 1
            if first_mismatch is None:
                first_mismatch = idx
    return exact_matches, mismatches, first_mismatch


def compare_title_triangle() -> TraceCompareResult:
    sim = simulate_title_triangle()
    trace_periods, trace_linear = load_title_triangle_trace()

    frames_compared = min(len(sim.frames), len(trace_periods))
    exact_matches = 0
    exact_mismatches = 0
    sounding_agreement = 0
    sounding_disagreement = 0
    first_period_mismatch = None

    for i in range(frames_compared):
        sim_frame = sim.frames[i]
        trace_period = trace_periods[i]
        trace_lin = trace_linear[i]

        sim_sounding = sim_frame.period > 0 and sim_frame.linear_value > 0
        trace_sounding = trace_period > 0 and trace_lin > 0

        if sim_sounding == trace_sounding:
            sounding_agreement += 1
        else:
            sounding_disagreement += 1

        if sim_frame.period == trace_period:
            exact_matches += 1
        else:
            exact_mismatches += 1
            if first_period_mismatch is None:
                first_period_mismatch = i + 1

    return TraceCompareResult(
        channel="triangle",
        frames_compared=frames_compared,
        exact_scaled_period_matches=exact_matches,
        exact_scaled_period_mismatches=exact_mismatches,
        sounding_agreement=sounding_agreement,
        sounding_disagreement=sounding_disagreement,
        first_period_mismatch=first_period_mismatch,
    )


def compare_title_pulse(channel: str) -> TraceCompareResult:
    sim = simulate_title_pulse_channel(channel)
    trace_periods, trace_volumes = load_title_trace_channel(channel)

    frames_compared = min(len(sim.frames), len(trace_periods))
    exact_matches = 0
    exact_mismatches = 0
    sounding_agreement = 0
    sounding_disagreement = 0
    first_period_mismatch = None

    for i in range(frames_compared):
        sim_frame = sim.frames[i]
        trace_period = trace_periods[i]
        trace_volume = trace_volumes[i]

        sim_sounding = sim_frame.period > 0 and sim_frame.volume > 0
        trace_sounding = trace_period > 0 and trace_volume > 0

        if sim_sounding == trace_sounding:
            sounding_agreement += 1
        else:
            sounding_disagreement += 1

        if sim_frame.scaled_trace_period == trace_period:
            exact_matches += 1
        else:
            exact_mismatches += 1
            if first_period_mismatch is None:
                first_period_mismatch = i + 1

    return TraceCompareResult(
        channel=channel,
        frames_compared=frames_compared,
        exact_scaled_period_matches=exact_matches,
        exact_scaled_period_mismatches=exact_mismatches,
        sounding_agreement=sounding_agreement,
        sounding_disagreement=sounding_disagreement,
        first_period_mismatch=first_period_mismatch,
    )
