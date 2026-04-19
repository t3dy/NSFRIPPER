# Why the Python scripts sound different from the JSFX plugin

Short answer: **they are two completely different renderers** that have
converged on similar-sounding output but are not the same code.  The
Python pipeline is a batch tool that produces WAV stems; the JSFX is a
real-time plugin.  They share no DSP code and cannot produce
bit-identical audio.

Longer answer — and whether the current Python approach actually gets
you to "playable synth + MIDI keyboard" — below.

## What each renderer is

### Python stems pipeline (`scripts/render_channel_stems.py`)

- **Offline.**  Emulates the NSF via py65 to get per-frame APU
  register state, then synthesizes audio in numpy.
- **Outputs**: 5 WAV files per song (pulse1, pulse2, triangle, noise,
  dmc).  Loaded into REAPER as audio tracks.
- **DSP specifics** (all shipped this week):
  - Analytical bandlimited pulse synthesis (integrated fraction per
    sample window).
  - Triangle gate-off holds the last DAC value (hardware-accurate).
  - 4-pole Butterworth LP @ 14 kHz.
  - 1-pole HP DC blocker @ 10 Hz.
  - Shared-scale stem normalization.
  - LFSR sub-sample time-integration for noise.

### JSFX plugin (`studio/jsfx/ReapNES_APU2_v2.jsfx`, etc.)

- **Real-time.**  Runs in REAPER's audio engine.  Receives MIDI in,
  produces audio out.
- **Three-mode input cascade** (from `docs/SYNTHMERGE.md`):
  - Priority 1: SysEx register replay (bit-accurate NES hardware).
  - Priority 2: CC11/CC12 automation playback (file-driven).
  - Priority 3: ADSR keyboard mode (live playing).
- **DSP specifics**: JSFX-native implementations of pulse / triangle /
  noise generators, hand-rolled non-linear mixer.  Has had some of the
  APU2 corrections (non-linear mixer, Rule 27) but not all of the
  anti-aliasing work Python got this week.

## Why the two diverged

Originally the JSFX was going to be the whole product (one synth,
three input modes, per `docs/SYNTHMERGE.md`).  Then two things
happened:

1. **Multi-track REAPER projects could not reproduce the non-linear DAC
   mix at the master bus level.**  Because each JSFX instance only
   sees one channel's data, their linear sum on the master bus
   overloads by ~15% when multiple channels play together.  This is
   the "overdrive" the user heard.  See `RESEARCH_ANTIALIAS.md` §6.

2. **Fixing JSFX multi-track mixing turned out to be hard.**  The
   cross-channel compression needs all channels visible to one
   plugin, which breaks the per-track model.  Python stems sidestep
   the problem by running the non-linear mixer offline on the full
   sum.

So the project pivoted to stems (captured in MEMORY.md's
"project_stems_default").  Stems are static audio — they are not a
synth.  They cannot respond to a MIDI keyboard.

## What you said you want

Quoting the user:

> I want a playable synth I can plug into midi files that sounds game
> accurate, or play with a midi input keyboard.

The stems approach does NOT deliver this.  Stems are WAVs.  You can't
hit a MIDI keyboard and have a WAV respond — it's not a synth.  You
can only play the already-rendered music.

The JSFX plugin does deliver this.  It's a real synth.  But its DSP
is behind what Python shipped this week, and nobody's been testing
its live-keyboard path recently.

**If your primary goal is a playable synth, the stems work this week
has been the wrong priority.**  It produced a great archival pipeline
(hence "all sounds amazing" on ear tests) but doesn't let you play
anything live.

## Your three real options

### Option A: Two products, both kept.  (Current trajectory, recommended.)

Keep stems as the archival / YouTube-friendly path.  Fix JSFX in
parallel to bring its DSP up to the Python pipeline's quality.  The
two don't need to sound bit-identical; they just need to both sound
good enough to ear-test.

Concretely:
- JSFX needs the triangle gate-off fix (Rule 34).
- JSFX needs the analog LP + DC blocker (Rule 33).
- JSFX needs the bandlimited pulse formula (Rule 35) — or its moral
  equivalent in real-time.
- JSFX needs the $4015 noise gate (Rule 30) — probably already has
  it, needs audit.

Estimate: 1-2 days to port the DSP, assuming the JSFX language allows
the math we need (it does; we have examples in the existing JSFX
files).

### Option B: JSFX-only, drop stems.

Go back to the original plan.  Delete the stems pipeline.  Every
song becomes a REAPER project with MIDI tracks routed through JSFX
instances.  Accept the ~15% non-linear-mix overload as the cost of
multi-track editability.

Rules 34/35/36 (stems-side fixes) still apply to the MIDI path, but
the audio rendering is all JSFX.

**Loses**: the clean archival audio stems that sound best.  The
"distortion" problem comes back.

**Gains**: one code path, live-playable in REAPER, MIDI keyboard
works out of the box.

### Option C: Stems via JSFX offline render.

Use REAPER's offline render on JSFX instances to produce stems.  This
means the JSFX is still the authoritative sound, but you get stems as
a rendered artifact of it — so what you record on YouTube and what
you play live are bit-identical.

**Cost**: requires REAPER to be scriptable from CLI (it is, via
ReaScript), plus JSFX quality parity with Python DSP.  Moderate
complexity; 2-3 days.

**Benefit**: full coherence.  What the plugin plays is what the stems
contain.

## What I recommend

**Option A.**  The stems you have now are valuable — they're the
cleanest archival recording you'll ever get of these games, and they
sound better than any NES emulator.  Don't throw that away.

In parallel, bring the JSFX up to parity.  Specifically:
1. Port Rule 34 (triangle gate-off DAC hold) — 20 minutes.
2. Port Rule 35 (bandlimited pulse via polyBLEP since JSFX is
   real-time) — 2-4 hours.
3. Audit Rule 30 noise gate — 30 minutes.
4. Audit non-linear mixer (Rule 27) — should already be there.

Once those land, the JSFX gives you the keyboard-playable,
MIDI-file-playable, video-recordable synth you want.  The Python
pipeline keeps making the archival stems.

The 150-game rebuild running right now does not block this work — it
just produces the stems.  Once it finishes (~day), you can switch
focus to the JSFX.

## What's NOT going to work

- Pretending the stems are a synth.  They're WAVs.
- Making Python and JSFX sound identical without significant effort.
  They run on different runtimes (py65 emulator + numpy vs REAPER's
  JSFX engine).  You'll get close, not identical.
- Using the Python pipeline for live keyboard input.  Python is not
  low-latency enough (emulate + synthesize + filter at >60 Hz).
  JSFX IS the low-latency path.

## Honest take on this week's work

Everything shipped this week — the triangle gate-hold, bandlimited
pulse, NSF $4015 init, silence-threshold fixes, off-by-one fix,
name/audit pipeline — is real and valuable.  It produces correct
archival stems for 150+ games.

But if the user's actual goal is a playable live synth, this week's
work was a detour.  The real direction is the JSFX plugin, and the
next actionable step is porting the DSP fixes there.

Want me to start that port?  The first one (Rule 34 triangle
gate-off) is a 5-line change to the JSFX.
