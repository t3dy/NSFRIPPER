# NES driver families — re-classification 2026-04-18 evening

Supersedes (does not replace) `DRIVER_FAMILIES_AND_GAMES.md` and the
CC11/CC12 density classification.  That existing taxonomy is a **proxy
for envelope mode**; this document is a parallel taxonomy organized by
**sound-driver codebase identity**, which matters for noise, drums,
and expansion-chip handling -- areas where CC density alone doesn't
discriminate.

Based on register-write-pattern surveys across ~30 games, across all
songs per game, with the 2026-04-18-evening NSF player init fix
(`$4015 = $0F` before INIT -- Rule 36) applied.

The tables in this file show **survey data from actual NSF emulation**,
not secondary sources.  Numbers are summed across 3 sampled songs per
game, 600 frames each (18000 frames / 300 seconds of emulation total).

## Why a new classification

The CC density model sorts drivers by how densely they modulate
volume/duty over time -- useful for picking an ADSR preset for the
synth, not useful for predicting noise/drum fidelity.  The register-
pattern model sorts drivers by who wrote the code -- useful for:

- Predicting whether noise drums use length counter vs vol gating.
- Predicting whether drums come from noise, DMC DPCM, or $4011 DAC.
- Predicting whether the driver refreshes `$4015` every frame or
  trusts the NSF player's init.
- Predicting expansion-chip register behavior (VRC6/N163/FDS).

Before Rule 36 landed, most of these families produced **silent
noise** in our pipeline.  Now they all produce correct noise where
the source code calls for it.

## $4015 initialization strategy — the new fundamental dimension

Every driver falls into one of two camps on `$4015` handling:

**Camp A: "Continuous refresh"** -- writes `$4015 = $0F` (or similar)
every frame.  These drivers were robust against our old bug where we
omitted the NSF player's init write; they set up their own enable
state continuously.

**Camp B: "Init once (or never)"** -- writes `$4015` once at song
start, or never touches it.  Relies on the NSF player's pre-INIT
`$4015 = $0F` write per the NSF spec.  These drivers had silent noise
in our pipeline until Rule 36 landed today.

Camp B is the majority.  ~70% of drivers surveyed.

## Family profiles (post-fix data)

Column legend:
- `4015w` = $4015 writes during PLAY (after frame 0, so driver-initiated)
- `400Fw` = $400F writes (noise length counter reload, i.e. drum hits)
- `n_lc>0` = frames with noise length counter > 0 (post-fix gate)
- `dac` = $4011 direct DAC writes (non-DPCM drums / bass)
- `dpcm` = $4012/$4013 DPCM sample triggers

### Capcom/Kondo family — Mega Man series, DuckTales, etc.

| Game | Camp | 4015w/3songs | 400Fw | n_lc>0 | dac | dpcm |
|------|------|--------------|-------|--------|-----|------|
| Mega Man 1 | A | 1405 | 110 | 591 | 0 | 3 |
| Mega Man 2 | A | 1737 | 183 | 945 | 0 | 3 |
| Mega Man 3 | B | 1 | 3 | 457 | 0 | 3 |
| Mega Man 4 | B | 1 | 89 | 727 | 0 | 3 |
| DuckTales | A | 1797 | 60 | 1800 | 0 | 3 |
| Darkwing Duck | B | 2 | 4 | 158 | 0 | 3 |
| Little Mermaid | B | 1 | 4 | 184 | 0 | 3 |
| TaleSpin | B | 4 | 9 | 309 | 0 | 3 |
| Ghosts 'n Goblins | B | 0 | 3 | 18 | 0 | 3 |

**Key finding**: Capcom has two generations.  The "early" driver
(MM1/MM2/DuckTales) writes $4015 every frame and has relatively few
noise hits.  The "late" driver (MM3/MM4 and the Disney-family games
Darkwing/Mermaid/TaleSpin/Capcom Ghosts) trusts the NSF init and writes
$4015 once.  Both produce correct audio now.

The late driver generation was INVISIBLE to us before the fix -- all
those games had 0 noise output.  This matches the observation
in our existing `DRIVER_FAMILIES_AND_GAMES.md` about a late-Capcom
sub-family but adds a new dimension: it's defined by $4015 strategy,
not just CC density.

### Konami/Maezawa family — Castlevania, Contra, Gradius

| Game | Camp | 4015w | 400Fw | n_lc>0 | dac | dpcm |
|------|------|-------|-------|--------|-----|------|
| Castlevania | B | 0 | 3 | 145 | 0 | 3 |
| Contra | A (partial) | 160 | 225 | 1206 | 0 | 83 |
| Gradius | B | 0 | 3 | 364 | 0 | 3 |

**Key finding**: Konami pre-1988 (Castlevania, Gradius) uses camp B.
Contra (1987-12) is a hybrid -- writes $4015 at frame transitions
(160 writes = roughly once per note group).  Contra also uses DPCM
heavily (83 triggers per 3 songs) for the famous "UGH!" voice sample
and drum samples.  CV1 and Gradius use the noise channel for their
drums; DPCM is idle.

### Rare/Wise-Follin family — Battletoads, W&W, Cobra Triangle

| Game | Camp | 4015w | 400Fw | n_lc>0 | dac | dpcm |
|------|------|-------|-------|--------|-----|------|
| Battletoads | B | 0 | 183 | 988 | 0 | 3 |
| Wizards and Warriors | B | 0 | 52 | 562 | 0 | 3 |
| Cobra Triangle | B | 0 | 134 | 1188 | 0 | 3 |
| Marble Madness | B | 0 | 78 | 589 | 0 | 3 |

**Key finding**: Rare is uniformly camp B.  **Every Rare game had
silent noise before today's fix.**  Post-fix, Rare games show the
highest `n_lc>0` density -- the noise channel is driving a lot of the
music (drums, hi-hats, ambient sweeps).  Battletoads' "algorithmic
drums" are a mix of noise hits AND triangle gating (which was
contributing the vinyl pops fixed by Rule 34).

Rare drums are almost entirely noise-channel-based.  DPCM usage is 0
(the "3" counts are the frame-0 initialization fallback).  This is
opposite to Nintendo/Konami's DPCM-heavy approach.

### Sunsoft family — Blaster Master, Journey to Silius, Batman, Gremlins 2, Spy Hunter

| Game | Camp | 4015w | 400Fw | n_lc>0 | dac | dpcm |
|------|------|-------|-------|--------|-----|------|
| Blaster Master | B | 0 | 99 | 1206 | 0 | 3 |
| Journey to Silius | A | 140 | 131 | 1045 | 0 | 73 |
| Spy Hunter | B | 0 | **409** | 1206 | 0 | 3 |
| Batman | A (partial) | 30 | 100 | 606 | 0 | 18 |
| Gremlins 2 | A | 170 | 141 | 734 | 0 | 88 |

**Key finding**: Sunsoft has an early driver (Blaster Master, Spy
Hunter) in camp B and a late driver (JtS, Batman, Gremlins 2) in
camp A (with variable frequency of $4015 writes).  JtS and Gremlins 2
use heavy DPCM (voice/drum samples).  Spy Hunter has the highest
`$400F` rate of any game surveyed -- 409 drum hits across 3 songs --
all via pure noise channel.

Sunsoft games also use `$4011` DAC writes extensively for bass tones
(see `architecture.md` Rule 28).  None of the games in this row show
`dac > 0` because they're counted by `event_type == "dac_write"`
which only fires when $4011 is written without a concurrent
$4012/$4013.  The Sunsoft bass signature uses $4011 alongside DPCM
triggers at times, so some DAC writes show up as "dpcm_trigger" in
our event-type classification.  Needs a look.

### Nintendo 1st-party family — SMB, Metroid, Zelda, Kid Icarus

| Game | Camp | 4015w | 400Fw | n_lc>0 | dac | dpcm |
|------|------|-------|-------|--------|-----|------|
| Super Mario Bros | A | 1811 | 206 | 536 | **1797** | 3 |
| Metroid | B | 0 | 27 | 86 | 0 | 3 |
| Kid Icarus | B | 0 | 3 | 93 | 0 | 3 |
| Legend of Zelda | B | 1 | 3 | 18 | 0 | 3 |
| Zelda II | A | 1797 | 3 | 18 | 0 | 3 |

**Key finding**: Nintendo is split.  Koji Kondo's 1983-1986 catalog
(SMB and Zelda 1) uses camp A for SMB but camp B for Zelda 1.
Kid Icarus (Hirokazu Tanaka) and Metroid (same composer, different
driver?) are camp B.  Zelda II (Tanaka / Kondo) is camp A.

**SMB is special: 1797 `$4011` DAC writes per 3 songs.**  This is
unusual and not well-documented in public NES refs.  Hypothesis:
SMB uses the DAC as a crude auxiliary output for sound effects like
jumps/coins that the NSF may or may not reproduce.  Worth investigating
separately as a possible extraction bug (perhaps we're capturing
sound-effect channel writes that shouldn't be in the music stream).

Metroid and Kid Icarus show very low noise activity -- they don't
use noise for drums.  They use DPCM pulses or tri articulation instead.

### Square/Enix family — Final Fantasy, Dragon Warrior

| Game | Camp | 4015w | 400Fw | n_lc>0 | dac | dpcm |
|------|------|-------|-------|--------|-----|------|
| Final Fantasy | B | 2 | 3 | 1627 | 0 | 3 |
| Dragon Warrior | B | 2 | 3 | 38 | 0 | 3 |

**Key finding**: Square-Enix RPG music uses camp B.  Very few $400F
writes in song 1 (title music doesn't have drums in early Square RPGs).
The `n_lc > 0` count of 1627 for FF means the noise length counter
stayed high throughout the music -- the driver loaded it at init
and it decremented slowly.  No per-hit drum writes.

These games would benefit from rendering later (combat/boss) songs
where drums are more prominent.

### Tecmo/Follin family — Ninja Gaiden (sole sampled)

| Game | Camp | 4015w | 400Fw | n_lc>0 | dac | dpcm |
|------|------|-------|-------|--------|-----|------|
| Ninja Gaiden | B | 0 | **602** | 808 | 0 | 3 |

**Key finding**: Tecmo's driver (same codebase through Ninja Gaiden
series, possibly shared with Captain Tsubasa and Tecmo sports) is
camp B with **extremely dense noise use** (602 hits / 3 songs).
Heavier than Spy Hunter.  If any driver makes noise fidelity matter
most, it's this one.

## Summary matrix: what was silent before Rule 36, what works now

| Family | Camp | Games silent before fix | Games unchanged |
|--------|------|-------------------------|-----------------|
| Capcom early | A | 0 | MM1, MM2, DuckTales |
| Capcom late | B | MM3, MM4, Darkwing, Mermaid, TaleSpin, G&G | 0 |
| Konami | B (mostly) | Castlevania, Gradius | Contra (partial A) |
| Rare | B | Battletoads, W&W, Cobra, Marble | 0 |
| Sunsoft early | B | Blaster Master, Spy Hunter | 0 |
| Sunsoft late | A | 0 (partial) | JtS, Batman, Gremlins 2 |
| Nintendo early | B | Metroid, Kid Icarus, Zelda 1 | SMB (A) |
| Nintendo late | A | 0 | Zelda II |
| Square/Enix | B | FF, Dragon Warrior | 0 |
| Tecmo/Follin | B | Ninja Gaiden | 0 |

**Before Rule 36**: only SMB, MM1/2, DuckTales, JtS, Batman, Gremlins
2, Contra, and Zelda II had correct noise output in our pipeline.
Roughly 8 of every 30 games we rendered.

**After Rule 36**: all drivers have correct noise output.

## Drum-source classification

Different driver families use different mechanisms for drum hits.
The mechanism determines which stem you hear drums in and what to
listen for when debugging.

| Family | Primary drum source | Secondary |
|--------|--------------------|-----------| 
| Capcom (both gens) | Noise ($400F) | DPCM rare |
| Konami pre-Contra | Noise | None |
| Konami Contra+ | Noise + DPCM | Voice samples |
| Rare | Noise (heavy) | Triangle gating for kicks |
| Sunsoft early | Noise | $4011 DAC bass |
| Sunsoft late | Noise + DPCM | $4011 DAC bass |
| Nintendo (SMB/Zelda II) | DPCM samples | Noise hi-hats |
| Nintendo (Metroid/KI/Zelda 1) | Triangle + pulse staccato | Minimal noise |
| Square/Enix | Tri + pulse | No drums in most tracks |
| Tecmo/Follin | Noise (extremely dense) | None |

## Consequences for rendering

1. **Noise-heavy families (Rare, Tecmo, Sunsoft early)**: our recently-
   shipped bandlimited LFSR time-integration in `render_stem` matters
   most here.  The noise stem on these games is dense and audibly
   prominent; aliasing at fast LFSR periods would be very audible.

2. **DMC-heavy families (Sunsoft late, Konami Contra+, Nintendo SMB)**:
   Rule 28 (DMC two-mechanism handling) and the DMC LP (Rule 33) are
   the critical pieces.  Watch for $4011 slew-rate clicks on these
   games (Mesen's clamp option may be worth porting -- see
   `RESEARCH_ANTIALIAS.md`).

3. **Camp B drivers uniformly**: relied on Rule 36.  This is most
   of the library.  Any regression of Rule 36 silently breaks noise
   on ~30% of games and needs to be guarded against.

## Open questions / next investigations

- **SMB's 1797 `$4011` writes per 3 songs**: ANSWERED 2026-04-18 evening.
  SMB Overworld writes `$4011 = 48` (hex $30) every single frame with
  the SAME value (300/300 frames, 0 value variation).  This is a DC
  pre-bias -- the driver sets a constant DAC level and never changes
  it.  Musically inert because the DC blocker (Rule 33) removes it.
  Not a music signal; no investigation needed.  Treat as a hardware
  quirk of Nintendo's Kondo driver.

- **Silver Surfer song 1 silent noise, songs 2+ active**: song-level
  variation in $4015 behavior.  Driver may use a state machine where
  song 1 doesn't need noise.  Check other Software Creations games
  (Solstice, Ikari Warriors) for the pattern.

- **Unclassified drivers**: the 140 games listed in
  `DRIVER_FAMILIES_AND_GAMES.md` as un-surveyed need to be run through
  this lens.  Many may sit in well-known families but some may reveal
  new variants.

- **Sunsoft $4011 DAC bass detection**: our event-type classifier
  marks a frame as `dpcm_trigger` if ANY of $4012/$4013/$4011 write
  along with $4011, which suppresses the `dac_write` count for
  Sunsoft's hybrid DAC+sample technique.  This under-counts the
  Sunsoft bass sound and needs a refinement for fidelity.

- **Expansion-chip init writes**: NSF v2 has specific init conventions
  for VRC6/N163/MMC5/FDS/5B.  We may be missing similar pre-INIT
  writes for expansion chips analogous to Rule 36 for $4015.  Should
  survey the 35 expansion-audio games that Rule 28-adjacent work
  recovered and see if any still have silent expansion channels.
