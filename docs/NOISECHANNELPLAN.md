# Plan: getting the noise channel sounding like the game drums

Companion to `STATEOFTHEPROJECT.md` and `NOISEPROBLEM.md`.

This plan is for restoring the noise channel to audible fidelity on
the games where it's currently silent or wrong -- specifically
targeting the "noise channel is supposed to have drums but doesn't"
issue that showed up in the Battletoads/CV/W&W investigation.

As of 2026-04-18 evening, the biggest root cause has been found and
fixed (NSF player init, `architecture.md` Rule 36).  This plan
covers (1) what still needs verification, (2) the remaining
per-driver-family edge cases, and (3) how to validate fixes without
just trusting the render to sound right.

## Status after today's fixes

The evening brought two noise-adjacent wins:

1. **Noise length counter simulation** (Rule 32, landed morning).
   SMB / Nintendo-family noise drums now silence correctly instead
   of washing continuously.
2. **NSF player $4015 init** (Rule 36, landed evening).  Noise was
   entirely silent for ~30% of games because their drivers relied on
   the NSF player to enable channels before INIT.  Post-fix survey:
   Battletoads, CV, Gradius, Kid Icarus, Wizards & Warriors, Spy
   Hunter, Kirby, Ninja Gaiden, and many more now produce noise
   drums matching the `$400F` write pattern of the original driver.

Known hardware behaviors still covered correctly (Rules 30-32):

- `$4015 bit 3` gates output
- `$400F` loads length counter (when enabled)
- `$400C bit 5` (env_loop) halts length counter decrement
- Length counter decrements by 2 per frame (2 half-frame ticks)
- `$4015 bit 3 = 0` forces length counter to 0

## What's NOT yet proven to work

Per-driver-family verification not yet complete.  The audit shows the
length counter is ACTIVE on most games, but "active in capture" is not
the same as "matches the original game acoustically."  The user's ear
test on Battletoads earlier this session confirmed the recent fixes
make Battletoads better, but noise was silent in that render and is
now audible post-Rule 36 -- meaning the user heard a version WITHOUT
noise drums before.  The new version with noise drums may or may not
match their memory of the game.

Three categories of uncertainty:

### 1. Audible correctness on Rare noise drums

Battletoads, Wizards and Warriors, Cobra Triangle, Marble Madness now
all produce noise output.  `n_lc > 0` counts are high (562-1188 per 3
songs).  But we haven't confirmed the drums sound like the original
games.  Rare drivers use noise aggressively; a bug in noise period
mapping or length-counter decrement rate would be very audible.

Test protocol:
- Render Battletoads song 1 at 60 s.
- A/B compare against a reference (libgme command-line render, or a
  known-good FCEUX/Mesen dump, or YouTube gameplay footage).
- If drums match, move to song 2.  If not, compare per-hit noise
  period and volume at specific timestamps.

### 2. Silent-before-fix games with NO verified drum source

Some games came back silent-noise in the audit but DO have drums in
the original.  Investigation flow:

- **Gradius**: $4015 never written, noise vol never written in song 1.
  But Gradius has drums on hardware.  Hypothesis: drums are on a
  later song.  Action: audit all 32 Gradius songs.
- **Metroid**: 0 $4015 writes, 0 noise vol in song 1.  But Metroid's
  item get jingle and boss music have obvious noise drums.  Action:
  audit songs beyond song 1.
- **Final Fantasy / Dragon Warrior**: similar.  Many RPG songs don't
  have percussion in the overworld; drums appear in combat/boss.

### 3. $4015 bit 3 clear-during-play drivers

Some drivers actively silence noise per-frame by clearing bit 3 (a
pattern seen on certain racing games and sfx-heavy titles).  Our
current gate handles this correctly (`length_counter = 0` when bit
cleared).  But we should verify the bit-clear frames correspond to
expected silent moments, not bugs where noise is over-silenced.

Games to check:
- Any game in the `silent_bit3_unset` audit bucket pre-fix --
  recheck that they really are silent on hardware.  Use libgme for
  reference.
- Wheel of Fortune (both editions): 206 enabled frames but 0 vol
  writes -- possibly meant to be silent.

## Action items ordered by impact

### P1: Verify Battletoads / Rare noise drums acoustically (30 min)

Render Battletoads song 1 + song 2 post-fix.  A/B against Zophar's
Music Domain or YouTube reference.  Document match / mismatch.

If drums sound right: Rule 36 is validated for Rare drivers, the
main noise restoration story is done.  Move to P2.

If drums are wrong in an identifiable way (wrong pitch, wrong length,
wrong accent pattern): drill into `render_channel_stems.py` noise
renderer, compare per-frame to a tracked FCEUX trace.

### P2: Run the rebuild_v6 across all 44 games post-fix (already running)

The rebuild is regenerating every outputv5 game into outputv6 with
Rule 36 active.  Est 15-30 min total.

After completion, re-run the audit script to confirm noise output is
present on games where it was silent before, and that no game that
was previously working has regressed.

### P3: Survey uncovered songs on RPG-family games (1 hour)

Final Fantasy, Dragon Warrior, Zelda 1/2 -- their song 1 is usually
title or overworld with no drums.  Extend the audit to all songs per
game.  If any song in these RPGs has drums in the original but silent
noise in our render, investigate.

### P4: SMB $4011 DAC investigation (2 hours)

SMB writes $4011 1797 times per 3 songs (nearly every frame).  This
is unusual.  Possibilities:

- Driver uses $4011 as an auxiliary DAC for sfx.
- Our capture is picking up non-music register writes.
- Driver uses $4011 for "click" articulation on note attacks.

Render SMB with DMC stem muted.  If output sounds clearly better /
cleaner, $4011 was contributing noise.  If it sounds worse / missing
elements, the DAC writes are intentional music.

### P5: Detect and verify $4015 bit-clear-during-play drivers (1 hour)

Some drivers clear $4015 bit 3 to stop notes (instead of writing
vol=0 or length counter).  Find these in the 30-game survey, verify
our gate responds correctly, and compare a specific moment against
reference.

### P6: Expansion-chip init survey (2 hours)

Analogous to Rule 36 for expansion chips.  NSF players are
conventionally supposed to write $4010 = 0 (DMC IRQ off), $4017 =
$40 (frame IRQ off) before INIT.  We now do $4017.  But expansion
chips (VRC6 $9000-9002, N163 $4800-$F800, FDS $4089, 5B $C000-$E000)
may need their own init.

Games with expansion audio that might still have silent channels:

- VRC6: Castlevania 3, Madara, Esper Dream 2
- N163: Mega Man Wily Tower, Rolling Thunder, Megami Tensei 2
- FDS: Kid Icarus (FDS), Doki Doki Panic, Yume Koujou Doki Doki Panic
- MMC5: Just Breed, Metal Slader Glory, Uchuu Keibitai SDF
- 5B: Gimmick!, Lagrange Point

For each: survey if the expansion channel has silent output despite
the driver writing to it.  If yes, add expansion-init writes
analogous to Rule 36.

### P7: Long-term: Blargg BLEP port (deferred, see RESEARCH_ANTIALIAS.md)

Fully replaces our analytical-integration pulse + naive noise LFSR
with Blargg's delta-based BLEP resampling.  Eliminates the remaining
~15 clicks/sec of pulse aliasing AND properly handles noise LFSR
edges at fast period indices.  1 day of work.  Parallel track to the
noise investigation -- shouldn't block noise validation.

## Validation methodology

For each game we care about, the validation protocol is:

1. **Render**: `python scripts/render_channel_stems.py <nsf> --song N --seconds 60 --out-dir <tmp>`
2. **Reference**: libgme render at same sample rate, OR Zophar's Domain
   OGG, OR YouTube gameplay capture (noise-isolated via bandpass if
   needed).
3. **Visual diff**: spectrogram comparison via `scripts/visual_compare.py`
   (exists, verify it handles stems).
4. **Acoustic diff**: short A/B by ear at specific seconds.
5. **Per-register diff**: if above reveal differences, dump the
   exact frames and register writes for the mismatch window.

The acoustic step is authoritative.  Spectrogram diffs catch macro
issues but miss click/pop artifacts that were the whole reason we're
here.  Log all results in a per-game validation record under
`docs/noise_validation/<game>.md` so we can see which games are
confirmed-good over time.

## What to ask the user for

When the rebuild completes, the most valuable thing the user can do:

- Pick 3-5 games with distinctive drum patterns they remember:
  - Battletoads song 1 (pause screen theme, iconic drums)
  - Castlevania Vampire Killer (Stage 1)
  - Contra stage 1
  - Super Mario Bros Overworld
  - DuckTales Moon theme
- Ear-test outputv6 vs their memory.  Report by game: "drums sound
  right / wrong / missing / extra."
- Any "wrong" report kicks in the P1/P3 validation flow for that game.

## Success criteria

We call this plan done when:

- Every game in the "noise-heavy" driver families (Capcom,
  Konami, Rare, Sunsoft, Tecmo) has noise output matching the
  driver's `$400F` write pattern, verified by audit script.
- At least 5 user ear-tests across different driver families confirm
  "drums sound like the game."
- No regression in the games that were working before Rule 36 (SMB,
  Contra, DuckTales, MM1/2, JtS, Batman, Gremlins 2, Zelda II).

This plan's predecessor documents:
- `RESEARCH_ANTIALIAS.md` -- community techniques
- `NOISEPROBLEM.md` -- diagnosis of the click/pop symptoms
- `STATEOFTHEPROJECT.md` -- overall state
- `NEWDRIVERFAMILIES.md` -- driver-pattern taxonomy
