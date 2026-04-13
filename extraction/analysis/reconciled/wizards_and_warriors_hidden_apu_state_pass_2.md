# Wizards & Warriors Hidden APU State Pass 2

This pass adds a standard 2A03-style hidden-state model over the title phrase:

- pulse envelope start / divider / decay
- triangle linear reload / reload flag / current counter

It does **not** claim perfect hardware timing yet.
It is a narrow falsification tool for the disputed phrase.

## Modeled Results In The Phrase

Key frames from the modeled hidden state:

| Frame | Pulse 1 effective vol | Pulse 2 effective vol | Triangle modeled counter |
| --- | ---: | ---: | ---: |
| `928` | `15` | `15` | `1` |
| `936` | `10` | `15` | `1` |
| `944` | `4` | `15` | `1` |
| `952` | `0` | `15` | `1` |
| `960` | `15` | `15` | `1` |
| `976` | `15` | `15` | `1` |

## Interpretation

### Pulse

The pulse result is exactly the kind of hidden hardware behavior we were missing:

- pulse 1 starts bright at frame `928`
- its modeled envelope level falls rapidly by `936`, `944`, and `952`
- the same-pitch retrigger at `960` resets it back to `15`

That is a much better explanation for the missing harpsichord-like `tink` than
"more filter" alone.

### Triangle

Under a standard linear-counter interpretation, the title triangle does **not**
solve the over-sustain problem by itself:

- `$4008 = 0x81` means reload=`1`, control=`1`
- repeated `$400B` writes set the reload flag
- with control bit `1`, the modeled counter remains effectively armed

So the standard hidden triangle counter model stays at `1` across the phrase.

That means:

- pulse hidden state is a strong real breakthrough
- triangle overhang is **not** fully explained by the standard linear-counter
  interpretation alone

## Ranked Consequences

1. strongest:
   pulse envelope state must become first-class playback data

2. still open:
   triangle body is likely too prominent in playback for a reason beyond just
   the raw linear reload register

3. plausible remaining causes for triangle overhang:
   - output/mix balance and perceived body weighting
   - title-specific release/body classification layer
   - another still-unmodeled hardware interaction

## Bottom Line

This pass gives a clean split:

- the missing pulse articulation is very likely hidden envelope state
- the remaining bass over-sustain is not fully closed by standard triangle
  counter semantics, so that branch stays open
