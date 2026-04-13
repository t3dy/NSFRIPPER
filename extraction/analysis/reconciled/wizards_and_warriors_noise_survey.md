# Wizards & Warriors Noise Survey

This note records the current state of the `Wizards & Warriors` noise channel
before a dedicated noise simulator is built.

Reference method:

- direct NSF emulation via `init` + per-frame `play`
- observed registers: `$400C`, `$400E`, `$400F`
- sample window: first `512` play frames of each song

Helper code:

- `capture_nsf_noise_registers()` in
  `C:\Dev\NSFRIPPER\extraction\drivers\other\wizards_and_warriors_simulator.py`

## Headline Result

The noise channel falls into three distinct buckets:

1. truly inactive sentinel reuse
2. muted but not fully static register state
3. genuinely active noise programming that still needs dedicated semantics

This is good news because it means most songs do not need full noise decoding
before project generation can proceed.

## Bucket 1: Inactive Sentinel Stream

Many songs point noise at the common stream `0xF1E0`.

Observed behavior:

- no audible noise activity
- per-frame state stays effectively silent for the sampled window
- typical state is `(volume=0, period=0, mode=0, length=0)`

Songs in this bucket:

- `1` Title
- `3` Tree
- `4` Ice Cave
- `7` Got an Item
- `9` Castle Ironspire
- `10` Entering a Door
- `11` Map
- `12` Potion
- `13` Fire Cavern
- `14` Inside the Big Tree
- `15` Boss

## Bucket 2: Muted but Register-Primed Noise

These songs do not produce audible noise in the sampled window, but the driver
still leaves the noise registers in non-zero or changing states.

### Song 5: Low on Energy

- noise pointer: `0xF578`
- captured steady state: `$400C=0x40`, `$400E=0x00`, `$400F=0x08`
- audible result is still muted because noise volume nibble remains `0`

### Song 8: Outside Castle Ironspire

- noise pointer: `0xF764`
- captured states include:
  - `$400C=0x40`, `$400E=0x00`, `$400F=0x08`
  - `$400C=0x40`, `$400E=0x02`, `$400F=0x08`
- again, volume nibble remains `0`, so this is register motion without audible
  output in the sampled window

Interpretation:

- these are not "fully inactive" in a hardware sense
- but they are still effectively silent for output purposes

## Bucket 3: Active Noise Songs

These songs produce real audible noise activity and need dedicated decoding.

### Song 2: Forest of Elrond

- noise pointer: `0xF293`
- active frames in first `512`: `204`
- observed states:
  - `(volume=2, period=0, mode=0, length=8)`
  - `(volume=0, period=0, mode=0, length=8)`

Interpretation:

- likely a simple gated-noise percussion line
- structural parse shows repeated `0xC1` events plus command `0x04`
- `0x04` appears to switch `$400C` between `0x42` and `0x40`

### Song 6: Initial Registration

- noise pointer: `0xF641`
- active frames in first `512`: `512`
- observed states:
  - `(volume=1, period=2, mode=0, length=16)`
  - `(volume=3, period=2, mode=0, length=16)`

Interpretation:

- clearly active throughout the sampled window
- structural parse is dominated by alternating `0xC3` / `0x80` with `0x04`
  register changes
- this looks like a compact repeating percussion pattern with fixed period and
  instrument toggles

### Song 16: Forest of Elrond (alt)

- noise pointer reported by init emulation: `0xF232`
- active frames in first `512`: `512`
- observed states include:
  - `(volume=2, period=11, mode=1, length=17)`
  - `(volume=2, period=6, mode=0, length=19)`
  - `(volume=2, period=9, mode=1, length=18)`
  - `(volume=2, period=14, mode=1, length=18)`

Important nuance:

- the stream at `0xF232` looks melodic under the current structural parser
- but the NSF driver clearly interprets it as valid noise control for song `16`

Current inference:

- the noise channel has its own interpretation of the byte stream
- reusing melodic `TableNoteEvent.period` semantics here is incorrect

## Structural Parsing Implication

The current parser is still useful for noise because it preserves:

- boundaries
- durations
- loop shape
- command placement

But it is not yet semantically correct for noise note values.

For noise, the key missing step is not pointer recovery or loop recovery.
It is the mapping from raw event bytes to:

- `$400C` volume/instrument state
- `$400E` period index
- `$400E` mode bit
- `$400F` length reload behavior

## Next Noise Targets

The best decode order is:

1. song `2`
   simplest active case; only volume toggles are obvious
2. song `6`
   fixed-period repeating percussion with instrument variation
3. song `16`
   richest active case and likely the best source for raw-byte-to-noise-index
   mapping

## Current Project Status Impact

What this supports:

- most songs can already be treated as "no audible noise content" or
  "effectively silent noise" for provisional project generation
- the melodic simulator milestone remains valid

What this does not support:

- claiming full four-channel semantics validation for songs `2`, `6`, and `16`
- trusting current structural noise event values as musical truth
