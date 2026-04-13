# Wizards & Warriors Middle-Layer Implementation Target

## Purpose

This note answers a practical question:

If we want to stop the title phrase from collapsing into an over-sustained
composite, which missing fields can be derived **right now** from existing
export data, and which would require a new transport field?

## Already Available In Export Data

The current exporter already emits enough information to derive most of the
phrase-critical interpretation:

- raw per-frame register state (`0x02`)
- per-frame write mask (`0x02`)
- parser boundary flag (`0x03 bit0`)
- hidden same-pitch retrigger flag (`0x03 bit1`)
- visible period attack flag (`0x03 bit2`)
- composite hidden attack flag (`0x03 bit3`)
- sounding flag (`0x03 bit4`)
- release class (`0x03 payload byte 3`)

For this title, that means the transport already knows:

- when `pulse1` has a fresh same-pitch attack
- when `triangle` has a hidden same-pitch boundary
- when the frame is the special composite `960` case
- when the frame should read as `fresh_full_body` vs
  `fresh_attack_damped_body`

## Derivable Today Without New Export Fields

These fields can be derived by a playback consumer from what we already emit:

### `pulse_retrigger`

Derivation:

- `flags & 0x02` for pulse channels

### `composite_pulse_led`

Derivation:

- pulse1 `flags & 0x08`

Interpretation:

- this is already the best marker for the special `960` event

### `triangle_support_only`

Derivation:

- triangle `release_class == fresh_attack_damped_body`
- especially when paired with composite hidden attack

### `triangle_full_body`

Derivation:

- triangle `release_class == fresh_full_body`

### `phase-reset-like attack cue`

Derivation:

- pulse write mask includes timer-high register write
- hidden retrigger or visible period attack also present

This is already richer than note-only or latch-only playback.

## Not Fully Derivable Today

These fields are only partly present and would still need either:

- a more explicit derived sideband
- or synth-side reconstruction logic

### `pulse_env_mode`

Partly available:

- raw `$4000` carries `const_vol`

Problem:

- committed APU2 does not expose this as a playback concept

### `pulse_attack_strength`

Partly available:

- can be inferred from envelope mode plus retrigger

Problem:

- there is no exported "effective pulse loudness curve"
- synth would need to reconstruct the envelope countdown

### `triangle_body_authority`

Partly available:

- release class strongly hints at this

Problem:

- current sideband uses coarse `level`
- there is no explicit scalar for "foreground body" vs "background support"

### Ordered intra-frame attack dominance

Not available as first-class transport truth.

Problem:

- write mask tells us which registers changed, not the exact order

This may matter less than the missing pulse envelope / triangle body
distinction, but it remains a possible residual gap.

## Practical Conclusion

A useful middle-layer implementation does **not** require inventing many new
concepts from scratch.

The exporter already emits enough to support a much better playback contract if
the synth starts consuming:

- `0x03` flags
- `release_class`
- envelope-mode semantics from `$4000`

The highest-value missing reconstruction is:

- pulse envelope meaning after retrigger

The highest-value missing interpretation is:

- triangle `full_body` vs `support_only`

## Bottom Line

The next fidelity step is likely **consumer-side**, not exporter-side:

- the transport already carries most of the important phrase markers
- the committed synth simply does not read them yet

So the middle layer is not hypothetical anymore.
It already exists in partial form in the exported sideband; it just is not yet
being honored by playback.
