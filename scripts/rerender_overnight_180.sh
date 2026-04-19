#!/usr/bin/env bash
# Overnight: after the current render chains finish (rebuild + 4 queued
# render_*.sh scripts), re-render every outputv6 game at --seconds 180
# so that songs whose M3U length > 60s play their full length.
#
# Kicked off 2026-04-18 evening after user reported Metroid Brinstar
# (95.9s M3U) rendering at 60s.  The rebuild_v6.py default was bumped
# to 180 in the same change; this script applies the same setting to
# the non-rebuild game set (wishlist, RPG parts, Nintendo classics,
# action classics).
set -u
cd "$(dirname "$0")/.."

echo "=== waiting for in-flight chains to finish ==="
# Wait for each chain's log to show its DONE marker.  Main rebuild has
# no DONE marker (prints "Done." at end); check for the final game instead.
wait_for_done() {
    local logfile="$1"
    local marker="$2"
    while ! grep -q "$marker" "$logfile" 2>/dev/null; do
        sleep 120
    done
    echo "  done: $logfile"
}

wait_for_done outputv6/_log_wishlist.log            "^=== DONE ===\|^Done\."
wait_for_done outputv6/_log_rpg_wishlist.log        "=== DONE ==="
wait_for_done outputv6/_log_rpg_wishlist2.log       "=== DONE ==="
wait_for_done outputv6/_log_nintendo_classics.log   "=== DONE ==="
wait_for_done outputv6/_log_rpg_wishlist3.log       "=== DONE ==="
wait_for_done outputv6/_log_action_classics.log     "=== DONE ==="
wait_for_done outputv6/_log_fan_favs_5.log          "=== DONE ==="
# Main rebuild: wait for the final line "Done. ..." or for the process to exit
while pgrep -f "rebuild_v6.py" > /dev/null; do
    sleep 120
done
echo "  done: main rebuild"

echo ""
echo "=== rebuild_v6 at --seconds 180 (the 44 outputv5 games) ==="
python -u scripts/rebuild_v6.py --force --numeric-labels \
    > outputv6/_log_rerebuild_180.log 2>&1
echo "  main rebuild done"

# Now re-render every non-outputv5 outputv6 game at 180s.  We look up
# the NSF path from output/<slug>/nsf/ -- if the slug differs between
# outputv6 and output/, fall back to finding any NSF file next to it.
echo ""
echo "=== re-rendering non-rebuild games at 180s ==="

# Games covered by the main rebuild -- these are in outputv5/
rebuild_games=$(ls outputv5/ 2>/dev/null | grep -v "^_")

for d in outputv6/*/; do
    slug=$(basename "$d")
    [[ "$slug" == _* ]] && continue
    # Skip if already covered by the rebuild_v6 run above
    if echo "$rebuild_games" | grep -qxF "$slug"; then
        continue
    fi
    # Find the NSF.  Try output/<slug>/nsf/ first, else glob outputs for
    # an NSF whose basename contains the slug.
    nsf=""
    if [ -d "output/$slug/nsf" ]; then
        nsf=$(ls "output/$slug/nsf/"*.nsf 2>/dev/null | head -1)
    fi
    if [ -z "$nsf" ]; then
        # Try output/ directory search as last resort
        nsf=$(ls output/*"$slug"*/nsf/*.nsf 2>/dev/null | head -1)
    fi
    if [ -z "$nsf" ]; then
        echo "  SKIP $slug -- no NSF found"
        continue
    fi
    echo ""
    echo "=== $slug ==="
    python scripts/batch_stems_project.py "$nsf" \
        --out-dir "outputv6/$slug/" --seconds 180 2>&1 | tail -3
done

echo ""
echo "=== DONE ==="
