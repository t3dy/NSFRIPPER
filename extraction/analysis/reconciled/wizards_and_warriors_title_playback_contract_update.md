# Wizards & Warriors Title Playback Contract Update

## What changed

The playback path now has a distinct audible-state sideband in addition to raw
register replay.

SysEx message types:

- `0x02`: register replay + write mask
- `0x03`: audible-state sideband

`0x03` payload:

- `ch`
- `flags`
- `level`
- `release_class`

Flag bits:

- `bit0`: parser boundary
- `bit1`: hidden same-pitch retrigger
- `bit2`: visible period attack
- `bit3`: composite pulse1+triangle hidden attack
- `bit4`: sounding

Release classes:

- `0`: effectively muted
- `1`: sustain body
- `2`: ringing decay
- `3`: fresh attack, damped body
- `4`: fresh full body

## Why this matters

The title phrase contains attacks that are musically real but do not appear as
new latched periods.

Concrete evidence:

- frame `929` carries parser-boundary + visible-attack state
- frame `961` carries composite hidden-attack state on both `pulse1` and
  `triangle`

This is the missing middle layer between:

- raw hardware control writes
- note/latch projection
- synth playback behavior

## Verified transport result

In in-memory title MIDI generation:

- frame `929` pulse1 sideband = `19`
  - parser boundary + visible period attack + sounding
- frame `961` pulse1 sideband = `27`
  - parser boundary + hidden retrigger + composite attack + sounding
- frame `961` triangle sideband = `27`
  - parser boundary + hidden retrigger + composite attack + sounding

So the playback transport can now distinguish:

- ordinary note attacks
- hidden same-pitch retriggers
- cross-channel composite attacks
- attack-heavy damped retriggers versus full-bodied onsets

## Synth behavior change

`ReapNES_APU2.jsfx` now consumes `0x03` and uses it for lightweight articulation:

- pulse channels get a short attack emphasis
- triangle gets a short pluck/damping envelope
- composite attack frames trigger a stronger onset than ordinary attacks

This is intentionally small.
The sideband is not a replacement for register truth; it is a playback hint for
musically important behavior that raw latch state does not classify well enough
on its own.

## Architectural conclusion

Plain MIDI is too lossy.

Write-aware register replay is necessary but still incomplete.

The minimum useful middle layer for this title is:

- per-channel attack classification
- hidden retrigger markers
- composite attack markers
- effective level / sounding state
- release/body class

That is now encoded as a first playback-facing contract rather than only an
analysis document.
