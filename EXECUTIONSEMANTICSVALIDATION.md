# Execution Semantics Validation

## The Problem It Solves

A parser that produces zero byte-stream errors has correctly identified the
boundary of every command, note, and parameter in the data. That's necessary
but not sufficient. Zero parse errors means "the bytes are correctly
partitioned." It does NOT mean:

- The pitches are correct
- The durations are correct
- The envelopes are correct
- The notes sound like the game

Between "bytes correctly partitioned" and "sounds like the game" lies the
**execution semantics** — the actual behavior of the 6502 driver when it
processes those bytes frame by frame.

## What Execution Semantics Validation Is

Simulate the driver's frame-by-frame state machine and compare every frame's
output against the Mesen trace (ground truth).

The simulation must model:

### 1. Tempo Accumulator

```
Each NMI (frame):
  accumulator += tempo_speed    ; 8-bit addition, wraps at 256
  if carry:
    process_music_tick()        ; advance all channels
  else:
    process_envelopes_only()    ; per-frame pitch/volume modulation
```

Battletoads Level 1: tempo = 0x57 (87). Overflow every 3 frames exactly.
4029-frame loop / 3 = 1343 music ticks expected.

### 2. Duration Counter (Per Channel)

```
Each music tick:
  duration_counter--
  if duration_counter == 0:
    read_next_event()           ; advance the song data pointer
```

Duration counter is loaded from either:
- The inline byte after a note (when $0351,X = 0)
- The persistent duration value (when $0351,X != 0)

### 3. Period Register (What the APU Plays)

The NOTE HANDLER sets the period from the period table. But the period is
modified every frame by:
- Arpeggio system (CMD 0x0D/0x0E): cycles note index offset per frame
- Vibrato system (CMD 0x16): oscillates period value per frame
- Sweep unit ($4001): hardware pitch bend

The TRACE captures the FINAL period after all modifications. The PARSER
gives us the BASE note. The gap between them is the arpeggio/vibrato system.

### 4. Volume Register (Envelope)

The envelope system (CMD 0x03) shapes volume per frame:
- Attack: initial volume
- Decay: per-frame volume decrease
- Sustain: held volume level
- Release: volume after note-off

Plus per-note envelope override (CMD 0x22 / $03A2 flag) which provides
a specific volume byte per note.

### 5. Duty Cycle

Set by instrument commands (CMD 0x08/0x17) and held until changed.

## How to Validate

### Step 1: Build Per-Frame State From Parser Events

```
For each frame (1 to loop_end):
  advance_tempo_accumulator()
  if music_tick:
    for each channel:
      if duration_counter > 0:
        duration_counter -= 1
      else:
        consume_next_event()
        set base_period from note
        set duration_counter from duration
  for each channel:
    apply_arpeggio(base_period) -> actual_period
    apply_envelope() -> actual_volume
    record: frame, actual_period, actual_volume
```

### Step 2: Compare Against Mesen Trace

```
For each frame:
  sim_period = simulated_period[channel][frame]
  trace_period = trace_period[channel][frame]

  if sim_period != trace_period:
    record mismatch(frame, channel, sim_period, trace_period)
```

### Step 3: Diagnose Mismatches

Mismatches fall into categories:

| Category | Symptom | Cause |
|----------|---------|-------|
| Tempo drift | Frame N: first mismatch at note boundary | Tempo calculation wrong |
| Duration error | Sim advances to next note too early/late | Duration value or tick rate wrong |
| Arpeggio error | Base note correct, per-frame period wrong | Arpeggio params not modeled |
| Envelope error | Period matches but volume differs | Envelope table or shape wrong |
| Transpo error | All notes in a section off by constant | Transposition tracking bug |
| Alignment | Everything shifted by N frames | Start frame offset wrong |

## Why This Step Cannot Be Skipped

### The Battletoads Arpeggio Lesson

The parser extracts base notes like G6 (period ~71). The trace shows
period 2713 at the same position. The difference factor is ~38x.

This is the arpeggio system adding large index offsets per frame,
transposing the base note down several octaves. Without simulating
the arpeggio, the parser's "G6" note is meaningless — it never
actually plays as G6.

### The Duration Discrepancy

Parser total: 2048 duration ticks. Expected from loop length: ~1343 ticks
(at 3 frames/tick). Ratio: 1.52x. Something in the duration accounting
is wrong. Either:
- Some duration values are wrong
- The tempo changes mid-song (CMD 0x10/0x11)
- The subroutine loop mechanism consumes ticks differently than I modeled
- The rest/note boundary between subroutine iterations adds hidden ticks

A frame-by-frame simulation would expose EXACTLY which duration is wrong
by showing where the sim diverges from the trace.

### The Three-Layer Separation

This project's architecture requires three distinct layers:

1. **Observed data** (Frame IR from trace) — what the APU actually did
2. **Interpreted musical events** (from parser) — what the ROM intends
3. **Projected playback** (MIDI/RPP) — what we generate

Execution semantics validation sits between layers 1 and 2. It answers:
"Given the ROM's intended events, does simulated execution produce the
same APU state as the trace?"

If yes: the parser correctly captures intent AND the driver model is correct.
If no: either the parser is wrong (bytes misinterpreted) or the driver
model is incomplete (missing arpeggio, wrong tempo, etc.).

## Application to Our Project

### What We Have

- Rare driver parser: 39 commands decoded, all 4 channels parse zero errors
- Mesen trace: 20,885 frames of clean P2 APU state
- Tempo value: 0x57 (87), giving ~3 frames per music tick
- Duration discrepancy: 2048 sim ticks vs ~1343 expected ticks

### What We Need to Build

1. **Tempo accumulator simulator** — exact 8-bit overflow logic
2. **Duration counter per channel** — decrement per tick, advance on zero
3. **Arpeggio modeler** — decode CMD 0x0D/0x0E/0x16 parameters, compute
   per-frame period offset from base note
4. **Envelope modeler** — decode CMD 0x03 parameters, compute per-frame
   volume from envelope shape
5. **Per-frame comparator** — align sim frames with trace frames, report
   first mismatch per parameter (period, volume, duty)

### Acceptance Criteria

```
For P2 channel, first 4029 frames (one loop):
  - Period matches trace on 90%+ of sounding frames
  - Volume matches trace on 80%+ of frames
  - Note boundaries (duration counter hitting zero) align with trace
    note attacks within +/- 1 frame
```

Until these criteria pass, no musical claims about pitch, rhythm, or timbre
are valid. The parser output is a hypothesis. The simulation validates it.

## What This Is NOT

- Not MIDI generation (that comes after)
- Not ear-checking (that's the final gate)
- Not Frame IR in the existing pipeline sense (that's for trace data)

This is: running the ROM's data through a model of the driver and checking
whether the model's output matches what the real 6502 produces. It's a
test of our understanding of the driver, not a musical product.
