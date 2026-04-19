# Critique of system files and database ontology + what you really want

Direct, unsparing look at the current state of your system files
(`.claude/rules/*.md`, `CLAUDE.md`, the 106 files in `docs/`) and
your ANTIRIPPER oracle DB schema, followed by a clearer statement of
what a Nintendo-music-hacking knowledge base should actually contain.

## Inventory

### System files (.claude/rules/)

8 files, all markdown, all treated as "always load" context.  Total
~60-80 KB of prose loaded every session:

- `architecture.md` — 36 numbered rules (Rules 1-36).  Load-bearing.
- `session_protocol.md` — working order, oracle workflow, gates.
- `reaper_projects.md` — RPP generation rules.
- `synth_fidelity.md` — synth CC/SysEx semantics.
- `jsfx_deploy.md` — shipping discipline.
- `new-game-parser.md` — checklist.
- `debugging-protocol.md` — debug order.
- `output-versioning.md` — file naming.

### CLAUDE.md

One big project guide file.  Re-states the primary goal, lists
commands, lists driver families, hands off to rule files.  ~9 KB.

### docs/

106 files.  Many are session artifacts that never got cleaned up:
`FIXINGMARIO1.md`, `HACKINGMARIOWEB.md`, `BATTLETOADS_SESSION_BLOOPERS.md`,
`HANDOVER_2026_04_14_S415.md`, `HANDOVER_2026_04_14_S416.md`,
`HANDOVER_2026_04_14_FINAL.md`, `HANDOVER_2026_04_14.md`, …

### ANTIRIPPER oracle DB

Schema:
- `attempts` (8 rows) — risky changes logged
- `claims` (0 rows) — hypotheses.  Never populated.
- `evidence_items` (1163 rows) — file paths, metrics, observations
- `hardware_facts` (80 rows) — immutable behavior entries
- `prevention_patterns` (37 rows) — learned failure modes
- `driver_families` (5 rows) — the old CC-density classification
- `decision_records` (522 rows) — extraction-route choices per game
- `concept_bridges` — unused?
- `synth_patches` — unused?
- `claim_evidence_links` — index only; no claim data to link

## Critique

### 1. System files carry too much identically-weighted rule material

36 architecture rules are "always load."  Many of them are
code-adjacent and should live in code comments instead.  Rule 5
("triangle is 1 octave lower") is a one-liner fact that belongs in
the pitch-computation function's docstring, not in every session's
context window.

**The rules that MUST be always-loaded are maybe 8-10**:

- Observed/Intent/Projection (Rule 12).
- Frame IR is canonical (Rule 9).
- Trust hierarchy (fidelity ladder).
- Triangle octave (Rule 5).
- Don't overclaim (feedback memory).
- Delivery gates.

The other 25+ rules are look-up-when-relevant material, not
ambient-background material.  Loading them costs context window
that could be used for the actual work.

### 2. Documentation is stratified by session, not by topic

106 docs in one flat directory is not organized.  Reading through
them you find:

- Pipeline rules (good)
- One-off debug narratives (should be compressed)
- Duplicate explanations of the same thing (one topic, 3 docs)
- Session handovers (should rotate out after 1-2 weeks)

The user experience is "search for something, find 5 related docs,
each partially right, each partially stale."

**What should exist**: a 2-level structure with a canonical doc
per topic, plus an `archive/` for session narratives older than
~1 month.

### 3. The oracle DB schema is powerful but under-used

80 hardware facts and 37 prevention patterns are great.  They
crystallize what would otherwise be lore.  But:

- `claims` has 0 rows.  The hypothesis-tracking table is unused.
  This means we have no structured record of "X might be true;
  we'll know after Y test."  Without it, hypotheses live as free
  text in handovers and get lost.
- `concept_bridges` and `synth_patches` appear unused.  If so,
  delete or populate.
- `driver_families` has 5 rows — the old CC-density classification.
  The 5-axis code-identity taxonomy from 2026-04-17 has ~14
  families; those aren't in the DB yet.
- `evidence_items` at 1163 rows is informative but unstructured;
  it's a junk drawer.  Needs tighter schema or better tagging.
- Per-game `decision_records` at 522 rows is appropriate for 321
  games — but 1.6 per game average.  Games with complex histories
  (CV1, Battletoads) need many more; the schema doesn't encourage
  that.

### 4. Game-level identity is weakly modeled

The DB keys games by slug.  But:
- CV3 US and CV3 JP are different drivers, different output.  One
  slug per region, or a region-qualified key?
- Different NSF rips of the same game (Zophar vs Nintendo Sound
  Format Collection vs community redumps) can have different track
  orderings.  Our DB doesn't encode "which rip" in any row.
- M3U playlists are a project-external authority (community-ripped)
  that we sometimes trust for labels.  The DB doesn't track which
  M3U was the source-of-truth for a given decision.

### 5. Mixed abstraction levels in the same table

`evidence_items` contains everything from `"trace captured 1792
frames"` to `"CC12 density for Mega Man 3 is 0.08"` to `"parser
returned 47 notes"`.  These are different KINDS of evidence that
should be typed more richly.

### 6. No cross-project reuse / foreign-key discipline

`hardware_facts` is hardware truth, independent of any game.  But
some hardware facts ARE driver-specific ("Capcom late driver uses
env_loop=0 convention").  Mixing these two concepts in one table
loses the distinction.

### 7. Session-scoped state leaks into global

`decision_records` has 522 rows, each a per-game route decision.
Some are outdated (pre-fix choices).  No "supersedes" column,
no timestamp-aware querying.  Risk: a 3-month-old decision gets
treated as current.

## What you really want in a Nintendo music hacking KB

Based on what the project is actually doing — NES audio extraction,
live-play, driver analysis — and what the current DB falls short
on:

### Core entity: the NES song identity

Not a game slug.  A triple: **(game, region, NSF rip, song number)**.
Each combination is a distinct thing.  All per-song metadata hangs
off this.

```
song {
  id: INTEGER,
  game_slug: TEXT,          -- "Castlevania_3"
  region: TEXT,             -- "US" or "JP" or "PAL"
  nsf_hash: TEXT,           -- SHA256 of the NSF file
  nsf_track: INTEGER,       -- 1-indexed NSF track number
  m3u_position: INTEGER,    -- position in the M3U if any
  m3u_label: TEXT,          -- name per the M3U
  canonical_title: TEXT,    -- what it IS (user + research)
  ...
}
```

### Driver family as first-class

Not a free text string.  A real entity:

```
driver_family {
  id: INTEGER,
  name: TEXT,               -- "Capcom_Kondo_early"
  code_fingerprint: TEXT,   -- INIT signature
  $4015_strategy: TEXT,     -- "continuous_refresh" vs "init_once"
  envelope_mode: TEXT,      -- "hardware_decay" vs "software_vol"
  noise_strategy: TEXT,     -- "length_counter" vs "vol_gate"
  dmc_usage: TEXT,          -- "dac_writes" vs "dpcm_samples" vs "both"
  ...
}
```

And games are `(song, driver_family)` with confidence levels.

### Research artifacts typed explicitly

Today's `evidence_items` is a junk drawer.  Replace with:

```
measurement {        -- things we MEASURED
  id,
  subject_type,      -- "song", "driver_family", "register"
  subject_id,
  metric,            -- "cc12_density", "pulse1_peak_vol", "hz_range"
  value_numeric,
  value_text,
  method,            -- which tool/emulator/ear
  date
}

observation {        -- things we NOTICED, not formal metrics
  id,
  subject_type,
  subject_id,
  kind,              -- "bug", "quirk", "curiosity"
  text,
  date
}

hypothesis {         -- things we THINK are true, unverified
  id,
  claim_text,
  predicted_test,    -- how to prove/disprove
  status,            -- "open", "verified", "rejected"
  date
}
```

### Lineage / history on every row

Every fact should carry:
- `added_date`
- `last_verified_date`
- `superseded_by` (optional FK to a newer row)
- `source_tool_version` (which emulator, which pipeline version)

So you can always answer "was this true as of April 14?"

### Cross-layer tagging

Following the HYGIENE.md discipline: every claim should tag which
abstraction layer it lives at:

```
claim_layer: ENUM(
  "hardware",        -- physical chip behavior
  "register",        -- $4000-$4017 level
  "frame_ir",        -- our canonical per-frame state
  "midi",            -- downstream CC + SysEx + notes
  "stems_audio",     -- Python-rendered WAVs
  "jsfx_audio",      -- real-time JSFX output
  "analog_out"       -- real-hardware post-RC-filter
)
```

A fact's layer determines what evidence is valid for it, and what
other layers it constrains.

### Playable-synth-specific additions

Because the primary goal is live keyboard play, add:

```
preset {
  id,
  driver_family_id,
  approach,           -- "jsfx_adsr", "chipsounds", ...
  json_params,
  calibration_song,   -- reference song it was tuned against
  tester_verdict      -- "matches", "approximates", "misses"
}

experiment {
  id,
  preset_id,
  keyboard_id,
  test_game,          -- what we tried to play
  overall_rating,
  notes
}
```

This is what `keyboard_lab/db/keyboard.db` is already starting to
do — but ideally MERGED with the oracle DB so a `song` row links
to the `preset` rows that work for it.

### Drop things that aren't load-bearing

- `concept_bridges` — unclear purpose, unused.
- `synth_patches` — unused.  If needed, resurrect with real schema.
- Free-text evidence_items — replace with typed measurement /
  observation / hypothesis.
- Session handover files older than 2 months — archive, don't load.

## Proposed refactor in three phases

### Phase A — Hygiene pass (1 day)

- Move session narratives to `docs/archive/` (one dir per month).
- Consolidate duplicate topic docs; leave a single canonical doc
  per topic.
- Remove 15-20 rules from "always load" set; leave them as
  look-up-when-relevant.

### Phase B — DB schema v3 (2-3 days)

- Create new tables: `song`, `driver_family_v2` (with 5-axis
  fields), `measurement`, `observation`, `hypothesis`, `preset`,
  `experiment`, `claim_layer`.
- Write migration from `evidence_items` + `decision_records` +
  `hardware_facts` into new shape.  Much content is re-typeable
  automatically; some needs human review.
- Keep old tables as `*_v1` for transition.

### Phase C — Cross-index + validation (2-3 days)

- Build audit script: every `song` has at least one `driver_family`
  association.  Every `driver_family` has ≥3 songs as examples.
  Every `measurement` has a citation.
- Add a "freshness" view that flags rows older than N months
  without re-verification.
- Cross-link `keyboard_lab` DB to `ANTIRIPPER_v3` via `song_id` FK.

## Net recommendation

- The system files are doing their job but carry too much ambient
  weight.  Trim to ~10 essential rules; move the rest to
  referenceable tech-spec docs.
- The docs folder is chronologically organized; it needs a topical
  reorg.
- The ANTIRIPPER DB is the right instinct but under-used and
  under-typed.  The three-table refactor above would turn it from
  a junk drawer into a real knowledge base.
- The keyboard_lab DB should merge with the main KB rather than
  grow in parallel — once the main KB is cleaned up.

None of this is urgent.  But if the project's going to live long
enough to cover the full NES library and turn into a releasable
product, doing Phases A-C at some point will save more time than
it costs.

The current state is "works, but shows its seams."  That's fine for
a research project.  For a product, it'd need this refactor pass.
