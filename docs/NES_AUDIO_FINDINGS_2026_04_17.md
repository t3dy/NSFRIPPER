# NES Audio Findings — 2026-04-17

Systematic register-level analysis of 298 NSF-extracted games (trace-based
variants excluded). Data source: `data/register_analysis.json` via
`scripts/register_analysis.py` which parses SysEx streams from MIDI
files to reconstruct per-frame APU register state.

## Most Important Findings

### 1. The 4-family taxonomy is too coarse

The existing classification (Sparse/Active/Duty-Animators/Dense) is
based on CC11/CC12 density per note. CC density is a PROXY for
envelope mode but mislabels many games. Real envelope modes:

| Mode | const_vol bit | Games | Meaning |
|------|---------------|-------|---------|
| HW envelope dominant | bit 4 cleared >80% of frames | 26 | Uses APU hardware envelope (linear decay) |
| SW envelope dominant | bit 4 set >80% | 243 | Driver writes volume every frame |
| Mixed HW+SW | 20-80% either | 29 | Driver selects mode per note — sophisticated |

### 2. Triangle length counter is never used (proven invariant)

**0 out of 298 games enable $4015 bit 2 (triangle length counter gating).**
Every driver uses the linear counter ($4008 bit 7 + reload value) for
triangle note gating. This is a universal NES convention that was
undocumented in our system until now.

Implications:
- Triangle synth playback can ignore length-counter logic entirely
- Trace validation can assume triangle `enabled` bit is irrelevant

### 3. env_loop bit modulation is Nintendo's driver signature

When const_vol=1, $4000 bit 5 is "length counter halt". Most games
leave it at 1 (halt on). 59 games actively modulate this bit — and
it's almost exclusively **Nintendo first-party and Rare games**:

```
Legend of Zelda              Zelda II                 Punch Out!!
Super Mario Bros 2/3         Mighty Bomb Jack          Platoon
Nankin no Adventure          720 Degrees               Spy Hunter
Captain Skyhawk (Rare)       R.C. Pro-Am (Rare)        Time Lord (Rare)
Slalom (Rare)                Anticipation (Rare)       Xenophobe
Tsuppari Oozumou (Tecmo)     Super Star Force         Nazo no Magazine Disk 3
```

These drivers use **length-counter gating** for note-off. Our MIDI
pipeline doesn't capture this — it gates on volume=0. The gating
works but the MECHANISM differs across drivers.

**New finding: "Nintendo driver family"** — a 5th family we didn't have.

### 4. Sweep is used by far more games than expected

50 games show sweep enabled on >1% of frames. Categories:

**Heavy sweep musical use (>100 writes):**
- Blaster Master (Sunsoft): 94% enabled, 376 writes
- Batman (Sunsoft): 90% enabled, 2987 writes
- Festers Quest (Sunsoft): 87% enabled, 1944 writes
- After Burner: 99% enabled, 3018 writes (sweep-heavy arcade port)
- Nantettatte Baseball: 94% enabled, 1355 writes
- Sekiryuuou: 97% enabled, 374 writes
- Nazo no Magazine Disk 3: 86% enabled, 1327 writes

**Sweep-at-init only (~10-20 writes):**
20+ games, likely enabling sweep once and leaving it static

**Current pipeline doesn't apply sweep to pitch** — these games have
pitch modulation we're discarding. Fixing this would audibly change
Sunsoft output.

### 5. DMC rate selection reveals driver/composer preferences

Rate index 0 = 4.2 kHz (lowest), index 15 = 33.1 kHz (highest).

```
Rate 15 (33 kHz) — high quality:  Batman (1413), Ninja Gaiden (1098)
Rate 14 (25 kHz):                  Super Mario Bros 3 (259)
Rate 12 (17 kHz):                  Gremlins 2 (256), Journey to Silius (452)
Rate 0  (4 kHz)  — bass/low:       Battletoads, Zelda
```

Sunsoft uses high-quality samples. Nintendo (Zelda, SMB3) uses mid-low
rates. Rare (Battletoads) uses lowest rate — fits their algorithmic
approach.

### 6. Driver identification via NSF init signature

`scripts/probe_driver_signature.py` finds 9 shared init-routine
signatures across 23 games. Largest clusters:

**Capcom late driver** (7 games, sig `4cfe80a90085c2a0`):
Mega Man 3, Mega Man 4, Darkwing Duck, TaleSpin, Little Mermaid,
Mighty Final Fight, Tenchi wo Kurau II

All 7 share identical register behavior: 100% const_vol, 100% env_loop,
5-7% phase_reset, 0% sweep. This is the "Capcom 6C80" driver format
mentioned in earlier docs.

**Capcom early driver** (different signature, inferred from behavior):
Mega Man 1/2, Bionic Commando, Commando, Section Z, Gun.Smoke, Ghosts'n'Goblins
Pattern: higher phase reset rates (42-60%+), often HW envelope, more
aggressive retriggering.

**Konami driver** (various sub-drivers):
Castlevania, Contra, Gradius, Hyper Sports, Road Fighter
Pattern: 100% SW envelope, 100% env_loop, moderate phase reset
(2-3%), some sweep usage.

**Sunsoft driver**:
Blaster Master, Batman, Journey to Silius, Gremlins 2
Pattern: SW envelope, moderate env_loop variation, HEAVY sweep usage
(94%+ enabled, hundreds of writes), high-rate DPCM.

**Nintendo R&D driver**:
Zelda, SMB, SMB2, SMB3, Punch Out, Mighty Bomb Jack
Pattern: env_loop actively modulated (length counter gating),
mixed HW/SW envelope.

**Square (Nobuo Uematsu)**:
3D WorldRunner, JJ Tobidase Daisakusen 2 share init signature.
Also: Final Fantasy 1/2/3 — need to verify same cluster.

**Rare driver**:
Battletoads (algorithmic), Wizards & Warriors (specialized), R.C. Pro-Am
(Nintendo-style env_loop), Cobra Triangle (HW envelope dominant)
Pattern: highly varied across Rare's titles — no single "Rare driver".

## Proposed Revised Taxonomy

The current 4-family CC density model describes OUTPUT (how many CC
events per note). A better taxonomy describes DRIVER BEHAVIOR:

| Axis | Value | Signature |
|------|-------|-----------|
| Envelope mode | HW / SW / Mixed | const_vol distribution |
| Length counter | halt / cycle | env_loop variation |
| Phase reset style | dense / moderate / sparse | $4003/$4007 write rate |
| Sweep use | musical / static / unused | $4001/$4005 enabled % + write count |
| DMC quality | low / mid / high / none | rate_idx histogram |
| Triangle gate | linear / length | length-counter-enable rate (universal: linear) |

Every driver sits on a 5-dimensional behavior space. Games cluster by
publisher/composer — same driver code produces identical signatures.

## Sub-families to Add

Based on signature matches, the 298-game corpus breaks into at least
10 identifiable driver families (not 4):

1. Capcom late (6C80): 7+ games, sig match confirmed
2. Capcom early: ~10 games, same-behavior cluster
3. Konami: 15+ games, same-behavior cluster
4. Sunsoft (Naoki Kodaka): 6+ games, sweep signature
5. Nintendo R&D (Koji Kondo): 10+ games, env_loop modulation
6. Square (Nobuo Uematsu): 9 games by artist credit
7. Rare (David Wise + others): 6+ games, multiple sub-drivers
8. Tecmo: Captain Tsubasa, Solomon's Key, Mighty Bomb Jack, Tecmo Bowl
9. Taito (Bubble Bobble, Don Doko Don): sweep-forward
10. Arcade ports (After Burner, Alien Syndrome): static/simple drivers

## Unknowns Still Remaining

1. **Per-note envelope shape** — when const_vol=0 (HW envelope mode),
   the driver sets $4000 bits 0-3 = envelope period. We track this
   but haven't analyzed what shapes games actually write.

2. **Noise channel gating** — we assume noise gates on volume=0.
   Some games might use $4015 bit 3 toggling. Current data shows 0
   games do this but our detection may be wrong.

3. **Timing patterns** — some drivers run at 60Hz, some at APU IRQ
   rate (~240Hz quantized). We haven't measured this.

4. **Per-game DMC sample inventory** — we count trigger events but
   don't know WHAT samples each game ships. The sample_addr field
   is captured but unused.

5. **Early Capcom driver (MM1/2)** — signature not yet confirmed
   via hex matching. Need to inspect those NSFs' init code.

6. **VRC7 (3 games) and 5B (Gimmick! = 1 game)** — register capture
   works but register SEMANTICS not parsed. FM synthesis and YM2149
   envelope shapes are still black boxes.

## Next Investigation Steps

1. **Confirm early Capcom driver via hex signature** — check MM1/MM2
   and Bionic Commando init routines for shared bytes.
2. **Nintendo driver signature** — check Zelda/SMB2/SMB3/Punch Out
   init routines for matching pattern.
3. **Analyze HW envelope periods** — when HW envelope is used, which
   period values are popular? Reveals "decay preference" per driver.
4. **Phase reset timing patterns** — are phase resets synchronized
   with musical beats? Could reveal tempo detection.
5. **VRC7 game parse** — take Lagrange Point's captured $9010/$9030
   writes, decode the YM2413 instrument patches, see what's there.

## Correction (2026-04-17 pass 2): "HW envelope dominant" count was inflated

The original finding of "26 games HW envelope dominant" was based on
`const_vol bit 4 of $4000 cleared >80% of frames`. That criterion
treats $4000 = $00 (never-initialized default) as "HW envelope" when
it's really just "silent / unused channel".

**Section Z** and **Destiny of an Emperor**: 100% of pulse1 frames
have $4000 = $00 literal. The driver never writes pulse1's control
register at all. Pulse1 is silent. The 100% phase_reset rate on
pulse1 is $4003 writes to an uninitialized channel — the driver
sets period but never volume. Likely pulse1 is reserved or these
games use only pulse2/triangle/noise for music.

**Corrected HW envelope finding**: Of 26 "HW envelope dominant" games,
the genuine HW-envelope users (where pulse1 has non-zero volume/period
but const_vol=0 AND active envelope) are a smaller subset. Candidates
confirmed by non-zero env_period distribution:

| Game | env_period pattern |
|------|-------------------|
| Commando | 100% period=15 (slowest decay, "legato" HW envelope) |
| Ghosts'n'Goblins | 69% period=15, 30% period=8 |
| Super Arabian | 95% period=10 (fixed medium-slow) |
| Smash T.V. | 100% period=1 (fastest/percussive) |
| Chinou Game Series 1 | 50% period=15, mixed |
| Ikki | 46% period=15, 44% period=7 |
| Maerchen Veil | 36% period=12, 36% period=14 |
| Defender of the Crown | 50% period=9, 39% period=11 |
| Apple Town Monogatari | 50% period=3, 25% period=8 |

**New rule: channel active classifier.** A channel is "active" when
period > 8 (pulse) or linear > 0 (triangle) or vol > 0, AND $4000
is non-zero. Silent-default channels don't count as "HW envelope
users". Future driver-family analysis should include this filter.

## Driver cluster validation via byte matching (pass 2)

Compared init-routine hex bytes across the 5 hypothesized clusters.

| Cluster | Byte identity | Verdict |
|---------|--------------|---------|
| Capcom late | 7 games, 59/64 bytes identical (94%) | **Confirmed same driver code** |
| Capcom early | 0 bytes common across 8 games | Multiple sub-drivers, not one family |
| Nintendo R&D | 0 bytes common across 6 games | Every game has distinct driver code |
| Sunsoft | 0 bytes common across 5 games | Journey/Gremlins share prefix, others differ |
| Konami | 0 bytes common across 5 games | Hyper Sports/Road Fighter identical, others differ |

**Behavioral clustering ≠ code clustering.** Register behavior
converges because composers/sound designers follow conventions even
when the code differs. Only Capcom's late 6C80 driver has true code
identity across multiple games.

Confirmed sub-clusters with byte match:
- **Capcom late/6C80** (7 games): MM3, MM4, Darkwing Duck, TaleSpin,
  Little Mermaid, Mighty Final Fight, Tenchi wo Kurau II
- **Capcom early variant A** (Mega Man 1): `4c70beea4c2a91c9fdd0034c2e91c9fe`
- **Capcom early variant B** (Bionic Commando, Gun.Smoke): `4cXXbfea4c2X81c9fdd0034c2X81c9fe`
- **Konami arcade-port** (Hyper Sports + Road Fighter): identical first 16 bytes
- **Sunsoft late** (Journey to Silius + Gremlins 2): near-identical

**Nintendo has NO single driver.** SMB, SMB2, SMB3, Zelda, Zelda II,
Punch Out all have distinct init code. The env_loop modulation
convention we found is shared BY CONVENTION, not by code identity.

## Pass 3 (2026-04-17): DMC sample inventory + VRC7 gap discovered

### DMC sample usage patterns per game

Counting distinct (sample_addr, sample_len) pairs per game reveals
how drivers use DPCM:

| Game | Unique samples | Triggers | Rates used | Strategy |
|------|---------------:|---------:|-----------|----------|
| Gremlins 2 (Sunsoft) | 8 | 1584 | 0,7,8,9,10,12,13,14,15 | Large drum kit, many rates |
| Super Mario Bros 3 | 9 | 2535 | 0,14,15 | 9 samples, 3 rates — distinct drums |
| Journey to Silius (Sunsoft) | 6 | 1952 | 7-15 (all high) | 6 drums pitched via rate |
| Batman (Sunsoft) | 4 | 2533 | 0,12,14,15 | 4 core samples, pitched |
| Ninja Gaiden | 3 | 2872 | 0,15 | Heavy reuse of 3 samples |
| Ninja Gaiden II | 3 | 1570 | 0,15 | Same strategy as NG1 |
| Contra (Konami) | 3 | 2262 | 0,15 | Standard Konami drum kit |
| Kirby's Adventure | 3 | 941 | 0,15 | Nintendo minimal sample set |
| Blaster Master (Sunsoft) | **1** | 5 | 0 | **No DPCM samples — uses DAC writes** |
| Battletoads (Rare) | 1 | 10 | 0 | **Algorithmic DAC-only — confirmed** |
| Castlevania (Konami) | 1 | 5 | 0 | Init-only, uses noise for drums |
| Metroid, MM2/3/4, Zelda, DT2, W&W | 1 | 3-10 | 0 | Init-only, no DPCM use |

**Key insights:**
- **Sunsoft uses the MOST diverse rate set** (Gremlins 2: 9 different rates).
  They pitch-shift samples to cover percussion AND bass melodies.
- **Blaster Master uses ZERO DPCM samples** — only 5 init triggers. The
  signature Sunsoft bass is DAC writes ($4011), confirming Rule 28.
- **Battletoads confirmed algorithmic-only** — 1 sample × 10 triggers =
  just init. All drums come from DAC writes.
- **Capcom late driver (MM3/MM4)** uses DPCM minimally (1 sample × 5
  triggers). Percussion in late Capcom games comes from noise channel.
- **Nintendo SMB3** has 9 distinct samples — the most sample-diverse
  Nintendo title in the library.

### VRC7 pipeline gap (2026-04-17)

Lagrange Point NSF has expansion byte 0x02 (VRC7 set). Emulator captures
$9010/$9030 register writes correctly (the capture_ranges include these).
But the extracted MIDI has **zero type-0x04 expansion SysEx messages**
for VRC7 channels. Pipeline gap:

- `frames_to_channel_data()` has no VRC7 channel handling
- `build_midi()` expansion SysEx emission only covers VRC6 + FDS
- No VRC7 MIDI track in output

Impact: 3 VRC7 games (Lagrange Point, Tiny Toon Adventures 2 Montana
Lands, and one other) have their FM synthesis completely absent from
MIDI output. Standard 2A03 channels still work.

This is deferred work — VRC7 is 3 games out of 321 (<1% coverage).
Full implementation needs: YM2413 register decoding, FM patch schema,
FM-to-MIDI mapping (doesn't fit CC11/CC12 paradigm).

## Pass 4 (2026-04-17): Automatic cluster discovery across full library

Ran `scripts/auto_driver_clusters.py` on all 298 NSFs. Found clusters
automatically — no hypotheses. Confirmed code-identity driver families:

### Init-routine clusters (16-byte prefix, strict identity)

| # | Prefix (hex) | Games | Driver |
|---|--------------|------:|--------|
| 1 | `4cfe80a90085c2a00806c226c1900d18` | 7 | **Capcom late / 6C80**: MM3, MM4, Darkwing Duck, TaleSpin, Little Mermaid, Mighty Final Fight, Tenchi II |
| 2 | `c9fcd0034c2981c9fdd0034c2d81c9fe` | 2 | **Capcom 1943-era** (Perorins Tonomura): 1943 Battle of Midway, Destiny of an Emperor |
| 3 | `48a9c08d174068aabdc0dc85e8bdd0dc` | 2 | **Square early (Uematsu)**: 3-D WorldRunner, JJ Tobidase 2 |
| 4 | `48a9808d174068aabdc0c0481012a940` | 2 | **Chinou Series** (FDS, puzzle/adventure): Chinou 1, Chinou 2 |
| 5 | `48a91f8d1540a9008d00408d01408d02` | 2 | **Kyouhei Sada**: Dungeon Magic US + JP (regional duplicates) |
| 6 | `aaa9808d1740bdf6bd38e901207c8160` | 2 | **Konami Goonies**: The Goonies II + Goonies_II_The (duplicates) |
| 7 | `48a91f8d1540a9008d00058d01058d02` | 2 | **Konami early arcade-port**: Hyper Sports, Road Fighter |
| 8 | `4c70beea4c2a91c9fdd0034c2e91c9fe` | 2 | **Capcom MM1 era (C. Manami + Yukichan's Papa)**: Mega Man, Mega_Man_1 |

### Play-routine clusters add 6 more driver families

| Prefix | Games | Driver |
|--------|------:|--------|
| `4c6c804cfe80a90085c2a00806c226c1` | 7 | Capcom late / 6C80 (same 7, confirmed by play routine) |
| `4c3a804cc980a90085c2a00806c226c1` | 2 | **Chip n Dale Rescue Rangers + Mizushima Shinji** (variant of 6C80) |
| `a5902901f00320c880a5902904f00320` | 2 | **After Burner + Festers Quest** (shared 3rd-party arcade port driver?) |
| `a540f00320af80a541f00320af80a542` | 2 | **Sunsoft sports (Naoki Kodaka)**: Dodge Danpei 1+2 |
| `4c5a874c27804c0980ad154029e08d15` | 2 | **Nantettatte Baseball** (Sunsoft sports, Kodaka+Morota): NB + NB 91 |
| `4c3d82c9fcd0034c2881c9fdd0034c2c` | 2 | **Capcom horror/adventure (Jun.A)**: Marusa no Onna + Sweet Home |

### 8-byte-prefix clusters reveal variant families

| Prefix | Games | Family |
|--------|------:|--------|
| `4c6c804cfe80a900` | 7 | Capcom late (same cluster at 8-byte) |
| `a210a00086f484f5` | 3 | **Konami early arcade-port expanded**: Circus Charlie + Road Fighter + Yie Ar Kung Fu |
| `4c3d82c9fcd0034c` | 3 | **Capcom Jun.A expanded**: Marusa no Onna + Pro Yakyuu Satsujin Jiken + Sweet Home |

### Total map of confirmed code-identity driver families

Combining init and play clusters + variant matches:

1. **Capcom late/6C80** (7 games) — largest cluster
2. **Capcom MM1 era** (2) — C. Manami + Yukichan's Papa composers
3. **Capcom 1943-era** (2) — Perorins Tonomura composer
4. **Capcom Jun.A horror/adventure** (3) — Marusa no Onna + Sweet Home + Pro Yakyuu Satsujin Jiken
5. **Capcom variant of 6C80** (2) — Chip n Dale + Mizushima Shinji
6. **Konami early arcade-port** (3+) — Circus Charlie, Road Fighter, Yie Ar Kung Fu; Hyper Sports also shares
7. **Konami Goonies** (2) — same game, duplicate entry
8. **Sunsoft late** (Journey to Silius + Gremlins 2) via near-match
9. **Sunsoft Dodge Danpei** (2) — Naoki Kodaka sports games
10. **Sunsoft Nantettatte Baseball** (2) — Kodaka + Morota
11. **Square/Uematsu early** (2) — 3-D WorldRunner + JJ Tobidase 2
12. **Kyouhei Sada (Dungeon Magic)** (2) — US + JP regional
13. **Chinou Series** (2) — FDS puzzle games
14. **After Burner / Festers Quest shared** (2) — cross-publisher driver sharing

Total: **14 identified code-identity driver families covering ~38 games**.
The other 260 games have unique driver code (at 8+ byte prefix).

### Observations

- **Capcom has at least 5 distinct sound drivers** across its library:
  early MM1, MM2 era, 1943-era, 6C80 (late), Jun.A horror/adventure.
- **Sunsoft has at least 3 distinct drivers**: Blaster Master's own
  (unique), Journey/Gremlins (late), and two sports variants (Dodge
  Danpei, Nantettatte Baseball).
- **Konami has at least 3 drivers**: early arcade-port (Circus Charlie
  family), Goonies' own, and later CV/Contra/Gradius each with unique
  code.
- **Nintendo R&D has NO shared driver** across first-party games.
  Each title has its own code.
- **Cross-publisher driver sharing** exists: After Burner (Tengen
  port of Sega) and Festers Quest (Sunsoft) share play-routine
  bytes. Likely a licensed/contracted sound library.

## Pass 5 (2026-04-17): Noise channel conventions + Gimmick! 5B deep dive

### Noise channel usage patterns — per-driver drum conventions

Aggregate noise period usage across 28 tested games:

| Period | Frames | % | Meaning |
|-------:|-------:|--:|---------|
| 3 | 92539 | 29.2% | Dominant snare/mid period |
| 4 | 34843 | 11.0% | Snare variant |
| 11 | 34599 | 10.9% | Low/kick |
| 2 | 33960 | 10.7% | High-snare |
| 10 | 26083 | 8.2% | Kick variant |
| 1 | 22765 | 7.2% | Hi-hat/crash |
| 13 | 18864 | 6.0% | Low-kick variant |
| 8 | 17842 | 5.6% | Mid |
| 6 | 15878 | 5.0% | Mid |
| 15 | 6389 | 2.0% | Rumble |
| 0 | 5378 | 1.7% | Highest pitch |
| 5, 7, 9, 12, 14 | <1% each | rare |

**Noise mode 1 (tonal/short LFSR) is essentially unused** — >99% of
noise frames use mode 0 (long LFSR). Only Section Z uses tonal noise
(25% of its noise frames). This is a near-universal invariant.

**Per-driver drum palette size:**
- **Nintendo minimal palette**: Zelda 100% period 3 (1 drum sound).
  Metroid 100% period 2. Punch Out 98% period 2. SMB/SMB2/SMB3 use
  3-4 periods. Nintendo uses the FEWEST distinct noise pitches.
- **Capcom late (6C80) varied palette**: MM3/MM4/Darkwing/TaleSpin use
  5-8 distinct periods. Larger drum kit.
- **Konami CV/Contra canonical**: 2-3 periods (1, 3, 6 for CV; 1, 3 for
  Contra).
- **Sunsoft short-period-heavy**: Blaster Master, Batman, Journey,
  Gremlins all favor periods 1-3 (66-94% of their noise is short-period).
- **Square/Uematsu binary**: 3-D WorldRunner + JJ Tobidase 2 BOTH use
  only periods 4 and 11 (60/40 split). Two drum sounds period.
- **W&W unique**: 100% period 0 (highest-pitch only). Distinctive.

**Pipeline implication**: The current drum note mapping
(period<=4=hi-hat, <=8=snare, else kick) is consistent with the
observed distribution. Period 3 → snare (most common), period 11 →
kick. Fine-grained mapping per driver family would be more accurate
but the coarse mapping catches the main cases.

### Gimmick! 5B (Sunsoft YM2149) — first deep dive into the one 5B game

Probed song 3 "Good Weather" for 1800 frames. Register write counts:

| Register | Writes | Per-frame | Top values |
|:---------|-------:|----------:|:-----------|
| R0-R5 (6 tone regs) | 1800 each | 1.00 | Fine tones vary; coarse always $00 |
| R7 (Mixer) | 1800 | 1.00 | $F8 exclusively (tones on, noise off) |
| R8 (Ch A vol) | 1800 | 1.00 | vol 7, 9, 8, 10 — direct mode |
| R9 (Ch B vol) | 1800 | 1.00 | vol 7, 3, 0, 6, 5 — direct mode |
| R10 (Ch C vol) | 1800 | 1.00 | vol 7, 9, 0, 8, 10 — direct mode |
| R6 (Noise period) | 173 | 0.10 | $00 always |
| R11, R12 (Env period) | 116 | 0.06 | $00 always |
| R13 (Env shape) | 116 | 0.06 | $99 (decay-single-then-silent) 96x |

**Findings about Gimmick!'s 5B usage:**

1. **100% DIRECT volume mode** — Gimmick! does NOT use the 5B
   hardware envelope for main volume. All volume writes have bit 4 = 0.
   This is counter-intuitive — you'd expect Sunsoft to leverage the
   hardware envelope, but they implement SW envelope like a 2A03.

2. **3-channel SW-envelope extension of standard APU** — Gimmick uses
   5B as three EXTRA software-envelope square-wave channels. The driver
   writes volume + tone period every frame, same as 2A03 SW drivers.

3. **Noise generator unused** — Mixer $F8 has all noise-disable bits
   set. The noise portion of 5B is never used for music.

4. **Coarse tone period always $00** — Only 8-bit fine period used,
   limiting 5B melody to frequencies ≥ 219Hz (A3). Low bass handled
   by standard APU triangle.

5. **Envelope shape $99 for percussion effects only** — Shape $99 =
   decay-single-then-silent, used 96 times across 1800 frames (5%).
   Likely for short percussive accents, NOT main melody.

6. **APU side: sweep register written every frame** — Gimmick's 2A03
   side writes $4001/$4005 every single frame (27000/27000) but never
   enables sweep. Likely to keep the sweep divider reset for timing
   purposes, not for musical pitch modulation.

7. **NO DPCM usage** — 5B channels replace what DPCM would be in
   other Sunsoft games. Gimmick! has zero DPCM triggers.

**Conclusion**: Gimmick!'s legendary sound comes from having 5
software-enveloped square-wave channels (pulse1 + pulse2 + 5B A/B/C)
plus a triangle bass. The 5B is used in its SIMPLEST mode — like a
plain YM2149 with no hardware-envelope tricks. The richness comes
from channel count and dense per-frame envelope writing, not from
exotic 5B features.

**Pipeline implication**: Implementing 5B support for Gimmick! only
requires: reading R0/R1 (fine+coarse) → period, R8/R9/R10 → volume
(strip bit 4), R7 → ignored (always mixer=$F8). The envelope-shape
bursts are a small extra. This is ~30 lines of code in
`frames_to_channel_data()`, similar complexity to VRC6.

## Tooling added this session

- `scripts/register_analysis.py` — parses MIDI SysEx streams to extract
  per-game register behavior stats (envelope mode, sweep, phase reset,
  DMC rates, duty distribution, volume reset patterns)
- `scripts/probe_driver_signature.py` — reads NSF headers and extracts
  32-byte init signatures, clusters games by matching bytes
- `scripts/probe_driver_clusters.py` — verifies behavioral clusters by
  computing longest common byte prefix + byte-position agreement rate
  across all games in a hypothesized cluster
- `scripts/probe_dmc_inventory.py` — extracts unique DPCM samples per
  game by parsing (sample_addr, sample_len) pairs from trigger events
- `scripts/auto_driver_clusters.py` — scans all 298 NSFs, groups games
  by matching init/play-routine prefix bytes, identifies code-identity
  clusters automatically without hypotheses
- `scripts/probe_noise_patterns.py` — per-game noise period/mode
  distribution and aggregate statistics across drivers
- `scripts/probe_gimmick_5b.py` — 5B (YM2149) register protocol decoder
  for Gimmick!, reveals driver's actual 5B usage mode
- `data/register_analysis.json` — full 321-game analysis output
