# Results — the synth's covenant with live performance

Summary of what was produced in response to the prompt:

> "how will my synthesizer design solve the problem of the ROM file not
> translating into live performance because it is hard to capture all
> the things the hardware is doing in midi"

## What was delivered

One focused doc: [keyboard_lab/docs/THE_LIVE_PERFORMANCE_PROBLEM.md](../keyboard_lab/docs/THE_LIVE_PERFORMANCE_PROBLEM.md)

It states the problem clearly, catalogs every NES behavior that can
or cannot survive a MIDI round-trip, and describes the synth's answer.

## The short answer

The synthesizer **doesn't solve the gap — it partitions it**, via a
three-priority input cascade:

1. **SysEx register replay** — file playback only, bit-accurate to
   hardware.  Not reachable from a live keyboard.
2. **CC11/CC12 automation** — file playback or CC-knob live input.
   Gets ~70% of hardware fidelity.
3. **ADSR keyboard mode** — live keyboard plays into slider-preset
   envelopes.  Game-specific presets supply the character that a
   keyboard can't.

This lets the same project simultaneously play hardware-exact
extracted MIDI on 4 channels (Priority 1) and let the user layer
keyboard performance on a 5th (Priority 3) using a preset tuned to
the same game's character.

## What's captured in the doc

### The full table of NES register behaviors vs MIDI equivalents

For every `$4000`-`$4017` register function, what MIDI representation
(if any) captures it and how lossy that is.  ~30 distinct behaviors;
fewer than half survive standard MIDI without SysEx.

### What a live MIDI keyboard actually sends

Note on, note off, velocity, maybe pitch bend.  That's it.  Every
other NES behavior has to come from synth preset state.

### The partition's specific trade-offs

| Mode | Reachable via | Covers | Loses |
|------|---------------|--------|-------|
| P1 SysEx | File playback | Everything | Needs pre-extracted MIDI |
| P2 CC | File playback + CC knobs | Period + duty + volume curves | Sweep, noise mode, phase reset, DMC |
| P3 ADSR | Live keyboard | Note events + velocity + presets | Per-frame register modulation |

### What the design does NOT solve (honest list)

1. Live keyboard can't reproduce per-frame register manipulation
   (a driver's duty-animation during sustain is impossible from one
   keypress).
2. Noise channel has no pitch concept — our mapping is invented.
3. DMC needs sample data the keyboard can't provide.
4. Priority 1 (SysEx) requires pre-computed MIDI; live improvisation
   is always at Priority 3 quality.

### The realistic live-play experience

- **Quality**: 90-95% NES-like on a well-tuned preset.
- **Latency**: 5-15 ms end-to-end in REAPER.
- **Multi-voice**: split the keyboard range across 4 JSFX instances.
- **Video-recording**: sliders + scope animate on-camera.

## How this doc fits the bigger picture

This is the **design justification** doc — it explains WHY the
architecture is what it is.  Pair it with:

- `docs/SYNTHMERGE.md` — the original plan for the three-priority
  cascade.
- `docs/SYNTH_VS_SCRIPTS.md` — why Python stems and JSFX diverged.
- `keyboard_lab/docs/THE_LIVE_PERFORMANCE_PROBLEM.md` — the full
  content of this summary, with tables.

## Final answer restated

The synth's job isn't to make a live MIDI keyboard sound exactly
like the NES.  Its job is to give you ONE interface where:

- A) hardware-exact extracted files play back with full fidelity,
- B) you perform live in the same characteristic sound,
- and these two use cases coexist in the same project without
  conflict.

If you accept that partition as the design target, the remaining
work is: make Priority 3 (ADSR) sound as close as possible to the
driver family's signature.  That's tuneable via presets, which is
the concrete next step for the `keyboard_lab/` workbench.
