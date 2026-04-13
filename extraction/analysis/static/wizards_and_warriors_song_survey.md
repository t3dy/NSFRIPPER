# Wizards & Warriors Song Survey

This note summarizes a structural survey of all 16 `Wizards & Warriors` songs
using the current discovery-stage parser.

The purpose is not to claim musical correctness for every track.
The purpose is to answer:

- which channels are active per song
- which streams are likely sentinel/inactive
- which songs look like strong next candidates for simulator work
- which songs appear to reuse other songs' channel data

## Method

For each NSF song number:

1. emulate the NSF init routine
2. recover per-channel pointers from channel RAM state
3. parse each channel structurally with the current parser
4. record event count, bytes consumed, and terminal event type

This reflects parser/discovery state only.

## Key Global Findings

### 1. `0xF1E0` is a Common Inactive / Sentinel Stream

The stream at `0xF1E0` appears in many songs, especially on noise and
sometimes triangle. In the title capture it is inactive, looping on a trivial
sentinel pattern rather than producing audible events.

Songs using `0xF1E0`:

- song 1 noise
- song 3 noise
- song 4 noise
- song 7 triangle
- song 7 noise
- song 9 noise
- song 10 triangle
- song 10 noise
- song 11 noise
- song 12 noise
- song 13 noise
- song 14 noise
- song 16 pulse1

### 2. Song 16 Appears to Reuse Song 2 Material in a Rotated Layout

Song 16 pointers:

- pulse1 -> `0xF1E0`
- pulse2 -> `0xF1E8`
- triangle -> `0xF20D`
- noise -> `0xF232`

Song 2 pointers:

- pulse1 -> `0xF1E8`
- pulse2 -> `0xF20D`
- triangle -> `0xF232`
- noise -> `0xF293`

This strongly suggests song 16 is an alternate arrangement / reduced variant
of song 2 rather than fully independent data.

### 3. The Title Is Not an Outlier

The title track was a good first target because:

- it has clean capture data
- pulse and triangle channels are active
- noise is inactive, reducing complexity

But the broader survey suggests the same parser architecture should transfer
to many other songs, especially those dominated by pulse/triangle content.

## Per-Song Structural Summary

### Song 1 - Title

- pulse1 `0xF07B`: 116 events, ends with `StopEvent`
- pulse2 `0xF0E0`: 297 events, ends with `StopEvent`
- triangle `0xF1A3`: 91 events, ends with `StopEvent`
- noise `0xF1E0`: sentinel/inactive loop

This is currently the best-understood song.

### Song 2 - Forest of Elrond

- pulse1 `0xF1E8`: 60 events, loop-driven
- pulse2 `0xF20D`: 60 events, loop-driven
- triangle `0xF232`: 151 events, loop-driven
- noise `0xF293`: 49 events, loop-driven

This is a strong next full-track candidate because all 4 channels appear active
and structurally nontrivial.

### Song 3 - Tree

- pulse1 `0xF2B3`: 101 events
- pulse2 `0xF2EF`: 93 events
- triangle `0xF327`: 53 events
- noise `0xF1E0`: inactive sentinel

Also a strong candidate because the noise channel is absent and the track is
compact.

### Song 4 - Ice Cave

- pulse1 `0xF345`: 233 events
- pulse2 `0xF3EB`: 230 events
- triangle `0xF492`: 231 events
- noise `0xF1E0`: inactive sentinel

This is large, rich, and probably excellent once the generic simulator is more mature.

### Song 5 - Low on Energy

- pulse1 `0xF539`: 25 events
- pulse2 `0xF54F`: 33 events
- triangle `0xF564`: 33 events
- noise `0xF578`: 13 events

A short track and likely good for validating multi-channel handling quickly.

### Song 6 - Initial Registration

- pulse1 `0xF582`: 80 events, explicit stop
- pulse2 `0xF5B1`: 77 events, explicit stop
- triangle `0xF5F2`: 267 events, explicit stop
- noise `0xF641`: 83 events, loop-driven

Another useful candidate because multiple channels terminate cleanly.

### Song 7 - Got an Item

- pulse1 `0xF668`: 25 events, explicit stop
- pulse2 `0xF68A`: 23 events, explicit stop
- triangle `0xF1E0`: inactive sentinel
- noise `0xF1E0`: inactive sentinel

Very strong candidate for a quick confidence pass after the title.

### Song 8 - Outside Castle Ironspire

- pulse1 `0xF694`: 68 events
- pulse2 `0xF6CB`: 145 events
- triangle `0xF72D`: 68 events
- noise `0xF764`: 37 events

Moderate complexity, likely a good later target.

### Song 9 - Castle Ironspire

- pulse1 `0xF77B`: 95 events
- pulse2 `0xF7D8`: 108 events
- triangle `0xF854`: 82 events
- noise `0xF1E0`: inactive sentinel

Good candidate because noise is absent.

### Song 10 - Entering a Door

- pulse1 `0xF8A4`: 12 events, explicit stop
- pulse2 `0xF8B3`: 12 events, explicit stop
- triangle `0xF1E0`: inactive sentinel
- noise `0xF1E0`: inactive sentinel

Excellent short-form validation target.

### Song 11 - Map

- pulse1 `0xF8C2`: 8 events, explicit stop
- pulse2 `0xF8CA`: 25 events, explicit stop
- triangle `0xF8D2`: 10 events, explicit stop
- noise `0xF1E0`: inactive sentinel

Another excellent short-form target.

### Song 12 - Potion

- pulse1 `0xF8DA`: 39 events
- pulse2 `0xF8F3`: 11 events
- triangle `0xF932`: 10 events
- noise `0xF1E0`: inactive sentinel

Short and structurally manageable.

### Song 13 - Fire Cavern

- pulse1 `0xF959`: 185 events
- pulse2 `0xF9D9`: 192 events
- triangle `0xFA45`: 38 events
- noise `0xF1E0`: inactive sentinel

Rich but probably a later-stage candidate.

### Song 14 - Inside the Big Tree

- pulse1 `0xFA55`: 72 events
- pulse2 `0xFA9B`: 10 events
- triangle `0xFAC4`: 39 events
- noise `0xF1E0`: inactive sentinel

Could be a practical medium-complexity target.

### Song 15 - Boss

- pulse1 `0xFB0B`: 196 events
- pulse2 `0xFB72`: 257 events
- triangle `0xFBC3`: 157 events
- noise `0xF1E0`: inactive sentinel

Large and likely a strong stress-test once the simulator is more generalized.

### Song 16 - Forest of Elrond (alt)

- pulse1 `0xF1E0`: inactive sentinel
- pulse2 `0xF1E8`
- triangle `0xF20D`
- noise `0xF232`

Structurally appears derived from song 2.

## Recommended Next Targets

If the goal is fastest progress:

1. Song 7 - very short, pulse-only core
2. Song 10 - very short
3. Song 11 - very short

If the goal is best transfer of the current title work:

1. Song 2 - full active arrangement and likely shared logic with song 16
2. Song 3 - no active noise
3. Song 9 - no active noise

If the goal is strongest later stress-test:

1. Song 4
2. Song 13
3. Song 15

## Practical Recommendation

The best next main target is probably **Song 2 - Forest of Elrond**.

Reasons:

- all 4 channels appear active
- it likely shares reusable logic with song 16
- it is structurally rich enough to expose remaining command semantics
- it should generalize the title work better than a tiny jingle would

If a quick confidence win is preferred first, use **Song 7** or **Song 10**
before Song 2.
