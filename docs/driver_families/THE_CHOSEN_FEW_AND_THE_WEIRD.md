# The Chosen Few and the Weird

## Family 5: Konami Full Animation, the Lonely Peak, and the Games That Refuse to Be Classified

---

*In which we meet the only game in the NES library that does everything
at once, and then meet the games that broke our taxonomy entirely.*

---

## Part I: SMB3 -- The Only One

### A Family of One

Out of 65 NES games surveyed, 64 of them fall into four tidy families.
And then there is Super Mario Bros. 3.

| Metric | SMB3 | Next Closest (SMB1) | Family 4 Leader (FF1) |
|--------|------|---------------------|-----------------------|
| CC11/note | 7.7 | 4.9 | 14.9 |
| CC12/note | **1.3** | 0.8 | 0.0 |
| Songs extracted | 60 | 19 | 23 |
| Total notes | 15,875 | 15,510 | 13,889 |
| Dominant duty | 12.5% | 50% | 12.5% |
| Duty distribution | 9805/7211/2675/1 | 481/476/450/? | Nearly all 12.5% |
| Noise coverage | 40% | 33% | 0% |

What makes SMB3 unique is not that its volume automation is the densest
(Final Fantasy holds that crown at 14.9 CC11/note). What makes it unique
is the **combination**: high-density volume automation (7.7) AND
high-density duty cycle animation (1.3). It is the only game in the
entire survey where both numbers cross their respective thresholds
simultaneously.

Family 3 (the Capcom Duty Switchers) has games with CC12 values of
0.7-1.0. Family 4 (the Dense Automators) has games with CC11 values
of 5.1-14.9. SMB3 sits in the overlap of both territories and nobody
else is there with it.

It is a family of one. The loneliest peak in the NES landscape.

### What Does Full Animation Actually Sound Like?

To understand why this matters, think about what each CC stream
controls on the NES APU:

- **CC11 (volume)** controls the 4-bit amplitude of the pulse wave.
  A note with 5+ CC11 events per note has a sculpted volume contour:
  sharp attack, shaped decay, possibly a sustain plateau, then release.
  The note breathes.

- **CC12 (duty cycle)** controls the waveform shape. The NES pulse
  channels have four duty settings:

  | Duty value | Waveform width | Character |
  |------------|---------------|-----------|
  | 0 (12.5%) | Narrow spike | Thin, nasal, buzzy |
  | 1 (25%) | Quarter wave | Bright, classic chiptune |
  | 2 (50%) | Square wave | Full, warm, hollow |
  | 3 (75%) | Inverted 25% | Identical to 25% but inverted phase |

  When duty changes during a note, the timbre shifts in real time.
  A note can start bright (25%) and mellow into warmth (50%). Or
  start thin (12.5%) and fatten up. The note transforms.

Most NES games pick ONE of these things to animate. Sunsoft-style
games (Family 2) animate volume and leave duty static -- you get
punchy notes with a fixed timbre. Capcom Duty Switchers (Family 3)
animate both, but modestly -- a CC12/note of 0.7-1.0 means roughly
one duty change per note. Enough for an attack/sustain timbral shift,
not enough for continuous timbral motion.

SMB3 at CC12=1.3 does not sound radically different from a Family 3
game to a casual listener. The difference is in the *density* and
*coordination*. In SMB3, the duty changes are synchronized with the
volume changes frame by frame. When the volume ramps up during an
attack, the duty may simultaneously shift from 12.5% to 25%. When the
note sustains, the duty may settle back. The result is that each note
has a unified timbral-dynamic envelope -- not just a volume shape
sitting on top of a static waveform, but a coordinated evolution of
both dimensions simultaneously.

Think of it this way:

| Family | Analogy |
|--------|---------|
| Family 1 (Minimal) | A singer who holds one note at one volume |
| Family 2 (Sunsoft) | A singer with good dynamics but one vocal color |
| Family 3 (Duty Switchers) | A singer who shifts tone color at phrase boundaries |
| Family 4 (Dense) | A singer with incredible dynamic range but one tone |
| **Family 5 (Full Animation)** | **A singer who simultaneously controls dynamics AND vocal timbre, per syllable** |

That last one is Koji Kondo in SMB3.

### SMB3's Duty Distribution Tells a Story

Look at the raw duty numbers:

| Duty | Count | Percentage |
|------|-------|------------|
| 12.5% (thin) | 9,805 | 49.8% |
| 25% (bright) | 7,211 | 36.6% |
| 50% (warm) | 2,675 | 13.6% |
| 75% (inverted) | 1 | 0.005% |

Nearly half of all duty values are 12.5% -- the thinnest, most nasal
setting. This is unusual. Most NES games park on 25% or 50% as their
default. SMB3 uses the thin pulse as its home base and then shifts UP
to brighter/warmer settings for emphasis.

This is an inverted approach. Where other games start warm and get
brighter for attacks, SMB3 starts thin and gets fuller. The result is
a distinctive sound: the resting state is buzzy and forward, and
melodic emphasis comes through timbral warming rather than timbral
brightening. It is, frankly, part of why SMB3 has one of the most
recognizable soundtracks on the platform.

That single lonely duty=75% value? Probably a sound effect. Or a
data artifact. Either way, Kondo found everything he needed in three
of the four duty settings and barely touched the fourth.

### Koji Kondo's Arc: From Family 3 to Family 5

This is a composer leveling up his engine between games.

| Game | Year | CC11/note | CC12/note | Family | Total notes |
|------|------|-----------|-----------|--------|-------------|
| Super Mario Bros. | 1985 | 4.9 | 0.8 | 3 (Duty Switchers) | 15,510 |
| Super Mario Bros. 3 | 1988 | 7.7 | 1.3 | 5 (Full Animation) | 15,875 |

Three years between games. In that time:
- Volume density went from 4.9 to 7.7 (a 57% increase)
- Duty density went from 0.8 to 1.3 (a 63% increase)
- Note count stayed roughly constant (~15,500)
- Bankswitch capability was added (the SMB3 cartridge is bigger)

The note count similarity is interesting. Kondo did not write more
notes -- he wrote the same amount of notes with more *detail per note*.
This is the difference between writing more sentences and writing
better sentences. The musical vocabulary stayed roughly the same size,
but each word became richer.

SMB2 (1988, same year) tells a different story:

| Game | CC11/note | CC12/note | Family |
|------|-----------|-----------|--------|
| Super Mario Bros. 2 | 9.7 | 0.3 | 4 (Dense) |

SMB2 has even higher volume density than SMB3 (9.7 vs 7.7) but almost
no duty animation (0.3). SMB2 was originally Doki Doki Panic, a
Fuji Television tie-in game developed by a different team. The sound
engine was not Kondo's. This is a genuine engine fingerprint at work:
same console, same publisher, same year, radically different driver
philosophy.

### The Irony of the Name

The family is called "Konami Full Animation" in our taxonomy. But
the only confirmed member is a Nintendo game. Not Gradius (Konami).
Not Contra (Konami). Not Castlevania (Konami). Super Mario Bros. 3,
by Koji Kondo, for Nintendo.

The name stuck because the *approach* -- per-frame coordinated
volume-and-duty animation -- is what Konami's best engines aspired to
but never quite reached in our survey data. Konami games like
Castlevania 3 JP (CC12=1.0) came closest, but their volume density
(CC11=3.7) stayed in Family 3 territory rather than crossing into
the dense zone.

If the name bugs you, think of it as aspirational rather than
attributive. "Konami Full Animation" is not "Konami made this." It is
"this is what Konami-style engineering looks like when taken to its
logical conclusion." And it took a Nintendo composer to get there.


---


## Part II: The Outliers

### Games That Break the Taxonomy

Our five-family model works for 64 of 65 surveyed games. But within
those families, there are games whose numbers tell strange stories --
games where the data contradicts the classification, where two
extraction methods disagree about reality, or where a famous
composer's fingerprints point somewhere unexpected.

These are the outliers. They are not wrong. The taxonomy is incomplete.

---

### Gradius: The Statistical Lie

#### The Number That Does Not Mean What You Think

Here is Gradius in the survey:

| Metric | Value |
|--------|-------|
| CC11/note | **26.2** |
| CC12/note | 0.2 |
| Classification | **Sparse** |
| Dominant duty | 25% |
| Songs | 32 |
| Total notes | 13,415 |
| Artist | Miki Higashino |
| Developer | Konami |

Read that again. CC11/note of 26.2 -- the highest in the entire survey
by nearly double -- and classified as "sparse." Final Fantasy at 14.9
is classified "dense." Blaster Master at 11.7 is "dense." Gradius at
26.2 is "sparse."

This is not a bug. This is a lesson about statistics.

#### Mean vs. Median: How One Song Can Wreck an Average

The CC11/note metric is an average across all extracted songs. Gradius
has 32 songs. If 30 of those songs have CC11/note around 1.0 (genuinely
sparse, minimal volume automation), and 2 songs have CC11/note of
400+, the average is:

```
(30 * 1.0 + 2 * 400) / 32 = (30 + 800) / 32 = 25.9
```

That is approximately what is happening. Gradius has a handful of songs
-- likely sound effects, demo sequences, or boss themes with extreme
volume modulation -- that pull the mean into the stratosphere while the
median song is simple, gated, minimal-driver output.

The classification algorithm looks at the *median* behavior, not the
mean. The median Gradius song is sparse. The mean is a lie told by
outlier songs.

#### What Konami's Engine Is Actually Doing

Miki Higashino (who would later compose for the Suikoden series)
wrote Gradius on Konami's internal NES sound engine. The engine is
capable of rapid volume modulation -- it can write to $4000/$4004
every frame if the song data tells it to. Most Gradius songs do not
ask for this. A few of them use volume as a special effect:

- **Rapid tremolo**: alternating volume 0/15 at frame rate creates a
  buzzy, ring-modulated texture
- **Echo simulation**: a decaying volume ramp after each note gives
  the illusion of reverb in a system with zero audio memory
- **PCM-like effects**: extremely rapid volume changes can create
  amplitude-modulated waveforms that approximate sampled audio

These are not musical envelopes. These are sound design tricks. The
engine is not shaping notes -- it is abusing the volume register as
a modulation source.

#### The Lesson for the Pipeline

Gradius proves that a single aggregate metric is insufficient for
driver classification. The pipeline needs to look at the *distribution*
of CC11/note across songs, not just the mean. A game with a bimodal
distribution -- most songs sparse, a few songs extreme -- is a
fundamentally different animal from a game where every song is
uniformly dense.

| Statistic | What it captures | Gradius | Final Fantasy |
|-----------|-----------------|---------|---------------|
| Mean CC11/note | Overall density | 26.2 | 14.9 |
| Median CC11/note | Typical song behavior | ~1.0 (est.) | ~14.0 (est.) |
| Max CC11/note | Extreme outlier | 400+ (est.) | ~20 (est.) |
| Distribution shape | Driver character | Bimodal | Unimodal |

Final Fantasy is uniformly dense -- Nasir Gebelli's engine writes
volume every frame for every song. Gradius is occasionally volcanic
and usually dormant. Same number, wildly different musical reality.

---

### Contra: The Fidelity Schism

#### Two Numbers, One Game

| Source | CC11/note | Notes | Classification |
|--------|-----------|-------|----------------|
| NSF rip (original) | 1.5 | 199 | Sparse/Minimal |
| Trace v2 | 7.4 | 4,987 | Dense |
| Trace v5 | 6.1 | 3,909 | Dense |
| Trace v6 | 6.9 | 7,646 | Dense |
| Trace v7 | 6.9 | 7,594 | Dense |
| Trace v8 | 7.1 | 7,496 | Dense |

The NSF rip of Contra produces 199 notes with 1.5 CC11 events per
note. The Mesen trace of the same game running on the same console
produces 4,987-7,646 notes with 6.1-7.4 CC11 events per note.

This is not a small discrepancy. This is a 4.6x difference in volume
density and a 25-38x difference in note count. The NSF says Contra is
a minimal driver. The trace says Contra is a dense automator. They
cannot both be right about the same thing, and in fact they are not
describing the same thing.

#### Why NSF and Trace Disagree

NSF files are extracted from the ROM by isolating the music driver code
and running it through a 6502 CPU emulator. The NSF init routine sets
up the driver, and the NSF play routine advances it one tick. This is
supposed to produce the same audio as the real game.

But "supposed to" is doing a lot of heavy lifting.

Contra's NSF rip captures a **minimal playback mode**. The driver
initializes, plays notes with basic gating (volume on, volume off),
and does not engage the full per-frame envelope system. Why? Possibly:

1. **The NSF init address skips setup code** that the game's main loop
   normally runs before starting music
2. **The driver has a runtime mode flag** (game context vs. NSF
   playback) and the NSF pathway does not set it
3. **The envelope tables live in a bankswitched region** that the NSF
   does not map correctly
4. **The driver reads game state variables** (like stage number or
   boss presence) that affect envelope behavior, and those variables
   are zero in NSF mode

Whatever the cause, the result is devastating for extraction fidelity.
If you only have the NSF, you think Contra is a Family 1 game with
simple gated output. If you have the Mesen trace, you know Contra is
a Family 4 game with dense per-frame envelopes.

This is why the fidelity hierarchy exists:

```
1. Mesen trace (actual APU hardware state)        <-- GROUND TRUTH
2. ROM music data (driver's intended notes)
3. NSF extraction (6502 emulation)                 <-- CAN BE WRONG
4. Frame IR (interpreted musical events)
5. MIDI/CC encoding (downstream projection)
```

NSF is convenience. Trace is truth. Contra proved it.

#### The Konami Engine Spectrum

With trace data, the Konami Contra-family engine reveals itself:

| Game | Source | CC11/note | CC12/note | Notes |
|------|--------|-----------|-----------|-------|
| Contra NSF | NSF | 1.5 | 0.3 | 199 |
| Contra trace (v6-v8 avg) | Trace | 7.0 | 0.1 | ~7,579 |
| Super C | NSF/Trace | 5.2 | 0.1 | 2,038 |
| Castlevania 1 | NSF | 4.3 | 0.2 | 13,121 |
| Castlevania 2 | NSF | 2.8 | 0.6 | 12,446 |
| Castlevania 3 US | NSF | 4.6 | 0.8 | 30,780 |
| Goonies II | NSF | 2.7 | 0.2 | 14,918 |

When the trace is available, Contra is the densest Konami game in the
survey. The engine is clearly capable of sophisticated per-frame
envelopes. The NSF pathway simply does not expose this capability.

This raises an uncomfortable question: **how many other games are
hiding dense automation behind broken NSF rips?**

We do not know. We have trace data for very few games. Every game
whose NSF CC11/note seems surprisingly low is a candidate for
investigation. Goonies II at 2.7, on the same Konami engine family
as Contra, might be another game where the NSF undersells the driver.

#### What This Means for Automated Extraction

Contra's schism puts a crack in the foundation of batch extraction.
The pipeline (`batch_nsf_all.py`) runs every game through NSF
emulation and trusts the output. For most games, this is fine -- the
NSF faithfully reproduces the driver. But for games like Contra, the
pipeline produces an artifact that sounds nothing like the game.

The fix is trace-based extraction for suspected fidelity failures, but
trace extraction requires actually playing the game in Mesen and
recording the APU state. This is manual. This does not batch. This is
the cost of ground truth.

---

### 3D WorldRunner: Uematsu Before Final Fantasy

#### The Composer's Fingerprint

| Metric | 3D WorldRunner | Final Fantasy |
|--------|----------------|---------------|
| Artist | Nobuo Uematsu | Nobuo Uematsu |
| Year | 1987 | 1987 |
| CC11/note | 5.4 | 14.9 |
| CC12/note | 0.0 | 0.0 |
| Dominant duty | **75%** | 12.5% |
| Noise coverage | 88% | 0% |
| Total notes | 7,140 | 13,889 |
| Songs | 8 | 23 |
| Bankswitch | Yes | No |
| Developer | Square | Square |

Same composer. Same developer. Same year. Different engines, different
numbers, different sounds. And that duty cycle: **75%**.

#### The Enigma of 75% Duty

The NES pulse channel's 75% duty setting produces a waveform that is
the phase-inverted version of 25%. In theory, 75% and 25% should sound
identical because human hearing is insensitive to absolute phase.

In practice, they do not always sound identical. The NES DAC has
nonlinearities, and the way the mixer combines pulse channels means
that 75% duty can interact differently with the triangle channel and
the other pulse channel than 25% does. The difference is subtle --
most people cannot hear it in isolation -- but it affects the overall
mix character.

Most NES games avoid 75% duty entirely. Look at the survey: almost
every game parks on 25% or 50%. Using 75% as a dominant duty is
eccentric. It is a choice that says "I tested this and preferred how
it sounded in context," not "I picked the standard setting."

Uematsu used 75% duty for 3D WorldRunner and then abandoned it for
Final Fantasy, where 12.5% dominates. This suggests that the duty
choice was engine-driven (the 3D WorldRunner sound driver defaulted
to 75%) rather than composer-preferred (Uematsu chose 75% because he
liked it). By Final Fantasy, he had a different engine and a different
default.

#### From 5.4 to 14.9: A Volume Density Revolution

In one year, Uematsu's games went from 5.4 CC11/note to 14.9. That is
a 2.76x increase. The engine change between 3D WorldRunner and Final
Fantasy was not incremental -- it was a paradigm shift.

3D WorldRunner at 5.4 CC11/note sits in the borderland between
Family 2 (Sunsoft-style, 3.5-5.6) and Family 4 (Dense, 5.1-15.0).
It has per-frame volume updates, but not every frame. There is room
between the volume writes. The engine is doing envelope table lookups
with moderate resolution.

Final Fantasy at 14.9 CC11/note is writing volume literally every
frame. Every single frame, for every note, the engine updates $4000
and $4004. This is not an envelope table -- this is a continuous
software-controlled volume curve that the CPU computes in real time.
Nasir Gebelli (Square's engine programmer) built one of the most
sophisticated NES sound drivers ever made, and Uematsu composed
specifically for its capabilities.

The gap between the two games tells us that engine capability is the
bottleneck, not composer skill. Uematsu was already writing music that
wanted dense automation in 3D WorldRunner -- the engine just could
not deliver it. When Gebelli gave him an engine that could, the music
immediately exploited the full range.

#### 88% Noise: A Drum-Heavy Composer

3D WorldRunner has 88% noise channel utilization -- 7 of 8 songs use
the noise channel. Final Fantasy has 0%. Zero. Not a single song in
the original Final Fantasy uses the NES noise channel for percussion.

This is fascinating. Uematsu went from "nearly every song has drums"
to "no song has drums" in the span of a single year. The explanation
is genre: 3D WorldRunner is an action game with driving rhythms that
need percussion. Final Fantasy is an RPG with orchestral ambitions
where the noise channel would sound out of place.

But it also reflects engine capability. The Final Fantasy engine uses
the CPU cycles that would go to noise channel management for additional
volume resolution on the melodic channels. Removing drums freed up
processing time for the 14.9 CC11/note density. There is a tradeoff
hiding in the numbers: you can have drums or you can have ultra-dense
melodic envelopes, but the 6502 CPU at 1.79 MHz cannot always give
you both.

#### The Pre-FF Sound: What Could Have Been

3D WorldRunner is Uematsu writing for a lesser engine. The music is
good -- Uematsu was already Uematsu -- but the engine constrains the
expression. The 75% duty gives it a distinctive nasal quality. The 5.4
CC11/note gives notes a moderate envelope but not the lush, orchestral
smoothness of FF1. The 88% noise usage gives it a driving, rhythmic
energy that FF1 deliberately eschews.

If you want to hear what Final Fantasy would have sounded like on a
weaker engine, 3D WorldRunner is the answer. And if you want to hear
what 3D WorldRunner would have sounded like with the FF1 engine... well,
that is what SysEx register replay and engine re-synthesis are for.
The pipeline could, in principle, take the musical content of WorldRunner
and reprocess it through a denser volume resolution. Nobody has asked
for this. But the architecture supports it.

---

### Wizards and Warriors: The Invisible Engine

This is not a formal outlier in the same way as Gradius or Contra, but
it deserves mention as the most extreme case of NSF underrepresentation
in the survey.

| Source | CC11/note | CC12/note |
|--------|-----------|-----------|
| NSF | 0.1 | 0.0 |
| Trace | (richer -- not fully quantified) | (richer) |

Rare's engine for Wizards and Warriors produces almost no CC
automation through NSF emulation. The music sounds flat, gated,
lifeless. But the in-game audio -- captured by Mesen trace -- reveals
a more complex driver that the NSF pathway does not trigger.

This is the same pattern as Contra, but more extreme. Contra's NSF
at least produces 1.5 CC11/note. Wizards and Warriors produces 0.1.
The NSF is nearly silent in terms of volume shaping.

---

## Part III: The Missing Family

### Could There Be a Sixth?

The current taxonomy has five families based on the CC11/CC12 plane:

| Family | CC11 range | CC12 range | Members |
|--------|-----------|-----------|---------|
| 1. Minimal | 0.1-2.8 | 0.0-0.6 | 25 |
| 2. Sunsoft-style | 3.5-5.6 | <0.5 | 18 |
| 3. Capcom Duty Switchers | 3.7-4.9 | 0.7-1.3 | 5 |
| 4. Dense Automators | 5.1-15.0 | <0.5 | 16 |
| 5. Konami Full Animation | >6.0 | >1.0 | 1 |
| (Unclassified) | varies | varies | 16 |

Those 16 unclassified games are the prime candidates for a sixth
family. Look at their characteristics:

| Game | CC11/note | CC12/note | Developer |
|------|-----------|-----------|-----------|
| Journey to Silius | 7.8 | 0.3 | Sunsoft |
| Blaster Master | 11.7 | 0.2 | Sunsoft |
| Final Fantasy | 14.9 | 0.0 | Square |
| Ultima: Exodus | 9.0 | 0.2 | Origin/Pony Canyon |
| Kid Icarus | 5.1 | 0.2 | Nintendo R&D1 |
| Metroid | 5.1 | 0.0 | Nintendo R&D1 |
| Contra (trace) | 6.9 | 0.1 | Konami |
| Super Mario Bros. 2 | 9.7 | 0.3 | Nintendo EAD (Doki Doki) |
| 3D WorldRunner | 5.4 | 0.0 | Square |
| Batman | 7.9 | 0.1 | Sunsoft |
| Super C | 5.2 | 0.1 | Konami |
| Ninja Gaiden II | 10.5 | 0.0 | Tecmo |

These games have CC11/note values ranging from 5.1 to 14.9, but their
CC12/note values are uniformly low (0.0-0.3). They are "Dense
Automators" -- but that is currently just a catchall, not a coherent
engine family. Could there be structure within the unclassified group?

#### The Nintendo R&D1 Cluster

Kid Icarus (5.1) and Metroid (5.1) have identical CC11/note values and
were both developed by Nintendo R&D1 (Gunpei Yokoi's team). Same
developer, same engine, same numbers. Hip Tanaka composed both
soundtracks. This is almost certainly a single engine appearing twice.

| Game | CC11 | CC12 | Year | Composer |
|------|------|------|------|----------|
| Kid Icarus | 5.1 | 0.2 | 1986 | Hip Tanaka |
| Metroid | 5.1 | 0.0 | 1986 | Hip Tanaka |

**Candidate Family 6a: Nintendo R&D1 engine.** Moderate density
(~5.1), no duty animation, atmospheric sound design. If we surveyed
more R&D1 games (Wrecking Crew, Balloon Fight, etc.), we might find
a cluster.

#### The Sunsoft Supercluster

Journey to Silius (7.8), Blaster Master (11.7), and Batman (7.9) are
all Sunsoft games. They share the same Init=$8003, Play=$8000 NSF
address pattern. But their CC11/note values vary significantly:

| Game | CC11 | CC12 | Year |
|------|------|------|------|
| Journey to Silius | 7.8 | 0.3 | 1990 |
| Batman | 7.9 | 0.1 | 1989 |
| Blaster Master | 11.7 | 0.2 | 1988 |

Blaster Master is substantially denser than the other two despite being
the oldest. This could reflect different engine versions, different
composer preferences, or different CPU budget allocation. Either way,
these three games represent a "Sunsoft Dense" sub-family that is
distinct from the "Sunsoft-style" Family 2 games (Castlevania at 4.3,
Gargoyle's Quest II at 4.8).

**Candidate Family 6b: Sunsoft Dense engine.** High density (7.8-11.7),
no duty animation, aggressive bass tones, strong identity. The famous
"Sunsoft bass" sound that NES enthusiasts love is a direct product of
this engine's per-frame volume resolution.

#### The Missing 1577

We have surveyed 65 games out of 1,577 available on joshw's NSF
archive. That is 4.1% coverage. The odds that we have discovered every
driver family are approximately zero.

Candidates for undiscovered families:

- **Namco internal engine** (used in Pac-Man, Galaga NES ports) --
  possibly a minimal driver with hardware-specific tricks
- **Jaleco/TOSE engine** (used in dozens of budget games) -- unknown
  characteristics, possibly a distinct minimal variant
- **Expansion chip engines** (VRC6, VRC7, FDS, N163, Sunsoft 5B) --
  these add extra sound channels with different capabilities and
  likely have their own automation profiles
- **Late-era engines** (1993-1994 games) -- the NES was still receiving
  games in its twilight years, and late engines may have been more
  sophisticated than early ones

The missing 1,512 games are the largest gap in the survey. Every one
of them might belong to a known family. Or one of them might be the
second member of Family 5.

---

## Part IV: Implications for the Pipeline

### What Outliers Mean for Automated Extraction

The outliers teach three uncomfortable lessons:

#### Lesson 1: NSF Is Not Always Truth

Contra and Wizards and Warriors prove that NSF emulation can produce
a fundamentally different result from in-game playback. The batch
pipeline (`batch_nsf_all.py`) trusts NSF. For these games, that trust
is misplaced.

**Pipeline impact:** Any game where NSF CC11/note is suspiciously low
(below 2.0 for a known-capable engine family like Konami) should be
flagged for trace investigation. The pipeline should output a
"fidelity confidence" score alongside each extraction.

#### Lesson 2: Aggregate Metrics Lie

Gradius proves that mean CC11/note can be wildly misleading. A game
with 30 sparse songs and 2 extreme songs looks "dense" in aggregate.

**Pipeline impact:** The driver survey should report median, mean,
min, max, and standard deviation per game, not just mean. A game with
high standard deviation needs per-song classification, not per-game.

#### Lesson 3: The Same Composer Sounds Different on Different Engines

Uematsu sounds radically different on the 3D WorldRunner engine (5.4,
75% duty, 88% noise) vs. the Final Fantasy engine (14.9, 12.5% duty,
0% noise). Kondo sounds different on the SMB1 engine (4.9/0.8) vs.
the SMB3 engine (7.7/1.3). The engine shapes the music at least as
much as the composer.

**Pipeline impact:** Per-game extraction profiles must be
engine-specific, not composer-specific. Knowing that a game is "by
Uematsu" tells you nothing about extraction parameters. Knowing that
a game uses "Square engine v2" tells you everything.

### The Extraction Decision Tree for Outliers

```
Is this game an outlier?
|
+-- Is NSF CC11/note < 2.0 for a game from Konami, Sunsoft, or Tecmo?
|   +-- YES --> Suspect NSF fidelity failure. Get Mesen trace.
|   +-- NO  --> NSF probably faithful.
|
+-- Is mean CC11/note > 3x median CC11/note?
|   +-- YES --> Bimodal distribution. Classify per-song, not per-game.
|   +-- NO  --> Unimodal. Aggregate classification is valid.
|
+-- Is CC12/note > 0.5 AND CC11/note > 6.0?
|   +-- YES --> Family 5. Use SysEx register replay for maximum fidelity.
|   +-- NO  --> Not Full Animation. CC-driven mode is sufficient.
|
+-- Does this game exist in both NSF and trace versions?
    +-- YES --> Compare. If they disagree, trace wins.
    +-- NO  --> Accept NSF with noted confidence level.
```

### The SysEx Advantage for Full Animation Games

For Family 5 games (currently just SMB3), CC-driven MIDI playback
loses information. Here is what each encoding layer captures:

| Capability | SysEx replay | CC11+CC12 | CC11 only | ADSR |
|------------|:----:|:----:|:----:|:----:|
| Exact volume per frame | Yes | Yes | Yes | No |
| Exact duty per frame | Yes | Yes | No | No |
| Sweep unit modulation | Yes | No | No | No |
| Phase reset on note | Yes | No | No | No |
| Noise mode bit | Yes | No | No | No |
| Sub-semitone pitch | Yes | No | No | No |
| Synchronized vol+duty | Yes | Mostly | No | No |

For Family 1-2 games, where duty is static and volume is simple,
CC11-only mode is perfectly adequate. For Family 3 games, CC11+CC12
captures the essential timbral animation. For Family 4 games, CC11
mode works but SysEx captures sweep and sub-semitone detail.

For Family 5, SysEx is the only encoding that preserves the full
coordinated animation without quantization loss. This is the ReapNES
synth's Priority 1 input cascade at work: when SysEx data is
available, it bypasses all MIDI encoding and replays the raw APU
register state. For SMB3, this is the difference between a faithful
reproduction and a very good approximation.

---

## Part V: The Scoreboard

### All Outlier Games, Ranked by Weirdness

| Rank | Game | Why It Is Weird | Weirdness Factor |
|------|------|----------------|-----------------|
| 1 | Gradius | 26.2 CC11/note but classified "sparse" -- statistics ate itself | Extreme |
| 2 | Contra | 4.6x fidelity discrepancy between NSF and trace | Extreme |
| 3 | Super Mario Bros. 3 | Only game in a family of one; Nintendo game named after Konami | High |
| 4 | 3D WorldRunner | Uematsu's pre-FF fingerprint; 75% duty dominant; 88% noise | High |
| 5 | Wizards and Warriors | 0.1 CC11/note from NSF; trace reveals hidden complexity | Moderate |
| 6 | Final Fantasy | 14.9 CC11/note with 0% noise; the anti-drum RPG engine | Moderate |
| 7 | Ninja Gaiden II | 10.5 CC11/note with 75% duty; Tecmo's dense outlier | Moderate |
| 8 | Blaster Master | 11.7 in 1988; denser than Sunsoft's later games | Low |

### The Full Animation Leaderboard (CC11 x CC12)

If we multiply CC11/note by CC12/note to get a "total animation score,"
the ranking shakes out like this:

| Rank | Game | CC11 | CC12 | Score (CC11 x CC12) | Family |
|------|------|------|------|---------------------|--------|
| 1 | **Super Mario Bros. 3** | 7.7 | 1.3 | **10.01** | 5 |
| 2 | Gradius | 26.2 | 0.2 | 5.24 | 1 (misclassified?) |
| 3 | Castlevania 3 US | 4.6 | 0.8 | 3.68 | 3 |
| 4 | Super Mario Bros. | 4.9 | 0.8 | 3.92 | 3 |
| 5 | Castlevania 3 JP | 3.7 | 1.0 | 3.70 | 3 |
| 6 | Super Mario Bros. v2 | 4.8 | 0.8 | 3.84 | 3 |
| 7 | Super Mario Bros. 2 | 9.7 | 0.3 | 2.91 | 4 |
| 8 | Kirby's Adventure | 3.7 | 0.7 | 2.59 | 3 |

SMB3 is not just first -- it is nearly double the runner-up. (And the
runner-up is Gradius, whose score is inflated by the mean-vs-median
statistical artifact discussed above.) Among games with honest numbers,
SMB3 leads by a factor of 2.5x.

Koji Kondo's SMB3 engine stands alone.

---

## Appendix: Quick Reference

### Family Classification Cheat Sheet

```
CC12/note
  ^
  |
1.3+  .  .  .  .  .  .  . [SMB3] .  .  .  .  .  .  .  .
  |                           |
1.0+  .  .  . [CV3JP] .  .  |  .  .  .  .  .  .  .  .  .
  |              |            |
0.8+  .  . [Kirby]--[SMB1]  |  .  .  .  .  .  .  .  .  .
  |     FAMILY 3  [CV3US]    |
0.5+  .  .  .  .  .  .  .  .|  .  .  .  .  .  .  .  .  .
  |                          .|
0.3+  .  .  .  .  .  .  .  . |. [SMB2] . [FFFF?] .  .  .
  |                           |              |
0.1+  [DW]--[MM2]---[CV1]--[BT]---[JtS]--[BM]-----[FF] .
  |     FAMILY 1    FAMILY 2  |    FAMILY 4    (Dense)
  +---+----+----+----+----+---+----+----+----+----+----+-->
  0   1    2    3    4    5   6    7    8    9   10   15
                                                CC11/note
```

### Key Abbreviations

| Abbrev. | Game |
|---------|------|
| SMB1/2/3 | Super Mario Bros. 1/2/3 |
| CV1/3 | Castlevania 1/3 |
| CV3JP | Castlevania 3 Japanese |
| DW | Dragon Warrior |
| MM2 | Mega Man 2 |
| BT | Battletoads |
| JtS | Journey to Silius |
| BM | Blaster Master |
| FF | Final Fantasy |
| 3DWR | 3D WorldRunner |

---

*65 games surveyed. 5 families defined. 1 game standing alone at the top.
And at least 1,512 more games waiting to be measured.*

*The weird ones are always the most interesting.*
