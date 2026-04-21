# Keyboard-pop A/B test -- ReapNES_HW plugin

Two REAPER projects, same MIDI, same instrument profile, **only
the JSFX plugin differs**:

- `old_apu2v2.rpp` -- loads `ReapNES Studio/ReapNES_APU2.jsfx` (the mainline plugin)
- `new_hw.rpp`     -- loads `ReapNES Studio/ReapNES_HW.jsfx` (hardware_semantic copy with three fixes applied)

MIDI: `fugue1_C_major_ww_cc.mid` (copied into this folder).

## What changed in ReapNES_HW.jsfx (three fixes)

**Fix 1: Attack Enhancer off (via slider preset).**  The plugin's
`slider20` (Attack Enhancer) defaults to 0.4, firing a velocity-
scaled transient burst of up to 6 NES vol units over ~20 ms on
every pulse note_on.  Designed as a 'tink' for CC11-quantized game
MIDIs; for live play / Bach (no CC11 automation) it's a pop per
note.  All hardware_semantic RPPs now set it to 0.  Plugin header
itself says: 'Set to 0 for pure hardware fidelity.'

**Fix 2: Rule 34 triangle hold on gate-off** (in JSFX code).  The
triangle output path has three branches (one per input-priority
mode).  All three now hold the DAC value when the gate closes:

| Branch | Old (`APU2_v2`) | New (`HW`) |
|---|---|---|
| SysEx (priority 1) | `tri_out = tt[...]`  (hold) | same -- already correct |
| CC (priority 2)    | `tri_out = 0`        (pop)  | `tri_out = tt[...]`  (hold) |
| ADSR (priority 3)  | `tri_out = 0`        (pop, two spots) | `tri_out = tt[...]`  (hold) |

`tt[...]` is the triangle-wave lookup table evaluated at the
CURRENT phase, so the DAC sits at whatever step the sequencer was
paused on.  Matches real NES hardware behavior per NESdev wiki.

**Fix 3: Rule 33 LP + DC blocker at output** (in JSFX code).  This
is the main fix for on-hit / on-release pops: when `p1_en` flips
from 0 to 1 on note_on, `out` jumps from 0 to approximately +/-0.5
in a single sample.  That's broadband energy -> audible click.

New output chain: channel mix -> HP440 (existing) -> **2-pole
Butterworth LP at 14 kHz** -> **1-pole HP at 10 Hz (DC blocker)**
-> output.  Same design as `scripts/render_channel_stems.py`
`apply_nes_analog_lp()` + `dc_block()`.  The LP spreads 1-sample
steps across ~4 samples (~90 us), well below the ear's click
threshold.  The HP removes any DC offset from stuck triangle holds
or duty-asymmetric pulse averages.

## What to listen for

1. **Note-on / note-off clicks.** Play the MIDI, play single
   keyboard notes.  Old: pop per note on hit and release.  New:
   smooth attack, smooth release.  The LP filter is doing most
   of this work.
2. **Triangle note-off specifically.** With Rule 34 hold, triangle
   notes should decay into silence rather than step to zero.
3. **High-pitched pulse timbre.** The 14 kHz LP takes edge off the
   pulse-edge aliasing grit that Rule 35 would fully solve.  If
   bright pulse notes still sound wrong (hissy / gritty rather
   than clicky), Rule 35 is the next port (analytical-integral
   bandlimited pulse synthesis).
4. **Nothing else should sound different.**  Game stems in other
   projects continue to use the mainline `ReapNES_APU2.jsfx` and
   are unchanged by this work.

## Rolling back

If the new plugin sounds wrong, just delete it:

```
rm 'C:\Users\PC\AppData\Roaming\REAPER\Effects\ReapNES Studio\ReapNES_HW.jsfx'
```

REAPER falls back to showing the projects with a missing-plugin
error on `new_hw.rpp` only.  `old_apu2v2.rpp` and every other
existing project is unaffected -- this plugin lives parallel to
APU2_v2, not in place.

## If the fix sounds right

The change in the repo is at
`approaches/hardware_semantic/jsfx/ReapNES_HW.jsfx`.  We can then
choose: keep the new plugin as the hardware-semantic path's
default (design doc Phase 3), or backport the same three-line
change into the mainline `studio/jsfx/ReapNES_APU2_v2.jsfx`.
The second option updates every existing RPP without renaming
plugins.