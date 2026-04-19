#!/usr/bin/env bash
# Part 5: Rare/Technos Kunio/Konami deep cuts/arcade ports/FDS+VRC6
# expansion audio/fan favorites.  Chains after action classics.
# Rendered at --seconds 180 (post-Metroid bump).
set -u
cd "$(dirname "$0")/.."

while ! grep -q "=== DONE ===" outputv6/_log_action_classics.log 2>/dev/null; do
  sleep 60
done

games=(
  # Rare
  "Mike_Tysons_Punch_Out|output/Mike_Tysons_Punch_Out/nsf/Mike Tyson's Punch-Out!! (1987-09-14)(Nintendo R&D3)(Nintendo).nsf"
  "Solar_Jetman|output/Solar_Jetman_Hunt_for_the_Golden_Warship/nsf/Solar Jetman - Hunt for the Golden Warship (1990-09)(Rare)(Tradewest).nsf"
  "Snake_Rattle_n_Roll|output/Snake_Rattlen_Roll/nsf/Snake Rattle 'n' Roll (1990-07)(Rare)(Nintendo).nsf"
  "RC_Pro_Am|output/R_C_Pro_Am/nsf/R.C. Pro-Am (1988-03)(Rare)(Nintendo).nsf"
  "RC_Pro_Am_II|output/R_C_Pro_Am_II/nsf/R.C. Pro-Am II (1992-12)(Rare)(Tradewest).nsf"
  "Wizards_and_Warriors_3|output/Wizards_and_Warriors_III_Kuros_Visions_of_Power/nsf/Wizards & Warriors III -  Kuros - Visions of Power (1992-03)(Zippo)(Acclaim).nsf"
  # Expansion audio: VRC6, FDS
  "Castlevania_3_JP_VRC6|output/Castlevania_3_Draculas_Curse_JP/nsf/Castlevania 3 - Dracula's Curse JP [Akumajou Densetsu] (VRC6)(1989-12-22)(Konami).nsf"
  "Zelda_FDS_JP|output/Zelda_no_Densetsu_The_Hyrule_Fantasy_FDS/nsf/Zelda no Densetsu - The Hyrule Fantasy (FDS)(1986-02-21)(Nintendo EAD)(Nintendo).nsf"
  "Metroid_FDS_JP|output/Metroid/nsf/Metroid (1986-08)(Nintendo R&D1)(Nintendo).nsf"
  "Akumajou_Special_Boku_Dracula|output/Akumajou_Special_Boku_Dracula_kun/nsf/Akumajou Special - Boku Dracula-kun (1990-10-19)(Konami).nsf"
  "Madara|output/Mouryou_Senki_Madara/nsf/Mouryou Senki Madara (VRC6)(1990-03-30)(Wolfteam)(Konami).nsf"
  # Konami deep cuts
  "Blades_of_Steel|output/Blades_of_Steel/nsf/Blades of Steel (1988-12)(Konami).nsf"
  "Track_and_Field|output/Track_and_Field/nsf/Track & Field [Hyper Olympic] (1987-06)(Konami).nsf"
  "Goonies_1|output/Goonies_The/nsf/Goonies, The (FDS)(1986-02-21)(Konami).nsf"
  "Goonies_2|output/Goonies_II_The/nsf/Goonies II, The [Goonies 2 - Furatty Saigo no Chousen] (1987-03-18)(Konami).nsf"
  "Jackal|output/Jackal/nsf/Jackal [Tokushu Butai Jackal] (1988-09-02)(Konami).nsf"
  "Rolling_Thunder|output/Rolling_Thunder/nsf/Rolling Thunder (1989-12)(Tengen).nsf"
  # Tecmo + Natsume obscure
  "Ninja_Crusaders|output/Ninja_Crusaders/nsf/Ninja Crusaders [Ninja Crusaders - Ryuuga] (1990-11-30)(Sachen)(American Sammy).nsf"
  # Action/adventure fan favs
  "Guardian_Legend|output/Guardian_Legend_The/nsf/Guardian Legend, The [Guardic Gaiden] (1988-02-05)(Compile)(Irem).nsf"
  "Vice_Project_Doom|output/Vice_Project_Doom/nsf/Vice - Project Doom (1991-02)(Aicom)(American Sammy).nsf"
  "Solstice|output/Solstice_The_Quest_for_the_Staff_of_Demnos/nsf/Solstice - The Quest for the Staff of Demnos (1990-09)(Software Creations)(CSG Imagesoft).nsf"
  "Immortal|output/Immortal_The/nsf/Immortal, The (1990-09)(Electronic Arts).nsf"
  "Time_Lord|output/Time_Lord/nsf/Time Lord (1990-11-09)(Rare)(Milton Bradley).nsf"
  "Gun_Smoke|output/Gun_Smoke/nsf/Gun.Smoke (1988-01)(Capcom).nsf"
  "Kabuki_Quantum_Fighter|output/Kabuki_Quantum_Fighter_NTSC/nsf/Kabuki Quantum Fighter (NTSC) (1991 - HAL Labs) (SFX).nsf"
  "Krion_Conquest|output/Krion_Conquest_The/nsf/Krion Conquest, The [Magical Doropie] (1990-08-10)(Vic Tokai).nsf"
  # Arcade ports
  "Paperboy|output/Paperboy/nsf/Paperboy (1988-12)(Tengen).nsf"
  "Gauntlet_II|output/Gauntlet_II/nsf/Gauntlet II (1990-09)(Tengen).nsf"
  "Galaga|output/Galaga_Demons_of_Death/nsf/Galaga - Demons of Death (1988-09)(Namco).nsf"
  "Pac_Man|output/Pac_Man/nsf/Pac-Man (1988-06)(Namco)(Tengen).nsf"
  "Xevious|output/Xevious/nsf/Xevious (1988-11)(Namco).nsf"
  # Wrestling
  "WWF_Wrestlemania|output/WWF_Wrestlemania/nsf/WWF Wrestlemania (1989-01)(Rare)(Acclaim).nsf"
  "Tag_Team_Wrestling|output/Tag_Team_Wrestling/nsf/Tag Team Wrestling [The Big Pro Wrestling!] (1986-04-02)(Tehkan)(Data East).nsf"
  "Tecmo_World_Wrestling|output/Tecmo_World_Wrestling/nsf/Tecmo World Wrestling [Wrestle Angels - Hakumen Hime Densetsu] (1989-07-14)(Tecmo).nsf"
  # Technos Kunio — closest Zophar has to River City Ransom (same engine)
  "Downtown_Nekketsu|output/Downtown_Nekketsu_Koushinkyoku_Soreyuke_Daiundoukai/nsf/Downtown Nekketsu Koushinkyoku - Soreyuke Daiundoukai (1990-08-10)(Technos).nsf"
  "Crash_n_the_Boys|output/Crash_n_the_Boys_Street_Challenge/nsf/Crash 'n the Boys - Street Challenge (1992-11)(Technos)(American Technos).nsf"
  "Double_Dragon_III|output/Double_Dragon_III_The_Sacred_Stones/nsf/Double Dragon III - The Sacred Stones (1991-07)(Technos)(Acclaim).nsf"
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
      --out-dir "outputv6/$slug/" --seconds 180 2>&1 | tail -3
done

echo ""
echo "=== DONE ==="
