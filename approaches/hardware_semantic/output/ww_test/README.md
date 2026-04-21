# W&W Phase-1 CBG Test Output

First 4 songs in M3U play order, processed through the
hardware-semantic stack (CBG middle layer) instead of the legacy
boundary-map MIDI path.

Render cap: 40 s per song (M3U durations clipped).

## What to listen for

Triangle bass articulation in Title and Forest of Elrond.
The audio stems are rendered from the same HW simulation the
stems pipeline already ear-confirmed; the CBG-derived MIDI now
marks note boundaries using the same liveness logic instead of
the legacy pitch-continuity + W&W-specific note_boundary_map.

In REAPER, the audio track plays by default; the MIDI/JSFX track
is muted.  Unmute the MIDI track to hear the current JSFX output
driven by CBG-derived boundaries; compare to the audio stem (ground
truth).  For legacy comparison, open `midi/<slug>_legacy.mid`.

## Per-song summary

### 01_title -- Wizards & Warriors Title
- frames captured: 2256
- CBG notes:    416
- legacy notes: 422  (delta: -6)
- liveness:
    - **pulse1**: 1212 audible / 532 silent / 0 gated; 45 transitions, 91 retriggers
    - **pulse2**: 2168 audible / 88 silent / 0 gated; 2 transitions, 269 retriggers
    - **triangle**: 1644 audible / 100 silent / 0 gated; 3 transitions, 58 retriggers
    - **noise**: 0 audible / 2256 silent / 0 gated; 1 transitions, 0 retriggers

### 02_map -- Map
- frames captured: 324
- CBG notes:    16
- legacy notes: 19  (delta: -3)
- liveness:
    - **pulse1**: 0 audible / 0 silent / 0 gated; 1 transitions, 1 retriggers
    - **pulse2**: 120 audible / 204 silent / 0 gated; 2 transitions, 13 retriggers
    - **triangle**: 108 audible / 216 silent / 0 gated; 2 transitions, 3 retriggers
    - **noise**: 0 audible / 324 silent / 0 gated; 1 transitions, 0 retriggers

### 03_forest_of_elrond -- Forest of Elrond
- frames captured: 2400
- CBG notes:    382
- legacy notes: 529  (delta: -147)
- liveness:
    - **pulse1**: 1572 audible / 828 silent / 0 gated; 124 transitions, 100 retriggers
    - **pulse2**: 1572 audible / 828 silent / 0 gated; 124 transitions, 100 retriggers
    - **triangle**: 1992 audible / 408 silent / 0 gated; 60 transitions, 156 retriggers
    - **noise**: 900 audible / 1500 silent / 0 gated; 51 transitions, 0 retriggers

### 04_entering_a_door -- Entering a Door
- frames captured: 144
- CBG notes:    18
- legacy notes: 19  (delta: -1)
- liveness:
    - **pulse1**: 45 audible / 99 silent / 0 gated; 2 transitions, 9 retriggers
    - **pulse2**: 45 audible / 99 silent / 0 gated; 2 transitions, 9 retriggers
    - **triangle**: 0 audible / 0 silent / 0 gated; 1 transitions, 1 retriggers
    - **noise**: 0 audible / 144 silent / 0 gated; 1 transitions, 0 retriggers
