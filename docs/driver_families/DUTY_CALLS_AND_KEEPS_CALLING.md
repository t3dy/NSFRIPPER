# Duty Calls (And Keeps Calling)

## The Capcom Duty Switchers: Five NES Games That Refused to Pick a Waveform and Stick With It

Most NES music engines make a decision about duty cycle early and move on
with their lives. Set it to 50%, play the melody, call it a day. Not these
five games. These five looked at the NES APU's four duty cycle settings and
said: "Why choose one when we can use all of them? *During the same note?*"

Welcome to the most exclusive club in the NES library. Out of 65 games
surveyed, exactly five qualify as Capcom Duty Switchers -- games whose
music engines actively animate both volume (CC11) AND duty cycle (CC12)
during sustained notes. The result is a sound that shimmers, breathes,
and changes character mid-phrase in a way that no other NES driver family
achieves.

The name "Capcom Duty Switchers" is a misnomer, by the way. Only zero of
the five games were made by Capcom. The name stuck because the behavior
pattern was first identified in engines with Capcom-era envelope density.
The actual developers are Nintendo, Konami, and HAL Laboratory. Capcom's
own games sit comfortably in the Minimal and Sunsoft-style families,
content with their static duty cycles. Life is full of little ironies.

---

## The Membership Roster

Five games. Three developers. One shared secret: duty cycle is not a
set-and-forget parameter.

| Game | Developer | Year | Songs | Notes | CC11/note | CC12/note | Dominant Duty | Bankswitch |
|------|-----------|------|-------|-------|-----------|-----------|---------------|------------|
| Kirby's Adventure | HAL Laboratory | 1993 | 56 | 78,992 | 3.7 | 0.7 | 50% | Y |
| Castlevania 3: Dracula's Curse (US) | Konami | 1989 | 19 | 30,780 | 4.6 | 0.8 | 25% | Y |
| Super Mario Bros v2 | Nintendo | 1985 | 19 | 16,806 | 4.8 | 0.8 | 50% | -- |
| Castlevania 3: Dracula's Curse (JP) | Konami | 1989 | 15 | 15,564 | 3.7 | 1.0 | 12.5% | Y |
| Super Mario Bros | Nintendo | 1985 | 19 | 15,510 | 4.9 | 0.8 | 50% | N |

**Combined corpus:** 128 songs, 157,652 notes, all with active duty animation.

For context, the next-closest game in the entire survey is Super Mario Bros 3,
which has CC12/note of 1.3 but also has CC11/note of 7.7 -- putting it in the
even rarer "Full Animation" family (population: 1). Below that, the CC12/note
ratio drops off a cliff. Castlevania 2: Simon's Quest manages 0.6. Gradius
hits 0.2. Most games are at 0.0-0.1. The gap between the Duty Switchers and
the rest of the NES library is not subtle.

### The Qualifying Criteria

To earn membership, a game must show:

- **CC11/note between 3.7 and 4.9** -- active per-frame volume envelopes
  (lookup table driven, not just on/off gating)
- **CC12/note between 0.7 and 1.3** -- active duty cycle animation during
  notes (not just setting duty once at note start)
- **Duty distribution across multiple values** -- using 3 or 4 of the
  available duty settings, not stuck on one

That second criterion is the killer. Plenty of games have high CC11 density
(Battletoads at 4.1, Ninja Gaiden III at 5.6, Final Fantasy at a staggering
14.9). But their CC12/note is 0.0-0.1. They animate volume like champions
and ignore duty entirely. The Duty Switchers animate both.

---

## What the NES Duty Cycle Actually Does

The NES APU's two pulse channels each have a 4-bit duty cycle selector.
This controls the waveform's shape -- specifically, what fraction of each
wave cycle is "high" versus "low." Four options:

| Duty Value | Waveform | Pulse Width | Sound Character |
|------------|----------|-------------|-----------------|
| 0 (12.5%) | `_-------` | 1/8 high | Thin, nasal, reedy. Sounds like a muted trumpet or an oboe with a cold. Cuts through a mix. |
| 1 (25%) | `__------` | 2/8 high | Bright, punchy, present. The classic "NES lead" sound. Think Mega Man stage select. |
| 2 (50%) | `____----` | 4/8 high | Warm, full, round. Classic square wave. Closest to what people imagine when they hear "chiptune." |
| 3 (75%) | `______--` | 6/8 high | Identical to 25% in frequency content (inverted waveform), but phase-offset. Sounds hollow, slightly darker. |

Most NES games pick one duty value per instrument voice and leave it there.
Mega Man 2 lives on 12.5%. Castlevania 1 prefers 50%. DuckTales likes 50%.
These games have characteristic timbres because the duty cycle IS the timbre
-- it is the only timbral control the pulse channels offer.

The Duty Switchers break this convention. They change duty cycle *within a
note*, sometimes multiple times per note, synchronized with volume changes.
The result: the waveform's harmonic content shifts while the note is sounding.

---

## What It Sounds Like (And Why You Can Hear the Difference)

### The Static Duty Experience

When a game uses static duty, every note on a given channel sounds
fundamentally the same. A sustained C4 on pulse 1 at 25% duty will be
bright for its entire duration. The volume envelope may shape the note's
loudness -- attack, decay, sustain -- but the *color* of the sound does
not change. It is a bright note that gets louder and softer.

This is how 60 out of 65 surveyed games work.

### The Duty Switcher Experience

When a Duty Switcher plays a sustained C4, the note might begin at 12.5%
duty (thin, nasal attack) while volume ramps up, switch to 25% duty
(bright, forward) at peak volume, then settle to 50% duty (warm, round)
during the sustain phase as volume decays. The listener hears a note that
*transforms* -- thin and biting at the start, warm and mellow at the end.

This is spectral animation. The harmonic content of the waveform is
changing in real time, synchronized with the amplitude envelope. In the
analog synthesizer world, this is what a filter sweep does -- it changes
the brightness of the sound over time. The NES has no filter. Duty cycle
switching is the only way to achieve this effect, and these five games
figured that out.

The sonic result:

- **Shimmering** -- sustained notes have an internal movement that static-
  duty notes lack. You hear it as a subtle brightness shift.
- **Animated attacks** -- the leading edge of a note has a different
  character than the body. Attacks sound "brighter" or "sharper" even
  at the same volume level.
- **Timbral depth** -- the ear perceives a richer, more complex sound
  because the harmonic spectrum is not constant. This is the same
  psychoacoustic principle that makes a real trumpet sound different
  from a sustained synthesizer note.
- **Expressive phrasing** -- melodic lines feel more "played" than
  "sequenced." The duty shifts give notes a vocal quality.

To test this yourself: play back any Duty Switcher MIDI through a synth
that handles CC12, then play it again with CC12 disabled. The CC12-disabled
version will sound flat, static, and noticeably less interesting -- even
though every note, rhythm, and volume curve is identical.

---

## The Duty Distribution: Who Uses What

Not all Duty Switchers use the four duty values equally. The distribution
reveals each engine's timbral strategy.

### Raw Duty Event Counts

| Game | 12.5% events | 25% events | 50% events | 75% events | Total CC12 | Strategy |
|------|-------------|-----------|-----------|-----------|------------|----------|
| Kirby's Adventure | 3,289 | 3,358 | 13,966 | 10,633 | 31,246 | Full spectrum, 50% home base |
| CV3 US | 5,080 | 6,283 | 2,011 | 105 | 13,479 | Bright-biased (25% home) |
| SMB v2 | 1,465 | 13 | 1,475 | 6 | 2,959 | Binary flip: 12.5% and 50% only |
| CV3 JP | 5,608 | 3,987 | 2,220 | 2 | 11,817 | Thin-biased (12.5% home) |
| SMB | 1,441 | 0 | 1,457 | 0 | 2,898 | Binary flip: 12.5% and 50% only |

This is where it gets interesting.

**Kirby's Adventure** is the only game that genuinely uses all four duty
values in significant quantities. It has a huge 75% usage (10,633 events!)
that no other game in the family comes close to. HAL Laboratory's engine
treats the duty cycle as a continuous expressive parameter with the full
range available. This is the most harmonically diverse sound in the family.

**Castlevania 3 (both versions)** favors the bright end of the spectrum.
The US version homes to 25% with significant 12.5% usage. The JP version
shifts even further toward 12.5%. Neither version uses 75% in any
meaningful way (105 and 2 events respectively out of thousands). Konami's
Castlevania engine likes its pulse channels thin and cutting.

**Super Mario Bros (both versions)** does something beautifully simple:
it flips between exactly two duty values -- 12.5% and 50% -- with almost
nothing in between. Zero 25% events. Zero (or 6) 75% events. The engine
alternates between "thin" and "warm" with no intermediate stops. This is
binary duty switching: the waveform either sounds nasal or round, and it
toggles between them. It is the crudest approach in the family, and it
still sounds better than static duty.

### What This Tells Us About the Composers

The duty distribution is a fingerprint of compositional intent:

- **Koji Kondo (SMB):** Pragmatic. Two timbral states are enough. The
  melody carries the music, not the waveform complexity. (He later wrote
  a much more sophisticated engine for SMB3.)
- **Konami sound team (CV3):** Aggressive. Thin, cutting timbres that
  slice through the mix. The Castlevania aesthetic demands it.
- **Hirokazu Ando & Jun Ishikawa (Kirby):** Luxurious. Every timbral
  shade available, and they use all of them. Kirby's soundtrack is warm
  and playful, and the full duty range supports that.

---

## How to Recognize a Duty Switcher in the Wild

When you run the driver survey on a new game and the numbers come back,
here is the decision tree:

```
CC12/note < 0.3?  --> Not a Duty Switcher. Move on.
CC12/note 0.3-0.6? --> Borderline. Check duty distribution.
                       If all events cluster on one value: not a switcher.
                       If spread across 2+: possible switcher, investigate.
CC12/note 0.7-1.3? --> Duty Switcher. Welcome to the club.
CC12/note > 1.3?   --> Full Animation family (SMB3 territory).
```

### Secondary Indicators

Beyond the raw CC12/note number, look for:

1. **Duty distribution across 2+ values.** A game with CC12/note of 0.8
   but all events at 50% is not a switcher -- the engine is writing the
   same value repeatedly (redundant writes). A real switcher has events
   distributed across at least two distinct duty values.

2. **CC12 events correlated with CC11 events.** In a true Duty Switcher,
   duty changes happen alongside volume changes as part of a unified
   envelope. If CC12 events happen only at note boundaries (not mid-note),
   the engine is setting duty per-note, not animating it.

3. **Temporal pattern.** Duty Switcher CC12 events are typically 1-3 per
   note (CC12/note 0.7-1.3), compared to 3-5 CC11 events per note.
   The duty envelope is simpler than the volume envelope but runs in
   parallel with it.

### The NSF Address Clue

Some NSF address patterns correlate with driver families:

| Game | Init Addr | Play Addr | Pattern |
|------|-----------|-----------|---------|
| Super Mario Bros | $BE34 | $F2D0 | Nintendo internal (unique) |
| CV3 US | $FFDB | $E24E | Konami late-era |
| CV3 JP | $E0E0 | $E0D0 | Konami VRC6 variant |
| Kirby's Adventure | $FFEF | $FF28 | HAL Laboratory |

No shared address pattern. Unlike Capcom's $8003/$8000 pattern (which
identifies a whole family of engines), the Duty Switchers come from
three independent development lineages. The technique was invented
independently at least three times.

---

## Extraction Tips: Getting the Shimmer Into Your DAW

### The Golden Rule

**Both CC11 AND CC12 must play back faithfully.** Any synth, plugin, or
playback engine that ignores CC12 will strip the timbral animation from
these games. You will hear the notes. You will hear the volume envelopes.
But the characteristic shimmer -- the thing that makes a Duty Switcher
sound like a Duty Switcher -- will be gone.

This is not a subtle difference. A/B testing Kirby's Adventure with and
without CC12 playback sounds like the difference between a real instrument
and a ringtone.

### ReapNES Synth Handling

The ReapNES synthesizer handles Duty Switchers through its three-priority
input cascade:

| Priority | Input | CC12 Handling | Fidelity |
|----------|-------|---------------|----------|
| 1 (highest) | SysEx register replay | Duty from raw APU register bits | Perfect -- hardware-identical |
| 2 | CC11/CC12 automation | CC12 mapped to duty: 0-31=12.5%, 32-63=25%, 64-95=50%, 96-127=75% | Excellent -- per-frame accuracy |
| 3 (lowest) | ADSR keyboard | Duty from knob/slider position (static) | None -- no animation |

For Duty Switcher games, **Priority 2 (CC mode) is the minimum acceptable
fidelity level.** Priority 3 (ADSR keyboard) cannot reproduce duty
animation because the duty is set by a static knob, not by incoming MIDI
data. If you are playing these games through ReapNES in ADSR mode, you
are missing the point.

Priority 1 (SysEx) is ideal because it captures the exact APU register
state including duty bits, but the CC route is nearly as good for these
games because duty cycle only has 4 possible values -- the CC12 mapping
is lossless.

### MIDI File Structure

NSF-extracted MIDIs for Duty Switcher games contain:

```
Track 0: Metadata (tempo 128.6 BPM, game name, song name)
Track 1: Square 1 (ch 0) -- CC11 (volume), CC12 (duty), note events
Track 2: Square 2 (ch 1) -- CC11 (volume), CC12 (duty), note events
Track 3: Triangle (ch 2) -- CC11 (gate only), note events
Track 4: Noise (ch 3)    -- velocity-driven, note events
```

CC12 events appear on tracks 1 and 2 (pulse channels only). Triangle
and noise have no duty cycle parameter in hardware.

### Typical CC12 Density Per Game

| Game | Avg CC12/note | CC12 events per song (approx) | MIDI size impact |
|------|---------------|-------------------------------|------------------|
| Kirby | 0.7 | ~390 | Moderate |
| CV3 US | 0.8 | ~565 | Moderate |
| SMB v2 | 0.8 | ~124 | Light |
| CV3 JP | 1.0 | ~590 | Moderate |
| SMB | 0.8 | ~108 | Light |

The MIDI files are not dramatically larger than Sunsoft-style games (which
have similar CC11 density but no CC12). The CC12 stream adds maybe 10-15%
to file size. The musical payoff for that 10-15% is enormous.

---

## The Castlevania 3 Mystery: Japan vs. America

Castlevania 3: Dracula's Curse exists in two versions with different
hardware and different sound characteristics. The Japanese version
(*Akumajou Densetsu*) uses the VRC6 expansion chip, which adds two
extra pulse channels and a sawtooth channel. The American version uses
the standard NES APU only.

### The Numbers

| Metric | CV3 US | CV3 JP | Delta |
|--------|--------|--------|-------|
| CC11/note | 4.6 | 3.7 | US has 24% more volume automation |
| CC12/note | 0.8 | 1.0 | JP has 25% more duty animation |
| Total notes | 30,780 | 15,564 | US has 2x the note count |
| Songs extracted | 19 | 15 | US has more extractable songs |
| Dominant duty | 25% | 12.5% | Different timbral home base |
| 12.5% events | 5,080 | 5,608 | JP uses more thin timbre |
| 25% events | 6,283 | 3,987 | US uses more bright timbre |
| 50% events | 2,011 | 2,220 | Similar warm timbre usage |
| 75% events | 105 | 2 | Neither uses hollow timbre |
| Noise usage | 84% of songs | 80% of songs | Similar |

### The Inversion

Here is the puzzle. The JP version has the VRC6 chip providing three
additional sound channels -- two extra pulses and a sawtooth. You might
expect the base APU channels to do *less* work, since the expansion
channels can carry some of the harmonic load. Instead, the base APU
channels do *more* duty switching in the JP version (1.0 vs 0.8 CC12/note).

Why? Three hypotheses:

**Hypothesis 1: Complementary timbral roles.** The VRC6 channels provide
sustained pad-like tones (the sawtooth is warm and constant). To contrast
with them, the base APU pulse channels need *more* timbral movement, not
less. The duty switching gives the APU channels a shimmering quality that
distinguishes them from the VRC6's static timbres.

**Hypothesis 2: The composer leaned in.** With the VRC6 handling harmony
and bass duties, the composer could dedicate the APU pulse channels more
fully to lead melody with expressive duty animation. The APU channels
became soloists instead of workhorses.

**Hypothesis 3: Different driver code paths.** The JP version runs
different init/play addresses ($E0E0/$E0D0 vs $FFDB/$E24E). The JP
driver may have a more sophisticated envelope system that naturally
produces more duty events, independent of compositional intent.

The dominant duty shift is also telling: US homes to 25% (bright, forward),
JP homes to 12.5% (thin, nasal). The JP version's pulse channels sound
thinner and more reedy, which contrasts well with the VRC6's warmer
additional channels. The US version, without that contrast, picks the
brighter 25% as its default for more presence.

### What This Means for Extraction

Both versions must be extracted with CC12 handling. But:

- **CV3 US:** Standard 4-channel extraction. CC11 + CC12 on both pulse
  channels. The music stands alone on the base APU.
- **CV3 JP:** The base APU extraction captures the duty-switching pulse
  channels, but *misses the VRC6 channels entirely* unless the NSF
  extractor supports expansion audio. The VRC6 channels are a separate
  extraction challenge requiring expansion chip emulation support.

A CV3 JP extraction that only captures the base APU will sound incomplete
-- not because the duty switching is wrong, but because three entire
channels of music are missing.

---

## Why So Few? The Rarity of Duty Animation

Five games out of 65 surveyed. That is 7.7%. And three of those five are
from the same two franchises (Mario, Castlevania). Why is duty switching
so rare?

### It Is Not a Hardware Limitation

Switching duty cycle is trivially easy on the NES. You write a value to
register $4000 (pulse 1) or $4004 (pulse 2), bits 6-7. It takes exactly
one CPU instruction. There is no timing constraint, no glitch, no
penalty. You can change duty every single frame (60 times per second)
with negligible CPU cost.

The NES hardware actively invites duty switching. Almost nobody accepted
the invitation.

### It Is a Compositional Sophistication Issue

Writing a music engine that changes duty mid-note requires:

1. **Envelope tables that include duty.** Instead of a volume-only
   envelope (a list of volume values per frame), the engine needs a
   combined envelope that specifies both volume AND duty per frame.
   This means wider envelope table entries and more ROM space.

2. **A composer who thinks in terms of timbre evolution.** Writing
   duty-animated music means deciding, for each instrument voice, how
   the waveform should change over the life of a note. This is a
   synthesizer design skill, not a traditional composition skill.
   Most NES composers came from a music background, not a synth
   programming background.

3. **Ears that care about the difference.** On a television speaker in
   1988, the difference between static 50% duty and animated
   12.5%-to-50% duty is... subtle. It is there. A careful listener
   hears it. But it is not the difference between having music and not
   having music. Most development teams had bigger priorities.

### The Economics of NES Sound

NES development was brutally resource-constrained. ROM space was precious.
CPU time was precious. The music engine competed with gameplay code for
both. A more sophisticated envelope system meant:

- More ROM for envelope tables (each entry wider by 2 bits)
- Slightly more CPU per frame (one extra register write per channel)
- More composer time designing timbral envelopes

The payoff -- notes that shimmer instead of sitting flat -- was real but
marginal compared to the effort. Most teams optimized for "music that
sounds good enough" and spent their remaining resources on gameplay.

The five games that DID invest in duty switching were all either:
- Made by teams with world-class sound programmers (Konami, Nintendo, HAL)
- Late-era NES titles with mature engines (Kirby 1993, CV3 1989)
- Flagship franchises where audio quality was a competitive differentiator

There are no obscure Duty Switcher games. No budget titles. No licensed
movie tie-ins. Every member of this family is a canonical NES classic.

---

## Kirby's Adventure: The Outlier That Explains Everything

Kirby's Adventure is the oddball. It is not made by Konami or Nintendo's
internal Kondo team. It is HAL Laboratory -- a second-party developer
that went on to create the Smash Bros series. Its composers, Hirokazu Ando
and Jun Ishikawa, are legends of game audio but do not share a codebase
or development lineage with the other four games in this family.

### What Makes Kirby Different

| Metric | Kirby | CV3 US | SMB | Family Avg |
|--------|-------|--------|-----|------------|
| CC12/note | 0.7 | 0.8 | 0.8 | 0.8 |
| Total notes | 78,992 | 30,780 | 15,510 | 31,530 |
| Songs | 56 | 19 | 19 | 26 |
| 75% duty events | 10,633 | 105 | 0 | 2,149 |
| Uses all 4 duties? | YES | Barely | NO | -- |

Kirby is the largest game in the family by a wide margin: 78,992 notes
across 56 songs, more than double the next largest (CV3 US at 30,780).
It has the lowest CC12/note ratio (0.7), which might seem like it is
"less" of a duty switcher -- but raw event counts tell the opposite
story. With 56 songs and 78,992 notes, the total CC12 event volume is
enormous.

The real outlier is Kirby's use of 75% duty. Every other game in the
family effectively ignores this waveform (105 events or fewer). Kirby
uses it 10,633 times. That is more 75% events than most games have
total CC12 events. HAL's engine treats the full duty spectrum as
available territory, while Konami and Nintendo treat it as a 2-3 value
parameter.

### What Kirby Tells Us About Independent Invention

Kirby proves that duty switching was not a technique passed between
studios. HAL Laboratory arrived at the same approach independently:

- Different NSF address pattern ($FFEF/$FF28 -- unique to HAL)
- Different duty distribution strategy (full spectrum vs. binary/bright)
- Different era (1993 vs. 1985-1989 for the others)
- Different musical aesthetic (playful and warm vs. dark/heroic)

Three separate development teams, working years apart, all concluded
that duty cycle animation was worth the investment. This is convergent
evolution: the same environmental pressure (NES audio limitations)
produced the same adaptation (duty switching) in unrelated lineages.

It also suggests that the 60 games that *did not* adopt duty switching
were leaving performance on the table. The technique was available from
day one of the NES hardware. It took the best sound teams in the
industry to realize its potential, and even they did not always use it
(Konami's Castlevania 1 has CC12/note of 0.2 -- solidly in the
Sunsoft-style family, not a Duty Switcher).

---

## The Bigger Picture: Where Duty Switchers Fit

### The Five NES Driver Families

| Family | Games | CC11/note | CC12/note | Sound |
|--------|-------|-----------|-----------|-------|
| Minimal | 25 | 0.1-2.8 | 0.0-0.2 | Clean, simple on/off |
| Sunsoft-style | 18 | 3.5-5.6 | 0.0-0.2 | Punchy, aggressive envelopes |
| **Duty Switchers** | **5** | **3.7-4.9** | **0.7-1.3** | **Shimmering, animated timbre** |
| Dense Automators | 16 | 5.1-15.0 | 0.0-0.3 | Rich, orchestral volume |
| Full Animation | 1 | 7.7 | 1.3 | Everything animated per-frame |

The Duty Switchers occupy a unique position: moderate volume automation
(similar to Sunsoft-style) but with the addition of duty animation that
no other family below Full Animation achieves. They are the only family
defined by CC12 behavior rather than CC11 behavior.

### The Evolution Path

Looking at the five families as an evolutionary sequence:

```
Minimal (set once) -----> Sunsoft-style (animate volume)
                                   |
                                   +-----> Duty Switchers (animate volume + duty)
                                   |
                                   +-----> Dense Automators (animate volume harder)
                                                      |
                                                      +-----> Full Animation (animate everything)
```

Super Mario Bros 3 (the lone Full Animation game) is the logical endpoint:
Koji Kondo took his SMB1 Duty Switcher approach and combined it with
Dense Automator-level volume density. The result is a game with CC11/note
of 7.7 AND CC12/note of 1.3 -- the only surveyed game that maxes out
both axes simultaneously.

The Duty Switchers are the fork in the road. Most engine developers, when
they wanted richer sound, invested in more volume automation (the Dense
Automator path: Final Fantasy, Blaster Master, Ninja Gaiden II). A small
minority invested in timbral animation instead (the Duty Switcher path).
Only Kondo walked both paths at once.

---

## Appendix A: Quick Reference Card

```
CAPCOM DUTY SWITCHERS -- IDENTIFICATION & EXTRACTION
=====================================================

IDENTIFY:
  CC12/note >= 0.7         (duty events happening mid-note)
  CC11/note 3.7-4.9        (active volume envelopes)
  Duty distribution: 2+ values with significant counts

EXTRACT:
  NSF pipeline: works, captures CC11 + CC12
  ReapNES mode: CC (Priority 2) minimum. SysEx (Priority 1) ideal.
  ADSR mode: DO NOT USE -- loses all duty animation

PLAYBACK CHECK:
  [ ] CC12 events present in MIDI file?
  [ ] Synth responding to CC12? (listen for timbral shifts)
  [ ] A/B test: mute CC12 track -- sound should become flatter
  [ ] Duty values span 2+ settings in MIDI CC12 data?

KNOWN MEMBERS:
  Kirby's Adventure       (HAL)    3.7/0.7  50% home  all 4 duties
  CV3 US                  (Konami) 4.6/0.8  25% home  3 duties
  CV3 JP                  (Konami) 3.7/1.0  12.5% home 3 duties
  Super Mario Bros        (Nintn.) 4.9/0.8  50% home  2 duties
  Super Mario Bros v2     (Nintn.) 4.8/0.8  50% home  2 duties

NEAR MISSES (not in family):
  Super Mario Bros 3      7.7/1.3  --> Full Animation (too dense)
  Castlevania 2           2.8/0.6  --> Minimal (too sparse)
  Castlevania 1           4.3/0.2  --> Sunsoft-style (no duty anim)
```

## Appendix B: The Name Problem

"Capcom Duty Switchers" is objectively the wrong name for this family.
No Capcom game qualifies. The name arose from the survey methodology:
the CC11/note range (3.7-4.9) overlaps heavily with Capcom's envelope
density range, and the duty switching behavior was initially expected to
appear in Capcom titles. It did not.

Alternative names considered and rejected:

- **"The Shimmer Club"** -- too vague, sounds like a cocktail lounge
- **"Duty Animators"** -- accurate but boring
- **"The Waveform Wigglers"** -- too cute
- **"Per-Frame Timbral Envelope Games"** -- technically perfect, spiritually dead
- **"Konami-Nintendo-HAL Duty Cycle Animation Family"** -- accurate, unusable

"Capcom Duty Switchers" it remains. The name is wrong. The music is right.
That is the NES in a nutshell.
