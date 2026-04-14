# Web Research: NES ROM Hacking, Music Extraction, and Driver Knowledge

Research conducted 2026-04-13 across ROM hacking forums, music archives,
and NES development communities. Full detailed reports in `docs/research/`.

## Executive Summary

We surveyed the entire NES music extraction ecosystem. Key findings:

1. **Our pipeline is unique.** No other tool preserves per-frame APU volume
   and duty cycle as MIDI CC automation for DAW playback. nsf2midi produces
   lossy General MIDI. FamiStudio captures the same data but exports to
   tracker format, not REAPER.

2. **No automated ROM-to-NSF converter exists.** NSF ripping is still manual
   reverse engineering. The joshw.info archive (1577 games) is the practical
   solution, not building our own ripper.

3. **130+ distinct NES sound driver families** are documented across VGMPF
   and GDRI. Company attribution does NOT predict our CC11 density families.
   The same Rare driver produces 0.1 (W&W) and 4.1 (Battletoads) CC11/note.

4. **Our "Sunsoft-style" label is wrong.** Real Sunsoft games (Journey to
   Silius 7.8, Blaster Master 11.7) are denser than the 3.7-5.6 family
   we named after them. Should rename to "Standard Envelope."

5. **NES-MDB (Stanford, 5278 songs)** is the closest academic parallel.
   They treat all NSF as ground truth; we use Mesen trace as higher authority.

---

## Source Directory

### Archives (where to get NSF files)

| Source | URL | Games | Format | Status |
|--------|-----|-------|--------|--------|
| **nsf.joshw.info** | https://nsf.joshw.info/ | 1577+ | NSF in .7z | Active (Mar 2026), OUR PRIMARY |
| **Zophar's Domain** | https://www.zophar.net/music/nintendo-nes-nsf | ~500+ | Plain NSF | Stagnant since ~2005 |
| **VGMRips** | https://vgmrips.net/packs/ | 4327 packs (all platforms) | VGM/VGZ | Active, different format |
| **Internet Archive** | https://archive.org/details/thenesprojectnsfs | ~700 | NSF | Static collection |

**Recommendation:** Stay with joshw.info. Consider VGMRips for track metadata
(names, durations, composers) that joshw NSFs lack.

Full report: [docs/research/ARCHIVES.md](docs/research/ARCHIVES.md)

### NESDev Community (technical knowledge)

The NESDev wiki and forums are the authoritative source for NES hardware
documentation and sound engine knowledge.

**Gold mine pages:**
- [NSF Format Spec](https://www.nesdev.org/wiki/NSF) -- header, init/play, bankswitching
- [APU Registers](https://www.nesdev.org/wiki/APU_registers) -- all $4000-$4017 details
- [APU Period Table](https://www.nesdev.org/wiki/APU_period_table) -- note-to-period math
- [Audio Drivers List](https://www.nesdev.org/wiki/Audio_drivers) -- homebrew engines with source
- [Expansion Audio Games](https://www.nesdev.org/wiki/List_of_games_with_expansion_audio) -- VRC6/VRC7/FDS/MMC5/N163/5B

**Key forum threads:**
- [Battletoads PCM drums](https://forums.nesdev.org/viewtopic.php?t=15586) -- algorithmic synthesis, not stored samples
- [NES to NSF conversion](https://forums.nesdev.org/viewtopic.php?t=6627) -- manual ripping process
- [Behind the scenes NSF ripping](https://forums.nesdev.org/viewtopic.php?t=16630) -- rippers discuss their process
- [Music driver poll](https://forums.nesdev.org/viewtopic.php?t=17812) -- what homebrew devs use

Full report: [docs/research/NESDEV.md](docs/research/NESDEV.md)

### Romhacking.net (documents and tools)

**Critical documents:**
- [Capcom "6C80" Sound Engine Documentation](https://www.romhacking.net/documents/274/) -- most detailed byte-level commercial NES sound engine doc. Covers Mega Man 3+, Mighty Final Fight. **Essential if we ever parse Capcom ROMs directly.**
- [Castlevania Music Format](https://www.romhacking.net/documents/150/) -- melody hacking for CV1
- [NES Music Ripping Guide](https://www.romhacking.net/documents/573/) -- beginner's NSF ripping tutorial
- [Hacking NES Music](https://www.romhacking.net/documents/39/) -- general NES music editing

**Tools:**
- [NSF Tool](https://www.romhacking.net/utilities/546/) -- view/edit NSF metadata
- [NES2NSF](https://www.romhacking.net/utilities/545/) -- ROM-to-NSF (mapper 0 only, buggy, outdated)

### Sound Engine Databases (who made what)

**VGMPF Famicom/NES Sound Driver List** is the definitive attribution database:
https://www.vgmpf.com/Wiki/index.php?title=Famicom/NES_Sound_Driver_List

Maps games to driver programmers. Key entries:

| Publisher | Driver Author | Games | Our Survey Finding |
|-----------|-------------|-------|-------------------|
| Capcom | Yoshihiro Sakaguchi | 30+ | Reliably Minimal (CC11 0.2-2.2) |
| Konami | Maezawa / Fujio | 30+ variants | Spans 3 families (wildly variable) |
| Rare | Stamper / Betteridge | ~48 | Minimal (W&W) to Sunsoft-style (Battletoads) |
| Sunsoft | Takeuchi / Morota / Seya | ~20 | Actually Dense (7.8-11.7), NOT our "Sunsoft-style" |
| Square | Toshiaki Imai | FF, Rad Racer | Densest in survey (14.9 CC11/note) |
| Nintendo | Koji Kondo et al. | SMB, Zelda, etc. | Spans Families 3-5 |
| Tecmo | Keiji Yamagishi | ~15 | Spans Families 2-4 |
| HAL Lab | Suga | Kirby's Adventure | Duty Switcher (unique) |

**Key insight:** Same driver, different density. Rare's engine produces CC11
0.1 (W&W) and 4.1 (Battletoads). Driver architecture sets the ceiling;
composer technique determines where within that ceiling the music lands.

Full report: [docs/research/ENGINES.md](docs/research/ENGINES.md)

### State of the Art (what else exists)

**No automated ROM-to-NSF tool exists.** Best practice is still manual:
disassemble ROM, find init/play addresses, package with NSF header. The
joshw.info community has already done this for 1577+ games.

**Our competitive advantages:**
- Per-frame CC11/CC12 as MIDI automation (nobody else does this)
- REAPER integration with custom NES synth
- Mesen trace as higher-fidelity ground truth than NSF alone
- Driver family classification by CC density (novel)

**Tools worth investigating:**
- [FamiStudio](https://famistudio.org/) -- visual NSF editor, good for cross-checking extraction
- [NSFPlay](https://github.com/bbbradsmith/nsfplay) -- LOG_CPU mode for per-frame register dumps
- [NES-MDB](https://github.com/chrisdonahue/nesmdb) -- Stanford dataset, 5278 songs, validation reference
- [vgm2mid / vgm2txt](https://github.com/vgmrips/vgmtools) -- VGM tools for comparison

Full report: [docs/research/RIPPING_STATE_OF_ART.md](docs/research/RIPPING_STATE_OF_ART.md)

---

## Actionable Next Steps

### Immediate
1. Scrape VGMPF driver list to tag our 65 surveyed games with actual driver
   attribution (Sakaguchi, Maezawa, etc.)
2. Rename "Sunsoft-style" family to "Standard Envelope" -- real Sunsoft games
   don't belong there
3. Download vgm2mid from vgmtools and nsf2midi from Zophar -- compare output

### Medium-term
4. Download NES-MDB dataset -- cross-validate our extraction against 5278 songs
5. Investigate NSFE collection (1600+ files with track names) for song labeling
6. Read the Capcom 6C80 format doc for direct ROM parsing of Mega Man 3+ games

### Long-term
7. Build VGM-to-frame-state converter for independent validation without Mesen
8. Contribute corrections back to joshw.info when our pipeline finds NSF issues
9. Survey all 1577 joshw games to build the complete driver density map

---

## Sources

All URLs documented in the detailed reports under `docs/research/`:
- [ARCHIVES.md](docs/research/ARCHIVES.md) -- Zophar, joshw.info, VGMRips
- [NESDEV.md](docs/research/NESDEV.md) -- NESDev wiki, forums, driver knowledge
- [ENGINES.md](docs/research/ENGINES.md) -- Sound engine databases, per-company docs
- [RIPPING_STATE_OF_ART.md](docs/research/RIPPING_STATE_OF_ART.md) -- Tools, methods, academic work
