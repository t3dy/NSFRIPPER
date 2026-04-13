# REAPER Fuckery

## What I was trying to do

I had already changed the repo copy of:

- `C:\Dev\NSFRIPPER\studio\jsfx\ReapNES_APU2.jsfx`

Those changes were meant to improve the `Wizards & Warriors` title phrase by:

- treating the disputed bass/pluck moment as a composite `pulse1 + triangle` event
- damping triangle body much harder on the disputed reattack
- keeping fuller triangle body on the surrounding full reattacks

At that point, I wanted a **real audition** instead of only code-level reasoning.

So I tried to use REAPER to render the existing title project:

- `C:\Dev\NSFRIPPER\Projects\Wizards_and_Warriors\Wizards_&_Warriors_01_Wizards_&_Warriors_Title_APU2_releaseaware_v5.rpp`

The goal was simple:

1. render the title project with the updated JSFX
2. confirm whether the phrase around frames `928 / 960 / 976` now sounds closer to the game audio

## Why REAPER mattered

The `.rpp` project is the real playback environment for this work.

The quick math/model checks I ran in the shell are useful, but they are still only approximations of what the actual REAPER + JSFX chain will do.

So I was trying to move from:

- "the code probably behaves better"

to:

- "the rendered project actually sounds better"

## What went wrong

### 1. My first REAPER probe hung

I tried asking REAPER for command-line help.

That was a mistake in this environment because it left a REAPER process open and tied up the turn for too long.

### 2. The project was not necessarily using the repo file I edited

This was the important discovery.

The `.rpp` references the installed JSFX by REAPER effect name:

- `ReapNES Studio/ReapNES_APU2.jsfx`

REAPER's installed effects copy lives at:

- `C:\Users\PC\AppData\Roaming\REAPER\Effects\ReapNES Studio\ReapNES_APU2.jsfx`

That means:

- editing the repo copy does **not automatically** mean REAPER will use it

So even if my repo edit was correct, REAPER could still have been loading stale code.

### 3. I synced the updated JSFX into REAPER's installed effects folder

I copied:

- `C:\Dev\NSFRIPPER\studio\jsfx\ReapNES_APU2.jsfx`

to:

- `C:\Users\PC\AppData\Roaming\REAPER\Effects\ReapNES Studio\ReapNES_APU2.jsfx`

That part succeeded.

### 4. Headless render still did not complete

I created a disposable render-check copy of the title project in:

- `C:\Dev\NSFRIPPER\scratch\ww_render_check\WW_Title_APU2_releaseaware_v5_rendercheck.rpp`

and set it up with explicit render output settings for:

- `C:\Dev\NSFRIPPER\scratch\ww_render_check\WW_Title_APU2_releaseaware_v5_rendercheck.wav`

Then I launched REAPER with `-renderproject`.

What happened:

- REAPER opened
- the process stayed responsive
- no `.wav` file was produced before timeout
- I killed the process after the timeout instead of letting it sit forever

So the current blocker is:

- I do **not** yet have a successful non-interactive REAPER render from this shell

## What I *did* verify without REAPER

I checked the new triangle behavior mathematically against the old constants.

Current direction:

- the disputed damped hit around `960` is much weaker than before
- the surrounding full reattacks recover more body than my first over-aggressive pass

In short:

- the code changes are pointed in the right direction
- the missing piece is a successful real REAPER audition/render

## Current best interpretation

The main thing I was doing was **not random REAPER thrashing**.

I was trying to answer this very specific question:

- "Does the updated live JSFX actually make the `Wizards & Warriors` title phrase sound more like the game?"

To answer that honestly, I needed the real REAPER project to render or play with the updated installed JSFX.

## Practical next step

The easiest next step is probably interactive, not headless:

1. open the title `.rpp` in REAPER
2. confirm it is loading the installed `ReapNES_APU2.jsfx`
3. audition the phrase around frames `928 / 960 / 976`
4. decide whether the triangle is still too strong, or whether pulse1 still needs more attack dominance

## Files involved

- `C:\Dev\NSFRIPPER\studio\jsfx\ReapNES_APU2.jsfx`
- `C:\Users\PC\AppData\Roaming\REAPER\Effects\ReapNES Studio\ReapNES_APU2.jsfx`
- `C:\Dev\NSFRIPPER\Projects\Wizards_and_Warriors\Wizards_&_Warriors_01_Wizards_&_Warriors_Title_APU2_releaseaware_v5.rpp`
- `C:\Dev\NSFRIPPER\scratch\ww_render_check\WW_Title_APU2_releaseaware_v5_rendercheck.rpp`

## Bottom line

The REAPER work was an attempt to do proper audio verification of the new composite-bass fix.

The useful result from that detour is:

- I discovered the installed REAPER JSFX copy was separate from the repo copy
- I synced the new JSFX into REAPER's effects folder
- I still need a reliable way to render or audition the project in REAPER itself
