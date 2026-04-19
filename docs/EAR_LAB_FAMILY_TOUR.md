# Ear Lab — driver family tour

A curated 14-game listening trip across every NES driver family in our
library.  Each family has characteristic quirks.  Going through this
tour in one sitting gives you a complete sense of how each variant
(A/B/C) handles the range of games we care about.

Pick a song from each group, open it in all three variants, and
compare.  Estimated time: 30-60 minutes depending on how thoroughly
you listen.

Games marked `⏳ pending` are still in the main rebuild queue.  Games
marked `✓ ready` have A/B/C variants already generated.

## 1. Capcom / Kondo family

Two generations.  "Continuous refresh" (early) writes `$4015` every
frame; "init-once" (late) trusts the NSF player.  Rule 36 fixed the
init-once games.

- **Mega_Man_1** (early Capcom) — iconic pulse leads, minimal noise.
  Sharp attacks on keyboard.
  ⏳ pending (main rebuild not yet at M)
- **Mega_Man_2** — same engine, denser composition.
  ⏳ pending
- **DuckTales** — early Capcom Disney.  Very bright pulses; tests
  Rule 35 (bandlimited) the hardest.
  ⏳ pending
- **Darkwing_Duck** — late Capcom, noise drums via length counter.
  ⏳ pending
- **Little_Mermaid** — late Capcom, pulse-dominant with triangle
  bass counterline.
  ⏳ pending

**Listen for**: pulse grit on high notes (Rule 35 absence in JSFX).
Crisp drum hits in stems vs wash in JSFX (Rule 30 absence).

## 2. Konami / Maezawa family

Mostly "init-once."  Uses triangle + noise prominently.

- **Castlevania** — Vampire Killer bassline is the canonical
  triangle staccato test.  Rule 34 (gate-off DAC hold) is the
  difference-maker.
  ✓ ready
- **Castlevania_2_Simons_Quest** — similar engine, more melodic.
  ⏳ pending
- **Castlevania_3_Draculas_Curse_JP** — VRC6 expansion audio.
  Tests our always-capture-VRC6 fix.
  ⏳ pending
- **Gradius** — Konami arcade-to-NES conversion.
  ⏳ pending
- **Contra** — hybrid (writes `$4015` per-frame for boss
  sections).  DPCM voice samples.
  ⏳ pending

**Listen for**: Triangle pops (should be GONE in both stems and JSFX
now that Rule 34 ported).  VRC6 saw on CV3 JP.

## 3. Rare / Wise-Follin family

Uniformly init-once.  Every Rare game had silent noise before the
Rule 36 fix.  Noise-heavy.

- **Battletoads** — pause theme is famous.  Drums prominent.
  ✓ ready
- **Wizards_and_Warriors** — Follin-style progressive metal-chiptune.
  ⏳ pending
- **Marble_Madness** — simpler but distinctive.
  ⏳ pending

**Listen for**: Every drum hit should trigger and decay crisply.
If noise sounds "washed out" or continuous, that's Rule 30 not
being in JSFX.

## 4. Sunsoft family

Heavy `$4011` DAC bass writes.  Split into early (init-once) and
late (continuous refresh with DPCM).

- **Blaster_Master** — early Sunsoft.  Triangle + DAC bass
  combination.
  ⏳ pending
- **Journey_to_Silius** — late Sunsoft.  DPCM voice + bass.
  ⏳ pending
- **Batman** — late Sunsoft (Tim Follin!).
  ⏳ pending
- **Gremlins_2** — late Sunsoft with heavy DPCM samples.
  ⏳ pending

**Listen for**: Bass warmth — Sunsoft's DMC DAC bass should sound
present and weighty, not just clicks.  Rule 28 handles this.

## 5. Nintendo 1st-party family

Split: Kondo-era init-once vs later continuous-refresh.

- **Super_Mario_Bros** — the `$4011 = 48` DC bias oddity
  (documented in NEWDRIVERFAMILIES.md §5).  Drum samples via DPCM.
  ⏳ pending
- **Metroid** — Brinstar (Hirokazu Tanaka).  Song 1 Intro was
  truncated in the pre-fix renders; now correct at 92 s.
  ✓ ready (via the Metroid-specific render we did)
- **Kid_Icarus** — same composer as Metroid.
  ⏳ pending
- **Legend_of_Zelda** — Kondo Zelda Overworld.  Check the
  triangle bassline.
  ⏳ pending
- **Zelda_II** — continuous-refresh successor.  Palace theme is a
  good melodic test.
  ✓ ready

**Listen for**: Distinctive composer voices (Kondo vs Tanaka).
Bass weight (triangle is the foundation on these games).

## 6. Square / Enix family

RPG music.  Less percussion-driven, more atmospheric.

- **Final_Fantasy** — Uematsu's iconic Prelude.  Mostly pulse +
  triangle, very few drums.
  ⏳ pending
- **Dragon_Warrior** — Sugiyama's classical-style Overworld.
  ⏳ pending
- **Final_Fantasy_II** — longer arrangements.
  ⏳ pending

**Listen for**: Pulse timbre purity.  RPG music tests sustained notes
where Rule 35 (bandlimited pulse) matters most.

## 7. Tecmo / Follin family

Tim Follin's extraordinary driver.  Noise-heavy with pitched drums.

- **Ninja_Gaiden** — every theme has complex noise percussion.
  ⏳ pending

**Listen for**: Noise prominence.  If JSFX handles Tim Follin's
noise right, it handles noise right for almost any game.

## Suggested listening session

1. Start with **Castlevania Vampire Killer** (✓ ready) in all
   three variants — the triangle fix is the most audible win.
2. Then **Battletoads** (✓ ready) for drum-heavy Rare feel.
3. Then **Balloon_Fight** (✓ ready) for clean, simple baseline.
4. Then **Zelda_II** (✓ ready) for Nintendo mid-era.
5. Wait for the main rebuild to catch up to each subsequent family
   and continue.

## Report back

Once you've listened through 3-5 games, open
**docs/EAR_LAB_REPORT_CARD.md** and fill in your verdict.  Paste that
back at me and I'll know which DSP port work (if any) to do next.
