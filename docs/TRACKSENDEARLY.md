# Tracks Ending Early — Theories and Plan (2026-04-19)

User reports that many songs in outputv6 end before their M3U-declared
duration.  Confirmed across several games: Metroid Intro (10 s instead of
92 s), Castlevania 3 "Beginning" (2.1 s instead of 100 s), various
DuckTales tracks, Legend of Zelda song 2, etc.

This file catalogs every mechanism that can cause early endings in our
stems pipeline, identifies the root cause(s), and describes the fix
plan.  The big one — discovered while writing this file — is the bottom
of the list: an off-by-one bug in `render_channel_stems.py` that caused
stems to render the WRONG NSF track entirely.

## How we know the ground-truth track length

The community-ripped Zophar NSFs include M3U playlist files next to
the `.nsf`.  Format:

```
<filename>::NSF,<NSF_track_number>,<song_name>,<H:MM:SS.msec>,,...
```

The third field is the full song length on real hardware, measured by
the ripper.  For Metroid:

```
::NSF,1,Intro,0:01:32.508,,0:00:03.718
::NSF,3,Brinstar,0:01:35.925,,
```

`batch_stems_project.py::parse_m3u()` reads this and uses it for per-
song `--seconds` at render time.  So we **do** have authoritative
track boundaries for every game we're rendering.  The issue isn't
"we don't know when the track ends" — it's that the pipeline terminates
the render before the M3U-declared duration.

## Mechanisms that can terminate a render early

Six known exit paths in the pipeline that can cause truncation.  In
order of specificity (most specific first).

### 1. `--seconds` CLI cap (HARD user-side limit)

`batch_stems_project.py` takes `--seconds` (default 180).  Per-track
duration is `min(m3u_seconds, args.seconds)`.  If the user passes
`--seconds 60` and Metroid Brinstar M3U duration is 95.9 s, Brinstar
gets rendered at 60 s.

**Status**: Working as intended.  User must pass `--seconds` high
enough (default is now 180 s per 2026-04-18 evening edit).

### 2. `SILENCE_THRESHOLD` in `nsf_to_reaper.py::play_song`

If no APU writes occur for N consecutive frames AND frame > 60, break.

- Old value: 120 frames (2 s).  Truncated CV3 "Beginning" to 2.1 s.
- Current value: 600 frames (10 s).

**Status**: Probably OK at 600, but fragile — any driver with a
10-second quiet section during active playback gets cut off.  For M3U-
driven renders where we already know the target duration, silence
early-exit is unnecessary safety — the duration bound is enough.

**Plan**: Consider disabling silence early-exit entirely when the
caller has passed an explicit duration from an M3U-backed context.

### 3. `STUCK_THRESHOLD` in `nsf_to_reaper.py::play_song`

If N consecutive PLAY calls hit the `max_cyc` limit without returning
normally, break.  Intended to catch drivers that hang.

- Old value: 30 frames of max_cyc hits (0.5 s).  Combined with
  `max_cyc = 30000` instructions, this caused aggressive early exits
  on drivers with spikey per-frame CPU cost.
- Current values: `max_cyc = 200000`, `STUCK_THRESHOLD = 600`
  (10 s).

**Status**: Larger headroom now, but still not infinite.  A genuinely
hung driver still trips at 10 s.

### 4. `STUCK_THRESHOLD` on invalid-song-index INIT

Several drivers respond to `INIT(A=invalid_song)` by halting in a way
that `max_cyc` never terminates cleanly.  My Metroid probe showed
`INIT(A=0xFF)` produces a driver state that emits zero APU writes but
doesn't visibly hang — so the silence threshold fires instead of stuck
threshold.  Either way, the render terminates far before the M3U
duration.

**Status**: This would not be a bug if we were always passing the
right song number.  But see mechanism #6.

### 5. `max_cyc` during INIT or PLAY

If INIT or PLAY exceeds `max_cyc = 200000` instructions in one call,
the call returns `completed=False`.  Some busy drivers (per-frame
heavy calculation + DPCM setup + bank switching + etc.) might exceed
this.

**Status**: 200000 instructions = ~6-7 NES frames of CPU time per
single-frame PLAY.  Way more than real hardware gets.  If a driver
legitimately needs more, something is deeply wrong (infinite loop or
wait for a signal we don't emulate).

### 6. **Off-by-one in `render_channel_stems.py` (ROOT CAUSE, just found)**

The stems renderer had:

```python
frames = emu.play_song(args.song - 1, frames_target)
```

But `emu.play_song()` internally does:

```python
call(self.init_addr, a=song_num - 1)
```

Both subtract 1.  So when the caller passes `--song 1`, render_channel_stems
called `play_song(0, ...)`, which INITed with `A = -1 = 0xFF`.  For most
drivers, this is an invalid song index.  Metroid's driver responded to
`A=0xFF` by producing zero APU writes — which tripped the silence
threshold at 10 s.  Other drivers wrap modulo or clamp, giving a render
that's "audio from some track, just not the one we asked for."

**This bug has been present since stems were added to the pipeline.
Every outputv6 stem rendered so far was off-by-one.**

User-reported symptoms:
- Battletoads / Castlevania / Bionic Commando sounded "right" because
  their drivers handle `A=0xFF` non-destructively (probably clamp / wrap)
  and the rendered track was at least *a* valid song.  User might have
  accepted it as "this game's music."
- Metroid Intro silent and short — driver handles `A=0xFF` by halting
  output.
- Legend of Zelda song 2 ends early — likely similar: position 2 in the
  M3U was actually NSF track X-1 on our pipeline.
- Most "tracks ending early" reports traceable to this.

**Fix (just landed)**: `render_channel_stems.py` now passes `args.song`
directly (no -1).  Verified on Metroid: all 12 songs now render at their
M3U-declared duration (Song_01 Intro: 10 s → 92.5 s).

## What I'm going to do

### Immediate

1. **Kill render_all_nsfs.py** — it started before this fix, so its
   in-progress games are using the buggy code.
2. **Re-render everything in outputv6 from scratch** with the fix.
   This takes several hours but is the correct move — every outputv6
   stem we shipped until now was off-by-one.

### Short-term follow-ups (not urgent but worth doing)

3. **Disable silence early-exit when duration is M3U-backed.**
   `nsf_to_reaper.py::play_song` should optionally accept a flag that
   says "I trust the duration the caller passed; don't early-exit on
   silence."  batch_stems_project would set it whenever an M3U was
   used to pick `song_seconds`.  This eliminates edge cases like CV3
   "Beginning" that have a real quiet intro.
4. **Add a post-render duration audit.**  After each game renders,
   compare actual stems duration vs M3U duration per song and flag
   any >10% discrepancy.  Caught the off-by-one by hand today; a
   regression like this should fail the validation gate next time.
5. **Add a smoke test** that renders the first second of a known-good
   game (e.g. Battletoads song 1) and asserts the pulse1 waveform
   matches a stored reference.  Catches pipeline regressions before
   they ship to REAPER.

### Medium-term

6. **Better driver-hang heuristics.**  The stuck-count mechanism is
   load-bearing but the current values are guesses.  Instrumenting
   play_song to report per-frame instruction count, hung PC address,
   and register read pattern would let us distinguish genuine hangs
   (wait loops) from slow-but-progressing drivers.
7. **NSFe support.**  NSFe is a newer NSF format with embedded track
   metadata (names, durations, loop points).  If we can parse NSFe,
   we get track boundaries directly from the file instead of a
   sidecar M3U.  Reduces dependence on community-ripped M3Us.
8. **Loop-point detection.**  Some tracks loop indefinitely; the M3U
   duration is arbitrary (usually "two loops").  Detecting the exact
   loop point from the emulated register state lets us render cleanly
   without arbitrary cutoffs.

## What the user should expect

The outputv6 renders existing right now are useful but not authoritative
— each song's stems may be from an adjacent NSF track.  When games
*sound right* on ear-test, it's because the neighbor happened to be
musically similar (Battletoads, Castlevania) OR the driver's
INIT-with-invalid-song handling produced something playable.  Games
where the neighbor was significantly different (Metroid Intro → silent,
Zelda tracks shifted) are the visible failures.

After the re-render lands, every stem should match its NSF-declared
track number, and songs should render to their full M3U duration unless
legitimately blocked by a driver hang.
