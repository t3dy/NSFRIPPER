# Macro system (minimal design)

Companion to `docs/PERFORMANCE_ABSTRACTION_LAYER.md`.  Defines the
foundation on which PAL **Class B** dimensions are realized in the
JSFX live path.

A macro is a short, time-scheduled sequence of internal parameter
writes that the synth runs **autonomously** after a performer
gesture triggers it.  Macros are how the single-keyboard performer
reaches behaviors that require per-frame driver-style control
(duty animation, phase-reset bursts, arpeggio cycles, noise-length
silencing, DPCM triggers).

This doc specifies the data model, trigger model, scheduler model,
and the mapping from macros to PAL Class B dimensions.  It is
intentionally minimal — the goal is the smallest load-bearing
design, not a full automation engine.

Status: **design**.  No JSFX implementation yet.  First JSFX macro
item lands in `docs/JSFX_LIVE_PRIORITY.md` Should-do #6 (stepped
duty animation macro).

## Scope

Macros exclusively realize **PAL Class B** dimensions:

- #5 Duty cycle animation (per-frame)
- #9 Sweep unit pitch modulation
- #11 Arpeggio / chord illusion
- #14 Noise length-counter silencing
- #15 DMC sample trigger

Macros do NOT cover Class A (live) or Class C (preset) dimensions.
Class A is directly wired to hand controls; Class C is baked into
the preset.  Macros are the only mechanism for Class B.

Macros DO NOT attempt Class D dimensions.  A macro is a performer-
triggered loop of Class A/C writes; it is not a general-purpose
per-frame register recorder.

## Data model

A macro is a fixed record:

```
macro {
    id                    int           -- stable identifier, 1..N
    name                  text          -- human label, e.g. "konami_stab"
    pal_dim               int           -- which PAL dim # it targets (5, 9, 11, 14, 15)
    duration_frames       int           -- total runtime in 60 Hz frames
    loop                  bool          -- if true, runs until stops_on fires
    stops_on              enum          -- 'natural_end' | 'note_off' | 'retrigger' | 'reset_cc'
    steps                 step[]        -- time-ordered parameter writes
}

step {
    at_frame              int           -- 0-indexed offset from trigger
    target                enum          -- 'duty' | 'vol_add' | 'phase_reset' |
                                        --  'period_add' | 'vibrato_depth' |
                                        --  'length_remaining' | 'dmc_trigger' |
                                        --  'arp_select'
    value                 int           -- target-specific, see §Targets below
    blend                 enum          -- 'set' | 'delta' | 'ramp_to'
}
```

A macro library is a flat list of `macro` records keyed by `id`.
In JSFX this is a fixed-size C-style array, zero-allocated; no
dynamic data structures needed.

Example — "Konami pulse stab" (PAL #5):

```
macro id=1 name="konami_stab" pal_dim=5 duration_frames=4 loop=false
  stops_on=natural_end
  steps:
    {at_frame=0, target=duty, value=1, blend=set}   -- 25%
    {at_frame=1, target=duty, value=2, blend=set}   -- 50%
    {at_frame=2, target=duty, value=1, blend=set}   -- 25% again
    -- at frame 4, natural_end: return to preset duty
```

Example — "Arp up 3-note" (PAL #11):

```
macro id=3 name="arp_up_3" pal_dim=11 duration_frames=0 loop=true
  stops_on=note_off
  steps:
    {at_frame=0, target=arp_select, value=0, blend=set}   -- voice 0
    {at_frame=1, target=arp_select, value=1, blend=set}   -- voice 1
    {at_frame=2, target=arp_select, value=2, blend=set}   -- voice 2
  -- loop repeats; rate modulated by CC75 (see §Trigger model)
```

## Trigger model

A macro fires in response to **exactly one** performer gesture.
Three trigger types cover every Class B use case:

1. **Keyswitch trigger** — note_on at a specific pitch in a
   reserved keyboard range (C0-B0, MIDI 12-23).  Velocity is
   passed to the macro as a scalar `trigger_velocity ∈ [0, 1]`
   that individual steps may reference via the `value` field
   (special sentinel `-1 = trigger_velocity * 127`).
2. **Pad trigger** — equivalent to keyswitch but on a controller
   pad bank.  Pads and keyswitches are interchangeable for JSFX
   purposes; the MIDI message is identical (note_on).
3. **CC-crossing trigger** — a CC value crossing a threshold
   (e.g. CC75 moving from 0 to 1 fires the arpeggio macro on).
   Used for toggle-style macros.

Trigger → macro is a **fixed map** shipped with each preset.  The
performer does not design macros live; they select a preset whose
map wires their available triggers to appropriate macros for the
target driver family.

Retriggering a running macro:
- `stops_on='retrigger'`: kill the running instance, start fresh.
- `stops_on='natural_end'`: ignore the retrigger; finish current run.
- `stops_on='note_off'`: treat note_off as stop, note_on as retrigger.

## Scheduler model

Per-channel JSFX instance maintains a fixed-size **active slot
array**:

```
active_slots[MAX_CONCURRENT]   -- MAX_CONCURRENT = 2 per channel
each slot:
    macro_id       int   -- 0 if slot is empty
    elapsed_frame  int
    step_cursor    int   -- index into macro.steps
    trigger_vel    float
```

Each audio frame (1/60 s, not per-sample), for each non-empty
slot:

1. `elapsed_frame += 1`
2. While `steps[step_cursor].at_frame <= elapsed_frame`:
   - apply the step's parameter write (blend mode-dependent)
   - `step_cursor += 1`
   - if `step_cursor >= len(steps)`:
     - if `loop`: reset `elapsed_frame = 0`, `step_cursor = 0`
     - else: clear the slot
3. If `elapsed_frame >= duration_frames` and not loop: clear the slot.

**Concurrency**: `MAX_CONCURRENT = 2` is enough for realistic use
(e.g. duty-anim macro on top of arp macro).  If a 3rd macro fires
and both slots are in use, the oldest is evicted (FIFO).

**Frame quantization**: macros run at 60 Hz (driver native).  This
is per PAL open hypothesis HYP-PAL-4 ("60 Hz quantization is
audibly preferable to smooth").  In JSFX: one macro tick per
`samplesblock` boundary where `samplesblock` covers 1/60 s, or on
every 735-sample boundary at 44100 Hz (`floor(srate/60)`).

**Mid-frame MIDI**: if a trigger arrives mid-frame, macro start is
deferred to the next frame boundary.  This enforces the 60 Hz feel
and keeps the scheduler trivial.

## Targets (step.target enum)

| target | Effect | Blend modes | PAL dim # |
|--------|--------|-------------|-----------|
| `duty` | overrides pulse duty register | set | 5 |
| `vol_add` | adds to envelope output (-15..+15) | set, delta | 5, 14 |
| `phase_reset` | forces `phase = 0` on next sample | set (value ignored) | 6 supplement |
| `period_add` | adds to period register (signed) | set, delta, ramp_to | 9 |
| `vibrato_depth` | sets vibrato LFO depth (cents) | set, ramp_to | 10 supplement |
| `length_remaining` | noise length counter value | set | 14 |
| `dmc_trigger` | fires DPCM sample (value = sample bank idx) | set | 15 |
| `arp_select` | which voice of the held-chord to play | set | 11 |

`blend=ramp_to` interpolates over `duration_frames - at_frame`
remaining frames from current to `value`.  `blend=delta` adds
`value` to the current running target each frame until the macro
ends.  Most steps use `set`.

## Representation in keyboard_lab DB

Add two tables (future work, not in v2 schema yet):

```sql
CREATE TABLE macros (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    pal_dim INTEGER,
    duration_frames INTEGER,
    loop INTEGER,                       -- 0/1
    stops_on TEXT,
    notes TEXT
);

CREATE TABLE macro_steps (
    macro_id INTEGER REFERENCES macros(id),
    at_frame INTEGER,
    target TEXT,
    value INTEGER,
    blend TEXT,
    PRIMARY KEY (macro_id, at_frame, target)
);
```

Presets (existing `presets.slider_json`) gain a `macro_map` field:
mapping from keyswitch pitch / pad index / CC number to a
`macros.id`.  JSFX loads the map on preset change.

**Status**: design only.  Not yet added to `extend_capabilities.py`.
Land alongside the first shipped macro (JSFX Should-do #6).

## Relation to PAL Class B dimensions

| PAL dim # | Class B behavior | Macro(s) | Trigger |
|-----------|------------------|----------|---------|
| 5  | Duty animation | `konami_stab`, `rare_swell`, `nintendo_flat` | keyswitch (C0/D0/E0) |
| 9  | Sweep proxy | `sunsoft_sweep_up`, `sunsoft_sweep_dn` | pitch-bend crossing |
| 11 | Arpeggio | `arp_up_3`, `arp_dn_3`, `arp_random` | CC75 threshold + held chord |
| 14 | Noise burst | `kick_short`, `snare_long`, `hat_tick` | pad trigger (G0/A0) |
| 15 | DMC trigger | `dmc_kick`, `dmc_snare`, `dmc_vox` | pad trigger (separate bank) |

Each preset ships with a subset of these macros bound to the
preset's trigger map.  A Konami preset has `konami_stab` on C0;
a Sunsoft preset has `sunsoft_sweep_up` on pitch-bend-up.  Same
macro-engine underneath, different bindings.

## What this does NOT include (deliberately)

- **General-purpose parameter automation language** (envelopes,
  curves beyond `ramp_to`).  If needed, extend `blend` enum —
  don't build a DSL.
- **Dynamic macro authoring from the performer**.  Macros ship
  with presets.  Performer cannot write a macro live.  Authoring
  happens in keyboard_lab DB or by editing preset JSON.
- **Per-sample parameter writes**.  60 Hz is the contract.
- **Cross-channel coordination** (macro on pulse1 affecting
  triangle).  Each channel's macro scheduler is independent.  If
  coordinated writes are needed, fire the same macro_id on each
  channel's instance via matching keyswitches.
- **Macro recording from file playback**.  Priority 1 SysEx is
  the recording path; macros are the live-play path.  Do not
  attempt to derive macros from SysEx captures in this version.

## Open hypotheses

- HYP-MAC-1: `MAX_CONCURRENT = 2` is enough.  May need to bump
  to 3 if arp + duty-anim + sweep all fire simultaneously.
  Test: enable all three on a preset, ear-test.
- HYP-MAC-2: 60 Hz scheduler feels right vs 30 Hz or smooth-
  continuous.  Same test as PAL HYP-PAL-4.
- HYP-MAC-3: single-slot (MAX_CONCURRENT=1) may be sufficient
  and halves code complexity.  Test: try single-slot on the
  Konami preset and see if anything is missing.

## First implementation target

Per `docs/JSFX_LIVE_PRIORITY.md` Should-do tier, the **first macro
to ship** is `konami_stab` — minimum viable to validate the whole
pipeline (trigger → scheduler → step application → natural_end).
Effort estimate: ~4 hours (includes the scheduler infra, because
nothing of it exists yet).  Once `konami_stab` works, subsequent
macros are ~30 min each.

Validation: load a Konami-family preset, press the C0 keyswitch
while holding a pulse1 note, ear-confirm the 2-frame duty flip
sequence, update DB `approach_capabilities` for PAL dim #5 from
`unsupported` to `approximate` with verified_date.
