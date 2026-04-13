# Wizards & Warriors APU2 Consumer Algorithm Sketch

## Purpose

This note describes the smallest consumer-side behavior change that would let
playback honor the already-exported title articulation data more faithfully.

It is intentionally phrased as an algorithm sketch, not an implementation
patch.

## Inputs Already Available

The current exported transport already provides:

- raw register state via SysEx `0x02`
- write mask via SysEx `0x02`
- articulation flags via SysEx `0x03`
- release class via SysEx `0x03`

The hidden-state and release artifacts already justify these phrase meanings:

- `pulse1` retriggers at `928`, `960`, `976`
- pulse is in hardware envelope mode at those frames
- triangle is `full_body` at `928` and `976`
- triangle is `support_only` at `960`
- `960` is a composite pulse-led event

## Consumer-Side State To Maintain

Per pulse channel:

- `env_mode`
- `env_period`
- `env_value`
- `env_divider`
- `last_r3`
- `attack_strength`

Per triangle channel:

- `triangle_body_gain`
- `triangle_support_only`
- `triangle_full_body`
- `last_release_class`

Per frame:

- `art_flags`
- `release_class`
- `write_mask`

## Pulse Algorithm

### On SysEx `0x02` for pulse

Decode from `$4000`:

- duty
- loop flag
- constant-volume flag
- low nibble

If constant-volume flag is `1`:

- use low nibble directly as current loudness

If constant-volume flag is `0`:

- treat low nibble as envelope period
- do **not** treat it as direct loudness

### On pulse retrigger

Trigger condition:

- timer-high rewrite and either:
  - hidden retrigger flag
  - visible period attack flag

On trigger:

- reset pulse phase
- reset envelope to near-full attack state
- restart envelope divider

### Per sample / per frame pulse loudness

Use:

- hardware-envelope-derived effective level

Not:

- raw nibble loudness

### Additional weighting for composite event

If pulse1 `flags & 0x08`:

- allow pulse attack to remain foreground
- do not suppress the restart into a same-pitch continuation

## Triangle Algorithm

### Base gate rule

Triangle should still require:

- enable bit active
- valid period

But `$4008 & 0x7F > 0` should not be treated as sufficient proof of full body.

### Body-authority rule

If `release_class == fresh_full_body`:

- `triangle_body_gain = full`

If `release_class == fresh_attack_damped_body`:

- `triangle_body_gain = reduced`
- `triangle_support_only = true`

If `release_class == ringing_decay`:

- `triangle_body_gain = decaying`

If `release_class == sustain_body`:

- `triangle_body_gain = medium / held`

The exact gain values remain to be tuned by evidence-guided listening, but the
classification boundary itself is already justified.

### Composite frame override

If triangle `flags & 0x08` and `release_class == fresh_attack_damped_body`:

- do not treat this as a full triangle re-onset
- keep triangle present
- reduce body authority relative to pulse attack

## Three-Frame Expected Behavior

### Frame `928`

- pulse attack restarts strongly
- triangle body gain = full
- result = fresh full-bodied onset

### Frame `960`

- pulse attack restarts strongly
- triangle remains present but body gain = reduced
- result = pulse-led pluck over damped low support

### Frame `976`

- pulse attack restarts strongly
- triangle body gain = full
- result = next full-bodied onset

## Why This Is The Right Next Contract

This sketch does not invent:

- a hidden opcode
- a fake title-only ADSR
- a new exporter dependency

It simply makes playback consume:

- known pulse envelope semantics
- already-exported articulation flags
- already-exported release classes

## Bottom Line

The next justified playback step is not "find more notes."

It is:

- reconstruct pulse attack from known hardware-envelope semantics
- demote triangle from full-body to support-only at `960`
- let the existing composite sideband actually affect playback
