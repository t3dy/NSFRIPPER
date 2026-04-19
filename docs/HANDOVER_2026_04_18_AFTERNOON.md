# Handover — 2026-04-18 afternoon session

Copy the block below into a new Claude Code window at `C:\Dev\NSFRIPPER`.

---

## HANDOVER PROMPT

I'm continuing work on the NSFRIPPER stems pipeline at `C:\Dev\NSFRIPPER`.

**Load these first:**

1. `CLAUDE.md` — read the "2026-04-18 afternoon: Four more pipeline fixes shipped (outputv6)" section at the top.
2. `docs/STEMS_APPROACH.md` — updated "Limitations and follow-up" section reflects what's now fixed.
3. `.claude/rules/architecture.md` Rules 27-33 — APU non-linear mixing (27), DMC split (28), phase-reset/$4015/sweep (29), noise $4015 gate (30), stems are the deliverable (31), **noise length counter (32)**, **LP + DC blocker (33)**.
4. `docs/HANDOVER_2026_04_18_AFTERNOON.md` — this file.
5. MEMORY.md — auto-loaded.

**State of the pipeline (what changed this session):**

Five separate bugs were fixed on top of the morning's stems approach. The common thread: each bug was invisible to spectral-matching metrics (our measurements against libgme were all within 1.3 dB) but audible in a DAW.

1. **Shared-scale stems** (`scripts/render_channel_stems.py::main`).
   - Bug: each stem was normalized to peak 0.9 independently → REAPER summed to ~2.7× clipping.
   - Fix: render all stems unnormalized (`normalize=False`), compute one scale factor from the summed peak, apply to every stem. Sum now peaks at 0.9 as intended.
   - Evidence: FF3 s2 measured sum peak 2.70 → 0.90 after.

2. **NES analog LP** (`render_channel_stems.py::apply_nes_analog_lp`).
   - Bug: hard amplitude steps at note-on / phase-reset / $4003 writes produced click-on-every-note ("overdrive" / "static" perception).
   - Fix: scipy Butterworth 2-pole LP at 14 kHz applied after the per-channel DAC. Approximates the real NES analog RC filter. libgme uses BLEP synthesis — same end result via a different route.
   - Evidence: Ghosts 'n Goblins max sample-to-sample diff 0.563 → 0.356 (37% less click).

3. **DC blocker** (`render_channel_stems.py::dc_block`).
   - Bug: `mix -= np.mean(mix)` shifted silent regions to a non-zero constant when the signal was asymmetric (drums on noise stem bias mean positive → silent regions at -0.030 instead of 0).
   - Fix: 1-pole HP DC blocker at ~10 Hz via scipy.signal.lfilter.
   - Evidence: SMB noise silent regions went from constant -0.030 to true zero.

4. **Noise length counter** (`scripts/nsf_to_reaper.py::frames_to_channel_data`).
   - Bug: noise gated only on `vol > 0 AND enabled`. Nintendo 1st-party (SMB/Kondo, Zelda, Metroid, Kid Icarus) and Capcom drivers write vol=12 once and rely on the hardware length counter to silence each drum hit. Our output was continuous noise.
   - Fix: capture $400F writes (length reload from `LENGTH_TABLE`), $400C bit 5 (env_loop halt), $4015 bit 3 clear (force zero). Decrement by 2 per frame unless halted/just-reloaded. Render gate now `vol>0 AND enabled AND length_counter>0`.
   - Evidence: SMB Overworld noise active frames 276/300 → 74/300 (drum bursts as intended, 147 silent→active transitions over 30s).

5. **M3U-aware batching** (`scripts/batch_stems_project.py`).
   - Bug: batch iterated all NSF tracks including SFX and blank banks. Section Z was rendering 32 tracks with SFX mixed in.
   - Fix: auto-detect the nsfe2m3u `*.m3u` file next to the NSF, iterate only listed music tracks with per-track durations and real names. `--no-m3u` overrides. Section Z: 32 tracks → 12 music tracks, properly named (`01_Title.rpp` … `12_Game_Over.rpp`).

**Output directories:**
- `outputv5/` — preserved as "noisy examples" archive for before/after comparison. (Ghosts_n_Goblins and Super_Mario_Bros inside v5 got partially overwritten by earlier re-renders before the preserve-outputv5 decision — note this if comparing.)
- `outputv6/` — new canonical output with all five fixes. Generated via `scripts/rebuild_v6.py` from outputv5's game list. Full rebuild is running in background (see "Jobs in progress" below).

**Oracle records (attempts 5-8, decision 522):**
- 4 attempts+outcomes logged for each fix
- Decision `pipeline/pipeline_action` (id 522) = "outputv6 is the canonical location, rebuild_v6.py sweeps all games"

## Jobs in progress

Check on start:
```bash
ps -ef | grep rebuild_v6 | grep -v grep
ls outputv6/ | grep -v "^_" | wc -l
tail outputv6_rebuild.log
```

`scripts/rebuild_v6.py` was kicked at ~14:00 to rebuild all 44 games from outputv5 into outputv6 at 60-second max duration per song. Skips any game that already has RPPs in outputv6 (idempotent).

## User listening issues still open

Confirmed symptoms after the five fixes are shipped but before user has re-tested:

- **SMB2 hanging note at end of song 2** — not yet investigated. Likely an NSF loop-end boundary issue. Pipeline keeps emulating after the song's final note, so a sustained note extends past its musical end. Look at `scripts/nsf_to_reaper.py::play_song` / `frames_to_channel_data`. User's complaint specifically was "a note hangs for a while at the end."

- Noise channel across games using different driver patterns. The length counter fix covers Nintendo/Capcom-style drivers. Other drivers may rely on `vol=0` or `$4015 bit 3=0` for silencing — those already work. If a game sounds wrong, check driver_survey.py family and look at the per-frame `noise` fields (`vol`, `enabled`, `length_counter`, `env_loop`).

## Do's and don'ts

DO:
- Use `outputv6/` as output location. `outputv5/` is read-only reference for before/after.
- Run `scripts/rebuild_v6.py --only GAME` for targeted re-renders.
- Read `architecture.md` Rules 32 and 33 before touching noise capture or DAC post-processing.
- Remember: spectral match vs libgme does NOT imply DAW-audible fidelity. User ear-test is authoritative.

DO NOT:
- Revert per-stem normalization (it re-introduces the 2.7× clipping sum).
- Replace the DC blocker with `mix -= np.mean(mix)` (silent regions off-zero).
- Remove the LP (pulse clicks come back).
- Gate noise only on `vol>0 AND enabled` (drops SMB drum silencing).
- Render RPP files by hand — always via `generate_project.py` or `generate_stems_rpp.py`.
- Overclaim. User corrects "works" / "fixed" language repeatedly. Say "shipped, awaiting ear-test."

## Key files changed this session

| File | Change |
|------|--------|
| `scripts/render_channel_stems.py` | added `apply_nes_analog_lp`, `dc_block`, shared-scale scaling in `main()`, `normalize=False` flag on `render_stem`/`render_dmc_stem` |
| `scripts/nsf_to_reaper.py` | added `LENGTH_TABLE` constant, `env_loop`/`const_vol`/`env_period`/`length_counter`/`length_reload_frame` fields on noise channel, $400F handler, $4015 bit-3-clear handling, per-frame length counter decrement |
| `scripts/batch_stems_project.py` | added `parse_m3u()`, M3U auto-detection, `--m3u`/`--no-m3u` flags, per-track durations from M3U |
| `scripts/rebuild_v6.py` | NEW — batch rebuild all outputv5 games into outputv6 |
| `.claude/rules/architecture.md` | Rules 32 (noise length counter) + 33 (LP + DC blocker) added |
| `CLAUDE.md` | updated stems-approach section with the five fixes, updated Key Commands |
| `docs/STEMS_APPROACH.md` | updated "Limitations and follow-up" — items 2-8 now show fixed status |
| `docs/HANDOVER_2026_04_18_AFTERNOON.md` | THIS FILE |
| ANTIRIPPER oracle DB | 4 attempts+outcomes, 1 decision |

## First action in the new window

```bash
# 1. See how much of the outputv6 rebuild completed:
ls outputv6/ | grep -v "^_" | wc -l
ps -ef | grep rebuild_v6 | grep -v grep
tail -30 outputv6_rebuild.log

# 2. Preflight the next game the user asks about:
python -c "from ANTIRIPPER.agent_oracle import AgentOracle; o=AgentOracle(); print(o.get_preflight_context('<game_slug>', 'nsf_extraction'))"
```
