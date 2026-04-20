# Live control mappings

A concrete, opinionated proposal for wiring a standard MIDI
controller to the ReapNES JSFX synth in Priority 3 (live play)
mode, implementing the Performance Abstraction Layer (PAL) Class A
and Class B dimensions from
`docs/PERFORMANCE_ABSTRACTION_LAYER.md`.

This doc specifies the **performer interface** — what the human
hands touch and what happens in the synth.  It is the visible
counterpart to the abstraction in the PAL doc.

## Design principles

1. **Few high-leverage controls over many low-level parameters.**
   The performer has two hands; complexity budget is small.
2. **Every performer gesture maps to exactly one NES behavior or
   one macro.**  No ambiguity about what a control does.
3. **Standard-controller-first.**  Target a common MIDI keyboard
   (61-88 keys, mod wheel, pitch bend, aftertouch, sustain pedal,
   ideally 4+ CC knobs).  No custom hardware required.
4. **Preset state, not per-note state, carries driver-family
   character.**  The performer switches presets between songs,
   not within them.
5. **Honor the PAL Class D non-performables.**  Don't expose
   controls for things that can't work live.  Pretend-controls
   that do nothing are worse than honest silence.

## Target hardware profile (nominal)

The mapping assumes a controller with at minimum:

- 49+ keys (ideally 61).
- Velocity-sensitive keys.
- Mod wheel (CC1).
- Pitch bend wheel.
- Channel aftertouch (monophonic).
- Sustain pedal input (CC64).
- 4 assignable CC knobs (any CC numbers).
- Optional: 4-8 velocity-sensitive pads.
- Optional: octave-shift / transpose buttons.

Fallback if fewer controls: most mappings still work with just
keys + mod wheel + pitch bend + velocity.

## The mapping

### Hand controls (always-on)

| Controller | MIDI | → NES behavior (PAL dim #) | Class |
|------------|------|---------------------------|-------|
| Note keys | note_on / note_off | Pitch (#1), Timing (#2) | A |
| Velocity | note_on.velocity | Initial volume (#3) + attack transient intensity (#6) | A |
| Mod wheel | CC1 | Duty cycle value 0-3 (#4, dynamic) | A/C |
| Pitch bend | pitch_bend | Sweep-like pitch modulation (#9), coarse | B |
| Aftertouch | channel_pressure | Vibrato depth (#10) + envelope-sustain press | A |
| Sustain pedal | CC64 | Extend release / hold gate open | A |

**Notes on intent**:

- **Velocity** does double-duty: initial volume AND transient
  intensity.  Hard hits are brighter AND louder, matching the
  "snap" character of NES attacks.
- **Mod wheel** quantizes to 4 discrete duty values (12.5% / 25%
  / 50% / 75%) — no smooth interpolation.  NES duty is discrete
  and the stepped feel is part of the sound.  Range 0-31 → duty
  0, 32-63 → duty 1, etc.
- **Pitch bend** range = ±2 semitones.  Continuous, but subtle.
  Not a full sweep emulator; a rough approximation of the sweep
  unit's effect.
- **Aftertouch** does dual duty: when you press harder on a held
  note, vibrato DEPTH increases (not rate); when you press
  harder at attack, it boosts the envelope sustain level.
  Depth effect is subtle (~20 cents max) to stay musical.

### CC knob controls (if available)

Four knobs, tuned for live-play expressiveness.  These are
performance-time adjustments that re-shape the preset without
switching presets.

| Knob | CC  | → NES behavior (PAL dim #) | Class | Notes |
|------|-----|---------------------------|-------|-------|
| 1    | CC74  | Envelope decay time (#7) | C-live | "Length" knob — short decay at 0, long sustain at 127 |
| 2    | CC71  | Performance-macro "Intensity" | multi | Moves 4 params at once; see §Performance Macro below |
| 3    | CC73  | Attack transient intensity (#6) | A | Independent of velocity, for setting the baseline snap |
| 4    | CC75  | Arpeggio rate (#11) when 2+ notes held | B | 0 = off; 1-127 = 1-16 Hz arp rate |

These CCs are sticky — they persist across notes within a session
but not across project reloads.  Their default values come from
the preset.

### Keyswitches (pads or low-range keys)

If the controller has pads, assign them directly.  If not, use the
lowest octave (C0-B0, MIDI notes 12-23) as keyswitches, with the
playable range starting at C1.

Each keyswitch fires a **macro** — a time-scheduled sequence of
internal parameter changes the synth runs autonomously.  Macros
implement PAL Class B dimensions.

| Pad / Key | Macro name | → NES dimension (#) | Description |
|-----------|-----------|---------------------|-------------|
| Pad 1 / C0 | Konami stab | #5 duty anim + #6 transient | Flip duty 25%→50%→25% over 2 frames + sharp attack |
| Pad 2 / D0 | Nintendo sustain | #5 off + #7 long decay | Flat volume with no duty change; decay 400 ms |
| Pad 3 / E0 | Rare swell | CC11 ramp + #10 vibrato | Slow 200 ms volume ramp up + auto-vibrato |
| Pad 4 / F0 | Phase-reset burst | #6 max transient + phase reset | For re-articulating the same held pitch |
| Pad 5 / G0 | Drum kit A (kick/snare/hat) | #14 noise bursts | For noise-channel-instance tracks |
| Pad 6 / A0 | Drum kit B (alternative) | #14 variant | Different pre-tuned drum bursts |
| Pad 7 / B0 | Arp hold | toggle arpeggio engine | Stays on until retoggled |
| Pad 8 / C#0 | Clear all macros | reset | Emergency stop for runaway macro states |

Keyswitches are **momentary** by default (except Pad 7 toggle).
Firing a macro does not interrupt the currently-held note; macros
layer their parameter changes on top of the regular envelope
state.

### Pedal (sustain) behavior

CC64 (sustain pedal) extends the release of any currently-fading
note.  Held pedal → notes ring until pedal is released.  No
all-notes-off behavior; just release extension.

**Not** mapped: arpeggio hold (use Pad 7), volume freeze (use
aftertouch), infinite sustain (explicitly avoided because NES
triangle is the only channel that can actually sustain
indefinitely).

## Per-channel instance configuration

Each NES channel (pulse1, pulse2, triangle, noise, optionally DMC)
is a separate JSFX instance on its own REAPER track, receiving
MIDI from one of up to 5 input channels.

### Typical layout

```
track 1 "Pulse 1"   JSFX Ch Mode=0  MIDI in: ch 1 (keyboard ch 1)
track 2 "Pulse 2"   JSFX Ch Mode=1  MIDI in: ch 2
track 3 "Triangle"  JSFX Ch Mode=2  MIDI in: ch 3
track 4 "Noise"     JSFX Ch Mode=3  MIDI in: ch 4  -- drum kit
(optional track 5 "DMC" for sampled content)
```

### Keyboard range splits (optional)

If controlling all channels from one MIDI channel, split by range:

- C1-B3: pulse1 + pulse2 (two-handed chord voicing).
- C0 and below: keyswitches + drum pads.
- C4-C7: triangle (bass) or note layering.

Channel splits are preferred where the controller supports them
(most mid-range controllers can split).

## Preset switching

Presets load per-channel slider state (Class C dimensions).
Switching mid-performance:

- Via program change (CC0/CC32 + PC).
- Via keyswitch in the lowest octave if PC unavailable.
- Via REAPER's plugin state recall.

**Recommended practice**: switch presets between songs, not
during.  Switching mid-note causes envelope discontinuities.

Ships with at least 4 presets per NES channel:
- "Capcom-Kondo" — bright, duty 25%, fast decay.
- "Konami-Maezawa" — static duty 50%, medium decay.
- "Rare-Wise" — dense animation, duty 25%+50% alternating.
- "Sunsoft" — heavy bass emphasis, duty 12.5%.

Presets persist in the keyboard_lab DB as `preset` rows; see
`keyboard_lab/db/README.md`.

## Performance Macro (CC71)

The "Intensity" knob on CC71 collapses multiple per-frame
behaviors into a single performable dimension.  Internally it
drives:

- Envelope decay: slower at low intensity, faster at high.
- Duty animation enable: off at low, on at high.
- Vibrato: low depth at low, full depth at high.
- Transient boost: subtle at low, aggressive at high.

The macro is a **preset-tuned curve** — different presets have
different maps from CC71 → internal parameters.  A Capcom-Kondo
preset might map CC71 to just volume + decay; a Rare preset
might add duty animation more aggressively.

This implements PAL §"Performance-compression macro" (mapping #9
from `PERFORMANCE_MAPPINGS.md`).

## What's deliberately NOT mapped

Per PAL Class D, these gestures are NOT available:

- No "per-frame register editing" keyboard input.  Use Priority 1
  SysEx for that.
- No DMC sample-address selection.  Use Priority 1 SysEx.
- No frame-counter-mode switching.
- No direct `$4015` manipulation from the keyboard.
- No `$4011` DMC DAC absolute-value writes.

Trying to expose these would clutter the interface without
audible benefit.

## Implementation status

Of the mappings above, current JSFX supports:

- ✅ All Hand controls except aftertouch (needs wiring).
- ⚠️ CC knob control: only Channel Mode (slider 1) and Keyboard
  Mode (slider 2) on CCs.  The four performance knobs (decay,
  intensity, transient, arp rate) not yet wired.
- ❌ Keyswitches: no macro subsystem yet.
- ❌ Arpeggio engine.
- ❌ Performance macro.
- ✅ Preset switching via slider state (but not via program
  change yet).

Completing the "missing" items is the work of the JSFX priority
list in `docs/JSFX_LIVE_PRIORITY.md` (Deliverable 4).

## Validation protocol

Once an item is implemented, validate via:

1. Connect a MIDI keyboard to REAPER.
2. Load a Variant B project (e.g.
   `outputv6_B/Castlevania/reaper/02_Song_02.rpp`).
3. Play the target mapping.  Confirm audibly.
4. Insert `experiments` row in keyboard_lab DB with overall
   rating.
5. Insert `findings` rows per capability dimension with scores
   (1-10).
6. Update `approach_capabilities` row for the JSFX approach with
   new coverage level (exact / approximate / preset / unsupported)
   and `verified_date`.

## Open questions (hypotheses to test)

- HYP-LCM-1: is 4 CC knobs enough, or do performers want 8?
  Answered by ear-tests on controllers with varying knob counts.
- HYP-LCM-2: is the low-octave-as-keyswitch scheme ergonomic,
  or do performers prefer dedicated pads?  Depends on the
  controller form factor.
- HYP-LCM-3: does per-JSFX-instance MIDI-channel routing
  overwhelm REAPER users?  Alternative: single JSFX in Full-APU
  mode.

Each hypothesis ear-tests as a single experiment.  Results feed
back into this doc.
