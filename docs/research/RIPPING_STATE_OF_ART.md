# NSF Ripping and NES Music Extraction: State of the Art

Research date: 2026-04-13

## Our Current Approach

We download pre-ripped NSF files from joshw.info, emulate them via a 6502 CPU
running the game's sound driver, capture per-frame APU register state (CC11/CC12
volume and duty), and export to MIDI with full envelope automation. For games
needing higher fidelity, we use Mesen trace captures as ground truth and run
ROM-level reverse engineering of the sound driver. This document surveys what
else exists in the ecosystem.

---

## 1. NSF Ripping: ROM to NSF

### The Manual Process (Still Dominant)

There is no general-purpose automated ROM-to-NSF converter. NSF ripping remains
a manual reverse-engineering task requiring 6502 assembly knowledge. The process:

1. Load ROM in an emulator with debugger (Mesen, FCEUX)
2. Set write breakpoints on APU registers ($4000-$4015)
3. Identify the sound driver's INIT, PLAY, and LOAD addresses
4. Isolate the sound engine code and music data from the ROM
5. Dump the relevant memory region ($8000-$FFFF typically)
6. Prepend an NSF header with the three addresses and bank info
7. Test in an NSF player

Key references:
- [NES Music Ripping Guide](https://www.romhacking.net/documents/573/) -- the
  canonical tutorial, covers the full manual process
- [VGMRips NES Ripping Tutorial](https://vgmrips.net/wiki/Nintendo_Entertainment_System_ripping_tutorial) --
  modern version with Mesen-based workflow
- [Gil-Galad NSF Ripping Intro](http://anotherwormhole.com/gil-galad/nsf/level-20/intro.html) --
  step-by-step walkthrough

### Why Automation Is Hard

Each game uses a different sound driver. The driver code, music data format,
pointer tables, bank-switching scheme, and init/play calling convention are all
game-specific. A universal ROM-to-NSF tool would need to solve driver
identification and isolation automatically, which nobody has done.

The closest approach to partial automation is a nesdev forum thread discussing
dumping $8000-$FFFF after a breakpoint hit and hoping the sound engine is
self-contained. This works for simple mappers but fails for bankswitched games.
Source: [NES to NSF discussion](https://forums.nesdev.org/viewtopic.php?t=6627)

### Reverse Direction: NSF to NES ROM

Two tools exist for the opposite direction (embedding NSF playback in a ROM):
- **nsf2nes** ([GitHub](https://github.com/karmic64/nsf2nes)) -- converts NSF
  rips back to playable NES ROMs. Limitations: no bankswitching, no expansion
  audio, needs one free memory page.
- **EZNSF** ([GitHub](https://github.com/bbbradsmith/eznsf)) -- similar tool by
  Brad Smith. No expansion audio, standard engine rate only.

These are useful for testing but not relevant to our extraction pipeline.

### Relevance to Our Project

**No action needed.** The joshw.info archive already has NSF rips for the vast
majority of the NES library. Manual ripping is only needed for obscure or
unlicensed games missing from the archive. Our real value-add is the extraction
pipeline after the NSF stage, not the ripping itself.

---

## 2. NSFe and NSF2 Extended Formats

### NSFe (Extended NSF)

Created to add metadata that the original NSF format lacks:
- Per-track titles and durations
- Fade-out timing per track
- Playlist ordering
- Ripper credit
- UTF-8 text encoding

Structure: begins with 'NSFE' magic bytes, uses a chunked format.
Source: [NSFe spec on NESdev](https://www.nesdev.org/wiki/NSFe)

### NSF2

A backward-compatible extension that merges NSFe metadata into the NSF format
and adds hardware features:
- Programmable timer IRQ (cycle-counting timer at $401B-$401D)
- Non-returning INIT paradigm (INIT runs continuously, PLAY arrives as NMI)
- DMC and Frame Counter IRQ access
- Mandatory metadata chunks (via feature flag bit 7)
- 24-bit data length field at header offset $07D-$07F

The non-returning INIT is significant: some games run their sound driver as a
persistent loop rather than a per-frame callback. NSF2 models this correctly;
original NSF cannot. Source: [NSF2 spec on NESdev](https://www.nesdev.org/wiki/NSF2)

**Only NSFPlay 2.4+ supports NSF2.** Very few NSFs actually need it
(Rollerblade Racer is one confirmed case).

### Relevance to Our Project

**Low priority but worth awareness.** Our emulation pipeline should handle NSFe
metadata (track names, durations) if present. NSF2's non-returning INIT could
matter for games whose sound drivers use that paradigm -- but these are rare.
The joshw.info archive serves standard NSF files.

---

## 3. NSF-to-MIDI Converters (Competing Approaches)

### nsf2midi (Japanese tool)

A Windows program that plays NSF files through emulation and converts the
output to MIDI. Supports RP2A03, VRC VI, RP2C33, NAMCO163, and 5B expansion
chips. Features include pitchbend detection, envelope matching, and configurable
MIDI instrument assignment. Can output to General MIDI, Roland GS, or Yamaha XG.
Available in English, Japanese, and Russian. Last updated ~2016.

Does NOT support NSFe.

Source: [VGMPF NSF to MIDI page](https://www.vgmpf.com/Wiki/index.php/NSF_to_MIDI),
[Zophar's Domain](https://www.zophar.net/utilities/converters/nsf2midi.html)

**Comparison to our approach:** nsf2midi tries to produce "nice" General MIDI
output with instrument assignments and pitchbend -- it is a transcription tool,
not a fidelity tool. It loses per-frame volume/duty automation. Our pipeline
preserves the raw APU envelope as CC11/CC12, which is fundamentally different
and far more faithful to the original sound.

### vgm2midi (emulation-based)

Built on byuu's higan emulator for high-accuracy console emulation. Supports
NSF and SPC (SNES). Extracts MIDI from hardware state during emulated playback.
990 commits, GPLv3. Documentation is sparse; methodology unclear.

Source: [GitHub](https://github.com/JamesDunne/vgm2midi)

**Comparison:** Interesting architectural parallel to our approach (emulation
then extraction). Worth investigating whether their pitch detection from APU
registers is comparable to ours.

### ValleyBell MidiConverters

A collection of game-specific ROM-to-MIDI converters. NES support is limited to
Hummer Team games (Somari and similar). Each converter is written against a
specific sound driver's data format -- it parses the ROM music data directly
rather than emulating.

Source: [GitHub](https://github.com/ValleyBell/MidiConverters)

**Comparison:** This is the ROM-parsing approach (our Layer 3). ValleyBell's
converters are per-driver, same as our Konami parser. The difference is we also
have the NSF emulation pipeline as a fallback.

### NES Music Database (NES-MDB)

An academic dataset of 5,278 songs from 397 NES games (296 composers, 2M+ notes).
Extracted by parsing game assembly code, not emulation capture. Available in MIDI,
expressive score (dense piano roll at 24 Hz with all synthesis parameters),
separated score, blended score, NES Language Modeling format, and raw VGM.

The Python package can render any format through NES synthesizer emulation.

Source: [GitHub](https://github.com/chrisdonahue/nesmdb),
[ISMIR 2018 paper](https://cseweb.ucsd.edu/~jmcauley/pdfs/ismir18.pdf)

**Comparison:** NES-MDB's "expressive score" format (Nx4x3 array at 24 Hz with
timing, pitch, and synthesis parameters) is conceptually similar to our Frame IR.
Their methodology differs: they parsed assembly code rather than capturing APU
state from emulation. Their 24 Hz resolution is lower than our frame-accurate
60 Hz capture. The dataset could be useful for bulk comparison or validation.

---

## 4. Tracker-Based Import Tools

### NSF Importer for FamiTracker (rainwarrior)

A modified FamiTracker 0.3.7 that embeds an NSF player and records APU register
state at 60 fps into a FamiTracker document (.FTM). The imported result has
all volumes and pitches set through the effect panel -- no instruments, no
envelopes, no repeating patterns. Useful for studying how game sounds were
achieved, not for clean transcription.

Does not support Sunsoft 5B or NAMCO163 expansion. No longer maintained.
Source: [rainwarrior.ca](https://rainwarrior.ca/projects/nes/nsfimport.html)

**Comparison:** Same fundamental approach as our pipeline (emulate NSF, capture
register state per frame). The difference is output format: they write to
FamiTracker's tracker grid, we write to MIDI with CC automation. Their 60 Hz
capture rate matches ours.

### FamiStudio NSF Import

FamiStudio (v4.5.0, actively developed) can import NSF and NSFe files directly
in its desktop version, including expansion audio. The import captures the NSF
through emulation, producing a tracker document with per-frame parameter data.

Configurable options: duration, pattern length, start frame offset. Ignores
hardware sweeps and advanced DPCM manipulation.

The developers explicitly note that NSF import is useful for reverse-engineering
how songs were composed -- the demo songs shipped with FamiStudio were created
this way.

Source: [FamiStudio import docs](https://famistudio.org/doc/import/),
[GitHub](https://github.com/BleuBleu/FamiStudio)

**Comparison:** FamiStudio is the most actively maintained tool in this space.
Its NSF import is essentially doing what we do (emulate + capture) but targeting
a tracker format. It could be useful for visual inspection of extraction results
or as a cross-check against our MIDI output.

### Furnace Tracker

Multi-system chiptune tracker supporting 60+ chip types. Cannot import NSF
directly. Workaround: use rainwarrior's NSF Importer to create .FTM, then import
that into Furnace. The result is messy (speed 1, no instruments).

Source: [Furnace](https://tildearrow.org/furnace/),
[GitHub](https://github.com/tildearrow/furnace)

**Relevance:** Not useful for our pipeline. Furnace is a composition tool.

---

## 5. Emulator-Based Extraction

### Mesen / Mesen2

Mesen is the gold standard NES emulator for accuracy. Its debugging features
that are relevant to us:

- **APU Viewer**: real-time display of per-channel register state
- **Trace Logger**: logs CPU execution trace to file (instruction-level)
- **Breakpoints**: can break on APU register writes ($4000-$4015)
- **Lua scripting**: programmable hooks for custom data capture
- **Memory viewer**: dump arbitrary memory ranges

We already use Mesen trace captures as ground truth. The trace logger produces
per-instruction logs; our pipeline converts these to per-frame APU state.

Mesen does NOT have a built-in "export to MIDI" or "export NSF" function. All
music extraction requires external processing of trace/debug output.

Source: [Mesen docs](https://www.mesen.ca/docs/debugging.html),
[GitHub Mesen2](https://github.com/SourMesen/Mesen2)

### FCEUX

Older emulator, less accurate than Mesen but with useful features:
- Lua scripting for register capture
- Built-in NSF player
- Sound channel toggles for isolation

### NSFPlay (Brad Smith)

Dedicated NSF player and Winamp plugin. Key features:
- Full NSF2 support (non-returning INIT, IRQ, metadata)
- Per-channel mixer with panning
- WAV export (command-line batch mode)
- High-accuracy NES APU emulation

Source: [NSFPlay site](http://bbbradsmith.github.io/nsfplay/),
[GitHub](https://github.com/bbbradsmith/nsfplay)

**Relevance:** NSFPlay's WAV export could be used for reference audio generation.
Its per-channel mixer is what we achieve through MIDI channel separation.

---

## 6. Channel Isolation

### Software (Emulator-Based)

Every modern NES emulator (Mesen, FCEUX, NSFPlay) supports per-channel muting/
soloing. This is the standard way to isolate NES audio channels. Our pipeline
does this inherently by extracting each channel to a separate MIDI track.

### Hardware

The NES APU has two physical output pins: one for pulse channels, one for
triangle/noise/DPCM. Hardware stereo mods exploit this natural separation.
Some enthusiasts have built full 5-channel separation circuits, but this
requires significant hardware modification.

Source: [ConsoleMods NES Stereo Mod](https://consolemods.org/wiki/NES:%22Stereo%22_Audio_Mod)

**Relevance:** None for our pipeline. Software isolation through emulation is
superior for extraction purposes.

---

## 7. NES Sound Driver Ecosystem

### Scale of the Problem

The VGMPF wiki documents **130+ distinct NES sound driver families** across
the full NES/Famicom library. Major driver lineages:

| Company | Notable Driver Authors | Characteristics |
|---------|----------------------|-----------------|
| Konami | Hidenori Maezawa, Atsushi Fujio | MML-like command stream, many variants per game |
| Capcom | Yoshihiro Sakaguchi | Hex MML input from keyboard composition |
| Sunsoft | Akito Takeuchi, Shinichi Seya | Known for advanced DPCM usage |
| Nintendo | Koji Kondo, Hirokazu Tanaka | Multiple internal driver versions |
| Rare | David Wise et al. | Custom dispatch table engine (Battletoads) |
| Square | Toshiaki Imai | Unique per-game driver variants |
| Namco | Multiple programmers | Company-wide shared engine |

The NESdev wiki lists 15+ homebrew audio drivers (FamiStudio engine, FamiTone2,
GGSound, Pently, etc.) that are well-documented. Commercial game drivers are
far less documented and require reverse engineering.

Sources:
- [VGMPF NES Sound Driver List](https://www.vgmpf.com/Wiki/index.php?title=Famicom/NES_Sound_Driver_List)
- [NESdev Audio Drivers](https://www.nesdev.org/wiki/Audio_drivers)
- [GDRI NES Sound Driver List](https://gdri.smspower.org/wiki/index.php/Famicom/NES_Sound_Driver_List)

**Relevance:** This confirms our architecture decision: there is no universal
decoder. Each driver family needs either (a) its own ROM parser, or (b) the NSF
emulation escape hatch that treats all drivers uniformly. Our two-layer approach
(NSF emulation for all games, ROM parsing for high-fidelity games) is correct.

---

## 8. Academic Research

### The NES Music Database (ISMIR 2018)

Donahue et al. created NES-MDB with 5,278 songs from 397 games. Provides MIDI
at 44.1 kHz timing resolution and "expressive score" at 24 Hz with all synthesis
parameters. Used for training music generation models.

Source: [Paper (PDF)](https://cseweb.ucsd.edu/~jmcauley/pdfs/ismir18.pdf)

### NES Video-Music Database (FDG 2024)

Extension pairing 98,940 gameplay videos from 389 NES games with symbolic
soundtrack data. Targets video-music alignment research.

Source: [arXiv:2404.04420](https://arxiv.org/abs/2404.04420)

### LakhNES (ISMIR 2019)

Transfer learning applied to NES music generation. Improved multi-instrumental
generation quality by 10% through pretraining on the Lakh MIDI dataset before
fine-tuning on NES-MDB.

Source: [Paper (PDF)](https://archives.ismir.net/ismir2019/paper/000083.pdf)

### Sunsoft Compositional Analysis

Academic study of chiptune compositional techniques in Sunsoft NES games
(1988-1992), examining how hardware constraints shaped musical decisions.

Source: [Academia.edu](https://www.academia.edu/15400351/)

**Relevance:** NES-MDB is the most directly relevant. Their dataset could serve
as a bulk validation reference for our extraction pipeline. The 24 Hz expressive
score format is lower resolution than our 60 Hz frame-accurate CC automation,
but the dataset's breadth (397 games) far exceeds our current coverage.

---

## 9. Comprehensive Tool Reference

### loveemu VGMDocs

The most complete catalog of video game music conversion tools. NES-specific
entries include all tools mentioned above plus obscure per-driver converters.
Maintained by loveemu, who has reversed multiple commercial music engines.

Source: [VGMDocs Conversion Tools](https://loveemu.github.io/vgmdocs/Conversion_Tools_for_Video_Game_Music.html),
[GitHub](https://github.com/loveemu/vgmdocs)

### VGMTrans

Cross-platform tool for detecting and converting sequenced game music. Strong
support for PS1, PS2, SNES, GBA, DS. NES support is minimal -- the NES
ecosystem uses NSF rather than raw sequence data, so VGMTrans defers to
NSF-specific tools.

Source: [VGMTrans](https://vgmtrans.github.io/vgmtrans/),
[GitHub](https://github.com/vgmtrans/vgmtrans)

### nsf-ripper (asanoic)

Small C++ tool that extracts NSF audio to FLAC format. Minimal community
adoption (1 star). Essentially an NSF player with file output.

Source: [GitHub](https://github.com/asanoic/nsf-ripper)

---

## 10. Summary: Where We Stand

| Capability | Best Available Tool | Our Approach | Gap? |
|-----------|-------------------|-------------|------|
| NSF archive | joshw.info | Download pre-ripped NSFs | None |
| NSF emulation to audio | NSFPlay, Mesen | Custom 6502 emulation + APU capture | None |
| NSF to MIDI (lossy) | nsf2midi | N/A (we do lossless CC extraction) | None -- ours is better |
| NSF to tracker | FamiStudio, NSF Importer | N/A | Could use FamiStudio as cross-check |
| Per-frame APU capture | Mesen trace logger | Mesen trace as ground truth | None |
| ROM-level parsing | ValleyBell (per-driver) | Per-driver parsers (Konami, Rare) | Ongoing per-game work |
| Channel isolation | All emulators | Separate MIDI tracks | None |
| Bulk dataset | NES-MDB (5,278 songs) | Per-game extraction | Could cross-reference |
| NSF2/NSFe support | NSFPlay 2.4+ | Not yet implemented | Low priority |
| MIDI + envelope fidelity | Nobody else does this | CC11/CC12 per-frame automation | Unique to us |

### What Nobody Else Does

Our pipeline's distinctive feature is preserving per-frame APU volume and duty
cycle as MIDI CC automation (CC11, CC12). Every other NSF-to-MIDI tool in the
ecosystem either:

1. Produces "clean" General MIDI with approximated instrument patches (nsf2midi)
2. Dumps to a tracker format that is hard to use in a DAW (FamiStudio, NSF Importer)
3. Provides raw VGM register dumps without musical interpretation (NSFPlay, Mesen)

We bridge the gap: frame-accurate NES envelope data in a format that REAPER (or
any DAW) can play back through our custom synth plugin.

### Integration Candidates

| Tool | Integration Idea | Priority |
|------|-----------------|----------|
| FamiStudio | Cross-check extraction results visually | Low |
| NES-MDB dataset | Bulk validation against 5,278 songs | Medium |
| NSFPlay WAV export | Generate reference audio for ear-checks | Low |
| vgm2midi | Study their emulation-to-MIDI methodology | Low |
| VGMPF driver list | Cross-reference with our driver survey | Medium |

### Gaps Worth Filling

1. **NSFe metadata parsing**: Track names and durations from NSFe files would
   improve our output labeling. Medium effort, medium value.
2. **NES-MDB cross-validation**: Compare our per-game MIDI output against their
   dataset for the ~397 games they cover. Could catch systematic errors.
3. **Driver identification database**: The VGMPF list of 130+ drivers could feed
   our driver survey, helping predict which extraction approach to use per game.
