# Wizards & Warriors Triangle Reset Handover

## Why This Reset Exists

The current `Wizards & Warriors` title triangle interpretation is still
musically wrong.

User-verified audible contradictions:

- the first short bass note after the longer one is still barely audible
- the bass note durations are still too long
- the current output still misses an important shaping layer, likely envelope /
  retrigger / gate behavior beyond naive note boundaries

Conclusion:

- the current triangle path should be treated as **untrusted**
- do **not** keep patching the existing interpretation forward as if the core
  model were sound
- restart from first principles and re-derive how ROM data produces the
  hardware behavior that produces the heard audio

## Non-Negotiable Rule

When heard output contradicts the current decode:

- reopen the interpretation
- do not defend a local match if the musical macro shape is wrong
- do not promote title-specific hacks into engine truth

## Current State Of The Project

Strongest current results:

- pulse channels for title are in strong shape
- melodic channels across songs `1-16` have strong internal NSF-emulation
  agreement for period paths in the current simulator
- all tracks exist as generated MIDI / RPP artifacts

But for this reset, the important caveat is:

- **triangle articulation is not solved**
- title triangle especially may be overfit

## What Is Actually Known

### Evidence Sources Available

- ROM:
  `C:\Dev\NSFRIPPER\extraction\roms\Wizards & Warriors (U) (V1.0) [!].nes`
- NSF:
  `C:\Dev\NSFRIPPER\state\ww_ref\Wizards & Warriors [Densetsu no Kishi - Elrond] (1987-12)(Rare)(Acclaim).nsf`
- title trace:
  `C:\Dev\NSFRIPPER\extraction\traces\wizards_and_warriors\title_capture.csv`
- MP3 refs:
  `C:\Dev\NSFRIPPER\state\ww_mp3_ref`

### Parser / Driver Facts Worth Keeping

- game-specific parser:
  `C:\Dev\NSFRIPPER\extraction\drivers\other\wizards_and_warriors_parser.py`
- game-specific simulator:
  `C:\Dev\NSFRIPPER\extraction\drivers\other\wizards_and_warriors_simulator.py`
- NSF exporter:
  `C:\Dev\NSFRIPPER\scripts\nsf_to_reaper.py`

Likely valid driver facts:

- NSF load `0x8000`
- NSF init `0xFFC0`
- NSF play `0xEE55`
- command dispatch around `0xEEEE`
- title triangle stream start `0xF1A3`
- `0x07` appears to set persistent duration
- `0x08` appears to cancel persistent duration / return to inline duration

### Title Triangle Structural Sequence

Current parser output for the audible title phrase:

- long run of silent `0x80` entries before music starts
- then at frame `513`:
  - `CMD 04 [129,135,18]`
  - `CMD 07 [32]`
  - note run of `32`-frame notes
- near the disputed phrase:
  - frame `929`: raw `0xA2`, duration `32`
  - frame `961`: `CMD 07 [16]`
  - frame `961`: raw `0xA2`, duration `16`
  - frame `977`: raw `0xA0`, duration `16`
  - frame `993`: raw `0x9E`, duration `16`
  - frame `1009`: raw `0x9D`, duration `16`

This is useful, but still only structural evidence.

### Direct Hardware-State Findings

Direct NSF emulation shows fresh triangle timer writes across the phrase.

Important observed writes:

- frame `513`: `$4008=0x81`, `$400A/$400B` set to first audible period
- then fresh timer writes every `32` frames in the opening run
- later fresh timer writes every `16` frames in the short-note run

Important nuance:

- `$4008` stays latched through much of that phrase
- so the audible note shape is not explained by simple visible changes in the
  captured triangle linear register alone

This suggests there may be another layer of driver semantics or playback
behavior that the current note-level export does not represent well.

## What Was Tried And Why It Is Not Enough

### 1. Title-tail release patch

There is a title-scoped triangle release hack in:

- `C:\Dev\NSFRIPPER\extraction\drivers\other\wizards_and_warriors_simulator.py`

This should now be treated as provisional and suspect.

Reason:

- it may help a narrow tail slice
- but it does not explain the heard phrase shape
- it risks masking true event boundaries

### 2. Same-pitch retrigger export patch

The exporter was updated so a same-pitch triangle event can emit a fresh MIDI
note attack:

- `C:\Dev\NSFRIPPER\scripts\nsf_to_reaper.py`

This was a real bug and fixing it was directionally correct, but it did **not**
solve the audible problem.

Reason:

- the user still hears the first short note as too weak
- overall triangle durations still feel too long
- therefore note boundary splitting alone is not enough

### 3. Simple synth-envelope tweaking

Console / APU2 project tweaking improved some roughness but is not a valid
substitute for decoding the actual driver behavior.

Reason:

- the user explicitly wants hardware-behavior-first decoding
- synth-side guessing should not replace ROM + frame-state interpretation

## Working Diagnosis

The missing layer is likely one of these, ranked roughly by priority:

1. Triangle articulation is controlled by frame-level hardware behavior that is
   not representable as plain MIDI note durations alone.

2. The current export path is still too note-centric and not state-centric.

3. There may need to be an intermediate representation between parsed events
   and MIDI / plugin playback, such as:
   - per-frame channel state IR
   - event + retrigger markers
   - gate / enable / reload actions
   - instrument / articulation envelopes inferred from driver behavior

4. The triangle voice may require a playback path that honors register-replay
   semantics more directly than the current synth usage.

## Design Direction For The Next Attempt

Do not start by fixing the current MIDI note lengths.

Start from this question:

`What exact frame-level hardware behavior produces the heard title bass phrase?`

Then decide the output architecture.

### Strong Candidate Architecture

1. ROM parser layer
- structural events only
- no trust claims

2. Driver semantics layer
- convert structural events into frame-by-frame intended APU actions
- include:
  - duration countdown
  - persistent vs inline duration
  - note reloads
  - gate / enable behavior
  - any channel-specific articulation behavior

3. Frame IR layer
- canonical per-frame state
- not just period
- also:
  - reload markers
  - gate state
  - effective sounding state
  - any inferred articulation class

4. Playback/export layer
- decide whether MIDI alone is enough
- if not, keep MIDI for note view / editing but add a middle layer for the
  plugin to consume

### Middle-Layer Question

Yes, a middle layer is now a serious possibility.

Possible answer:

- MIDI by itself may be too lossy for triangle articulation
- a better system may be:
  - MIDI for coarse musical events
  - per-frame control / SysEx / automation / sidecar state for articulation
  - plugin consumes that richer state to reproduce hardware behavior

Possible forms:

- embedded SysEx register replay
- sidecar JSON / CSV frame-state file
- REAPER automation generated from frame IR
- hybrid: MIDI notes + per-note retrigger metadata + frame overlays

The next window should evaluate this explicitly instead of assuming MIDI alone
is the final truth layer.

## Concrete Tasks For The Next Window

### A. Throw Out False Confidence

- treat current title triangle as unresolved
- do not describe it as solved
- do not rely on the title-tail patch as truth

### B. Reconstruct The Title Triangle From First Principles

- isolate the first audible triangle phrase
- enumerate parser events
- enumerate direct NSF register writes for:
  - `$4008`
  - `$400A`
  - `$400B`
  - `$4015` if meaningful in the capture path
- correlate those writes with audible attacks in the MP3

### C. Use MP3 As Falsification

Use the title MP3 to falsify candidate interpretations on:

- total cue duration
- one longer note then short notes
- first short note stronger onset
- phrase-end decay / stop

If a model misses those, reject it.

### D. Decide The Export Architecture

Explicitly answer:

- can triangle articulation be represented faithfully in plain MIDI notes?
- if no, what middle layer is needed?
- should the APU2 path consume richer frame-state data directly?

### E. Only Then Rebuild Outputs

Once the new semantics model is better:

- regenerate title MIDI
- regenerate REAPER project
- update plugin or plugin-input path if needed

## Files Worth Reading First

- `C:\Dev\NSFRIPPER\CLAUDE.md`
- `C:\Dev\NSFRIPPER\EXECUTIONSEMANTICSVALIDATION.md`
- `C:\Dev\NSFRIPPER\.claude\skills\MUSICFINDER_ORCHESTRATOR.md`
- `C:\Dev\NSFRIPPER\.claude\skills\SIMULATORBUILDER.md`
- `C:\Dev\NSFRIPPER\CODEXWIZARDSWARRIORS.md`
- `C:\Dev\NSFRIPPER\extraction\analysis\reconciled\wizards_and_warriors_title_triangle_mismatch_report.md`

## Current Test Artifacts To Treat As Experiments, Not Truth

- `C:\Dev\NSFRIPPER\Projects\Wizards_and_Warriors\Wizards_&_Warriors_01_Wizards_&_Warriors_Title_triangle_retrigger_v2.rpp`
- `C:\Dev\NSFRIPPER\Projects\Wizards_and_Warriors\Wizards_&_Warriors_01_Wizards_&_Warriors_Title_APU2_triangle_retrigger_v2.rpp`
- `C:\Dev\NSFRIPPER\Projects\Wizards_and_Warriors\midi\Wizards_&_Warriors_01_Wizards_&_Warriors_Title_triangle_retrigger_v2.mid`

These are useful comparison artifacts, but they should not anchor the next
interpretation.
