#!/usr/bin/env bash
# Render the 7 user-wishlist games into outputv6/ sequentially.
# Runs after the main rebuild_v6 finishes.
set -e
cd "$(dirname "$0")/.."

# Build from what's in output/<slug>/nsf/ so we pick up whatever was
# imported by scripts/import_zophar_nsfs.py
for slug in Bubble_Bobble Double_Dragon Double_Dragon_II_The_Revenge \
            Dragon_Warrior_II Crystalis StarTropics Shadowgate; do
    nsf=$(ls "output/$slug/nsf/"*.nsf 2>/dev/null | head -1)
    if [ -z "$nsf" ]; then
        echo "=== $slug: NO NSF (skipping) ==="
        continue
    fi
    echo "=== $slug ==="
    python scripts/batch_stems_project.py "$nsf" \
        --out-dir "outputv6/$slug/" --seconds 60 \
        > "outputv6/_log_${slug}.log" 2>&1
    n=$(ls "outputv6/$slug/reaper/"*.rpp 2>/dev/null | wc -l)
    echo "  -> $n RPPs"
done
echo "Wishlist renders done."
