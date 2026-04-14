# NES Music Archive Sources

Research date: 2026-04-13. Sources investigated via web search for
relevance to the ReapNES Studio pipeline (NSF -> MIDI -> REAPER).

---

## 1. Zophar's Domain (zophar.net)

### URLs

- NSF music archive: https://www.zophar.net/music/nintendo-nes-nsf
- NSF utilities: https://www.zophar.net/utilities/nsf.html

### What They Have

Zophar's Domain is one of the oldest emulation resource sites on the
web, dating back to the late 1990s. Their NES NSF music section hosts
plain (uncompressed) NSF files organized alphabetically by game name.
Individual game pages (e.g., `/music/nintendo-nes-nsf/1942`) provide
direct download links.

The collection size is not precisely documented in public-facing pages.
Community forum posts on nesdev.org characterize Zophar's NSF archive
as approximately 105 MB in RAR format. The broader NSF ecosystem
contains 4,400+ NSFs across all archives; Zophar's share of that is
a substantial but not exhaustive subset.

### Tools and Utilities Hosted

Zophar hosts a dedicated NSF utilities page with players, converters,
and editing tools:

**Players:**
- NSFplay -- standalone Windows NSF player (sound engine from NSFplug)
- NotSo Fatso -- open-source Winamp plugin, high-quality NSF/NSFE playback
- Nosefart -- lightweight NSF player
- G-NSF -- NSF player based on G-NES emulator engine
- NSFten -- Winamp plugin, emulates NES APU + VRC6
- NEZplug -- multi-format plugin (NSF, KSS, GBR, GBS, HES, AY)

**Converters:**
- nsf2midi -- loads NSF files and exports MIDI output

**Utilities:**
- NSF Tool -- view/edit NSF info tags, batch rename NSF files

### Quality Assessment

**Strengths:**
- Historical significance; many early NSF rips originated here
- Clean, direct file downloads (no 7z wrapping)
- Hosts legacy tools that are hard to find elsewhere
- nsf2midi is directly relevant to our pipeline research

**Weaknesses:**
- The site has not been substantially updated since approximately 2005
- NSF files may lack modern corrections (wrong track counts, missing
  expansion audio flags, timing errors fixed in later rip revisions)
- No NSFE support (no track names, no track times)
- Many hosted tools target Winamp or Windows XP-era platforms
- Community consensus on nesdev.org is that Zophar's NSF collection
  is "very out of date" compared to joshw.info

### Relevance to ReapNES

**Low-medium.** We already pull from joshw.info (1577 games), which is
more current and complete. Zophar's value is:

1. **nsf2midi tool** -- worth examining as prior art for NSF-to-MIDI
   conversion, even though our pipeline uses direct 6502 emulation
   with per-frame CC extraction rather than note detection
2. **NSF Tool** -- useful for batch-inspecting NSF metadata/tags
3. **Gap-filling** -- some obscure titles on Zophar may not be on joshw
4. **Historical reference** -- earliest rips for provenance research

**Should we pull data?** No bulk import needed. Cherry-pick specific
games if they are missing from our joshw.info collection. The nsf2midi
tool is worth downloading for comparison testing.

---

## 2. nsf.joshw.info

### URLs

- Main archive: https://nsf.joshw.info/
- Parent project: https://vgm.hcs64.com/ (alternative entry point)
- Community thread: https://hcs64.com/mboard/forum.php?showthread=26929

### What They Have

The joshw.info domain hosts an enormous video game music data archive
spanning dozens of platforms, each on its own subdomain (nsf.joshw.info,
spc.joshw.info, psf.joshw.info, usf.joshw.info, etc.). The NES
subdomain serves NSF files organized as an Apache-style directory
listing, alphabetical by first letter, then by game name within each
letter directory.

Our batch pipeline (`scripts/fetch_and_extract.py`) already pulls from
this source. Current count: **1577 games** in our local mirror.

Each game is individually 7z-compressed. The archive is linked to
the HCS64 community (Halley's Comet Software), which is the primary
hub for video game music research and preservation tooling.

### Who Maintains It

- **Josh W (joshw)** -- hosts the infrastructure and web server
- **Knurek** -- primary content maintainer and contributor who
  updates the archive with new rips and corrections
- Additional contributions from the broader HCS64 community of
  extractors and rippers

Directory timestamps show updates as recent as March 2026, confirming
the archive is actively maintained.

### Ripping Methodology and Quality Standards

The joshw.info archive stores NSF files -- the original NES sound
format created by Kevin Horton. NSF files contain the actual 6502
machine code from the game ROM that generates sound. Playing an NSF
file requires emulating the NES CPU, which makes NSF extraction a
non-trivial reverse engineering task: the ripper must identify the
init, play, and load addresses in the ROM and package them correctly.

Quality standards are community-enforced rather than formally
documented. The nesdev.org forum threads show ongoing discussion
about:
- Correct expansion chip flags (VRC6, VRC7, FDS, MMC5, N163, FME-7)
- Accurate track counts (some NSFs include SFX tracks that should
  be excluded or marked)
- Proper bankswitch configuration for games with complex memory maps
- PAL vs NTSC timing flags

The archive contains plain NSF files only (not NSFE). This means
**no track names and no track durations** are embedded in the files.
Track naming requires external M3U playlists or manual identification.
A separate community effort has produced an NSFE collection (1600+
files as of 2023) that wraps NSF data with track metadata, but this
is maintained independently.

### Quality Assessment

**Strengths:**
- Largest and most actively maintained NSF archive available
- Community of expert rippers ensures high baseline quality
- Connected to HCS64 ecosystem (tools, forums, expertise)
- Consistent 7z packaging format
- Regular updates with new rips and corrections

**Weaknesses:**
- NSF-only (no NSFE metadata -- no track names or times)
- No formal quality grading per file (no "verified" vs "unverified" flags)
- Directory listing only; no searchable database or API
- Some NSFs may have known issues that are documented only in
  nesdev.org forum threads, not in the archive itself
- 7z compression adds an extraction step to our pipeline

### Relevance to ReapNES

**Critical -- this is our primary source.** Our `fetch_and_extract.py`
script already pulls from joshw.info and we have 1577 games locally.

**Ongoing value:**
1. Monitor for new additions and updated rips
2. Cross-reference with the NSFE collection for track names
3. The HCS64 community is the best place to report and resolve
   NSF quality issues we discover during our pipeline runs

**Should we pull data?** Already doing it. Consider:
- Periodic re-sync to catch updated/corrected NSFs
- Downloading the community NSFE collection for track metadata
- Building a local quality database that flags NSFs with known issues

---

## 3. VGMRips (vgmrips.net)

### URLs

- Main packs page: https://vgmrips.net/packs/
- NES system page: https://vgmrips.net/packs/system/nintendo/nintendo-entertainment-system
- NES ripping tutorial: https://vgmrips.net/wiki/Nintendo_Entertainment_System_ripping_tutorial
- VGM specification: https://vgmrips.net/wiki/VGM_Specification
- VGM tools (GitHub): https://github.com/vgmrips/vgmtools
- Logging guide: https://vgmrips.net/wiki/Logging_VGMs

### What They Have

VGMRips is the largest active site for retro video game music rips.
As of late 2025, the full archive contains approximately **4,327 packs
with 72,024 songs** across all platforms (NES, Genesis, Master System,
Game Boy, arcade, etc.). The NES-specific count is a subset of this;
not precisely reported but browsable at the NES system page.

The fundamental difference from joshw.info: VGMRips uses the **VGM
format**, not NSF. VGM (Video Game Music) is a sample-accurate sound
logging format that records the actual register writes sent to the
sound chip during playback. This is a critical architectural
distinction:

| Aspect | NSF (joshw.info) | VGM (VGMRips) |
|--------|------------------|---------------|
| Contains | 6502 machine code | Register write log |
| Playback | Requires CPU emulation | Replays register writes |
| File content | The program that makes sound | The sound that was made |
| Registers | $4000-$4013, $4015 | Same, logged with timestamps |
| Expansion chips | Flagged in header | Logged if chip supported |
| Accuracy | Depends on emulator quality | Sample-accurate to logging |
| Editability | Can modify code (hard) | Can trim/splice logs (easy) |
| Size | Small (code only) | Larger (timestamped log) |

### How VGM Ripping Works (NES)

The NES ripping tutorial on VGMRips wiki, written by Sonic of 8,
documents two paths:

**Path 1: From NSF files (preferred for NES)**
1. Use NEZPlay with VGMLogging=1 in nezplay.ini
2. Drag-drop the NSF file onto NEZPlay
3. Music is logged to VGM as each track plays
4. Let looping tracks play for at least 3 loops
5. Process with vgm_trim and vgm_cmp from vgmtools

**Path 2: From game ROM via MAME (for games without NSF)**
1. Use MAME's VGM logging mod
2. Play through the game to reach each music track
3. Log the register writes during playback
4. Limitation: VRC6 and N163 expansion chip logging not supported

**Important caveat** documented in their forums: when creating NES
packs from NSF files, the $4017 register behavior may differ between
the NSF and the actual game ROM. This is a known fidelity concern
that aligns with our own finding that NSF emulation can diverge from
in-game audio (documented in our Mesen-vs-NSF comparisons for
Battletoads and Mario).

### Pack Structure and Metadata

Each VGMRips pack includes:
- VGM/VGZ files (one per track, gzip-compressed)
- Title screen screenshot(s) (256x240, taken via MAME)
- Metadata tags (game name, system, composer, developer)
- Track listing with names and durations
- Pack assembled and reviewed by community contributors

This metadata richness is superior to both joshw.info (no metadata)
and Zophar (minimal metadata).

### VGMTools (GitHub)

The vgmrips/vgmtools repository provides a comprehensive C toolchain:

- **vgm_trim** -- trim VGM files, add save-state headers
- **vgm_cmp** -- compress/optimize VGM by stripping redundant commands
- **vgm2txt** -- convert VGM to human-readable text (register dump)
- **vgm_stat** -- statistics about a VGM file
- **vgm_tag** -- read/write VGM metadata tags
- **vgm_vol** -- adjust volume
- **vgm2mid** -- convert VGM to MIDI (supports NES APU)
- Plus ~15 more specialized tools

The **vgm2mid** tool is particularly relevant: it converts VGM register
logs to MIDI, which is exactly our pipeline's goal but from a different
source format. Worth examining for algorithm comparison.

### Quality Assessment

**Strengths:**
- Sample-accurate register logging (higher fidelity ceiling than NSF
  for the specific playback that was logged)
- Rich metadata per pack (track names, composers, durations)
- Active community with review process for submitted packs
- Comprehensive open-source toolchain
- Documented ripping tutorials
- Full download available (4.09 GB as of 2025-10-17)

**Weaknesses:**
- VGM is a log, not a program -- it captures ONE specific playback,
  not the music engine. If the NSF plays tracks differently (tempo
  variation, randomization), the VGM only has what was logged.
- NES coverage may be less complete than joshw.info (VGMRips requires
  manual pack assembly and review; joshw.info is more of a raw dump)
- VGM format is not directly usable in our current pipeline (we
  emulate NSF via 6502; we would need a VGM-to-frame-state converter)
- Expansion chip logging gaps (VRC6, N163 not supported in MAME path)
- The $4017 caveat means NSF-sourced VGMs inherit NSF inaccuracies

### Relevance to ReapNES

**Medium-high for research and cross-validation; low for direct
pipeline integration.**

VGMRips offers something we do not currently have: pre-logged register
write sequences with timestamps. This is conceptually very close to
our Mesen trace captures (which also log register state per frame).

**Specific value propositions:**

1. **vgm2txt as validation tool** -- convert a VGM to text, compare
   register writes against our NSF-extracted frame state. This gives
   us an independent reference for games where we lack Mesen traces.

2. **vgm2mid for algorithm comparison** -- examine how their VGM-to-MIDI
   conversion handles note boundary detection, volume envelopes, and
   noise mapping. Compare against our CC11/CC12 approach.

3. **Track metadata** -- VGMRips packs include track names and durations
   that our joshw.info NSFs lack. We could scrape this metadata to
   populate our M3U files and database.

4. **Cross-validation for fidelity** -- for games where our NSF
   pipeline output sounds wrong, compare against the VGM log to
   determine whether the issue is in our extraction or in the NSF
   itself.

5. **$4017 research** -- their documented concern about $4017
   divergence between NSF and ROM is directly relevant to our
   Mesen-vs-NSF discrepancy findings.

**Should we pull data?** Not for bulk pipeline integration (wrong
format). Targeted downloads for:
- Track name metadata scraping (populate our song database)
- Specific games where we need independent fidelity reference
- vgm2mid and vgm2txt tools for comparison/validation workflows
- The full 4 GB pack as a reference corpus

---

## Comparative Summary

| Criterion | Zophar's Domain | nsf.joshw.info | VGMRips |
|-----------|----------------|----------------|---------|
| Format | NSF (plain) | NSF (7z) | VGM/VGZ |
| NES coverage | Medium (dated) | Highest (~1577+) | Partial (curated) |
| Last updated | ~2005 | March 2026 | Active (2025+) |
| Track metadata | None | None | Full (names, times, composers) |
| Quality control | None visible | Community-maintained | Reviewed packs |
| Tools hosted | Players, nsf2midi | None (data only) | vgmtools suite (GitHub) |
| Direct pipeline use | Yes (NSF) | Yes (NSF, primary) | No (needs VGM converter) |
| Validation value | Low | N/A (is our source) | High (independent reference) |
| Bulk download | Yes | Yes (per-game 7z) | Yes (4.09 GB full pack) |

## Recommendations

### Immediate Actions

1. **Keep joshw.info as primary source.** It is the most complete,
   most current NSF archive and already integrated into our pipeline.

2. **Download vgm2mid and vgm2txt from vgmrips/vgmtools.** These are
   directly useful for validation and algorithm comparison.

3. **Download nsf2midi from Zophar.** Compare its MIDI output against
   ours for the same games to validate our approach.

### Medium-Term

4. **Scrape VGMRips track metadata** for NES packs. Use track names
   and durations to populate our pipeline database and generate M3U
   files for the joshw.info NSFs.

5. **Investigate the community NSFE collection** (1600+ files with
   track names/times). This would give us metadata without needing
   to scrape VGMRips.

6. **Set up periodic joshw.info re-sync** to catch corrected NSFs.

### Long-Term

7. **Build a VGM-to-frame-state converter** to use VGMRips data as
   an independent validation source (alternative to Mesen traces for
   games we have not traced).

8. **Contribute back:** when our pipeline identifies NSF issues
   (wrong track counts, expansion chip flags, timing), report to
   the HCS64 community and VGMRips forums.

---

## Additional Resources Discovered

- **VGMPF Wiki** (vgmpf.com) -- Video Game Music Preservation Foundation,
  documents NSF format specification and links to archives
- **nesdev.org NSF forums** -- active discussion of NSF quality issues,
  ripping techniques, and format extensions (NSF2, NSFE)
- **NSFPlay** (bbbradsmith.github.io/nsfplay) -- modern NSF player with
  channel visualization, useful for debugging our pipeline output
- **NSFE format** (nesdev.org/wiki/NSFe) -- extended NSF with track
  names and durations, created by Disch, popularized by NotSoFatso
- **NSF2 format** (nesdev.org/wiki/NSF2) -- newer extension incorporating
  NSFE metadata into the NSF header structure

## Sources

- [Zophar NES NSF Archive](https://www.zophar.net/music/nintendo-nes-nsf)
- [Zophar NSF Utilities](https://www.zophar.net/utilities/nsf.html)
- [nsf.joshw.info](https://nsf.joshw.info/)
- [joshw.info Archive Thread (HCS64)](https://hcs64.com/mboard/forum.php?showthread=26929)
- [Bizarchivist Sound Project (joshw.info overview)](https://steamcommunity.com/groups/bizarchivistsoundproject/discussions/3/1318835718933308990/)
- [VGMRips Packs](https://vgmrips.net/packs/)
- [VGMRips NES Ripping Tutorial](https://vgmrips.net/wiki/Nintendo_Entertainment_System_ripping_tutorial)
- [VGMRips VGM Specification](https://vgmrips.net/wiki/VGM_Specification)
- [vgmrips/vgmtools (GitHub)](https://github.com/vgmrips/vgmtools)
- [VGMRips Logging VGMs](https://vgmrips.net/wiki/Logging_VGMs)
- [VGMRips $4017 Caution Thread](https://vgmrips.net/forum/viewtopic.php?t=2655)
- [VGMPF NSF Wiki](https://www.vgmpf.com/Wiki/index.php?title=NSF)
- [nesdev.org NSFE Thread](https://forums.nesdev.org/viewtopic.php?t=23674)
- [nesdev.org NSF Rip Archive Thread](https://forums.nesdev.org/viewtopic.php?t=7814)
- [NSFe Specification (NESdev Wiki)](https://www.nesdev.org/wiki/NSFe)
- [NSF2 Specification (NESdev Wiki)](https://www.nesdev.org/wiki/NSF2)
