# Wizards & Warriors Middle-Layer Coverage Matrix

## Purpose

This matrix asks one narrow question:

For the disputed title phrase, which hardware-backed facts are already
captured, which are transported, which are consumed by the current synths, and
what audible consequence follows when a fact is flattened away?

It is not a proposal to add arbitrary synth controls.
It is a checklist for preserving phrase-critical hardware meaning.

## Matrix

| Hardware / musical fact | Present in ROM / analysis | Transported now | Consumed by committed APU2 | Likely audible consequence when missing |
| --- | --- | --- | --- | --- |
| Pulse timer-high retrigger at `928/960/976` | Yes | Yes, in raw regs and hidden-retrigger flags | Partly; period updates and enable only | Attack boundary exists but reads too weakly |
| Pulse envelope-mode vs constant-volume distinction (`const_vol=0`) | Yes | Indirectly in raw `$4000`; not explicit in sideband | No | Pluck is flattened into static square loudness |
| Pulse effective post-retrigger loudness is initially high, then decays | Yes, in hidden-state interpretation | No explicit live curve; CC11 only mirrors nibble-like `vol` | No | High-band onset under-spoken, phrase sounds too blob-like |
| Triangle parser boundary at `960` | Yes | Yes | No phrase-specific interpretation | Hidden event treated too much like ordinary note continuation or ordinary restart |
| Triangle same-pitch retrigger is not equivalent to pulse retrigger | Yes, by combined write/audio evidence | Partly, via flags | No | `960` loses its special identity |
| Triangle full-body onset vs support-only continuation | Yes, in release IR (`fresh_full_body` vs `fresh_attack_damped_body`) | Yes, as `release_class` | No | Triangle body stays too prominent where it should be reduced |
| Composite `pulse1 + triangle` hidden attack at `960` | Yes | Yes, `flags bit3` | No | Playback cannot promote pulse-led attack over low support |
| Triangle `$4008` reload/control is not direct audible level | Yes | Raw reg carried | No; treated largely as gate presence | Triangle can read as too continuously authoritative |
| Write mask for the frame | Yes | Yes, `0x02` payload | No | Same-pitch events lose some articulation meaning |
| Ordered write sequence inside the frame | Not yet fully preserved | No | No | Possible residual mismatch in onset feel |
| Hardware mixer nonlinearity | Yes in principle | N/A | Yes, basic mixer math | Better than generic synths, but still under-informed by missing articulation fields |

## What This Says About The Missing Layer

The phrase is not mainly failing because the stack lacks:

- note timing
- pitch identity
- channel existence

The phrase is mainly failing because the stack still cannot preserve or
consume enough information about:

- pulse attack truth
- triangle body authority
- composite cross-channel articulation

## Most Valuable Fields To Promote

If the middle layer promotes only a few extra concepts, the highest-value ones
appear to be:

- `pulse_env_mode`
- `pulse_attack_strength`
- `pulse_retrigger`
- `triangle_body_authority`
- `triangle_support_only`
- `composite_pulse_led`

These can all be justified by current ROM / NSF / aligned-audio evidence.

## Bottom Line

The current project is close because the structural music survives transport.

The remaining error is concentrated in a thinner but more important layer:

- whether a fresh event is full-body or damped-body
- whether pulse should dominate the onset
- whether triangle is foreground body or background support

That is exactly the layer a middle representation is for.
