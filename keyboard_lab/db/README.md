# keyboard_lab database

Purpose: track, per-approach, which live-play behaviors are
supported, at what coverage level, and what experimental evidence
backs that claim.

## Schema

Two generations:
- **v1** (`init_keyboard_db.py`): approaches, presets, game_refs,
  keyboards, experiments, findings.  Tracks sessions + ratings.
- **v2 PAL extension** (`extend_capabilities.py`):  capabilities,
  approach_capabilities.  Tracks behavior-by-behavior coverage per
  the PAL doc (`docs/PERFORMANCE_ABSTRACTION_LAYER.md`).

Run in order:

```
python keyboard_lab/db/init_keyboard_db.py
python keyboard_lab/db/extend_capabilities.py
```

Both are idempotent.

## Standard queries

### Coverage matrix for all approaches

```sql
SELECT a.name, c.code, ac.coverage
FROM approaches a
LEFT JOIN approach_capabilities ac ON ac.approach_id = a.id
LEFT JOIN capabilities c ON ac.capability_id = c.id
ORDER BY a.name, c.pal_class, c.code;
```

### How many Class A (live) dimensions does each approach cover?

```sql
SELECT a.name,
       COUNT(CASE ac.coverage WHEN 'exact' THEN 1 END)       AS exact,
       COUNT(CASE ac.coverage WHEN 'approximate' THEN 1 END) AS approx,
       COUNT(CASE ac.coverage WHEN 'preset_only' THEN 1 END) AS preset,
       COUNT(CASE ac.coverage WHEN 'unsupported' THEN 1 END) AS unsup
FROM approaches a
LEFT JOIN approach_capabilities ac ON ac.approach_id = a.id
LEFT JOIN capabilities c
    ON ac.capability_id = c.id AND c.pal_class = 'A'
GROUP BY a.name;
```

### Which Class B behaviors are no approach covers?

```sql
SELECT c.code, c.name
FROM capabilities c
WHERE c.pal_class = 'B'
  AND NOT EXISTS (
    SELECT 1 FROM approach_capabilities ac
    WHERE ac.capability_id = c.id
      AND ac.coverage IN ('exact', 'approximate')
  );
```

### Gap analysis: Class A/B dimensions marked unsupported

These are implementation targets.  Run:

```sql
SELECT a.name, c.pal_class, c.code, ac.notes
FROM approach_capabilities ac
JOIN approaches a ON ac.approach_id = a.id
JOIN capabilities c ON ac.capability_id = c.id
WHERE ac.coverage = 'unsupported'
  AND c.pal_class IN ('A', 'B')
ORDER BY c.pal_class, a.name;
```

## Adding a new approach

1. Insert row into `approaches` (category = jsfx / vsti / hardware /
   hybrid).
2. For each capability, insert `approach_capabilities` row with
   coverage in {exact, approximate, preset_only, unsupported} and a
   note explaining how you verified it.
3. Run an experiment (see `experiments` table) and rate it via
   `findings` per dimension.

## Coverage-level semantics

- **exact** — the approach reproduces this NES behavior with
  measurable fidelity under live conditions.  Use this sparingly;
  requires ear-test confirmation.
- **approximate** — the approach produces a similar-sounding
  behavior, but it's not bit-accurate.  Most Class A dimensions
  land here in practice.
- **preset_only** — the behavior is set before the performance
  and cannot change live.  Class C dimensions land here by
  definition.
- **unsupported** — the approach does not implement this behavior.
  Class D dimensions are always unsupported; some Class A/B
  dimensions are unsupported because we haven't built them yet.
