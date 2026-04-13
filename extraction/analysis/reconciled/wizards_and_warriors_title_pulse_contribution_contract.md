# Wizards & Warriors Title Pulse Contribution Contract

## Purpose

This note turns the current pulse-envelope findings into a playback-facing
comparison for the disputed phrase.

It does **not** claim a cycle-perfect reconstructed pulse envelope.
It states the strongest current conclusion about what pulse must contribute at
the three key frames in order for the phrase to read correctly.

## Known Facts

At frames `928`, `960`, and `976`:

- `pulse1` is a fresh event each time
- `$4000 = 0x45`
- `const_vol = 0`
- hidden-state interpretation says effective pulse loudness should restart near
  full (`15`), not at the raw nibble value (`5`)

Current committed playback flattening:

- committed `APU2` treats the pulse loudness too much like raw nibble `5`

That implies a rough onset under-read of about:

- `15 / 5 = 3x`

This ratio should not be taken as final mixed loudness.
It is only a useful statement of how much pulse attack truth is currently being
flattened at the point of retrigger.

## Three-Frame Comparative Read

### Frame `928`

Current evidence says:

- pulse attack should restart strongly
- triangle also contributes a true full-body bass onset

Expected musical result:

- bright attack
- strong low body

If pulse is under-read here:

- the onset becomes softer than intended
- but the phrase can still sound "mostly right" because triangle body is strong

### Frame `960`

Current evidence says:

- pulse attack should restart strongly again
- triangle does **not** contribute an equivalent full-body renewal
- release class is `fresh_attack_damped_body`
- audio high-band is strongest here, while low body is reduced

Expected musical result:

- pulse-led pluck
- reduced low support

This is the frame where pulse flattening hurts the most.

If pulse is under-read here:

- the main attack identity becomes too weak
- the remaining low support feels over-exposed
- the listener reports "triangle sustain is too long" or "the bass lingers too
  much"

This symptom is therefore compatible with missing pulse attack truth, not just
with excess triangle sustain.

### Frame `976`

Current evidence says:

- pulse attack restarts strongly
- triangle returns to true full-body authority

Expected musical result:

- next full-bodied onset

If pulse is under-read here:

- the phrase still loses some pluck
- but triangle body again partly hides the mistake

## Contract

The current evidence supports this consumer-side contract:

1. Pulse should restart with high effective attack authority at `928`, `960`,
   and `976`.
2. Triangle should supply full body only at `928` and `976`.
3. The special audible identity of `960` depends more heavily on pulse than the
   other two frames do.
4. Therefore:
   - pulse-envelope reconstruction is optional-ish for `928/976`
   - pulse-envelope reconstruction is close to essential for `960`

## Bottom Line

The title phrase can sound too sustained even if note timing is correct because
the current playback likely makes this mistake:

- pulse attack is rendered too weakly at all three key retriggers
- especially at `960`, where triangle is supposed to be support-only rather
  than full-body

That gives the composite phrase the wrong center of gravity.
