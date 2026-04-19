#!/usr/bin/env bash
# Render extra user-requested games into outputv6/ sequentially.
# Kicked off to run after the main rebuild_v6 finishes.
set -e
cd "$(dirname "$0")/.."

for spec in \
    "Faxanadu|output/Faxanadu/nsf/Faxanadu (1987-11-16)(Falcom, Hudson)(Hudson).nsf" \
    "Life_Force|output/Life_Force/nsf/Life Force [Salamander] (1987-09-25)(Konami).nsf" \
    "Willow|output/Willow/nsf/Willow (1989-07-18)(Capcom).nsf" \
; do
    game="${spec%%|*}"
    nsf="${spec#*|}"
    echo "=== $game ==="
    python scripts/batch_stems_project.py "$nsf" \
        --out-dir "outputv6/$game/" --seconds 60 \
        > "outputv6/_log_${game}.log" 2>&1
    n=$(ls "outputv6/$game/reaper/"*.rpp 2>/dev/null | wc -l)
    echo "  -> $n RPPs"
done
echo "All extra renders done."
