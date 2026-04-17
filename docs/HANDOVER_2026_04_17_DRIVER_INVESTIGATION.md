# Handover — Driver & Chip Investigation Session (2026-04-17)

## Session goal

User priority: **learn what we still don't know about the NES sound chip
and driver families**. Not feature implementation — investigation and
knowledge encoding. Seven systematic passes against the 298-NSF,
321-extracted-game corpus.

## What was accomplished

### Implementation work (earlier in session, before investigation focus)
- **Expansion audio (VRC6 + FDS)** — 35 games, 768 songs now in MIDI/RPP
- **Non-linear APU mixing** — Console JSFX + render_wav now use impedance formulas
- **DPCM/DAC extraction** — 694 songs across 19 games, two mechanisms distinguished
- **Phase reset + $4015 + sweep capture** — extended `frames_to_channel_data()`

### Seven investigation passes

| Pass | Probe | Key finding |
|-----:|-------|-------------|
| 1 | Register behavior across 298 games | 5-axis taxonomy (envelope mode × length counter × phase reset × sweep × DMC) replaces 4-family CC-density model |
| 2 | Byte-level cluster validation | Behavioral clustering ≠ code identity. Only Capcom late 6C80 has 7-game code identity. |
| 3 | DMC sample inventory + VRC7 gap | Sunsoft uses few samples at many rates; Capcom late uses DPCM minimally; VRC7 captured but not encoded |
| 4 | Automatic driver clustering | 14 confirmed code-identity driver families covering ~38 games (87% have bespoke code) |
| 5 | Noise drum conventions + Gimmick! 5B | Period 3 canonical (29%); tonal noise essentially unused; Gimmick! uses 5B as 3 SW-envelope squares (not hardware envelope) |
| 6 | Envelope shapes + $4017 | Nintendo R&D convention triad: attack-swell + $4017-every-frame + env_loop modulation |
| 7 | Note durations + more publishers | Capcom early = 95% staccato; Uematsu wrote 3 different FF drivers; Tecmo has 4+ drivers; boilerplate correction |

## Key discoveries this session

### About the chip
1. **Triangle length counter is universally unused** — 0/298 games enable $4015 bit 2. All triangle gating via linear counter.
2. **const_vol bit 4 semantics** fully understood, with the dual-meaning bit 5 (env_loop when const_vol=0, length-counter-halt when const_vol=1).
3. **Tonal noise mode is essentially dead** — <1% of noise frames use short-LFSR mode across the whole library.
4. **NES APU uses impedance-based non-linear mixing** (formulas implemented in Rule 27).
5. **DMC is two mechanisms** ($4011 DAC writes vs $4012/$4013 sample triggers) — Rule 28.
6. **$4003/$4007/$400B writes cause phase reset** — Rule 29 drives same-pitch retriggers.
7. **$4017 write side effects**: frame counter reset + IRQ inhibit.

### About driver families
8. **14 confirmed code-identity driver families** in the library, covering ~38 games. 260 games have bespoke code per title.
9. **Capcom late 6C80** (7 games: MM3/4, Darkwing Duck, TaleSpin, Little Mermaid, Mighty Final Fight, Tenchi wo Kurau II) is the LARGEST code-identity cluster.
10. **Capcom has ≥5 distinct drivers**, Konami ≥3, Sunsoft ≥3, Tecmo ≥4, Nintendo R&D 0 (every title has its own codebase).
11. **Nintendo R&D convention triad**: attack-swell envelopes + $4017-every-frame + env_loop modulation per note. These three co-occur despite no shared code. Shared STYLE GUIDE, not shared code.
12. **Cross-publisher driver sharing exists** (After Burner/Tengen + Festers Quest/Sunsoft share play routine).
13. **Uematsu wrote different drivers for FF1/FF2/FF3** — Square rewrote the sound engine each title.
14. **Composer vs driver asymmetry**: MM3 and MM4 share byte-identical driver code but have DIFFERENT envelope shapes — the sound designer varied envelope within the same engine.

### Per-driver fingerprints measured
15. **Envelope shapes**: Nintendo has unique attack-swell; everyone else has attack-decay. MM4 near-legato; CV sharp percussive; Batman hump-shaped.
16. **Note durations**: Capcom early median 1 frame (95% staccato); Metroid median 42 frames (longest); Uematsu evolved from staccato to sustained.
17. **Noise drum palettes**: Nintendo uses 1-3 periods minimum, Capcom late 6C80 uses 5-8 periods maximum.
18. **DMC strategies**: Sunsoft uses FEW samples × MANY rates; Nintendo SMB3 uses MANY samples × few rates; Capcom late uses MINIMAL DPCM.

### Corrections and traps documented
19. **CC density is a proxy, not the real classifier** — it mislabels mixed-mode drivers.
20. **Behavioral clustering is looser than code-identity clustering** — shared CONVENTION ≠ shared CODE.
21. **$4000 = $00 (default) means silent, not HW envelope** — earlier "HW envelope dominant" count inflated.
22. **Byte `48a91f8d1540a900` is the standard APU init boilerplate**, NOT a driver signature. 8-byte-prefix clusters may include false positives.
23. **$4015 is NOT a per-note MIDI gate** — most drivers write it once at init with $00.

## Where the knowledge lives now

### Code
- `scripts/nsf_to_reaper.py` — VRC6/FDS/DMC extraction, phase reset tracking, $4015 capture, sweep capture, non-linear mixing
- `scripts/generate_project.py` — expansion tracks in RPP
- `scripts/generate_site.py` — expansion + DMC descriptions
- `scripts/register_analysis.py` — per-game register behavior stats
- `scripts/probe_driver_signature.py` — 32-byte init signature clustering
- `scripts/probe_driver_clusters.py` — behavioral cluster validation via byte matching
- `scripts/probe_dmc_inventory.py` — DPCM sample cataloging
- `scripts/auto_driver_clusters.py` — automatic cluster discovery (no hypotheses)
- `scripts/probe_noise_patterns.py` — per-driver noise period distributions
- `scripts/probe_gimmick_5b.py` — 5B register protocol decoder
- `scripts/probe_envelope_shapes.py` — post-attack volume curves
- `scripts/probe_note_durations.py` — duration distribution analysis

### Data
- `data/register_analysis.json` — 321-game register behavior dump
- `data/family_census_v2.json` — 271-game CC density census (earlier)
- `data/expansion_audit.json` — 297 NSFs expansion flag audit

### Rules (loaded into every session)
- `.claude/rules/architecture.md` — Rules 1-29 including:
  - Rule 26: NSF bankswitch emulation (2 bugs)
  - Rule 27: Non-linear APU mixing is mandatory
  - Rule 28: DMC is two mechanisms, not one
  - Rule 29: Phase reset + $4015 + sweep events
- `.claude/rules/synth_fidelity.md` — Rule 7: Non-linear mixing formulas with implementation status
- `CLAUDE.md` — driver families section cross-references `NES_AUDIO_FINDINGS_2026_04_17.md`

### Oracle (queryable via `get_preflight_context`)
- **52+ hardware facts** tagged `parser,synth,routing` so they surface on any task type
- **12+ prevention patterns** across parser/routing/synth subsystems
- **4+ decision records** (system_wide taxonomy revisions, VRC7 gap, DMC implementation)

### Docs
- `docs/NES_AUDIO_FINDINGS_2026_04_17.md` — **THE comprehensive investigation report** covering all 7 passes with tables, behavior maps, and examples
- `docs/NES_AUDIO_GAPS_AND_NEXT_STEPS.md` — updated, sections 2.2/2.4/2.7/4.4 marked IMPLEMENTED
- `docs/MULTI_CHIP_SCHEMA.md` — Section 3 has IMPLEMENTATION STATUS header

## What's still unexplored

### Easy wins with existing data
- **Triangle linear counter value distributions** per driver family (would reveal decay-time preferences)
- **Phase reset / tempo correlation** — are phase resets locked to beat boundaries? Could derive BPM.
- **The 13 "fuzzy zone" games** (CC12 0.3-0.7) still need classification using our new tools
- **Publisher coverage extension** — sample more of Jaleco, Natsume, Hudson, SNK, etc.

### Requires new implementation work
- **VRC7 FM patches** — 3 games (Lagrange Point, Tiny Toon Adventures 2 Montana, others). Register capture works but no MIDI emission. Needs YM2413 register decoding + FM patch schema + non-CC11/CC12 MIDI mapping.
- **5B parsing for Gimmick!** — pass 5 mapped the strategy (direct-volume mode, 3 squares, fine period only). Implementation is ~30 LOC similar to VRC6.
- **Sweep unit effective-period calculation** — currently captured but not applied to MIDI pitch. Sunsoft games would benefit significantly.
- **Early Capcom driver sub-cluster identification** — MM1/MM2/BC/Gun.Smoke all differ. Exhaustive hex comparison would map them all.

### Pipeline gaps known but unaddressed
- **Cross-validation pipeline** — no auto-compare NSF vs VGM logs vs NES-MDB (the `scripts/cross_validate.py` never built)
- **Capcom 6C80 ROM parser** — highest-ROI next parser per older docs, not built

## How to pick up the work

### Session-start preflight
```python
from ANTIRIPPER.agent_oracle import AgentOracle
oracle = AgentOracle()
# For any specific game:
ctx = oracle.get_preflight_context("<game_slug>", "nsf_extraction")
# For synth/JSFX work:
ctx = oracle.get_preflight_context("<game_slug>", "synth_fidelity")
```
This will surface the 52+ hardware facts + 12+ prevention patterns automatically.

### To re-run any investigation pass
All probe scripts are self-contained and work against existing extracted MIDIs.
```bash
python scripts/register_analysis.py --json data/register_analysis.json
python scripts/auto_driver_clusters.py
python scripts/probe_note_durations.py
python scripts/probe_envelope_shapes.py
```

### Default priority order if no specific request
1. **Triangle linear counter value distributions** — cheapest next probe, completes the APU register analysis
2. **Classify the 13 fuzzy-zone games** — use new envelope shape + note duration tools
3. **Phase reset / tempo correlation** — would derive per-game BPM
4. **VRC7 register parsing** — 3 games gain FM synthesis in MIDI output
5. **5B parsing for Gimmick!** — 1 game, legendary music, ~30 LOC

## Recent commits (newest first)

```
f6fbc09d Driver investigation pass 7: note durations + Tecmo cluster + boilerplate
1ceee7b9 Driver investigation pass 6: envelope shape fingerprints + $4017 Nintendo signature
507790ca Driver investigation pass 5: noise conventions + Gimmick! 5B deep dive
56992780 Driver investigation pass 4: automatic cluster discovery (14 code-identity)
f451f1f5 Driver investigation pass 3: DMC sample inventories + VRC7 pipeline gap
d9080193 Driver investigation pass 2: behavioral != code identity
e1263f08 Driver & chip investigation pass 1: 5-axis taxonomy
0e632c90 Phase reset + $4015 + sweep capture
ece60e91 DPCM/DAC extraction: 694 songs across 19 games
87c713f4 Non-linear APU mixing implementation
e7e6037a Expansion audio: VRC6 + FDS (35 games, 768 songs)
```

## If you're starting fresh on NSFRIPPER without knowing anything

Read these in order:
1. `CLAUDE.md` — project overview, driver families table, cross-reference index
2. `.claude/rules/architecture.md` — Rules 1-29 (core invariants)
3. `docs/NES_AUDIO_FINDINGS_2026_04_17.md` — this session's investigation findings
4. `docs/NES_AUDIO_GAPS_AND_NEXT_STEPS.md` — what's still open
5. `docs/AGENT_ORACLE.md` — how to query institutional memory

Then run a preflight on any game to see the facts/patterns the oracle surfaces.
