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
