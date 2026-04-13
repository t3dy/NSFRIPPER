# Silence of the Square Waves

## A Field Guide to the NES Minimal Driver Family

*25 games. 0.1 to 2.8 CC11 events per note. The sound of hardware left alone.*

---

There is a particular kind of confidence in saying almost nothing. In
music, it is the rest between the notes. In painting, it is the bare
canvas showing through. And in the NES Audio Processing Unit, it is the
driver that writes a volume byte once, sets the period register, and
then walks away from the microphone.

Welcome to the Minimal Driver family: twenty-five games whose sound
engines range from the near-silent (Dragon Warrior at 0.1 CC11 per note,
meaning one volume event for every ten notes) to the merely terse
(Castlevania 2 at 2.8). In an era when other engines were scribbling
volume automation onto every frame like hyperactive court stenographers,
these drivers trusted the hardware to speak for itself.

Some of the best NES soundtracks ever written belong to this family.
That is not a coincidence. That is the thesis.

---

## 1. The Complete Roster

The following table lists every game classified as Minimal in the
65-game driver survey. The columns that matter: CC11/note tells you how
much the driver talks to the volume register per note event. CC12/note
tells you how much it fiddles with duty cycle. Lower numbers mean the
driver is more hands-off.

| Game | Developer | Composer | Songs | Notes | CC11/note | CC12/note | Dominant Duty | Noise |
|------|-----------|----------|-------|-------|-----------|-----------|---------------|-------|
| Dragon Warrior | Enix / Chunsoft | Koichi Sugiyama | 47 | 12,146 | 0.1 | 0.1 | 50% | Y |
| Wizards & Warriors | Rare / Acclaim | David Wise | 29 | 15,646 | 0.1 | 0.0 | 50% | Y |
| Ghosts'n Goblins | Capcom | Ayako Mori | 3 | 1,221 | 0.1 | 0.1 | 25% | N |
| Mega Man 1 | Capcom | Manami Matsumae | 17 | 20,198 | 0.2 | 0.0 | 75% | Y |
| Trojan | Capcom | (uncredited) | 35 | 7,635 | 0.2 | 0.2 | 12.5% | Y |
| 1942 | Capcom / Micronics | (uncredited) | 13 | 119 | 0.4 | 0.4 | 50% | Y |
| Section Z | Capcom | (uncredited) | 19 | 6,953 | 0.7 | 0.1 | 12.5% | Y |
| Mega Man 2 | Capcom | Takashi Tateishi | 24 | 41,291 | 0.8 | 0.0 | 12.5% | Y |
| DuckTales | Capcom | (uncredited) | 45 | 16,137 | 0.8 | 0.2 | 50% | Y |
| Bionic Commando | Capcom | Junko Tamiya | 22 | 19,234 | 0.9 | 0.0 | 25% | Y |
| Legendary Wings | Capcom | (uncredited) | 36 | 23,474 | 1.0 | 0.0 | 50% | Y |
| Strider | Capcom | Harumi Fujita | 15 | 21,744 | 1.0 | 0.0 | 75% | Y |
| Contra | Konami | (various) | 2 | 199 | 1.5 | 0.3 | 12.5% | N |
| Metal Gear | Konami | Kazuki Muraoka | 56 | 18,288 | 2.0 | 0.2 | 50% | Y |
| Faxanadu | Hudson / Falcom | (uncredited) | 44 | 13,909 | 2.1 | 0.1 | 50% | Y |
| Abadox | Natsume | Kyouhei Sada | 29 | 19,371 | 2.2 | 0.1 | 50% | Y |
| Castlevania III (trace) | Konami | (various) | 10 | 349 | 2.5 | 0.3 | 12.5% | Y |
| The Goonies II | Konami | (uncredited) | 56 | 14,918 | 2.7 | 0.2 | 50% | Y |
| Castlevania 2: Simon's Quest | Konami | Kenichi Matsubara | 51 | 12,446 | 2.8 | 0.6 | 25% | Y |
| Marble Madness | Rare / Milton Bradley | (uncredited) | 9 | 4,224 | 3.5 | 0.2 | 50% | N |
| Castlevania II (trace) | Konami | (various) | 7 | 750 | 3.6 | 0.1 | 12.5% | Y |
| Punch-Out!! | Nintendo | Yukio Kaneoka | 17 | 1,381 | 4.3 | 0.3 | 50% | Y |
| Gradius | Konami | Miki Higashino | 32 | 13,415 | 26.2 | 0.2 | 25% | Y |
| W&W (title, triangle fix) | Rare | David Wise | 1 | 405 | 0.0 | 0.0 | 25% | N |
| W&W (trace) | Rare | David Wise | 1 | 399 | 0.0 | 0.0 | 25% | N |

**Total: ~295,000 notes across 25 game entries.**

A few items in that table demand immediate comment. Gradius at 26.2
CC11/note is sitting at the Minimal table like a Ferrari parked in a
monastery lot. Punch-Out at 4.3 and Marble Madness at 3.5 are on the
border. We will deal with these outliers in Section 6. For now, note
that the survey classified them as Minimal based on their median song
behavior, not their most extreme tracks.

---

## 2. What "Minimal" Means at the Hardware Level

### The NES APU in 30 Seconds

The NES has five audio channels: two pulse wave generators, one triangle
wave generator, one noise generator, and one delta modulation channel
(which we ignore here because almost nobody used it for music). Each
pulse channel has four registers that control:

- **Volume** ($4000/$4004): 4-bit value (0-15), plus decay/length counter flags
- **Sweep** ($4001/$4005): frequency sweep unit (pitch bends)
- **Period low** ($4002/$4006): lower 8 bits of the timer period
- **Period high + length** ($4003/$4007): upper 3 bits of period + length counter load

The triangle channel has a linear counter instead of volume (it is
always at full amplitude or silent -- there is no in-between). The noise
channel replaces the period registers with a mode/period selector.

### What a Minimal Driver Does

A Minimal driver's note-playing routine looks approximately like this
in pseudocode:

```
play_note(channel, pitch, volume):
    write volume register  (once)
    write period low       (once)
    write period high      (once)
    return
```

That is it. Three register writes. The volume is set at note-on and
never touched again until the next note. The duty cycle (the waveform
shape -- 12.5%, 25%, 50%, or 75% pulse width) was typically set once
during initialization or at the start of a song and left alone for the
entire track.

Compare this to a Sunsoft-style engine (Castlevania 1, Mega Man 3-4)
which writes the volume register 4-5 times per note using lookup table
envelopes, or a Dense Automator like Final Fantasy which writes volume
literally every frame (14.9 CC11/note -- roughly once every 16.7
milliseconds).

### What the Hardware Does When Left Alone

This is the critical insight. When a Minimal driver writes volume = 12
and walks away, the NES APU does not simply hold that volume forever.
Depending on the flags in the volume register:

- **Length counter enabled**: the channel silences itself after a
  hardware-determined duration (based on a lookup table indexed by the
  length counter load value). This gives automatic note-off behavior
  without any further driver intervention.
- **Decay enabled**: the APU runs its own internal volume envelope,
  decrementing the volume at a hardware-controlled rate. This produces
  a natural fade-out on each note.
- **Constant volume mode**: the volume holds at exactly the written
  value until the driver writes a new one or the length counter expires.

Minimal drivers exploit these hardware features. They are not lazy --
they are *delegating*. The NES APU has a perfectly serviceable built-in
envelope generator. Why replicate it in software and burn CPU cycles
when the hardware will do it for free?

### The Volume Register as a Single Instruction

In CC11 terms, this means:

| CC11/note | What is happening |
|-----------|-------------------|
| 0.0 - 0.2 | Driver sets volume once at song start, relies entirely on hardware length/decay. Some notes get no volume write at all. |
| 0.5 - 1.0 | One volume write per note (note-on). Hardware handles decay. Silence achieved by length counter or explicit note-off. |
| 1.0 - 2.0 | Volume at note-on plus one adjustment (maybe a release, maybe a gate-off at note end). |
| 2.0 - 2.8 | Simple two-phase: set volume at attack, reduce/kill at release. Possibly a basic software envelope with 2-3 steps. |

Dragon Warrior at 0.1 is so minimal that many notes share a single
volume event. The driver writes a volume level, then plays an entire
phrase of notes at that volume, changing only the pitch registers. Pure
hardware envelope territory.

### The Duty Cycle: Set It and Forget It

CC12/note values in this family are almost universally near zero:

| Game | CC12/note | Interpretation |
|------|-----------|----------------|
| Mega Man 1 | 0.0 | Duty set once per song (75%), never changed |
| Mega Man 2 | 0.0 | Same -- locked to 12.5% |
| Bionic Commando | 0.0 | Locked to 25% |
| Wizards & Warriors | 0.0 | Locked to 50% |
| Strider | 0.0 | Locked to 75% |
| Legendary Wings | 0.0 | Locked to 50% |
| DuckTales | 0.2 | Rare duty changes, mostly 50% |
| Castlevania 2 | 0.6 | Highest in family -- occasional timbral shifts |

When CC12/note is 0.0, it means the pulse waveform shape is identical
for every single note in the track. The timbre does not change within
notes or between notes. The only timbral variation comes from the
interaction between the fixed duty cycle and the changing pitch -- a
50% square wave at C3 sounds different from a 50% square wave at C5
simply due to the physics of harmonics at different frequencies.

Castlevania 2: Simon's Quest at CC12/note = 0.6 is the most
duty-active member of the family and hints at the transition toward
the Sunsoft-style approach that Konami would adopt for Castlevania 3.

---

## 3. What It Sounds Like

### The Adjective List

If you play a Minimal driver game next to a Dense Automator game, these
are the words that tend to surface:

| Minimal Driver Sound | Dense Automator Sound |
|----------------------|----------------------|
| Clean | Rich |
| Bright | Warm |
| Crisp | Smooth |
| Mechanical | Organic |
| Arcade-like | Cinematic |
| Transparent | Lush |
| Precise | Expressive |
| Toy-like (pejorative) | Muddy (pejorative) |

### The Character of Silence

A Minimal driver note has a particular envelope shape that is
unmistakable once you learn to hear it. It goes like this:

1. **Instant attack.** Volume jumps from 0 to the target level in a
   single sample (one write to $4000). There is no fade-in, no soft
   onset, no gradual swell. The note exists or it does not.

2. **Flat sustain.** If the driver uses constant volume mode, the
   amplitude holds perfectly flat for the entire note duration. This
   produces the characteristic "buzz" of early NES music -- a square
   wave at constant amplitude is about as far from a natural instrument
   as you can get.

3. **Hard release.** The note ends either by the length counter expiring
   (a clean chop) or by the driver writing volume = 0 (another clean
   chop). There is no release tail, no reverb, no lingering decay.

The overall effect is a soundscape built from rectangular blocks of
sound. Notes are bricks. Melody is masonry. There is no mortar.

### How Composers Compensated

The great Minimal driver composers understood the constraints and
turned them into style. Without per-frame volume envelopes, they had
exactly three tools for expression:

1. **Note duration.** Short notes create staccato articulation. Long
   notes create legato. The gap between notes is the only dynamic
   shaping available. Listen to DuckTales: The Moon -- the melody's
   expressiveness comes entirely from how long each note is held
   relative to its neighbors.

2. **Pitch register changes.** Fast arpeggios (cycling through chord
   tones rapidly) create the illusion of chords on a single channel.
   Mega Man 2's "Dr. Wily Stage 1" uses arpeggiated bass on the
   triangle channel to simulate a fuller sound than three channels
   should be able to produce.

3. **Duty cycle selection.** While the duty does not change per-note,
   the *choice* of duty cycle for each channel defines the timbral
   palette of the entire soundtrack. Mega Man 1 at 75% sounds hollow
   and slightly mournful. Strider at 75% sounds eerie and alien.
   Bionic Commando at 25% sounds bright and punchy. Wizards & Warriors
   at 50% sounds full and warm.

### The Triangle Channel: Nature's Minimal Driver

The triangle channel deserves special mention because it is *always*
minimal, regardless of the driver family. The NES triangle channel has
no volume control -- it is either on or off. CC11 on triangle is always
127 (full gate) or absent. Even Castlevania 1's Sunsoft-style engine,
with its elaborate envelope tables, can only gate the triangle on and
off. The triangle is the one channel where every driver is Minimal by
hardware mandate.

This is why the triangle bass in Mega Man 2 and Castlevania 2 sounds
so similar despite the games having very different driver architectures
on the pulse channels. The triangle does not care about your driver's
sophistication.

---

## 4. How to Recognize a Minimal Driver

### By the Numbers

When you extract a new game through the NSF pipeline and run
`driver_survey.py`, the classification fingerprint is:

```
CC11/note < 3.0  AND  CC12/note < 0.5
```

If both conditions hold, you are almost certainly looking at a Minimal
driver. The CC12 threshold is important -- Castlevania 2 at CC12 = 0.6
is the borderline case that hints at a transition to a more
sophisticated architecture.

### By Ear

Play the extracted audio and listen for these tells:

1. **No punch on attacks.** Sunsoft-style engines have a distinctive
   "pop" at the start of each note (volume spike then rapid decay).
   Minimal drivers do not have this. Notes start and sustain at the
   same volume.

2. **No fade on releases.** Listen to the ends of notes. If they cut
   off sharply with no trailing decay, that is Minimal. If there is
   a quick downward slope before silence, that is an envelope table.

3. **Uniform timbre across a track.** Pick a pulse channel and listen
   to 20 consecutive notes. If they all sound like exactly the same
   waveform at different pitches, the duty cycle is not changing. That
   is Minimal.

4. **Expressiveness through rhythm, not dynamics.** If the music
   sounds rhythmically complex but dynamically flat, the composer is
   working within Minimal constraints and using note placement as the
   primary expressive tool.

### By Looking at the MIDI

Open the extracted MIDI in a DAW and look at the CC11 automation lane:

- **Minimal**: sparse dots or nothing. Long stretches with no CC11
  events between notes.
- **Sunsoft-style**: staircase patterns. 3-5 steps per note forming
  a decay curve.
- **Dense**: continuous curves. CC11 events on nearly every tick.

The visual difference is unmistakable. A Minimal driver's CC11 lane
looks like a starfield. A Dense driver's CC11 lane looks like a
mountain range.

---

## 5. Extraction Tips and ReapNES Settings

### NSF Pipeline: It Just Works

Minimal drivers are the easiest family to extract. The NSF pipeline
captures everything the driver does because the driver barely does
anything. There is almost nothing to lose in the NSF-to-MIDI
translation.

```bash
python scripts/fetch_and_extract.py "Dragon Warrior"
python scripts/driver_survey.py --game Dragon_Warrior
# CC11/note: 0.1 -- confirmed Minimal
```

### ReapNES Synth Settings

Because these drivers delegate volume shaping to the hardware, the
ReapNES synth can actually run in ADSR mode and produce reasonable
results. This is the ONE family where ADSR keyboard mode is a viable
substitute for CC-driven playback:

| Setting | Recommendation | Why |
|---------|---------------|-----|
| Input mode | CC or ADSR both work | So little CC data that ADSR approximation is close |
| Volume source | CC11 if available, else ADSR | CC11 data is sparse but correct when present |
| Duty cycle | Match dominant duty from survey | Static duty -- set once, leave alone |
| Decay rate | Short (50-100ms) | Mimics hardware length counter behavior |
| Release | Hard cut (0ms) | No trailing release in hardware |

For the ultra-minimal games (Dragon Warrior, Wizards & Warriors,
Mega Man 1 at CC11 < 0.3), you can essentially treat the MIDI as
note-on/note-off data and let the synth's ADSR shape the sound.
The CC11 data is so sparse it adds little that a well-tuned ADSR
would not already provide.

### Watch for: Contra and Wizards & Warriors

Two games in this family carry asterisks:

**Contra (1.5 CC11/note in NSF, 6.9 in Mesen trace):** The NSF rip
captures a simplified playback mode. The actual game runs Konami's
full per-frame envelope engine. If you extract Contra from NSF, you
get a Minimal-sounding result. If you trace it from the running game,
you get a Dense Automator. This is the single strongest proof in the
survey that NSF fidelity is not always equal to in-game fidelity.

**Wizards & Warriors (0.1 CC11/note from NSF, richer in trace):**
Rare's engine is deceptively simple in NSF output. The ROM parser
reveals behavior that the NSF extraction does not capture. For
production-quality W&W output, the trace pipeline is recommended.

These two games are the canaries in the coal mine. When a Minimal
classification feels wrong -- when the game sounds richer than 0.1
CC11/note should allow -- suspect an NSF fidelity gap and investigate
with Mesen.

### The Generate-and-Listen Workflow

For any Minimal driver game, the fast path is:

1. `fetch_and_extract.py` -- get the NSF, extract all songs
2. `driver_survey.py` -- confirm CC11/note < 3.0
3. `generate_project.py --nes-native` -- build the REAPER project
4. Open in REAPER, listen, compare to game audio
5. If it sounds right (it usually will), done. Ship it.

The entire pipeline for a Minimal driver game can run unattended.
No trace capture needed. No envelope debugging. No CC synchronization
headaches. This is why the batch processing pipeline exists -- the
Minimal family is the low-hanging fruit that fills the library.

---

## 6. Notable Outliers and Curiosities

### Gradius: The 26.2 CC11/note Elephant in the Room

Gradius sits in the Minimal family table with a CC11/note value of
26.2, which is not only the highest in the family but the highest in
the entire 65-game survey. Higher than Final Fantasy (14.9). Higher
than Blaster Master (11.7). What is happening?

The answer is that Gradius's classification as Minimal is based on
median song behavior, not mean. Most of Gradius's 32 songs are
straightforward and sparse. But a handful of tracks use Konami's
engine for rapid volume modulation effects -- echo simulation,
tremolo, and fade effects that produce enormous CC11 density on those
specific songs. The outlier songs drag the mean up to 26.2 while the
median sits comfortably in Minimal territory.

This is actually a common Konami pattern. The engine is capable of
sophisticated behavior, but most songs do not use it. Gradius's
composer Miki Higashino wrote mostly clean, simple arrangements and
reserved the heavy automation for special-effect passages. The engine
has gears; most songs idle in first.

Gradius: 32 songs, 13,415 notes, and a lesson in why median matters
more than mean when classifying drivers.

### Marble Madness and Punch-Out: The Borderline Cases

Marble Madness (3.5 CC11/note) and Punch-Out (4.3 CC11/note) sit at
the upper boundary of the Minimal family, close enough to the
Sunsoft-style range (3.5-5.6) to raise an eyebrow.

Marble Madness is an interesting case -- Rare developed it (same
studio as Wizards & Warriors), it has no noise channel at all, and
its 9 songs across 4,224 notes show just enough envelope activity to
suggest a basic software envelope rather than pure hardware
delegation. It may represent Rare's engine at a slightly more
sophisticated stage than the W&W build.

Punch-Out at 4.3 is genuinely on the border and could be classified
either way. Yukio Kaneoka's engine for this game has a modest envelope
capability that it uses sparingly. The classification as Minimal
reflects the overall character of the soundtrack more than the
numerical threshold.

### DuckTales: 0.8 CC11/note and One of the Greatest NES Soundtracks

This is the mystery and the miracle. DuckTales has a CC11/note ratio
of 0.8. Less than one volume event per note on average. The driver
writes volume at note-on, maybe adjusts once, and that is it. No
envelope tables. No per-frame shaping. No tricks.

And yet "The Moon" theme from DuckTales is regularly cited as one of
the greatest pieces of video game music ever written. How?

The answer is composition. When your driver cannot shape sound,
everything falls on the notes themselves. DuckTales' composer (likely
Hiroshige Tonomura, though Capcom's credits were notoriously vague)
wrote melodies with such strong contour, such precise rhythmic
placement, and such clever use of two-channel counterpoint that the
music transcends its technical limitations.

The pulse channels alternate between melody and accompaniment. The
triangle provides a walking bass that anchors the harmony. The noise
channel (present in 56% of songs) adds rhythmic drive. All of this
works because the notes are right, not because the envelopes are
sophisticated.

DuckTales is the proof that in the Minimal family, the composer
matters more than the engine.

### Dragon Warrior: The Absolute Floor

At 0.1 CC11/note, Dragon Warrior is the most minimal game in the
survey. One volume event for roughly every ten notes. Koichi
Sugiyama's orchestral arrangements -- the same composer who scored
the Tokyo Olympics ceremonies -- are rendered here in their most
skeletal form.

The 47 songs and 12,146 notes of Dragon Warrior represent what
happens when a classically trained orchestral composer writes for
hardware that offers essentially no dynamic control. Sugiyama's
response was to write as if scoring for a music box: clean melodies,
simple harmonies, and dignity through restraint. The famous overworld
theme works because the melody itself carries all the emotional
weight. It does not need an envelope to tell you how to feel.

### Castlevania 2: The Transitional Fossil

Castlevania 2: Simon's Quest (2.8 CC11/note, 0.6 CC12/note) is the
most active member of the Minimal family and the clearest transitional
case. Its CC11 is nearly at the boundary with Sunsoft-style (3.0+),
and its CC12 of 0.6 is by far the highest in the family -- three times
the next highest member.

Konami was evolving. Castlevania 1 (not in this family -- it is
Sunsoft-style at 4.3 CC11/note) had already demonstrated full envelope
tables. But CV2 uses a lighter touch, perhaps because the soundtrack
is more atmospheric and less action-driven. The famous "Bloody Tears"
theme works with a relatively sparse envelope because the composition
is built on arpeggiation and rhythmic drive rather than dynamic
shaping.

The duty switching at 0.6 CC12/note shows Konami experimenting with
timbral animation within notes -- a technique they would fully develop
for Castlevania 3 (0.8-1.0 CC12/note in the Capcom Duty Switcher
family). CV2 is the evolutionary link between Konami's early Minimal
approach and their later sophisticated engine.

---

## 7. Developer Patterns

### Capcom Dominates the Minimal Family

Count the Capcom games in the roster:

| Capcom Game | CC11/note | Years |
|-------------|-----------|-------|
| Ghosts'n Goblins | 0.1 | 1986 |
| Mega Man 1 | 0.2 | 1987 |
| Trojan | 0.2 | 1987 |
| 1942 | 0.4 | 1986 |
| Section Z | 0.7 | 1987 |
| Mega Man 2 | 0.8 | 1988 |
| DuckTales | 0.8 | 1989 |
| Bionic Commando | 0.9 | 1988 |
| Legendary Wings | 1.0 | 1988 |
| Strider | 1.0 | 1989 |

That is 10 out of 25 games. Forty percent of the Minimal family is
Capcom. And the NSF address pattern tells the story: six of these
games share the Init=$8003/Play=$8000 signature, indicating the same
underlying sound driver binary.

Capcom's early NES engine was explicitly Minimal. It set volume once,
picked a duty cycle, wrote the period, and moved on. This was a
deliberate engineering choice -- Capcom's games were action-heavy and
needed CPU cycles for sprite handling, scrolling, and collision
detection. Spending frames on volume automation would have competed
with gameplay performance.

The transition away from Minimal happened around Mega Man 3 (1990),
when Capcom's engine gained envelope lookup tables and moved to the
Sunsoft-style family at 3.7 CC11/note. DuckTales (1989) was one of
the last great Minimal Capcom soundtracks before the transition.

### Konami: Minimal by Choice, Not by Limitation

Konami's presence in the Minimal family is more nuanced:

| Konami Game | CC11/note | Note |
|-------------|-----------|------|
| Contra (NSF) | 1.5 | Actually 6.9 in trace -- NSF fidelity gap |
| Metal Gear | 2.0 | Legitimate Minimal |
| Castlevania III (trace) | 2.5 | Trace excerpt, not full NSF |
| The Goonies II | 2.7 | Legitimate Minimal |
| Castlevania 2 | 2.8 | Transitional to Sunsoft-style |
| Gradius | 26.2 | Outlier (median is Minimal, mean is not) |

Konami's engine was always capable of more. Castlevania 1 (4.3
CC11/note, Sunsoft-style) proves the engine had envelope tables as
early as 1986. When Konami games appear in the Minimal family, it is
because the *composer* chose restraint, not because the *engine*
lacked capability.

Metal Gear is the clearest example: 56 songs, 18,288 notes, 2.0
CC11/note. Kazuki Muraoka wrote a stealth-game soundtrack that is
deliberately sparse and understated. The Minimal driver approach
serves the game's atmosphere of tension and isolation. A dense,
punchy Sunsoft-style envelope would have been wrong for the mood.

### Rare: Minimal to the Core

Rare (Wizards & Warriors, Marble Madness) produced some of the most
extremely Minimal results in the survey. W&W at 0.1 CC11/note and
Marble Madness at 3.5 represent the range of their engine. David
Wise's compositions for W&W are among the most beloved NES
soundtracks, proving once again that Minimal does not mean inferior.

The W&W trace data is particularly interesting: even when captured from
the running ROM, the CC11 density remains at 0.0. This is a genuinely
Minimal engine, unlike Contra where the NSF understates the driver's
actual behavior.

### Other Studios

| Developer | Game | CC11/note |
|-----------|------|-----------|
| Enix / Chunsoft | Dragon Warrior | 0.1 |
| Hudson / Falcom | Faxanadu | 2.1 |
| Natsume | Abadox | 2.2 |
| Nintendo | Punch-Out!! | 4.3 |

Each of these represents a different engine with its own Minimal
characteristics. Faxanadu is notable as a Hudson Soft production with
Falcom involvement -- the same Falcom that would later produce the
Ys series with its famously rich FM synthesis soundtracks. On the NES,
they were content with 2.1 CC11/note.

---

## 8. The NSF Address Fingerprint

Minimal driver games cluster around a few NSF init/play address
patterns, which helps identify engine families before even listening:

| Init/Play Pattern | Games | Likely Engine |
|-------------------|-------|---------------|
| $8003 / $8000 | Mega Man 2, DuckTales, Bionic Commando, Legendary Wings, Strider, Section Z | Capcom standard (late 1987+) |
| $9003 / $9000 | Mega Man 1 | Capcom standard (early, different load addr) |
| $8380 / $842B | Ghosts'n Goblins | Capcom early (pre-standard) |
| $BF90 / $BFD0 | Trojan | Capcom (unique address set) |
| $F200 / $F2C0 | Dragon Warrior | Enix custom |
| $8000 / $9344 | Metal Gear | Konami (Metal Gear variant) |
| $BDE6 / $8179 | The Goonies II | Konami (Goonies variant) |
| $BC0C / $967D | Castlevania 2 | Konami (Castlevania variant) |
| $EC48 / $ED30 | Gradius | Konami (Gradius variant) |
| $B3D8 / $B3D1 | Faxanadu | Hudson custom |
| $C3A0 / $8016 | Abadox | Natsume custom |
| $FBA5 / $F060 | Punch-Out!! | Nintendo custom |
| $8000 / $801D | Marble Madness | Rare custom |

The Capcom $8003/$8000 cluster is the strongest signal: if a new
game has those addresses, expect Minimal behavior with CC11/note
under 1.5.

---

## 9. The Philosophical Case for Minimalism

### Less Is Not Worse

There is a temptation, when you have a metric like CC11/note, to
treat higher numbers as better. More automation. More sophistication.
More effort by the driver. And yet:

- DuckTales (0.8) is more beloved than most games at 5.0+
- Mega Man 2 (0.8) defined the NES sound for a generation
- Dragon Warrior (0.1) launched the JRPG genre with a score that
  still gets orchestral concert performances 35 years later
- Wizards & Warriors (0.1) has one of the most distinctive bass
  sounds on the platform

The Minimal family contains an outsized share of the NES canon. Not
despite its simplicity, but because of a particular property that
emerges from constraint: **transparency**.

### The Transparency Argument

When a Dense Automator writes volume every frame, the driver's
personality is baked into every note. Final Fantasy sounds like
Final Fantasy partly because of Uematsu's melodies, but also partly
because of Nasir Gebelli's envelope engine. The driver is an
instrument in itself, imposing a particular character on everything
it plays.

When a Minimal driver steps back, the composition is naked. There is
nowhere to hide. A weak melody played through Castlevania 1's
Sunsoft-style engine might still sound interesting because the punch
of the envelope table gives it energy. A weak melody played through
Mega Man 2's Minimal engine sounds weak. Full stop.

This means that every great Minimal driver soundtrack is great because
the *music itself* is great. The notes carry all the meaning. The
composition does all the work. The driver is a transparent window,
not a stained-glass filter.

### The Piano Analogy

Think of it this way. A piano has a fixed timbre -- you cannot change
the waveform of a hammer hitting a string. The expressiveness comes
from which notes you play, how long you hold them, and how loud you
strike them. A Minimal NES driver is similar, except you also lose
the dynamic range (every note is approximately the same volume).

What remains is pure pitch and rhythm. Melody in its most
crystalline form. And it turns out that pitch and rhythm are quite
enough, in the right hands.

Bach wrote keyboard works on instruments with even less dynamic
range than the NES. The harpsichord has no velocity sensitivity at
all -- every note is the same volume regardless of how hard you press
the key. Bach did not seem to find this limiting. The Minimal NES
driver composers did not either.

### The Production Argument

From a pipeline perspective, Minimal drivers are a gift. They
extract cleanly, convert losslessly, and play back accurately in
virtually any synth configuration. The signal-to-noise ratio of the
extraction is effectively 1:1 because there is barely any signal to
lose.

The 25 games in this family represent the fastest path to a complete
NES music archive. Run the NSF pipeline, generate the REAPER
projects, and the output is ready. No trace debugging. No envelope
calibration. No CC synchronization nightmares. Just music, as the
composers wrote it, transparent and undistorted.

That simplicity is not just a production convenience. It is a
philosophical statement about what matters in music. Sometimes the
answer is not more data, more automation, more control. Sometimes
the answer is a square wave, a good melody, and the confidence to
let the hardware handle the rest.

---

## Appendix A: CC11/note Distribution Within the Family

```
0.0  |##            W&W trace variants
0.1  |####          Dragon Warrior, Wizards & Warriors, Ghosts'n Goblins
0.2  |##            Mega Man 1, Trojan
0.4  |#             1942
0.7  |#             Section Z
0.8  |##            Mega Man 2, DuckTales
0.9  |#             Bionic Commando
1.0  |##            Legendary Wings, Strider
1.5  |#             Contra (NSF -- actual in-game is 6.9)
2.0  |#             Metal Gear
2.1  |#             Faxanadu
2.2  |#             Abadox
2.5  |#             Castlevania III (trace)
2.7  |#             The Goonies II
2.8  |#             Castlevania 2
3.5  |#             Marble Madness (borderline)
3.6  |#             Castlevania II trace (borderline)
4.3  |#             Punch-Out!! (borderline)
    ...
26.2 |#             Gradius (outlier -- median is Minimal)
```

The distribution clusters heavily below 1.0, with a long tail toward
the Sunsoft-style boundary. The family's center of gravity is around
0.5-1.0 CC11/note: one volume write per note, the platonic ideal of
Minimal.

## Appendix B: Duty Cycle Preferences

| Dominant Duty | Games | Character |
|---------------|-------|-----------|
| 12.5% | Mega Man 2, Trojan, Section Z, Castlevania II/III traces | Thin, nasal, buzzy. The narrowest pulse. |
| 25% | Bionic Commando, Ghosts'n Goblins, Castlevania 2, Gradius | Bright, punchy, clear. Classic NES "lead" sound. |
| 50% | Dragon Warrior, DuckTales, W&W, Metal Gear, Faxanadu, Legendary Wings, Goonies II, Marble Madness, Punch-Out, 1942 | Full, warm, hollow. The most popular choice. |
| 75% | Mega Man 1, Strider | Hollow, slightly darker than 25%. Mathematically related to 25% (inverted). |

50% duty dominates the Minimal family (10 of 25 games). This makes
sense: the 50% square wave has the simplest harmonic series (only odd
harmonics) and the fullest tone of the four options. When you can only
pick one timbre for an entire soundtrack, you pick the one that sounds
the most complete.

## Appendix C: Quick Reference Card

```
MINIMAL DRIVER FAMILY
=====================
Identification: CC11/note < 3.0, CC12/note < 0.5
Games: 25 in survey (likely 200+ in full NES library)
Peak years: 1986-1989
Dominant developer: Capcom (40% of family)

Extraction: NSF pipeline, fully automated
ReapNES mode: CC or ADSR (both work)
Fidelity risk: Low (except Contra and W&W -- check trace)
REAPER project: generate_project.py --nes-native

Sound: Clean, bright, transparent. No envelope shaping.
Musical character: Composition-dependent. All expression
  from note placement, duration, and pitch.

Best examples: DuckTales, Mega Man 2, Dragon Warrior
Curiosities: Gradius (26.2 mean, Minimal median),
  Contra (NSF says Minimal, trace says Dense)
```

---

*"Simplicity is the ultimate sophistication." -- Leonardo da Vinci,
who never heard a square wave but would have understood immediately.*
