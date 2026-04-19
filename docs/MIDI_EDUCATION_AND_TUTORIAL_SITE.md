# Teaching MIDI software — educational analysis + tutorial website plan

Problem statement: MIDI software has a notoriously steep learning
curve because it combines five independent conceptual stacks (music
theory, signal routing, DAW operation, sound synthesis, plugin
architecture) plus the historical baggage of a 40-year-old protocol
designed for hardware that barely exists anymore.  A tutorial site
that actually teaches MIDI needs to be unusually careful about what
order it reveals complexity.

This doc is an educational analysis of why MIDI is hard, followed by
a concrete plan for a tutorial website that addresses those
difficulties.

## Part 1 — The educational problem

### Why MIDI is confusing for newcomers

#### 1. Five stacks in one interface

Opening REAPER (or any modern DAW) with a MIDI keyboard plugged in
confronts the learner with all of these simultaneously:

1. **Music theory** — notes, keys, tempo, time signatures.
2. **Signal routing** — which device sends where, which plugin
   processes what.
3. **DAW operation** — tracks, items, regions, automation, render.
4. **Sound synthesis** — what a note "sounds like" is separate
   from the note event.
5. **Plugin architecture** — VST vs JSFX vs AU, synth vs effect,
   MIDI FX vs audio FX.

Most tutorials assume the learner already has 2-3 of these.  The
average beginner has 0-1.  The gap is vast.

#### 2. MIDI's history is a trap

MIDI was designed in 1983 for connecting hardware synthesizers.
Many of its quirks (128 note limit, 16 channels, General MIDI
program numbers, 7-bit CC resolution) are artifacts of that era
that bleed into modern software.  Teaching MIDI means teaching its
history, not just its mechanics, because the mechanics don't make
sense otherwise.

#### 3. Software hides its layers

In REAPER, clicking "record" on a track with a MIDI keyboard
already plugged in will Just Work for some users and silently fail
for others.  The difference depends on:
- Which audio device is set as input (if any).
- Which MIDI device is enabled in preferences.
- Which track is "record armed" with MIDI input selected.
- Whether a synth plugin is loaded on the track.
- Whether that plugin accepts MIDI input.

Each of these is a layer that can silently fail, and error messages
rarely name which one.  A good tutorial has to walk the learner
through the full signal chain BEFORE they try to make sound, so
they have a mental model of what's happening.

#### 4. The terminology is overloaded

"Track" means a REAPER timeline lane.  Also means a MIDI track
inside a `.mid` file (different thing).  Also means an audio file
track (different thing).  Also used loosely as "song."

"Channel" means a MIDI channel (1-16 in a MIDI stream).  Also a
REAPER audio channel (left/right).  Also "a part" in colloquial
music-speak.

"Instrument" means a VSTi.  Also means an orchestral voice.  Also
means a MIDI instrument program number.

Words carry multiple meanings that only context disambiguates.
Beginners don't have the context.

#### 5. The abstraction stack isn't bottom-up

Most software is learnable bottom-up: files → functions → tools.
MIDI isn't.  You can't understand "MIDI file" without first
understanding "MIDI event," and you can't understand "MIDI event"
without understanding "what a MIDI sequencer does," which requires
understanding why anyone wanted sequencers in the first place.

Teaching it bottom-up = lose the learner's attention at layer 2.
Teaching top-down = they hit "MIDI event = a byte pattern" too
abstract to ground.  The right order is **spiral**: introduce the
whole landscape at a shallow level, then deepen.

### What good MIDI education looks like

Synthesizing from pedagogy literature + our own use cases:

- **Goal-driven from the first minute.**  "I want to record myself
  playing a scale" beats "Here is a MIDI event."  The learner has
  a task; every concept is motivated by that task.
- **Concrete → abstract progression.**  Start with the physical
  keyboard, end with the byte-level protocol.  Every abstraction
  introduced after the learner has first seen its concrete
  behavior.
- **Spiral curriculum.**  Cover the full landscape at a shallow
  level first (a 10-minute overview of DAW + MIDI + synth), then
  each deepening pass.  Each pass can stand alone.
- **Error-model explicit.**  When something doesn't work,
  immediately say which layer failed ("no sound" has 6 possible
  causes; name them).  Don't make the learner debug silently.
- **Hands-on before explanation.**  Make a sound first.  THEN
  explain why it sounded that way.  Not the other way around.
- **Tool-specific examples + tool-agnostic principles.**  Every
  principle illustrated in 1-2 tools, but the principle itself
  abstracted so it transfers.

## Part 2 — The tutorial website plan

### Site goals

1. Take a complete newcomer from "what is a MIDI keyboard" to
   "I can record and produce music in REAPER" in 3-5 hours of
   content.
2. Give an intermediate learner a reference for specific problems
   ("how do I route a MIDI track to a VSTi").
3. Give an advanced learner a detailed dive into NES-specific
   MIDI workflows (this is our unique contribution).

### Information architecture

Three top-level paths through the site, matching the three user
types above:

```
/start/         - Complete beginner path (1 hour total)
/reference/     - Topic-indexed reference (any depth)
/nes/           - Advanced NES-specific workflows
```

Plus `/glossary/`, `/troubleshoot/`, `/about/` as supporting.

### Site tree

```
/
├── start/                     Beginner path (linear, ~1 hour)
│   ├── 01-what-is-midi.md     "It's a protocol for 'play this note now'"
│   ├── 02-your-first-sound.md DAW + virtual keyboard + built-in synth
│   ├── 03-midi-keyboard.md    Plugging in hardware; device detection
│   ├── 04-recording.md        Arm track; press record; stop; play back
│   ├── 05-editing-notes.md    Piano roll basics
│   ├── 06-multiple-tracks.md  Layering instruments
│   └── 07-rendering.md        Export to audio file
├── reference/                 Topic-indexed
│   ├── midi-events/           Event types: note-on, CC, pitch-bend, SysEx
│   ├── midi-channels/         Channel routing rules
│   ├── midi-files/            SMF (.mid) format
│   ├── plugins/               VST vs VSTi vs MIDI FX
│   ├── routing/               Track I/O, sends, buses
│   ├── automation/            CC automation envelopes
│   └── controllers/           Physical MIDI controllers
├── nes/                       NES-specific advanced paths
│   ├── 01-nes-overview.md     What the NES sound chip does
│   ├── 02-nsf-to-midi.md      Our extraction pipeline explained
│   ├── 03-cc11-cc12.md        How we encode NES envelopes as CC
│   ├── 04-sysex-replay.md     Our SysEx format for hardware-exact replay
│   ├── 05-the-jsfx.md         Using ReapNES_APU2_v2.jsfx
│   ├── 06-live-keyboard.md    Playing NES sounds live (the core product)
│   ├── 07-driver-families.md  Per-family presets and character
│   └── 08-your-own-remix.md   Take an extracted MIDI, remix it
├── troubleshoot/              "My X isn't working" paths
│   ├── no-sound.md            The 6-layer signal-chain debug
│   ├── wrong-instrument.md
│   ├── latency.md
│   └── crashes.md
├── glossary/
│   └── index.md               Every term with all its overloaded meanings
└── about/
    └── index.md               What this site is, who made it
```

### Format per page

Each tutorial page follows the same template:

1. **Goal** — a single-sentence task the learner is about to do.
2. **Prerequisites** — which earlier page(s) this builds on.  If
   none, says so.
3. **Landscape** — a ~3-sentence orientation of where this sits.
4. **Do it** — literal step-by-step with screenshots.
5. **Why that works** — mini-explanation of the concept behind it.
6. **What to try next** — 1-2 explorations or link to next page.
7. **If it broke** — 2-3 most common failure modes + fixes.

### Tech stack recommendation

- **Static site generator**: Eleventy (11ty) or Astro.  Both support
  Markdown + MDX + components.  Astro wins for interactive demos
  (embedded MIDI keyboard).
- **Hosting**: GitHub Pages (free, already set up for this project).
- **Interactive elements**:
  - Web MIDI API for browser MIDI input (works in Chrome/Edge).
  - Tone.js for in-browser synthesis demos.
  - Embedded audio players for reference listening.
  - iframes of CodePen for quick experiments.
- **Accessibility**: screen-reader-friendly math notation; audio
  waveforms have text descriptions; keyboard-navigable piano-roll
  demos.

### Our NES-specific advantages

The `/nes/` section is unique to us.  It teaches things not
documented elsewhere:

- Why NES has 5 channels and how each is different.
- Why MIDI CC11 isn't quite "NES volume."
- How SysEx replay gives bit-exact hardware emulation.
- Why stems and live-play diverge (links to `SYNTH_VS_SCRIPTS.md`).
- How to pick a driver-family preset for a given game.

This is where we differentiate from every other MIDI tutorial on
the internet.  The `/start/` and `/reference/` paths are generic
DAW-MIDI education that anyone could write; the `/nes/` path is
ours alone.

### Suggested writing schedule

- **Week 1**: `/start/` beginner path, 7 pages.  ~2 days writing.
- **Week 2**: `/reference/` core entries (midi-events, channels,
  plugins, routing).  ~3 days.
- **Week 3**: `/nes/` advanced path, 8 pages.  We already have most
  content in this repo's docs — distill and re-pitch.  ~3 days.
- **Week 4**: Troubleshooting + glossary + polish.  ~2 days.

Total: ~10 working days for a serviceable v1.

### Differentiation strategy

MIDI tutorials on the web fall into two buckets:

1. **Producer-focused**: teach DAWs as tools for making dance music,
   hip-hop, etc.  Examples: Sonic Academy, Ask.Audio.  Focus on
   aesthetics and workflow.
2. **Academic**: teach MIDI as a protocol for music-tech coursework.
   Examples: the official MIDI Association site, university CS
   courses.  Rigorous but dry.

**Our niche**: retro gaming / chiptune.  Neither producer-aesthetic
nor academic-rigor.  We teach MIDI specifically through the lens of
reproducing classic game music.  Every abstract concept ("what's
CC12?") has a concrete NES-specific example ("it's how we encode
pulse duty — Castlevania's distinctive timbre").

### Launch sequencing

- Phase 1 (week 1-2): `/start/` + 4 pages of `/reference/`.  Launch
  to a small audience (Reddit r/chiptune, r/REAPER) for feedback.
- Phase 2 (week 3-4): `/nes/` path + troubleshoot.  Launch to
  broader chiptune community.
- Phase 3 (month 2): fill out `/reference/` fully; add more NES
  deep-dives.  Promote on Hacker News, chip music forums.

### Measurement

Success metrics:

- Beginners complete `/start/` in <90 min (survey).
- Avg bounce rate <50% on first-page tutorials.
- 5+ community-submitted "my first NES remix" projects within 3
  months.
- Cross-references from major chiptune sites within 6 months.

### Monetization (if desired)

- Free base site.
- Premium tier: interactive exercises, downloadable project
  templates, personal support (~$10/month).
- Sponsored content from NES-music communities / REAPER itself.
- Book / PDF compilation of the whole site for offline reference.

## Part 3 — Integration with the main project

This tutorial site is the teaching surface of the project.  It
turns private docs into public education:

- `docs/UNDERSTANDING_THE_CHIP.md` → `/nes/01-nes-overview.md`.
- `docs/NAMING_POLICY.md` → `/nes/02-nsf-to-midi.md` (naming is an
  advanced topic; mention in passing at this level).
- `docs/SYNTH_VS_SCRIPTS.md` → `/nes/06-live-keyboard.md`.
- `docs/DRIVER_FAMILIES_AND_GAMES.md` → `/nes/07-driver-families.md`.

The translation is mostly tone.  Our docs are for us; the tutorial
site is for a newcomer.  The material is 80% the same; the framing
is different.

### Cross-link both ways

Each advanced tutorial page links back to its source doc for
readers who want more depth.  Each source doc links forward to
the tutorial for readers who want to learn from scratch.

This creates a funnel: curious chiptune listeners discover the
site, work through the beginner path, arrive at NES-specific
content, get hooked, dive into the project docs.  Some will
contribute (patches, parsers, tutorials of their own).

## The pitch in one sentence

A tutorial site that teaches MIDI from the ground up, using our
NES-music project's extracted data and plugins as worked examples,
aimed at anyone who ever wanted to understand "how that Castlevania
song is actually made" and leaves them able to play the same kind
of music themselves.
