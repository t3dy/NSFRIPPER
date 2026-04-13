# Every Frame Is Sacred

## The Dense Automators: 16 NES Games That Refused to Let the Hardware Do Its Job

*A deep dive into the most obsessive-compulsive family of NES music drivers ever written.*

---

Most NES music drivers are polite. They set a volume, play a note, maybe
update the volume a couple of times during the note's life, and move on.
They trust the hardware. They delegate.

The Dense Automators do not delegate. They do not trust. They write a
fresh volume value to the APU registers on nearly *every single frame* of
audio. Sixty times a second, for every note, on every channel, the CPU
marches over to the APU and says: "Here is your volume. Yes, I know I told
you a sixtieth of a second ago. I'm telling you again. Deal with it."

This is the story of 16 games whose sound engines treated the NES APU
like a puppet on very short strings.

---

## 1. The Family Roster

The Dense Automators are defined by a single metric: **CC11 events per
note** between 5.1 and 15.0. In our survey of 65 NES games, this puts
them firmly in the top tier of envelope sophistication -- well above the
Sunsoft-style lookup table drivers (3.5-5.6) and in a completely different
universe from the Minimal drivers that populate early Capcom and Enix
titles (0.1-2.8).

Here they are, ranked by obsessiveness:

| Rank | Game | Developer | CC11/note | CC12/note | Songs | Notes | Duty | Noise |
|------|------|-----------|-----------|-----------|-------|-------|------|-------|
| 1 | Final Fantasy | Square (Nasir Gebelli) | **14.9** | 0.0 | 23 | 13,889 | 12.5% | N |
| 2 | Blaster Master | Sunsoft | **11.7** | 0.2 | 16 | 17,993 | 50% | Y |
| 3 | Ninja Gaiden II | Tecmo | **10.5** | 0.0 | 1* | 1,464 | 75% | Y |
| 4 | Super Mario Bros. 2 | Nintendo R&D4 | **9.7** | 0.3 | 24 | 7,153 | 25% | Y |
| 5 | Ultima: Exodus | FCI / Origin | **9.0** | 0.2 | 11 | 10,217 | 25% | N |
| 6 | Batman | Sunsoft | **7.9** | 0.1 | 3* | 3,498 | 25% | Y |
| 7 | Journey to Silius | Sunsoft | **7.8** | 0.3 | 12 | 22,137 | 25% | Y |
| 8 | Super Mario Bros. 3 | Nintendo R&D4 | **7.7** | 1.3 | 60 | 15,875 | 12.5% | Y |
| 9 | Contra (trace v2) | Konami | **7.4** | 0.1 | 11 | 4,987 | 12.5% | N |
| 10 | Contra (trace v8) | Konami | **7.1** | 0.1 | 11 | 7,496 | 12.5% | Y |
| 11 | Contra (trace v6) | Konami | **6.9** | 0.1 | 11 | 7,646 | 12.5% | Y |
| 12 | Contra (trace v7) | Konami | **6.9** | 0.1 | 11 | 7,594 | 12.5% | Y |
| 13 | Contra (trace v5) | Konami | **6.1** | 0.0 | 3 | 3,909 | 12.5% | Y |
| 14 | 3-D WorldRunner | Square (Nobuo Uematsu) | **5.4** | 0.0 | 8 | 7,140 | 75% | Y |
| 15 | Super C | Konami | **5.2** | 0.1 | 9 | 2,038 | 12.5% | Y |
| 16 | Kid Icarus | Nintendo R&D1 | **5.1** | 0.2 | 28 | 9,850 | 50% | Y |
| 17 | Metroid | Nintendo R&D1 | **5.1** | 0.0 | 11 | 9,423 | 50% | Y |

*\*Partial extraction -- not all songs surveyed yet.*

**Composers represented:** Nobuo Uematsu (Final Fantasy, 3-D WorldRunner),
Naoki Kodaka (Blaster Master, Journey to Silius, Batman), Koji Kondo
(SMB2, SMB3), Hirokazu "Hip" Tanaka (Kid Icarus, Metroid), and the
uncredited Konami sound team (Contra, Super C).

**Total notes across the family:** ~148,000+

**Total songs:** ~200+

That is a *lot* of volume automation.

---

## 2. What "Dense Automation" Actually Means

### The NES APU in 30 Seconds

The NES Audio Processing Unit has four channels: two pulse waves, one
triangle wave, and one noise channel. Each pulse channel has a 4-bit
volume register (values 0-15). The CPU can write to this register
whenever it wants.

The NES runs at approximately 60 frames per second (60.0988 Hz NTSC).
Most music drivers execute once per frame, during the vertical blank
interrupt. Each execution is an opportunity to update the APU registers.

### What the Numbers Mean

When we say Final Fantasy has a CC11/note ratio of **14.9**, here is
what that means in concrete terms:

- The NES runs at ~60 fps
- A typical note lasts maybe 6-20 frames (100-333ms)
- For a 15-frame note, 14.9 CC11/note means the driver writes a volume
  value on **every single frame** and then some (the "and then some"
  comes from notes that are shorter than average, driving the ratio above
  1.0 per frame)
- The driver never skips a beat. It never says "eh, same volume as last
  frame, I'll save the bus cycle." It writes. Every. Frame.

By contrast, Castlevania 1 (the quintessential Sunsoft-style driver)
clocks in at 4.3 CC11/note. That means roughly one volume update every
3-4 frames per note. Still shaped, still musical, but the driver is
being selective about when to bother the APU.

And Dragon Warrior? 0.1 CC11/note. That driver sets the volume once and
then goes to take a nap.

### Hardware Envelopes vs. Software Envelopes

The NES APU does have a built-in hardware envelope generator. You can
configure it to do a simple linear decay from volume 15 down to 0. It is
... fine. It is the kind of envelope a hardware engineer designs when
nobody on the team has opinions about music.

The Dense Automators completely ignore this hardware feature. They
disable the hardware decay (by setting the "constant volume" flag in
register $4000/$4004) and then proceed to manually write every single
volume value themselves. The CPU becomes the envelope generator.

Why would you do this? Because the hardware envelope is a one-trick
pony: linear decay at a fixed rate. Software envelopes can do anything:

- **Attack-sustain-decay** with arbitrary curve shapes
- **Tremolo** (periodic volume oscillation)
- **Echo simulation** (volume re-attack after a gap)
- **Per-instrument envelopes** (strings decay differently than brass)
- **Dynamic response** (volume tied to game state, not just note data)
- **Crescendo and decrescendo** (gradual volume changes across phrases)

The Dense Automators are, in essence, running a tiny software synthesizer
inside the NES, using the APU as nothing more than a dumb DAC for
square waves.

### The Frame Budget Problem

Here is the catch: writing to APU registers costs CPU cycles. At 60 fps
on a 1.79 MHz processor, you have about 29,780 cycles per frame. The
music driver shares this budget with everything else: game logic,
physics, sprite rendering, input polling, and the existential dread of
being a video game in 1987.

A single APU register write is cheap (6-8 cycles for a STA instruction).
But when you multiply that across 4 channels, add the envelope
calculation logic, the note sequencing, the tempo management, and the
pointer chasing through song data, the music driver for a Dense
Automator game might eat 5-10% of the total CPU budget.

For Final Fantasy at 14.9 CC11/note, Nasir Gebelli's engine is spending
a *remarkable* amount of the frame doing nothing but sculpting sound.
Every frame. For the entire game. On a CPU that also needs to render
a JRPG.

---

## 3. What It Sounds Like

### The Sonic Signature

You can hear a Dense Automator game without looking at the data. The
telltale signs:

**Smooth volume curves.** Where Minimal drivers produce clean, blocky
square waves that go ON and then OFF, Dense Automators produce notes
that breathe. Volume ramps up during attack, sustains at a controlled
level, and decays gracefully. The result sounds less like a computer
and more like an instrument.

**Echo and reverb simulation.** Several Dense Automator engines (notably
Sunsoft's) use the per-frame volume control to create fake echo effects.
A note plays at full volume, decays, then the volume briefly rises again
to simulate a reflection. This is why Journey to Silius sounds like it
was recorded in a concert hall and not inside a grey plastic rectangle.

**Rich bass tones.** The triangle channel on the NES has no volume control
-- it is either on or off. But Dense Automator engines work around this
by manipulating the triangle's gate timing with extreme precision. The
result is bass that feels weighty and articulated, not just a
monotone hum.

**Orchestral ambition.** Games in this family tend to sound like they are
*trying* to be more than chiptunes. Final Fantasy's prelude arpeggio,
Batman's Stage 1 theme, Journey to Silius's entire soundtrack -- these
all sound like compositions that were written for a full ensemble and
then painstakingly transcribed to four channels of beepy hardware.

### The Uncanny Valley of Chiptunes

There is an interesting aesthetic tension here. Minimal drivers like
Mega Man 2 sound undeniably like a NES. That is part of their charm.
The blocky, unadorned square waves are iconic.

Dense Automators sometimes land in a strange middle ground: too
sophisticated to sound like "classic NES" but too limited by the
hardware to sound like real instruments. They are reaching for something
the hardware cannot quite deliver. When it works (Journey to Silius,
Batman, Final Fantasy), the result is transcendent. When it doesn't quite
land, it can sound slightly uncanny -- like a music box trying to play
a symphony.

---

## 4. How to Recognize a Dense Automator

If you are extracting NES music and want to quickly identify whether you
are dealing with a Dense Automator, here is the field guide:

### In the MIDI File

| Indicator | What you see | What it means |
|-----------|-------------|---------------|
| CC11 event count | Thousands to tens of thousands | Volume is being written every frame |
| CC11/note ratio | 5.0+ | Dense automation confirmed |
| File size | 50-200 KB per song | All that CC data adds up |
| CC11 value distribution | Smooth gradients, not just 0 and 127 | Software envelope, not on/off gating |
| CC12 events | Usually low (0.0-0.3) | Dense automators invest in volume, not duty |

### In the NSF Metadata

| Indicator | What to check | Dense Automator signature |
|-----------|--------------|--------------------------|
| Init/Play addresses | Varies by developer | See per-developer patterns below |
| Bankswitch | Mixed | Not a reliable indicator |
| Frame timing | Always 60 Hz NTSC | No surprises here |

### Developer Fingerprints

| Developer | Init Pattern | CC11/note Range | Calling Card |
|-----------|-------------|-----------------|--------------|
| Square (Gebelli) | Init=$FFD2, Play=$B000 | 5.4-14.9 | Extreme density, no noise, no duty changes |
| Sunsoft (Kodaka) | Init=$8003/$8013, Play=$8000/$8077 | 7.8-11.7 | Famous bass, echo effects |
| Nintendo R&D1 (Tanaka) | Init=$E000/$A000 | 5.1 | Atmospheric, minimal noise |
| Nintendo R&D4 (Kondo) | Init=$8800/$9000 | 7.7-9.7 | Melodic, balanced, wide duty spread |
| Konami (trace) | N/A (trace-derived) | 6.1-7.4 | 12.5% duty lock, aggressive |
| Tecmo | Init=$BDD0 | 10.5 | Cinematic, 75% duty preference |

---

## 5. Extraction Tips for Dense Automators

### The Good News

Dense Automator games are often the *easiest* to get right through NSF
extraction. Why? Because the driver is doing all the work in software.
The NSF emulator runs the same 6502 code, the same driver writes the
same volume values to the same registers at the same time. What you
capture is what the game plays.

This is the opposite of Minimal drivers, where the driver delegates to
hardware envelopes that the NSF emulator may or may not reproduce
faithfully.

### The Bad News: File Size

A typical Dense Automator MIDI file is 3-10x larger than an equivalent
Minimal driver MIDI:

| Game | Songs | Total Notes | Estimated CC11 Events | MIDI Size Impact |
|------|-------|-------------|----------------------|-----------------|
| Final Fantasy | 23 | 13,889 | ~207,000 | Massive |
| Blaster Master | 16 | 17,993 | ~210,000 | Massive |
| Journey to Silius | 12 | 22,137 | ~172,000 | Large |
| Kid Icarus | 28 | 9,850 | ~50,000 | Moderate |
| Dragon Warrior (for comparison) | 47 | 12,146 | ~1,200 | Tiny |

That is not a typo. Final Fantasy generates roughly **170x more CC11
events** than Dragon Warrior for a comparable number of notes. Your MIDI
files will be chunky. Your REAPER projects will have dense automation
lanes. Plan accordingly.

### The Ugly News: Quantization Artifacts

When Dense Automator CC11 data gets quantized during MIDI encoding (the
NES uses 4-bit volume, 0-15, but MIDI CC uses 7-bit, 0-127), there is
potential for rounding artifacts. The mapping:

```
NES volume 0  -> MIDI CC11 0
NES volume 1  -> MIDI CC11 8
NES volume 2  -> MIDI CC11 17
...
NES volume 15 -> MIDI CC11 127
```

This is a lossy mapping. When the synth converts back (MIDI CC11 to NES
volume via `floor(cc * 15 / 127)`), values that fall between the 16
canonical levels can produce volume "wobble" -- tiny fluctuations that
were not in the original. With 14.9 CC11 events per note, even a tiny
wobble compounds into audible stepping artifacts.

**Mitigation:** The SysEx register replay route (Priority 1 in the
ReapNES synth) bypasses this entirely by sending raw 4-bit APU register
values. For Dense Automator games, SysEx is the clearly superior route.

### Practical Extraction Checklist

```
[ ] Run driver_survey.py to confirm CC11/note > 5.0
[ ] Extract via NSF pipeline (fetch_and_extract.py)
[ ] Check MIDI file sizes -- expect 50-200 KB per song
[ ] Generate both CC route and SysEx route via kitchen_sink.py
[ ] Compare SysEx playback to CC playback
[ ] Listen for volume stepping artifacts in CC route
[ ] If stepping is audible, prefer SysEx route for final output
[ ] Expect large REAPER projects with dense automation lanes
```

---

## 6. The Final Fantasy Phenomenon

### 14.9 CC11/note. What Was Nasir Gebelli Doing?

Nasir Gebelli is one of the most fascinating figures in early game
development. An Iranian-American programmer who had already made a name
for himself writing Apple II games in the early 1980s, he was recruited
by Hironobu Sakaguchi to program the original Final Fantasy for the NES.

His sound engine is, by our measurements, the most obsessively automated
music driver in the entire NES library (among surveyed games). At 14.9
CC11 events per note, it is:

- **1.3x** denser than the next contender (Blaster Master at 11.7)
- **3.4x** denser than the Castlevania 1 engine (4.3)
- **149x** denser than Dragon Warrior (0.1)

The music for Final Fantasy was composed by Nobuo Uematsu, who would
go on to become one of the most celebrated video game composers in
history. But Uematsu did not write the sound driver. That was Gebelli's
department. And Gebelli made a sound engine that treated every frame as
a canvas.

### What the Data Shows

Final Fantasy's driver profile is distinctive:

| Attribute | Value | What it means |
|-----------|-------|---------------|
| CC11/note | 14.9 | Volume on literally every frame |
| CC12/note | 0.0 | Duty cycle NEVER changes mid-note |
| Dominant duty | 12.5% | Narrow pulse, bright and thin |
| Noise | None | No percussion channel at all |
| Duty distribution | 12.5% and 25% only | Two timbres, no more |

This is a driver that pours all of its CPU budget into one thing:
volume sculpting. It does not bother with duty animation (0.0 CC12/note).
It does not even use the noise channel for percussion. All four channels
are devoted to melody and harmony, and every frame of every note gets a
hand-crafted volume value.

The result is the smoothest, most dynamically expressive sound on the
NES. The famous Final Fantasy prelude (that cascading arpeggio) sounds
the way it does because each note in the arpeggio has its own volume
envelope, and those envelopes interlock to create a shimmering,
harp-like effect. Without per-frame volume control, it would sound like
a machine gun of beeps. With it, it sounds like music.

### The Uematsu Connection: 3-D WorldRunner

Here is a detail that ties a bow on this: Nobuo Uematsu also composed
the music for 3-D Battles of WorldRunner, a Square game released in
1987 -- the same year as Final Fantasy. WorldRunner's CC11/note ratio
is 5.4, firmly in Dense Automator territory but nowhere near the 14.9
of Final Fantasy.

Both games were developed at Square. The difference? WorldRunner was
an earlier title, likely using an earlier version of the engine. By the
time Final Fantasy shipped, Gebelli had apparently tripled down on the
per-frame automation approach.

The duty preference also shifted: WorldRunner uses 75% duty (warm, fat
pulse), while Final Fantasy uses 12.5% (thin, bright, piercing). Same
composer, same studio, same era, completely different timbral character.
Uematsu adapted his compositions to the engine's strengths.

---

## 7. The Sunsoft Bass Mystery

### Why Do Sunsoft Games Sound So Good?

If you have spent any time in NES music communities, you have heard
people talk about "the Sunsoft bass." Journey to Silius, Blaster Master,
Batman -- these games have bass lines that sound impossibly deep and
rich for NES hardware. People have written forum posts, YouTube videos,
and academic papers trying to explain it.

The answer, it turns out, is in the data: **Sunsoft games are Dense
Automators.**

| Sunsoft Game | CC11/note | Notes | Noise % |
|-------------|-----------|-------|---------|
| Blaster Master | 11.7 | 17,993 | 75% |
| Batman | 7.9 | 3,498 | 100% |
| Journey to Silius | 7.8 | 22,137 | 92% |

All three are well above the Dense Automator threshold. Blaster Master
at 11.7 is the second-densest engine in our entire survey, behind only
Final Fantasy.

### The Naoki Kodaka Factor

All three of these games share a common lineage: Naoki Kodaka. The NSF
metadata for Journey to Silius credits "Nobuyuki, Marumo, N.Kodaka et
al." Blaster Master credits "Naoki Kodaka, Marumo." Batman credits
"Nobuyuki Kun, Kodaka San."

Kodaka's sound engine uses per-frame volume automation to create several
signature effects:

1. **Simulated echo.** After a note's initial attack-decay, the volume
   briefly rises again 4-6 frames later, simulating a room reflection.
   This makes the sound feel "wet" -- like it exists in a physical space
   rather than in a circuit.

2. **Tremolo bass.** On the triangle channel, rapid gate on/off cycling
   at sub-note speeds creates a tremolo effect that gives bass notes a
   pulsing, living quality.

3. **Dynamic attack shaping.** Different instruments (within the
   same pulse channel) get different attack curves. A lead melody note
   might ramp up over 2 frames; a staccato bass hit might slam to full
   volume instantly. This is all controlled by the per-frame volume
   stream.

### Why Blaster Master Is Denser Than Batman

Blaster Master (11.7) clocks almost 50% more CC11/note than Batman
(7.9). This is likely because Blaster Master's soundtrack is more
ambitious in its use of volume effects. The game's overworld theme uses
sustained, evolving pads built entirely from volume-modulated pulse
waves -- a technique that requires constant volume updates to avoid
audible stepping.

Batman, by contrast, is more percussive and rhythm-driven. Its Stage 1
theme (one of the most famous NES tracks ever) gets its energy from note
density and harmonic movement rather than from elaborate volume
envelopes. Faster notes = fewer frames per note = fewer CC11 events
per note, even though the driver is still writing every frame.

The Sunsoft engine appears to be the same driver across all three games
(similar init/play address patterns: $8003/$8000 for Journey to Silius
and Batman, $8013/$8077 for Blaster Master). What changes is how the
composers use it.

---

## 8. The Contra Discrepancy

### 1.5 From NSF. 6.9 From Trace. What?

This is one of the most revealing discoveries in the entire driver
survey, and it casts a long shadow over NSF-based extraction.

Here are the numbers:

| Contra Version | Source | CC11/note | Notes | Songs |
|---------------|--------|-----------|-------|-------|
| Contra (NSF) | NSF emulation | **1.5** | 199 | 2 |
| Contra_v2 | Mesen trace | **7.4** | 4,987 | 11 |
| Contra_v5 | Mesen trace | **6.1** | 3,909 | 3 |
| Contra_v6 | Mesen trace | **6.9** | 7,646 | 11 |
| Contra_v7 | Mesen trace | **6.9** | 7,594 | 11 |
| Contra_v8 | Mesen trace | **7.1** | 7,496 | 11 |

The NSF rip says Contra is a Minimal driver (1.5 CC11/note -- barely
more than on/off gating). The Mesen trace says Contra is a Dense
Automator (6.1-7.4 CC11/note -- full per-frame envelope control).

**Same game. Same Konami sound engine. Completely different behavior
depending on how you observe it.**

### Why This Happens

NSF files are extracted from ROMs by isolating the sound driver code and
the song data. The NSF player initializes the driver and calls its play
routine 60 times per second, just like the NES would. But there is a
subtlety: some engines behave differently depending on context.

Konami's engine for Contra appears to have a **playback mode** that is
simpler when running in isolation (NSF) versus when running inside the
full game (ROM). The game's main loop may pass additional state to the
sound driver -- volume tables, envelope parameters, or trigger flags
that the NSF rip doesn't provide. Without this context, the driver falls
back to a simpler mode: set volume, play note, move on.

This is not a bug in the NSF rip. It is a fundamental limitation of the
NSF format. The NSF specification assumes the sound driver is
self-contained. When it isn't -- when the driver depends on the game to
tell it how to shape sound -- the NSF output is an impoverished version
of what you hear in-game.

### What This Means for Extraction

The Contra discrepancy proves the fidelity hierarchy documented in
CLAUDE.md:

1. **Mesen trace** (actual APU registers during gameplay) -- ground truth
2. **NSF emulation** (driver running in isolation) -- *may diverge*

For Contra specifically, NSF extraction misses approximately **80%** of
the volume automation. If you only use the NSF pipeline, your Contra
MIDI files will sound flat and lifeless compared to the actual game.
The trace pipeline captures the full Dense Automator behavior.

This raises an uncomfortable question: **how many other games in our
survey are Dense Automators in-game but appear as Minimal drivers in
NSF?** Wizards & Warriors (0.1 CC11/note from NSF) is another known
case where trace data tells a richer story. The true number of Dense
Automators in the NES library may be significantly larger than our
survey suggests.

---

## 9. Nintendo's In-House Engines

### Hip Tanaka's Twin Engines: Kid Icarus and Metroid

Both games clock in at exactly **5.1 CC11/note** -- the threshold of
Dense Automator territory. Both were composed by Hirokazu "Hip" Tanaka,
one of Nintendo's in-house composers and sound designers. And both use
a driver that Tanaka likely wrote himself.

| Game | CC11/note | CC12/note | Duty | Noise % | Songs | Notes |
|------|-----------|-----------|------|---------|-------|-------|
| Kid Icarus | 5.1 | 0.2 | 50% | 57% | 28 | 9,850 |
| Metroid | 5.1 | 0.0 | 50% | 18% | 11 | 9,423 |

The identical CC11/note ratio is almost certainly not a coincidence.
These games share a sound engine -- possibly the same binary code, just
with different song data.

The difference is in how Tanaka used it:

- **Kid Icarus** is bright, bouncy, and melodic. 57% noise usage means
  plenty of percussion. Duty distribution includes some 75% values for
  warmer tones.
- **Metroid** is dark, atmospheric, and sparse. Only 18% noise usage --
  Tanaka deliberately suppressed the percussion to create a sense of
  isolation. 0.0 CC12/note means the duty cycle never changes mid-note:
  the timbre is as static and cold as the planet Zebes.

Same engine, same automation density, opposite aesthetic results. The
driver is just a tool. The composer decides what it sounds like.

### Koji Kondo's Evolution: SMB2 and SMB3

Koji Kondo, Nintendo's legendary composer, shows up twice in the Dense
Automator family:

| Game | CC11/note | CC12/note | Duty Spread | Notes |
|------|-----------|-----------|-------------|-------|
| Super Mario Bros. 2 | 9.7 | 0.3 | Even across all 4 | 7,153 |
| Super Mario Bros. 3 | 7.7 | 1.3 | 12.5% dominant | 15,875 |

The story here is one of *trade-offs and maturation*.

**SMB2** invests heavily in volume automation (9.7 CC11/note) but
barely touches duty (0.3 CC12/note). Its duty distribution is remarkably
even: 462/481/476/450 across the four duty cycles. This is a driver that
uses all available timbres but shapes them primarily through volume.

**SMB3** backs off on volume automation (7.7 CC11/note) but **massively**
increases duty switching (1.3 CC12/note -- the highest in our entire
survey). Its duty distribution is wildly skewed: 9,805 events at 12.5%,
7,211 at 25%, 2,675 at 50%, and a single lonely event at 75%.

Kondo's engine evolved between games. In SMB2, he was a volume sculptor.
By SMB3, he had become a timbre animator. The total "envelope investment"
(CC11 + CC12 combined) is similar -- 10.0 for SMB2, 9.0 for SMB3 --
but the budget allocation shifted dramatically.

SMB3 is, in fact, the only game in our entire 65-game survey where
*both* CC11 and CC12 are in Dense Automator territory. It is technically
classified as "Konami Full Animation" (Family 5) in our taxonomy, making
it the single most sophisticated driver we have measured. And it was
written for a game about a plumber in a raccoon suit.

### The Nintendo R&D Division Theory

Looking at the Nintendo entries together:

| Game | Team | Year | CC11/note | CC12/note |
|------|------|------|-----------|-----------|
| Kid Icarus | R&D1 (Tanaka) | 1986 | 5.1 | 0.2 |
| Metroid | R&D1 (Tanaka) | 1986 | 5.1 | 0.0 |
| Super Mario Bros. 2 | R&D4 (Kondo) | 1988 | 9.7 | 0.3 |
| Super Mario Bros. 3 | R&D4 (Kondo) | 1988 | 7.7 | 1.3 |

There is a clear generational jump between the R&D1 games (1986, 5.1
CC11/note) and the R&D4 games (1988, 7.7-9.7 CC11/note). Two possible
explanations:

1. **Engine maturity.** By 1988, Nintendo's sound engine technology had
   simply gotten better. More CPU budget available, more optimized code,
   more sophisticated envelope algorithms.

2. **Different teams, different priorities.** R&D1 under Gunpei Yokoi had
   a hardware-engineering mindset; their driver is efficient and
   restrained. R&D4 under Shigeru Miyamoto was all about player
   experience; their driver spends CPU like it is going out of style
   because the music needs to *feel* right.

Either way, all four games are Dense Automators. Nintendo's internal
teams, across divisions and across years, consistently chose the
"software does everything" approach. They had the luxury of being
first-party: they knew the hardware intimately, and they spent their CPU
budget accordingly.

---

## 10. The Outliers and Borderline Cases

### Ninja Gaiden II: The 10.5 Enigma

Tecmo's Ninja Gaiden II (The Dark Sword of Chaos) registers at 10.5
CC11/note -- third-densest in the survey. But we only have data from
1 song and 1,464 notes. That is a small sample. The game's NSF file
lists 84 songs total, meaning we have surveyed barely 1% of the
soundtrack.

What we can say: the Tecmo driver uses 75% duty as its dominant pulse
width (warm, hollow tone), has 0.0 CC12/note (no duty switching), and
uses all four channels including noise. The sonic profile is consistent
with the cinematic, dramatic style that Ninja Gaiden II is famous for.

If the full soundtrack maintains the 10.5 ratio, Tecmo's engine belongs
solidly in the top tier of Dense Automators. More extraction needed to
confirm.

### Super C: Konami's Sequel Tax

Super C (the NES port of Super Contra) comes in at 5.2 CC11/note --
just barely over the Dense Automator threshold. Its 9 songs and 2,038
notes suggest a modest soundtrack. Like its predecessor Contra, it uses
12.5% duty exclusively.

Notably, Super C's CC11 density is *lower* than Contra's trace values
(6.1-7.4). This is counterintuitive -- you would expect the sequel to
be at least as sophisticated. But Super C's data comes from a different
extraction version, and the same NSF-vs-trace discrepancy that affects
Contra may be at play here. Super C in-game might be significantly
denser than what we have measured.

### Ultima: Exodus -- The Forgotten RPG

At 9.0 CC11/note, Ultima: Exodus (developed by FCI for the NES port
of the Origin Systems PC game) is the fifth-densest engine in our
survey. It shares an interesting trait with Final Fantasy: **no noise
channel usage at all.** Zero percussion. The entire soundtrack is pure
melodic content with aggressive volume shaping.

The composer, Tsugutoshi Goto, was working with what appears to be a
unique engine (init=$FA10, play=$8100 -- no matches to any other game
in our survey). This is a one-off driver, purpose-built for a single
game, and it is one of the most automated in the library.

---

## 11. The Dense Automator Taxonomy

Not all Dense Automators are created equal. Within the family, we can
identify distinct sub-groups based on how they spend their automation
budget:

### Sub-Group A: Pure Volume Sculptors

*All budget on CC11, none on CC12. The purists.*

| Game | CC11/note | CC12/note | Profile |
|------|-----------|-----------|---------|
| Final Fantasy | 14.9 | 0.0 | Maximum volume, zero duty |
| Ninja Gaiden II | 10.5 | 0.0 | High volume, zero duty |
| Metroid | 5.1 | 0.0 | Moderate volume, zero duty |
| 3-D WorldRunner | 5.4 | 0.0 | Moderate volume, zero duty |
| Contra v5 | 6.1 | 0.0 | Moderate-high volume, zero duty |

These drivers have decided: the only knob worth turning is volume.
Timbre (duty cycle) is set once per note -- or per song -- and left
alone. The expressiveness comes entirely from dynamics.

### Sub-Group B: Volume-Primary With Light Duty

*Heavy CC11, a touch of CC12. The pragmatists.*

| Game | CC11/note | CC12/note | Profile |
|------|-----------|-----------|---------|
| Blaster Master | 11.7 | 0.2 | Heavy volume, light duty |
| Ultima: Exodus | 9.0 | 0.2 | Heavy volume, light duty |
| Batman | 7.9 | 0.1 | Heavy volume, minimal duty |
| Journey to Silius | 7.8 | 0.3 | Heavy volume, light duty |
| Contra v2/v6/v7/v8 | 6.9-7.4 | 0.1 | Heavy volume, minimal duty |
| Super C | 5.2 | 0.1 | Moderate volume, minimal duty |
| Kid Icarus | 5.1 | 0.2 | Moderate volume, light duty |

These drivers mostly sculpt with volume but occasionally switch duty
for specific timbral effects -- perhaps a brighter attack followed by
a warmer sustain, or different duty cycles for different instrument
voices within the same channel.

### Sub-Group C: The Balanced Approach

*Significant investment in both CC11 and CC12.*

| Game | CC11/note | CC12/note | Profile |
|------|-----------|-----------|---------|
| SMB3 | 7.7 | 1.3 | Heavy volume, heavy duty |
| SMB2 | 9.7 | 0.3 | Heavy volume, moderate duty |

Only two games in our survey. Koji Kondo stands alone in the "animate
everything" philosophy. SMB3 in particular is an outlier among outliers:
the only game where duty animation is itself in Dense Automator territory.

---

## 12. Implications for the ReapNES Pipeline

### Route Selection

For Dense Automator games, the pipeline route matters more than for any
other family:

| Route | Fidelity for Dense Automators | Why |
|-------|-------------------------------|-----|
| SysEx (Priority 1) | Excellent | Raw 4-bit APU values, no MIDI quantization loss |
| CC11/CC12 (Priority 2) | Good, with caveats | 7-bit to 4-bit roundtrip can introduce wobble |
| ADSR keyboard (Priority 3) | Poor | Static envelopes cannot reproduce per-frame sculpting |

**ADSR mode is essentially useless for Dense Automator playback.** The
entire point of these drivers is that every note has a unique volume
contour. A static attack-decay-sustain-release curve cannot replicate
that. It would be like trying to reproduce a watercolor painting using
four crayons.

### REAPER Project Considerations

Dense Automator REAPER projects will have:

- **Dense CC automation lanes.** Expect hundreds of automation points per
  channel per song. The automation lane will look like a solid wall of
  data points.
- **Large file sizes.** RPP files for a full Dense Automator soundtrack
  can exceed 1 MB.
- **High CPU during playback.** The ReapNES synth must process all those
  CC events in real time. Not a problem on modern hardware, but
  worth noting.
- **Smooth playback requirement.** Any dropped frames or timing jitter
  in the synth will be more audible in Dense Automator output than in
  Minimal driver output, because the ear expects continuous volume
  movement. A glitch in Mega Man 2 is a click. A glitch in Final
  Fantasy is a stutter.

### The Kitchen Sink Pipeline

For Dense Automator games, `kitchen_sink.py` should generate both routes
and compare them. The report should note:

1. CC11/note ratio (confirm Dense Automator classification)
2. SysEx vs CC route fidelity comparison
3. Any volume stepping artifacts in CC route
4. Recommended route for final output

---

## 13. Summary: What Makes This Family Special

The Dense Automators represent about **25% of our surveyed games** (16
out of 65) but account for a disproportionate share of the NES's most
celebrated soundtracks. They include:

- The most famous JRPG soundtrack on the NES (Final Fantasy)
- The most famous action platformer soundtrack (Batman)
- The most technically impressive NES audio (Journey to Silius)
- Three of Nintendo's own flagship titles (SMB2, SMB3, Metroid)
- The game that proved NSF is not always ground truth (Contra)

What unites them is a philosophy: **the hardware is a canvas, not a
collaborator.** These drivers do not trust the NES APU to shape sound.
They take total control, writing volume values on every frame, sculpting
every note by hand (well, by lookup table, but you get the idea).

The result is NES music that sounds less like "chiptunes" and more like
"music that happens to be playing on a NES." For better or worse, these
games reached beyond the perceived limitations of the hardware and
squeezed out an expressiveness that nobody thought four channels of
beeps could deliver.

Every frame. Every note. Every channel. Every time.

Every frame is sacred.

---

## Appendix A: Complete Data Table

For reference, here is every Dense Automator game with full survey data:

| Game | Developer | Composer | CC11/note | CC12/note | Songs | Notes | Duty | Noise | Init | Play |
|------|-----------|----------|-----------|-----------|-------|-------|------|-------|------|------|
| Final Fantasy | Square | Nobuo Uematsu | 14.9 | 0.0 | 23 | 13,889 | 12.5% | N | $FFD2 | $B000 |
| Blaster Master | Sunsoft | Naoki Kodaka et al. | 11.7 | 0.2 | 16 | 17,993 | 50% | Y | $8013 | $8077 |
| Ninja Gaiden II | Tecmo | S. Kajiya et al. | 10.5 | 0.0 | 1 | 1,464 | 75% | Y | $BDD0 | $8000 |
| Super Mario Bros. 2 | Nintendo | Koji Kondo | 9.7 | 0.3 | 24 | 7,153 | 25% | Y | $8800 | $8000 |
| Ultima: Exodus | FCI | Tsugutoshi Goto | 9.0 | 0.2 | 11 | 10,217 | 25% | N | $FA10 | $8100 |
| Batman | Sunsoft | Naoki Kodaka et al. | 7.9 | 0.1 | 3 | 3,498 | 25% | Y | $8003 | $8000 |
| Journey to Silius | Sunsoft | Naoki Kodaka et al. | 7.8 | 0.3 | 12 | 22,137 | 25% | Y | $8003 | $8000 |
| Super Mario Bros. 3 | Nintendo | Koji Kondo | 7.7 | 1.3 | 60 | 15,875 | 12.5% | Y | $9000 | $A000 |
| Contra v2 (trace) | Konami | Konami Sound Team | 7.4 | 0.1 | 11 | 4,987 | 12.5% | N | -- | -- |
| Contra v8 (trace) | Konami | Konami Sound Team | 7.1 | 0.1 | 11 | 7,496 | 12.5% | Y | -- | -- |
| Contra v6 (trace) | Konami | Konami Sound Team | 6.9 | 0.1 | 11 | 7,646 | 12.5% | Y | -- | -- |
| Contra v7 (trace) | Konami | Konami Sound Team | 6.9 | 0.1 | 11 | 7,594 | 12.5% | Y | -- | -- |
| Contra v5 (trace) | Konami | Konami Sound Team | 6.1 | 0.0 | 3 | 3,909 | 12.5% | Y | -- | -- |
| 3-D WorldRunner | Square | Nobuo Uematsu | 5.4 | 0.0 | 8 | 7,140 | 75% | Y | $DCA0 | $DCF0 |
| Super C | Konami | Konami Sound Team | 5.2 | 0.1 | 9 | 2,038 | 12.5% | Y | -- | -- |
| Kid Icarus | Nintendo | Hip Tanaka | 5.1 | 0.2 | 28 | 9,850 | 50% | Y | $E000 | $DFF3 |
| Metroid | Nintendo | Hip Tanaka | 5.1 | 0.0 | 11 | 9,423 | 50% | Y | $A000 | $B3B4 |

---

## Appendix B: For Further Investigation

1. **Full Ninja Gaiden II extraction.** Only 1 of 84 songs surveyed.
   Does the 10.5 ratio hold across the full soundtrack?

2. **Contra NSF vs trace deep dive.** What exact mechanism causes the
   NSF rip to lose volume automation? Is it an init parameter? A
   missing memory-mapped register? A different code path?

3. **Super C trace capture.** Is Super C also denser in-game than in
   NSF, like Contra?

4. **Cross-family comparisons.** How does a Dense Automator game sound
   when played through a Minimal-style CC stream (volume stripped)?
   What is the subjective loss?

5. **The 1577-game question.** Our survey covers 65 games. Running
   driver_survey.py on the full joshw.info NES library would reveal
   whether Dense Automators are rare (our 16 games = a lucky sample) or
   common (dozens more exist). The smart money is on "dozens more exist."

6. **Expansion audio interaction.** Do Dense Automator games that use
   expansion chips (VRC6, FDS, etc.) apply the same per-frame philosophy
   to the expansion channels? Castlevania 3 JP (Capcom-style, not Dense
   Automator) might not, but other games might.

---

*Generated from driver_survey.json (65 games), DRIVER_SURVEY.md, and
KNOWLEDGETHATHELPSYOUCRACKNEWGAMES.md. Data collected via NSF emulation
and Mesen trace capture. Part of the ReapNES Studio documentation.*
