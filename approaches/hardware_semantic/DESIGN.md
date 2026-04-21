# Hardware-Semantic Translation — Design

Working design document.  Tied to concrete fidelity blockers, not vague
architecture.

## 0. Positioning

**Supersedes (as a mental model):**
- The project as "NSF-to-MIDI ripper"
- The JSFX as "synth polish downstream of MIDI"
- "Zero parse errors" as a fidelity claim

**Establishes:**
- A unified interpretive stack: capture -> reconstruct -> project -> render
- A middle-layer IR (Channel Behavior Graph, CBG) that preserves hardware
  semantics
- A validation model anchored in Mesen trace / libgme / ear-test
- A slice-by-slice roadmap with Oracle-recording hooks at each gate

**Scope:** additive.  The stems renderer (outputv6, Rule 31), existing JSFX
(ReapNES_APU2_v2, ReapNES_Studio), and current extractor
(`scripts/nsf_to_reaper.py`) remain in place.  This approach lives at
`approaches/hardware_semantic/` and will grow its own prototype pipeline
in parallel until it demonstrably matches or exceeds the existing paths.

**Reference games for all validation in this document:**
- **Contra** -- triangle bass rings over as one sustained drone.
  One-sided failure (too long).
- **Wizards & Warriors title + early stages** -- triangle bass rings over
  AND drops out in the same song.  Two-sided failure.  User has ear-tested
  extensively and can confirm acceptance.  This is the primary validator
  because any model that fixes W&W handles the general case -- it cannot
  be fixed by a one-directional adjustment.

## 1. Problem Reframing

### What the hardware actually is

A NES game's audio is not a sequence of notes.  It is a state machine of
five APU channels (pulse1, pulse2, triangle, noise, DMC) plus optional
expansion chips (VRC6, FDS, VRC7, MMC5, 5B, N163), driven at 60 Hz by a
6502 CPU running driver code, producing analog output through a
non-linear DAC through an RC-filter into a speaker.

"Notes" are a human transcription abstraction.  They exist nowhere in the
hardware or the driver.  A driver loop might:

- Write duty=2, period=0x3A5, vol=15 at frame 0
- Decrement vol to 12 at frame 3
- Write period=0x3A5 again at frame 5 (phase reset + length reload)
- Decrement vol to 9, 6, 4 at frames 6-8
- Stop writing at frame 9 (HW envelope decay takes over, if enabled)
- Hardware length counter expires at frame 14

There is no "note on" or "note off" in that stream.  There is state
transitions that the listener interprets as articulation.

Different drivers encode articulation differently, even within the same
"driver family":

- **Contra triangle:** driver writes $400B (retrigger) and sets
  linear_reload to a small value so the linear counter decays to 0
  between notes.  Liveness goes false between notes naturally.
- **W&W title triangle:** driver uses a mix of $400B retriggers AND
  direct state manipulation.  In some stages it writes reload=127
  (no decay) and in others reload=15 (fast decay).  Liveness must track
  both paths.  Single-mode fixes break the other.
- **SMB triangle:** driver uses $4015 bit 2 + length counter for gating
  instead of linear counter.  Totally different articulation path.

### Three-layer-pitfall

Architecture Rule 12 names this: **Observed -> Intent -> Projection.**
The current pipeline tries to go Observed -> Projection in one step
(register writes -> MIDI notes), with the middle layer implicit and
scattered across `frames_to_channel_data`, W&W-specific boundary maps,
Rule 30 gates, etc.

The middle layer must be explicit and queryable.  That is what CBG is.

### The real project

A bidirectional interpretive translator:

```
 NES hardware behavior  <-- validation --.
           ^                             |
           | extraction                  |
           v                             v
         [CBG]  <-- shared schema -->  [CBG]
           ^                             |
           | projection                  |
           v                             v
  DAW (MIDI + SysEx + plugin state)  <-- round-trip check
```

- Forward path (extraction): `NSF/trace -> CBG -> MIDI + plugin state`
- Reverse path (authoring): `MIDI edits or keyboard -> plugin's internal
  CBG rebuild -> hardware simulation -> audio`
- Both directions must agree on CBG semantics, or the plugin's audio
  drifts from what the extractor intended.

This is not "MIDI with extra data."  It is a shared interpretive
contract.  MIDI is one projection of CBG, not the CBG itself.

## 2. Middle Layer Redesign — Channel Behavior Graph

### Design goals

1. Preserve causality -- which register write caused which audible event
2. Preserve liveness -- was the channel actually audible at frame N
3. Distinguish driver intent (explicit register writes) from hardware
   side-effect (counter decrements, envelope decay)
4. Represent non-note events natively (DAC writes, sweep, noise-mode
   changes, phase resets)
5. Support multiple projections (MIDI, SysEx, stem audio, notation,
   plugin state)
6. Queryable: "what was pulse 1 doing at frame 273, and why"

### Event taxonomy

All events share:

```python
@dataclass
class CBGEvent:
    frame: int                  # 60 Hz frame index
    quarter: int                # 0-3, for 240 Hz sub-frame resolution
    channel: ChannelId          # pulse1 / pulse2 / triangle / noise / dmc / vrc6_* / ...
    event_type: EventType
    source: Source              # REGISTER_WRITE / HW_INTERNAL / DERIVED
    cause: Optional[EventRef]   # ref to prior event enabling this one
    audibility: Audibility      # AUDIBLE / SILENT / GATED_OUT / DEGENERATE
    confidence: Confidence      # HIGH / MEDIUM / LOW
    payload: dict               # type-specific fields
```

Initial event-type enumeration:

**Gate / articulation**
- `GATE_OPEN` -- channel audibility begins (derived from state transition)
- `GATE_CLOSE` -- channel audibility ends
- `RETRIGGER` -- $4003 / $4007 / $400B write (phase reset + counter reload)
- `LENGTH_RELOAD` -- $400F / length-bits write
- `LINEAR_RELOAD` -- $4008 reload flag set + consumed

**Envelope / volume**
- `ENV_SW_SET` -- driver wrote a volume ($4000/$4004/$400C lower nibble
  with const_vol=1)
- `ENV_HW_STEP` -- derived: hardware envelope decrementer stepped at
  quarter-frame
- `ENV_HW_RELOAD` -- hardware envelope counter reloaded

**Timbre**
- `DUTY_CHANGE` -- $4000 / $4004 upper bits change
- `NOISE_MODE_CHANGE` -- $400E bit 7 toggle
- `EXPANSION_TIMBRE` -- VRC6 duty, FDS wave upload, VRC7 instrument, 5B env

**Pitch**
- `PERIOD_SET` -- full period write ($4002+$4003, $4006+$4007, etc.)
- `PERIOD_LOW_ONLY` -- $4002/$4006/$400A without hi write (sub-semitone
  modulation)
- `SWEEP_ACTIVE` -- sweep unit running, computed period per quarter-frame
- `SLIDE` -- period change without retrigger (driver-driven portamento)

**DAC / sample**
- `DPCM_TRIGGER` -- sample playback start (Rule 37)
- `DAC_WRITE` -- direct $4011 write (Rule 28 mechanism 2)
- `DPCM_SILENCE` -- sample_bytes_remaining reached 0

**Liveness / meta**
- `LIVENESS_RESOLVED` -- materialized per-frame audibility (dense, one
  per channel per frame)
- `DRIVER_SILENT_FRAME` -- driver updated nothing; HW continues per rules

### CBG = sparse events + dense liveness array

Per channel:

```python
@dataclass
class ChannelCBG:
    events: list[CBGEvent]                    # sparse, observation-derived
    liveness: np.ndarray[Audibility]          # dense, one per frame, resolved
    instrument: Optional[InstrumentBinding]   # template + params (Phase 4+)
```

Liveness is computed by walking the event stream forward and applying
HW simulation.  It is the **single source of truth** for "is this
channel sounding at frame N."

### Why this beats notes+CC

- Notes force a binary on/off decision at encoding time; CBG defers it
  to a query
- CC11/CC12 encode magnitude but drop causality; CBG records "HW
  envelope decremented to 9" vs "driver wrote 9"
- MIDI has no representation for phase reset, length counter reload,
  sweep; CBG has all of them as first-class events
- CBG is lossless re: what the hardware did; MIDI is a lossy projection
  that can be validated against CBG

### Projections

From a fully-built CBG we can emit:

1. **Editable MIDI** -- pitched events + CC automation; note boundaries
   come from liveness transitions (not from guessed pitch continuity)
2. **Archival SysEx** -- per-frame register state blob for lossless
   replay (Priority 1 in the existing input cascade)
3. **Plugin state snapshots** -- internal-register values for plugin
   on-load restore
4. **Stem audio** -- per-channel WAV rendered from CBG's liveness + state
   arrays directly (this is what the current stems pipeline does, but
   with CBG as the intermediate)
5. **Score notation** -- quantized rhythm + pitched notes for
   visualization / YouTube
6. **CBG-to-CBG edit** -- user edits pitch in DAW, MIDI projection
   re-derives CBG, plugin runs CBG forward

Each projection is a pure function of CBG + projection parameters.
MIDI round-trip errors are errors in the projection, not in CBG.

## 3. Channel Liveness Model

### Per-channel liveness conditions (formal)

Each channel is AUDIBLE in a frame iff all its hardware gates are open:

**Pulse 1 / Pulse 2**

```
audible(f) = vol(f) > 0
        AND length_counter(f) > 0     [unless env_loop halts LC]
        AND $4015_bit_k(f) == 1
        AND period(f) >= 8             [sweep mute condition per NESdev]
```

Retrigger semantics: `$4003 / $4007` write -> phase_counter=0, LC
reload from LENGTH_TABLE, and retrigger marked in CBG.

**Triangle**

```
audible(f) = linear_counter_live(f) > 0
        AND length_counter(f) > 0
        AND $4015_bit_2(f) == 1
        AND period(f) >= 2
```

Linear counter is the crux of the Contra/W&W bug class:

- $4008 write latches `reload_value` and `control_bit`
- $400B write sets internal `reload_flag`
- At each quarter-frame tick (240 Hz):
  - If `reload_flag == 1`: `linear_counter = reload_value`
  - Else if `linear_counter > 0`: `linear_counter -= 1`
- If `control_bit == 0`: `reload_flag` is cleared at the end of each
  quarter-frame

The current extractor records `linear_reload` (latched) as if it were
the live counter.  It is not.  This is what causes W&W bass to ring
over and Contra bass to be one sustained drone.

The same simulation produces the *drop-out* bug: if the driver writes
$4008 with `reload_value=15` but then delays $400B for several frames,
the previous bass note decays to silence before the retrigger.  Liveness
goes false during the gap.  Current extractor does not model this, so
we keep emitting a MIDI note that should have ended.  The plugin then
sustains it -- producing the "holding the previous bass note too long"
sound the user has heard.

**Noise**

```
audible(f) = vol(f) > 0
        AND length_counter(f) > 0       [unless env_loop halts LC]
        AND $4015_bit_3(f) == 1
```

Already modeled in current extraction (Rule 30 + Rule 32).  CBG
formalizes the events rather than adding more rules.

**DMC**

```
audible_sample(f) = sample_bytes_remaining(f) > 0 AND $4015_bit_4(f) == 1
audible_dac(f)    = dac_transition_within_window(f)
audible(f)        = audible_sample OR audible_dac
```

Rule 37 -- don't fire DPCM_TRIGGER on parameter-latch writes when DMC
is disabled.  CBG honors this naturally because DPCM_TRIGGER's
`cause` field must point to the $4015-enable edge.

**VRC6 pulse / saw**

```
audible_pulse(f) = vol(f) > 0 AND enable_bit(f) == 1
audible_saw(f)   = accum_rate(f) > 0 AND enable_bit(f) == 1
```

No length counter on VRC6.  Purely driver-controlled.

**FDS wave**

```
audible(f) = vol_gain(f) > 0 AND master_vol(f) > 0 AND period(f) > 0
```

Plus modulator unit state, to be modeled in Phase 7.

**VRC7 / 5B / N163** -- own sub-documents, Phase 7.

### Audibility levels (not just binary)

```
AUDIBLE     -- channel DAC non-zero this frame
SILENT      -- any gate false by volume/counter/period (natural silence)
GATED_OUT   -- explicitly silenced by $4015 bit clear
DEGENERATE  -- in a HW-edge-case range (sweep mute, period < 2 triangle)
```

Distinguishing SILENT-by-state from GATED_OUT-by-$4015 matters for
articulation: drivers treat these differently as boundaries, and our
MIDI projection can collapse them differently too.

### How liveness reframes note-boundary logic

Current extractor decides note boundaries from:

- Period change
- OR phase_reset fires
- OR vol goes 0->nonzero

This misses the W&W bass cases where period stays constant, phase
resets happen, vol stays nonzero, but the linear counter decays.  The
W&W `note_boundary_map` workaround is a hand-coded patch around this
specific case.

In CBG + liveness:

- Note boundary = `liveness` transitions `AUDIBLE -> SILENT -> AUDIBLE`
  **or** `RETRIGGER` event inside an `AUDIBLE` run **or** `PERIOD_SET`
  event with period delta > threshold

Contra bass: linear_counter_live decays between driver retriggers ->
liveness false for a frame or two -> boundary falls out.

W&W bass: same mechanism closes over both ringing-over and
dropping-out cases simultaneously.  Ringing-over = liveness was false
but we were still emitting audio; drop-out = liveness was true but we
had MIDI gaps.  Correct liveness = correct boundaries in both
directions.

SMB drums: noise length counter drop-out gives per-hit boundaries.

## 4. FamiTracker-Inspired but Hardware-Faithful

### What we borrow

- **Instruments** as reusable parameter bundles: per-channel
  characteristic sound captured as volume/duty/pitch/arpeggio sequences
- **Sequences** as parametric curves driving per-frame state
- **Effect codes** as edit-friendly shorthand for common driver idioms
  (Axy arpeggio, 4xy vibrato, Sxx release)
- **Loop / release points** in sequences, matching the
  `{attack, sustain-loop, release}` driver pattern

### Where FamiTracker is insufficient

**1. Parametric sequences can't represent all drivers.**

W&W title pulse 2 modulates duty in a non-periodic pattern tied to
driver state.  No FT sequence template reproduces it exactly.  We need
*opaque* sequences: a blob of per-frame register state attached to an
instrument, non-editable as parameters but editable as pitch.

**2. Effect codes lose causality.**

`A03` means "arpeggio A-C-E".  But the driver may have used:

- $4002/$4003 writes cycling three periods every 2 frames, OR
- $4003 retrigger each step, OR
- Period once + sweep unit chirping

These are different CBG events.  Collapsing to A03 loses the
extraction-time decision about which mechanism produced the sound.

**3. No representation for HW-internal state.**

FT effects don't express "HW envelope at step 5 of 15" or "linear
counter reloaded this quarter-frame."  These matter for live keyboard
play and for faithful re-rendering.

### Behavior Template library

A **behavior template** is an executable rule for per-frame channel
state:

```python
class BehaviorTemplate(ABC):
    name: str
    params: dict

    def apply(self, frame: int, channel_state: ChannelState,
              midi_input: MidiContext) -> FrameUpdate:
        """Given a frame index, current state, and MIDI context
        (note, velocity, CCs), return register updates for this frame."""
```

Built-in templates (initial set):

- `HWEnvelopeDecay(period, start_vol)` -- $4000 bit 4=0 mode
- `SWLinearFade(start, end, frames)` -- driver writes vol each frame
- `DutyAlternator(duties, rate)` -- Family 3 pattern (SMB3, KHS)
- `SweepChirp(direction, shift, rate)` -- $4001/$4005 effect
- `LFSRDrumBurst(period, length_load)` -- noise drum pattern with LC decay
- `SunsoftDPCMBass(notes)` -- Rule 28 mechanism 2
- `TriangleStaccato(reload_value)` -- short-reload triangle (Contra bass)
- `TriangleSustained(control_bit=1)` -- drone triangle (some W&W stages)
- `OpaqueReplay(frame_blob)` -- fallback: replay observed frames verbatim

Templates are identified from extracted CBG events during ingest:

- Scan event streams for known patterns (duty alternator, chirp, drum
  burst, linear-counter cadence)
- Fit parameters by least-squares or pattern-match
- If fit confidence > threshold, tag instrument with parametric
  template; else fall back to `OpaqueReplay`
- Driver classification (Rule 18) extends to template fingerprints

### Instrument / template separation

- **Instrument** = user-visible editable entity (name, assigned channel,
  selected template, parameters)
- **Template** = executable per-frame state generator
- **Opaque template** = instrument tied to observed frames: pitch is
  editable, per-frame duty/vol aren't

User flow:

- Import Castlevania NSF -> CBG built -> templates identified ->
  instruments bundled -> MIDI + RPP with instruments attached as
  Program Change + SysEx preamble
- User edits a pitch in REAPER -> MIDI changes -> plugin re-runs
  template with new pitch -> hardware-accurate output
- User picks Castlevania's lead instrument for their own composition ->
  Program Change on MIDI channel -> plays from MIDI keyboard ->
  plugin runs template live

## 5. Emulator-Driven Validation Model

### Ground truth hierarchy (restated in CBG terms)

1. **Mesen trace** -- ground truth APU register stream per frame
2. **libgme stem audio** -- ground truth audio, 44.1 kHz
3. **NSF emulation (py65)** -- convenience source; trust requires
   validation
4. **VGM logs** -- third-party crosscheck for NSF
5. **NES-MDB** -- library for spot-checks

### Validation as CBG diff

Given trace T, our extraction E, render R:

| Gate | What it checks                              | Operates on           | Cost      |
|------|---------------------------------------------|-----------------------|-----------|
| A    | register byte diff(T, E)                    | raw register streams  | trivial   |
| B    | CBG event diff(T, E), modulo known projections | CBG events         | cheap     |
| C    | liveness diff(T, E), +/-1 frame tolerance   | dense liveness arrays | cheap     |
| D    | articulation diff(T, E), +/-1 frame         | RETRIGGER events      | cheap     |
| E    | spectral diff(R, libgme), per-band threshold| rendered audio        | moderate  |
| F    | human ear confirmation                      | listening session     | user-time |

Gates A-D are **CBG-internal** -- fast, no audio rendering, isolate
interpretation bugs from synthesis bugs.

Gate E is audio-domain.  Already tooled (libgme reference + spectral
compare).

Gate F is **mandatory** before claiming "done."  Per memory "No
overclaiming."

### Why B/C/D are the new capability

Today we can only run A (trivially) and E/F.  When audio is wrong, we
can't isolate whether liveness is wrong, articulation is wrong,
synthesis is wrong, or mixing is wrong.  CBG gates let us localize:

- Audio off + C passes + E fails -> synthesis bug (LP filter, DAC, etc.)
- Audio off + C fails -> liveness model bug (the W&W bass case)
- Audio off + B fails but C passes -> extractor decode bug on a
  non-liveness event type

### Reference regression set

Minimum set of games that every rule change must pass:

| Game              | Chosen because it exposes                         |
|-------------------|---------------------------------------------------|
| Contra            | Triangle ring-over (one-sided triangle failure)   |
| W&W title + stage | Ring-over AND drop-out (two-sided triangle)       |
| SMB overworld     | Noise length counter (Rule 32)                    |
| Castlevania 1     | Pulse envelope + noise gate (Rule 36)             |
| Battletoads s1    | DMC direct DAC + triangle staccato                |
| Metroid           | DMC phantom trigger (Rule 37)                     |
| Mega Man 2        | HW envelope-driven decay (Family 1A)              |
| Sunsoft (Batman)  | DPCM bass + sweep unit                            |

Each has a known expected behavior (trace + libgme render + ear-test
notes).  Regression harness runs gates A-E across this set and flags
any regression.

### Oracle hooks for validation

Every CBG extraction run produces Oracle-recordable artifacts:

- `record_attempt` before the run (hypothesis, planned_change)
- `record_outcome` after (which gates passed, evidence refs)
- `propose_claim` per game for driver-identified templates
- `log_decision` if the run changes the game's extraction route
- `prevention_patterns` for any failure mode uncovered

## 6. Representation Gaps — Prioritized

Tied to concrete games and fidelity blockers:

| # | Gap                                   | Affected                          | Priority |
|---|---------------------------------------|-----------------------------------|----------|
| 1 | Triangle linear counter live sim      | Contra, W&W, many others          | **P0**   |
| 2 | const_vol vs HW envelope distinction  | Family 1 (156 games)              | **P0**   |
| 3 | $4015 init modeled as CBG events      | Rule 36 games                     | P1       |
| 4 | Sweep unit applied to pitch           | Sunsoft, Blaster Master, Batman   | P1       |
| 5 | Length counter for pulse / triangle   | TBD census                        | P1       |
| 6 | DPCM sample-ID classification         | Battletoads, SMB3 drums           | P2       |
| 7 | Frame counter mode ($4017 bit 7)      | Games using 5-step mode           | P2       |
| 8 | VRC7 FM modeling                      | Lagrange Point, Magical Kid Gogo  | P3       |
| 9 | 5B YM2149 envelope                    | Gimmick                           | P3       |
| 10| FDS modulator unit                    | Doki Doki, CV3 JP                 | P3       |

**P0** = required for the new approach to demonstrate value vs current
pipeline on the two primary reference games (Contra, W&W).

**P1** = required for 80% of non-expansion games.

**P2** = kit/drum fidelity.

**P3** = expansion chips; deferred.

### Closing P0 gap 1 — triangle linear counter live sim

Existing code: `scripts/nsf_to_reaper.py:1568+` simulates
`tri_linear_live` **inside the stem renderer only**.  The MIDI
extraction (`frames_to_channel_data`) records latched `linear_reload`,
not the live counter.

Plan:

1. Lift the sim into the builder layer (i.e. the CBG equivalent of
   `frames_to_channel_data`)
2. Record it as a per-frame CBG fact (on the `LIVENESS_RESOLVED` event
   for triangle)
3. Drive MIDI note-boundary decisions off liveness, not pitch continuity
4. Port the same sim into the new JSFX so plugin behavior matches CBG

Validation: gates A-C on Contra + W&W.  Ear-check Gate F with user
confirming bass articulation is right in both directions.

### Closing P0 gap 2 — const_vol vs HW envelope

Currently we assume software volume writes drive per-frame CC11.  But
Family 1 games use `const_vol=0` mode and let hardware envelope
decrement the volume.  We get CC11 = const value from the latched
`env_period` (which is the envelope *start* volume, not the live
output).

Plan:

1. Detect mode per-channel per-game:
   - `mode = HW_ENVELOPE` if `$4000 bit 4 == 0` and per-frame vol
     writes are sparse (<= 0.5 per note)
   - `mode = SW_VOLUME` if `$4000 bit 4 == 1` or per-frame vol writes
     are dense (>= 2.8 per note)
   - `mode = MIXED` otherwise; classify per-note
2. Emit `ENV_HW_STEP` events derived from the HW simulation (240 Hz
   quarter-frame decrement)
3. MIDI projection uses derived volume, not latched
4. Plugin implements HW envelope state machine

Validation: Family 1A games (Mega Man, Marble Madness) should see
CC11 envelope shapes matching libgme output.  Gate E spectral correlation
should improve materially over current CC11-from-latched behavior.

## 7. REAPER / JSFX Architecture Implications

### The plugin's redefined job

Not "play NES-style sounds."  Instead: **be a parameterized NES APU
implementation** that accepts MIDI + SysEx + instrument-state and
produces hardware-faithful audio, with full CBG semantics internal.

### Architecture

```
MIDI stream in
   |
   v
[MIDI Decoder] ---> [Event Router] --->
                         |
         +---------------+---------------+---------------+---------------+---------------+
         v               v               v               v               v               v
    [P1 State]      [P2 State]      [Tri State]    [Noise State]    [DMC State]    [VRC6 / FDS / ...]
    period, vol,    period, vol,    period,        vol, period,     dac, sample_    chip state
    duty, env_ctr,  duty, env_ctr,  lin_ctr,       mode, len_ctr,   remaining,
    len_ctr,        len_ctr,        len_ctr,       LFSR state       rate_idx,
    phase, sweep    phase, sweep    phase                           loop
         |               |               |               |               |               |
         v               v               v               v               v               v
    [DAC Synth]     [DAC Synth]     [DAC Synth]    [DAC Synth]      [DAC Synth]    [Expansion DAC]
    bandlimited     bandlimited     continuous     LFSR + LC        DPCM + DAC      per-chip
    pulse, HW env   pulse, HW env   wave, Rule-34  gate              + rate-idx
    + LC gate       + LC gate       hold on gate                     timing
                                    close
         |               |               |               |               |               |
         +---------------+---------------+---------------+---------------+---------------+
                                         |
                                         v
                              [Non-Linear Mixer]
                              pulse pin + TND pin per architecture.md Rule 27
                                         |
                                         v
                              [4-pole Butterworth LP 14 kHz]
                                         |
                                         v
                              [1-pole HP DC Blocker ~10 Hz]
                                         |
                                         v
                                      Output
```

### Input mode cascade (per channel, per frame)

1. **SysEx register-state in** -- if arriving, write directly to
   channel state, bypass MIDI interpretation entirely.  Maximum fidelity.
2. **CC-driven** -- if CC11/CC12/custom CCs are present, drive channel
   state from CCs + period from MIDI note.  Editable path.
3. **Instrument template** -- if neither, run the selected
   `BehaviorTemplate` for the channel with MIDI note/vel input.
4. **Manual knobs** -- no template, use slider positions.  Live
   keyboard default.

Priority resolved per-channel per-frame, not globally.  A track can
have CCs on pulse 1 (editable) and SysEx on noise (archival fidelity)
at the same time.

### Internal tick rates

| Rate      | What runs                                           |
|-----------|-----------------------------------------------------|
| Sample rate (44.1 / 48 kHz) | DAC output synthesis               |
| 240 Hz (quarter-frame)      | HW envelope step, triangle linear counter, sweep unit |
| 120 Hz (half-frame)         | Length counters                    |
| 60 Hz (frame)               | MIDI event dispatch, CBG event apply |

JSFX @sample is the hot loop; sub-frame counters increment by fractional
steps per sample.  Existing APU2_v2 already has quarter-frame triangle
linear counter sim -- reuse.

### MIDI vs plugin responsibility split

**In MIDI (what the extractor emits):**
- Pitched note events (for editability, score, visualization)
- CC11 / CC12 (volume / duty for non-HW-envelope modes)
- Custom CCs for secondary channel params if needed
- Program Change for instrument/template select
- SysEx for:
  - Initial plugin state (per-channel regs)
  - Archival per-frame register state (optional, high-fidelity)
  - Retrigger events that don't map to MIDI (rare articulations)

**In plugin (what JSFX implements):**
- All hardware state machines (envelope, LC, linear counter, sweep, LFSR)
- Non-linear DAC mixing (Rule 27)
- Bandlimited synthesis (Rule 35 polyBLEP or 3-level edge)
- Analog LP + DC block (Rule 33)
- BehaviorTemplate library (preset bank)

**Not in either, derived:**
- Per-frame liveness (plugin computes from state)
- Channel pair interaction (non-linear compression of pulse 1 by pulse 2)

### Why non-linear mixing belongs inside the plugin

Non-linear mixing requires simultaneous access to all channel
amplitudes (Rule 27).  REAPER's per-track FX chain can't do this --
each plugin instance sees only one MIDI channel's output.  Rule 31
(stems approach) exists because of this.

The new plugin uses **single-track full-APU routing**.  MIDI channels
0-3 (plus expansion chip channels) all feed the same plugin instance.
Plugin mixes internally.  Non-linear DAC is invariant-preserved.

Trade-off vs current per-channel tracks:
- Con: less per-channel control in REAPER's mixer UI
- Pro: non-linear mixing works as hardware
- Pro: plugin is single source of truth for audio

This is a deliberate architectural decision, not a convenience.  For
user-facing per-channel control, the plugin exposes channel-level
sliders; for automation, the user can use MIDI channel filtering.

### Relationship to existing plugins

- `ReapNES_Studio.jsfx` / `ReapNES_Console.jsfx` / `ReapNES_APU2_v2.jsfx`
  stay in place.  They are the mature line.
- New plugin is `approaches/hardware_semantic/jsfx/ReapNES_HW.jsfx`
  (tentative name).  Parallel, single-track-full-APU, CBG-aware.
- Sync tooling (`scripts/sync_jsfx.py`) extended to cover both lines.

## 8. Practical Roadmap

### Phase 0 -- Design frozen (this document)

Deliverable: this `DESIGN.md`, reviewed and accepted.

Oracle:
```python
oracle.log_decision(
    "project_level", "new_approach_adopted",
    rationale="Unified interpretive stack via CBG IR; stems pipeline "
              "remains parallel for YouTube audio",
    outcome="hardware_semantic_stack_phase0_accepted",
)
```

### Phase 1 -- CBG builder + Contra + W&W

Duration: 1-2 sessions.

Build:

- `cbg/schema.py` -- `CBGEvent`, `ChannelState`, `Audibility`,
  `EventType`, `InstrumentBinding` dataclasses
- `cbg/builder.py` -- `frames -> CBG events` (reuses register decode
  from `nsf_to_reaper.py` but emits CBG, not channel dict)
- `cbg/hw_sim.py` -- per-channel state machines:
  - Triangle linear counter live sim (P0 gap 1)
  - Noise length counter (reuse Rule 32)
  - Pulse envelope (HW + SW modes, P0 gap 2)
- `cbg/liveness.py` -- dense per-frame audibility resolution from
  event stream + sim state

Validate on Contra AND W&W (user's two reference games):

- Extract CBG from NSF emulation (no trace needed for first pass --
  trace validation is phase 4)
- Run HW sim, produce liveness array per channel
- Dump liveness transitions; visually compare to expected articulation
- Ear-check: render current stems path vs render from CBG; compare to
  user's ear-notes for W&W title/stages bass articulation

Gates:
- Gate A: register decode trivially matches (same decoder on both sides)
- Gate B: CBG event inventory -- triangle retriggers present, linear
  reload events present, no obvious misclassifications
- Gate C: liveness -- W&W title triangle liveness transitions match
  user's ear-count for the first 30 seconds of the track
- Gate F: user ear-confirm that CBG-derived MIDI, rendered through
  current stems OR current JSFX, fixes the ringing-over-and-dropping-out
  both directions

Oracle (each per game):
```python
aid = oracle.record_attempt(
    "wizards_and_warriors", "cbg_phase1",
    hypothesis="Triangle linear counter live sim in middle layer "
               "fixes both ring-over and drop-out cases",
    planned_change="Port tri_linear_live simulation up from stem "
                   "renderer into CBG builder; derive liveness from it",
)
# after run:
oracle.record_outcome(aid, "success",
    evidence_refs=["approaches/hardware_semantic/out/ww_cbg_v1/"],
    lessons="Same simulation, applied at middle layer instead of "
            "render layer, dissolves the note_boundary_map workaround")
oracle.propose_claim("wizards_and_warriors",
    "title-screen triangle uses TriangleStaccato template with "
    "reload_value=15",
    evidence=[...])
```

### Phase 2 -- CBG -> MIDI projector

Duration: 1 session.

Build:
- `projection/cbg_to_midi.py` -- CBG + liveness -> MIDI with
  driver-aware note boundaries
- `projection/cbg_to_sysex.py` -- CBG -> archival SysEx blob

Validate:
- Existing stems pipeline consumes the new MIDI; Gate E spectral diff
  vs libgme
- Gate F: user ear-test Contra + W&W

### Phase 3 -- New JSFX prototype

Duration: 2-3 sessions.

Build `approaches/hardware_semantic/jsfx/ReapNES_HW.jsfx`:
- Per-channel HW state machines (port from `cbg/hw_sim.py`)
- Triangle linear counter live sim (already in APU2_v2; adapt)
- Non-linear DAC per-channel (Rule 27)
- 4-pole LP, DC block (Rule 33)
- Bandlimited pulse (Rule 35)
- Triangle hold on gate-off (Rule 34)
- Single-track full-APU MIDI routing
- BehaviorTemplate library (initial: `OpaqueReplay`, `TriangleStaccato`,
  `TriangleSustained`)

Validate:
- Gate A: plugin internal state after MIDI input matches CBG-derived
  expected state
- Gate E: plugin output spectrally matches libgme for Contra + W&W
- Gate F: user ear-test in REAPER with single-track full-APU project

### Phase 4 -- Driver-family coverage + trace validation

Duration: 3-4 sessions.

- Extend CBG + hw_sim for Families 1-4
- Add `BehaviorTemplate` library entries: `HWEnvelopeDecay`,
  `SWLinearFade`, `DutyAlternator`, `LFSRDrumBurst`,
  `SunsoftDPCMBass`
- Template identification step in CBG builder: fit event patterns to
  templates, choose best fit
- Add trace-based Gate B/C/D validation: Mesen trace -> CBG -> compare
  to NSF-derived CBG; any divergence classifies NSF trust level
- Extend regression set to: Castlevania 1, Battletoads s1, Metroid,
  Mega Man 2, Sunsoft (Batman), SMB overworld

Oracle updates:
- `log_decision` per game for extraction_route
- `propose_claim` for each game's template bundle
- Update `driver_families` table with template fingerprints
- `prevention_patterns` for any new failure mode uncovered

### Phase 5 -- Close P1 gaps

- const_vol / HW envelope distinguishing heuristic (already scheduled
  for Phase 1 P0 gap 2; refined here)
- Sweep unit applied to pitch (Sunsoft)
- Length counter for pulse / triangle where applicable

### Phase 6 -- P2 gaps

- DPCM sample-ID classification (ROM-aware; ties into BehaviorTemplate
  `SunsoftDPCMBass`, `BattletoadsDrum`)
- Frame counter mode ($4017 bit 7)

### Phase 7 -- Expansion chips

- VRC6 (already partially done in current pipeline -- integrate)
- FDS modulator
- VRC7 FM
- 5B envelope

### Phase 8 -- Institutionalize

- Oracle: `prevention_patterns` for every failure mode closed
- Rule files: CBG elevated to first-class project concept in
  `CLAUDE.md` and `.claude/rules/architecture.md`
- Tools: CBG inspection CLI, CBG diff viewer
- Regression harness automated on full reference set
- MISTAKEBAKED.md entries for every 2+ prompt learning

### Knowledge-hardening discipline per phase

Every phase MUST produce, before completion:

1. Code (builder / sim / projector / plugin as applicable)
2. Rule or reference doc update (CBG IR spec, liveness rules, template
   library doc)
3. Oracle records (decisions, claims, prevention patterns, evidence)
4. `MISTAKEBAKED.md` entries for anything costing 2+ prompts

Non-negotiable per `CLAUDE.md` Knowledge Hardening section.

## Appendix A -- Target file layout

```
approaches/hardware_semantic/
|-- README.md                       # entry-point overview
|-- DESIGN.md                       # this document
|-- IR_SPEC.md                      # formal CBG schema (Phase 1 deliverable)
|-- ROADMAP.md                      # live phase/gate tracker (Phase 1+)
|-- cbg/
|   |-- __init__.py
|   |-- schema.py                   # CBGEvent, ChannelState, enums
|   |-- builder.py                  # frames -> CBG events
|   |-- hw_sim.py                   # per-channel HW state machines
|   |-- liveness.py                 # per-frame audibility resolution
|   +-- templates.py                # BehaviorTemplate library
|-- projection/
|   |-- cbg_to_midi.py
|   |-- cbg_to_sysex.py
|   +-- cbg_to_stems.py             # parallel stems path for validation
|-- jsfx/
|   |-- ReapNES_HW.jsfx
|   +-- sync.py                     # sync to REAPER Effects folder
|-- validate/
|   |-- gate_b_events.py
|   |-- gate_c_liveness.py
|   |-- gate_d_articulation.py
|   +-- reference_games.py          # Contra, W&W, SMB, CV1, BT, Metroid, MM2, Batman
+-- notes/
    |-- const_vol_vs_hw_env.md      # working doc for P0 gap 2
    |-- sweep_unit_usage.md
    |-- triangle_liveness_ww.md     # W&W-specific analysis
    +-- template_signatures.md
```

## Appendix B -- What this approach is NOT

- Not a replacement for the stems pipeline.  Stems remain canonical
  audio for YouTube / MP4 rendering (Rule 31).  This approach's audio
  output is for editable / playable REAPER projects.
- Not a fork of existing JSFX.  `ReapNES_APU2_v2` and `ReapNES_Studio`
  stay in place.  This approach builds a new plugin with a different
  architectural contract (single-track full-APU, CBG-aware).
- Not a fix for known bugs in the current extractor.  Current
  `frames_to_channel_data` continues to serve the stems path.  The new
  CBG builder is parallel, not replacement, until it demonstrably
  matches or exceeds.
- Not an excuse to skip planning.  Each phase has gates.  Gates must
  pass before the next phase begins.  Oracle records are mandatory.

## Appendix C -- Success criteria

The approach is considered successful when:

1. **W&W title + early stage bass** plays as articulated discrete notes
   in a single-track RPP using the new JSFX, matching user's ear-test
   expectations in both ring-over and drop-out directions.
2. **Contra bass** plays as discrete notes (not one drone), audio
   matches libgme spectrally, user ear-confirms.
3. **CBG gates B-D** can identify a liveness or articulation bug
   *before* audio rendering, isolating interpretation bugs from
   synthesis bugs.
4. **Round-trip** works: a user imports an NSF, gets a REAPER project,
   edits a pitch, plays a MIDI keyboard into the same plugin, and
   hears hardware-faithful output.
5. **Driver family classification** automatically selects the right
   behavior templates on import, without per-game manual overrides.
6. **Discoveries land in oracle + rule files** before each session
   ends, per the Knowledge Hardening protocol.
