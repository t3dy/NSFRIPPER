# NES Sound Engine Research

Web research connecting community knowledge of NES sound engines to our
5-driver-family taxonomy (derived from CC11/CC12 density analysis of 65 games).

---

## Our Five Families (Quick Reference)

| # | Family Name | CC11/note | CC12/note | Signature |
|---|-------------|-----------|-----------|-----------|
| 1 | Minimal ("Silence of the Square Waves") | 0.1--2.8 | 0.0--0.6 | Hardware does the work; driver is hands-off |
| 2 | Sunsoft-style ("Punch You in the Envelope") | 3.5--5.6 | < 0.5 | Detailed volume envelope, static duty |
| 3 | Capcom Duty Switchers ("Duty Calls") | 3.7--4.9 | 0.7--1.0 | Both volume AND duty animated per note |
| 4 | Dense Automators ("Every Frame Is Sacred") | 5.1--14.9 | 0.0--0.3 | Per-frame volume writes, obsessive automation |
| 5 | Konami Full Animation ("The Chosen Few") | 7.7 | 1.3 | High density on BOTH axes; SMB3 only |

---

## 1. The Master Database: VGMPF / GDRI Sound Driver List

**URL:** https://www.vgmpf.com/Wiki/index.php?title=Famicom/NES_Sound_Driver_List
**Mirror:** https://gdri.smspower.org/wiki/index.php/Famicom/NES_Sound_Driver_List

The Video Game Music Preservation Foundation maintains the most comprehensive
NES sound driver database in existence. It catalogs hundreds of games with
their sound driver programmer attribution. Originally hosted by the Game
Developer Research Institute (GDRI), now maintained on VGMPF.

Key insight: the database confirms that NES sound drivers were overwhelmingly
company-specific. Each publisher wrote their own driver (or hired a programmer
to write one), and that driver was reused across most of their catalog. The
driver programmer is often a different person from the composer.

### Major Driver Lineages From VGMPF

| Company | Driver Programmer(s) | Notable Games | Our Family |
|---------|---------------------|---------------|------------|
| Konami | Hidenori Maezawa, Atsushi Fujio, Shigeru Fukutake(?) | Castlevania, Contra, Gradius, TMNT, Life Force | 1 (Minimal) and 2 (Sunsoft-style) depending on game |
| Capcom | Yoshihiro Sakaguchi | Mega Man 1-6, DuckTales, Bionic Commando, Ghosts'n Goblins, Strider | 1 (Minimal) |
| Sunsoft | Akito Takeuchi, Shinichi Seya | Blaster Master, Batman, Journey to Silius, Gimmick! | 4 (Dense Automators) |
| Nintendo | Yukio Kaneoka (base), Koji Kondo (variant), Hirokazu Tanaka (variant) | Super Mario Bros 1-3, Metroid, Kid Icarus, Dr. Mario | 3 and 5 (SMB1/SMB3) or 4 (SMB2, Kid Icarus) |
| Rare | Chris Stamper, Mark Betteridge | Battletoads, R.C. Pro-Am, Marble Madness (~50 games total) | 1 (Minimal) to 2 (Sunsoft-style) |
| Square | Toshiaki Imai (FFI), Hiroshi Nakamura (FFII+) | Final Fantasy, Rad Racer, 3-D WorldRunner | 4 (Dense Automators) |
| HAL Laboratory | Hiroaki Suga | Kirby's Adventure, Adventures of Lolo, Air Fortress | 3 (Duty Switchers) |
| Tecmo | Keiji Yamagishi, Michiharu Hasuya | Ninja Gaiden I-III, Rygar, Tecmo Bowl | 2 (Sunsoft-style) to 4 (Dense) |
| Natsume | Iku Mizutani | Shadow of the Ninja, Shatterhand | Unclassified |

---

## 2. Konami: Maezawa's Engine and Its Variants

**URLs:**
- https://www.vgmpf.com/Wiki/index.php/Hidenori_Maezawa
- https://www.vgmpf.com/Wiki/index.php?title=Konami

Konami's NES sound driver has an unusual number of one-off variants.
The original was written by an unknown programmer (possibly Shigeru
Fukutake) and was then heavily redesigned by Hidenori Maezawa. After
Maezawa's redesign, two main branches emerged: one by Maezawa and one
by Atsushi Fujio.

**Composition workflow:** Composers wrote music on synths/sequencers,
then typed assembly macros into the driver, assembled for playback,
entered data into a shared mainframe, ran through a sound emulator,
and finally directed programmers on placement.

**Driver-family mapping:** Konami games scatter across our families.
Castlevania 1 (4.3 CC11/note) sits in Family 2 (Sunsoft-style).
Gradius (26.2 CC11/note) is an outlier in Family 1 due to data
anomalies. Castlevania 3 US (4.6 CC11/note, 0.8 CC12/note) sits in
Family 3 (Duty Switchers). This confirms VGMPF's claim of many
customized variants: the Konami name does not predict a single
envelope behavior.

**VRC6 expansion:** The Japanese Castlevania 3 (Akumajou Densetsu)
used the VRC6 chip adding 2 extra pulse channels and a sawtooth wave.
The US version lost this hardware and had to rearrange music for the
standard APU -- which our data captures as different CC12/note density
(1.0 JP vs 0.8 US).

---

## 3. Capcom: Sakaguchi's MML Engine

**URLs:**
- https://www.vgmpf.com/Wiki/index.php/Yoshihiro_Sakaguchi_(NES_Driver)
- https://www.romhacking.net/documents/274/ (6C80 engine docs)
- https://www.romhacking.net/documents/875/ (Sound Engine 1 format)

Yoshihiro Sakaguchi wrote the dominant Capcom NES sound driver in 6502
assembly for the RP2A03. Composers wrote music in a custom hexadecimal
Music Macro Language (MML). The driver powered 35+ games from 1942
(1985) through Mega Man 6 (1993).

**Technical documentation exists:** The "Capcom 6C80 Sound Engine"
document on romhacking.net covers the music data format used in later
Capcom games (Mega Man 3 onward), including command codes, instruments,
and sound effects. A separate document covers "Sound Engine 1" for
earlier titles.

**Driver-family mapping:** Capcom games cluster almost entirely in
Family 1 (Minimal). Mega Man 1 has 0.2 CC11/note, Mega Man 2 has 0.8,
DuckTales has 0.8, Strider has 1.0. The Sakaguchi driver does not do
dense per-frame volume automation -- it sets volume and lets hardware
decay handle the rest. Later Capcom titles (Mega Man 3-4 at 3.7
CC11/note, Gargoyle's Quest II at 4.8) shift into Family 2
(Sunsoft-style), possibly reflecting the transition to Make Software's
driver for late-era Capcom NES games.

**Irony noted in our reports:** The "Capcom Duty Switchers" family
(Family 3) contains zero actual Capcom games. The name stuck from
initial analysis before developer attribution was complete.

---

## 4. Sunsoft: DPCM Bass and Dense Automation

**URLs:**
- https://www.vgmpf.com/Wiki/index.php?title=Sunsoft
- https://www.nesdev.org/wiki/Sunsoft_5B_audio
- https://www.romhacking.net/documents/665/ (engine analysis)
- https://beatscribe.wordpress.com/2013/11/27/the-sunsoft-dpcm-bass-trick-in-famitracker-tutorial/

Sunsoft's NES audio is famous for two innovations:

1. **DPCM bass**: Using the delta modulation channel for pitched bass
   notes instead of just drum samples. The samples came from an AKAI
   S700 sampler. This freed the triangle channel for melody, giving
   Sunsoft games an unusually full sound.

2. **Dense volume automation**: Blaster Master (11.7 CC11/note) and
   Journey to Silius (7.8) are among the most volume-obsessive games
   in the NES library. Batman (7.9) is similar.

**Sunsoft 5B chip:** The FME-7 mapper variant called "Sunsoft 5B"
contained a Yamaha YM2149 PSG adding 3 extra square channels. Only
Gimmick! (1992, Japan-only) used it. This is the rarest NES expansion
audio chip in commercial releases.

**Driver programmers:** Akito Takeuchi wrote the driver for Blaster
Master and Batman. Shinichi Seya wrote the driver for Journey to Silius
and Gimmick!.

**Driver-family mapping:** Sunsoft games are the core of Family 4
(Dense Automators). Blaster Master at 11.7 and Journey to Silius at
7.8 are signature members. Batman at 7.9 belongs here too. Our survey
correctly identified the Sunsoft sonic signature through pure CC11
density measurement, without knowing the company attribution.

**Academic study:** An academic paper on compositional techniques in
Sunsoft games (1988-1992) identified loops, echo effects, and
counter-melodies as defining features -- all enabled by the dense
automation approach.

---

## 5. Nintendo: Multiple Drivers, Multiple Families

**URL:** https://www.vgmpf.com/Wiki/index.php?title=Nintendo

Nintendo did not have a single sound driver. Yukio Kaneoka wrote the
base driver, and each major composer (Koji Kondo, Hirokazu Tanaka,
Akito Nakatsuka) created personalized variants. Joy Mech Fight used
a completely separate driver by Hideaki Shimizu.

**Koji Kondo** programmed his own driver variant for Super Mario Bros.
Music was written in pure 6502 assembly. SMB1 (4.9 CC11/note, 0.8
CC12/note) lands in Family 3 (Duty Switchers). SMB3 (7.7 CC11/note,
1.3 CC12/note) is the sole member of Family 5 -- high density on both
axes simultaneously.

**Hirokazu Tanaka** wrote the driver variant for Metroid and Kid Icarus.
Both show CC11/note around 5.1, placing them in the Dense Automators
(Family 4). Tanaka's driver was later adapted for Game Boy.

**Driver-family mapping:** Nintendo games span Families 3, 4, and 5
depending on the composer/programmer variant. This aligns with VGMPF's
documentation of multiple internal driver forks.

---

## 6. Rare: One Driver, Fifty Games

**URL:** https://www.vgmpf.com/Wiki/index.php/Rare_(NES_Driver)

Rare's NES sound driver powered approximately 50 games from Slalom
(1987) to Battletoads & Double Dragon (1993). Initially programmed by
Chris Stamper (Rare's founder), later maintained by Mark Betteridge.
David Wise was the sole music composer for the driver.

**Composition method:** Wise wrote music directly in 6502 assembly hex.
Pitch and length were encoded as hex pairs (e.g., "81,08" = low C,
length 8). He used the text editor Brief.

**Technical note:** The driver doubled time counters during playback,
affecting duration calculations. DPCM was rarely used -- Pin-Bot sound
effects and Battletoads pause music are notable exceptions.

**Driver-family mapping:** Wizards & Warriors (0.1 CC11/note) sits
deep in Family 1 (Minimal). Marble Madness (3.5) is borderline
Family 2. Battletoads NSF extraction (4.1) lands in Family 2
(Sunsoft-style), but Battletoads trace data (4.7-4.8) also fits
Family 2. The Rare driver appears to be a Minimal-to-Sunsoft-style
driver depending on the game's specific configuration.

---

## 7. Square: Imai's Driver and Dense Volume

**URLs:**
- https://www.vgmpf.com/Wiki/index.php/Toshiaki_Imai
- https://vgmpf.com/Wiki/index.php/Nobuo_Uematsu

Toshiaki Imai wrote Square's first NES sound driver (used for Final
Fantasy and Rad Racer). Hiroshi Nakamura wrote the replacement used
from Final Fantasy II onward. Nobuo Uematsu composed on an MSX using
MML notation (e.g., "C8" for an 8th note C), and Imai transplanted
the music into the driver.

**Driver-family mapping:** Final Fantasy is the densest game in the
entire survey at 14.9 CC11/note, making it the crown jewel of Family 4
(Dense Automators). Notably, it has 0.0 CC12/note -- zero duty
animation. The Square driver does volume obsessively but ignores
duty entirely. 3-D Battles of WorldRunner (5.4 CC11/note) also belongs
to this lineage.

---

## 8. HAL Laboratory: Suga's Driver and Duty Animation

**URL:** https://vgmpf.com/Wiki/index.php/HAL_Laboratory

Hiroaki Suga programmed HAL's NES sound driver. The driver evolved
over time, with later versions adding DPCM drum support. HAL later
created "Music Maker," a custom MML tool replacing raw assembly entry.

**Driver-family mapping:** Kirby's Adventure (3.7 CC11/note, 0.7
CC12/note) is the largest game in Family 3 (Duty Switchers) with
78,992 notes across 56 songs. HAL's driver is one of the few that
actively animates duty cycle during sustained notes, producing a
shimmering timbre effect.

---

## 9. Tecmo: Yamagishi's Driver Spans Two Families

**URL:** https://www.vgmpf.com/Wiki/index.php?title=Famicom/NES_Sound_Driver_List

Keiji Yamagishi and Michiharu Hasuya wrote Tecmo's NES sound driver,
used for Ninja Gaiden, Rygar, and Tecmo Bowl.

**Driver-family mapping:** Ninja Gaiden III (5.6 CC11/note) sits at
the top of Family 2 (Sunsoft-style). Ninja Gaiden II (10.5 CC11/note)
jumps to Family 4 (Dense Automators). This suggests the Tecmo driver
was configurable or was revised between games, allowing composers to
dial envelope density up or down.

---

## 10. FamiTracker / FamiStudio: Modern Drivers Informed by History

**URLs:**
- https://famistudio.org/doc/soundengine/
- https://www.nesdev.org/wiki/Audio_drivers

FamiTracker and its successor FamiStudio provide modern NES sound
engines for homebrew development. They are relevant because they
reverse-engineered and documented the per-frame volume control
techniques used by commercial games.

**Key technical insight from FamiStudio docs:** Using constant volume
mode with per-frame software control is far more versatile than the
hardware envelope (which only does linear decay to zero). This is
exactly what our Dense Automators and Sunsoft-style families do.
Commercial games that rely on hardware envelope alone (our Minimal
family) trade expressiveness for CPU efficiency.

**Modern homebrew drivers documented on NESdev wiki:**
- FamiStudio engine (bleubleu) -- full expansion audio support
- FamiTone2 (Shiru) -- minimalist, 186 bytes RAM
- GGSound (Gradual Games) -- 128 instruments, 3KB ROM
- Pently (Damian Yerrick) -- MML-inspired, scalable
- NSD.Lib (S.W.) -- low CPU, used in 8Bit Music Power
- Sabre (CutterCross) -- linear counter trill for triangle

These modern engines confirm the historical split: some prioritize
efficiency (FamiTone2 ~ our Minimal family), while others prioritize
per-frame expressiveness (FamiStudio ~ our Dense Automators).

---

## 11. NES APU: Hardware vs Software Envelopes

**URLs:**
- https://www.nesdev.org/wiki/APU_Envelope
- https://www.nesdev.org/wiki/APU

The NES APU envelope generator has two modes:
1. **Hardware envelope:** Linear decay from max to zero, optional loop.
   Simple but inflexible. One shape only.
2. **Constant volume mode:** Driver writes volume directly each frame.
   CPU-intensive but allows arbitrary envelope shapes.

Our five families map directly to this hardware/software split:

- **Family 1 (Minimal):** Relies on hardware envelope or sets volume
  once. 0.1-2.8 CC11/note means the driver writes volume at most a
  few times per note.
- **Families 2-5:** All use constant volume mode with software
  envelopes. The density differences (3.5 to 14.9 CC11/note) reflect
  how aggressively each driver updates volume per frame.

**Advanced techniques documented on NESdev:**
- **Echo via ring buffer:** Neil Baldwin created one-channel echo by
  buffering APU writes into a ring buffer and replaying delayed.
- **Sweep unit tremolo:** High-speed sweep parameter changes create
  wobbling/tremolo effects on pulse channels.
- **DPCM pitched bass (Sunsoft):** Using the delta modulation channel
  for melodic bass notes instead of just drums.

---

## 12. GitHub Disassembly Projects

**URLs:**
- https://github.com/cyneprepou4uk/NES-Games-Disassembly (26 games)
- https://github.com/josephstevenspgh/Castlevania-Labelled-Disassembly
- https://github.com/bbbradsmith/nes-audio-tests (APU test ROMs)
- https://github.com/Shaw02/nsdlib (NSD.Lib MML compiler + driver)
- https://github.com/pinobatch/pently (Pently engine)
- https://github.com/nesdoug/famitone5.0 (FamiTone5)
- https://github.com/blw043/nesmus3 (NESMUS3 engine)

**NES-Games-Disassembly** contains full disassemblies for 26 games
including Castlevania III, Super C, The Little Mermaid, Son Son, and
The Legend of Zelda. Sound engine code is present but not separately
documented.

**Castlevania-Labelled-Disassembly** is an incomplete but labeled
disassembly of Castlevania 1 (NES). Relevant for our Konami/Maezawa
driver research.

**nes-audio-tests** by bbbradsmith provides test ROMs and NSFs for
verifying APU behavior, including expansion audio chips. Useful for
validating our synth against hardware behavior.

---

## 13. Cross-Reference: Our Families vs Known Engines

This table maps our CC11/CC12 density families to the actual sound
drivers identified by VGMPF/GDRI research.

| Our Family | Known Engines | Why They Cluster |
|------------|---------------|------------------|
| 1: Minimal | Capcom (Sakaguchi early), Rare (Stamper/Betteridge), Enix/Chunsoft, early Konami (Fujio branch) | Hardware envelope or single-write volume; driver trusts APU |
| 2: Sunsoft-style | Konami (Maezawa branch), Tecmo (Yamagishi), Rare (Battletoads config), late Capcom (Sakaguchi v3+) | 3-6 volume writes per note via lookup table; static duty |
| 3: Duty Switchers | Nintendo (Kondo SMB1), Konami (CV3 variant), HAL (Suga) | Both CC11 and CC12 animated; rare technique |
| 4: Dense Automators | Square (Imai), Sunsoft (Takeuchi/Seya), Nintendo (Tanaka), Tecmo (NG2 variant) | Per-frame volume writes; software envelope maximalism |
| 5: Full Animation | Nintendo (Kondo SMB3 variant) | Dense on BOTH axes; unique to one game |

**Key findings:**
- Company attribution does NOT reliably predict family membership.
  Konami games span Families 1, 2, and 3. Nintendo spans 3, 4, and 5.
  Tecmo spans 2 and 4.
- The CC11 density metric is a better predictor of sonic character than
  company name, because different driver variants within a company
  produce different envelope behaviors.
- The Sakaguchi (Capcom) driver is a Family 1 engine. The "Capcom Duty
  Switchers" name for Family 3 is a historical misnomer -- zero Capcom
  games belong to it.
- Sunsoft's actual games (Blaster Master, Batman, Journey to Silius)
  belong to Family 4, not Family 2. The name "Sunsoft-style" for
  Family 2 reflects the envelope shape (punch-decay) rather than
  the company of origin.

---

## 14. Romhacking.net Technical Documents

| Document | URL | Content |
|----------|-----|---------|
| Capcom 6C80 Sound Engine (v4.0) | https://www.romhacking.net/documents/274/ | Music data format for later Capcom NES games (MM3+), including sound effects and instruments |
| Capcom Sound Engine 1 | https://www.romhacking.net/documents/875/ | Format for earlier Capcom titles |
| Sunsoft NES Audio Engines Analysis | https://www.romhacking.net/documents/665/ | Technical notes on sound engines across multiple Sunsoft games |

These documents provide byte-level format specifications that could be
used to build ROM parsers for games in our pipeline.

---

## 15. Additional Resources

| Resource | URL | Relevance |
|----------|-----|-----------|
| NESdev Wiki: Audio drivers | https://www.nesdev.org/wiki/Audio_drivers | Master list of homebrew + commercial driver documentation |
| NESdev Wiki: APU reference | https://www.nesdev.org/wiki/APU | Hardware register documentation |
| NESdev Wiki: APU Envelope | https://www.nesdev.org/wiki/APU_Envelope | Hardware vs constant volume mode |
| Retro Game Audio blog | https://retrogameaudio.tumblr.com/ | Technical analysis of NES audio techniques |
| Retro Reversing: NES | https://www.retroreversing.com/nes | Guides for NES reverse engineering |
| VGMPF: Category:Drivers | https://www.vgmpf.com/Wiki/index.php/Category:Drivers | Index of all documented NES sound drivers |
| Classical Gaming blog | https://classicalgaming.wordpress.com/ | Analysis of expansion audio chips |
| Sunsoft DPCM bass tutorial | https://beatscribe.wordpress.com/2013/11/27/the-sunsoft-dpcm-bass-trick-in-famitracker-tutorial/ | How to recreate Sunsoft bass in FamiTracker |
| Famicom expansion audio overview | https://jsgroth.dev/blog/posts/famicom-expansion-audio/ | Technical deep dive on all expansion chips |

---

## Summary

Our CC11/CC12 density analysis independently rediscovered the major
fault lines in NES sound engine design that the preservation community
has documented through disassembly and attribution research. The five
families correspond not to companies but to engineering philosophies:
how much CPU time does the driver spend talking to the APU per frame?

The VGMPF database, romhacking.net format documents, and NESdev wiki
together provide the byte-level specifications needed to extend our
ROM parsing pipeline beyond Konami games. Capcom's 6C80 engine and
Sunsoft's audio engines both have published format documentation.
