# Punch You in the Envelope

## The Sunsoft-Style Driver Family: 18 Games That Define the NES Sound

If you close your eyes and think "NES music," you are hearing this family.
Not the sparse bleeps of Dragon Warrior. Not the orchestral density of
Final Fantasy. You are hearing a square wave that hits you in the chest
on the first frame and decays over the next four, like a tiny fist made
of voltage punching you directly in the eardrum. You are hearing
Castlevania. Mega Man 3. Battletoads. The games that made the NES sound
like the NES.

This is the Sunsoft-style family, and this report is going to explain
exactly what these 18 games have in common, why they sound the way they
do, and how to extract their music without losing the punch that makes
them special.

---

## 1. The Family Roster

The Sunsoft-style family is defined by two numbers:

- **CC11 per note: 3.5 to 5.6** (volume changes per note event)
- **CC12 per note: below 0.5** (duty cycle changes per note event)

Translation: these drivers shape every note with a detailed volume
envelope (3-6 APU writes per note), but they pick a duty cycle at the
start and leave it alone. Volume is animated. Timbre is static. That
combination produces the signature punch.

### The Full Roster

| # | Game | Developer | Songs | Notes | CC11/note | CC12/note | Duty | Year |
|---|------|-----------|-------|-------|-----------|-----------|------|------|
| 1 | **Ninja Gaiden III** | Tecmo | 10 | 16,836 | **5.6** | 0.0 | 12.5% | 1991 |
| 2 | **Super Mario Bros v3** | Nintendo (trace) | 3 | 4,187 | 4.9 | 0.0 | 50% | 1985 |
| 3 | **Gargoyle's Quest II** | Capcom | 21 | 22,739 | 4.8 | 0.0 | 25% | 1992 |
| 4 | **Battletoads (Level 1)** | Rare (trace) | 1 | 1,094 | 4.8 | 0.1 | 12.5% | 1991 |
| 5 | **Castlevania APU2** | Konami (trace) | 1 | 814 | 4.5 | 0.1 | 50% | 1986 |
| 6 | **Castlevania** | Konami | 53 | 13,121 | **4.3** | 0.2 | 50% | 1986 |
| 7 | **Battletoads** | Rare | 21 | 17,554 | 4.1 | 0.1 | 25% | 1991 |
| 8 | **Battletoads (trace)** | Rare (trace) | 4 | 3,115 | 3.9 | 0.1 | 12.5% | 1991 |
| 9 | **Battletoads (trace v3)** | Rare (trace) | 1 | 2,331 | 3.8 | 0.0 | 50% | 1991 |
| 10 | **Battletoads (trace v5)** | Rare (trace) | 1 | 2,331 | 3.8 | 0.0 | 50% | 1991 |
| 11 | **Mega Man 3** | Capcom | 57 | 36,803 | **3.7** | 0.1 | 25% | 1990 |
| 12 | **Mega Man 4** | Capcom | 70 | 39,179 | **3.7** | 0.1 | 50% | 1991 |
| 13 | **Battletoads (trace v2)** | Rare (trace) | 1 | 2,059 | 4.7 | 0.1 | 50% | 1991 |
| 14 | **Battletoads (trace v4)** | Rare (trace) | 1 | 2,032 | 4.8 | 0.1 | 50% | 1991 |
| 15 | **Battletoads (trace v6)** | Rare (trace) | 1 | 2,041 | 4.8 | 0.1 | 50% | 1991 |
| 16 | **Battletoads (trace v7)** | Rare (trace) | 1 | 1,907 | 4.8 | 0.1 | 50% | 1991 |
| 17 | **Battletoads (trace v8)** | Rare (trace) | 1 | 885 | 4.7 | 0.1 | 12.5% | 1991 |
| 18 | **Battletoads (trace v9)** | Rare (trace) | 1 | 885 | 4.7 | 0.1 | 12.5% | 1991 |

**Total: 251 songs, 167,962 notes across the family.**

### Wait, Why Is Battletoads Listed Ten Times?

Good question. The survey data contains multiple entries for Battletoads
because the game was captured through different extraction routes:

- **Battletoads** (21 songs, 17,554 notes) — full NSF emulation extraction
- **Battletoads_Level1** (1 song, 1,094 notes) — Mesen trace of Level 1 only
- **Battletoads_trace** through **Battletoads_trace_v9** — iterative trace
  extractions as the parser was refined across sessions

Each trace version represents a different iteration of the Battletoads ROM
parser. Versions v2 through v9 are successive refinements of the same
extraction pipeline, each improving frame alignment, duration accuracy, or
envelope fidelity. They are not different songs — they are different *attempts
to perfectly capture the same songs*.

The fact that every single Battletoads trace version lands in the same family
(CC11/note between 3.8 and 4.8, CC12/note at 0.0-0.1) is actually a strong
validation signal. No matter how the extraction was done — NSF emulation or
Mesen trace, parser v2 or parser v9 — the driver fingerprint stays consistent.
The engine is what it is.

**Deduplicated, the family contains 7 unique games:**

| Game | Developer | CC11/note | The Sound |
|------|-----------|-----------|-----------|
| Ninja Gaiden III | Tecmo | 5.6 | Razor-sharp, fastest envelopes in the family |
| Gargoyle's Quest II | Capcom | 4.8 | Dark, precise, late-era Capcom polish |
| Castlevania | Konami | 4.3 | THE benchmark. Gothic punch. |
| Battletoads | Rare | 4.1 | Aggressive funk. Bass that hits like a truck. |
| Super Mario Bros v3 | Nintendo | 4.9 | Trace version. Classic pluck. |
| Mega Man 3 | Capcom | 3.7 | Bright, heroic, entry-level envelope |
| Mega Man 4 | Capcom | 3.7 | Same engine as MM3, slightly softer |

---

## 2. What the Driver Does (Technical)

### The Envelope Lookup Table: A Tiny Drum Machine for Every Note

The defining technical feature of this family is the **volume envelope
lookup table**. Here is how it works, step by step:

1. The sound driver triggers a note (writes a new period to the APU).
2. Simultaneously, it loads a pointer to a **volume envelope table** in ROM.
3. On each subsequent frame (~60fps on NTSC), the driver reads the next
   byte from the envelope table and writes it to the APU volume register.
4. When the table ends (or the note ends), the driver stops updating volume.

That is it. That is the whole trick. But the consequences are enormous.

A typical envelope table for a Castlevania pulse channel looks like this
in terms of NES volume levels (0-15):

```
Frame 0:  15  (ATTACK — full volume, instant)
Frame 1:  12  (rapid decay begins)
Frame 2:   9
Frame 3:   6  (sustain level reached)
Frame 4:   4  (slight continued decay)
```

Five frames. Five volume writes. That is why the CC11/note ratio lands
around 4-5 for this family: each note gets roughly one volume update per
frame for the duration of its attack-decay envelope.

### Why Duty Stays Static

The other half of the family signature is the nearly-zero CC12 activity.
These drivers set the duty cycle (waveform shape) once per note — or
often once per *song* — and then never touch it again.

Why? Because the NES APU duty cycle register ($4000/$4004 bits 6-7) shares
a byte with the volume register. On the NES, you write duty and volume
together in a single register write:

```
$4000: DDLC VVVV
        |||| ||||
        |||| ++++-- Volume (0-15)
        |||+------- Constant volume flag
        ||+-------- Length counter halt
        ++--------- Duty cycle (0-3)
```

When a Sunsoft-style driver writes per-frame volume, it COULD change duty
at the same time for free — the bits are right there. But these drivers
choose not to. They set D bits once and then only vary V bits.

This is a deliberate design choice. The envelope table contains volume
values, not duty+volume pairs. The table is smaller (one nibble per frame
instead of a full byte), the code is simpler, and the sound is *consistent*.
You know what a Castlevania pulse sounds like: it sounds like 50% duty
with a sharp attack. Always. Every note. That consistency IS the identity
of the game's sound.

Compare this to the Capcom Duty Switcher family (Castlevania 3, Kirby's
Adventure), where CC12/note climbs to 0.7-1.0. Those drivers DO change
duty mid-note, creating a shimmering quality. The Sunsoft-style family
trades that shimmer for raw, uncompromising punch.

### The Per-Frame Volume Pipeline

Here is what happens on every single frame (every 16.67ms on NTSC)
inside a Sunsoft-style driver:

```
1. Is a note currently sounding?
   No  -> write volume 0, done
   Yes -> continue

2. Read envelope_table[envelope_index]
   -> Write to APU volume register (preserving duty bits)
   -> Increment envelope_index

3. Has envelope_index reached table end?
   Yes -> Hold last value (sustain) OR decay to 0
   No  -> Next frame will read next table entry

4. Has note duration expired?
   Yes -> Start next note (or rest). Reset envelope_index to 0.
   No  -> Wait for next frame.
```

The key insight: **volume automation IS the note's character.** In a
minimal driver (Dragon Warrior, Mega Man 1), a note is a pitch at a
fixed volume. In a Sunsoft-style driver, a note is a pitch with a
*sculpted amplitude contour*. The contour is what you hear. The contour
is what makes Vampire Killer sound different from Bloody Tears even
though both songs use the same NES hardware.

### Volume Levels in Practice

The NES APU has 16 volume levels (0-15). That is not a lot. But 16
levels over a 4-5 frame envelope is enough to create sharp attacks
and musical decays. Here is what typical envelope shapes look like:

```
CASTLEVANIA "PUNCH" ENVELOPE (pulse lead):
Frame:  0    1    2    3    4
Vol:   15   11    8    5    4
       ####
       ###
       ##
       #
       #
       Sharp attack, fast 4-frame decay to sustain

MEGA MAN 3 "HEROIC" ENVELOPE (pulse lead):
Frame:  0    1    2    3
Vol:   15   13   10    8
       ####
       ####
       ###
       ##
       Slightly softer attack, 3-frame decay, higher sustain

BATTLETOADS "FUNK" ENVELOPE (bass pulse):
Frame:  0    1    2    3    4    5
Vol:   15   15   12    9    6    3
       ####
       ####
       ###
       ##
       #
       #
       2-frame hold at max, then steady ramp down
```

These are approximations — real games vary by channel and by song.
But the pattern is universal across the family: **instant attack to
max, rapid multi-frame decay, low sustain or silence.**

---

## 3. What It Sounds Like

### The Punch

Close your eyes. Press Start on Castlevania.

The first pulse channel note of Vampire Killer hits at NES volume 15 —
full power, no ramp-up, no fade-in. Within four frames (67 milliseconds)
it has dropped to volume 4. Your ear registers this as a *transient*: a
sharp percussive attack followed by a ringing sustain. It sounds like
someone plucking a very aggressive guitar string made of electricity.

That is the punch. Every note in this family has it. The attack is
always instantaneous (frame 0 = max volume), and the decay is always
fast enough to be perceived as part of the attack transient rather than
a slow fade. The result is a sound that is inherently rhythmic even
when playing melodic lines.

### The Aggression

Minimal drivers (Family 1) sound *clean*. Notes are pure tones at steady
volumes. Pleasant. Polite.

Sunsoft-style drivers sound *aggressive*. Every note announces itself.
The rapid volume decay creates an implicit accent on every single note
onset, which makes even legato passages sound punchy. When the melody
goes fast — and NES melodies go fast — the punch stacks up into a
relentless rhythmic drive.

This is why Castlevania, Mega Man, and Battletoads *feel* more intense
than their contemporaries. The music does not play — it attacks.

### The Warmth (Hidden)

Here is something that surprises people: this family is actually warmer
than you would expect. The reason is the sustained duty cycle. Because
duty never changes mid-note, the harmonic content of each note is
constant. A 50% duty square wave is a pure, warm, hollow tone (only odd
harmonics). A 25% duty wave is brighter and buzzier. Either way, the
timbre stays locked for the entire note duration.

Compare this to the Duty Switcher family, where timbre shifts mid-note,
creating a more complex and sometimes harsher sound. The Sunsoft-style
family has a paradoxical character: the volume is aggressive but the
timbre is stable. Punchy AND warm. That is why it is so listenable for
extended play sessions.

### The Three Signature Sounds

**The Castlevania Lead:** 50% duty, 4-frame decay. Gothic and heroic.
Every note rings like a bell in a cursed cathedral.

**The Mega Man Power Chord:** 25% duty, 3-frame decay. Brighter and
more metallic. Notes cut through the mix like a robot arm through a
steel door.

**The Battletoads Funk Bass:** Triangle channel with tight gating,
pulse channels with held attacks. Rare's engine gives bass notes a
slightly longer sustain before the decay kicks in, creating a groove
that is more funky than aggressive. Battletoads sounds less like a
horror game and more like a dance club run by amphibians.

---

## 4. How to Recognize It

### The CC11 Fingerprint

When you run `driver_survey.py` on a new game, here is what to look for:

| Metric | Sunsoft-style value | Not Sunsoft-style |
|--------|--------------------|--------------------|
| CC11/note | 3.5 - 5.6 | Below 3.0 = minimal, above 6.0 = dense |
| CC12/note | 0.0 - 0.2 | Above 0.5 = duty switching |
| Dominant duty | One clear winner | Even distribution |
| Noise channel | Present | (either way) |

The most important diagnostic is the **CC11-to-CC12 ratio**. In this family,
it is always at least 20:1 and often 50:1 or higher. The driver cares
enormously about volume and barely at all about duty.

### The Envelope Shape Test

If you plot CC11 values over time for a single note, a Sunsoft-style
game looks like this:

```
Volume
15 |X
   |
12 | X
   |
 9 |  X
   |
 6 |   X
   |
 3 |    X X X X X X X X (sustain or silence)
   |
 0 +--+--+--+--+--+--+--+---> Frames
   0  1  2  3  4  5  6  7
```

A minimal driver looks like this:

```
Volume
15 |X X X X X X X X X X X X (constant)
   |
 0 +--+--+--+--+--+--+--+---> Frames
```

A dense automator looks like this:

```
Volume
15 |X
12 | X
 9 |  X
 6 |   X
 9 |    X
12 |     X   (tremolo or re-attack)
 9 |      X
 6 |       X
 3 |        X
 0 +--+--+--+--+--+--+--+---> Frames
```

The Sunsoft-style shape is monotonically decreasing (or decreasing to a
sustain plateau). The dense automator shape has wiggles, bumps, re-attacks.
The minimal shape is a flat line. One glance at the volume contour tells
you which family you are dealing with.

### The NSF Address Hint

Several Sunsoft-style games share the Capcom late-era init/play pattern:

```
Init = $8003, Play = $8000
```

This pattern appears in Mega Man 3, Mega Man 4, Gargoyle's Quest II,
and several other Capcom titles. If you see this address pair in the
NSF header, there is a good chance you are dealing with a Sunsoft-style
or Capcom engine that uses envelope lookup tables.

Castlevania uses `Init=$BB09, Play=$838A` (Konami's own engine), and
Battletoads uses `Init=$8054, Play=$8865` (Rare's engine). Same family,
different origins.

---

## 5. Extraction Tips

### CC11 Is the Sound. Respect It.

The single most important extraction rule for this family:

**CC11 automation must be played back faithfully. ADSR approximation
will not work.**

Here is why. The ReapNES synth has three input modes:

1. **SysEx register replay** (Priority 1) — raw APU state. Perfect.
2. **CC11/CC12 automation** (Priority 2) — volume/duty from MIDI. Faithful.
3. **ADSR keyboard mode** (Priority 3) — synthetic envelope. Generic.

For Sunsoft-style games, you need Priority 1 or 2. Priority 3 will
produce a generic chiptune sound that lacks the specific envelope
contour of each game. Castlevania ADSR will not sound like Castlevania.
It will sound like "some NES game."

The difference is real and audible:

| Aspect | CC11 playback | ADSR approximation |
|--------|---------------|--------------------|
| Attack | Instant (frame 0 = max) | Configurable ramp (never instant enough) |
| Decay shape | Game-specific table (4.3 CC/note) | Exponential curve (generic) |
| Per-note variation | Each note can have a different table | All notes use same ADSR |
| Sustain level | Table-determined, varies by instrument | Fixed parameter |
| Identity | Sounds like Castlevania | Sounds like "a synth" |

### ReapNES Settings for This Family

When building REAPER projects for Sunsoft-style games:

```
Synth mode:     CC (Priority 2) — NOT ADSR
CC11 response:  Linear, per-frame
CC12 response:  Static (will barely change)
Keyboard mode:  OFF for file playback
Channel mode:   Per-track (Sq1=0, Sq2=1, Tri=2, Noise=3)
```

For maximum fidelity, use SysEx register replay (Priority 1) if available.
The trace-captured versions of Castlevania and Battletoads include SysEx
data that reproduces exact APU register state, including sweep unit behavior
that CC encoding loses.

### What CC11 Values Mean on the NES

The mapping from MIDI CC11 (0-127) to NES volume (0-15):

```
NES volume = floor(CC11 * 15 / 127)

CC11   0-8   = NES vol 0 (silent)
CC11   9-16  = NES vol 1
CC11  17-25  = NES vol 2
CC11  26-33  = NES vol 3
...
CC11 119-127 = NES vol 15 (maximum)
```

With only 16 actual levels, the 4-5 CC11 events per note are encoding
4-5 distinct volume steps. That is the entire envelope. There is no
interpolation, no smoothing — what you see in the MIDI is what the
hardware played.

### Triangle Channel Special Handling

Triangle channels in this family always show CC11 = 127 (always on).
The NES triangle has no volume control — it is either sounding or silent.
The driver gates it with the length counter, not with volume writes.

This means triangle notes in Sunsoft-style games get their articulation
entirely from **note duration** (period changes), not from volume
envelopes. A staccato triangle bass note is a SHORT note, not a quiet
one. The synth must respect this: triangle CC11 is a gate signal, not
a volume curve.

### Noise Channel Notes

Noise channels in this family typically use velocity-driven envelopes
rather than CC11. The note-on velocity sets the initial hit level, and
the hardware decay handles the rest. This means noise extraction is
simpler than pulse extraction — you need the right MIDI velocity, not
a CC11 automation curve.

All but one game in this family (Super Mario Bros v3 trace, which shows
noise at 100%) have active noise channels. Noise percentages range from
62% (Castlevania) to 100% (trace versions), indicating drums are
present in most songs.

---

## 6. The Konami-Capcom Convergence

### Same Solution, Different Buildings

Here is the remarkable thing about this family: it was invented
independently at least twice.

**Castlevania** (Konami, 1986) uses an engine written by Kinuyo Yamashita
(credited as James Banana — yes, really). Konami's driver uses lookup
tables stored in the ROM to shape volume per frame. The init/play addresses
are `$BB09/$838A`. The engine was designed for Konami's internal
development pipeline.

**Mega Man 3** (Capcom, 1990) uses an engine from Capcom's late-era NES
sound driver, written by Yasuaki Fujita (credited as Bun Bun). The
init/play addresses are `$8003/$8000`. The engine was designed for
Capcom's internal development pipeline.

These two companies, working independently, arrived at the same
fundamental approach: per-frame volume envelopes from lookup tables,
static duty cycle, 3-5 updates per note. The CC11/note numbers are
strikingly close: Castlevania at 4.3, Mega Man 3 at 3.7.

Why did they converge? Because the NES hardware practically demands it.

### The Hardware Argument

The NES APU gives you:
- 16 volume levels (4 bits)
- 4 duty cycles (2 bits)
- ~60 frames per second

If you want notes that sound like *instruments* rather than *beeps*,
you need to shape the volume over time. The simplest way to do that
is a lookup table: small, fast, deterministic. You write it once in
ROM and index into it on every frame.

How much data do you need? A 4-frame envelope is 4 nibbles = 2 bytes.
A 6-frame envelope is 3 bytes. For an entire game's worth of
instruments, you might need 50-100 bytes of envelope tables. On a
system with 32KB-256KB of ROM, that is nothing.

How much CPU time does it cost? One table read, one register write,
per channel, per frame. Four channels times one byte each equals four
bytes of work per frame. On a 1.79 MHz CPU with ~29,780 cycles per
frame, that is negligible.

The lookup table approach is the **minimum viable envelope system**.
Anything simpler (constant volume) sounds flat. Anything more complex
(per-frame computation, duty switching) costs more ROM and CPU for
diminishing returns. The Sunsoft-style approach is the optimal point
on the cost-quality curve for NES audio.

Konami found it. Capcom found it. Tecmo found it (Ninja Gaiden III).
Rare found it (Battletoads). They all found it because it was the
obvious answer to the same engineering problem.

### The Timeline

| Year | Game | Developer | CC11/note | What happened |
|------|------|-----------|-----------|---------------|
| 1985 | Super Mario Bros | Nintendo | 4.9* | Early example (trace version in family) |
| 1986 | Castlevania | Konami | 4.3 | Konami perfects the approach |
| 1987 | Mega Man 1 | Capcom | 0.2 | Capcom still using minimal driver |
| 1988 | Mega Man 2 | Capcom | 0.8 | Slightly more, still minimal |
| 1990 | Mega Man 3 | Capcom | 3.7 | Capcom catches up. Envelope tables arrive. |
| 1991 | Mega Man 4 | Capcom | 3.7 | Same engine, refined |
| 1991 | Battletoads | Rare | 4.1 | Rare independently converges |
| 1991 | Ninja Gaiden III | Tecmo | 5.6 | Tecmo pushes it furthest |
| 1992 | Gargoyle's Quest II | Capcom | 4.8 | Capcom's late peak |

*Super Mario Bros v3 is a trace version; the standard NSF extraction
(v2) lands in the Capcom Duty Switcher family at 4.8/0.8 instead.*

Konami had envelope tables in 1986. Capcom did not adopt them until 1990.
That four-year gap explains why Mega Man 1 and 2 sound "simpler" than
Castlevania despite being later games — the sound engines were at
different evolutionary stages.

---

## 7. Notable Outliers

### Ninja Gaiden III: The Overachiever (CC11/note = 5.6)

At 5.6 CC11 events per note, Ninja Gaiden III has the highest envelope
density in the family. It is at the very upper boundary — one more
CC11 event per note and it would spill into the Dense Automator family.

What Tecmo's engine does differently: the envelope tables are longer.
Where Castlevania uses 4-5 frame envelopes, Ninja Gaiden III uses 5-6
frame envelopes with more gradual decay curves. The result is a sound
that is still punchy (instant attack) but has a slightly more musical
decay. Notes ring longer before they fade.

The dominant duty is 12.5% — the thinnest, buzziest pulse waveform the
NES can produce. Combined with the longer envelopes, this gives Ninja
Gaiden III a distinctively *nasal*, almost reedy quality. It sounds
like an angry oboe played through a distortion pedal.

CC12/note is exactly 0.0. Not 0.1, not 0.05 — zero. Tecmo set the
duty cycle once and literally never touched it again for the entire
song. Maximum commitment to the Sunsoft-style philosophy.

### Battletoads: The Unlikely Member

Battletoads is a Rare game. Rare is a British studio best known for
Donkey Kong Country and GoldenEye. They are not Konami. They are not
Capcom. They did not have access to either company's sound drivers.

And yet: CC11/note = 4.1, CC12/note = 0.1. Squarely in the
Sunsoft-style family.

Rare's NES sound engine was written by David Wise, who would later
become famous for the Donkey Kong Country soundtrack. On the NES, Wise's
engine uses the same per-frame envelope lookup approach as Konami and
Capcom, but with a distinctively rhythmic sensibility. Battletoads music
grooves in a way that Castlevania music does not — the envelopes are
shaped for funk, not for gothic drama.

The survey captured Battletoads through both NSF emulation (21 songs) and
multiple Mesen trace iterations (9 additional entries). Every version
lands in the same family. The NSF extraction at 4.1 CC11/note and the
trace extractions ranging from 3.8 to 4.8 CC11/note are all consistent
with the envelope table approach. The spread in trace versions (3.8-4.8)
reflects differences in extraction accuracy, not differences in the
underlying engine.

Battletoads is proof that the Sunsoft-style approach was not a trade
secret or a proprietary technique. It was a *convergent solution* that
any competent NES audio programmer would discover independently.

### Gargoyle's Quest II: Capcom's Late Masterpiece

At 4.8 CC11/note and 0.0 CC12/note, Gargoyle's Quest II (1992) is
Capcom's most refined Sunsoft-style title. It arrived at the very
end of the NES lifecycle, when Capcom's sound team had years of
experience with their engine.

The 25% dominant duty gives it a brighter, more aggressive tone than
Castlevania's 50%. Combined with 22,739 total notes across 21 songs,
it is one of the most note-dense games in the family — Capcom's
composers were writing increasingly complex music as the hardware
matured.

### Super Mario Bros v3: The Ghost Entry

Super Mario Bros appears in this family as "v3" — a trace-captured
version showing 4.9 CC11/note and 0.0 CC12/note. The standard NSF
extraction of SMB (v2) shows 4.8 CC11/note with 0.8 CC12/note, which
puts it in the Capcom Duty Switcher family.

This discrepancy matters. It demonstrates that the same game can land
in different families depending on the extraction route. The trace
version captures the actual APU register behavior, which may differ
from what the NSF rip reproduces. In this case, the trace shows the
driver's volume behavior more clearly while missing some of the duty
switching that the NSF captures.

This is a data quality lesson, not a musical one. The real Super Mario
Bros probably belongs in the Duty Switcher family (it does switch duty),
but its volume behavior alone is Sunsoft-style enough to land here when
CC12 is suppressed in the trace.

---

## 8. Why This Is "The NES Sound"

### The Cultural Argument

Ask someone to hum a NES tune. They will hum Castlevania, Mega Man,
or the Mario theme. Two of those three are Sunsoft-style games. The
third (Mario) has trace versions that land in this family.

Ask someone to describe the NES sound. They will say "bleepy" and
"punchy" and "catchy." The bleepiness comes from square waves. The
punchiness comes from envelope tables. The catchiness comes from
the composers. Two out of three are Sunsoft-style features.

This family defined the NES sound because its games were the
best-selling, most-remembered, most-replayed titles on the system.
Castlevania sold over a million copies. Mega Man 3 and 4 were
flagship Capcom titles. Battletoads was one of the most talked-about
games of 1991. These were the games that formed people's acoustic
memories of what "NES" sounds like.

### The Technical Argument

The Sunsoft-style approach occupies a unique sweet spot:

- **More expressive than minimal drivers** — each note has a sculpted
  attack and decay instead of a flat beep
- **Less expensive than dense automators** — 4-5 writes per note
  instead of 10-15, less ROM, less CPU
- **More consistent than duty switchers** — timbre does not waver,
  creating a signature sound that is immediately recognizable
- **Accessible to composers** — writing an envelope table is simpler
  than programming a per-frame volume stream

This sweet spot made it the go-to approach for studios that wanted
professional-sounding music without dedicating excessive resources to
the sound engine. It is the "just right" porridge of NES audio design.

### The Psychoacoustic Argument

The human ear is extremely sensitive to attack transients. We identify
instruments primarily by their attack characteristics — the first
50-100ms of a sound tell our brain what is making the noise. Sustain
and release are secondary.

The Sunsoft-style envelope concentrates all its expressive power in the
attack transient: 67ms of rapid volume change (4 frames at 60fps) followed
by a steady-state sustain. This is psychoacoustically optimal. It gives
the ear the maximum possible information about the "instrument" in the
minimum possible time, using only 4 bits of volume resolution.

Dense automators spread their volume information across the entire note,
which can sound richer but also more diffuse. Minimal drivers give no
attack information at all, which is why they sound "flat." The
Sunsoft-style approach is the most perceptually efficient use of the
NES APU's limited volume resolution.

---

## Summary Statistics

### Family Envelope Profile

| Statistic | Value |
|-----------|-------|
| Games (unique) | 7 |
| Games (with trace variants) | 18 |
| Total songs (unique games only) | 235 |
| Total notes (unique games only) | ~150,000 |
| CC11/note range | 3.7 - 5.6 |
| CC11/note mean | 4.3 |
| CC12/note range | 0.0 - 0.2 |
| CC12/note mean | 0.07 |
| Typical envelope length | 4-6 frames (67-100ms) |
| Volume levels used | 4-8 of 16 possible |

### Developer Representation

| Developer | Games | Era |
|-----------|-------|-----|
| Capcom | 3 (MM3, MM4, Gargoyle's Quest II) | 1990-1992 |
| Konami | 1 (Castlevania) | 1986 |
| Rare | 1 (Battletoads) | 1991 |
| Tecmo | 1 (Ninja Gaiden III) | 1991 |
| Nintendo | 1 (Super Mario Bros, trace variant) | 1985 |

### How This Family Compares to Its Neighbors

| Family | CC11/note | CC12/note | Character |
|--------|-----------|-----------|-----------|
| Minimal | 0.1-2.8 | 0.0-0.6 | Clean, simple, polite |
| **Sunsoft-style** | **3.5-5.6** | **0.0-0.2** | **Punchy, aggressive, THE NES sound** |
| Capcom Duty Switcher | 3.7-4.9 | 0.7-1.0 | Animated, shimmering, sophisticated |
| Dense Automator | 5.1-15.0 | 0.0-0.3 | Rich, complex, orchestral |
| Konami Full Animation | 7.7+ | 1.3+ | Everything animated, maximum control |

---

## The Bottom Line

The Sunsoft-style family is not named after Sunsoft the company (who
actually made Dense Automator games like Blaster Master and Batman).
It is named after the *style* — the per-frame envelope table approach
that Sunsoft helped popularize but that Konami, Capcom, Tecmo, Rare,
and Nintendo all discovered independently.

It is the middle path of NES audio: more expressive than a beep, less
expensive than a symphony. It is the sound of a square wave that
arrives at full power and decays in four frames. It is the sound of a
composer trusting the attack transient to do all the work. It is the
sound of Vampire Killer, Snake Man, and the Battletoads pause screen.

It is the punch.

And when you extract it, play back the CC11 automation faithfully,
because that tiny five-frame volume curve IS the music. Without it,
you just have beeps. With it, you have the sound that a generation
of gamers can hum from memory thirty-five years later.

That is what four bits of volume and five frames of envelope can do
when you use them right.
