# Agent Oracle

The oracle is a thin policy-enforcing Python interface over the SQLite
knowledge base. It is not an AI system, not a service, and not a generic
database browser.

## Why It Exists

AI agents working on NES audio extraction were:
1. Querying raw SQL and pulling wrong context
2. Forgetting prior failures across sessions
3. Overwriting curated truth (hardware facts, driver families)
4. Mutating stable pipeline logic without logging intent

The oracle forces agents into a traceable workflow:

```
preflight context -> record attempt -> do work -> record outcome
```

## What Agents Are Allowed To Use

```python
from ANTIRIPPER.agent_oracle import AgentOracle

oracle = AgentOracle()  # uses antiripper_v2.db by default
```

### Core Functions

| Function | Purpose | Read/Write |
|----------|---------|------------|
| `get_preflight_context(game_slug, task_type)` | Get everything needed before starting work | Read |
| `record_attempt(game_slug, task_type, hypothesis, planned_change)` | Log intent BEFORE action | Write |
| `record_outcome(attempt_id, result, evidence_refs, lessons)` | Log result AFTER action | Write |
| `get_validation_requirements(game_slug)` | What must be checked for this game | Read |
| `get_edit_guardrails(target_subsystem)` | Prevention patterns before editing code | Read |

### Optional Functions

| Function | Purpose |
|----------|---------|
| `propose_claim(subject_type, subject_id, statement, confidence, evidence_ids)` | Propose a hypothesis |
| `list_recent_failures(game_slug, task_type, limit)` | Learn from past mistakes |
| `explain_route_choice(game_slug)` | Why was this extraction route chosen |
| `register_evidence(game_slug, type, source_path, metrics)` | Pipeline hook: register evidence |
| `log_decision(game_slug, decision_type, rationale, outcome)` | Pipeline hook: log decision |

## What Agents Are Forbidden From Doing

- Running raw SQL against any ANTIRIPPER database
- Browsing tables directly
- Promoting claims to `accepted` (requires human review)
- Inserting or updating hardware facts
- Bypassing the preflight check before starting work
- Using a generic `query()` function (none exists)

## Example Usage

### Before starting work on a game

```python
oracle = AgentOracle()

# 1. Get context
ctx = oracle.get_preflight_context("contra", "rom_parsing")
print(ctx["prevention_patterns"])  # What to watch out for
print(ctx["hardware_facts"])       # Immutable truths
print(ctx["claims"])               # What's already known

# 2. Record what you're about to try
attempt_id = oracle.record_attempt(
    "contra", "rom_parsing",
    hypothesis="DX opcode reads 3 bytes in Contra driver",
    planned_change="Update parser to read 3 bytes after DX",
)

# 3. Do the work...

# 4. Record what happened
oracle.record_outcome(
    attempt_id,
    result="success",
    evidence_refs=["output/Contra/trace_comparison.csv"],
    lessons="Confirmed via disassembly line 412: 3-byte DX format",
)
```

### Before editing a subsystem

```python
guards = oracle.get_edit_guardrails("parser")
print(guards["warnings"])  # High-cost mistakes to avoid
print(guards["prevention_patterns"])  # Detailed guardrails
```

### Learning from past failures

```python
failures = oracle.list_recent_failures(game_slug="battletoads")
for f in failures:
    print(f"Attempt #{f['id']}: {f['hypothesis']}")
    print(f"  Result: {f['result']}")
    print(f"  Lesson: {f['lessons']}")
```

## Data Separation

The oracle enforces strict separation between data types:

| Layer | Mutability | Agent Access |
|-------|-----------|-------------|
| Hardware Facts | Immutable (locked=1) | Read only |
| Prevention Patterns | Append by human | Read only |
| Driver Families | Set by classification | Read only |
| Evidence Items | Append by pipeline hooks | Write via `register_evidence` |
| Claims | Append by agents | Write via `propose_claim` (always starts as 'proposed') |
| Decision Records | Append by pipeline | Write via `log_decision` |
| Attempts | Append by agents | Write via `record_attempt` / `record_outcome` |

## Database Schema

See `ANTIRIPPER/SCHEMA_V2.sql` for the full schema (9 tables across 8 layers).
The `attempts` table is created automatically by the oracle if it doesn't exist.

## Task Types

The oracle maps task types to subsystems for pattern matching:

| Task Type | Subsystem |
|-----------|-----------|
| `rom_parsing` | parser |
| `nsf_extraction` | routing |
| `trace_capture` | routing |
| `synth_tuning` | synth |
| `synth_preset` | synth |
| `midi_generation` | routing |
| `timing_validation` | timing |
| `reaper_project` | routing |

## Testing

```bash
python -m pytest ANTIRIPPER/tests/test_agent_oracle.py -v
```

24 tests covering all core functions, edge cases, and policy enforcement.
