# Synth, ROM, and Translate

## Scope

This note explains two things:

1. how NES "instruments" actually work in the games we have meaningfully ripped and studied in this repo
2. how our REAPER plugins translate those game behaviors into playback

This is not a claim that every game in `Projects/` has been equally validated. The games with explicit instrument/playback study in the repo are:

- `Castlevania`
- `Contra`
- `Super Mario Bros`
- `Mega Man 2`
- `Metroid`
- `Battletoads`
- `Wizards & Warriors`

Those games sit at different confidence levels. `Castlevania` and `Contra` are the strongest early validated examples. `Battletoads` and `Wizards & Warriors` drove the newer, more complex playback work. `Mario`, `Mega Man 2`, and `Metroid` are important envelope/playback case studies.

## The Core Idea: NES Instruments Are Not MIDI Instruments

On the NES, an "instrument" is usually not a named preset like "harpsichord" or "bass." It is the result of:

- which APU channel is used
- the timer period written to that channel
- duty cycle for pulse channels
- volume register and envelope behavior
- linear-counter behavior for triangle
- noise period/mode for noise
- driver-side effects such as arpeggios, sweeps, retriggers, table-driven envelopes, and frame-by-frame volume shaping

So when we "translate" NES music into REAPER, we are not doing General MIDI orchestration. We are trying to preserve:

- note timing
- per-frame loudness shape
- pulse timbre changes
- hardware pitch modulation
- channel-specific articulation behavior

That is why the repo has multiple playback layers instead of one simple synth.

## The Shared NES Channel Model

### Pulse 1 and Pulse 2

The pulse channels are the most instrument-like voices in the 2A03. Their identity comes from:

- duty cycle: `12.5%`, `25%`, `50%`, `75%`
- timer period
- envelope or constant-volume behavior
- sweep/arpeggio/modulation imposed by the game driver

In practice, pulse channels usually carry:

- melody
- countermelody
- chords implied by rapid arpeggiation
- bright plucks or stabs

### Triangle

Triangle is not a "volume-programmable synth voice" in the same sense as pulse. It is more constrained:

- fixed 32-step waveform
- no normal volume register
- effective articulation depends on period, enable state, and linear counter / gating behavior

In practice, triangle usually carries:

- bass
- low support
- legato motion
- fast punchy bass in some games

One recurring lesson in this repo is that triangle is easy to over-simplify. Treating it as just "note on while linear > 0" loses important articulation.

### Noise

Noise is its own semantic world. It is not just "drums."

Its identity comes from:

- volume
- short/long LFSR mode
- 4-bit period index
- driver-specific gating patterns

Depending on the game, noise may behave like:

- simple drum hits
- sustained percussion wash
- atmospheric texture
- gated instrument-state alternation

This repo repeatedly learned that noise cannot safely be forced through melodic assumptions.

## How Our Translation Stack Works

There are three practical playback tiers in the repo.

### 1. MIDI Notes + ADSR Approximation

This is the loosest layer and mainly exists for keyboard play or rough playback.

Files:

- [ReapNES_Console.jsfx](/C:/Dev/NSFRIPPER/studio/jsfx/ReapNES_Console.jsfx)
- [ReapNES_APU.jsfx](/C:/Dev/NSFRIPPER/studio/jsfx/ReapNES_APU.jsfx)

Behavior:

- MIDI note on/off carries pitch timing
- ADSR sliders approximate the envelope
- pulse duty can be approximated by slider or CC
- noise uses a drum-note mapping table

Good for:

- live keyboard play
- rough timbral approximation
- games with simpler envelopes

Bad for:

- frame-accurate volume curves
- sweep-heavy tracks
- arpeggio-heavy tracks
- games where envelope shape is the sound

### 2. MIDI Notes + CC11 / CC12 Frame Playback

This is the important "middle layer."

Exporters:

- [nsf_to_reaper.py](/C:/Dev/NSFRIPPER/scripts/nsf_to_reaper.py)
- [trace_to_midi.py](/C:/Dev/NSFRIPPER/scripts/trace_to_midi.py)

Encoding:

- `CC11` = NES volume / expression over time
- `CC12` = pulse duty cycle over time
- note on/off = note boundaries projected from per-frame state

Meaning:

- the MIDI file itself carries the envelope shape
- the synth should replay the envelope instead of inventing one

This is the layer that makes Mario, Castlevania, Contra, Metroid, and Mega Man 2 recognizable, because those games depend heavily on per-frame volume motion.

### 3. SysEx Register Replay

This is the highest-fidelity layer.

Main file:

- [ReapNES_APU2.jsfx](/C:/Dev/NSFRIPPER/studio/jsfx/ReapNES_APU2.jsfx)

Data source:

- `F0 7D 02 ...` write-aware per-frame APU register state
- `F0 7D 03 ...` audible-state sideband

Meaning:

- raw APU channel registers are replayed directly
- write masks preserve same-value rewrites and phase-reset semantics
- extra sideband data carries musical/articulation meaning that raw latch state alone misses

This path exists because MIDI cannot fully express things like:

- sweep-unit pitch motion
- noise mode changes
- exact phase resets on timer-high writes
- some same-pitch retrigger cases
- phrase-local articulation classes like the `Wizards & Warriors` composite bass behavior

## How the Exporters Translate ROM/Trace Data

### NSF Path

Main file:

- [nsf_to_reaper.py](/C:/Dev/NSFRIPPER/scripts/nsf_to_reaper.py)

What it does:

- runs the NSF driver through py65
- captures ordered writes to `$4000-$4017`
- reconstructs per-frame channel state
- emits note events, `CC11`, `CC12`, and optional SysEx

Important translation rules:

- pulse duty comes from `$4000/$4004 >> 6`
- pulse volume/envelope nibble comes from `$4000/$4004 & 0x0F`
- triangle gate is initially inferred from `$4008`
- triangle note pitch comes from `$400A/$400B`
- noise events come from `$400C/$400E`
- note boundaries can be augmented by parser-derived event starts when plain period-change logic would merge notes incorrectly

For `Wizards & Warriors`, this exporter also injects parser-informed same-pitch retriggers and audible-state classes.

### Trace Path

Main file:

- [trace_to_midi.py](/C:/Dev/NSFRIPPER/scripts/trace_to_midi.py)

What it does:

- reads Mesen CSV capture data
- uses decoded APU state rather than guessing from raw writes
- converts trace frames to the same channel-data shape used by the NSF pipeline
- emits MIDI plus optional SysEx-based REAPER playback

Why it matters:

- Mesen trace is ground truth when NSF diverges from gameplay
- it captures real sweep motion, real per-frame volume, and real triangle/noise behavior

This was decisive for `Battletoads` and also important for `Mario` validation.

### REAPER Project Generation

Main file:

- [generate_project.py](/C:/Dev/NSFRIPPER/scripts/generate_project.py)

What it does:

- creates per-channel or full-APU `.rpp` projects
- loads either Console or APU2 synth
- embeds MIDI inline with `HASDATA`
- merges SysEx track into each APU2 item when needed
- applies per-game ADSR defaults for keyboard-play approximation

Known game presets currently exist for:

- `MegaMan`
- `Castlevania`
- `CastlevaniaII`
- `Metroid`

Those presets are convenience approximations, not replacements for frame-accurate `CC11` or SysEx playback.

## The Plugins and What They Mean

### ReapNES_APU.jsfx

File:

- [ReapNES_APU.jsfx](/C:/Dev/NSFRIPPER/studio/jsfx/ReapNES_APU.jsfx)

Role:

- original simpler NES synth
- channel sliders for duty, volume, enable, triangle gate, noise setup
- "live patch" mode for basic NES-style keyboard shaping

Translation philosophy:

- treat NES channels as direct synth voices
- support drum-note mapping for noise
- useful as a legacy or lightweight playback tool

Limit:

- too simple for hardware-accurate reproduction

### ReapNES_Console.jsfx

File:

- [ReapNES_Console.jsfx](/C:/Dev/NSFRIPPER/studio/jsfx/ReapNES_Console.jsfx)

Role:

- more flexible musical/performer-facing synth
- ADSR per channel
- duty sweeps
- optional pulse sweep-unit controls
- noise/drum mapping

Translation philosophy:

- when used for live play, it gives a human-playable approximation of NES channel behavior
- when used for file playback, it should ideally honor exported `CC11/CC12`

Historically important limitation:

- several project logs note that Console playback initially ignored `CC11/CC12`, which meant the file already contained the right envelope shape, but the synth replaced it with generic ADSR

That gap is why so many docs describe "the MIDI is right, the playback still sounds wrong."

### ReapNES_APU2.jsfx

File:

- [ReapNES_APU2.jsfx](/C:/Dev/NSFRIPPER/studio/jsfx/ReapNES_APU2.jsfx)

Role:

- highest-fidelity 2A03 playback path in the repo
- three priority levels:
  - SysEx register replay
  - CC-driven playback
  - ADSR keyboard fallback

Translation philosophy:

- raw register truth first
- file-carried envelope/duty truth second
- human-play approximation only when no file data exists

Important features:

- pulse envelope replay from raw register semantics
- write-aware phase resets
- triangle articulation shaping using audible-state sideband
- noise register replay
- simple console/TV output shaping filters

This is the plugin that exists because some games cannot be translated honestly with note + CC alone.

## Per-Game Instrument Behavior and Translation

## Castlevania

Primary references:

- [PROJECTCASTLEVANIA.md](/C:/Dev/NSFRIPPER/docs/PROJECTCASTLEVANIA.md)
- [WHATWORKEDWITHCONTRAANDCASTLEVANIA.md](/C:/Dev/NSFRIPPER/docs/WHATWORKEDWITHCONTRAANDCASTLEVANIA.md)

What the instruments are doing:

- pulse channels are sharp, percussive, fast-decay voices
- pulse duty changes matter musically and shift timbre mid-phrase
- triangle is sustained bass support
- noise is active, rhythmic percussion with many short hits

Key instrument character:

- Pulse 1 often behaves like a crisp lead/pluck
- Pulse 2 is more timbrally varied and uses more duty switching
- the signature sound is the quick multi-step decay, not long sustain

What our translation does:

- parser emits full-duration notes
- frame IR / export emits the real decay curve through `CC11`
- duty variation is emitted as `CC12`
- Console preset approximates this with:
  - pulse1 `25%` duty, slower attack, low sustain
  - pulse2 `50%` duty, faster decay, very low sustain

Best translation path:

- `CC11/CC12` playback for ordinary use
- APU2 not usually required for the core CV1 lessons

Summary:

- Castlevania taught us that the envelope is the instrument

## Contra

Primary references:

- [PROJECTCONTRA.md](/C:/Dev/NSFRIPPER/docs/PROJECTCONTRA.md)
- [WHATWORKEDWITHCONTRAANDCASTLEVANIA.md](/C:/Dev/NSFRIPPER/docs/WHATWORKEDWITHCONTRAANDCASTLEVANIA.md)

What the instruments are doing:

- pulse voices have huge attack transients and long stepped decays
- velocity range is very wide
- triangle is fast rhythmic bass, not soft legato support
- DPCM/percussion complexity exceeds the plain NSF melodic path in places

Key instrument character:

- the opening pulse hit often behaves like a power-stab: loud transient, then a controlled tail
- triangle is short, active, and tempo-driving
- duty shifts are present but not hyper-dense

What our translation does:

- uses per-frame `CC11` to preserve the dramatic attack drop
- uses `CC12` where duty changes occur
- does not fully solve DPCM through the plain NSF melodic export

Best translation path:

- `CC11/CC12` playback for musical identity
- trace validation was crucial for proving correctness

Summary:

- Contra taught us that "correct notes" are not enough when the attack transient is the whole feel

## Super Mario Bros

Primary references:

- [PROJECTMARIO1.md](/C:/Dev/NSFRIPPER/docs/PROJECTMARIO1.md)
- [MARIODISCOVERIES.md](/C:/Dev/NSFRIPPER/docs/MARIODISCOVERIES.md)

What the instruments are doing:

- both pulse channels use a highly uniform staccato decay
- note duration is surprisingly fixed; perceived articulation comes mostly from envelope
- duty is nearly static
- triangle is more legato bass support
- noise is simple compared with later games

Key instrument character:

- Mario's melody is not "expressive" because of varied ADSR; it is expressive because every note gets the same quick, bright decay
- the sound is tight, standardized, and driver-regular

Important repo finding:

- Mesen capture showed the NSF path had a one-octave pitch problem in that investigation
- the envelope extraction itself was still meaningful; the main pitch bug was elsewhere

What our translation does:

- exports uniform `CC11` decay steps
- keeps duty nearly constant
- triangle remains mostly note/gate based

Best translation path:

- `CC11/CC12` playback is enough if pitch is corrected

Summary:

- Mario taught us that sometimes the right answer is not fancy modeling, just respecting a rigid repetitive envelope law

## Mega Man 2

Primary reference:

- [PROJECTMEGAMAN2.md](/C:/Dev/NSFRIPPER/docs/PROJECTMEGAMAN2.md)

What the instruments are doing:

- pulse 2 is often not "a sustained harmony voice" but an arpeggio engine
- notes can be one frame long
- pulse envelopes are minimal; texture comes from rapid note cycling more than long volume curves
- triangle is short and punchy
- noise is fast and dense

Key instrument character:

- harmony is an illusion generated by note speed
- duty changes contribute to brightness and shimmer
- low-velocity arpeggio notes matter; they cannot be dropped

What our translation does:

- emits huge note counts faithfully rather than collapsing them into chords
- uses `CC11` where available, but Mega Man's sonic identity depends even more on exact note timing
- applies a keyboard preset with brighter duty and short decay for live play

Best translation path:

- note-accurate MIDI + envelope playback
- low latency and accurate note boundaries are critical

Summary:

- Mega Man 2 taught us that the instrument can be "rapid monophonic note churn," not a stable held tone

## Metroid

Primary reference:

- [PROJECTMETROID.md](/C:/Dev/NSFRIPPER/docs/PROJECTMETROID.md)

What the instruments are doing:

- pulse envelopes can breathe, growing and shrinking within one note
- pulse 2 can retrigger decay patterns inside long sustained holds
- triangle is atmospheric support
- noise may be absent in important tracks

Key instrument character:

- Metroid's pulse voice is not a normal ADSR sound at all
- it behaves more like a breathing amplitude contour or cyclical pulse of presence

What our translation does:

- `CC11` carries the real crescendo-decrescendo shape
- ADSR presets only provide a rough atmospheric stand-in for live play

Best translation path:

- `CC11` playback is essential
- ADSR approximation is fundamentally inadequate for the strongest Metroid cases

Summary:

- Metroid taught us that some NES instruments are really time-varying amplitude scripts, not note plus release

## Battletoads

Primary references:

- [README.md](/C:/Dev/NSFRIPPER/README.md)
- [BATTLETOADSBAKETOIDS.md](/C:/Dev/NSFRIPPER/BATTLETOADSBAKETOIDS.md)
- [BATTLETOADSPRETTYGOOD.md](/C:/Dev/NSFRIPPER/BATTLETOADSPRETTYGOOD.md)
- [EXECUTIONSEMANTICSVALIDATION.md](/C:/Dev/NSFRIPPER/EXECUTIONSEMANTICSVALIDATION.md)

What the instruments are doing:

- the Rare driver uses effects that do not collapse cleanly into ordinary note events
- pulse periods wobble frame to frame because of sweep-unit vibrato
- triangle can micro-wobble too
- opening noise can be a continuous environmental texture, not simple drum hits
- arpeggio/sweep behavior changes the heard note without changing the parser's "base note"

Key instrument character:

- the game sound is more animated than the plain NSF output suggests
- the opening atmospheric wash and hardware pitch motion are part of the instrument identity

Critical repo finding:

- NSF was not ground truth for in-game Battletoads audio
- trace path became necessary

What our translation does:

- trace pipeline captures real hardware frame state
- APU2 SysEx replay preserves sweep, phase reset, noise mode, and exact register motion
- plain MIDI/CC path is useful but lower fidelity

Best translation path:

- trace-derived APU2 playback

Summary:

- Battletoads taught us why raw hardware-state replay exists in this repo at all

## Wizards & Warriors

Primary references:

- [CODEXWIZARDSWARRIORS.md](/C:/Dev/NSFRIPPER/CODEXWIZARDSWARRIORS.md)
- [WIZARDSWARRIORS_COMPOSITE_BASS_HANDOVER_2026-04-03.md](/C:/Dev/NSFRIPPER/WIZARDSWARRIORS_COMPOSITE_BASS_HANDOVER_2026-04-03.md)
- [wizards_and_warriors_title_composite_bass_audit.md](/C:/Dev/NSFRIPPER/extraction/analysis/reconciled/wizards_and_warriors_title_composite_bass_audit.md)
- [wizards_and_warriors_title_release_ir_report.md](/C:/Dev/NSFRIPPER/extraction/analysis/reconciled/wizards_and_warriors_title_release_ir_report.md)

What the instruments are doing:

- this game uses a custom driver, not the earlier families
- same-pitch retriggers matter
- triangle articulation is not captured well by simplistic gate logic
- some title-phrase events are best understood as a composite `pulse1 + triangle` instrument
- noise semantics vary by song and are only partially generalized

Key instrument character:

- pulse1 in the title can behave like an envelope-driven pluck voice
- triangle supplies body, but not always a fully renewed bass body
- the user-heard pluck may be composite rather than belonging to one channel alone

Important repo finding:

- the disputed title bass phrase is not "missing triangle"
- it is a composite articulation problem

What our translation does:

- exporter injects parser-boundary same-pitch retriggers
- audible-state SysEx classifies hidden attacks and release/body behavior
- APU2 uses those flags to shape pulse attack and triangle body
- recent tuning moved triangle from static gating toward phrase-local damped/full-body behavior

Best translation path:

- NSF + parser-informed note boundaries + APU2 audible-state sideband

Summary:

- Wizards & Warriors taught us that a musically honest translation sometimes needs a layer above raw registers but below hand-authored orchestration

## What the Game-Specific ADSR Presets Actually Mean

In [generate_project.py](/C:/Dev/NSFRIPPER/scripts/generate_project.py), the game presets are not claiming "this is the real hardware envelope." They mean:

- when a user opens a REAPER project and plays notes live from a keyboard
- and no file-driven `CC11/CC12` or SysEx is present
- use a shape that feels closer to that game's instrument style

So:

- `Castlevania` gets short, biting pulse settings
- `MegaMan` gets bright, fast pulse settings
- `Metroid` gets softer, more atmospheric settings

Those are ergonomic presets, not archival truth.

## The Main Translation Principle We Learned

The repo’s strongest recurring lesson is:

- parser events describe musical intent
- frame/state export describes what the driver actually does over time
- REAPER playback must honor the frame/state layer if we want the result to sound like the game

If we flatten the frame layer into plain held MIDI notes plus generic ADSR:

- Mario loses its crisp identical decay
- Castlevania loses its bite
- Contra loses its impact
- Mega Man 2 loses its shimmer
- Metroid loses its breathing
- Battletoads loses its hardware animation
- Wizards & Warriors loses its composite articulation

## Practical Translation Ladder

If someone asks "which path should I use for a given game?", the current best rule is:

1. Use plain ADSR only for live play or rough sketching.
2. Use `CC11/CC12` playback when the game's identity lives in per-frame envelope and duty shape.
3. Use APU2 SysEx replay when hardware register behavior itself is musically essential.
4. Use trace-derived data when NSF diverges from gameplay.

## Bottom Line

NES instruments in this repo are best understood as channel behaviors plus driver behaviors, not preset names.

Our REAPER plugins translate them at three levels:

- ADSR approximation for playability
- `CC11/CC12` playback for frame-shaped musical realism
- SysEx register replay for hardware-faithful behavior

The games we studied most deeply each forced a different truth into the system:

- `Castlevania`: the decay is the instrument
- `Contra`: the attack transient is the instrument
- `Mario`: the uniform fixed envelope is the instrument
- `Mega Man 2`: the rapid note engine is the instrument
- `Metroid`: the breathing contour is the instrument
- `Battletoads`: the hardware motion is the instrument
- `Wizards & Warriors`: the cross-channel composite articulation is the instrument
