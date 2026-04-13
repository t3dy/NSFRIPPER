# Wizards & Warriors Pulse Envelope Flattening Note

## Purpose

This note isolates one specific likely failure mode in the current playback
stack:

- `pulse1` hardware envelope behavior is present in the ROM / NSF evidence
- some of that truth is preserved in export metadata
- the committed fidelity synth still flattens it into a much steadier signal

That flattening can make the disputed title phrase sound like a low object that
"rings too long" even when the deeper problem is that the pulse pluck is not
speaking strongly enough.

## Hardware-Backed Facts

For the key title frames `928`, `960`, and `976`:

- `pulse1` is a real fresh event at all three frames
- at `928` and `960`, the period remains `508`, but `$4003` is rewritten
- `$4000 = 0x45`

Interpreting `$4000 = 0x45`:

- duty = `1`
- loop = `0`
- const_vol = `0`
- envelope period nibble = `5`

This is **hardware envelope mode**, not constant volume `5`.

## Hidden-State Evidence

The hidden-state title report already captures the important distinction:

- frame `928`: `pulse1 = hardware_envelope`, nibble `5`, effective volume `15`
- frame `960`: `pulse1 = hardware_envelope`, nibble `5`, effective volume `15`
- frame `976`: `pulse1 = hardware_envelope`, nibble `5`, effective volume `15`

Consequence:

- the low nibble should not be read as a steady output level
- each timer-high retrigger should restore a bright pulse attack shape
- the effective loudness should decay after the retrigger

## What The Exporter Preserves

`nsf_to_reaper.py` currently preserves several facts that point at this attack:

- parser boundaries
- hidden same-pitch retrigger flags
- visible period-attack flags
- composite hidden-attack flags
- per-frame raw register replay (`0x02`)
- per-frame articulation sideband (`0x03`)

But the editable note-track route still projects pulse level coarsely through:

- note on/off
- `CC11`
- `CC12`

That route does not preserve a hardware envelope curve inside the note span.

## Where The Flattening Happens

The committed `ReapNES_APU2.jsfx` SysEx path does this for pulse channels:

- reads `$4000`
- stores `r0 & 0x0F` as the pulse "volume"
- outputs the pulse directly at that stored level

So, in the current fidelity path:

- `$4000 = 0x45` becomes approximately "play at level `5`"
- `const_vol = 0` is not consumed as envelope-mode semantics
- timer-high retriggers do not reconstruct a live decay curve

This means the synth currently treats an envelope-driven pulse voice as a
mostly static-amplitude square wave.

## Why This Matters For The Title Phrase

Release-side audio evidence says:

- frame `928` = `fresh_full_body`
- frame `960` = `fresh_attack_damped_body`
- frame `976` = `fresh_full_body`

At frame `960` specifically:

- the high-band onset is strongest in the phrase window
- the low-band body is much weaker than at `928` or `976`
- triangle period does not change

That strongly suggests the audible "pluck" at `960` depends heavily on pulse
attack truth.

If pulse attack is flattened:

- the fresh onset will read too weakly
- the remaining triangle/body support will feel too exposed
- the user may describe the result as "triangle sustaining too long"

That symptom description is compatible with a pulse-envelope failure.

## Implication For A Middle Layer

The middle layer should preserve pulse information in a form the synth can
actually consume, for example:

- `pulse_env_mode`
- `pulse_env_period`
- `pulse_retrigger`
- `pulse_attack_strength`
- possibly `pulse_effective_level` as a derived playback hint

Without that, the stack keeps collapsing:

- hardware envelope voice
- into static nibble volume
- into a weaker-than-correct pluck

## Bottom Line

One major missing layer is now specific and concrete:

- the current playback stack does not reproduce live pulse envelope meaning
  after timer-high retriggers

That does not fully solve the title phrase by itself, but it is a strong
explanation for why the project can be structurally correct and still sound too
sustained or too blob-like in the disputed composite phrase.
