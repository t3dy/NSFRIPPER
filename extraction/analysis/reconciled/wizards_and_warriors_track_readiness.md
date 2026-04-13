# Wizards & Warriors Track Readiness

This file answers the practical question: how much of the `Wizards & Warriors`
soundtrack can we treat as "gotten" right now?

Short answer:

- all 16 tracks already exist as `.mid` and `.rpp` outputs in
  `C:\Dev\NSFRIPPER\Projects\Wizards_and_Warriors`
- melodic channels are internally locked across the whole game
- the formerly active noise blockers on songs `2`, `6`, and `16` now have
  working first-`512`-frame NSF-grounded simulator coverage

## Existing Whole-Game Outputs

Current project folder:

- `C:\Dev\NSFRIPPER\Projects\Wizards_and_Warriors`

Contents already present:

- `16` MIDI files under
  `C:\Dev\NSFRIPPER\Projects\Wizards_and_Warriors\midi`
- `16` REAPER projects under
  `C:\Dev\NSFRIPPER\Projects\Wizards_and_Warriors`

So in a concrete file-output sense, yes: the whole soundtrack is already
materialized.

## Validation Meaning

For this readiness sheet:

- `melodic locked` means `pulse1`, `pulse2`, and `triangle` match direct NSF
  emulation exactly for the first `512` frames
- `noise silent` means the sampled window has no audible noise activity
- `noise muted` means registers move but the noise volume nibble stays `0`
- `noise active-locked` means active noise matches direct NSF register state
  exactly for the first `512` frames with the current provisional simulator

## Track Matrix

| Song | Title | Files Present | Melodic Status | Noise Status | Practical Readiness |
| --- | --- | --- | --- | --- | --- |
| 1 | Wizards & Warriors Title | Yes | Locked | Silent | Strong |
| 2 | Forest of Elrond | Yes | Locked | Active-locked | Strong |
| 3 | Tree | Yes | Locked | Silent | Strong |
| 4 | Ice Cave | Yes | Locked | Silent | Strong |
| 5 | Low on Energy | Yes | Locked | Muted | Strong for audible result |
| 6 | Initial Registration | Yes | Locked | Active-locked | Strong |
| 7 | Got an Item | Yes | Locked | Silent | Strong |
| 8 | Outside Castle Ironspire | Yes | Locked | Muted | Strong for audible result |
| 9 | Castle Ironspire | Yes | Locked | Silent | Strong |
| 10 | Entering a Door | Yes | Locked | Silent | Strong |
| 11 | Map | Yes | Locked | Silent | Strong |
| 12 | Potion | Yes | Locked | Silent | Strong |
| 13 | Fire Cavern | Yes | Locked | Silent | Strong |
| 14 | Inside the Big Tree | Yes | Locked | Silent | Strong |
| 15 | Boss | Yes | Locked | Silent | Strong |
| 16 | Forest of Elrond (alt) | Yes | Locked | Active-locked | Strong, with broader-lookup caveat |

## Best Current Interpretation

If the goal is "get all the tracks" in the sense of:

- having every song extracted
- having every song in MIDI and REAPER form
- having melodic channels strongly validated

then the answer is yes.

If the goal is stricter:

- full four-channel execution semantics for every song
- including trustworthy noise interpretation everywhere

then the remaining blockers are:

- broader noise generalization beyond the currently observed first-`512`-frame
  active cases
- external per-song capture validation

## Recommended Use Right Now

These tracks are currently the safest to treat as effectively complete:

- `1` through `15`

Track `16` is also strong now, but should still keep one caveat attached:

- its active noise model is exact for the first `512` frames, but still relies
  on a partial observed byte map rather than a fully generalized noise-note
  decoder

## Relevant Supporting Notes

- melodic sweep:
  `C:\Dev\NSFRIPPER\extraction\analysis\reconciled\wizards_and_warriors_nsf_semantics_sweep.md`
- noise survey:
  `C:\Dev\NSFRIPPER\extraction\analysis\reconciled\wizards_and_warriors_noise_survey.md`
- project notebook:
  `C:\Dev\NSFRIPPER\CODEXWIZARDSWARRIORS.md`
