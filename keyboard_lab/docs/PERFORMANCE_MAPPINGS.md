# Performance mappings — giving the keyboard player access to NES dynamics

Companion to `keyboard_lab/docs/THE_LIVE_PERFORMANCE_PROBLEM.md`.  That
doc stated the problem (MIDI + keyboard can't capture everything the
NES hardware does).  This doc answers the **design question that
follows**: given the unavoidable gap, how do we give the keyboard
player continuous access to time-varying driver behavior through the
low-bandwidth human-interface channels available (a keyboard, 1-2
knobs, mod wheel, aftertouch, pitch wheel, a few pads)?

## The axis we're mapping

The NES produces time-varying register state at 60 Hz, driver-
controlled.  A human keyboard player produces roughly ~5 Hz of
velocity + position events plus ~5-30 Hz of mod-wheel / aftertouch /
CC knob updates.  **We are compressing 60 Hz × ~10 registers into
~40-50 Hz × ~5 control channels.**  That's real information loss;
our job is to make the loss musical instead of audible.

This doc catalogs **nine mappings**, each collapsing a specific
hardware behavior onto a specific keyboard gesture.  They are not
mutually exclusive — a real preset combines 3-5 of them.  Priority
ranking at the end.

## The nine mappings

### 1. Envelope macro control (volume trajectory)

**Hardware behavior**: per-frame volume changes via `$4000` envelope
period or software vol writes.  Character: fast decay (Castlevania),
long sustain (Mario overworld), loop (Battletoads drums).

**Keyboard controls**:
- **Velocity** → initial volume + decay speed
  (hard hit = bright attack + fast decay; soft hit = quiet steady).
- **Mod wheel (CC1)** → envelope shape morph
  (left = pluck, right = sustain).
- **Aftertouch** → sustain pressure / pseudo-loop
  (hold down harder to retrigger envelope).

**Audibility**: very high.  Volume trajectory is what the ear
locates first.

**Limitation**: cannot reproduce frame-perfect envelope resets or
irregular decay steps.  Those require SysEx replay (Priority 1).

**JSFX implementation**: already largely present (sliders 5-8 per
pulse set attack / decay / sustain / release).  Missing: mod-wheel
→ envelope-shape morph.  ~1 hour to add.

### 2. Duty cycle performance control (pulse animation)

**Hardware behavior**: `$4000/$4004` bits 6-7 select one of 4 duty
cycles.  Some drivers animate duty per-frame during sustained
notes (Battletoads, MM3 later).  This IS a signature timbre move.

**Keyboard controls**:
- **CC12 (or mod wheel)** → duty value (12.5%, 25%, 50%, 75%),
  quantized stepping (no smooth interpolation — hardware is discrete).
- Optional tempo-synced LFO → auto-cycling duty.
- Advanced: velocity → initial duty; aftertouch → duty sweep over
  time.

**Audibility**: one of the most audible NES "animations."

**Limitation**: real drivers change duty per-frame conditionally on
song state.  Our mapping is a simplification; user has to "perform"
the animation.

**JSFX implementation**: sliders 3, 9, 15 already expose duty per
channel.  Missing: a dedicated CC→duty mapping with quantization
in the JSFX input path.  ~2 hours.

### 3. Driver macro buttons (discrete behavior injection)

**Hardware behavior**: specific stylistic gestures that recur in a
driver family (Konami pulse stab, Nintendo sustain, Rare swell,
Square/Enix arpeggio burst).

**Keyboard controls**:
- Assign pads or keyswitches (e.g. octave below the playable range):
  - Pad 1 → "Konami stab" (fast decay + duty flip sequence).
  - Pad 2 → "Nintendo sustain" (flat volume, no decay).
  - Pad 3 → "Rare swell" (volume ramp + subtle duty motion).
  - Pad 4 → "Arpeggio burst" (fast pitch cycling).
- Each pad fires a time-programmed sequence of CC/pitch changes.

**Audibility**: high.  Gestures are recognizable signatures.

**Limitation**: discrete.  Not expressive unless layered with
continuous controls (velocity + mod wheel).

**JSFX implementation**: new territory.  Requires a "macro"
subsystem in the JSFX: a time-triggered playback of pre-canned
CC+pitch sequences fired by special key-range.  ~1-2 days.

### 4. Arpeggio engine on chords (chord illusion)

**Hardware behavior**: NES "chords" are usually one channel
rapidly cycling through 3 pitches (because only 4 channels total).

**Keyboard controls**:
- Detect multi-note input (user holds a chord).
- Convert to arpeggio cycle (up, down, custom pattern).
- Mod wheel → rate.
- Keyswitch → pattern selection.

**Audibility**: **signature**.  This is one of the most recognizable
NES illusions.

**Limitation**: timing must be tight (snap to tempo grid or high
frame rate) or it sounds like a generic MIDI arpeggiator.

**JSFX implementation**: new subsystem.  Needs note-tracking (hold
detection) + scheduled playback.  ~1 day.

### 5. Pitch micro-modulation (sweep + vibrato)

**Hardware behavior**: `$4001/$4005` sweep unit modulates pulse
period at 120 Hz; triangle has none.  Some drivers add software
vibrato via per-frame period tweaks.

**Keyboard controls**:
- Pitch bend → manual sweep (coarse).
- Aftertouch → vibrato depth.
- Automatic note-duration-sensitive vibrato (vibrato grows as note
  held longer).
- Optional: envelope-driven pitch dip at attack.

**Audibility**: medium.  Adds perceived analog-ness; most listeners
don't explicitly notice but feel it.

**Limitation**: hardware sweep uses bitwise shifts on the period
register.  Continuous pitch-bend approximates but doesn't exactly
match hardware behavior.

**JSFX implementation**: pitch bend is already mapped.  Missing:
automatic vibrato ramp with note age.  ~2 hours.

### 6. Noise channel reinterpretation (playable percussion)

**Hardware behavior**: noise = LFSR with 2 modes (long hiss / short
tonal) and 16 discrete period indices.  Not pitch-mapped.

**Keyboard controls (two paths)**:

**Path A: drum mapping** — specific keys trigger specific noise
configurations:
- C2 → kick (period 12, mode 0, short decay).
- D2 → snare (period 8, mode 0, medium decay).
- E2 → hi-hat closed (period 2, mode 1, fast decay).
- F2 → hi-hat open (period 2, mode 1, long decay).

**Path B: continuous control**:
- Velocity → noise burst length (via length counter).
- CC → "noise pitch band" (heuristic period mapping, not real pitch).

**Audibility**: high for drums, low for melodic noise.

**Limitation**: entirely interpretive.  Real games don't map
keyboard to noise — they just fire specific noise configurations
at specific musical moments.

**JSFX implementation**: already drum-mapped in the current JSFX
noise channel (note 36 = kick, 38 = snare, 42 = hat per the MIDI
export convention).  Missing: continuous-control path B.  ~2-4 hours.

### 7. Phase-reset / attack shaping (the "snap")

**Hardware behavior**: writing `$4003/$4007/$400B` resets the pulse
phase counter, producing an audible "snap" on note-on.  Real NES
notes have this; softer synthesized notes often don't.

**Keyboard controls**:
- Force phase reset on every note-on.
- Add 1-2 ms amplitude transient boost at attack.
- Velocity scales transient intensity.

**Audibility**: **very high** — it's the difference between "generic
keyboard synth" and "NES-like."  Users may not consciously name this
but will immediately hear "that sounds right."

**Limitation**: doesn't capture driver-timing subtleties (some
drivers delay the phase reset for rhythmic effect).

**JSFX implementation**: phase reset is already there in Priority 1
SysEx mode.  Missing: velocity-scaled transient boost in Priority 3
ADSR mode.  ~1 hour.  **This is the highest-ROI mapping.**

### 8. Time-quantized modulation (fake 60 Hz frame updates)

**Hardware behavior**: all NES register updates happen on 60 Hz
frame boundaries.  Smooth analog modulation doesn't exist on NES.

**Keyboard controls**: quantize ALL modulation updates to ~60 Hz
steps — volume, duty, pitch, whatever.  Inside the JSFX, round
down all CC applications to the next 16.67 ms grid point.

**Audibility**: subtle but real.  "Stepped" modulation sounds
hardware-like where smooth modulation sounds soft-synth-like.

**Limitation**: global approximation.  Different drivers used
different frame-counter rates (60 vs 240 Hz) for different
behaviors; we're flattening all to 60 Hz.

**JSFX implementation**: ~1 hour.  Just add a quantization step
at the CC-read path.

### 9. Performance-compression macro (single high-leverage knob)

**Hardware behavior**: multi-axis combinations specific to games
(e.g. "Battletoads pulse1 voice" = specific decay + specific duty
cycling + specific vibrato amount).

**Keyboard controls**: one macro knob labeled "Intensity" or
"Driver Energy" that coordinates:
- Envelope decay time.
- Duty animation depth.
- Vibrato amount.
- Slight detune / noise bleed.

Turning this one knob moves 4 parameters in a pre-defined
coordinated way.

**Audibility**: depends on tuning.  With a well-tuned macro,
extremely satisfying — "the game's personality knob."

**Limitation**: less precise per-axis control.  Good for
performance; bad for detailed sound design.

**JSFX implementation**: needs a macro-definition subsystem
(slider → multi-slider link with per-game tuning).  ~4 hours to
do right including 3-4 preset macros.

## Priority matrix

In implementation order (do first = most ROI):

| Rank | Mapping | Hours | ROI | Reason |
|------|---------|-------|-----|--------|
| 1 | Phase-reset + attack transient (#7) | 1 | Highest | Biggest "sounds like NES" win; trivial code |
| 2 | Envelope macro (#1) | 1 | High | Player already expects velocity→volume; easy add |
| 3 | Duty-cycle CC quantized (#2) | 2 | High | Signature NES timbre; CC already wired |
| 4 | Noise drum mapping refinement (#6A) | 2 | High | Drums already exist; fine-tuning velocity |
| 5 | Time quantization to 60 Hz (#8) | 1 | Medium-high | Subtle character upgrade, cheap |
| 6 | Pitch micro-modulation (#5) | 2 | Medium | Vibrato ramp adds life |
| 7 | Performance macro knob (#9) | 4 | Medium | Useful once 1-5 exist; depends on them |
| 8 | Arpeggio engine (#4) | 8 | Medium | Big win for NES-chord illusion; non-trivial |
| 9 | Driver macro pads (#3) | 16 | Medium | Requires macro subsystem; do after #9 proves out |

Implementing ranks 1-5 (~7 hours total) would take Variant B's
JSFX from "generic chiptune synth" to "recognizably NES-performing
synth."  That's the realistic first sprint.

## Integration with the three-priority cascade

Our existing design splits input sources:
- Priority 1: SysEx replay (file-driven, hardware-exact)
- Priority 2: CC11/CC12 automation (file-driven, simplified)
- Priority 3: ADSR keyboard (live)

All nine mappings above live **inside Priority 3**.  They are the
"compressed, playable abstractions" that make P3 sound game-
accurate.  None of them violate Priority 1 or 2 — if SysEx arrives,
the mappings are suppressed and P1 takes over; if CC arrives with
no SysEx, P2 uses CC11/CC12 and the keyboard's controls (velocity,
mod wheel) can still layer additional expression via the P3
mappings.

This cleanly answers the design question from
`THE_LIVE_PERFORMANCE_PROBLEM.md`: **Priority 3 is where we compress
hardware dynamics into performable controls.  The nine mappings are
the specific compression schemes.**

## What it takes to ship a playable preset per driver family

For each driver family (Capcom early, Konami, Rare, Sunsoft, etc.)
build one `preset` row in the keyboard_lab DB containing:

```json
{
  "envelope_shape": "castlevania_pluck",
  "duty_cycle": 2,
  "duty_anim": { "mode": "static", "depth": 0 },
  "sweep_depth": 0.1,
  "vibrato_ramp_ms": 300,
  "phase_reset_transient_ms": 1.5,
  "transient_gain": 0.3,
  "noise_drum_map": "nintendo_kit",
  "arpeggio_enabled": false,
  "performance_macro_center": 0.7
}
```

One preset per driver family × keyboard instance × game as needed.
See `keyboard_lab/db/init_keyboard_db.py` schema.

## Strategic takeaway (from the user's own framing)

> You cannot expose "everything the hardware does."  The winning
> strategy is:
>
> 1. Identify perceptually dominant behaviors.
> 2. Collapse them into low-dimensional controls.
> 3. Provide both continuous (CC) and discrete (macro) access.

That aligns exactly with the three-tier priority model.  What we're
building is a **performance grammar for NES behavior**, not a literal
hardware-fidelity interface.  The mappings above are the vocabulary
of that grammar.

## Next concrete action

Start with mapping #7 (phase-reset transient).  One hour of JSFX
code.  Test on Castlevania Vampire Killer bass + Battletoads pause
theme.  If the transient makes the keyboard "sound like NES" to the
ear, the doctrine is validated and we commit to implementing ranks
2-5.  If not, we rethink.

Ear-test result goes into `keyboard_lab/db/keyboard.db` as an
experiment row.
