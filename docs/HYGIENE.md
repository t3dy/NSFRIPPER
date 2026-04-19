# HYGIENE — context engineering for a multi-layer hardware knowledge base

This is the same "data problem" as `docs/UNDERSTANDING_THE_CHIP.md`,
seen through the lens of context engineering: how does a human or an
AI agent carry a coherent model of the NES chip across hours or
weeks of conversation and still end up in the right layer of
abstraction for whatever task is in front of them?  Context hygiene
is the answer.  This doc names the specific hygiene moves that keep
the project from drifting into confusion.

## The problem in one sentence

**Any given claim about "the chip" is true at one layer and false or
nonsense at another.**  Without explicit layer tracking, long
conversations about hardware slowly misalign — a question about
register behavior gets answered with analog-output intuition; a
question about audio grit gets answered with emulator state.  Both
participants think they agree; they don't.

## The layers we operate at (reprise)

From `UNDERSTANDING_THE_CHIP.md`:

1. Physical hardware (transistors, RC filter).
2. Register state ($4000-$4017 at an instant).
3. Register write sequence (CPU-timed stream).
4. Per-frame snapshot (60 Hz VBlank view).
5. Per-channel digital output.
6. Analog DAC sum (non-linear mix, pre-filter).
7. Analog-filtered output (post-14 kHz RC).

Seven layers.  A casual conversation can drift through all of them
in a minute.  Context hygiene means every claim gets tagged — even
implicitly — with which layer it applies to.

## Hygiene moves we use

### Move 1 — Explicit pipeline stage naming

We name the pipeline stages:

- `trace` → Mesen APU capture
- `frame_ir` → our per-frame register state canonical form
- `midi` → CC + SysEx + note events
- `stems` → per-channel WAV
- `jsfx` → real-time plugin output
- `master` → linear sum in REAPER

When someone says "the noise sounds wrong", we ask: wrong where?
trace level (emulation bug)?  frame_ir (capture bug)?  stems
(rendering bug)?  jsfx (live-play bug)?  master (mix bug)?  Each
has different diagnostic tools.

### Move 2 — Architecture Rules that embed their layer

Every Rule in `.claude/rules/architecture.md` implicitly specifies
its layer:

- Rule 26 (bankswitch) → layer: trace/emulation.
- Rule 27 (non-linear mix) → layer: stems (audio).
- Rule 30 (noise $4015 gate) → layer: frame_ir (state capture) AND
  stems (rendering).
- Rule 34 (triangle gate-off) → layer: stems AND jsfx.
- Rule 35 (bandlimited pulse) → layer: stems only.
- Rule 36 (NSF init) → layer: trace/emulation.

A Rule is a cross-reference between layers where behavior must be
consistent.  Documenting which layers a Rule spans is context
hygiene.

### Move 3 — Validation ladder

The validation ladder (docs/VALIDATION_REFERENCE.md) assigns trust
levels by which layer was compared:

- Rung 1 (structural) — parser produced output, no comparison.
- Rung 2 (frame_ir validated) — Frame IR matches trace.
- Rung 3 (MIDI validated) — MIDI playback matches trace.
- Rung 4 (audio validated) — audio matches reference.
- Rung 5 (ear-tested) — human confirms.

Promoting claims up the ladder forces cross-layer validation.
Refusing to claim higher rung than evidence supports is the hygiene
move.

### Move 4 — Memory file "type" system

Per `auto memory` docs: every memory entry is typed as `user` /
`feedback` / `project` / `reference`.  This is context hygiene
applied to memory: a given piece of knowledge only fires in the
right layer of conversation.  If the user says "all sounds
amazing", that's a `feedback` about Rules 34-36 validated together
— distinct from a `project` entry about the current rebuild state.

### Move 5 — Never conflate Observed / Intent / Projection

Rule 12 of architecture.md, explicitly a hygiene rule:

- **Observed** (ground truth): raw APU registers.  Authoritative.
- **Intent** (parser interpretation): Frame IR.  HYPOTHESIS.
- **Projection** (output): MIDI / RPP / synth.  PROVISIONAL.

Any claim about "what the game does" must declare which layer it
operates at.  "Battletoads' drum sound" as Observed = a specific
register sequence.  As Intent = a MIDI-editable note at note 38
velocity 96.  As Projection = a WAV rendered from the stems
pipeline.  They are THREE different things.

## Common hygiene failures we've seen

### Failure 1 — The "it sounds like" trap

User reports "Castlevania sounds noisy."  Layer?  Stems playback?
JSFX live?  Master bus?  Their memory of the original game?  Until
we pin it, we're fighting air.  Our fix: re-render to
`outputv6/_diag_<game>/` before proposing changes (feedback memory:
"Diag-render first").

### Failure 2 — Inferring one layer from another without checking

"This NSF doesn't loop, so the driver must be broken."  Maybe.  Or
maybe our py65 hits stuck_count.  Or maybe silence_threshold fires.
Or maybe the M3U says it's a short song and we're capping.  Fix:
check each layer before concluding.

### Failure 3 — Stale model of the chip

NES wiki says "triangle sequencer holds its position when gated
off."  Our code says "triangle output = 0 when gate closed."
Different layers — the wiki talks about the DAC, our code about the
rendered wave.  Rule 34 fixed the mismatch.  Hygiene move: verify
the wiki's layer before coding against it.

### Failure 4 — Taking "the ROM" as monolithic

CV3 US has no VRC6; CV3 JP does.  "The Castlevania 3 driver" is
meaningless without a region suffix.  Similarly, Dragon Warrior vs
Dragon Quest (same driver, different ROM).  Hygiene: always tag
region when discussing a specific game's behavior.

### Failure 5 — Documentation drift

Rules added to architecture.md in one session don't propagate to
oracle DB entries, MISTAKEBAKED.md, or code comments in one pass.
For weeks, a claim can be "true in the rule file but old in the
code."  Fix: Knowledge Hardening protocol (CLAUDE.md) enforces
multi-location updates.

## The context-hygiene axioms

These are the rules we've baked in over the project's lifetime.  Each
is an ounce of prevention against a pound of confusion.

### Axiom 1 — State your layer

Any claim about the chip names the layer it applies to.  "At
frame_ir, the noise gate requires $4015 bit 3."  Not just "noise
needs $4015."

### Axiom 2 — Honor provenance

Register-state claims must cite source: Mesen trace, py65 emu,
libgme output, NESdev wiki, or direct hardware measurement.  Each
source has known errors; naming the source protects against
miscitation.

### Axiom 3 — Validate cross-layer

Before promoting a claim (from hypothesis to trusted), show it
holds at more than one layer.  Rule 12 enforces this.

### Axiom 4 — Reversibility

Every data transformation we apply should be reversible or
explicitly documented as lossy.  Frame IR is reversible to register
writes.  CC encoding from Frame IR is LOSSY and we note where.
MIDI → audio is lossy by design.  Knowing what's lossy is hygiene.

### Axiom 5 — One canonical form

Frame IR is the canonical Observed representation.  All other forms
are projections of it.  There is one authoritative representation
of any given song's per-frame state; everything else is derived.

## Applying this to the keyboard_lab

The `keyboard_lab/` DB adopts these axioms explicitly:

- `approaches.category` names the layer the approach operates at
  (jsfx vs vsti vs hardware).
- `findings.dimension` names which layer a rating applies to
  (latency = jsfx/REAPER; sound_accuracy = stems-equivalent-layer).
- `experiments` track keyboard + preset + game as separable
  variables so we can reason about any of them independently.

Hygiene wasn't an afterthought in the schema — it's the reason the
schema has the tables it does.

## The value of context hygiene

Without it:
- Week 1's findings contradict week 3's without either knowing why.
- Bugs get "fixed" at one layer and reintroduced at another.
- Documentation ages into lies.
- Collaborators talk past each other.

With it:
- A claim in week 1 can be verified in week 3 by checking the same
  layer with the same validator.
- Bugs get fixed in all layers they touch, and Rules record which
  layers.
- Docs have dates AND layers so staleness is visible.
- Collaborators can ask "which layer?" and get an unambiguous
  answer.

Context hygiene is the operating discipline of this project.
Architecturally it's enforced by Rules; operationally by the
three-layer reminder in CLAUDE.md ("Observed / Intent /
Projection").  As the project scales, hygiene failures are the
failure mode to watch for, more than DSP bugs.
