# Results — cartography of sound approaches

Summary of what was produced in response to the prompt:

> "I want to try basically every method of approximating the game sound
> using midi and synth or other kinds of reaper plugin, give me a plan
> for trying various other approaches we might be taking and estimate
> the highest priority potentials"

## What was delivered

A single mapping document: [docs/APPROACHES_PLAN.md](APPROACHES_PLAN.md)

It surveys **30+ distinct techniques** organized into four tiers and
ranks them by priority for trying first.  Each entry carries:

- Effort estimate (hours or days).
- Cost (free / $95 for chipsounds / $150 for MIDINES / etc.).
- Expected audio-quality grade (S / A / B / C).
- Priority (P0 = next to try, P3 = long-term research).
- First actionable step.

## The top 10 picks (from that plan)

In descending priority:

1. **FamiStudio** — free, likely very close to reference.  2 h to test.
2. **Plogue chipsounds** demo — commercial reference.  30 min to A/B.
3. **ReaPack JSFX survey** — might find a gem.  2 h.
4. **Tweakbench Triforce** — free VSTi.  1 h.
5. **Convolution with NES RCA impulse response** — biggest distinctive
   upgrade to stems.  1-2 days.
6. **2-bus-stem architecture** — small fix, large improvement.  2-3 h.
7. **Port polyBLEP to JSFX** — closes Variant B's biggest gap.  3-4 h.
8. **Blargg Blip_Buffer to numpy** — archival anti-aliasing.  1 day.
9. **ReaScript offline render** — unblocks Variant C.  1-2 days.
10. **Multi-sample library from real NES hardware** — ultimate
    archival authenticity.  3-5 days.

## The four tiers in one sentence

- **Tier 1 (P0)**: things you can try in an afternoon.  FamiStudio,
  chipsounds, Triforce, ReaPack, SF2 libraries.
- **Tier 2 (P1)**: DSP or tooling projects that materially improve an
  existing variant.  BLEP port, convolution, bus stems, polyBLEP,
  ReaScript.
- **Tier 3 (P2)**: creative and experimental — multi-sample libraries,
  neural synth models, real-hardware bridges, wavetable approaches.
- **Tier 4 (P3)**: translating to tracker ecosystems (FamiTracker,
  Furnace, BambooTracker) — likely covered by tier 1's FamiStudio.

## Decision framework baked into the plan

For each approach evaluated, the plan asks:

- Better than B (JSFX alone)?  → adopt as live path if licensing OK.
- Better than A (Python stems)?  → adopt as archival path.
- Equivalent?  → skip (complexity without win).
- Worse?  → document and move on.

Each evaluation writes a note.  The doc `docs/APPROACHES_NOTES.md`
(to be created when the first evaluation happens) holds those notes.

## What NOT to waste time on

Called out explicitly in the plan:

- Custom saturators / waveshapers claiming to reproduce "NES grit" —
  the grit is aliasing.  Fix it mathematically (BLEP), don't hide it.
- Writing a new VSTi from scratch before trying chipsounds /
  FamiStudio.  If those cover 95% of the use case, building our own
  is reinvention.
- Multi-sample libraries captured from emulators — they're just
  samples of other synths, not of hardware.

## Coverage

The plan covers every major axis: VSTi (commercial + free), wavetable
synths, SoundFont/SFZ, DSP improvements (BLEP, convolution, bus
stems), hardware bridges (MIDINES), ML approaches, and tracker
ecosystems.  Omitted on purpose: hardware-DIY projects beyond MIDINES
(too specialized), iPad/mobile synths (no REAPER integration),
and paid-only plugins other than chipsounds (chipsounds is the
benchmark; others would be evaluated only if chipsounds fails).

## Next step

Pick any P0 entry and try it for an hour.  Report back with a one-
line verdict; I'll update the corresponding row in the plan's
"sounds better / equivalent / worse" columns.  We iterate from there.
