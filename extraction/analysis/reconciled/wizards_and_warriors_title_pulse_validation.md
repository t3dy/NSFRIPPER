# Wizards & Warriors Title Pulse Validation

This report records the current execution-semantics validation state for the
`Wizards & Warriors` title track pulse channels.

It covers only the clean second-pass title reference span:

- trace file: `extraction/traces/wizards_and_warriors/title_capture.csv`
- frame window: `2721-4889`
- compared frames: `2169`

## Scope

Validated:

- pulse 1
- pulse 2
- triangle period path
- noise inactive path

Partially unresolved:

- triangle linear-counter fadeout / gate behavior

## Driver / Parser Basis

Validation used:

- `extraction/drivers/other/wizards_and_warriors_parser.py`
- `extraction/drivers/other/wizards_and_warriors_simulator.py`

Important semantics currently modeled:

- per-channel 3-byte stream header
- loop handling for command pair `0x05` / `0x06`
- duration mode from `$07E0,X`
- title pulse timing and period projection
- `0x80` interpreted as hold/tie when a note is already sounding

## Results

### Pulse 1

- exact scaled period matches: `2169 / 2169`
- exact scaled period mismatches: `0`
- sounding agreement: `2168 / 2169`
- sounding disagreement: `1 / 2169`
- disagreement frame: `2169`

Frame 2169 details:

- simulated period: `678` -> scaled trace period `1357`
- simulated volume: `5`
- trace period: `1357`
- trace volume: `0`

Interpretation:

- pitch/period remains aligned on the final frame
- disagreement is only the terminal volume drop at capture end

### Pulse 2

- exact scaled period matches: `2169 / 2169`
- exact scaled period mismatches: `0`
- sounding agreement: `2168 / 2169`
- sounding disagreement: `1 / 2169`
- disagreement frame: `2169`

Frame 2169 details:

- simulated period: `189` -> scaled trace period `379`
- simulated volume: `3`
- trace period: `379`
- trace volume: `0`

Interpretation:

- pitch/period remains aligned on the final frame
- disagreement is only the terminal volume drop at capture end

## What This Means

The title pulse channels are now strongly semantics-aligned for this capture
window.

Triangle summary:

- exact period match across the whole title reference span
- sounding agreement across the whole title reference span
- final release is now modeled correctly at the gate/on-off level
- exact intermediate linear-counter values during the last few release frames
  are still approximate

Noise summary:

- no active noise events were observed in this clean title capture
- inactive path matches for the full window

This does NOT yet mean:

- the full title track is trusted across all channels
- the whole driver is decoded
- the whole game is validated

It DOES mean:

- parser + simulator are now good enough to reproduce pulse timing and periods
  for the title track
- remaining title work should focus on triangle and noise, not re-litigating
  pulse pitch/timing

## Remaining Work

1. Model triangle linear-counter fadeout / release
2. Produce a cross-channel title validation report with period vs gate layers separated
3. Reuse the same simulator-building workflow on the remaining tracks
