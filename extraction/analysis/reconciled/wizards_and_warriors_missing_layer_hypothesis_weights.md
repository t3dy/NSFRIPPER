# Wizards & Warriors Missing-Layer Hypothesis Weights

## Goal

We need a way to move forward without fake certainty.

This document defines:

1. the candidate missing-layer hypotheses
2. how to weight them
3. what evidence currently supports or weakens each one
4. what would count as a breakthrough

The target is the `Wizards & Warriors` title, especially:

- triangle phrase articulation
- pulse 2 ending timbre/softness

## Weighting Method

Each hypothesis gets a score from `-2` to `+2` on each criterion:

- `Explains triangle phrase`
- `Explains bass over-sustain`
- `Explains pulse 2 ending softness gap`
- `Directly evidenced by data`
- `Survives known contradictions`
- `Requires minimal special pleading`

Total score:

- `10 to 12`: very strong working theory
- `6 to 9`: plausible and worth active testing
- `2 to 5`: secondary theory
- `<= 1`: weak / mostly unsupported

This is not proof by arithmetic.
It is a way to keep ourselves honest about where the evidence is actually
pointing.

## Core Evidence

### E1. Same-pitch title triangle re-attack is real at the write level

Direct NSF write log:

- frame `929`: `$4008=0x81`, `$400A=0xFD`, `$400B=0x10`
- frame `961`: `$4008=0x81`, `$400A=0xFD`, `$400B=0x10`

Important fact:

- frame `961` is a fresh write sequence even though the latched period value is
  unchanged

Implication:

- note-only MIDI is too lossy
- state-only register replay is also too lossy

### E2. Trace pulse 2 ending includes stepped softening

Title trace ending:

- frame `2081`: `$4004_vol = 9`
- frame `2113`: `$4004_vol = 6`
- frame `2145`: `$4004_vol = 3`

Implication:

- the ending pulse 2 tone is not just a new note pattern
- some of the heard softening is real per-frame amplitude behavior

### E3. Output-filter-only changes did not solve the core musical complaint

We already tried output shaping / softer playback directionally.

Result:

- timbre hypothesis remains plausible
- but it does not explain bass note over-sustain by itself

### E4. Trace-derived route already behaves more like the user's description

Why:

- pulse channels carry observed CC11 volume changes
- triangle route is at least driven by observed frame-state gating decisions

Implication:

- the missing layer is probably closer to effective audible state than to raw
  register latch bytes

### E5. The disputed title attack is composite, not triangle-only

Fresh articulation audit:

- pulse 1 has same-pitch parser boundaries at frames `928` and `960`
- NSF write capture shows full same-value pulse 1 rewrites at those frames:
  `$4000/$4001/$4002/$4003`
- triangle has the already-known same-pitch re-attack at frame `960`
- the aligned MP3 reference shows the strongest bright/high-band onset energy
  of the phrase at frame `960`, while low-band body is comparatively weak there

Implication:

- the missing title information is not just "triangle note starts"
- it includes composite attack / retrigger state across channels
- filter-only explanations get weaker, because the ROM/write data already says
  a fresh bright attack should exist there

### E6. The disputed title bass is likely composite, not triangle-only

Frame-aligned phrase audit:

- pulse 1 and triangle both retrigger at `928`, `960`, and `976`
- pulse 1 is in envelope mode (`$4000 = 0x45`, constant-volume bit clear)
- triangle holds `$4008 = 0x81` through the phrase
- reference audio at `960` has a strong bright onset but reduced low-body energy

Implication:

- the heard "plucked bass" is likely a composite pulse1+triangle result
- missing pulse attack dominance plus over-steady triangle body can produce the
  exact user complaint without requiring a hidden opcode

## Hypotheses

## H1. Missing layer = frame audible-state IR

Definition:

- a middle layer between raw register/control state and playback
- stores effective loudness, gate, retrigger, phase reset, continuity, and
  articulation markers per frame

Why it matters:

- same-value rewrites can matter
- internal counters can matter more than the written reload byte
- effective sounding state is not identical to note events

Scores:

- Explains triangle phrase: `+2`
- Explains bass over-sustain: `+2`
- Explains pulse 2 ending softness gap: `+2`
- Directly evidenced by data: `+2`
- Survives known contradictions: `+2`
- Requires minimal special pleading: `+2`

Total: `12`

Current status:

- strongest working theory
- now strengthened by direct evidence that the missing articulation is a
  composite pulse1+triangle attack marker, not a title-specific triangle patch

## H6. Missing layer = composite-bass voice is being flattened into isolated channel playback

Definition:

- the title bass instrument is not well described as "triangle alone"
- pulse 1 provides the percussive pluck
- triangle provides the low support/body
- playback still overweights steady triangle body and underweights envelope-led
  pulse attack

Scores:

- Explains triangle phrase: `+1`
- Explains bass over-sustain: `+2`
- Explains pulse 2 ending softness gap: `0`
- Directly evidenced by data: `+2`
- Survives known contradictions: `+2`
- Requires minimal special pleading: `+2`

Total: `9`

Current status:

- strong secondary theory
- likely a major subcomponent of `H1`
- especially important for the title cue, where the audible bass timbre appears
  to come from pulse attack plus triangle support rather than triangle alone

## H2. Missing layer = output filter / console output stage only

Definition:

- NES hardware/TV output shaping is the main missing ingredient

Scores:

- Explains triangle phrase: `0`
- Explains bass over-sustain: `-1`
- Explains pulse 2 ending softness gap: `+2`
- Directly evidenced by data: `+1`
- Survives known contradictions: `0`
- Requires minimal special pleading: `+1`

Total: `3`

Current status:

- real secondary factor
- not the primary missing layer

## H3. Missing layer = write-mask / same-value rewrite semantics only

Definition:

- preserving same-value rewrites and phase resets is sufficient

Scores:

- Explains triangle phrase: `+2`
- Explains bass over-sustain: `0`
- Explains pulse 2 ending softness gap: `0`
- Directly evidenced by data: `+2`
- Survives known contradictions: `0`
- Requires minimal special pleading: `+2`

Total: `6`

Current status:

- necessary
- probably not sufficient

This looks like a subcomponent of `H1`, not the full answer.
Same-value rewrites are clearly part of the answer, but the new evidence argues
that we also need a layer that knows when those rewrites form a musically
important composite attack across channels.

## H4. Missing layer = hidden note-duration/parser error

Definition:

- the ROM note lengths are still wrong, and the audible problems mainly come
  from bad duration decoding

Scores:

- Explains triangle phrase: `0`
- Explains bass over-sustain: `+1`
- Explains pulse 2 ending softness gap: `-1`
- Directly evidenced by data: `-1`
- Survives known contradictions: `-2`
- Requires minimal special pleading: `-1`

Total: `-4`

Current status:

- weak
- current data argues against this as the main diagnosis

## H5. Missing layer = project routing / single-track vs multi-track issue

Definition:

- the main problem is how the REAPER project is wired

Scores:

- Explains triangle phrase: `-1`
- Explains bass over-sustain: `-1`
- Explains pulse 2 ending softness gap: `+1`
- Directly evidenced by data: `0`
- Survives known contradictions: `0`
- Requires minimal special pleading: `+1`

Total: `0`

Current status:

- can make evaluation worse
- not the core cause

## Current Ranking

1. `H1` Frame audible-state IR: `12`
2. `H3` write-mask / same-value rewrite semantics: `6`
3. `H2` output filter / console output stage: `3`
4. `H5` project routing issue: `0`
5. `H4` hidden duration/parser error: `-4`

## What Counts As A Breakthrough

A breakthrough is **not**:

- a project that sounds slightly nicer
- a filter tweak that softens the highs
- a title-only patch that makes one phrase less embarrassing

A breakthrough is:

1. we identify a concrete data field that is missing from the current truth path
2. that field is observable or inferable from the source data
3. adding it explains both:
   - triangle articulation
   - pulse 2 ending softness behavior
4. the improvement follows from the data, not from ad hoc synth tuning

Current status:

- we now have a narrow breakthrough candidate:
  `composite frame-level retrigger / attack markers`
- evidence artifact:
  `wizards_and_warriors_title_articulation_breakthrough.json`
- supporting note:
  `wizards_and_warriors_title_articulation_breakthrough.md`

## Strongest Candidate Missing Information

The current best candidate is:

`effective per-frame audible state`

More specifically:

- effective gate/open state
- effective loudness state
- retrigger markers
- composite cross-channel attack markers
- phase-reset markers
- continuity class

This information is richer than:

- note events
- raw register latch bytes

and is the most likely missing middle layer.

## Next Proof-Oriented Steps

To increase confidence without relying on ear-check optimism:

1. Emit a first-class frame audible-state artifact for the title.
2. Compare three routes frame by frame:
   - raw latch replay
   - write-aware replay
   - audible-state replay
3. Show where each route diverges on:
   - sounding frames
   - retrigger frames
   - effective loudness curve
4. Promote only if the richer route explains both user complaints with one
   data-model change.

## Bottom Line

The current evidence strongly supports:

- the missing information is not just a note boundary
- not just a filter
- not just a routing bug

The leading theory is:

**there is a missing middle layer of frame-level audible-state information
between raw hardware control writes and MIDI/synth playback**
