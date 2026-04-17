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

## Tooling added this session

- `scripts/register_analysis.py` — parses MIDI SysEx streams to extract
  per-game register behavior stats (envelope mode, sweep, phase reset,
  DMC rates, duty distribution, volume reset patterns)
- `scripts/probe_driver_signature.py` — reads NSF headers and extracts
  32-byte init signatures, clusters games by matching bytes
- `scripts/probe_driver_clusters.py` — verifies behavioral clusters by
  computing longest common byte prefix + byte-position agreement rate
  across all games in a hypothesized cluster
- `data/register_analysis.json` — full 321-game analysis output
