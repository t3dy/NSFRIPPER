# Wizards & Warriors Noise Partial Semantics

This note captures the noise-channel semantics that are already strong enough
to state explicitly, even though a full noise simulator is not finished yet.

## What Is Now Clear

Two different active-noise patterns exist in the soundtrack:

1. simple percussion-gate behavior
2. note-like noise-period selection

The active songs split cleanly:

- song `2`: simple gate pattern
- song `6`: simple gate pattern with instrument toggles
- song `16`: note-like noise-period mapping

Using the provisional noise simulator now in
`C:\Dev\NSFRIPPER\extraction\drivers\other\wizards_and_warriors_simulator.py`,
all three active-noise songs match direct NSF noise-register state exactly for
the first `512` frames:

- song `2`: `512 / 512`
- song `6`: `512 / 512`
- song `16`: `512 / 512`

## Song 2: Forest of Elrond

Noise pointer:

- `0xF293`

Observed raw bytes:

- `0xC1`
- `0x80`
- command `0x04`

Observed register states:

- active state: `(volume=2, period=0, mode=0, length=8)`
- muted state: `(volume=0, period=0, mode=0, length=8)`

Practical interpretation:

- `0xC1` acts like the repeating trigger symbol for this percussion voice
- `0x80` does not create a new audible state by itself
- command `0x04` toggles the instrument between:
  - `0x42`-like active volume
  - `0x40`-like muted volume
- the new instrument state becomes audible on a later trigger rather than
  necessarily on the same frame as the command

What is stable enough to say:

- song `2` noise is structurally understood
- its audible state alternates between a single active noise voice and silence
- the current provisional simulator reproduces its NSF noise state exactly for
  the first `512` frames

## Song 6: Initial Registration

Noise pointer:

- `0xF641`

Observed raw bytes:

- `0xC3`
- `0x80`
- command `0x04`

Observed register states:

- `(volume=1, period=2, mode=0, length=16)`
- `(volume=3, period=2, mode=0, length=16)`

Practical interpretation:

- this is another compact repeating percussion pattern
- the underlying noise period and mode stay stable in the sampled window
- command `0x04` is again tied to instrument-volume changes
- `0xC3` is the repeating trigger symbol for this voice family

What is stable enough to say:

- song `6` noise is not a pitch-changing line
- it is a fixed-period percussion layer with two instrument intensities
- the current provisional simulator reproduces its NSF noise state exactly for
  the first `512` frames

## Song 16: Forest of Elrond (alt)

Noise pointer reported by init emulation:

- `0xF232`

This channel behaves differently from songs `2` and `6`.
It uses multiple raw bytes that map to distinct `$400E/$400F` states.

### Confirmed Raw Byte Mappings

The following mappings were observed directly by aligning parsed event starts
with NSF noise-register captures:

| Raw byte | Period index | Mode bit | Length load |
| --- | --- | --- | --- |
| `0x99` | `11` | `1` | `17` |
| `0x8D` | `6` | `0` | `19` |
| `0x8F` | `9` | `1` | `18` |
| `0x90` | `14` | `1` | `18` |
| `0x92` | `0` | `1` | `18` |
| `0x93` | `12` | `0` | `18` |
| `0x94` | `10` | `0` | `18` |

The ambient volume in the sampled window remains:

- `volume=2`

### About `0x80`

`0x80` appears in multiple captured states:

- `(6, 0, 19)`
- `(10, 0, 18)`
- `(14, 1, 18)`
- `(0, 1, 18)`

So for noise, `0x80` is not a universal silent rest symbol in the same sense
as melodic parsing.

Current best interpretation:

- `0x80` often behaves more like "hold current noise state" than "clear noise"
- this hold rule is sufficient for exact NSF-state reproduction over the first
  `512` frames of song `16`

## Why This Matters

These findings are enough to support better future work in two ways:

1. we now know songs `2` and `6` can likely be solved with a compact
   instrument-toggle model rather than a large lookup system
2. we now know song `16` needs a real raw-byte-to-noise-register lookup path

They are also enough to support a stronger present-tense claim:

- all genuinely active noise songs currently observed in the soundtrack have a
  working first-`512`-frame NSF-grounded simulator path

## What Is Still Missing

Still not fully solved:

- exact timing of when pending `0x04` instrument changes become active in
  songs `2` and `6` beyond the current reproduced behavior model
- a complete raw-byte noise lookup for song `16` beyond the bytes observed in
  the first `512` frames
- whether songs `2`, `6`, and `16` share one generalized noise decoder or use
  two different submodes under the hood
