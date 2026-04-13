# Wizards & Warriors Title Triangle Mismatch Report

## Scope

This report reopens the `Wizards & Warriors` title triangle interpretation.
It treats the current triangle model as suspect and ranks the failure modes
against four evidence sources:

- ROM parser events
- simulator frame-state
- direct NSF emulator register state
- reference title MP3 macro shape

## Concise Mismatch Report

The current triangle misinterpretation is **not** primarily the ROM parser's
duration decoding for the opening phrase. The opening phrase already parses as:

- one longer note at frame `929`, duration `32`
- then a fresh same-pitch note at frame `961`, duration `16`
- then shorter descending notes at `977`, `993`, and `1009`

The main musical failure was downstream:

- the exporter merged the `929` and `961` triangle events into one sustained
  MIDI note because it only emitted a new note when pitch changed
- that flattened a real same-pitch re-attack into continuation
- the fixed `90s` title export then hid the macro-duration mismatch

So the previous title triangle claim was overfit. It matched a narrow
period/gate slice, but it missed an audible phrase boundary.

## Evidence

### A. Triangle Event-Boundary Audit

Title triangle structural sequence, starting at the first audible phrase:

- frame `513`: `CMD 04 [129,135,18]`, `CMD 07 [32]`, note `0x8F`, duration `32`
- ...
- frame `897`: note `0x96`, duration `32`
- frame `929`: note `0xA2`, duration `32`
- frame `961`: `CMD 07 [16]`, note `0xA2`, duration `16`
- frame `977`: note `0xA0`, duration `16`
- frame `993`: note `0x9E`, duration `16`
- frame `1009`: note `0x9D`, duration `16`

Interpretation:

- `0x07` really is changing persistent duration for the triangle stream
- the `929 -> 961` pair is **not** a hold/tie in the ROM stream
- the first short note after the longer one should be treated as a fresh event

### B. Frame-State Audit

Direct NSF state confirms distinct triangle period writes on the phrase
boundaries:

- frame `929`: `$400A/$400B -> 0xFD/0x10` (`period 253`)
- frame `977`: `$400A/$400B -> 0x1C/0x11` (`period 284`)
- frame `993`: `$400A/$400B -> 0x3F/0x11` (`period 319`)
- frame `1009`: `$400A/$400B -> 0x52/0x11` (`period 338`)

Important nuance:

- `$4008` stays latched at `0x81` through this phrase
- so the audible articulation is not explained by a changing triangle envelope
- it is more consistent with event/reload boundaries than with volume shaping

The same-pitch `929 -> 961` split does not show up as a changed *period value*
in the per-frame capture because the new note reuses the same period.
That is exactly why pitch-only MIDI note segmentation was wrong.

### C. Macro Musical Shape Validation

Reference duration check:

- title MP3: `37.1171s`
- corrected title WAV test render: `37.1167s`

That closes the old macro-duration error from the previous `90s` export.

Phrase-shape check:

- the old exported triangle turned the long note plus first short note into one
  `48`-frame sustain
- the revised export now emits:
  - `57` for `32` frames
  - `57` again for `16` frames as a fresh note-on
  - then `55`, `53`, `52` as separate short notes

This matches the reported shape much more closely:

- one longer note
- then a run of shorter notes
- with a distinct onset on the first short note

## Exact Location Of The Misinterpretation

## 1. Primary: Retrigger / Attack

The main bug was in the triangle MIDI projection:

- [nsf_to_reaper.py](/C:/Dev/NSFRIPPER/scripts/nsf_to_reaper.py#L384)
- [nsf_to_reaper.py](/C:/Dev/NSFRIPPER/scripts/nsf_to_reaper.py#L388)
- [nsf_to_reaper.py](/C:/Dev/NSFRIPPER/scripts/nsf_to_reaper.py#L395)

Old behavior:

- triangle note changes were emitted only when `midi_note != prev_midi`

Failure:

- a fresh same-pitch triangle note at frame `961` was collapsed into
  continuation of the frame `929` note

### 2. Secondary: Macro Duration

The previous title testing path used a blunt fixed render length:

- [nsf_to_reaper.py](/C:/Dev/NSFRIPPER/scripts/nsf_to_reaper.py#L687)
- command-line default in `main()` remained `90` seconds for ad hoc exports

Failure:

- the title export could run far past the cue's real length
- that masked phrase-end sanity checks and exaggerated the sustained-tail issue

### 3. Not Primary Right Now: ROM Duration Decode

Current evidence does **not** support “wrong duration decoding after the first
long note” as the top diagnosis for the opening phrase.

Relevant parser locations:

- persistent duration set by `0x07`:
  [wizards_and_warriors_parser.py](/C:/Dev/NSFRIPPER/extraction/drivers/other/wizards_and_warriors_parser.py#L340)
- table-note duration choice:
  [wizards_and_warriors_parser.py](/C:/Dev/NSFRIPPER/extraction/drivers/other/wizards_and_warriors_parser.py#L379)

Current read:

- triangle persistent duration handling is plausible for the phrase
- the current contradiction was mainly export-layer retrigger flattening

## Revised Triangle Decoding Hypothesis

Ranked hypotheses:

1. Most likely
- Triangle event boundaries are structurally correct through the opening phrase.
- Same-pitch fresh notes must retrigger even when the timer period is unchanged.
- The first short note after the long note is a real re-attack, not a tie.

2. Plausible but lower priority
- Additional triangle articulation may come from driver-side reload behavior
  not fully represented by a simple linear-counter model.
- This matters for audible punch, but it does not overturn the event split.

3. Lower priority
- The title-tail release hack may still distort the ending, but it is not the
  main cause of the opening/mid-phrase articulation error the user reported.

## Exact Code / Data Locations To Change

Implemented now:

- Added parser-driven note boundaries for `Wizards & Warriors`:
  [nsf_to_reaper.py](/C:/Dev/NSFRIPPER/scripts/nsf_to_reaper.py#L247)
- Applied boundary-aware triangle retriggering:
  [nsf_to_reaper.py](/C:/Dev/NSFRIPPER/scripts/nsf_to_reaper.py#L384)
- Wired note-boundary loading into song export:
  [nsf_to_reaper.py](/C:/Dev/NSFRIPPER/scripts/nsf_to_reaper.py#L636)

Still provisional / should stay narrowly scoped:

- title-specific release patch in `simulate_title_triangle()`:
  [wizards_and_warriors_simulator.py](/C:/Dev/NSFRIPPER/extraction/drivers/other/wizards_and_warriors_simulator.py#L300)
- title-only branch in generic simulator:
  [wizards_and_warriors_simulator.py](/C:/Dev/NSFRIPPER/extraction/drivers/other/wizards_and_warriors_simulator.py#L556)

## Status Of The Old Sustained-Tail Model

Decision: **narrowed, not promoted**

- It is retained only as a provisional title-scoped end-of-stream release model.
- It is explicitly **not** accepted as general engine truth.
- It must not be allowed to mask true note boundaries.

This report rejects the older broader implication that triangle semantics were
“solved” for the title in a musically trustworthy sense.

## Cue Duration Note

Yes, the cue duration now matches the reference much more closely:

- old ad hoc render path: `90.0s`
- revised title test render: `37.1167s`
- reference MP3: `37.1171s`

So the macro-duration mismatch is effectively removed for the title test cue.
