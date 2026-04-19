# Stems Approach (2026-04-18)

## Why this exists

After weeks of trying to make a JSFX synth in REAPER sound like the NES, we
hit a fundamental wall: multi-track linear-sum playback in REAPER cannot
reproduce the NES APU's non-linear DAC mixing. Per-channel tracks with a
custom synth plugin sum linearly on the master bus, producing renders that
were measured +14 dB bass-heavy vs the libgme / Zophar reference, and
audibly "ringing" note tails.

The stems approach bypasses the problem: instead of trying to synthesize
the NES audio in REAPER, **we render each APU channel's audio as a
pre-baked WAV stem and place those stems as audio tracks in the REAPER
project**, with the MIDI tracks alongside (muted by default) for editing.

## Architecture

```
                    NSF file
                       |
                 [py65 emulator]
                       |
                       v
             per-frame APU register state
                       |
          +------------+------------+
          |            |            |
          v            v            v
     scripts/      scripts/     existing
     render_       render_        MIDI +
     channel_        wav()        RPP
     stems.py       (full          pipeline
          |           mix)
          v
  per-channel WAVs
  (pulse1.wav,
   pulse2.wav,
   triangle.wav,
   noise.wav)
          |
          +--+  scripts/generate_stems_rpp.py
             v
      REAPER project (.rpp)
      - 4 audio tracks (stems, unmuted)
      - 4 MIDI tracks (editable, JSFX synth muted by default)
```

The audio stems come from the same Python `render_wav()` logic that was
user-confirmed to match the Zophar MP3 reference within 1.3 dB on all
spectral bands. Each stem is rendered by running the full per-channel
HW envelope + triangle linear counter + non-linear DAC math with only
ONE channel's output active.

## Key scripts

| Script | Purpose |
|--------|---------|
| `scripts/render_channel_stems.py` | Renders per-channel WAV stems from an NSF + song number. Uses the same HW envelope + linear counter sim as `render_wav()`. |
| `scripts/generate_stems_rpp.py` | Builds a REAPER project with audio stems + editable MIDI tracks (JSFX synth muted by default). |
| `scripts/batch_stems_project.py` | Runs both above for every song in an NSF. Accepts optional `--names` JSON to map track numbers to song names. |

## Usage

**Single song:**
```bash
python scripts/render_channel_stems.py <game.nsf> --song 3 --seconds 60 \
    --out-dir outputv5/<game>/stems/song3/
python scripts/generate_stems_rpp.py \
    --midi <extracted>.mid \
    --stems-dir outputv5/<game>/stems/song3/ \
    --out outputv5/<game>/reaper/song3.rpp
```

**Whole game:**
```bash
python scripts/batch_stems_project.py <game.nsf> \
    --names song_names.json \
    --out-dir outputv5/<game>/
```

**Output directory structure:**
```
outputv5/<game>/
  reaper/       -- <slug>.rpp per song
  stems/<slug>/ -- pulse1.wav, pulse2.wav, triangle.wav, noise.wav
  midi/         -- <slug>.mid per song (for editing / score export)
  _nsf_extract/ -- intermediate, not for user consumption
```

## Track layout in generated RPPs

```
Track 1: [AUDIO] NES - Pulse 1       (stem from render_wav)
Track 2: [MIDI]  NES - Pulse 1 MIDI  (muted, JSFX loaded for keyboard play)
Track 3: [AUDIO] NES - Pulse 2
Track 4: [MIDI]  NES - Pulse 2 MIDI
Track 5: [AUDIO] NES - Triangle
Track 6: [MIDI]  NES - Triangle MIDI
Track 7: [AUDIO] NES - Noise
Track 8: [MIDI]  NES - Noise MIDI
```

Audio plays by default. MIDI tracks are muted but loaded with the JSFX
synth, so unmuting one lets you play the keyboard through that channel's
synth while the other channels play from audio.

## How it sounds

- Bass notes have proper articulation (triangle ring problem solved — each
  triangle note is gated by its hardware linear counter in the source
  render). Confirmed audibly: "bass notes are audible and have distinction."
- Per-channel DAC compression is baked into each stem, so linear summing
  in REAPER approximates hardware output. Not bit-exact (real hardware
  DAC is non-additive across channels) but close — user feedback: "not
  bad."

## Limitations and follow-up

1. **Per-channel DAC non-additivity:** summing 4 DAC-compressed stems is not
   the same as running 4 channels through one DAC. In practice the
   difference is small (a few dB in the loudest moments).

2. **Noise channel $4015 gate (fixed 2026-04-18 morning):** noise respects
   the $4015 bit 3 enable flag. Most games only briefly enable this during
   drum hits. Without the gate, continuous noise was audible across whole
   songs. See `.claude/rules/architecture.md` Rule 30.

3. **Noise length counter (fixed 2026-04-18 afternoon):** Nintendo 1st
   party and Capcom drivers leave noise vol=12 and $4015 bit 3 set, and
   rely on the hardware length counter ($400F load + half-frame
   decrement) to silence each drum hit. Without simulating this, SMB
   sounded like "a wash of noise." Full length counter sim now lives in
   `nsf_to_reaper.py::frames_to_channel_data`. See architecture.md Rule 32.

4. **DMC rendering** (implemented in `render_channel_stems.py`): DPCM
   samples are played back through the NES DMA/bit-reading algorithm and
   $4011 direct DAC writes are captured. Battletoads drums and Sunsoft
   DPCM-bass now audible.

5. **Pulse/triangle click transients (fixed 2026-04-18 afternoon):**
   naive square/triangle sampling produced hard zero-to-amplitude steps
   audible as "click on every note" / "overdriven synth." A 2-pole
   Butterworth LP at 14 kHz (matches NES analog RC filter) now smooths
   these. See architecture.md Rule 33.

6. **Silent-region DC bias (fixed 2026-04-18 afternoon):** `mix -= mean(mix)`
   shifted silent frames to a small constant offset when the signal was
   asymmetric (e.g. drum hits on noise stem). Replaced with a 1-pole HP
   DC blocker at ~10 Hz. Silent regions now at true zero.

7. **Per-stem normalization (fixed 2026-04-18 afternoon):** previously
   each stem was normalized to peak 0.9 independently. REAPER summed
   them to ~2.7× clipping. Now all stems share one scale factor computed
   from the summed peak, preserving per-channel level proportions.

8. **Song naming convention (fixed 2026-04-18 afternoon):** the nsfe2m3u
   M3U file next to the NSF is now the canonical "music only" filter and
   name source. `batch_stems_project.py` auto-detects it. Blank intro
   tracks and SFX banks (e.g. Section Z tracks 1-20) are skipped. Use
   `--no-m3u` to render everything.

9. **JSFX synth for live keyboard play still needs tuning.** The MIDI
   tracks in the generated RPPs are muted by default. To play keyboard:
   unmute one MIDI track, arm it, and play. The synth's pulse/triangle/
   noise character is approximate.

## What this replaced

Before the stems approach, we were trying to make `ReapNES_APU2_v2.jsfx`
reproduce the full NES APU in REAPER. That path required:

- Multi-track with non-linear DAC compression (tried: master FX block,
  bus track with AUXRECV, folder track — none worked for multi-track DAW
  editing)
- Exact HW envelope / linear counter / length counter simulation
  (implemented partially, measurably correct in Python but still misfiring
  in REAPER for unclear reasons)
- Analog output filters (attempted, turned out libgme doesn't apply them —
  removing them improved match)

All of that work informs the `render_channel_stems.py` pipeline. The JSFX
synth still exists and still loads on MIDI tracks for live keyboard play.
But the **audio is no longer synthesized live in REAPER** — it's pre-baked
from Python code with measured hardware accuracy.

## Relationship to existing docs

- `docs/NES_AUDIO_FINDINGS_2026_04_17.md` — investigation of driver
  families and APU behavior. The HW envelope + linear counter sim that
  produces the stems was built on those findings.
- `docs/AUDIO_DIFF_WORKFLOW.md` — how to measure our output against a
  reference (libgme, Zophar MP3, real hardware capture). Used to verify
  the stems' spectral accuracy.
- `.claude/rules/architecture.md` Rule 30 (new) — noise channel $4015
  gating, discovered via the stems approach when noise was audibly too
  present.
- `.claude/rules/reaper_projects.md` — the stems approach gives a
  **third** RPP generation pattern alongside Console and APU2.
