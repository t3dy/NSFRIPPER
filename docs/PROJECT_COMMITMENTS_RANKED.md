# Project commitments, ranked

What the project has committed to — architecturally, philosophically,
operationally — with honest ranking by confidence, evidence, and
value.  "Commitment" here means a path we've chosen that would be
expensive to reverse.

Ranking dimensions:
- **Confidence** — how sure are we this was right?  (Low / Med / High)
- **Evidence** — what proves it works?  (anecdotal / measured /
  ear-tested across games)
- **Reversibility** — how hard to undo?  (low = easy to remove;
  high = rip everything out)
- **Value** — does this live up to its cost?

## Tier S — load-bearing commitments, vindicated by use

### 1. Frame IR as the canonical representation

**What**: raw `$4000-$4017` register state per 60 Hz frame is the
canonical data format.  All downstream (MIDI, stems, JSFX) is
projection.

**Confidence**: High.  Rule 9 & Rule 12 of architecture.md.  Every
major extraction issue traces back to either "we skipped Frame IR"
or "we had the wrong Frame IR".

**Evidence**: 200+ games extracted correctly via this representation.

**Value**: Load-bearing.  Without it, no fidelity, no validation,
no audit pipeline.

**Would I commit again?**: Unconditionally yes.

### 2. Trust hierarchy (Mesen trace > NSF emu > Frame IR > MIDI > synth)

**What**: explicit ordering of data sources by fidelity with
rules for when to use which.

**Confidence**: High.  Every fidelity-validation bug (Mario, SMB)
is because we demoted a higher layer or promoted a lower one.

**Evidence**: 3 trace-validated games (CV1, Contra, W&W) act as
anchor points; many NSF games validated against Mesen.

**Value**: prevents overclaiming.  Makes it explicit that
"NSF emulation output" is hypothesis, not truth.

**Would I commit again?**: Yes.

### 3. Non-linear APU mixing (Rule 27)

**What**: Rule 27 applied across Python stems, JSFX, WAV renderer.
Impedance-based mix formula.

**Confidence**: High.  Ear-tested multiple games (user confirmed
"all sounds amazing" after it landed).

**Evidence**: spectral match vs libgme within 1.3 dB on all bands.
Ear-test confirmation.

**Value**: the difference between "too loud and muddy" and "sounds
like the game."

**Would I commit again?**: Yes, but the stem-level approximation
(linear sum of per-channel stems) is a known ~15% overload that
still needs the 2-bus-stem fix.

### 4. Architectural Rules 34-36 (triangle gate-off, bandlimited pulse, NSF init)

**What**: three 2026-04-18 rules that collectively eliminated the
majority of click/pop/distortion artifacts.

**Confidence**: High.  Ear-tested and DSP-validated.

**Evidence**: triangle max-step 0.386→0.006 on Battletoads.  User
"sounds a lot better."  Noise drums restored on 30% of games via
Rule 36.

**Value**: the difference between "painful to listen to" and
"archival-quality."

**Would I commit again?**: Yes.

## Tier A — good commitments with caveats

### 5. Stems pipeline (Python DSP → WAV → REAPER audio tracks)

**What**: Python renders per-channel audio stems that REAPER loads
as audio tracks.

**Confidence**: Medium-High.  Solved the non-linear-at-master-bus
problem that JSFX-multi-track couldn't.

**Evidence**: ear-test confirmed.  Archival quality.

**Value**: high for archival; **zero for live keyboard play**.
Static WAV cannot respond to MIDI input.

**Caveat**: if user's primary goal is live-play, this whole path
is a detour.  See `docs/SYNTH_VS_SCRIPTS.md`.

**Would I commit again?**: As the archival path, yes.  As THE
product, no — we'd skip to JSFX-only.

### 6. JSFX three-priority input cascade (SysEx > CC > ADSR)

**What**: the live-play plugin's input-mode hierarchy that lets
file playback (SysEx) and keyboard (ADSR) coexist in one project.

**Confidence**: High (design).  Medium (implementation) — ADSR
mode's sound doesn't yet match Python-stem quality.

**Evidence**: Rule 34 port to JSFX proves the model.  Need Rules
30/33/35 ported to reach parity.

**Value**: enables the "playable synth + file playback" product
vision.

**Would I commit again?**: Yes.  Best known design for the
use case.

### 7. NSF emulation via py65

**What**: pure-Python 6502 emulator as the canonical NSF runtime
for automated batch extraction.

**Confidence**: Medium.  It works but we fought it all week.

**Evidence**: Rules 26, 36 + silence/stuck threshold tuning all
traced back to py65 quirks.  Metroid Intro still hangs.

**Value**: medium.  The alternative (spawning libgme via CLI)
would be faster and more faithful but harder to instrument.

**Would I commit again?**: Possibly.  A Rust port with libgme
bindings would be better long-term.

### 8. M3U as the music-track filter

**What**: community-ripped M3U files filter NSF tracks to music-
only, provide names + durations.

**Confidence**: Medium.  M3U is sometimes wrong.  We trust it;
the user trusts it with caveats.

**Evidence**: 150 games' M3Us work for their nominal purpose.
Several have label errors (Ghosts 'n Goblins, FF1 "Battle Scene").

**Value**: high.  Without M3U, we'd render SFX + blank banks as
"songs."

**Would I commit again?**: Yes, but I'd add audit tooling (we
did — `scripts/audit_names.py`).

### 9. ANTIRIPPER oracle DB for institutional memory

**What**: SQLite DB tracking attempts, claims, hardware facts,
decision records, prevention patterns.

**Confidence**: Medium.  Good instinct, under-used.

**Evidence**: 1163 evidence items, 522 decision records, 80
hardware facts.  But 0 claims ever entered — hypothesis tracking
never adopted.

**Value**: medium.  Rules and docs carry most weight; DB is
supplementary.

**Would I commit again?**: Yes, but I'd refactor the schema per
`docs/CRITIQUE_OF_SYSTEM_FILES.md` recommendations.

## Tier B — defensible but disputable commitments

### 10. Five-family driver taxonomy (CC11/CC12 density)

**What**: 4-5 families sorted by per-note CC event density.

**Confidence**: Low-Medium.  Empirically useful but not a complete
model of driver behavior.

**Evidence**: 271-game census shows meaningful clustering.  But
the 5-axis code-identity taxonomy (April 17) reveals ~14 families,
not 4-5.

**Value**: adequate for selecting JSFX presets; inadequate for
research-grade classification.

**Would I commit again?**: Only as a legacy label.  The 5-axis
taxonomy is the real classification.

### 11. CC11/CC12 MIDI encoding

**What**: volume via CC11, duty via CC12.

**Confidence**: Medium.  Portable and editable but lossy.

**Evidence**: works in REAPER + our JSFX.  Loses sweep, noise
mode, phase reset, DMC details (all now live in SysEx).

**Value**: high for editability; low for hardware fidelity.

**Would I commit again?**: Yes, paired with SysEx augmentation.

### 12. Generated output mirrored in git

**What**: used to commit `output/*/midi/*.mid` and similar
generated artifacts.

**Confidence**: Low.  Caused repo bloat, 58 MB of deletions
this commit.

**Evidence**: git history ballooned; gitignore was updated
2026-04-19.

**Value**: past negative.  Now properly gitignored.

**Would I commit again?**: No — that's why we changed it.

## Tier C — commitments under active challenge

### 13. Three-variant architecture (A/B/C)

**What**: ship outputv6_A (stems+JSFX), outputv6_B (JSFX only),
outputv6_C (placeholder) simultaneously.

**Confidence**: Low.  Exploratory; awaiting ear-test.

**Evidence**: 10 games' variants generated; user ear-test
pending.

**Value**: unknown until ear-test.  May collapse to just B after
feedback.

**Would I commit again?**: Depends on ear-test outcome.

### 14. Rendering at 180s cap per song

**What**: songs capped at 180 seconds regardless of M3U duration.

**Confidence**: Low.  Arbitrary.

**Evidence**: few songs are longer than 180s anyway.  But some
RPG music (FF3, DQ4) has 3-4 minute tracks getting cut.

**Value**: disk-space win of ~50% vs no cap.

**Would I commit again?**: Only after checking every M3U for
songs >180s.

### 15. Parallel rebuild via `--jobs 6`

**What**: multi-process rendering pipeline.

**Confidence**: Medium.  Works, but introduces ordering
inconsistencies (logs interleave).

**Evidence**: ~6x speedup confirmed.

**Value**: high.  Without it, 150-game rebuild is unusable.

**Would I commit again?**: Yes, with better log handling.

## Tier D — commitments we should probably revisit

### 16. 106 docs in a flat `docs/` directory

**What**: everything we've written, piled up.

**Confidence**: Low.  Organically grown, now unwieldy.

**Evidence**: search for any concept returns 3-5 docs, most
partially stale.

**Value**: negative over time.  Friction exceeds benefit.

**Would I commit again?**: No.  Needs reorg per
`CRITIQUE_OF_SYSTEM_FILES.md`.

### 17. 8 always-loaded rule files

**What**: `.claude/rules/*.md` all loaded every session.

**Confidence**: Low.  Too much ambient context.

**Evidence**: contextual drift; rules occasionally contradict
when not all reconciled at once.

**Value**: neutral — needed rules are load-bearing; unneeded
rules waste context.

**Would I commit again?**: No.  Split into "always-load" (~6
rules) vs "lookup-on-demand" (~30 rules).

### 18. ANTIRIPPER DB unchanged schema for entire project

**What**: kept `evidence_items`, `claim_evidence_links`, etc. as
designed v1.

**Confidence**: Low.  Schema shows its age.

**Evidence**: `claims` is 0 rows; junk-drawer `evidence_items`.

**Value**: would be much higher after the schema-v3 refactor
described in `CRITIQUE_OF_SYSTEM_FILES.md`.

**Would I commit again?**: No — would design schema v3 from day
one.

## Meta-commitments (things we've implicitly committed to)

- **"Honest failure accounting"** — every mistake gets baked into
  MISTAKEBAKED.md, memory entries, or architecture rules.  High
  confidence this pays off.  High value.  Yes commit again.

- **"No overclaiming"** — no "fixed" until user ear-confirms.  User
  feedback rule.  High confidence, high value.

- **"Trace is truth"** — when available.  High confidence, limited
  applicability (only 3-4 games have traces).

- **"Stems pipeline as primary"** (MEMORY.md "project_stems_default")
  — committed 2026-04-18.  **Under challenge** as of this session
  because stems don't enable live MIDI keyboard.  May demote.

## Strategic reading

The top commitments (1-4) are solid and vindicated.  The middle
tier (5-9) has active tension — the stems vs JSFX fork is the big
one.  The bottom tier (10-18) accumulates the kind of technical
debt any 3-week-old project has; none urgent individually, but
worth a clean-up pass before this becomes a public release.

**The decision that matters most right now**: whether stems
(commitment #5) stays primary or yields to JSFX-only.  That
decision is blocked on ear-test of A/B/C variants.  Everything
else is secondary to that answer.
