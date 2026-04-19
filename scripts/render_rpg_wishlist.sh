#!/usr/bin/env bash
# Render the RPG/adventure wishlist into outputv6.
# Kicked off 2026-04-18 evening after user asked for "more games like Ultima".
set -u
cd "$(dirname "$0")/.."

games=(
  "Ultima_Exodus|output/Ultima_Exodus/nsf/Ultima - Exodus [Ultima - Kyoufu no Exodus] (1987-10-09)(Origin)(Pony).nsf"
  "Ultima_Quest_of_the_Avatar|output/Ultima_Quest_of_the_Avatar/nsf/Ultima - Quest of the Avatar [Ultima - Seija he no Michi] (1989-09-20)(Orgin)(Infinity)(Pony Canyon).nsf"
  "Deep_Dungeon_III|output/Deep_Dungeon_III_Yuushi_he_no_Tabi/nsf/Deep Dungeon III - Yuushi he no Tabi (1988-05-13)(HummingBird)(Square).nsf"
  "Dragon_Scroll|output/Dragon_Scroll_Yomigaerishi_Maryuu/nsf/Dragon Scroll - Yomigaerishi Maryuu (1987-12-04)(Konami).nsf"
  "Destiny_of_an_Emperor|output/Destiny_of_an_Emperor/nsf/Destiny of an Emperor [Tenchi wo Kurau] (1989-05-19)(Capcom).nsf"
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
