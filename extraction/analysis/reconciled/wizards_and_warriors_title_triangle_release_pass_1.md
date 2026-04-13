# Wizards & Warriors Title Triangle Release Pass 1

This pass asks one narrow question:

- does the reference title audio behave like one long sustained triangle note through the disputed phrase?
- or does it behave like a damped/plucked bass where the body has already fallen away before the same-pitch retrigger?

## Scope

- source audio: `C:\Dev\NSFRIPPER\state\ww_mp3_ref\1 - Wizards & Warriors Title.wav`
- source duration: `37.1170975s`
- effective frame count from WAV duration at `60 Hz`: `2227.0258`
- phrase window inspected: title frames `920-980`

Relevant triangle parser events in this window:

- frame `928`: period `253`, duration `32`
- frame `960`: period `253`, duration `16`
- frame `976`: period `284`, duration `16`

This is the exact region where the same-pitch short bass note has been reported as “missing” or masked by the previous note.

## Frame-Level Audio Read

For each NES-sized frame window, I measured:

- low-band energy: roughly `60-400 Hz`
- high-band energy: roughly `1500-5000 Hz`
- frame RMS

### Key frames

| Frame | Low band | High band | RMS | Read |
| --- | ---: | ---: | ---: | --- |
| `928` | `26.91` | `2.19` | `0.2725` | long-note onset with strong bass body |
| `944` | `17.51` | `2.06` | `0.1922` | decaying body |
| `952` | `14.91` | `1.62` | `0.1794` | body continues to fall |
| `959` | `14.69` | `1.94` | `0.1597` | previous note already much weaker |
| `960` | `12.37` | `3.56` | `0.1801` | bright retrigger, weak bass body |
| `961` | `11.56` | `3.31` | `0.1804` | same pattern continues |
| `966` | `9.06` | `2.17` | `0.1210` | body still damping away |
| `976` | `27.69` | `2.28` | `0.2710` | next pitch change produces full body again |

## What This Rules Out

The reference audio does **not** look like:

- one uninterrupted sustained bass body from `928` through `975`
- a second full-bodied copy of the `928` note at `960`

If it were a simple long sustain, low-band energy around `960` would stay near the `928` onset level.
It does not. It falls from about `26.9` at frame `928` onset to about `14.7` by frame `959`, then only about `12.4` at the `960` retrigger.

## What The Audio Supports

The reference behaves more like this:

1. frame `928` starts a strong plucked bass body
2. the low body decays substantially before frame `960`
3. frame `960` produces a fresh bright attack
4. that same-pitch short note does **not** regenerate the same full bass body
5. frame `976` does restore a strong body when the pitch changes

That is much closer to:

- `fresh_attack + damped_body`

than to:

- `fresh_attack + full sustain`

## Ranked Interpretation

1. strongest: the missing title layer includes effective per-frame triangle damping/release, not just attack truth
2. weaker: output filtering alone
3. weak: parser duration error

## Architectural Implication

The current audible-state IR is still missing at least one field in spirit, even if we name it differently later:

- `effective_release_class`

Candidate values:

- `fresh_full_body`
- `fresh_attack_damped_body`
- `ringing_decay`
- `effectively_muted`

The disputed title short bass note at frame `960` is best described, from current evidence, as:

- `fresh_attack_damped_body`

not as:

- `ordinary sustained note`

## Bottom Line

This pass strengthens the user-heard diagnosis.

The problem is not just that a short bass note exists in the data.
The problem is that our current playback model still lets too much bass body survive across the phrase.

The reference title audio supports a model where the previous body has already decayed heavily by the time the same-pitch retrigger happens, and the retrigger itself is comparatively attack-heavy and body-light.
