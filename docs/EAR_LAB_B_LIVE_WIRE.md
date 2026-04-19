# Variant B — "Live Wire"

The pure synth.  No pre-rendered audio.  REAPER loads 4-5 MIDI tracks,
each with the `ReapNES_APU2_v2.jsfx` plugin, and the only sound you
hear is what the plugin produces in real time.  This is the product
you asked for: a playable NES-accurate synth that takes MIDI input.

Location: `outputv6_B/<Game>/reaper/<song>.rpp`

## Why it exists

This is the answer to the question "can I plug a MIDI keyboard into
REAPER and have it sound like the NES?"  Variant B is the answer:
yes, open this project, hit a key on your keyboard, the JSFX responds.

Variant B is also the answer to "can I edit MIDI and hear it play
back game-accurately?"  Same yes — edit any note, duty CC, or volume
CC in REAPER's MIDI editor, the JSFX reacts.

## Track layout

```
[JSFX]   NES - Pulse 1
[JSFX]   NES - Pulse 2
[JSFX]   NES - Triangle
[JSFX]   NES - Noise
[JSFX]   NES - DMC              (only if game uses DMC)
```

Each track has:
- The NSF-extracted MIDI events (notes, CC11 volume, CC12 duty, SysEx
  register state).
- One instance of the JSFX set to the appropriate channel mode
  (Pulse 1, Pulse 2, Triangle, Noise, Full APU).
- Slider presets tuned for the game's driver family.

## Live keyboard setup

1. Plug a MIDI keyboard into your computer (USB or via MIDI
   interface).  REAPER should auto-detect it.
2. Open any B variant project.
3. In REAPER: **Options → Preferences → MIDI Devices**, ensure your
   keyboard is enabled as an input.
4. Arm any JSFX track for recording (the red button).  This routes
   your keyboard to that track's JSFX.
5. Play.  The keyboard should now drive that channel's JSFX.

### Playing multiple channels from one keyboard

The JSFX has three input-priority modes.  When you play the keyboard
while the MIDI item is also playing (not muted), the JSFX decides
priority:

- Priority 1 (SysEx register replay) wins over all others
- Priority 2 (CC11/CC12 automation) wins over keyboard
- Priority 3 (keyboard ADSR mode) only fires when 1 and 2 are idle

So to play the keyboard freely, mute the MIDI item on that track
(right-click → Item properties → Mute, or select + `M`).  Your
keyboard then has clean access to that JSFX.

## MIDI file editing

Every track's MIDI events are real MIDI.  You can:

- Drag notes around in the piano roll.
- Edit CC11 (volume) and CC12 (duty) automation curves.
- Delete notes, add notes, change pitch.
- Transpose with `shift+up/down` on a note selection.

REAPER will play back your edits through the JSFX immediately.  This
is the "play NES-accurate music from arbitrary MIDI input" product
you want.

## What you DON'T get in B (vs A)

No Python-rendered stems.  That means:

- No 14 kHz analog LP filter applied.  Pulse edges can sound slightly
  grittier on high sustained notes (the Rule 35 not-ported gap).
- No $4015 bit-3 noise gate (Rule 30).  For Nintendo / Rare / late-
  Capcom games, noise drums may sound as a continuous "wash" where
  stems sound as crisp percussion.
- No DC blocker.  Silent regions between songs sit at their native
  DC level instead of exactly zero.

For most games these matter less than being able to actually play
live.  Your ear will tell you when it matters.

## Reconfiguring the JSFX per channel

Each track's JSFX has a slider panel.  Key sliders:

- **Slider 1: Channel Mode** — fixed to 0/1/2/3 (Pulse1/2/Tri/Noise)
  per the track.  Don't change unless you know why.
- **Slider 2: Keyboard Mode** — set to 1 to enable live keyboard play
  (default is per-track).  When 0, the JSFX ignores keyboard and
  only plays from MIDI/CC/SysEx automation.
- **Sliders 3-8** (for pulse): Duty, Volume, ADSR envelope for the
  keyboard path.  Only matter when keyboard is driving.
- **Slider 19**: Output gain.  If overall mix is too quiet, nudge up.
- **Slider 20**: Two-phase attack (0 = off).  Adds a fast-decay
  transient on pulse note-ons.  Makes attack perkier at the cost of
  strict libgme parity.

Changes to these sliders persist in the project file.  Reopening the
same RPP later will keep your tweaks.

## Multiple JSFX projects in parallel

REAPER can have multiple projects open at once (File → Open in new
tab).  Useful for:
- A/B-listening two games' sound profiles.
- Layering channels from different games into a single mash-up.
- Copying MIDI from one game's project into another.

## First game to try

`outputv6_B/Balloon_Fight/reaper/01_Song_01.rpp`

Short, instantly recognizable, no complex DPCM or expansion audio.
If Variant B plays Balloon Fight correctly, the basic JSFX pipeline
works for you.

## Validation: if Variant B sounds right, you don't need the rest

If you open B projects for 3-4 games and they sound like the game,
you have your answer: JSFX is a viable stand-alone product.  I can
then:

- Delete the Python stems pipeline (-several GB disk, -thousands
  of lines of code).
- Delete `outputv6_A/` and `outputv6_C/`.
- Keep shipping just B.

That's the cleanest outcome for the product.  The ear-test is what
decides it.
