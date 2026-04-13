# Wizards & Warriors NSF Semantics Sweep

This report compares the current `Wizards & Warriors` structural simulator
against direct NSF emulation for the first `512` play frames of every song.

Scope:

- channels compared: `pulse1`, `pulse2`, `triangle`
- reference: direct NSF `init` + per-frame `play` emulation
- simulator: `extraction/drivers/other/wizards_and_warriors_simulator.py`
- note: this is an internal semantics checkpoint, not a substitute for
  external Mesen capture validation

## Summary

- exact channel matches: `48 / 48`
- songs with all three melodic channels exact for 512 frames: `16 / 16`
- strong result: the title-derived model generalizes across most of the game
- current melodic-channel model now reproduces every song's first `512` NSF
  frames exactly

## Song Results

Legend:

- `period` = exact period match count out of `512`
- `sound` = sounding-state agreement count out of `512`

| Song | Title | Pulse 1 | Pulse 2 | Triangle | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | Wizards & Warriors Title | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | Fully exact |
| 2 | Forest of Elrond | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | Fully exact |
| 3 | Tree | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | Fully exact |
| 4 | Ice Cave | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | `0x09` duration scaling now modeled |
| 5 | Low on Energy | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | Wider loop traversal fixes late alignment |
| 6 | Initial Registration | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | `0x09` song-level scaling + hold behavior reconcile all channels |
| 7 | Got an Item | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | Explicit pulse `StopEvent` mute behavior added |
| 8 | Outside Castle Ironspire | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | Fully exact |
| 9 | Castle Ironspire | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | Fully exact |
| 10 | Entering a Door | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | Explicit pulse `StopEvent` mute behavior added |
| 11 | Map | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | Title-only triangle release no longer leaks into generic playback |
| 12 | Potion | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | Wider loop traversal fixes late alignment |
| 13 | Fire Cavern | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | Simulator parse now permits deeper loop visitation |
| 14 | Inside the Big Tree | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | Same fix as song `13` |
| 15 | Boss | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | Fully exact |
| 16 | Forest of Elrond (alt) | `512/512`, `512/512` | `512/512`, `512/512` | `512/512`, `512/512` | Fully exact |

## Interpretation

The current simulator is now strong enough to make three concrete claims:

1. The parser's basic stream alignment is holding up across the soundtrack.
2. The melodic execution model now reproduces all 16 songs against direct NSF
   emulation for the first `512` frames.
3. The key remaining uncertainty has shifted away from melodic-channel timing
   and pitch, and toward external capture validation plus noise-specific logic.

## Semantics Discoveries That Closed the Sweep

The final step from partial coverage to `48 / 48` exact agreement came from a
small set of driver truths:

- `0x09` acts as a song-level duration scale.
  Ice Cave uses `3x`; Initial Registration uses `2x`.
- The generic simulator needed explicit pulse `StopEvent` muting.
  Hardware keeps the last period register but the pulse volume drops to zero.
- The title triangle's one-shot release tail is not a generic rule.
  It must stay title-scoped.
- Structural parsing needed a wider loop-visit allowance for simulator work.
  The old visit cap was appropriate for static summaries but too small for
  frame simulation of repeating channels.

## Promotion Status

What this sweep supports:

- the current simulator is no longer title-only in practice
- melodic channels `pulse1`, `pulse2`, and `triangle` now have exact internal
  NSF-emulation agreement for all 16 songs over the first `512` frames

What this sweep does not support:

- claiming whole-game external semantics validation
- trusting pulse/noise envelope behavior everywhere
- skipping per-track capture validation when preparing final REAPER output
