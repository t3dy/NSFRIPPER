# Audio Diff Workflow

Stop guessing what's wrong with the audio. Measure it.

## The tools

| Tool | What it does |
|------|--------------|
| `scripts/audio_diff.py` | Compares two WAV files. Reports per-band dB divergence over time + top mismatch hotspots. Writes CSV + heatmap PNG. |
| `scripts/reaper_render.py` | Headless REAPER CLI render of an `.rpp` to WAV. |
| `scripts/render_wav` (existing, inside `nsf_to_reaper.py`) | Python render: runs the 6502 emulator, applies envelope sim, non-linear mixing. |

## The three useful WAVs for any song

1. **Reference (ground truth)** — what the game *should* sound like. Options:
   - Record Mesen audio while the game plays. Save as WAV.
   - Use NSFPlay (download from https://bbbradsmith.github.io/nsfplay/) and save WAV.
   - Capture from real NES via line-in.
   - The existing `output/<Game>/wav/*.wav` (Python pipeline) — our current best Python render.

2. **REAPER render of v1 RPP** — what REAPER actually plays with the old Console plugin.
3. **REAPER render of v2 RPP** — what REAPER plays with the APU2_v2 (envelope + linear counter fixes).

## Typical diagnostic loop

```bash
# Get a ground-truth WAV for your song (from Mesen, NSFPlay, etc.):
# e.g. cp "<NSFPlay output>/Song_3.wav" ref/song_3_truth.wav

# Render the v2 RPP via REAPER
python scripts/reaper_render.py "output/<Game>_v2/reaper/<song>_v2.rpp" \
  --out "output/<Game>_v2/wav/<song>_v2_reaper.wav"

# Compare
python scripts/audio_diff.py \
  ref/song_3_truth.wav \
  output/<Game>_v2/wav/<song>_v2_reaper.wav \
  --plot diff.png \
  --out diff.csv \
  --top 15
```

Read the top-N hotspots. Each one says: "at second N.NNs, band B, test is X dB louder/quieter." Pick the biggest one, look at the frame, and make a hypothesis about what register dimension is responsible.

## What the bands mean

| Band | Hz | NES stuff it catches |
|------|-----|---------------------|
| sub | 50–120 | DMC bass samples, triangle very-low notes |
| bass | 120–250 | Triangle bass, DMC drums, pulse bottom octave |
| lowmid | 250–500 | Triangle mid, pulse mid-low |
| mid | 500–1k | Pulse lead, vocal-range melody |
| uppermid | 1–2k | Pulse presence, envelope attack transients |
| presence | 2–4k | Duty cycle character, noise drum body |
| brilliance | 4–8k | Noise hiss, high LFSR hits, pulse harmonics |
| air | 8–16k | Noise hi-hat / hiss character |

## Interpreting hotspots

- **TEST QUIETER in bass** at a timestamp where the game has a triangle note → triangle gate closing too early. Loosen the linear-counter interpretation or disable it temporarily.
- **TEST LOUDER in upper-mid** sustained → our pulse envelope is not decaying fast enough.
- **TEST QUIETER in brilliance/presence at regular intervals** where the game has drums → noise length counter silencing channel (or vice versa: test LOUDER in presence means noise is over-sustaining).
- **Systematic bias across all bands in one direction** → master gain mismatch, not a spectral problem.

## Limitations and gotchas

- **Alignment**: the tool cross-correlates the first 2 seconds. If the ref has a long silent lead-in and the test doesn't, alignment will be wrong. Use `--no-align` in that case and manually trim WAVs to match starts.
- **Silence vs noise** shows as ~65 dB divergence (floored). Treat these as "binary presence mismatch" not "65 dB spectral mismatch" — one of the two has no content at all in that band/time.
- **RMS normalization** matches overall loudness before diffing, so "test is too quiet" won't show as a global -10 dB bias — you see spectral *shape* differences, not level.
- **REAPER bus mixing is linear** — non-linear APU mixing in the JSFX only fires in `ch_mode=4` (Full APU, single-track). Multi-track RPPs sum linearly on REAPER's master. Diff A below illustrates this.

## What the first runs on W&W Song 3 revealed

| Diff | Finding |
|------|---------|
| Python v1 vs REAPER v1 | REAPER playback is +3 dB brighter and -3 dB less bassy than Python render. Consistent with REAPER's linear bus sum bypassing our non-linear APU mixer. |
| Python v1 vs REAPER v2 | All bands quieter in REAPER v2 (-2 to -6 dB). The triangle gate fix is removing energy — intended effect. |
| REAPER v1 vs REAPER v2 | First 2 seconds of v2 have -65 dB bass vs v1. Opening triangle notes are being cut off by the new linear counter. Likely over-aggressive. |

Actionable: the v2 plugin's triangle gate is probably closing too fast at song start. Either the `$400B`-write flag is not firing on the first triangle setup, or the counter decrement rate is wrong. Check the first 120 quarter-frames of triangle state vs what the gate produces.
