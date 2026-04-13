# Wizards & Warriors IR-Aware Playback Pass 1

## Scope

This pass implements the smallest credible playback-consumer upgrade for the
`Wizards & Warriors` title phrase without reopening parser work.

Target scope:

- title phrase around frames `896`, `928`, `960`, `976`, `992`, `1008`
- fidelity path only
- `ReapNES_APU2.jsfx` consumer behavior
- existing transport fields only where possible

This pass is **not** a final title solve.

## Changed Files

- [ReapNES_APU2.jsfx](/C:/Dev/NSFRIPPER/studio/jsfx/ReapNES_APU2.jsfx)
- [nsf_to_reaper.py](/C:/Dev/NSFRIPPER/scripts/nsf_to_reaper.py)
- [Wizards_&_Warriors_01_Wizards_&_Warriors_Title_releaseaware_v6_rebuilt.mid](/C:/Dev/NSFRIPPER/Projects/Wizards_and_Warriors/midi/Wizards_&_Warriors_01_Wizards_&_Warriors_Title_releaseaware_v6_rebuilt.mid)
- [Wizards_&_Warriors_01_Wizards_&_Warriors_Title_APU2_releaseaware_v7_rebuilt.rpp](/C:/Dev/NSFRIPPER/Projects/Wizards_and_Warriors/Wizards_&_Warriors_01_Wizards_&_Warriors_Title_APU2_releaseaware_v7_rebuilt.rpp)

## Playback Semantics Added

### 1. Pulse SysEx path now consumes middle-layer attack truth

Evidence used:

- hidden-state docs showing `$4000 = 0x45` / `$4004 = 0x43` are hardware
  envelope settings, not steady loudness
- title phrase hidden retriggers at `928` and `960`
- write-mask transport already present in `0x02`

Implemented behavior:

- `0x02` write mask is decoded in APU2
- pulse timer-high rewrites restart a narrow envelope replay model
- pulse SysEx path no longer treats envelope-mode low nibble as direct steady
  loudness
- APU2 now also consumes `0x03 level` when present, instead of ignoring it

### 2. Exporter now emits pulse effective level in the articulation sideband

Evidence used:

- hidden-state pass showing pulse effective title levels should restart near
  `15` at `928`, `960`, `976`
- prior `releaseaware_v5.mid` still carried stale `0x03 level = 5` for pulse1

Implemented behavior:

- pulse `0x03 level` is now derived from a narrow hardware-envelope replay
  model, not raw nibble volume

Concrete before/after:

- old `releaseaware_v5.mid`
  - frame `928`: pulse1 art = `[125, 3, 0, 19, 5, 3]`
  - frame `960`: pulse1 art = `[125, 3, 0, 27, 5, 3]`
  - frame `976`: pulse1 art = `[125, 3, 0, 21, 5, 4]`
- rebuilt `releaseaware_v6_rebuilt.mid`
  - frame `928`: pulse1 art = `[125, 3, 0, 19, 15, 3]`
  - frame `960`: pulse1 art = `[125, 3, 0, 27, 15, 3]`
  - frame `976`: pulse1 art = `[125, 3, 0, 21, 15, 4]`

### 3. Triangle SysEx path now consumes release-class body semantics

Evidence used:

- title release IR:
  - `928` = `fresh_full_body`
  - `960` = `fresh_attack_damped_body`
  - `976` = `fresh_full_body`
- composite attack marker at `960`
- hidden-state pass showing standard triangle counter semantics alone do not
  explain the remaining overhang

Implemented behavior:

- APU2 triangle SysEx path reads the existing `0x03 release_class`
- `fresh_attack_damped_body` lowers triangle body authority
- damped-body state now persists through the following `ringing_decay` frames
  until the next `fresh_full_body`

Why this matters:

- the earlier one-frame triangle dip was too weak; the overhang returned on the
  next frame because `ringing_decay` was mapped back to near-full body

## Phrase-Specific Expected Consequences

### Frame `928`

- pulse hidden retrigger should now read as a fresh attack
- triangle should remain full-body

### Frame `960`

- pulse hidden retrigger should now restart strongly
- composite marker is preserved
- triangle should remain present but with reduced body authority through the
  following decay span

### Frame `976`

- full-body attack behavior should recover
- triangle damped-decay carryover should reset

## Validation Performed

### Environment / deploy

- `session_startup_check.py`: PASS
- repo APU2 ASCII check: PASS
- installed APU2 ASCII check: PASS
- repo/install APU2 SHA-256 prefix match: `ffeb078e58829a31`

### Transport checks

- confirmed `releaseaware_v5.mid` already contained `0x02` and `0x03`
- confirmed old pulse sideband still carried stale `level=5`
- rebuilt versioned MIDI with pulse sideband updated to modeled effective
  levels

### Project rebuild

- generated versioned project:
  - [Wizards_&_Warriors_01_Wizards_&_Warriors_Title_APU2_releaseaware_v7_rebuilt.rpp](/C:/Dev/NSFRIPPER/Projects/Wizards_and_Warriors/Wizards_&_Warriors_01_Wizards_&_Warriors_Title_APU2_releaseaware_v7_rebuilt.rpp)

### Known validation limit

- headless REAPER render is still not a trustworthy validation path here
- this pass still requires interactive REAPER audition for the final phrase
  judgement

## Assumptions Still Approximate

- pulse envelope replay is intentionally narrow, not a full chip-perfect frame
  sequencer implementation
- triangle body authority is still inferred from release-class semantics rather
  than a proven live internal counter/body curve
- ordered intra-frame write effects are still not first-class playback data

## Unresolved Gaps

1. Triangle still has no fully proven per-frame effective body/gate curve.
2. Triangle `0x03 level` remains coarse (`1`) and is not yet a rich effective
   body signal.
3. The title may still need a stronger distinction between:
   - composite pulse-led attack
   - full-body bass onset
   - support-only low body
4. Interactive REAPER listening is still required to decide whether this pass
   materially improves separation in the disputed phrase.

## Trust Label

### Source / semantics scope

- melodic title phrase semantics were already supported by existing NSF/trace
  comparison and title IR work
- that evidence remains the basis for this pass

### Projection / playback scope

- this pass produces **hypothesis output**, not trusted output
- validation ladder status for the modified playback projection is:
  - below Rung 4 until interactive REAPER ear-check confirms the phrase
    improvement

Plainly:

- the consumer now honors more of the discovered middle-layer evidence
- the projection is improved and better grounded
- but it is **not yet claimable as trusted final title playback**
