#!/usr/bin/env bash
# Action/platformer/shmup classics — Konami, Capcom, Natsume, Tecmo,
# Sunsoft deep cuts + some expansion-audio titles (VRC7 Lagrange Point,
# Esper Dream FDS, Hebereke SFX).  Chains after RPG part 3 finishes.
set -u
cd "$(dirname "$0")/.."

while ! grep -q "=== DONE ===" outputv6/_log_rpg_wishlist3.log 2>/dev/null; do
  sleep 60
done

games=(
  # Konami greats
  "Castlevania_2|output/Castlevania_2_Simons_Quest/nsf/Castlevania 2 - Simon's Quest [Dracula 2 - Noroi no Fuuin] (1988-12)(Konami).nsf"
  "TMNT|output/Teenage_Mutant_Ninja_Turtles/nsf/Teenage Mutant Ninja Turtles [Gekikame Ninja Den] (1989-05-12)(Konami).nsf"
  "TMNT_2_Arcade|output/Teenage_Mutant_Ninja_Turtles_II_The_Arcade_Game/nsf/Teenage Mutant Ninja Turtles II - The Arcade Game [Teenage Mutant Ninja Turtles] (1990-12-07)(Konami).nsf"
  "TMNT_3_Manhattan|output/Teenage_Mutant_Ninja_Turtles_III_The_Manhattan_Project/nsf/Teenage Mutant Ninja Turtles III - The Manhattan Project [Teenage Mutant Ninja Turtles II - The Manhattan Project] (1991-12-13)(Konami).nsf"
  "Metal_Gear|output/Metal_Gear/nsf/Metal Gear (1987-12-22)(Konami).nsf"
  "Crisis_Force|output/Crisis_Force/nsf/Crisis Force (1991-08-27)(Konami).nsf"
  "Contra_Force|output/Contra_Force/nsf/Contra Force (1992-09)(Konami).nsf"
  "Bucky_O_Hare|output/Bucky_OHare/nsf/Bucky O'Hare (1992-01-31)(Konami).nsf"
  # Capcom greats
  "Mega_Man_5|output/Mega_Man_5/nsf/Mega Man 5 [RockMan 5 - Blues no Wana!] (1992-12-04)(Capcom).nsf"
  "Mega_Man_6|output/Mega_Man_6/nsf/Mega Man 6 [RockMan 6 - Shijou Saidai no Tatakai!!] (1993-11-05)(Capcom).nsf"
  "Chip_n_Dale|output/Chip_n_Dale_Rescue_Rangers/nsf/Chip 'n Dale Rescue Rangers [Chip to Dale no Daisakusen] (1990-06-08)(Capcom).nsf"
  "Chip_n_Dale_2|output/Chip_n_Dale_Rescue_Rangers_2/nsf/Chip 'n Dale Rescue Rangers 2 [Chip to Dale no Daisakusen 2] (1993-12-10)(Make)(Capcom).nsf"
  "Sweet_Home|output/Sweet_Home/nsf/Sweet Home (1989-12-15)(-)(Capcom).nsf"
  # Tecmo
  "Ninja_Gaiden_2|output/Ninja_Gaiden_II_The_Dark_Sword_of_Chaos/nsf/Ninja Gaiden II - The Dark Sword of Chaos [Ninja Ryukenden II - Ankoku no Jashinken] [Shadow Warriors II - Ninja Gaiden II] (1990-04-06)(Tecmo).nsf"
  "Ninja_Gaiden_3|output/Ninja_Gaiden_III_The_Ancient_Ship_of_Doom/nsf/Ninja Gaiden III - The Ancient Ship of Doom [Ninja Ryukenden III - Yomi no Hakobune] (1991-06-21)(Tecmo).nsf"
  "Rygar|output/Rygar/nsf/Rygar [Argos no Senshi - Hachamecha Daishingeki] (1987-04-17)(Tecmo).nsf"
  # Natsume
  "Power_Blade|output/Power_Blade/nsf/Power Blade [Power Blazer] (1990-04-20)(Natsume)(Taito).nsf"
  "Shadow_of_the_Ninja|output/Shadow_of_the_Ninja/nsf/Shadow of the Ninja [Kage] [Blue Shadow] (1990-08-10)(Natsume).nsf"
  "Shatterhand|output/Shatterhand/nsf/Shatterhand [Tokkyuu Shirei - Solbrain] (1991-10-26)(Natsume)(Angel).nsf"
  # Taito / others
  "Little_Samson|output/Little_Samson/nsf/Little Samson [Seirei Densetsu Lickle] (1992-06-26)(Taito).nsf"
  "Zombie_Nation|output/Zombie_Nation/nsf/Zombie Nation [Abarenbou Tengu] (1990-12-14)(KAZe)(Meldac).nsf"
  # HAL — Lolo puzzle series
  "Lolo_1|output/Adventures_of_Lolo/nsf/Adventures of Lolo [Egger Land - Meikyuu no Fukkatsu] (1988-08-09)(HAL Laboratory).nsf"
  "Lolo_2|output/Adventures_of_Lolo_2/nsf/Adventures of Lolo 2 [Adventures of Lolo] (1990-01-06)(HAL Laboratory).nsf"
  "Lolo_3|output/Adventures_of_Lolo_3/nsf/Adventures of Lolo 3 [Adventures of Lolo 2] (1990-12-26)(HAL Laboratory).nsf"
  # Shmups
  "Gun_Nac|output/Gun_Nac/nsf/Gun Nac (1990-10-05)(Compile)(Tonkin House).nsf"
  "Over_Horizon|output/Over_Horizon_NTSC_SFX/nsf/Over Horizon (NTSC) (SFX).nsf"
  "Recca|output/Summer_Carnival_92_Recca/nsf/Summer Carnival '92 - Recca (1992-07-17)(KID)(Naxat Soft).nsf"
  # Sunsoft expansion cut
  "Hebereke|output/Hebereke_SFX/nsf/Hebereke (SFX).nsf"
  # Konami expansion-audio (VRC7, FDS) — may render only standard channels
  "Lagrange_Point_VRC7|output/Lagrange_Point/nsf/Lagrange Point (VRC7)(1991-04-26)(-)(Konami).nsf"
  "Esper_Dream_FDS|output/Esper_Dream/nsf/Esper Dream (FDS)(1987-02-20)(Konami).nsf"
  "Esper_Dream_2|output/Esper_Dream_2_Aratanaru_Tatakai/nsf/Esper Dream 2 - Aratanaru Tatakai (1992-06-26)(Konami).nsf"
  # Nintendo
  "SMB_2_JP|output/Super_Mario_Bros_2_JP/nsf/Super Mario Bros. 2 JP [Super Mario USA] (1988-10)(Nintendo EAD)(Nintendo).nsf"
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
