#!/usr/bin/env bash
# Nintendo 1st-party classics not in the main rebuild queue.
# Chained to run after the RPG part-2 batch finishes so we don't
# overload with 4 parallel render jobs.
# Also includes Kid_Icarus_FDS + Punch_Out_VS which have distinct NSFs
# from the rebuild's Kid_Icarus / Punch_Out folders.
# Finally renders Final_Fantasy_II and Final_Fantasy_III which the main
# rebuild skipped due to a slug-mismatch (looked for FF_2 not FF_II).
set -u
cd "$(dirname "$0")/.."

while ! grep -q "=== DONE ===" outputv6/_log_rpg_wishlist2.log 2>/dev/null; do
  sleep 30
done

games=(
  "Final_Fantasy_II|output/Final_Fantasy_II/nsf/Final Fantasy II (1988-12-17)(Square).nsf"
  "Final_Fantasy_III|output/Final_Fantasy_III/nsf/Final Fantasy III (1990-04-27)(Square).nsf"
  "Kid_Icarus_FDS|output/Kid_Icarus_FDS/nsf/Kid Icarus [Hikari Shinwa - Palutena no Kagami] (FDS)(1986-12-19)(Nintendo R&D1, Tose)(Nintendo).nsf"
  "Punch_Out_VS|output/Punch_Out_VS/nsf/Punch-Out!! (VS)(1984)(Nintendo IRD)(Nintendo).nsf"
  "Ice_Climber|output/Ice_Climber/nsf/Ice Climber (1985-01-30)(Nintendo R&D1)(Nintendo).nsf"
  "Balloon_Fight|output/Balloon_Fight/nsf/Balloon Fight (1985-01-22)(HAL Laboratory)(Nintendo).nsf"
  "Excitebike|output/Excitebike/nsf/Excitebike (1984-11-30)(Nintendo EAD)(Nintendo).nsf"
  "Mario_Bros|output/Mario_Bros/nsf/Mario Bros. (1983-09-09)(Nintendo R&D1)(Nintendo).nsf"
  "Donkey_Kong|output/Donkey_Kong/nsf/Donkey Kong (1983-07-15)(Ikegami Tsushinki)(Nintendo R&D1)(Nintendo).nsf"
  "Donkey_Kong_Jr|output/Donkey_Kong_Jr/nsf/Donkey Kong Jr. (1983-07-15)(Nintendo R&D1)(Nintendo).nsf"
  "Donkey_Kong_3|output/Donkey_Kong_3/nsf/Donkey Kong 3 (1984-07-04)(Nintendo R&D1)(Nintendo).nsf"
  "Dr_Mario|output/Dr_Mario/nsf/Dr. Mario (1990-07-27)(Nintendo R&D1)(Nintendo).nsf"
  "Tetris|output/Tetris/nsf/Tetris (1988-12-22)(Bullet-Proof Software).nsf"
  "Tetris_2|output/Tetris_2/nsf/Tetris 2 [Tetris Flash] (1993-09-21)(Tose)(Nintendo).nsf"
  "Pinball|output/Pinball/nsf/Pinball (1984-02-02)(Nintendo R&D1)(Nintendo).nsf"
  "Clu_Clu_Land|output/Clu_Clu_Land/nsf/Clu Clu Land (1984-11-22)(Nintendo R&D1)(Nintendo).nsf"
  "Wrecking_Crew|output/Wrecking_Crew/nsf/Wrecking Crew (1985-06-18)(Nintendo R&D1)(Nintendo).nsf"
  "Mach_Rider|output/Mach_Rider/nsf/Mach Rider (1985-10-18)(HAL Laboratory)(Nintendo).nsf"
  "Ice_Hockey|output/Ice_Hockey/nsf/Ice Hockey (1988-03)(Nintendo IRD, Pax Softnica)(Nintendo).nsf"
  "Tennis|output/Tennis/nsf/Tennis (1984-01-14)(Nintendo R&D1)(Nintendo).nsf"
  "Baseball|output/Baseball/nsf/Baseball (1983-12-07)(Nintendo R&D1)(Nintendo).nsf"
  "Soccer|output/Soccer/nsf/Soccer (1985-04-09)(Iwasaki Giken)(Nintendo).nsf"
  "Volleyball|output/Volleyball/nsf/Volleyball (1987-03)(Nintendo IRD, Pax Softnica)(Nintendo).nsf"
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
