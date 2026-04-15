# Driver Family Taxonomy Revision — 2026-04-14

## Summary

A census of 271 extracted NES games (9,070 MIDI files) revealed that the
original 5-family driver classification needed revision. The revised model
has **4 families** with **sub-groups** in Family 1. Family 5 (Full Animation)
has been eliminated — zero games qualified under its thresholds.

### Changes from Previous Model

| Aspect | Before (2026-04-13) | After (2026-04-14) |
|--------|--------------------|--------------------|
| Family count | 5 | 4 |
| Family 1 name | Hardware Envelope | Sparse Envelope |
| Family 2 name | Standard Envelope | Active Envelope |
| Family 3 definition | CC11 3.7-4.9 AND CC12 0.7-1.0 | CC12 >= 0.7 (any CC11) |
| Family 4 threshold | CC11 > 5.1 | CC11 > 5.6 |
| Family 5 | CC11 > 7.0 AND CC12 > 1.0 (SMB3) | **Eliminated** (0 members) |
| Sub-groups | None | 1A (ultra-sparse) and 1B (moderate-sparse) |
| Fuzzy zone | Not tracked | CC12 0.3-0.7 flagged (13 games) |
| Games profiled | 30 (manual) | 271 (automated census) |

---

## Methodology

### Census Tool

`scripts/family_census.py` analyzes the first MIDI file per game (or all
tracks with `--all-tracks`). For each MIDI, it counts:

- **CC11 events** (volume automation, MIDI CC 11)
- **CC12 events** (duty cycle automation, MIDI CC 12)
- **Note-on events** (with velocity > 0)

The ratios CC11/note and CC12/note are the classification axes. These
ratios reveal how aggressively a game's sound driver writes to the APU
volume and duty registers per frame.

### Data Source

All 297 games with NSF files were extracted via `batch_nsf_all.py` using
the py65 NSF emulator. The emulator runs each game's original 6502 sound
driver and captures APU register writes per frame (~60 Hz NTSC). These
writes are encoded as CC11 (volume) and CC12 (duty) in MIDI output.

271 of 297 games produced analyzable MIDI output (the remainder had empty
or corrupt output — typically very short SFX-only NSFs).

### Census Results

Full data: `data/family_census_v2.json`

---

## The Revised 4-Family Model

### Family 1: Sparse Envelope (156 games, 57.6%)

**Definition:** CC11/note <= 2.8, CC12/note < 0.7

The driver writes volume infrequently — once per note onset, or a few
times during sustain. The APU's hardware envelope generator ($4000 bit 5 = 0)
may handle decay autonomously, or the driver sets a constant volume
($4000 bit 5 = 1) and leaves it.

**Sub-group 1A: Ultra-Sparse (53 games, CC11 <= 0.5)**
Truly minimal automation. The driver writes volume essentially once per
note (or not at all). Games sound "raw" and arcade-like. Many early NES
titles and Capcom's Sakaguchi engine fall here.

Representative: Marble Madness (0.06), Mega Man (0.15), Section Z (0.09),
R.C. Pro-Am (0.34), Wizards & Warriors (0.15), Son Son (0.28), Trojan (0.46)

**Sub-group 1B: Moderate-Sparse (103 games, CC11 0.5-2.8)**
Occasional volume writes — enough to shape attack/decay but not per-frame
obsessive. The driver is doing some work but not dominating CPU time.
Later Capcom titles and many Konami games fall here.

Representative: Mega Man 2 (1.12), Mega Man 3 (2.25), DuckTales (1.05),
Castlevania (2.00), Battletoads (2.39), Life Force (2.45), Metal Gear (1.74)

**Known sound drivers in Family 1:**
- Capcom Sakaguchi engine (early): Mega Man 1, 1942, Section Z, Ghosts'n Goblins
- Capcom Sakaguchi engine (mid): Mega Man 2-3, DuckTales, Sweet Home
- Rare Stamper/Betteridge (early): Wizards & Warriors, R.C. Pro-Am, Marble Madness
- Sunsoft (early): Batman, Blaster Master, Journey to Silius
- Early Konami: Castlevania, Metal Gear, Life Force
- Tecmo (early): Tecmo Bowl

**Synth implications:** ADSR keyboard mode works well. CC11 data is sparse
enough that the synth can interpolate. For 1A games, hardware decay preset
is ideal. For 1B games, a short software envelope preset is better.

### Family 2: Active Envelope (79 games, 29.2%)

**Definition:** CC11/note 2.8-5.6, CC12/note < 0.7

The driver writes volume several times per note — enough to shape a visible
envelope curve but not at per-frame density. Duty cycle is set once per note
and left static.

Representative: Contra (2.90), Mega Man 4 (3.22), Zelda II (3.42),
Ninja Gaiden III (5.08), TaleSpin (3.72), Chip'n Dale (4.03), Yo Noid (4.50)

**Known sound drivers in Family 2:**
- Capcom Sakaguchi (late): Mega Man 4+, Darkwing Duck, DuckTales 2, TaleSpin
- Konami Maezawa: Contra, Castlevania III (US), Jackal
- Tecmo Yamagishi: Ninja Gaiden II/III, Rygar
- Rare (Battletoads-era): Battletoads trace variants, R.C. Pro-Am II

**The Capcom evolution:** Capcom games span Families 1 and 2 using the
*same driver architecture* (Sakaguchi engine). Early titles (1985-1988)
are Family 1; later titles (1989-1993) are Family 2. The boundary at
CC11=2.8 corresponds to a shift in composition technique, not driver code.
This is why the F1/F2 split is somewhat arbitrary — there is no gap in the
CC11 distribution at 2.8. We retain the boundary because it corresponds to
audible differences in envelope complexity.

**Synth implications:** CC11 drives volume; ADSR bypassed during file
playback. Envelope shape is captured in the CC data.

### Family 3: Duty Animators (20 games, 7.4%)

**Definition:** CC12/note >= 0.7 (any CC11 range)

The defining feature is **duty cycle animation** — the driver changes the
pulse waveform duty (12.5%, 25%, 50%, 75%) per-frame within sustained notes.
This creates timbral sweeps that are a signature sound of certain NES games.
CC11 range varies widely (1.54 to 5.79) because duty animation is an
independent axis from volume automation.

Representative: Super Mario Bros 3 (CC11=4.62, CC12=1.24),
Konami Hyper Soccer (4.34, 1.49), Snakes Revenge (4.37, 1.40),
TwinBee 3 (3.70, 1.48), Skate or Die (3.08, 1.13), Contra Force (1.54, 0.71)

**Key finding — SMB3:** Super Mario Bros 3 was the supposed sole member of
the original Family 5 (Full Animation). The census revealed it actually
has CC11=4.62 (not >7.0) and CC12=1.24 (>0.7). It belongs in Family 3.
The original Family 5 threshold was set too high — no game in the library
has both CC11>7.0 AND CC12>=1.0.

**Known sound drivers in Family 3:**
- Nintendo Kondo: SMB3
- Konami (VRC6-aware branch): Konami Hyper Soccer, Snakes Revenge, TwinBee 3
- Konami (Gradius branch): Gradius II, Rollergames
- EA Canada: Skate or Die, Ski or Die

**Synth implications:** Both CC11 and CC12 must be played back faithfully.
The synth must update duty cycle per-frame from CC12 data, not hold a
static duty setting.

### Family 4: Dense Automators (16 games, 5.9%)

**Definition:** CC11/note > 5.6, CC12/note < 0.7

The driver writes volume obsessively — often every single frame — creating
a characteristic "shimmer" or "throb" from rapid volume modulation. This
can include tremolo, vibrato-like effects achieved through volume, or
simply very aggressive envelope shaping. Duty is typically static.

Representative: Metroid (11.50), Kid Icarus (7.38), Rad Racer II (16.25),
Maharaja (14.27), Esper Dream 2 (14.46), Super Mario Bros 2 (6.92)

**Known sound drivers in Family 4:**
- Nintendo Tanaka: Metroid, Kid Icarus (both FDS games)
- Nintendo: Super Mario Bros 2 (Doki Doki Panic port)
- Square: Final Fantasy
- Konami (early arcade-style): Gradius, Yie Ar Kung-Fu

**The long tail:** The CC11 distribution drops off sharply after 6.0 — only
16 games exceed this threshold, and they span a huge range (5.67 to 16.25).
The gap between the main population (0-6) and the extreme outliers (>10)
suggests these are genuinely different driver architectures, not just
aggressive composers.

**Synth implications:** CC11 data is the envelope. Large MIDI files due
to high event density. NSF trust is "Medium" — dense automation means more
opportunities for emulation artifacts. Cross-validation against VGM or
Mesen trace recommended.

---

## Family 5: Eliminated

The original Family 5 (Full Animation) was defined as CC11/note > 7.0 AND
CC12/note >= 1.0. **Zero games in the 271-game census meet this threshold.**

SMB3, the theoretical sole member, has CC11=4.62 and CC12=1.24. It qualifies
for Family 3 (Duty Animators) by the CC12 axis. There is no game with
extreme density on *both* axes simultaneously.

This makes sense architecturally: per-frame writes to both volume AND duty
on two pulse channels would consume significant CPU time (~480 register
writes per second). Most drivers that animate duty also have moderate
volume density — they balance CPU budget between the two axes.

---

## Boundary Analysis

### The F1/F2 Boundary (CC11 = 2.8)

The CC11 distribution is **continuous** at 2.8 — there is no gap or valley.
The 2.5-3.0 range has 70 games straddling the boundary. Same-publisher,
same-driver games fall on both sides:

- Capcom: Mega Man 3 (2.25, F1) vs Mega Man 4 (3.22, F2)
- Konami: Castlevania (2.00, F1) vs Contra (2.90, F2)
- Rare: Battletoads NSF (2.39, F1) vs Battletoads trace (3.02, F2)

We retain 2.8 as the boundary because:
1. It matches the Capcom driver evolution (early/late Sakaguchi engine)
2. It's audibly meaningful (occasional vs regular envelope shaping)
3. It matches the original research boundary from the 65-game survey
4. Moving it would not create a cleaner split — the distribution is smooth

### The Duty Animator Threshold (CC12 = 0.7)

CC12 is bimodal: 236 games (87%) have CC12 < 0.25, and 20 games have
CC12 >= 0.7. The gap between 0.25 and 0.7 contains only 15 games.
This is a much cleaner boundary than CC11.

### The Fuzzy Zone (CC12 0.3-0.7)

13 games have moderate CC12 that doesn't cleanly indicate duty animation:

| Game | CC11 | CC12 | Current Family |
|------|------|------|----------------|
| Q*bert | 1.27 | 0.38 | F1 |
| TMNT | 1.59 | 0.38 | F1 |
| CV3 Dracula's Curse | 3.14 | 0.39 | F2 |
| Kirby's Adventure | 2.06 | 0.42 | F1 |
| TMNT Tournament Fighters | 2.55 | 0.44 | F1 |
| Tiny Toon Adventures | 3.41 | 0.46 | F2 |
| 1942 | 0.50 | 0.50 | F1 |
| Ganbare Goemon 2 | 2.72 | 0.50 | F1 |
| Rad Racer II | 16.25 | 0.50 | F4 |
| Moai-kun | 3.33 | 0.55 | F2 |
| After Burner | 7.05 | 0.56 | F4 |
| Base Wars | 2.78 | 0.56 | F1 |
| CV2 Simon's Quest | 2.96 | 0.63 | F2 |

These should be ear-checked to determine if their duty changes are
musically significant (F3-like) or incidental (artifact of driver behavior).

---

## Publisher Cluster Analysis

### Capcom (27 games matched)

Single driver family (Sakaguchi engine) spanning **both F1 and F2**.
CC11 range: 0.09 (Section Z) to 4.50 (Yo Noid). The boundary maps to
a chronological evolution in composition technique:

- 1985-1988 (F1): 1942, Mega Man, Ghosts'n Goblins, Bionic Commando
- 1989-1993 (F2): Mega Man 4+, DuckTales 2, TaleSpin, Chip'n Dale

CC12 is nearly zero across all Capcom titles (max 0.50 for 1942).
Capcom never animated duty cycle.

### Konami (35 games matched)

Spans **all four families** (F1 through F4). Reflects multiple sound
drivers and composers within the same company:

- F1 (17 games): Early titles, Castlevania, Metal Gear, Life Force
- F2 (9 games): Contra, CV3 US, Jackal, Tiny Toon Adventures
- F3 (6 games): Duty-animating branch — Konami Hyper Soccer, Snakes Revenge, TwinBee 3
- F4 (3 games): Early arcade ports — Gradius, Yie Ar Kung-Fu

### Rare (20 games matched, including trace variants)

Two clean clusters:
- F1: Early Rare (W&W, R.C. Pro-Am, Marble Madness) — ultra-sparse
- F2: Later Rare (Battletoads trace, R.C. Pro-Am II) — moderate automation

The same Stamper/Betteridge driver evolved over time, just like Capcom.

### Nintendo First-Party

Every family represented, reflecting multiple composers and game engines:
- F1: Kirby's Adventure (2.06)
- F2: Super Mario Bros (3.60), Zelda II (3.42)
- F3: Super Mario Bros 3 (4.62, 1.24)
- F4: Super Mario Bros 2 (6.92), Kid Icarus (7.38), Metroid (11.50)

---

## Anomalies

### Games with <= 2 Active Channels

18 games showed only 1-2 channels in their first MIDI. Most are extraction
artifacts where the first track is a short jingle or SFX. Checking later
tracks in these games typically reveals full 4-channel music. Examples:

- 1942 (track 1: 2 channels, track 3: 3 channels)
- Final Fantasy (track 1: 2 channels, track 2: 3 channels)
- Contra (track 7: 2 channels — this is a ROM-parsed version, not NSF)

These are not classification errors — the census uses the first track,
which may not be representative. The `--all-tracks` mode averages across
all tracks and produces more stable results.

### Games with CC11 = 0

Two games (Super Arabian, Thexder) have zero CC11 events. These are
genuinely CC-free — the driver uses hardware envelope exclusively or
the NSF extraction didn't capture CC data. Both classify as Family 1A.

### Extremely Dense Games (CC11 > 10)

Four games: Rad Racer II (16.25), Esper Dream 2 (14.46), Maharaja (14.27),
Metroid (11.50). These represent the extreme end of volume automation.
All are Family 4.

---

## Synth Architecture Implications

### What the Census Confirms

1. **CC11/CC12 is sufficient for 88% of games.** The overwhelming majority
   (238/271 games) have normal CC11 density and static duty. The existing
   CC11-driven synth mode handles these correctly.

2. **Duty animation matters for 20 games.** Family 3 is real and distinct.
   The synth MUST play back CC12 per-frame for these games.

3. **Dense automation creates large MIDIs.** Family 4 games generate
   6-16x more CC events per note than Family 1. File sizes and processing
   load scale accordingly.

### What the Census Does NOT Address

The CC11/CC12 density classification captures **volume and duty behavior**
but misses several NES audio phenomena that affect fidelity:

1. **Expansion audio** (35 games): FDS wavetable, VRC6 extra pulses+saw,
   VRC7 FM synthesis, 5B squares. These chips produce sounds that CC11/CC12
   cannot represent. The current pipeline silently drops expansion channels.

2. **DPCM/DAC** (unknown count): Sample playback ($4010-$4013) and
   direct DAC writes ($4011) are conflated in the current pipeline. Sunsoft
   bass, Battletoads drums, and many other games use these for percussion
   or bass that is not captured in the current MIDI output.

3. **Non-linear APU mixing**: Two pulse channels at max volume produce
   ~0.278, not 2x one pulse (~0.184). Linear mixing (current JSFX) makes
   simultaneous channels too loud. The formulas are documented in
   `synth_fidelity.md` Rule 7 but not yet implemented.

4. **Frame-level events**: Phase reset, sweep, same-pitch retriggers,
   and noise mode changes are not captured by CC11/CC12. The Frame
   Audible-State IR design (`docs/MIDDLE_LAYER_RECOMMENDATION.md`)
   addresses this but is not yet fully integrated.

### Current Fidelity Stack and Options

The current pipeline: NSF → py65 emulator → CC11/CC12 MIDI → ReapNES synth

This gives us **volume-accurate, pitch-accurate, timing-accurate** output
for all 4 standard APU channels. What it misses:

| Gap | Impact | Potential Solution | Complexity |
|-----|--------|-------------------|------------|
| Expansion audio | 35 games lose channels | Extend emulator + MIDI encoding | High |
| Non-linear mixing | All games slightly too loud | Implement in JSFX | Medium |
| DPCM samples | Percussion missing | Sample trigger events in MIDI | High |
| DAC bass/drums | Algorithmic sounds missing | DAC ramp events in Frame IR | High |
| Phase reset | Retrigger artifacts | SysEx metadata per frame | Medium |
| Sweep vibrato | Smooth vibrato lost | SysEx period register replay | Already solved (SysEx mode) |

**Decision: The current CC11/CC12 pipeline is the right architecture for
batch production.** It covers 262/297 games (88%) at the standard APU level.
The SysEx register replay mode already solves sweep and phase reset for
games where maximum fidelity is needed. Expansion audio support is the
highest-value next investment (35 games, mostly FDS).

---

## Tools Built/Updated

| Tool | Status | Purpose |
|------|--------|---------|
| `scripts/family_census.py` | **New** | Fast CC density census, revised 4-family classification |
| `scripts/driver_survey.py` | **Updated** | Classification logic aligned to 4-family model |
| `data/family_census_v2.json` | **New** | Full census results for 271 games |
| `ANTIRIPPER/antiripper_v2.db` | **Updated** | driver_families table revised, decision record logged |

## Files Updated

| File | Change |
|------|--------|
| `CLAUDE.md` | Driver family table revised, census tool added |
| `.claude/rules/synth_fidelity.md` | Keyboard presets updated for 4 families + sub-groups |
| `docs/DRIVER_FAMILIES_AND_GAMES.md` | Updated (see note below) |
| `index.md` | Website landing page updated |
| `docs/NEWDRIVERFAMILIES414.md` | This document |

## Data Files

- `data/family_census_v2.json` — 271-game census with family_id, sub_group, fuzzy_zone flags
- `data/expansion_audit.json` — 297-game expansion audio scan (35 games with expansion chips)
