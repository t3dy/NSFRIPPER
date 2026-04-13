# Wizards & Warriors Title Articulation Breakthrough

## Narrow claim

The missing title articulation is not triangle-only. The disputed phrase contains
a synchronized same-pitch re-attack on both `pulse1` and `triangle`, and that
attack is invisible in the latched period state used by plain MIDI/note-only
routes.

## Core proof

- Best MP3/high-band alignment offset: `0` frames (`0.000s`).
- Parser boundaries place fresh events at frames `928`, `960`, `976`, `992`, `1008`.
- NSF write capture shows full same-value rewrites on both channels at frame `961`
  (1-based frame numbering in earlier notes, zero-based `960` here).
- Latched trace state does not show a new period at that frame, so latch-only export
  flattens the attack.

## Phrase evidence

- Frame `896`: pulse1 hidden retrigger=`False`, triangle hidden retrigger=`False`, high-band z=`-1.24`, low-band z=`-0.57`.
- Frame `928`: pulse1 hidden retrigger=`True`, triangle hidden retrigger=`False`, high-band z=`-0.38`, low-band z=`1.33`.
- Frame `960`: pulse1 hidden retrigger=`True`, triangle hidden retrigger=`True`, high-band z=`1.50`, low-band z=`-1.53`.
- Frame `976`: pulse1 hidden retrigger=`False`, triangle hidden retrigger=`False`, high-band z=`-1.13`, low-band z=`1.04`.
- Frame `992`: pulse1 hidden retrigger=`False`, triangle hidden retrigger=`False`, high-band z=`0.62`, low-band z=`0.34`.
- Frame `1008`: pulse1 hidden retrigger=`False`, triangle hidden retrigger=`False`, high-band z=`0.63`, low-band z=`-0.61`.

## Architectural consequence

The missing middle layer is a first-class frame audible-state / articulation layer
that carries at least:

- per-channel retrigger markers
- same-pitch rewrite markers
- composite cross-channel attack markers
- attack-vs-sustain classification for projection into MIDI / plugin playback

A triangle-only patch was never enough because the ROM data itself says the pulse1
attack is part of the same phrase shape.
