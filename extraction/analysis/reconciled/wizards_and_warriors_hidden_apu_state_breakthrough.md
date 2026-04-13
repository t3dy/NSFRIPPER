# Wizards & Warriors Hidden APU State Breakthrough

This pass checks whether we have been misreading APU setup registers as live
audible state.

## Breakthrough

Yes. Two major playback assumptions are flattening real NES hardware behavior:

1. pulse `$4000/$4004` low nibble is being treated as current volume even when
   the `constant volume` bit is `0`
2. triangle `$4008` low 7 bits are being treated as a live linear counter even
   though they are only the linear-counter reload value

Both are hardware-state mistakes, not just “missing filter” mistakes.

## Pulse Evidence

Title pulse setup in the disputed phrase:

- pulse 1 `$4000 = 0x45`
- pulse 2 `$4004 = 0x43`

Decode of `0x45`:

- duty = `1`
- length-halt / envelope-loop = `0`
- constant-volume = `0`
- envelope period nibble = `5`

Decode of `0x43`:

- duty = `1`
- length-halt / envelope-loop = `0`
- constant-volume = `0`
- envelope period nibble = `3`

That means these bytes are **not constant volumes**.
They are hardware envelope settings.

Current repo behavior still flattens them into static volume:

- [nsf_to_reaper.py](/C:/Dev/NSFRIPPER/scripts/nsf_to_reaper.py) currently does:
  - `channels["pulse1"]["vol"] = value & 0x0F`
  - `channels["pulse2"]["vol"] = value & 0x0F`
- [ReapNES_APU2.jsfx](/C:/Dev/NSFRIPPER/studio/jsfx/ReapNES_APU2.jsfx) currently does:
  - `sx[sx_base + 1] = r0 & 0x0F`

So the current pipeline is reading “envelope period” as “steady loudness.”

That would absolutely make pulse notes sound like a synth blob instead of a
percussive harpsichord attack.

## Triangle Evidence

Title triangle setup in the disputed phrase:

- `$4008 = 0x81`

Decode of `0x81`:

- control / length-counter halt bit = `1`
- linear-counter reload value = `1`

Important hardware point:

- the low 7 bits of `$4008` are **not** the live current linear counter
- they are the reload value used by the internal linear-counter unit

Current repo behavior still flattens them into live audible state:

- [nsf_to_reaper.py](/C:/Dev/NSFRIPPER/scripts/nsf_to_reaper.py) currently does:
  - `channels["triangle"]["linear"] = value & 0x7F`
- [ReapNES_APU2.jsfx](/C:/Dev/NSFRIPPER/studio/jsfx/ReapNES_APU2.jsfx) currently uses:
  - `(r0 & 0x7F) > 0` as triangle gate

So once `$4008 = 0x81` is written, the current playback path effectively keeps
triangle “alive” forever until another explicit change, even though the real
hardware linear counter is an internal per-clock state machine.

That is a direct match for the user-heard bass over-sustain problem.

## Why This Fits The Ear Better Than “Missing Filter”

The user’s two strongest complaints were:

- bass notes sustain too long
- pulse lacks the percussive `tink`

These map cleanly to the two hidden-state mistakes:

- triangle over-sustain:
  we are using reload value as if it were current linear-counter state
- pulse lack of `tink`:
  we are using envelope settings as if they were constant steady volume

Filtering can still matter at the output stage, but it is downstream of this.
If the per-note amplitude shape is already wrong, EQ/filter cannot restore the
missing harpsichord or plucked-bass articulation.

## Architectural Consequence

The middle layer needs another promotion:

- not just frame register replay
- not just attack/release sideband
- also **derived hidden APU state**

At minimum:

- pulse envelope mode
- pulse constant-vs-envelope interpretation
- pulse current effective volume if envelope is active
- triangle linear reload value
- triangle effective current linear/gate state
- eventually triangle length-counter interaction if needed

## Ranked Hypotheses Now

1. strongest:
   hidden APU envelope/counter state is the major missing layer

2. secondary:
   release/body classification is still useful, but it was compensating for
   hidden-state loss rather than replacing it

3. weaker:
   output filter / tone-softening stage

## Bottom Line

The project was likely overlooking a more basic interpretation error:

- pulse setup bytes were being mistaken for live volume
- triangle reload bytes were being mistaken for live gate/counter state

That is a better explanation for the remaining title failures than a missing
mystery command or a generic filter alone.
