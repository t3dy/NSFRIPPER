# JSFX live-play priority list

Minimum work in `studio/jsfx/ReapNES_APU2_v2.jsfx` to realize the
Performance Abstraction Layer's Class A + Class B dimensions.

Based on code inspection of current JSFX (at 2026-04-19) and gap
analysis against `docs/PERFORMANCE_ABSTRACTION_LAYER.md`.  Order is
implementation priority; each item's "why" is the PAL dimension it
unlocks.

## Perceptual priority of the 17 PAL dimensions

Ranked by **audible impact if the dimension is missing from live
play**.  Used to justify the ordering of the work tiers below.
Distinct from implementation cost; implementation order within a
tier still favors cheap wins.

Label key: `[impl]` = currently supported at exact/approximate.
`[preset]` = covered via Class C preset.  `[hyp]` = coverage is
hypothesis pending ear-test.  `[gap]` = not implemented; target
for this roadmap.  `[N/A]` = Class D, correctly non-performable.

### Tier 1 — "without this, no recognisable performance"

1. **#1 Note pitch** `[impl]` — trivially essential.
2. **#2 Note timing** `[impl]` — trivially essential.
3. **#3 Volume amplitude** `[impl, approximate]` — velocity covers
   the note-level; flat volume sounds lifeless.
4. **#7 Envelope decay shape** `[preset]` — differentiates sparse
   (Family 1: MM, DuckTales) from active (Family 2: Contra,
   Ninja Gaiden) families.  Carried by preset; live-tweakable via
   CC74 (see Should-do).

### Tier 2 — "without this, sounds non-NES"

5. **#6 Attack transient / phase reset** `[impl, approximate]` —
   gives the pulse its "bite"; velocity-coupling is Must-do #1.
6. **#4 Duty cycle static** `[preset]` — 12.5% vs 25% vs 50% is
   a dramatic timbre shift; live CC control is Must-do #2.
7. **#13 Noise mode (long/short LFSR)** `[preset]` — noise is
   wrong-flavoured without correct LFSR mode.  Preset coverage
   suffices for most live use.

### Tier 3 — "without this, sounds like a generic synth"

8. **#5 Duty animation** `[gap]` — driver-signature motion (SMB3,
   Rare).  Macro target, Should-do #6.
9. **#10 Vibrato** `[gap]` — expressive shiver; aftertouch wiring
   is Must-do #3.
10. **#11 Arpeggio / chord illusion** `[gap]` — distinctive NES
    chord sound.  Macro target, Should-do #5.
11. **#14 Noise length-counter silencing** `[gap]` — drum
    articulation.  Macro target, Later #10.

### Tier 4 — "specialist / song-specific"

12. **#9 Sweep unit** `[gap]` — Sunsoft signature (Blaster Master,
    Batman); rare elsewhere.  Later #9.
13. **#8 Envelope release** `[preset]` — staccato clarity; preset
    suffices for most cases.
14. **#12 Noise period (pitch)** `[impl, approximate]` — default
    mapping already works.
15. **#15 DMC sample trigger** `[gap]` — only for sample-heavy
    games (Sunsoft bass, Battletoads drums).  Later #11.

### Tier 5 — non-performable (Class D, `[N/A]`)

16. **#16 DMC DAC direct value** — correctly unsupported.
17. **#17 Frame-accurate register sequencing** — correctly
    unsupported.

### Implications for ordering

- The three Must-do items below each target a Tier 2 or Tier 3
  gap with low code cost — correct prioritisation.
- The "performance macro on CC71" (Should-do #4) is a single
  knob that moves multiple Tier 1-3 dimensions together, which
  justifies its placement ahead of the individual Class B
  macros in Should-do #5-7.
- The Later tier's items all target Tier 4 dimensions — correct
  relegation.
- Tier 5 dimensions are explicitly excluded — see Non-goals.

See `keyboard_lab/docs/MACRO_SYSTEM.md` for the macro
infrastructure that unblocks Should-do #5-7.  The macro scheduler
is a prerequisite once any Should-do item ships; whether to
build the general scheduler first (Later #8) or inline the
first macro (Should-do #6) is an implementation judgment call —
current recommendation: inline `konami_stab` first, generalise
the scheduler if a second macro needs it.

## Must-do now (next JSFX session)

These three items make live play substantially better at low code
cost.

### 1. Wire velocity → attack transient intensity (PAL #6)

**Current state**: slider 20 "Attack Enhancer (2-phase)" exists
with fixed intensity from slider value.  Velocity is received but
not wired to the enhancer.

**Change**: at note_on processing, scale the two-phase attack
boost by `velocity / 127.0`.  Velocity 127 = full slider value;
velocity 32 = quarter intensity.

**Code location**: `ReapNES_APU2_v2.jsfx` around line 515 where
`p1_inc = calc_pulse_inc(note2hz(midi_buf[1]))` is set.

**Effort**: 30 minutes.

**Unlocks**: PAL dim #6 moves from "approximate" to "exact" in DB.

### 2. Wire CC1 (mod wheel) → quantized duty (PAL #4)

**Current state**: duty comes from slider 3 (P1) or slider 9 (P2);
static per preset.  No CC routing.

**Change**: in Priority 3 mode, read CC1 (mod wheel).  Quantize
into 4 bins: 0-31 → duty 0, 32-63 → duty 1, 64-95 → duty 2,
96-127 → duty 3.  Apply only when sx[16]==0 (no SysEx live) and
cc[2]==slider3 (CC12 from file not overriding).

**Code location**: CC handling block in JSFX (around line 250-280
in current file).

**Effort**: 1 hour.

**Unlocks**: PAL dim #4 duty control becomes live-performable.

### 3. Wire aftertouch → vibrato depth (PAL #10)

**Current state**: no aftertouch routing.

**Change**: on channel_pressure message, set a global
`vib_depth_aftertouch` that applies a ±20-cent sine vibrato at
5 Hz to the pulse/triangle period.  Depth scales linearly
with aftertouch 0-127.

**Code location**: add MIDI channel_pressure handler in the MIDI
parsing loop; add a vibrato-add to the period calculation.

**Effort**: 2 hours.

**Unlocks**: PAL dim #10 vibrato becomes live-performable (Class A).

## Should-do next (second session)

These four items close the biggest remaining Class A and Class B gaps.

### 4. Performance macro on CC71 (PAL multi-dim)

**Current state**: no macro subsystem.

**Change**: wire CC71 to a preset-defined macro curve that
coordinates envelope decay, duty animation depth, vibrato depth,
and transient boost.  Each preset ships with a CC71 curve.

**Effort**: 4 hours.

**Unlocks**: the single most important live-play affordance —
"driver energy" knob.

### 5. Arpeggio engine on multi-note hold (PAL #11)

**Current state**: no arpeggio logic.

**Change**: when 2+ notes held, cycle through them at a rate
driven by CC75.  Up, down, or preset-selected pattern.

**Effort**: 6-8 hours.

**Unlocks**: the distinctive NES chord-illusion sound, entirely
Class B.

### 6. Stepped duty animation macro (PAL #5)

**Current state**: duty is static once set.  No macro scheduler.

**Change**: implement the minimum macro scheduler per
`keyboard_lab/docs/MACRO_SYSTEM.md` (single macro `konami_stab`,
MAX_CONCURRENT=1, `set`-blend only, keyswitch trigger).  Fire a
2-3 frame duty-flip sequence on C0 keyswitch, return to preset
duty after natural_end.

**Effort**: 3-4 hours (scheduler + one macro).

**Unlocks**: PAL dim #5 Class B triggerable; unblocks Should-do
#5 (arpeggio) and Later #10 (noise burst) by shipping the
scheduler.

### 7. Phase-reset burst macro (PAL #6 supplement)

**Current state**: phase reset exists in Priority 1 via SysEx.
Not triggerable from a keyswitch in P3.

**Change**: add a keyswitch that forces `p1_phase = 0` + full
transient.

**Effort**: 1 hour.

**Unlocks**: audible re-articulation of held pitches.

## Later / optional

### 8. Keyswitch macro subsystem

All items 4-7 can be hand-coded inline, but a general macro
subsystem (time-scheduled parameter automation from a fired
trigger) unifies them.  Do after items 4-7 prove out.

**Effort**: 1 day.

### 9. Sweep unit proxy on pitch bend (PAL #9)

**Current state**: pitch bend not interpreted.

**Change**: pitch bend modulates the period register directly.
Subtle; coarse approximation of the hardware sweep unit.

**Effort**: 2 hours.

### 10. Noise burst length macro (PAL #14)

**Current state**: noise burst is preset-length.

**Change**: velocity → burst length via length counter.

**Effort**: 2 hours.

### 11. DMC keyswitch samples (PAL #15)

**Current state**: DMC only in Priority 1 SysEx.

**Change**: pre-load 4-8 DPCM samples from a fixed bank; map to
keys.

**Effort**: 4 hours + sample-bank curation.

## Non-goals (explicitly)

- **Full DMC DAC live control** (PAL dim #16 Class D).  Correctly
  unsupported.
- **Frame-accurate register sequencing live** (PAL dim #17 Class D).
  Correctly unsupported.
- **Overhaul of ADSR logic**.  Current is fine as a baseline.
- **VST3 port.**  Not this session.  JSFX stays.

## Effort budget summary

| Tier | Items | Total effort | What it buys |
|------|-------|--------------|--------------|
| Must-do now | 1-3 | ~3.5 hours | Live-feel makeover; Class A fully lit |
| Should-do | 4-7 | ~15 hours | Macro subsystem; Class B partly lit |
| Later | 8-11 | ~1-2 days | Completion; Class B fully lit |

Must-do (3.5 hours) is the minimum to meaningfully improve live
play.  Should-do (~2 days of focused work) makes the live path
feature-complete.  Later is polish.

## Validation loop

After each shipped item:

1. Load `outputv6_B/Castlevania/reaper/02_Song_02.rpp`.
2. Play with a MIDI keyboard.
3. Update the `approach_capabilities` row in keyboard_lab DB for
   that PAL dimension, setting coverage and verified_date.
4. Record qualitative note in `findings`.

If the ear-test fails (the change sounds worse than before),
revert the change.  Don't ship unvalidated DSP.

## Coordination with archival path

Per Rule 31 + PERFORMANCE_ABSTRACTION_LAYER.md: archival (stems)
path remains authoritative for fidelity.  None of the JSFX
changes above affect Priority 1 SysEx replay; they all live in
Priority 3.  Stems-based renders continue to use Python DSP.

This means JSFX live can diverge in sound from stems (acknowledged
in the PAL doc's "non-performable" section) without breaking the
fidelity claim of the archival path.
