#!/usr/bin/env bash
# Part 2 of RPG wishlist: the 7 games freshly imported from Zophar.
# Chained to run after part 1 finishes.
set -u
cd "$(dirname "$0")/.."

# Wait for part 1 to finish (its last line is "=== DONE ===")
while ! grep -q "=== DONE ===" outputv6/_log_rpg_wishlist.log 2>/dev/null; do
  sleep 30
done

games=(
  "Legacy_of_the_Wizard|output/Legacy_of_the_Wizard/nsf/Legacy of the Wizard [Dragon Slayer IV - Drasle Family] (1987-07-17)(Falcom)(Namco).nsf"
  "Swords_and_Serpents|output/Swords_and_Serpents/nsf/Swords and Serpents (1990-08)(Interplay)(Acclaim).nsf"
  "Might_and_Magic|output/Might_and_Magic_Secret_of_the_Inner_Sanctum/nsf/Might and Magic - Secret of the Inner Sanctum (1990-07-31)(New World Computer)(G-Amusements)(Gakken).nsf"
  "Magic_of_Scheherazade|output/Magic_of_Scheherazade_The/nsf/Magic of Scheherazade, The [Arabian Dream Scheherazade] (1987-09-03)(Culture Brain).nsf"
  "Bokosuka_Wars|output/Bokosuka_Wars/nsf/Bokosuka Wars (1985-12-14)(ASCII)(Bits Laboratory)(ASCII).nsf"
  "Romance_of_the_Three_Kingdoms|output/Romance_of_the_Three_Kingdoms/nsf/Romance of the Three Kingdoms [Sangokushi] (1988-10-30)(Koei).nsf"
  "Little_Ninja_Brothers|output/Little_Ninja_Brothers/nsf/Little Ninja Brothers [Super Chinese 2 - Dragon Kid] (1989-05-26)(Culture Brain).nsf"
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
