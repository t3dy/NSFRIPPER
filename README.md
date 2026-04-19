# NSFRIPPER — NES Music Extraction Studio

## [Browse the Game Library](https://t3dy.github.io/NSFRIPPER/)

> 321 games extracted | 8,900+ MIDI files | Per-frame APU fidelity | REAPER projects included

---

## What This Is

A complete pipeline for extracting music from NES games via NSF emulation,
producing 4-channel MIDI with per-frame volume/duty automation, plus REAPER
DAW projects with the ReapNES synthesizer plugin.

**Fully automated.** NSF files are emulated via a 6502 CPU running the
original sound driver. APU register writes are captured at 60 Hz and
converted to MIDI with CC11 (volume) and CC12 (duty cycle) automation
that preserves the original envelope shapes.

## The NES Sound Chip (RP2A03)

5 channels, all synthesized:

| Channel | Waveform | Volume | Special |
|---------|----------|--------|---------|
| **Pulse 1** | Square (4 duty cycles) | 4-bit (0-15) | Sweep unit |
| **Pulse 2** | Square (4 duty cycles) | 4-bit (0-15) | Sweep unit |
| **Triangle** | Fixed triangle | Gate only (on/off) | 1 octave lower than pulse |
| **Noise** | LFSR (2 modes) | 4-bit (0-15) | 16 pitch periods |
| **DMC** | 1-bit delta PCM | 7-bit (0-127) | Sample playback |

## Driver Families

Games are classified by how aggressively their sound driver controls the
APU per frame, measured by CC11/CC12 density in extracted MIDI:

| Family | CC11/note | Example Games | Character |
|--------|-----------|---------------|-----------|
| **Hardware Envelope** | 0.1-2.8 | Mega Man, DuckTales | Clean, simple decay |
| **Standard Envelope** | 3.5-5.6 | Castlevania, Contra, Ninja Gaiden | Expressive per-frame volume |
| **Duty Animators** | 3.7-4.9 | Super Mario Bros, Kirby | Volume + timbral animation |
| **Dense Automators** | 5.1-14.9 | Final Fantasy, Batman | Near-continuous volume stream |
| **Full Animation** | >7.0 both | Super Mario Bros 3 | Both axes at frame rate |

## Pipeline

```
NSF file → 6502 emulation → APU register capture → MIDI + CC automation → REAPER project
```

### Key Commands

```bash
# Batch extract all games
python scripts/batch_nsf_all.py

# Single game
python scripts/nsf_to_reaper.py <nsf> --all -o output/Game/

# Generate REAPER project from MIDI
python scripts/generate_project.py --midi <file> --nes-native -o <out>

# Classify game into driver family
python scripts/driver_survey.py --game <slug>

# Regenerate website
python scripts/generate_site.py
```

### Tools

| Script | Purpose |
|--------|---------|
| `nsf_to_reaper.py` | NSF emulation + MIDI/REAPER extraction |
| `batch_nsf_all.py` | Batch process all games |
| `generate_project.py` | MIDI to REAPER project (canonical RPP builder) |
| `trace_to_midi.py` | Mesen trace to MIDI (ROM-parsed games) |
| `driver_survey.py` | CC density classification into 5 families |
| `generate_site.py` | Rebuild GitHub Pages site |
| `expansion_detect.py` | Scan NSFs for expansion audio chips |

## Extraction Status

321 games with NSF files extracted to MIDI. 278 with REAPER projects.

ROM-parsed games with trace-level validation:

| Game | Status | Validation |
|------|--------|-----------|
| Castlevania 1 | Trusted | 0 pitch mismatches against Mesen trace |
| Contra | Trusted | Full ROM parse, all 11 tracks |
| Wizards & Warriors | Partial | 16 songs structural, title track trace-validated |

## Fidelity Hierarchy

1. **Mesen Trace** — APU register dumps from real gameplay. Ground truth.
2. **SysEx in MIDI** — Lossless register state encoding.
3. **NSF Emulation** — 6502 CPU runs the sound driver. Per-frame CC11/CC12.
4. **CC11/CC12 in MIDI** — Volume + duty envelope. Loses sweep, noise mode.
5. **ADSR Approximation** — Only for live keyboard when no file data exists.

## ANTIRIPPER Knowledge Base

The project includes an oracle-backed knowledge base (`ANTIRIPPER/`)
that tracks extraction decisions, prevention patterns, hardware facts,
and driver family classifications. Pipeline hooks automatically record
evidence and decisions for every extraction run.

## Project History

Started as Battletoads NES music reconstruction, grew into a universal
NES music extraction pipeline. The original work on Castlevania, Contra,
Battletoads, and Wizards & Warriors established the trace validation
methodology and the 5-family driver classification system.

## Week-by-week progress

### Week 1 — 2026-03-31 to 2026-04-05: Foundation

Project migrated from its earlier home ("NESMusicStudio") into a clean
repo on 2026-03-31.  Five days of Battletoads reconstruction work
immediately followed — tracing the original Rare driver through Mesen
APU captures, fixing an 11-bit period mask bug, and shipping the first
validation-report + database-ontology scaffolding.

By 2026-04-02 the pipeline had a **sweep-induced fake-note detector**
(FAKENOTECHANGES.md), a first pass at merging six separate JSFX plugins
into one unified "ReapNES Studio" synth, and a "kitchen-sink audit" of
what the project already knew but wasn't using.  The week closed with
the **execution-semantics doctrine** baked into every system file —
the rule that parser output is hypothesis, not music, until driver
execution is simulated frame-by-frame.

### Week 2 — 2026-04-13 to 2026-04-17: Breakthrough

Two back-to-back sessions (415/416) on 2026-04-13 and 2026-04-14
shipped the **NSF bankswitch fix**: two subtle emulator bugs (non-page-
aligned load_addr and missing `$5FF6-$5FF7` handling) that together
recovered **233 songs across 16 previously-failing games** (Ninja
Gaiden, Zelda, CV3, Goemon, Mission Impossible).  84% of our NSF
extraction failures were bankswitch-related.

The same week closed with:
- **271-game driver family census** (2026-04-14) — 5→4 family taxonomy
  revision based on actual CC11/CC12 density data.
- **Non-linear APU mixing** (2026-04-15) — impedance-based mixing
  formulas ported into every renderer (Python, JSFX, WAV path).
  Fixes the "simultaneous channels too loud" bug that plagued every
  multi-channel render.
- **Expansion audio** (2026-04-15) — VRC6 + FDS channels extracted
  into MIDI/RPP for 35 games, 768 songs.
- **DPCM/DAC split** (2026-04-16) — DMC channel now correctly
  distinguishes sample-triggered playback from `$4011` direct DAC
  writes.  Recovers Sunsoft bass (Batman, Blaster Master, Journey to
  Silius, Gremlins 2) and Battletoads' algorithmic drums.
- **Phase reset + `$4015` + sweep capture** (2026-04-16) — three APU
  events previously dropped now correctly tracked per-frame.
- **321 game pages live** on GitHub Pages — classified by driver
  family with per-track listings.
- **Driver investigation week** (2026-04-17) — 7 investigation passes
  produced register-level evidence for **10+ driver families across
  5 axes** (code identity, envelope shape, noise conventions,
  `$4017` signature, expansion-audio patterns).  See
  `docs/NES_AUDIO_FINDINGS_2026_04_17.md` for the full taxonomy.

### Week 3 — 2026-04-18 to 2026-04-19: Stems pipeline + playable synth

**Stems approach introduced** (2026-04-18 morning) as the primary
deliverable path.  Instead of trying to reproduce hardware NES audio
inside a live REAPER JSFX, we render per-channel audio stems from the
Python pipeline and place them as audio tracks in the REAPER project —
sidestepping the non-linear-DAC-at-master-bus problem that multi-track
JSFX couldn't solve.  MIDI tracks preserved alongside for editing.

**Five stems-pipeline fixes** (2026-04-18 afternoon):
1. Shared-scale stem normalization (prevents REAPER's linear sum from
   clipping to 2.7×).
2. **14 kHz Butterworth LP** (approximates the NES analog output stage,
   kills per-note click transients).
3. **1-pole 10 Hz DC blocker** (replaces mean-subtraction, keeps silent
   regions at true zero).
4. **Noise length counter simulation** (SMB Overworld drums 276/300 →
   74/300 active frames — drum bursts instead of continuous wash).
5. **M3U-aware batching** (iterates only the playlist's music tracks
   with proper names and per-track durations).

**Architecture Rules 34-36 shipped** (2026-04-18 evening):
- Rule 34 — **Triangle gate-off holds DAC value**.  Eliminates
  vinyl-pop artifacts at triangle bass staccato transitions (measured
  98.4% click-magnitude reduction on Battletoads).
- Rule 35 — **Bandlimited pulse synthesis** via analytical per-sample
  integration.  ~67% reduction in pulse-edge aliasing.
- Rule 36 — **NSF player writes `$4015 = $0F` before INIT**.  Per NSF
  specification.  Restores noise drums on ~30% of games
  (Castlevania, CV3, all Rare, all late-Capcom, Kid Icarus, Metroid,
  Wizards & Warriors, Spy Hunter, Kirby, Ninja Gaiden).

**The off-by-one bug** (2026-04-19) — `render_channel_stems.py`
passed `args.song - 1` to `play_song()`, which itself already
subtracts 1 for INIT; double-subtract meant every stem since the
stems pipeline was added rendered from one adjacent NSF track.  For
drivers that gracefully handle `A=0xFF` (Battletoads, Castlevania) it
produced plausible-sounding audio from the wrong track; for Metroid
(which halts on invalid song index) it silently truncated the Intro
to 10 s.  Discovery and fix collapsed a week of "tracks ending
early" reports into one root cause.  See
`docs/TRACKSENDEARLY.md`.

**Deterministic naming-audit pipeline** shipped same day:
- `track.json` sidecar per song (pipeline version, NSF track, M3U
  position, rendered duration) as single source of truth.
- `scripts/audit_names.py` — classifies every song into
  `correct / rename_only / re_render_required / truncated /
  ambiguous`.
- `scripts/apply_repairs.py` — safe renames + emit re-render list.
- Validation guards in the pipeline reject invalid song indices
  loudly so the off-by-one bug cannot recur silently.
- Full policy in `docs/NAMING_POLICY.md`.

**Three-variant architecture** (2026-04-19):
- `outputv6_A/` "Double Dose" — audio stems + MIDI+JSFX together.
- `outputv6_B/` "Live Wire" — pure MIDI+JSFX, playable synth path.
- `outputv6_C/` "Ditto Head" — placeholder for JSFX-rendered stems
  via ReaScript (deferred).

Six EAR_LAB docs (`docs/EAR_LAB_*.md`) describe how to A/B-test the
three variants per driver family and report findings via a fill-in
report-card template.

**Parallelized rebuild** (2026-04-19) — `render_all_nsfs.py --jobs 6`
cuts the full 150-game rebuild from ~6 days sequential to ~1 day.
Zophar NSF importer + fuzzy-resolving downloader means any missing
NSF can be fetched with one command.

### Current status (as of 2026-04-19)

- **150 games** with NSFs in the pipeline.
- **150-game rebuild** in progress with all Rules 27-36 applied and
  the off-by-one fix.  Each completed game gets A/B/C variants
  generated.
- **JSFX** has Rule 27 (non-linear mixer) and Rule 34 (triangle
  gate-off) fixes shipped.  Rules 30/33/35 deferred pending user
  ear-test feedback on whether the live-playable JSFX is acceptable
  without them.
- **Ongoing question**: does JSFX-alone (Variant B) deliver the
  "playable synth + MIDI keyboard" product goal?  Ear-test answer
  drives the next ~week of work (either ship B as-is, or port the
  remaining DSP rules to JSFX).

---

# Approaches, pros/cons, and trade-offs

Below is the honest state of every architectural choice we've made.
Each approach has known strengths, known weaknesses, and unresolved
questions.  Future work items are called out explicitly so contributors
can pick them up.

## Approach 1 — NSF emulation via py65

What we do: run the NSF file through a pure-Python 6502 emulator
(`py65`), trap writes to APU registers (`$4000-$4017` plus expansion
ranges), and capture per-frame register state.  That state is the
canonical intermediate that MIDI + stems derive from.

**Pros**:

- **Fully automated.**  Given an NSF + M3U we extract music with no
  human intervention.  Scales to the whole NES library (~2000 games).
- **Self-contained.**  No external emulator binary required.  Just
  Python + a few dependencies.  Runs anywhere Python runs.
- **Transparent.**  Every register write is a Python event we can
  instrument, log, or mutate for research.  The emulator-in-Python
  gave us the bankswitch fix (Rule 26), the NSF player init fix
  (Rule 36), and the stuck-detection tuning.
- **Integrates with Python ML tooling.**  Per-frame register state
  goes directly to numpy; easy to build classifiers, visualizers,
  or fingerprinters on top.

**Cons**:

- **Slow.**  py65 is ~100-200K instructions/sec in pure Python.  A
  NES frame is ~30K cycles = ~10K instructions, so real-time (60 Hz)
  requires ~600K instr/sec — py65 is ~3-6x too slow.  That's fine
  for offline batch work but impractical for live playback.
- **Incomplete hardware modeling.**  py65 emulates the 6502 faithfully
  but doesn't model the PPU, NMI/IRQ scheduling, DMC DMA bus
  contention, or the frame counter.  Some drivers (Metroid Intro, a
  handful of others) rely on these and hang or misbehave.
- **Register-capture granularity is per-frame.**  Mid-frame register
  writes are preserved in order but timed coarsely.  For CC-automation
  purposes that's fine; for bit-accurate hardware replay it isn't.

**Alternative considered**: Blargg's `libgme` (the gold-standard
chiptune playback library).  Rejected for our core pipeline because
it's a black box from Python's perspective — we couldn't easily
instrument registers for MIDI export.  We still use `libgme` output
as a spectral reference target.

**Unsolved mysteries**:

1. **Metroid Intro hangs** — PLAY routine consistently hits `max_cyc`
   on every frame.  Probably a DMA-completion wait or frame-IRQ poll
   we don't emulate.  See `docs/TRACKSENDEARLY.md` §6 and
   `scratch/metroid_intro_probe.py`.
2. **SMB writes `$4011 = 48` every frame with the same value** — a
   constant DC bias.  Musically inert (the DC blocker removes it)
   but why does Kondo's driver do this?  Anti-pop trick?  DAC
   self-test?  See `docs/NEWDRIVERFAMILIES.md` Open Questions.
3. **How does Castlevania produce noise drums without writing `$4015`
   bit 3?**  Per NESdev spec, bit 3 clear forces length counter to 0
   which silences the channel.  Yet real CV has audible noise drums.
   Either our understanding of the spec is off or Rule 36 (`$4015 =
   $0F` before INIT) is doing more work than we realized.

**Possible next steps**:

- Port py65 emulation to a faster backend (Rust + pyo3, or a
  hand-optimized Python JIT).  ~10x speedup would make live playback
  feasible.
- Add frame IRQ + NMI emulation.  Would likely unstick Metroid Intro
  and any similar game.  Moderate work.
- Add DMC DMA bus-stealing modeling.  Would affect timing of
  DMC-heavy games (Battletoads, Journey to Silius) subtly.

## Approach 2 — ROM-parse (trace pipeline)

For games with specific trusted parsers (Castlevania 1, Contra,
Wizards & Warriors title), we read the original ROM's music data
directly and simulate the driver's playback logic frame-by-frame.
The output is compared against a live Mesen APU trace and is only
"trusted" when pitch/duration/volume all match.

**Pros**:

- **Validated against ground truth.**  Mesen trace from real gameplay
  is the highest-fidelity source available; matching it proves we
  understand the driver.
- **Encodes semantic intent.**  A ROM parse knows what the NOTE is,
  not just what the PERIOD register happened to be.  Frees downstream
  MIDI export from reverse-engineering pitch from register values.
- **Enables editing.**  If you want to remix Castlevania Vampire
  Killer, the ROM parse produces clean MIDI notes (not
  frame-quantized CC data).

**Cons**:

- **Per-driver.**  Each engine (Capcom Kondo, Konami Maezawa, Rare,
  Sunsoft, Nintendo 1st-party, …) needs its own parser.  We've done
  3; the NES library has ~10-14 distinct driver codebases.
- **Slow to expand.**  Writing a new parser is 1-2 weeks of reverse
  engineering.  Verifying it takes another week.  We won't scale
  past the dozen most-played games without someone else contributing
  parsers.
- **Requires disassembly.**  Most NES drivers have community-written
  disassemblies on GitHub; some don't.  Those without are effectively
  gated.

**Unsolved mysteries**:

- None specific to this approach — it's just expensive.

**Possible next steps**:

- **Capcom 6C80 parser** (high ROI).  Used by Mega Man series and
  many late Capcom Disney titles.  Format documentation exists in
  RH #274.  Parser not yet written.  Would add ~40 games to trusted
  status.
- **Sunsoft parser**.  Blaster Master, Journey to Silius, Batman,
  Gremlins 2.  Adds the signature DMC bass bend not captured well
  by NSF emulation alone.

## Approach 3 — Stems pipeline (Python → WAV → REAPER)

Render per-channel audio stems from the Python pipeline and place
them as audio tracks in the REAPER project.  Each stem goes through
the NES non-linear DAC formula, a 14 kHz analog LP, a DC blocker,
and shared-scale normalization.

**Pros**:

- **Archival-quality audio.**  Our Python DSP has the cleanest stems
  in the project: bandlimited pulse synthesis, proper analog LP,
  DC blocker.  User ear-confirmed ("all sounds amazing").
- **Sidesteps the non-linear mix problem.**  Because each stem is
  independently rendered through the DAC, REAPER's linear master-bus
  sum is approximately correct for each channel's contribution.
- **Parallelizable.**  `render_all_nsfs.py --jobs 6` cuts a 150-game
  rebuild from days to hours.  Each game is an independent
  subprocess.

**Cons**:

- **Static audio.**  Stems are pre-rendered WAVs.  You cannot play a
  MIDI keyboard into a WAV — there is no live synth in this path.
- **Approximation of hardware mix.**  The non-linear DAC formula has
  cross-terms between channels; rendering each channel alone and
  summing linearly loses the cross-channel compression.  Concretely:
  two pulses at vol 15 should produce 0.258 on hardware but our
  linear sum of stems produces 0.298 — ~15% too loud.
- **Disk-heavy.**  Stems are 5 × 180s × 44.1kHz × 2 bytes = ~16 MB
  per channel per song.  A full 150-game library with all songs is
  roughly 50 GB.
- **Rebuild from scratch whenever DSP changes.**  Anti-aliasing
  improvements, filter changes, etc. require re-rendering every
  stem.  ~1 day of compute on 6 parallel workers.

**Unsolved mysteries**:

- **The non-linear mix gap.**  Our stems sum linearly in REAPER but
  hardware mixes non-linearly.  `docs/RESEARCH_ANTIALIAS.md` §6
  describes the "2-bus-stem" architecture that would solve this
  (pulse pin + TND pin as two bus stems), but we haven't built it
  yet.

**Possible next steps**:

- **Implement 2-bus-stem rendering** (~2 hours).  Replaces our 5
  per-channel stems with 2 bus stems (pulse pin + TND pin), each
  rendered with the full non-linear formula before summing.  Linear
  master-bus sum then matches hardware exactly.  Loses per-channel
  fader control in REAPER; keeps MIDI tracks per-channel for
  editing.
- **Port Blargg's Blip_Buffer to numpy** (~1 day).  Replaces our
  analytical-integration pulse with proper BLEP anti-aliasing.
  Would eliminate the remaining ~14 pulse clicks/sec that survive
  our 4-pole LP.  See `docs/RESEARCH_ANTIALIAS.md` §2-4.

## Approach 4 — JSFX live synth

The `ReapNES_APU2_v2.jsfx` plugin runs in REAPER's audio engine at
sample rate, receiving MIDI events and producing audio in real time.
Implements a three-priority input cascade: SysEx register replay →
CC11/CC12 automation → ADSR keyboard mode.

**Pros**:

- **Live-playable.**  Plug in a MIDI keyboard; it responds.  This is
  the actual "playable NES synth" product.
- **MIDI file editable.**  Edit notes or CC automation in REAPER's
  piano roll; the JSFX plays the changes immediately.
- **Low latency.**  Sample-rate DSP inside REAPER's audio engine.
  Suitable for recording performances or streaming.
- **Animated UI.**  Sliders, knobs, and visualizations move in
  response to the audio.  Good for video recording (a primary
  product goal per `docs/SYNTHMERGE.md`).

**Cons**:

- **DSP divergence from Python stems.**  JSFX does NOT have the
  Python pipeline's bandlimited pulse (Rule 35), 14 kHz analog LP
  + DC blocker (Rule 33), or `$4015` noise gate (Rule 30).  Those
  gaps were intentional (optimized for libgme parity) but mean
  JSFX sounds grittier than stems on pulse-heavy, noise-heavy, or
  high-pitched content.
- **Non-linear mix CAN'T be done across multi-track JSFX.**  Each
  JSFX instance sees only its own channel's MIDI.  REAPER's master
  bus sums linearly.  Same ~15% overload bug as the stems, but from
  the other end.
- **Two DSP codebases to maintain.**  Python for stems, JSFX for
  live — diverging fixes are the norm, not the exception.
- **Not easily testable.**  JSFX runs inside REAPER; no headless
  test harness.  Every change requires opening REAPER to evaluate.

**Unsolved mysteries**:

- **Why does JSFX optimize for libgme parity while Python optimizes
  for DAW listenability?**  Historical accident — the JSFX was
  originally tuned against libgme frames via a spectrogram diff,
  while Python DSP evolved during 2026-04-18's focus on DAW ear-tests.
  Re-reconciliation is possible but requires a policy decision on
  which reference is authoritative.

**Possible next steps**:

- **Port Rule 35 to JSFX via polyBLEP** (~3-4 hours).  Gives live
  playback the same anti-aliasing quality as stems.
- **Port Rule 30 noise gate to JSFX** (~1 hour).  Fixes Nintendo
  drum "wash" in live playback.
- **Port Rule 33 14 kHz LP + DC blocker to JSFX** (~30 min).
  Smooths over per-note transient clicks.  Controversial (the
  existing JSFX comments say filters move away from libgme match —
  may need a user-switchable toggle).

## Approach 5 — Three-variant architecture (A/B/C)

Rather than pick stems-vs-JSFX up front, ship all three architectures
in parallel subfolders and let ear-testing decide.  See
`docs/EAR_LAB_00_INDEX.md`.

- `outputv6/` canonical — Python stems + MIDI tracks.
- `outputv6_A/` "Double Dose" — stems + JSFX together, both unmuted,
  user can solo either.
- `outputv6_B/` "Live Wire" — MIDI + JSFX only, no stems.  The
  playable-synth product.
- `outputv6_C/` "Ditto Head" — placeholder, will eventually be
  JSFX-rendered stems via ReaScript offline render.

**Pros**:

- **Deferred decision.**  Lets us ear-test three architectures
  without committing.
- **Each variant has a clear purpose.**  A = compare, B = play,
  C = archive.
- **Share infrastructure.**  All three use the same MIDI extraction,
  M3U naming, sidecar-based audit.

**Cons**:

- **Disk cost of A.**  Each A variant references 5 × 16 MB stems.
  Across 150 games this is ~50 GB just for the audio files.
- **Cognitive cost.**  Users need to understand what each variant is.
- **C is a placeholder.**  The ReaScript automation that would make
  C meaningful isn't built yet.

**Unsolved mysteries**:

- **Is B alone good enough to be the product?**  Under ear-test right
  now.  If yes, A and C become redundant and we delete the Python
  stems pipeline; if no, we keep A (archival) and build C properly.

**Possible next steps**:

- Build Option C's ReaScript offline render (~1-2 days).
- Once ear-test verdict is in, delete the loser variants to
  simplify.

## Approach 6 — CC11/CC12 automation as the MIDI envelope

Instead of approximating NES envelopes as ADSR on MIDI note events,
we capture per-frame CC11 (volume) and CC12 (duty) and write them as
MIDI controller automation.  The JSFX reads these back in real time.

**Pros**:

- **Preserves driver intent.**  Whatever the original sound engine
  did per frame — vibrato, tremolo, duty animation, volume ramps —
  is captured verbatim.
- **Edit-friendly.**  User can reshape a note's envelope by
  dragging CC automation in REAPER.
- **Driver-family agnostic.**  Works the same for Family 1 sparse
  envelopes and Family 4 dense animators.

**Cons**:

- **Lossy.**  Sub-frame effects (sweep modulation, phase reset
  timing, noise mode switches) don't survive the CC encoding.
  SysEx augments for this when both pipeline ends support it.
- **Bulky.**  A Family 4 dense-animator song can have 6-16 CC11
  events per note — tens of thousands of CCs across a 2-minute
  song.
- **JSFX interpretation sensitive.**  If the JSFX's CC-to-volume
  mapping is wrong by even one scale factor, the whole song plays
  at the wrong level.  (Rule 27 non-linear mix exposes this.)

**Unsolved mysteries**:

- **What's the right CC-to-NES volume mapping?**  We use
  `cc_value * 15 // 127`.  Some drivers use a 16-level volume
  lookup table instead; unclear whether that's musically audible.

**Possible next steps**:

- Consider MIDI pitch-bend or channel-aftertouch for sweep
  automation.  Currently lost in the CC encoding.

## Approach 7 — Driver family taxonomy (5-axis, code-identity)

Earlier work classified games by CC11/CC12 density into 4-5 "families"
(Hardware Envelope / Standard / Duty Animator / Dense).  The 2026-04-17
investigation expanded this to a **5-axis taxonomy** over 298 games:

1. Code-identity (same INIT fingerprint)
2. Envelope shape (hardware decay vs software writes)
3. Noise convention (`$4015` gate vs vol gate)
4. `$4017` frame-counter signature
5. Expansion audio pattern

This produces **~14 distinct driver codebases** across the NES
library, more granular than the old CC-density families.

**Pros**:

- **Matches reality.**  Two games can have identical CC density but
  totally different drivers; classifying by code identity catches
  this.
- **Predictive.**  If we know a game is "late Capcom 6C80" we can
  immediately predict its `$4015` behavior, envelope style, drum
  source, etc.
- **Enables parser reuse.**  Two games in the same code-identity
  family can share a parser (Mega Man 3/4 + Disney titles, for
  example).

**Cons**:

- **Not yet applied everywhere.**  The CC-density classification
  is baked into `driver_survey.py`; the 5-axis taxonomy lives in
  docs + `ANTIRIPPER/` metadata but hasn't replaced the older
  classification in the pipeline.

**Unsolved mysteries**:

- **Is family N equivalent across regional releases?**  We found CV3
  US (no VRC6) vs CV3 JP (VRC6) use visibly different drivers.
  How much of the library has region-specific driver differences?

**Possible next steps**:

- Merge the 5-axis data into `driver_survey.py` so the pipeline
  classifies every new game consistently.

## Approach 8 — Naming and audit pipeline

Shipped 2026-04-19 after the off-by-one bug.  Every song directory
now carries a `track.json` sidecar that is the single source of truth
for what NSF track the stems came from, what M3U position they
represent, and what name should be applied.  `audit_names.py`
classifies every song as `correct / rename_only / re_render_required /
truncated / ambiguous`.  `apply_repairs.py` applies deterministic
fixes — never destructive, never silent.

**Pros**:

- **Deterministic.**  Same inputs → same output.  No "it might be
  right" ambiguity.
- **Reversible.**  Renames logged to `_repair_log.json`; re-render
  list written to `_rerender_list.txt` before anything runs.
- **Self-verifying.**  Re-run audit after any repair to confirm
  zero issues remain.

**Cons**:

- **Requires sidecars everywhere.**  Pre-sidecar renders
  (pre-2026-04-19) classify as `re_render_required` even if they
  happen to be correct.  Conservative but costly.

**Unsolved mysteries**:

- **M3U labeling itself is often wrong.**  Zophar-ripped M3Us
  sometimes label NSF track 16 as "Battle Scene" when audio
  inspection reveals it's the Item Store.  Our audit flags the
  mismatch as `ambiguous` but can't resolve it without ground-truth
  listening.

**Possible next steps**:

- Integrate the M3U-vs-audio mismatch into a supervised ear-test
  flow where the user labels 2-3 tracks per game and the script
  auto-fills the rest by matching audio-fingerprint similarity.

# Known unsolved mysteries (collected)

Organized by impact on the product.

**Audibly affects playback**:
- Metroid Intro (NSF track 1) halts the py65 emulator.
- JSFX and Python stems sound different.  See Approach 4.
- Non-linear DAC mix is approximate at stem-sum level (~15% overload).

**Affects correctness but not audible today**:
- M3U track labels are sometimes wrong (community ripping errors).
- How does Castlevania drive noise drums without setting `$4015`
  bit 3?
- Region-specific driver variants (CV3 US vs CV3 JP) — how many
  games are affected?

**Interesting but not load-bearing**:
- Why does Kondo's SMB driver write `$4011 = 48` every frame?
- Why do some drivers use a 16-level volume lookup table vs a
  direct `vol * 15 // 127` scale?

# Roadmap

In rough priority order, based on what answers the biggest questions:

1. **Finish the current 150-game rebuild** (in progress) and run
   the full audit.  Close the off-by-one accountability loop.
2. **User ear-tests A/B/C variants.**  Decides whether we keep the
   Python stems pipeline, kill it for JSFX-only, or build Option C.
3. **If ear-test says "port more to JSFX"**: Rules 30/33/35 port,
   ~5-7 hours work.
4. **If ear-test says "bit-identity needed"**: build ReaScript
   offline render for Option C, ~1-2 days.
5. **2-bus-stem rendering** (~2 hours, low risk, high win).  Fixes
   the non-linear mix approximation regardless of variant choice.
6. **Metroid Intro investigation** (~1 day).  Likely reveals a
   general class of driver-hang bugs we should fix.
7. **Capcom 6C80 ROM parser** (~2 weeks).  Expands trusted-status
   games by ~40.
8. **Blargg Blip_Buffer port to numpy** (~1 day).  Archival-quality
   anti-aliasing.  Deferred until the above ship.
