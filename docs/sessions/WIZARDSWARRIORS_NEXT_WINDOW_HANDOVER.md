# Wizards & Warriors Next Window Handover

## Current state

The `Wizards & Warriors` title issue is currently best understood as a **composite articulation problem**, not a missing-note problem.

Most important conclusion:

- the disputed phrase around frames `928 / 960 / 976` is best modeled as `pulse1 + triangle`
- `pulse1` carries the pluck/attack
- `triangle` carries low support/body
- frame `960` should behave like **fresh attack + damped low body**, not like a full renewed triangle bass note

## Code already changed

File changed:

- [ReapNES_APU2.jsfx](/C:/Dev/NSFRIPPER/studio/jsfx/ReapNES_APU2.jsfx)

What was changed:

- triangle body is no longer treated as a nearly static scalar
- `fresh_attack_damped_body` now drives a lower `tri_body_target`
- composite hidden attacks clamp triangle body down faster
- triangle linear reload influences body more gently than before
- recent retune backed off an over-aggressive first pass so full-body reattacks recover more than the damped hit at `960`

Current direction from code-level checks:

- `960`-style damped event is substantially reduced vs the old model
- `928/976`-style full-body renewals still retain meaningfully more triangle body than `960`

## Export / evidence side

Key file:

- [nsf_to_reaper.py](/C:/Dev/NSFRIPPER/scripts/nsf_to_reaper.py)

Important current behavior:

- parser-boundary same-pitch retriggers are already present for `pulse1` and `triangle`
- SysEx `0x03` audible-state sideband carries:
  - flags
  - level
  - `release_class`
- composite hidden attack can be marked for `pulse1` + `triangle`

Important implication:

- do **not** reopen the "maybe the note is missing from MIDI" theory

## REAPER reality check

Read:

- [REAPERFUCKERY.md](/C:/Dev/NSFRIPPER/REAPERFUCKERY.md)

Key discoveries:

- REAPER loads the installed JSFX copy at:
  - `C:\Users\PC\AppData\Roaming\REAPER\Effects\ReapNES Studio\ReapNES_APU2.jsfx`
- that installed copy was synced from the repo copy already
- headless `-renderproject` attempts did **not** produce a WAV before timeout
- so there is still no trustworthy non-interactive REAPER render path from this shell

Important implication:

- the next useful verification step is probably **interactive REAPER audition**, not more blind headless render attempts

## Read first next time

- [WIZARDSWARRIORS_COMPOSITE_BASS_HANDOVER_2026-04-03.md](/C:/Dev/NSFRIPPER/WIZARDSWARRIORS_COMPOSITE_BASS_HANDOVER_2026-04-03.md)
- [REAPERFUCKERY.md](/C:/Dev/NSFRIPPER/REAPERFUCKERY.md)
- [wizards_and_warriors_title_composite_bass_audit.md](/C:/Dev/NSFRIPPER/extraction/analysis/reconciled/wizards_and_warriors_title_composite_bass_audit.md)
- [wizards_and_warriors_title_release_ir_report.md](/C:/Dev/NSFRIPPER/extraction/analysis/reconciled/wizards_and_warriors_title_release_ir_report.md)
- [ReapNES_APU2.jsfx](/C:/Dev/NSFRIPPER/studio/jsfx/ReapNES_APU2.jsfx)

## Best next step

Open this project in REAPER and judge the phrase directly:

- [Wizards_&_Warriors_01_Wizards_&_Warriors_Title_APU2_releaseaware_v5.rpp](/C:/Dev/NSFRIPPER/Projects/Wizards_and_Warriors/Wizards_&_Warriors_01_Wizards_&_Warriors_Title_APU2_releaseaware_v5.rpp)

Then focus on one question:

- does frame `960` now read as a plucked attack over damped low support, or is triangle still too present?

## If it is still wrong

Adjust in this order:

1. reduce triangle authority a bit more on `fresh_attack_damped_body`
2. only after that, consider strengthening `pulse1` attack dominance
3. do **not** restart from hidden-opcode hunting unless brand-new evidence forces it

## One-line carry-forward

The next window should start from: **the title phrase is a composite pulse1+triangle articulation, the JSFX has already been retuned in that direction, and the main missing step is interactive REAPER verification of the new body/attack balance.**
