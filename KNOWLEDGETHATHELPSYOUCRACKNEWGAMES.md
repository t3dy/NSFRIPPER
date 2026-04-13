# Knowledge That Helps You Crack New Games

What we learned from surveying 65 NES games and their music drivers.
This is the practical playbook for extracting music from any NES game.

## The One Number That Matters: CC11 Per Note

When you extract a game's music through NSF emulation, the single most
revealing metric is **how many volume (CC11) events occur per note**.
This number is the fingerprint of the music engine.

| CC11/note | What it means | What the driver is doing |
|-----------|---------------|-------------------------|
| 0.0 - 0.5 | Silent or hardware-only | Driver sets volume once, lets NES hardware decay handle it |
| 0.5 - 1.5 | Gated output | Volume on at note start, off at note end. No shaping. |
| 1.5 - 3.0 | Basic envelopes | Simple attack-decay written by the driver |
| 3.0 - 6.0 | Per-frame envelopes | Lookup table driven. Each note indexes a volume table. |
| 6.0 - 15.0 | Dense automation | Every frame gets a volume write. Sophisticated engine. |
| 15.0+ | Extreme / special effects | Volume used for tremolo, echo simulation, or PCM tricks |

## The Five Driver Families

### Family 1: Minimal Drivers (25 games)
**CC11/note: 0.1 - 2.8**

These drivers write volume once per note and let the NES hardware do the rest.
The music sounds "clean" and "simple" — think early Capcom and Enix.

**How to recognize:** Very few APU writes per frame. Music sounds like
square waves with simple on/off articulation.

**Examples:** Dragon Warrior (0.1), Mega Man 1-2 (0.2-0.8), DuckTales (0.8),
Bionic Commando (0.9), Wizards & Warriors (0.1)

**Extraction difficulty:** Easy. NSF pipeline handles these perfectly.
What you hear in the NSF is what the game plays.

**Key insight:** These games get their musical character from *note placement*
and *duty cycle choice*, not from envelope shaping. DuckTales sounds amazing
with only 0.8 CC11/note because the melodies and harmonies are that good.

### Family 2: Sunsoft-style (18 games)
**CC11/note: 3.5 - 5.6, CC12/note < 0.5**

These drivers have detailed volume envelopes (lookup tables that shape each
note's attack and decay) but set the duty cycle once and leave it alone.
The music sounds "punchy" and "aggressive."

**How to recognize:** 3-6 volume changes per note but duty almost never changes.
Strong attack transients, noticeable decay curves.

**Examples:** Castlevania 1 (4.3), Mega Man 3-4 (3.7), Battletoads (4.1),
Gargoyle's Quest II (4.8), Ninja Gaiden III (5.6)

**Extraction difficulty:** Medium. The envelope tables are faithfully captured
by NSF emulation. Fidelity is high. The ReapNES synth must play CC11
automation faithfully — ADSR mode will sound wrong for these games.

**Key insight:** This is the "golden era NES sound." The envelope tables
give each note a distinctive punch that minimal drivers lack. Konami's
Castlevania engine and Capcom's later Mega Man engine both converged
on this approach independently.

### Family 3: Capcom Duty Switchers (5 games)
**CC11/note: 3.7 - 4.9, CC12/note: 0.7 - 1.3**

These drivers actively switch duty cycle DURING notes for timbral animation.
A note might start at 25% duty (bright attack) and shift to 50% (warmer sustain).
The music sounds "animated" and "shimmering."

**How to recognize:** CC12 events happening alongside CC11 events. Duty
distribution across all 4 values, not concentrated on one.

**Examples:** Kirby's Adventure (3.7/0.7), Castlevania 3 US (4.6/0.8),
Castlevania 3 JP (3.7/1.0), Super Mario Bros (4.9/0.8)

**Extraction difficulty:** Medium-high. Both CC11 AND CC12 must be played
back faithfully. The ReapNES synth handles this, but any synth that
ignores CC12 will lose the timbral animation that makes these games
sound distinctive.

**Key insight:** Castlevania 3 JP has MORE duty switching than the US version
(1.0 vs 0.8 CC12/note). The Japanese version uses the VRC6 expansion chip
for extra channels, and the base APU channels use more sophisticated
duty animation to complement them.

### Family 4: Dense Automators (16 games)
**CC11/note: 5.1 - 15.0**

These drivers write to volume registers almost every frame. The envelope
isn't a simple table lookup — it's a continuous stream of per-frame values.
The music sounds "rich," "complex," or "orchestral."

**How to recognize:** High CC11 density. Music has very smooth volume
curves, echo effects, or tremolo built into the driver.

**Examples:** Final Fantasy (14.9!), Blaster Master (11.7), Ninja Gaiden II
(10.5), Super Mario Bros 2 (9.7), Batman (7.9), Journey to Silius (7.8),
Contra later versions (6.9-7.4)

**Extraction difficulty:** High. These drivers produce enormous amounts of
CC data. The MIDI files are large. Playback must be sample-accurate to
avoid audible artifacts from volume quantization.

**Key insight:** Final Fantasy at 14.9 CC11/note means Nasir Gebelli's
sound engine writes volume data literally every frame for every note.
This is why FF music sounds so different from other NES games — the
engine is doing software-controlled volume envelopes that the NES
hardware couldn't do on its own. Journey to Silius (Sunsoft) at 7.8
uses a similar technique for its famously rich bass tones.

### Family 5: Konami Full Animation (1 game confirmed)
**CC11/note > 6.0, CC12/note > 1.0**

Both volume AND duty are animated per-frame. This is the most sophisticated
approach: every aspect of the sound is under continuous software control.

**Examples:** Super Mario Bros 3 (7.7/1.3)

**Extraction difficulty:** Highest. Both CC streams must be perfectly
synchronized. This is the use case where SysEx register replay
(Priority 1 in the synth cascade) really shines — it captures the
exact register state without any MIDI encoding loss.

**Key insight:** SMB3 is actually a Nintendo game, not Konami, but it
uses the most Konami-like approach in our survey. The engine was
written by Koji Kondo, who also did the simpler SMB1 engine (Family 3).
He leveled up his driver between games.

## Practical Rules for New Games

### When you encounter a new game:

1. **Fetch the NSF:** `python scripts/fetch_nsf.py "Game Name" --first`
2. **Extract all songs:** `python scripts/fetch_and_extract.py "Game Name"`
3. **Survey the driver:** `python scripts/driver_survey.py --game Game_Slug`
4. **Check the CC11/note number** — this tells you which family it belongs to

### What the family tells you about extraction:

| Family | ReapNES mode | Fidelity concern | REAPER project notes |
|--------|-------------|------------------|---------------------|
| Minimal | CC or ADSR both work | Low — simple audio | ADSR presets will sound fine |
| Sunsoft-style | CC mode required | Medium — envelope tables | CC11 automation is the sound |
| Duty switchers | CC mode required | High — CC12 matters | Both CC11 + CC12 must play back |
| Dense | CC or SysEx mode | High — lots of data | Large MIDI files, dense automation |
| Full animation | SysEx preferred | Highest — both streams | SysEx register replay is ideal |

### What to listen for when ear-checking:

- **Minimal games:** Do notes start and stop cleanly? Any hanging notes?
- **Sunsoft-style:** Do notes have the right "punch"? Attack should be sharp.
- **Duty switchers:** Does the timbre shimmer/change during sustained notes?
- **Dense:** Are volume curves smooth? Any stepping or quantization artifacts?
- **Full animation:** Does it sound exactly like the game? Any duty glitches?

## The Outliers

**Gradius (26.2 CC11/note)** — Classified as "sparse" by our survey because
the median song is simple, but some songs have extreme volume density.
This is Konami's engine doing rapid volume modulation for special effects
(echo, fade, tremolo). The outlier songs need investigation.

**Wizards & Warriors (0.1 CC11/note from NSF)** — Rare's engine is
deceptively simple in NSF output but complex in the ROM. The NSF rip
may not capture all the driver's behavior. This is a game where Mesen
trace gives different (richer) results than NSF emulation.

**Contra (1.5 from NSF vs 6.9 from trace)** — Same engine, but the NSF
rip captures a simpler playback mode than what the actual game does.
The trace versions show Konami's engine running with full per-frame
envelope updates. This proves that **NSF fidelity is not always equal
to in-game fidelity** — the fidelity hierarchy in CLAUDE.md is correct.

## NSF Address Patterns

Games from the same developer often share init/play address patterns:

| Pattern | Developer | Games |
|---------|-----------|-------|
| Init=$8003, Play=$8000 | Capcom (late) | Mega Man 3-4, DuckTales, Bionic Commando, Gargoyle's Quest II, Strider, Journey to Silius |
| Init=$8000, Play=varies | Sunsoft | Batman, Blaster Master, 1942 |
| Init=$xxDB/E0, Play=$E24E | Konami (CV3) | Castlevania 3 US/JP |
| Init=$BB09, Play=$838A | Konami (CV1) | Castlevania 1 |
| Init=$FFEF, Play=$FF28 | HAL Laboratory | Kirby's Adventure |
| Init=$9000, Play=$9000 | Capcom (early) | Mega Man 1, Legendary Wings, Section Z |

Same init/play pattern = likely same music engine = same extraction approach works.
When you encounter a new game, check if its NSF addresses match a known pattern.
If they do, you already know that family's extraction characteristics.

## What We Still Don't Know

1. **How many of the 1577 joshw games fall into each family?** We've only
   surveyed 65. Running fetch_and_extract on all of them would give us
   the complete picture.

2. **Do NSF rips always capture the full driver behavior?** Contra and
   Wizards & Warriors suggest they don't. Games where NSF CC11 is much
   lower than trace CC11 are candidates for Mesen investigation.

3. **What makes the "Unclassified" games tick?** 16 games have dense
   volume automation but static duty — they might be a 6th family
   (Nintendo internal engines?) or variants of the Sunsoft approach
   with higher tick rates.

4. **Expansion audio chips** (VRC6, VRC7, FDS, MMC5, Namco 163, Sunsoft 5B)
   add channels that our survey doesn't cover yet. Castlevania 3 JP
   with VRC6 is the test case.
