# Middle Layer Recommendation

## Short Answer

Yes.

For fidelity playback, plain MIDI is too lossy, and raw register-latch replay
is also too lossy for some cues.

The pipeline needs a first-class middle layer between:

- observed per-frame hardware behavior
- downstream MIDI / SysEx / REAPER projection
- synth playback

That middle layer should not be "more notes."
It should be **frame-level audible-state IR**.

## Why MIDI Alone Is Not Enough

MIDI can represent:

- note on / note off
- controller changes
- coarse pitch changes

But NES playback depends on behaviors that are not equivalent to note events:

- same-pitch retriggers caused by timer-high writes
- phase reset on register writes
- frame-by-frame volume changes
- triangle gate behavior that does not equal note duration
- sweep / modulation that is not a semitone event
- output-state changes that affect articulation without changing pitch

For the `Wizards & Warriors` title, we already have a direct example:

- the first short bass note after the long one is a fresh hardware event
- it can disappear if we encode only note boundaries
- it can also disappear if we encode only latched register values

So the gap is not just "MIDI is lossy."
It is:

`musically important hardware behavior exists between note-level intent and raw register bytes`

## Why Raw SysEx Register Replay Is Still Not Enough

Raw register replay is better than plain MIDI, but it still misses cases where:

1. the visible register latch is not the same as the effective audible state
2. same-value rewrites matter
3. internal counters matter more than the exposed reload register
4. audible damping/gating is inferred from frame behavior rather than one byte

Examples:

- triangle: `$4008` is not itself the full audible envelope
- pulse/triangle attacks: same-value writes can retrigger phase/articulation
- end-of-note character: audible decay can depend on effective channel state,
  not just the last written timer value

That means the correct fidelity path is not:

- notes only
- or raw latch bytes only

It is:

- **observed frame behavior interpreted into an explicit audible-state layer**

## Recommended Middle Layer

## Name

`Frame Playback IR`

or more explicitly:

`Frame Audible-State IR`

## What It Should Contain

Per frame, per channel:

- timer period
- effective loudness or gate state
- duty / noise mode / sweep-visible state
- retrigger markers
- write-mask information
- phase-reset marker
- sounding/not-sounding decision
- note-continuity decision
- optional articulation class:
  - sustain
  - retrigger
  - mute
  - decay
  - gated-hold

Important distinction:

- raw register state is **observed control state**
- playback IR is **observed or inferred audible state**

Those are related, but not identical.

## Minimal Contract

For each frame/channel:

```json
{
  "frame": 961,
  "channel": "triangle",
  "period": 253,
  "effective_level": 1,
  "sounding": true,
  "write_mask": 13,
  "retrigger": true,
  "phase_reset": true,
  "gate_open": true,
  "continuity_group": 14,
  "articulation": "retrigger"
}
```

This is richer than MIDI but much more stable than plugin-specific code.

## Recommended Pipeline

For fidelity routes:

1. Observed source
   - trace
   - NSF emulation
   - ROM simulator

2. Canonical frame state
   - raw register / control facts

3. **Frame Audible-State IR**
   - audible gate / envelope / retrigger interpretation

4. Projection
   - note MIDI for editability
   - CC automation for effective loudness / duty
   - SysEx for register/write replay
   - REAPER project

5. Playback
   - synth consumes the richer IR projection, not just note data

## How To Project It

### For editable MIDI view

Keep:

- note on/off
- CC11 for effective loudness
- CC12 for duty

This is an editable approximation, not final truth.

### For fidelity playback

Use:

- SysEx register state
- plus write-mask / retrigger metadata
- plus effective gate/loudness metadata

This can still live inside one MIDI file if needed, but it is no longer
"plain MIDI."

## Best Concrete Forms

Ranked:

1. **MIDI + extended SysEx**
   - keeps REAPER compatibility
   - can carry write-mask + phase-reset + effective-state markers
   - best near-term choice

2. **MIDI + sidecar frame JSON**
   - easiest to debug
   - plugin or helper stage reads sidecar
   - good for development

3. **Dedicated monitor/helper plugin**
   - reads sidecar or extended SysEx
   - feeds the synth or visualizes state
   - useful later, not required first

## Recommendation For This Repo

Near-term:

1. Keep MIDI as the transport shell.
2. Promote SysEx from "raw latch replay" to "playback IR carrier."
3. Add explicit fields for:
   - write mask
   - retrigger
   - phase reset
   - effective loudness/gate
4. Treat note tracks as editorial view, not authority.

Fresh evidence backing this:

- `extraction/analysis/reconciled/wizards_and_warriors_title_articulation_breakthrough.md`
- `extraction/analysis/reconciled/wizards_and_warriors_title_audible_state_ir_report.md`

Those artifacts show a concrete title case where:

- note-only misses `3` hidden retrigger events in the disputed phrase window
- latch-only misses the same `3`
- write-aware sees those per-channel retriggers
- only the audible-state IR labels the composite pulse1+triangle attack at
  frame `960`

## Plugin Recommendation

Do **not** split immediately into many plugins.

Instead:

- keep one main playback synth
- allow it to consume richer playback IR
- optionally add a monitor/helper plugin later

What matters is not plugin count.
What matters is that the synth is no longer forced to infer everything from:

- note-on / note-off alone
- or raw latch bytes alone

## Explicit Answer To The User's Question

Yes:

the chiptune ROM/hardware is doing frame-by-frame behavior that plain MIDI
cannot fully encode.

And for this project, the correct fix is not just "better synth settings."
It is to introduce a middle layer that preserves frame-level audible behavior
before projection into MIDI/plugin playback.

## Practical Next Step

The next implementation step should be:

1. define `Frame Audible-State IR`
2. emit it as an artifact for title trace and NSF routes
3. extend the APU2 SysEx contract so playback can use:
   - raw register state
   - write mask
   - effective gate/loudness
   - composite attack / retrigger markers
4. judge title fidelity on that route, not on plain note MIDI
