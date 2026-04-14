# NESDev Community Research: NES Sound Engine Knowledge

Research conducted 2026-04-13. Sources: NESDev Wiki, NESDev Forums,
VGMPF Wiki, Romhacking.net, GitHub repositories.

---

## 1. NESDev Wiki Core References

### NSF Format (nesdev.org/wiki/NSF)

The NSF file format packages game music code with a 128-byte header.
Key technical details relevant to our pipeline:

- **Init/Play architecture**: NSF players call INIT once (song number
  in accumulator A), then call PLAY at ~60Hz (NTSC) or ~50Hz (PAL).
  The play routine runs the game's actual 6502 sound engine code.
- **Bankswitching**: 8 x 4KB banks via $5FF8-$5FFF. Games with >32KB
  of music data use this. Our `fetch_and_extract.py` handles this
  transparently via NSF emulation.
- **Expansion chip flags** ($07B): VRC6, VRC7, FDS, MMC5, N163,
  Sunsoft 5B, VT02+. Multi-chip NSFs are technically possible but
  never occurred on real hardware.
- **Playback rate**: default NTSC ~60.099 Hz. Custom rates exist.
  Our pipeline assumes 60Hz frame rate (16 ticks/frame at 128.6 BPM).

URL: https://www.nesdev.org/wiki/NSF

### APU Registers (nesdev.org/wiki/APU, /APU_registers)

The APU has 5 channels mapped to $4000-$4013, $4015, $4017:

| Channel | Registers | Key features |
|---------|-----------|-------------|
| Pulse 1 | $4000-$4003 | Duty (4 settings), envelope, sweep, 11-bit period |
| Pulse 2 | $4004-$4007 | Same as Pulse 1 |
| Triangle | $4008-$400B | No volume control (gate only), linear counter, 11-bit period |
| Noise | $400C-$400F | Envelope, 4-bit period index, mode bit (tonal/noise) |
| DMC | $4010-$4013 | Delta modulation, 7-bit DAC at $4011, sample playback |

The frame counter (~240Hz NTSC) drives envelope generators, sweep
units, and length counters. Games that write to $4017 every frame
manually synchronize the frame counter.

Non-linear mixing: pulse channels on one DAC, triangle/noise/DMC on
another. The $4011 DMC DAC value affects triangle/noise volume --
some games exploit this for crude mixing control.

URLs:
- https://www.nesdev.org/wiki/APU
- https://www.nesdev.org/wiki/APU_registers
- https://www.nesdev.org/wiki/APU_Noise

### APU Period Table (nesdev.org/wiki/APU_period_table)

The standard NTSC period formula:
`period = round(39375000 / (22 * 16 * freq)) - 1`

Triangle sounds 1 octave lower than pulse for the same period value
(32-step vs 16-step sequencer). The wiki provides lookup tables
(periodTableHi/Lo) indexed by note number. PAL uses a different
clock rate requiring separate tables.

This confirms our `pitch_to_midi` implementation subtracting 12 for
triangle is correct per hardware spec.

URL: https://www.nesdev.org/wiki/APU_period_table

---

## 2. Commercial Game Sound Engine Families

### 2.1 Konami (Maezawa/Fujio drivers)

**Source**: VGMPF Wiki, NESDev forums, Nerdly Pleasures blog

Konami's NES sound system has the most complex lineage of any publisher:

- **Original driver**: Unknown programmer (possibly Shigeru Fukutake), ~1986
- **Maezawa redesign**: Hidenori Maezawa heavily rewrote the driver after
  about a year. His variant became the de facto standard for Konami NES
  titles, used even in games he didn't compose.
- **Fujio branch**: Atsushi Fujio created a parallel variant. The two
  branches (Maezawa and Fujio) represent the main Konami driver families.
- **One-off variants**: VGMPF notes "an unusually large number of
  customized and one-time variations" exist across Konami's catalog.

**Expansion chips**: Konami created VRC6 (2 extra pulse + sawtooth,
used in Akumajou Densetsu/CV3 JP, Esper Dream 2, Madara) and VRC7
(FM synthesis, used only in Lagrange Point). Maezawa helped design
the VRC6 chip itself.

**Music entry**: Composers wrote in assembly macros, assembled for
playback on dev hardware.

**DPCM usage**: Konami used DPCM primarily for kick/snare drums and
occasional vocal effects.

**Relevance to our survey**: Our driver survey classified Castlevania 1
as "Sunsoft-style" (CC11/note ~4.3) and Castlevania 3 as "Capcom-style"
(CC11/note ~4.6, CC12/note ~0.8). The high duty switching in CV3 likely
reflects the VRC6 expansion's extra channels. The Maezawa driver's
per-frame volume updates explain the ~4-5 CC11 events per note we
observe in Konami titles.

URLs:
- https://www.vgmpf.com/Wiki/index.php?title=Konami
- https://www.vgmpf.com/Wiki/index.php/Hidenori_Maezawa

### 2.2 Capcom (Sakaguchi / 6C80 drivers)

**Source**: VGMPF Wiki, Romhacking.net document #274

Capcom's NES audio went through three phases:

1. **Early titles** (~1985-1986): Driver attribution unclear. Some
   games may have used Micronics programmer Kazuo Yagi's driver
   rather than Sakaguchi's.
2. **Sakaguchi driver** (majority of catalog): Written by Yoshihiro
   Sakaguchi in 6502 assembly for the RP2A03. Composers wrote music
   on keyboards, then converted to custom hexadecimal MML. No
   expansion chips -- Capcom never used expansion audio on NES.
3. **Make Software driver** (final titles): Replaced Sakaguchi's
   driver with a more user-friendly tool. Kenji Yoshida noted the
   new tool was easier to use.

**Games**: ~30+ titles including 1942, Mega Man 1-6, Ghosts 'N Goblins,
DuckTales, Bionic Commando, Darkwing Duck, Little Mermaid, etc.

**6C80 Sound Engine documentation** (Romhacking.net): Covers the
music data format used in later Capcom games (Mega Man 3 onward,
Mighty Final Fight). Includes instrument definitions, sound effects,
and data storage layout. This is the most detailed publicly available
byte-level format doc for any commercial NES sound engine.

**Relevance to our survey**: Capcom games cluster in our "Minimal"
family (CC11/note 0.2-2.2, CC12/note 0.0-0.2). Mega Man 1 has
CC11/note of only 0.2, Mega Man 2 is 0.8, DuckTales is 0.8. This
matches Capcom's approach: constant-volume envelope with hardware
envelope decay, minimal per-frame volume automation. The Sakaguchi
driver's MML-based composition explains the clean, structured note
patterns we see.

URLs:
- https://vgmpf.com/Wiki/index.php/Yoshihiro_Sakaguchi_(NES_Driver)
- https://www.vgmpf.com/Wiki/index.php?title=Capcom
- https://www.romhacking.net/documents/274/

### 2.3 Sunsoft (Takeuchi/Morota/Seya drivers)

**Source**: VGMPF Wiki, NESDev forums, retrogameaudio

Sunsoft's audio evolved through three programmers:
1. **Akito Takeuchi** -- initial driver
2. **Naohisa Morota** -- subsequent revision
3. **Shinichi Seya** -- final revision, reprogrammed to use MML

**Signature technique: DPCM bass**. Sunsoft was one of the few NES
publishers to use the DPCM channel for pitched instruments (not just
drums). Their picked/slap bass used samples from an AKAI S700 sampler,
optimized for NES memory constraints. Implementation requires 5
samples (A#, B, C, C#, D) at different pitches, mapped across the
bass range via pitch shifting.

**Sunsoft 5B (YM2149F)**: Used only in Gimmick! (Japan). Added 3
channels of PSG synthesis. Only one game ever used it for music.

**Relevance to our survey**: Our "Sunsoft-style" family (CC11/note
3.7-5.6, static duty) includes games like Battletoads, Castlevania 1,
Ninja Gaiden III. The name is somewhat misleading -- it captures the
envelope density pattern (detailed volume automation, minimal duty
switching) rather than actual Sunsoft-authored games. Journey to
Silius (actual Sunsoft) landed in "Unclassified" with CC11/note 7.8,
suggesting its DPCM bass and more aggressive envelope usage pushes
it into a denser category than the family named after it.

URLs:
- https://www.vgmpf.com/Wiki/index.php?title=Sunsoft
- https://musical-artifacts.com/artifacts/820
- https://beatscribe.wordpress.com/2013/11/27/the-sunsoft-dpcm-bass-trick-in-famitracker-tutorial/

### 2.4 Rare (Stamper/Betteridge driver)

**Source**: VGMPF Wiki, NESDev forums

One of the most prolific NES sound drivers -- used in ~48 games
(1987-1993). Programmed by Chris Stamper (Rare founder), later by
Mark Betteridge (from Cobra Triangle onward). David Wise was the
primary (often sole) composer.

**Technical details**:
- Composition in raw 6502 hex: pitch byte + length byte per note
- Length counter doubled internally (e.g., $06 = 12 frames)
- Four standard channels, limited DPCM usage
- PAL playback is a half-step lower than NTSC
- No expansion chip support

**Battletoads PCM drums**: Rather than playing stored samples,
Battletoads generates drums algorithmically by writing computed
values to $4011. Ramp-based synthesis with variable speed/length
creates triangular waveforms. This saves ROM space while producing
distinctive percussion.

**CPU performance**: Battletoads engine averages 482 cycles/frame
with 1820 peak -- lower peak than some alternatives, reducing lag
risk during gameplay.

**Relevance to our survey**: Wizards & Warriors (CC11/note 0.1) and
Battletoads (CC11/note 4.1) both use Rare's driver but fall into
different families. W&W is "Minimal" while Battletoads is
"Sunsoft-style". This proves that driver family classification by
CC density does not map 1:1 to actual driver authorship -- the same
engine can produce very different envelope profiles depending on how
the composer uses it. David Wise's later compositions (Battletoads)
used far more per-frame volume automation than his earlier work.

URLs:
- https://www.vgmpf.com/Wiki/index.php/Rare_(NES_Driver)
- https://forums.nesdev.org/viewtopic.php?t=15586

### 2.5 Nintendo (Kondo and others)

Nintendo's internal drivers are less documented than third-party ones.
Koji Kondo wrote the driver used in Super Mario Bros. and Zelda.
The VGMPF driver list identifies multiple Nintendo-internal drivers
without detailed technical documentation.

**Relevance to our survey**: Super Mario Bros. appears in both
"Sunsoft-style" (v3, CC11/note 4.9) and "Capcom-style" (v2, CC11/note
4.8, CC12/note 0.8) in our survey, depending on extraction version.
SMB3 is alone in the "Konami-style" family (CC11/note 7.7, CC12/note
1.3). The variation across Mario titles likely reflects different
extraction parameters rather than different drivers.

### 2.6 Other Publishers

**Tecmo**: "Super Sound Machine" by Keiji Yamagishi. Yoshiaki Inose
wrote an earlier variant (Chester Field, Mighty Bomb Jack).

**Square**: Toshiaki Imai wrote the driver for Final Fantasy and Rad
Racer. Our survey shows Final Fantasy at CC11/note 14.9 with no
CC12 automation -- extremely dense volume updates with static duty.

**Natsume, Jaleco, Taito, Irem**: Less documented. Jaleco used NEC
D7756C chip for sample playback in 6 games. Taito and Irem rarely
used expansion audio.

URL: https://www.vgmpf.com/Wiki/index.php?title=Famicom/NES_Sound_Driver_List

---

## 3. Homebrew / Modern Sound Engines

The NESDev wiki's Audio Drivers page catalogs available engines for
new NES development. These are relevant as reference implementations
showing how NES sound engines work internally:

| Engine | Author | RAM | ROM | Key feature |
|--------|--------|-----|-----|-------------|
| FamiTone2 | Shiru | 186B | 1636B | Minimal footprint, FamiTracker export |
| FamiStudio | bleubleu | varies | varies | All expansion chips, full envelope support |
| GGSound | Gradual Games | 168B | ~3048B | 128 instruments, used by NESmaker |
| Pently | Damian Yerrick | 112B | 1918B | Rows-per-minute tempo, grace notes |
| Penguin | pubby | 86B | varies | Constant 790 cycles, raster-safe |
| Lizard | Rainwarrior | 105B | 2152B | Fixed 150 BPM, volume column |
| NSD.Lib | S.W. | low | low | MML compiler, used in commercial homebrew |

**FamiTracker** remains the dominant composition tool. Its internal
format is not directly useful for our pipeline, but games composed
in FamiTracker and exported via FamiTone2/FamiStudio give predictable
envelope patterns that appear in NSF output.

**NESDev forum poll** (2018, 30 respondents): FamiTone 37%, Other 27%,
FamiTracker 13%, GGSound/Pently/NSF 7% each. Custom drivers are
common among experienced developers.

URLs:
- https://www.nesdev.org/wiki/Audio_drivers
- https://forums.nesdev.org/viewtopic.php?t=17812
- https://famistudio.org/doc/soundengine/

---

## 4. NSF Ripping and ROM-to-NSF Conversion

### Tools

- **NES2NSF** (Romhacking.net): Splits ROM into banks, adds NSF
  header. Buggy with 8K bank splitting. Mapper 0 only. Considered
  outdated.
- **NSFPlay** (bbbradsmith/nsfplay): Full-featured NSF player with
  LOG_CPU register dump capability. Useful for per-frame register
  extraction as alternative to Mesen.
- **FCEUX Code-Data Logger**: Can create stripped ROMs removing
  unused code, then NSF-ify the result.
- **EZNSF**: Reverse direction -- converts NSF to playable NES ROM.

### Manual Ripping Process

1. Load ROM in emulator with debugging (FCEUX, Mesen)
2. Set breakpoints on APU register writes ($4000-$4013)
3. Dump memory $8000-$FFFF (or $C000-$FFFF for 16KB PRG)
4. Prepend valid NSF header with correct INIT/PLAY addresses
5. For bankswitched games: configure bank mapping in header

**Key challenge**: NSF requires the play routine to be callable as
a subroutine (JSR/RTS), but many games use NMI-driven audio with
complex state machines. Restructuring interrupt-driven code for
NSF's polling model is the hardest part.

**Our pipeline avoids this entirely**: We use pre-ripped NSFs from
existing archives and run them through emulation to capture per-frame
APU state. We never need to rip NSFs from ROMs ourselves.

URLs:
- https://forums.nesdev.org/viewtopic.php?t=6627
- https://www.romhacking.net/utilities/545/
- https://github.com/bbbradsmith/nsfplay/releases/
- https://github.com/bbbradsmith/eznsf

---

## 5. NES Music Database (NES-MDB)

The NES-MDB project (Chris Donahue, Stanford) provides the closest
academic parallel to our pipeline:

- **5,278 songs** from **397 games**, 296 composers
- Extracts per-frame APU register state from NSF files
- Provides multiple output formats: MIDI, piano roll (24Hz), VGM,
  and a custom "NES Language Modeling" (NLM) format
- NLM expands register writes into 38 constituent functions per
  channel, removing unchanged parameters

**Key insight for our work**: NES-MDB's MIDI format uses 44.1kHz
timing resolution for sample-accurate reconstruction. Our 16-ticks-
per-frame approach at 128.6 BPM is coarser but sufficient for
musical playback. Their 24Hz piano roll format is interesting --
it's half our frame rate, suggesting they found sub-frame resolution
unnecessary for composition tasks.

**Difference from our approach**: NES-MDB treats all NSF output as
ground truth. Our pipeline recognizes that NSF may diverge from
actual game audio (proven with Mario and Battletoads), using Mesen
trace as higher-priority ground truth when available.

URL: https://github.com/chrisdonahue/nesmdb

---

## 6. Expansion Audio Chip Map

Games with expansion audio (Famicom only, not available on NES
without hardware mods):

| Chip | Publisher | Games | Extra channels |
|------|-----------|-------|---------------|
| VRC6 | Konami | Akumajou Densetsu, Esper Dream 2, Madara | 2 pulse + 1 sawtooth |
| VRC7 | Konami | Lagrange Point | 6-ch FM synthesis |
| FDS | Nintendo | ~90+ titles (Zelda, Metroid, Kid Icarus, etc.) | 1 wavetable |
| MMC5 | Various | Just Breed, Metal Slader Glory (3 total) | 2 pulse + PCM |
| N163 | Namco | Final Lap, Mappy Kids, King of Kings, etc. | 4-8 wavetable |
| 5B | Sunsoft | Gimmick! (1 game only) | 3 PSG (YM2149) |

**Relevance**: Our pipeline works exclusively with standard APU (no
expansion chips). Games in our library that had expansion audio on
Famicom (e.g., Castlevania 3 JP with VRC6) show different CC density
profiles than their NES counterparts -- CV3 JP has CC12/note 1.0 vs
CV3 US CC12/note 0.8, reflecting the extra channel activity captured
in the NSF even though our synth only plays the 5 standard channels.

URL: https://www.nesdev.org/wiki/List_of_games_with_expansion_audio

---

## 7. Cross-Reference: NESDev Knowledge vs. Our Driver Families

Our driver survey identified 5 families by CC11/CC12 density analysis
of 65 games. Here is how NESDev community knowledge maps to those
families:

### Minimal Family (25 games, CC11/note 0.1-4.3)

NESDev explanation: Games using hardware envelope decay ($4000 bits
4-5 set to constant volume or short decay). The driver writes volume
once per note, lets hardware handle decay. Capcom's Sakaguchi driver
is the archetype -- MML composition with fixed envelope settings.
Rare's early games (W&W, Marble Madness) also fit here.

Known drivers in this family: Capcom Sakaguchi, Rare Stamper/Betteridge
(early usage), Konami early variants.

### Sunsoft-style Family (18 games, CC11/note 3.7-5.6)

NESDev explanation: Software-driven volume envelopes updating every
frame. The driver maintains a volume envelope table and writes to
$4000/$4004 each frame. Typical pattern: attack at vol 15, decay
over 3-4 frames, sustain at vol 4-8. This is standard for mid-to-
late era NES games with more sophisticated sound programming.

Known drivers in this family: Konami Maezawa (CV1, Contra), Rare
Betteridge (Battletoads-era), Nintendo internal (SMB v3).

### Capcom-style Family (5 games, CC11/note 3.7-4.9, CC12/note 0.7-1.0)

NESDev explanation: Per-frame volume AND duty cycle animation. The
duty cycling creates timbral movement within each note -- brighter
attack, mellower sustain. This is more CPU-intensive and produces
richer sound. CV3 with VRC6 expansion naturally has more duty data
from the extra channels.

Known drivers: Nintendo internal (SMB, Kirby's Adventure), Konami
VRC6-aware driver (CV3 JP).

### Konami-style Family (1 game: SMB3)

NESDev explanation: Maximum per-frame automation of both volume and
duty. SMB3's sound engine is among the most sophisticated on the NES,
with CC11/note 7.7 and CC12/note 1.3. This represents the pinnacle
of NES sound programming where every frame carries musical information.

Known drivers: Nintendo late-era internal driver.

### Unclassified (16 games, CC11/note 5.1-14.9)

NESDev explanation: These games exceed the "Sunsoft-style" density
but don't show the duty animation of the "Capcom-style" family.
Notable entries:

- **Final Fantasy** (CC11/note 14.9): Square's Toshiaki Imai driver
  with extremely dense volume automation, possibly updating multiple
  times per frame or using very short notes.
- **Blaster Master** (CC11/note 11.7): Sunsoft game -- actual Sunsoft
  driver with their characteristically dense volume work.
- **Journey to Silius** (CC11/note 7.8): Also Sunsoft. Both real
  Sunsoft games land here, not in "Sunsoft-style."
- **Ninja Gaiden II** (CC11/note 10.5): Tecmo's Super Sound Machine.

This suggests our "Sunsoft-style" label is misnamed. Real Sunsoft
games are actually denser than that family. The family might be
better called "Standard Envelope" while actual Sunsoft games belong
to a "Dense Automation" tier.

---

## 8. Key Takeaways for the Pipeline

1. **Driver authorship does not predict CC density**. The same Rare
   driver produces CC11/note 0.1 (W&W) and 4.1 (Battletoads).
   Composer technique matters more than engine architecture.

2. **Capcom games are reliably minimal**. The Sakaguchi MML workflow
   produces consistent low-automation output across 30+ titles.
   Our "Minimal" family is essentially "Capcom and friends."

3. **Konami has the most driver variants**. No single characterization
   covers all Konami games. CV1, CV3 JP, and Gradius all use Konami
   drivers but produce wildly different CC profiles.

4. **Real Sunsoft games are denser than our "Sunsoft-style" family**.
   Journey to Silius (7.8) and Blaster Master (11.7) exceed the
   3.7-5.6 range of the family named after them.

5. **Battletoads PCM drums are algorithmic, not sampled**. The $4011
   writes we see in traces are computed waveforms, not stored DPCM.
   This explains the unusual noise channel behavior in our Battletoads
   extraction sessions.

6. **NES-MDB validates our approach** but at lower fidelity. They
   treat all NSF as ground truth; we use Mesen trace as higher
   authority. Our pipeline is more rigorous for games where NSF
   diverges from actual gameplay audio.

7. **The 6C80 Capcom format doc** (Romhacking.net #274) is the most
   detailed byte-level commercial engine documentation available.
   If we ever need to parse Capcom ROMs directly (Layer 3), this
   is the starting point for Mega Man 3+ era games.

8. **NSFPlay's LOG_CPU** could supplement Mesen trace for games where
   we want per-frame register state from NSF emulation specifically,
   rather than from gameplay recording.

---

## 9. VGMPF Driver Attribution Table (NES)

Comprehensive list of identified NES sound driver programmers and
their game catalogs, from VGMPF and GDRI sources:

| Developer | Programmer | Games (approx.) | Notes |
|-----------|-----------|-----------------|-------|
| Capcom | Yoshihiro Sakaguchi | 30+ | MML-based, no expansion |
| Capcom | Make Software | ~5 (late titles) | Replaced Sakaguchi driver |
| Konami | Hidenori Maezawa | 15+ (variant used in 30+) | VRC6 co-designer |
| Konami | Atsushi Fujio | 10+ | Parallel branch |
| Konami | Jun Funahashi | Several | Later Konami titles |
| Rare | Chris Stamper / Mark Betteridge | ~48 | Hex composition, David Wise primary composer |
| Nintendo | Koji Kondo | SMB, Zelda, etc. | Internal driver, poorly documented |
| Sunsoft | Takeuchi / Morota / Seya | ~20 | DPCM bass, AKAI S700 samples |
| Square | Toshiaki Imai | FF, Rad Racer | Dense volume automation |
| Tecmo | Keiji Yamagishi | ~15 | "Super Sound Machine" |
| Tecmo | Yoshiaki Inose | 4 (early) | Predecessor to Super Sound Machine |

---

## 10. Resource Links Summary

### Wiki References
- NSF format: https://www.nesdev.org/wiki/NSF
- APU overview: https://www.nesdev.org/wiki/APU
- APU registers: https://www.nesdev.org/wiki/APU_registers
- APU period table: https://www.nesdev.org/wiki/APU_period_table
- APU Noise: https://www.nesdev.org/wiki/APU_Noise
- Audio drivers: https://www.nesdev.org/wiki/Audio_drivers
- Music: https://www.nesdev.org/wiki/Music
- Expansion audio games: https://www.nesdev.org/wiki/List_of_games_with_expansion_audio
- NSF spec (plain text): https://www.nesdev.org/nsfspec.txt

### Forum Threads
- Music driver poll: https://forums.nesdev.org/viewtopic.php?t=17812
- Behind the scenes NSF ripping: https://forums.nesdev.org/viewtopic.php?t=16630
- NES to NSF conversion: https://forums.nesdev.org/viewtopic.php?t=6627
- Battletoads PCM drums: https://forums.nesdev.org/viewtopic.php?t=15586
- Homebrew music engines: https://forums.nesdev.org/viewtopic.php?t=13344
- Konami VRC6 engine: https://forums.nesdev.org/viewtopic.php?t=23009
- FamiStudio engine: https://forums.nesdev.org/viewtopic.php?t=20825
- Constant-cycle engine: https://forums.nesdev.org/viewtopic.php?t=16111

### VGMPF Driver Documentation
- Capcom Sakaguchi: https://vgmpf.com/Wiki/index.php/Yoshihiro_Sakaguchi_(NES_Driver)
- Konami: https://www.vgmpf.com/Wiki/index.php?title=Konami
- Sunsoft: https://www.vgmpf.com/Wiki/index.php?title=Sunsoft
- Rare: https://www.vgmpf.com/Wiki/index.php/Rare_(NES_Driver)
- Maezawa bio: https://www.vgmpf.com/Wiki/index.php/Hidenori_Maezawa
- Driver list: https://www.vgmpf.com/Wiki/index.php?title=Famicom/NES_Sound_Driver_List

### Tools and Datasets
- NSFPlay: https://github.com/bbbradsmith/nsfplay
- EZNSF: https://github.com/bbbradsmith/eznsf
- NES-MDB: https://github.com/chrisdonahue/nesmdb
- Capcom 6C80 format doc: https://www.romhacking.net/documents/274/
- NES2NSF: https://www.romhacking.net/utilities/545/
- FamiStudio: https://famistudio.org
- GDRI driver list: https://gdri.smspower.org/wiki/index.php/Famicom/NES_Sound_Driver_List
