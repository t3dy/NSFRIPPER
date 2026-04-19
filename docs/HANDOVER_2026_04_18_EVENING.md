# Handover — 2026-04-18 evening session

Copy the block below into a new Claude Code window at `C:\Dev\NSFRIPPER`.

---

## HANDOVER PROMPT

I'm continuing work on the NSFRIPPER stems pipeline at `C:\Dev\NSFRIPPER`.

**Load these first** (newest to oldest, each one builds on the previous):

1. `docs/HANDOVER_2026_04_18_EVENING.md` — this file.
2. `docs/STATEOFTHEPROJECT.md` — overall current state, what works / what's rough.
3. `docs/NEWDRIVERFAMILIES.md` — driver taxonomy by $4015 strategy + drum source.
4. `docs/NOISECHANNELPLAN.md` — validation plan for the noise-channel work.
5. `docs/RESEARCH_ANTIALIAS.md` — community research (Blargg BLEP, 2-bus-stem refactor).
6. `docs/NOISEPROBLEM.md` — Battletoads click/pop/overdrive diagnosis.
7. `.claude/rules/architecture.md` Rules 34–36 — triangle gate-hold, bandlimited
   pulse, NSF player $4015 init.
8. `docs/HANDOVER_2026_04_18_AFTERNOON.md` — the previous handover.  Useful if
   you want morning+afternoon context without reading through the other docs.
9. `CLAUDE.md` — background context.
10. `MEMORY.md` — auto-loaded user preferences (no-overclaiming, stems-default, etc).

## State of the pipeline (what changed this session, evening)

Six separate bugs found and fixed on top of the afternoon's work.  Each was
audibly-distinct but shared the same root symptom: either a click/pop, a
muted noise channel, or a truncated song.

### Fixes shipped this session

1. **Triangle gate-off holds DAC** (architecture.md Rule 34).
   `scripts/render_channel_stems.py::render_stem` `keep == "tri"` branch:
   during gate-off (linear counter = 0), output the wave at the frozen
   phase instead of zeroing.  Matches NESdev spec; eliminates 129 vinyl pops
   per 10 seconds of Battletoads bassline.  Measured: triangle max single-
   sample step 0.386 → 0.006 (98.4% reduction).

2. **Bandlimited pulse synthesis** (Rule 35).  Replaced
   `np.where(pa < duty, vol, 0)` with an analytical integral:
   `fraction_high = (H(pa_end) - H(pa_start)) / step`.  Reduces pulse edge
   aliasing by ~36%; combined with the LP bump, ~67% fewer clicks >10% peak.

3. **4-pole LP filter** (same rule).  Bumped from 2-pole to 4-pole
   Butterworth at 14 kHz.  Better aliasing attenuation, slightly more
   note-on ringing.

4. **NSF player $4015 = $0F before INIT** (Rule 36, THE BIG WIN).
   `scripts/nsf_to_reaper.py::NsfEmulator.play_song`, lines 254–255.  Per
   NSF spec, the player is required to enable channels before INIT; we
   weren't doing it.  This silently broke noise drums on ~30% of games
   (Battletoads, CV, CV3, Gradius, Kid Icarus, Wizards & Warriors, Spy
   Hunter, Kirby, Ninja Gaiden, all Rare / late-Capcom / early-Sunsoft
   titles).  Verified on Castlevania: Vampire Killer noise peak
   0.000 → 0.300, 12 of 15 songs now have active noise.

5. **Expansion chip always-capture** (same fix as #6 in same rule).  Previously
   VRC6/FDS/MMC5 registers were only captured if the NSF header had the
   expansion flag byte set.  Some NSFs have the flag cleared despite using
   expansion audio (e.g. JP Akumajou Densetsu rip).  Now capture those
   ranges unconditionally and auto-detect the chip post-capture from
   observed writes.

6. **Silence-threshold bump** (120 → 600 frames).
   `scripts/nsf_to_reaper.py::play_song` line 291.  The 2-second early-exit
   on "no APU writes" was truncating songs with quiet intros (DuckTales,
   CV3 boss themes).  Bumped to 10 seconds.  DuckTales all songs rendered
   correctly post-fix.

### New scripts added this session

| File | Purpose |
|------|---------|
| `scripts/download_zophar_nsfs.py` | Scrapes Zophar's Music Domain for NSFs by slug.  Handles URL-encoded names and the `(EMU).zophar.zip` convention. |
| `scripts/import_zophar_nsfs.py` | Scans `~/Downloads/` for Zophar-style zip files and extracts NSF + M3U into `output/<slug>/nsf/`.  Idempotent. |
| `scripts/render_wishlist.sh` | Sequentially renders the 7 wishlist games into `outputv6/`.  Running in background as of this handover. |
| `scripts/extra_rpg_renders.sh` | Sequentially renders Faxanadu + Life_Force + Willow into outputv6. |
| `scripts/extract_nsf_from_rom.py` | Scaffolding for Mesen-based NSF extraction from ROMs.  NOT currently functional — Mesen 2's CLI doesn't document an NSF Ripper hook.  Kept in place in case a CLI path is found or Mesen 1 classic gets reinstalled. |
| `scripts/rebuild_v6.py` | Added `--force` flag + fuzzy-name NSF resolution. |

### New documents added this session

| File | Purpose |
|------|---------|
| `docs/STATEOFTHEPROJECT.md` | One-page current state summary. |
| `docs/NEWDRIVERFAMILIES.md` | Driver taxonomy by $4015 strategy.  ~30 games surveyed. |
| `docs/NOISECHANNELPLAN.md` | Per-family validation plan, open investigations. |
| `docs/RESEARCH_ANTIALIAS.md` | Blargg BLEP + 2-bus-stem community research. |
| `docs/NOISEPROBLEM.md` | Battletoads click/pop/overdrive diagnosis. |
| `docs/HANDOVER_2026_04_18_EVENING.md` | This file. |

## Ear-test results from this session

| Game | User's assessment |
|------|-------------------|
| Battletoads | "sounds a lot better" — triangle pops gone, pulse buzz reduced |
| Bionic Commando | "sounds great" |
| DuckTales | User reported tracks ending early (bug #6 above); re-rendered post-fix but not yet re-tested |
| Castlevania 3 | User reported tracks ending early (bugs #5 and #6); rebuilt post-fix but US song 1 "Beginning" still has a driver-specific stuck state |

## Background jobs running at handover time

At the moment this handover was written, these jobs were active:

1. **Main rebuild** (`scripts/rebuild_v6.py --force --skip DuckTales`):
   at 6/43 (Castlevania_3 rendering).  Going through all 44 outputv5
   games with both Rule 36 and the silence-threshold fix.  ETA: ~3 hours
   from start (14:00-ish), so probably another 2 hours.
   Log: `outputv6_rebuild.log`, per-game logs in `outputv6/_log_*.log`.

2. **Wishlist batch** (`scripts/render_wishlist.sh`): rendering the 7
   just-downloaded wishlist games.  Halfway done when handover was
   written (Bubble_Bobble: 13 RPPs, Double_Dragon: 11 RPPs, Double_Dragon
   II started).  Log: `outputv6/_log_wishlist.log`.

To resume: check these commands first:

```bash
# See what's done
ls outputv6/ | grep -v "^_" | sort
# See main rebuild progress
tail -5 outputv6_rebuild.log
LC_ALL=C grep -a -E "^\[|ok," outputv6_rebuild.log | tail -10
# See wishlist progress
cat outputv6/_log_wishlist.log | LC_ALL=C grep -a "===\|-> [0-9]"
# Anything still running?
ps -ef | grep -E "python|rebuild" | grep -v grep
```

## Games available as of handover

**In outputv6 (audio stems + MIDI + RPP rendered)**: 13 games so far
— Batman, Battletoads, Bionic_Commando, Blaster_Master, Castlevania,
Castlevania_3, DuckTales (standalone re-render), Faxanadu, Life_Force,
Willow, Bubble_Bobble (partial), Double_Dragon (partial),
Double_Dragon_II_The_Revenge (in progress).  More will appear as
the background jobs finish.

**NSF files available but not yet rendered** (~22 games): many more
games than outputv5's 44 now have NSFs in `output/<slug>/nsf/` because
of the Zophar importer run.  Notable new ones not yet in outputv6:

- Castlevania_2_Simons_Quest, Castlevania_3_Draculas_Curse, _JP
- Gargoyles_Quest_II
- Goonies_II_The
- Kid_Icarus_FDS (FDS expansion audio version)
- Legendary_Wings
- Metal_Gear
- Ninja_Gaiden_II_The_Dark_Sword_of_Chaos
- Ninja_Gaiden_III_The_Ancient_Ship_of_Doom
- Punch_Out_VS
- Silver_Surfer_SFX
- Super_Mario_Bros_2_Prototype
- Trojan
- Ultima_Exodus, Ultima_Quest_of_the_Avatar
- StarTropics, Crystalis, Shadowgate, Dragon_Warrior_II (wishlist)

To render any of these: `python scripts/batch_stems_project.py <NSF_PATH>
--out-dir outputv6/<Game>/ --seconds 60`.

## User-requested wishlist status (2026-04-18 evening)

User asked for these games this session; status at handover:

| Game | NSF | outputv6 render | Notes |
|------|-----|-----------------|-------|
| Zelda 1 | ✅ | queued in main rebuild (Legend_of_Zelda) | fuzzy-match resolves |
| Zelda 2 | ✅ | queued (Zelda_II) | |
| Dragon Warrior | ✅ | ✅ 25 songs | rendered earlier in session |
| Dragon Warrior 2 | ✅ | queued in wishlist batch | |
| Final Fantasy | ✅ | queued in main rebuild | |
| Final Fantasy 2 | ✅ | queued | |
| Final Fantasy 3 | ✅ | queued | |
| Kid Icarus | ✅ | queued | |
| Metroid | ✅ | queued | |
| Kirby's Adventure | ✅ | queued | |
| Gradius | ✅ | queued | |
| Life Force | ✅ | ✅ (extra renders) | |
| Bubble Bobble | ✅ | partial (13 RPPs at handover) | Taito driver - new family! |
| Double Dragon 1 | ✅ | partial (11 RPPs) | Technos driver |
| Double Dragon 2 | ✅ | in progress | Technos driver |
| Crystalis | ✅ | queued in wishlist | SNK driver |
| StarTropics | ✅ | queued | Nintendo 1st-party |
| Shadowgate | ✅ | queued | Kemco driver |
| Faxanadu | ✅ | ✅ | Hudson/Falcom driver |

## Known open issues (where the next session might start)

### 1. CV3 US "Beginning" song 1 still silent

`output/Castlevania_3___Draculas_Curse/` NSF.  Song 1 "Beginning"
emulates 600 frames (post-threshold bump) but only has 34 APU writes
at the very start and then nothing.  Not an emulator termination bug —
the driver itself goes quiet.  Two hypotheses:
- Driver requires a specific IRQ (NMI or frame IRQ) that py65 doesn't fire
- Driver has a condition check (DMC completion?) that's not met in emulation

Not a widespread problem — only affects this one song on this one NSF.
Worth investigating but not urgent.

### 2. 2-bus-stem refactor deferred

The non-linear APU DAC mixing problem (stem sum overloads REAPER by
~15% when multiple channels active) is the likely residual "overdrive"
source.  Design complete in `RESEARCH_ANTIALIAS.md` section 6 option B.
Estimated 2 hours of work.  This is the next biggest ROI.

### 3. Blargg BLEP port deferred

Remaining ~14 pulse clicks/sec of aliasing after Rule 35.  Fully
addressed by porting `blip_buf` to numpy (~200 lines of C → ~300 lines
of python/numpy).  See RESEARCH_ANTIALIAS.md.  Estimated 1 day.

### 4. Mesen NSF extraction never got working

`scripts/extract_nsf_from_rom.py` is scaffolded but Mesen 2.1.1 doesn't
have a documented CLI or scripting API for NSF ripping.  Options to
make it work:
- Install Mesen Classic (v0.9.11) alongside Mesen 2 — it does have
  a CLI NSF ripper.
- Use pywinauto to drive the Mesen 2 GUI headfully.
- Build a from-scratch iNES → NSF extractor using our driver family
  fingerprints.
Zophar's importer made this redundant for the current wishlist.

### 5. New driver families to survey

Post-rebuild, we'll have audio stems from Taito (Bubble Bobble),
Technos (Double Dragon 1+2), SNK (Crystalis), Kemco (Shadowgate),
Chunsoft (Dragon Warrior 2) — drivers not yet in NEWDRIVERFAMILIES.md.
Update the taxonomy after ear-tests pass.

### 6. Expansion-chip init analogue to Rule 36

Rule 36 was about standard APU init.  NSF v2 may require similar init
writes for VRC6/N163/5B/FDS expansion.  We haven't verified all our
expansion-audio games work correctly (CV3 JP should be tested
post-rebuild).  Expand Rule 36 if a game's expansion channel is silent.

## Key commands reference

```bash
# Resume status
tail -5 outputv6_rebuild.log
cat outputv6/_log_wishlist.log | LC_ALL=C grep -aE "===|->"
ls outputv6/ | grep -v "^_" | wc -l

# Render a single new game (NSF already in output/<slug>/nsf/)
python scripts/batch_stems_project.py "output/Metal_Gear/nsf/Metal Gear*.nsf" \
    --out-dir outputv6/Metal_Gear/ --seconds 60

# Force-re-render a game (uses current code's fixes)
python scripts/batch_stems_project.py <NSF> --out-dir outputv6/<Game>/ --seconds 60

# Full rebuild (respects Rule 36 + silence fix, runs ~3 hours)
python scripts/rebuild_v6.py --force --seconds 60

# Download a Zophar NSF by slug
python scripts/download_zophar_nsfs.py metal-gear ultima-exodus

# Import all Zophar zips sitting in Downloads
python scripts/import_zophar_nsfs.py
```

## Do's and don'ts

DO:
- Use `outputv6/` as the canonical output location.  outputv5 is
  read-only reference.
- When user reports an audio issue, first check if it's pre- or post-
  Rule 36 fix.  Anything rendered before 2026-04-18 18:00 was missing
  the noise drums on ~30% of games.
- Surface the `no-overclaiming` rule: say "shipped, awaiting ear-test"
  not "fixed."  User has corrected this repeatedly.

DO NOT:
- Revert any of Rules 34, 35, 36.
- Re-enable the 120-frame silence threshold (reintroduces CV3/DuckTales
  truncation bug).
- Revert the always-capture-expansion-ranges change (reintroduces CV3
  JP truncation bug).
- Run multiple `rebuild_v6.py --force` instances in parallel — they
  compete for the same output paths and produce a mess.
- Overclaim.  User will correct "works" / "fixed" language.

## First action in the new window

```bash
# 1. Check on background jobs
ps -ef | grep -E "python|rebuild" | grep -v grep
ls outputv6/ | grep -v "^_" | wc -l
tail -5 outputv6_rebuild.log
cat outputv6/_log_wishlist.log | LC_ALL=C grep -a "===\|-> [0-9]" | tail

# 2. See what user would likely ask about
# (likely: "how's the rebuild going?" or "what ear-test should I do next?")
```
