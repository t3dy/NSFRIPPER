# Wizards & Warriors Title Audible-State IR Report

## Summary

- This artifact promotes the title breakthrough into a first-class middle layer.
- It stores per-frame articulation state, hidden retriggers, and composite attacks.
- Window: `880-1016`.
- Audio alignment offset: `0` frames.

## Route Comparison

- Note-only misses `3` hidden retrigger events in this window.
- Latch-only misses `3` hidden retrigger events in this window.
- Write-aware can see `3` hidden retrigger events, but still lacks explicit composite classification.
- Composite attack frames in this window: `[960]`.

## Phrase Frames

- Frame `896`: pulse1=`period_attack`, triangle=`period_attack`, composite_attack=`False`, high-z=`-1.24`, low-z=`-0.57`.
- Frame `928`: pulse1=`hidden_retrigger`, triangle=`period_attack`, composite_attack=`False`, high-z=`-0.38`, low-z=`1.33`.
- Frame `960`: pulse1=`hidden_retrigger`, triangle=`hidden_retrigger`, composite_attack=`True`, high-z=`1.50`, low-z=`-1.53`.
- Frame `976`: pulse1=`period_attack`, triangle=`period_attack`, composite_attack=`False`, high-z=`-1.13`, low-z=`1.04`.
- Frame `992`: pulse1=`period_attack`, triangle=`period_attack`, composite_attack=`False`, high-z=`0.62`, low-z=`0.34`.
- Frame `1008`: pulse1=`period_attack`, triangle=`period_attack`, composite_attack=`False`, high-z=`0.63`, low-z=`-0.61`.

## Consequence

The middle layer should preserve at least:

- per-channel parser boundaries
- per-channel write-aware hidden retriggers
- composite cross-channel attack markers
- attack vs sustain classification independent of note pitch change

This is the information plain MIDI and latch-only replay fail to carry on their own.

Strongest current composite-attack evidence frame(s): `960`.