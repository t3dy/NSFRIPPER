# Counterpoint in square waves — NES-authentic Bach with no noise

An exploration of what it takes to turn a Bach MIDI (or any
contrapuntal music) into something that sounds like "Bach on a
Nintendo" — without using the noise channel for percussion, because
Bach doesn't need drums.

## The short answer

Bach's three-part inventions map almost perfectly onto the NES
melodic channels:

- **Soprano voice** → pulse 1 (duty 25%, bright)
- **Alto voice** → pulse 2 (duty 50%, warm)
- **Bass voice** → triangle (one octave lower, natural)

The two-part inventions use pulse 1 + pulse 2 (or pulse 1 + triangle).
The four-part fugues need a strategy — NES has only three melodic
channels, so one voice either gets dropped, folded into another, or
rendered via DMC DAC (clean square-wave sample at a held DC level).

The **no-noise requirement** is a blessing, not a loss.  Bach has no
drums; removing the noise channel removes the biggest "chiptune"
giveaway.  What's left sounds like a very clean, slightly-electric
baroque trio.  Closer to a baroque organ with three manuals than to
a video game.

## Why NES is actually well-suited to Bach

Four reasons it works better than you'd expect:

### 1. Timbral clarity matches contrapuntal clarity

Bach's counterpoint depends on the listener following three or four
independent voices simultaneously.  This only works when each voice
has a **distinct, unchanging timbre** so the ear can track it.
Orchestral arrangements of Bach use different instrument families
per voice for exactly this reason.

Duty cycles 1 / 2 / 3 on two pulse channels plus triangle gives the
listener three absolutely distinguishable timbres.  No overlap, no
blend.  The voices never merge into an ambiguous texture.  For
counterpoint this is ideal.

### 2. Triangle bass is a natural Bach bass

The NES triangle is monophonic, sustained, smooth, and one octave
lower than the pulses would be at the same period.  That's exactly
what a Bach basso continuo wants.  No harpsichord struminess to
clash; just a clear rhythmic bass foundation.

### 3. Bach's tempos are slow enough for NES pitch resolution

The NES has 11-bit pitch periods: 2048 distinct pulse pitches across
the audible range.  At slow tempos (Bach presto BWV 831: ~144 BPM;
most Bach ~60-80 BPM), the pitch discretization is inaudible.  Fast
modern music at 180+ BPM exposes the NES pitch grid; Bach doesn't.

### 4. Bach's dynamics are implicit

Bach notated very few dynamic markings.  The NES's 16-level volume
granularity (effectively ~6-7 distinguishable levels at listenable
loudness) isn't the constraint it would be on Romantic music.

## The voice-assignment problem

### Two-part inventions (BWV 772-786)

Two voices.  Direct mapping:
- Upper voice → pulse 1 (duty 25%).
- Lower voice → pulse 2 (duty 50%).

Triangle unused, or optionally doubling the lower voice one octave
down for body.

### Three-part inventions / sinfonias (BWV 787-801)

Perfect fit:
- Soprano → pulse 1.
- Alto → pulse 2.
- Bass → triangle.

This is the "canonical" Bach-on-NES arrangement.  No compromise.

### Four-part fugues (WTC, Art of Fugue, etc.)

NES has 3 melodic channels; 4 voices need a reduction strategy.
Options:

**Option A — Drop a voice.**  Traditional: drop the alto (most often
doubled by other voices anyway).  Clean but reduces counterpoint
density.

**Option B — Fold two voices into one channel.**  When two voices
don't play simultaneously, share a channel.  Works for imitative
passages where voices enter and exit.  Requires per-passage analysis
or a "highest note wins" heuristic.

**Option C — Use DMC as a fourth voice.**  Set DMC to play a
constant DAC value via `$4011` writes.  This produces a very quiet
continuous tone — add on top with CC-driven DAC modulation and you
can get a third pulse-like voice.  Niche but viable.

**Option D — Stagger voices across two renders.**  Render SATB as
two three-voice stems (SAT and ATB), layer in REAPER.  Loses
single-NES authenticity but preserves counterpoint.

### Preludes with dense polyphony (WTC Prelude in C, etc.)

Preludes with arpeggiated figures often spell out harmony across
one voice.  NES-appropriately:
- Arpeggio voice → pulse 1 fast.
- Melody (if present) → pulse 2.
- Pedal → triangle.

## Tone design: NES-authentic Bach patches

### The "Trio Sonata" preset

Three melodic voices in three distinct NES timbres.  Use this for
inventions, sinfonias, three-part fugue subjects.

```
pulse1 (soprano):
  duty: 1 (25%)           -- bright, oboe-like clarity
  attack_ms: 5            -- near-instant but not pop
  decay_ms: 150           -- graceful settle
  sustain: 11             -- out of 15, for presence
  release_ms: 80          -- clean note-off
  phase_reset_on_note: yes -- slight "snap" articulates repeats

pulse2 (alto):
  duty: 2 (50%)           -- warm, woody
  attack_ms: 10
  decay_ms: 200           -- slightly slower settle than soprano
  sustain: 10
  release_ms: 100
  phase_reset_on_note: yes

triangle (bass):
  gate: on                -- no envelope needed; NES triangle has no vol
  -- triangle is an octave lower at same period; transpose +12 in MIDI
  -- so MIDI C4 → actual NES A3 audible
  phase_reset_on_note: no -- triangle phase holds for legato bass
```

### The "Chorale" preset

For Bach's hymn-like textures.  Smoother, less articulated.

```
pulse1: duty 2 (50%), longer attack (30 ms), longer decay (400 ms)
pulse2: duty 2 (50%), same
triangle: bass, soft attack
  -- both pulses on duty 2 for consort-like blend
  -- lose contrapuntal clarity for ensemble warmth
```

### The "Harpsichord" preset

Approximate baroque harpsichord articulation.

```
pulse1: duty 0 (12.5%), short attack (2 ms), fast decay (60 ms), sustain 7
  -- the narrow duty + fast decay gives a plucked-string-like sound
pulse2: duty 0 (12.5%), same
triangle: short decay, emphatic phase reset per note
  -- triangle gives the "buff stop" bass
```

### The "Organ Positiv" preset

Pipe-organ-like sustained voices.

```
pulse1: duty 1 (25%), attack 15 ms, no decay (sustain = volume), release 150 ms
pulse2: duty 2 (50%), same
triangle: always-on, phase held
  -- no decay means indefinite sustain per held MIDI note
  -- triangle rumble for 16' stop feel
```

### The "Expressive fugue" preset

Subtle vibrato + volume shaping per voice for Romantic-leaning
Bach performance.  Less historically accurate but musically rich.

```
pulse1: duty 1, add aftertouch → vibrato 3 cents, mod-wheel → duty morph
pulse2: duty 2, aftertouch → volume swell
triangle: static
```

## The MIDI preparation pipeline

Any Bach MIDI you find online isn't immediately ready for NES.
Five prep steps before rendering:

### Step 1 — Split voices into channels

A typical Bach MIDI has all notes on channel 1.  NES needs:
- Soprano events on MIDI channel 1 (→ pulse 1).
- Alto events on MIDI channel 2 (→ pulse 2).
- Bass events on MIDI channel 3 (→ triangle).

Use REAPER's "Extract MIDI Items" or a Python pre-processor.  For
well-made Bach MIDIs from IMSLP or musescore, voices are usually
already on separate tracks; just re-assign channels.

### Step 2 — Transpose to NES-friendly range

NES pulse range: roughly G1 (20 Hz) to C8 (4 kHz), but practically
the sweet spot is C3-C6.  NES triangle: G0-C6, best use C1-C5.

Bach inventions fit easily.  Fugues sometimes have soprano that
goes above C6 — octave-transpose down on any notes above C7.
Triangle voice may go above its range; octave-down as needed.

### Step 3 — Quantize ornaments carefully

Bach ornaments (trills, mordents, turns) are often notated as
grace notes or as a single note the performer expands.  If the MIDI
expands them, great.  If not, consider:
- Manual expansion per performance style.
- Leave as single notes for simplicity.

NES can render fast ornaments (trills at 8th notes resolution)
cleanly because pitch changes are instant via the period register.

### Step 4 — Apply per-voice CC11/CC12 automation

For authenticity-with-musicality:
- CC11 automation to shape phrases (crescendo entering a
  subject).
- CC12 automation if you want per-phrase duty changes
  (contrast between statement and episode).

Optional: add SysEx for phase-reset on all note-ons (tightens
articulation).

### Step 5 — Strip drums / percussion

If the source MIDI has drums (uncommon for Bach MIDI, common for
"Bach with drum beat" covers): delete all MIDI channel 10 events
and any noise-channel events.  This is the "no noise" requirement
from your question.

## What to NOT do

- **Don't use duty 3 (75%)** — it sounds nearly identical to duty
  1 (12.5%) acoustically (phase-inverted square wave).  Waste of
  a voice.
- **Don't add noise for "drum" effects on Bach.**  The whole point
  is no-noise Bach.  Noise belongs in game music, not counterpoint.
- **Don't use pitch bend on melodic voices.**  Bach's counterpoint
  depends on clean note boundaries.  Pitch bend blurs them.
- **Don't use sweep** unit modulation — too aggressive for Bach's
  stable pitches.
- **Don't apply the NES analog LP** (Rule 33) if you want the
  synth to sound "cleaner" than real NES.  Bach on pure unfiltered
  square waves sounds glassily precise; Bach on LP-filtered
  squares sounds a bit muffled.  Try both; pick by ear.

## Full pipeline from Bach MIDI to NES-authentic rendering

```
source.mid                         -- IMSLP-downloaded Bach MIDI
  ↓
[split voices into MIDI channels 1, 2, 3]
  ↓
[transpose to NES range]
  ↓
[apply CC11/CC12 automation if desired]
  ↓
[pick a preset: Trio Sonata / Chorale / Harpsichord / Organ Positiv]
  ↓
load into outputv6_B/<name>/reaper/*.rpp    -- using variant B template
  ↓
set JSFX channel 1 → pulse1 + preset values
set JSFX channel 2 → pulse2 + preset values
set JSFX channel 3 → triangle + preset values
  ↓
press play — you have Bach on NES
```

For stems version: do the same but render via
`scripts/render_channel_stems.py` after converting the MIDI to
Frame IR — or just render direct from JSFX using a ReaScript
render.

## Example: BWV 772 (Invention No. 1 in C major) rendering plan

BWV 772 is the canonical two-part invention.  Structure:

- Right hand = subject and episodes (pulse 1).
- Left hand = imitation + countersubjects (pulse 2).
- No bass line (two-part).

Preset: **Harpsichord** (appropriate for inventions; Bach taught
the inventions at the keyboard).

Specific tuning:
- Both pulses at duty 0 (12.5%) for pluck.
- Sustain 7 for mid-level presence.
- Decay 60 ms — short; each note has a clear start and stop.
- Phase reset on every note-on — harpsichord-like articulation.

Expected sound: crystalline, glassy, unmistakably "chip" yet
legibly Bach.  Each voice is clearly audible without either
dominating.

## Example: BWV 582 (Passacaglia in C minor) rendering plan

BWV 582 is an organ piece with a strong bass line.  Four-voice
dense polyphony in places.

Mapping:
- Bass (the passacaglia theme) → triangle.
- Upper voices 1-2 → pulse 1 + pulse 2.
- 4th voice when present → option B (fold into alto/bass based on
  range).

Preset: **Organ Positiv**.

Specific tuning:
- Triangle bass always on, sustained, phase held.
- Pulse sustains unlimited (sustain = max).
- No release — notes end instantly when gate closes (like pipe
  organ).
- Subtle CC11 dips between passages for breath.

Expected sound: surprisingly close to a small baroque positive
organ.  Triangle provides the 16' bass foundation; two pulses
provide 8' + 4' stops on different ranks.

## What changes if you add DMC

If you DO want to extend beyond 3 voices without using noise, DMC
is your fourth melodic channel.  Two ways to use it:

### DMC as a sustained tone

Set `$4011` to a fixed DC value (~64 = middle DAC).  The DMC
channel produces a constant audible level.  Modulate the DAC
value at MIDI note rate to create a third or fourth pulse-like
voice.

Caveat: DMC tone is extremely thin (1-bit delta PCM).  Sounds
more like telephone-grade squeaking than a musical voice.  Useful
for sustained pedal notes at the bass of large organ pieces; less
useful for melodic counterpoint.

### DMC as a sample player

Pre-render a clean sawtooth or sine as a short DPCM sample.  Play
it back via DMC at different rates for different pitches.  Gets you
a fourth voice with non-square timbre.

Caveat: only 16 rate values → only 16 distinct pitches.  Bach
tonal range exceeds 16 notes; you'd need multiple samples.

## The aesthetic argument

A noise-free NES Bach is a surprisingly beautiful thing.  The
square-wave timbres are cleaner than anything a real harpsichord
produces; the triangle bass is rounder than a pipe organ's 16'
stops; and the three voices never blend — they interlock like
three distinct hands at three distinct keyboards.

The result is *not* "Bach on a Game Boy."  It's closer to Bach on a
small baroque organ built from 8-bit DACs — a sound that shouldn't
exist, but does.

This is a viable artistic direction for the whole project, not just
a technical exercise.  Bach was writing for imagined instruments
he didn't have (the Art of Fugue is explicitly instrument-agnostic).
The NES is a new instrument in the same conceptual space.

## Next step

Pick one of:

1. **BWV 772 (two-part invention)** for the simplest two-voice
   test.
2. **BWV 787 (three-part sinfonia)** for the full trio-sonata
   sound.
3. **BWV 1080/14 (Art of Fugue, final unfinished contrapunctus)**
   for the hardest four-voice case.

Get the MIDI from IMSLP (public domain).  Split into channels per
step 1 above.  Route through `outputv6_B/` style JSFX project with
the **Trio Sonata** preset.  Listen.

If it sounds good, the direction is validated and we can build a
Bach-specific pipeline wrapper.  The `outputv6_bach/` directory
already exists — this workflow would populate it with Bach
renders alongside the game renders.
