# Wizards & Warriors Title Composite Bass Audit

## Narrow question

Why does the disputed title phrase sound like a plucked/muted bass in the game
while current playback still sounds like an over-sustained synth body?

## Phrase window

Primary frames: `928`, `960`, `976`

These are the parser and write-aligned phrase points for the title bass figure.

## Proven facts from ROM/parser/write data

### 1. There is no hidden `$4015` gate command in the disputed phrase

Frame write capture for `920-980` shows writes to:

- `pulse1`: `$4000/$4002/$4003`
- `pulse2`: `$4004/$4006/$4007`
- `triangle`: `$4008/$400A/$400B`

There are **no `$4015` writes** in this phrase window.

Conclusion:

- the phrase is not being muted by a direct channel-enable toggle
- the missing effect is not explained by a hidden enable/disable command

### 2. Pulse 1 and triangle are synchronously retriggered by timer-high writes

At frames `928`, `960`, and `976`:

- pulse 1 rewrites `$4003`
- triangle rewrites `$400B`

At `960`, this happens even though the pitch stays the same:

- pulse 1 period remains `508`
- triangle period remains `253`

Conclusion:

- this phrase contains real hardware re-articulation on same-pitch writes
- a note-only model is too coarse even before timbre is considered

### 3. Pulse 1 is in hardware envelope mode, not constant-volume mode

In this phrase pulse 1 uses `$4000 = 0x45`.

Decoded:

- duty = `1`
- loop/halt = `0`
- constant volume = `0`
- envelope period = `5`

So pulse 1 is not a fixed-level square here. It is an envelope-driven attack/decay
voice.

### 4. Triangle is not showing an obvious live release command in the data

In this phrase triangle uses `$4008 = 0x81`.

Decoded:

- control = `1`
- linear reload = `1`

The raw write stream does not show an explicit mid-phrase triangle shutdown
command. The repeated writes are:

- `$4008 = 0x81`
- `$400B = 0x10` at `928` and `960`
- `$400B = 0x11` at `976`

Conclusion:

- the over-long bass body is not explained by a newly discovered command byte
- if the heard bass body is more muted than our playback, the missing behavior is
  in live APU state or composite mixing, not a newly found event opcode

## Proven facts from the reference audio

From the release IR and aligned audio measurements:

- frame `928` = `fresh_full_body`
- frame `960` = `fresh_attack_damped_body`
- frame `976` = `fresh_full_body`

At frame `960`:

- high-band onset is strongest in the window
- low-band body is much weaker than at `928` or `976`

Conclusion:

- the short event at `960` is real
- it is not a full fresh low-bass body
- the audible result behaves like a bright re-attack with reduced bass body

## Composite-bass interpretation

The strongest current interpretation is:

- the perceived "plucked bass" is a **composite voice**
- pulse 1 provides the sharp pluck/attack
- triangle provides steady low support
- the disputed frame `960` is heard mostly as a fresh pulse attack over a reduced
  low-body carry, not as a fully separate new triangle bass note

Why this fits the data:

- pulse 1 is definitely envelope-driven in this phrase
- pulse 1 definitely retriggers at `928` and `960`
- triangle definitely retriggers at the write level, but its visible state still
  looks too sustain-like if interpreted only as `$4008 > 0`
- the audio shows a bright attack spike at `960` without strong matching low body

## What this means for the current playback failure

The present playback is likely wrong in two coupled ways:

1. Triangle body is still too steady.
2. Pulse 1 pluck is still not dominant enough in the composite result.

That combination would make the phrase sound like:

- one long ringing bass body
- with too little percussive attack definition

Which matches the user-reported result.

## Ranked hypotheses

### H1. Composite bass voice is being flattened into "triangle sustain plus weak pulse"

Weight: strongest

Evidence:

- pulse 1 envelope mode is proven
- pulse 1 timer-high restarts at the key phrase frames are proven
- reference audio shows attack emphasis without matching low-body restart at `960`

### H2. Triangle live-state semantics are still missing beyond raw `$4008`

Weight: strong

Evidence:

- current playback still turns `$4008 = 0x81` into near-steady gate
- no data-backed mid-phrase mute opcode has been found
- the raw register view does not itself explain the reduced body at `960`

### H3. Hidden mystery ROM command or filter opcode causes the mute/pluck

Weight: weak

Evidence against:

- no `$4015` writes in the phrase
- no newly discovered phrase-local opcode in the parser stream
- normal note and control-shadow events already explain the visible structure

## Best next step

Do not keep searching first for a secret command.

The next proof-oriented step should be:

1. treat frames `928/960/976` as a **composite pulse1+triangle articulation**
2. derive a composite attack/body target from the aligned audio
3. reduce triangle's authority as the sole "bass instrument" for this phrase
4. audit whether pulse 1 envelope replay in the current plugin is actually
   dominating the mix enough to create the plucked onset
