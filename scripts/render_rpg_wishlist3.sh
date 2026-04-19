#!/usr/bin/env bash
# Part 3: RPGs whose NSFs we pulled once the Zophar index cache was built
# and the fuzzy slug resolver was wired up.  Chains after part 2 finishes
# the Nintendo classics.
set -u
cd "$(dirname "$0")/.."

while ! grep -q "=== DONE ===" outputv6/_log_nintendo_classics.log 2>/dev/null; do
  sleep 60
done

games=(
  "Wizardry_1|output/Wizardry_Proving_Grounds_of_Mad_Overlord/nsf/Wizardry - Proving Grounds of Mad Overlord (1987-12-22)(Game Studio)(ASCII).nsf"
  "Wizardry_2|output/Wizardry_II_Legacy_of_Llylgamyn/nsf/Wizardry II - Legacy of Llylgamyn (1989-02-21)(Game Studio)(ASCII).nsf"
  "Wizardry_3|output/Wizardry_III_Knight_of_Diamonds/nsf/Wizardry III - Knight of Diamonds (1990-03-09)(Game Studio)(ASCII).nsf"
  "Hydlide|output/Hydlide/nsf/Hydlide [Hydlide Special] (1986-03-18)(T&E)(Toemiland).nsf"
  "Hydlide_3|output/Hydlide_3_Yami_kara_no_Houmonsha/nsf/Hydlide 3 - Yami Kara no Houmonsha (1989-02-17)(T&E)(Namco).nsf"
  "Bards_Tale|output/Bards_Tale_Tales_of_the_Unknown/nsf/Bard's Tale - Tales of the Unknown (1990-12-21)(Interplay)(Atelier Double)(Pony Canyon).nsf"
  "Bards_Tale_2|output/Bards_Tale_2_The_Destiny_Knight/nsf/Bard's Tale 2 - The Destiny Knight (1992-01-25)(Interplay)(Atelier Double)(Pony Canyon).nsf"
  "Ghost_Lion|output/Ghost_Lion/nsf/Ghost Lion [White Lion Densetsu - Pyramid no Kanata ni] (1989-07-14)(Kemco).nsf"
  "Dragon_Warrior_III|output/Dragon_Warrior_III/nsf/Dragon Warrior III [Dragon Quest III - Soshite Densetsu he...] (1988-02-10)(Chunsoft)(Enix).nsf"
  "Dragon_Warrior_IV|output/Dragon_Warrior_IV/nsf/Dragon Warrior IV [Dragon Quest IV - Michibikareshi Mono-tachi] (1990-02-11)(Chunsoft)(Enix).nsf"
  "AD_and_D_Dragons_of_Flame|output/ADandD_Dragons_of_Flame/nsf/AD&D Dragons of Flame (1992-02-21)(U.S. Gold)(Atelier Double)(Pony Canyon).nsf"
  "AD_and_D_DragonStrike|output/ADandD_DragonStrike/nsf/AD&D DragonStrike (1992-07)(Westwood)(FCI).nsf"
  "Deep_Dungeon_II|output/Deep_Dungeon_II_Yuushi_no_Monshou_FDS/nsf/Deep Dungeon II - Yuushi no Monshou (FDS)(1987-05-30)(HummingBird)(DOG).nsf"
  "Deep_Dungeon_IV|output/Deep_Dungeon_IV_Kuro_no_Youjutsushi/nsf/Deep Dungeon IV - Kuro no Youjutsushi (1990-04-06)(HummingBird)(Asmik).nsf"
  "Magic_Candle|output/Magic_Candle_The/nsf/Magic Candle, The (1992-03-06)(Japan Soft Technology)(Sammy).nsf"
  "Nobunagas_Ambition|output/Nobunagas_Ambition/nsf/Nobunaga's Ambition [Nobunaga's Ambition - Zenkokuban] (1988-03-18)(Koei).nsf"
  "Nobunagas_Ambition_II|output/Nobunagas_Ambition_II/nsf/Nobunaga's Ambition II [Nobunaga's Ambition - Sengoku Gunyuuden] (1990-02-03)(Koei).nsf"
  "Romance_of_the_Three_Kingdoms_II|output/Romance_of_the_Three_Kingdoms_II/nsf/Romance of the Three Kingdoms II [Sangokushi II] (1990-11-02)(-)(Koei).nsf"
  "Dragon_Quest_VIII|output/Dragon_Quest_VIII_19xx_Unknown/nsf/Dragon Quest VIII (19xx)(Unknown).nsf"
  "Dungeon_Magic|output/Dungeon_Magic_Sword_of_the_Elements/nsf/Dungeon Magic - Sword of the Elements (1989-11-10)(Natsume).nsf"
)

for entry in "${games[@]}"; do
  slug="${entry%%|*}"
  nsf="${entry##*|}"
  echo ""
  echo "=== $slug ==="
  if [ ! -f "$nsf" ]; then
    echo "  MISSING: $nsf"
    continue
  fi
  python scripts/batch_stems_project.py "$nsf" \
      --out-dir "outputv6/$slug/" --seconds 60 2>&1 | tail -3
done

echo ""
echo "=== DONE ==="
