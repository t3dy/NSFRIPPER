# Oracle API (Agent Cheatsheet)

```python
from ANTIRIPPER.agent_oracle import AgentOracle
oracle = AgentOracle()  # uses antiripper_v2.db

# BEFORE work: get context
ctx = oracle.get_preflight_context("game_slug", "rom_parsing")
# Returns: driver_family, prevention_patterns, hardware_facts, claims, decisions, validation_requirements

# BEFORE code changes: log intent
aid = oracle.record_attempt("game_slug", "rom_parsing", "hypothesis", "planned_change")

# AFTER work: log result
oracle.record_outcome(aid, "success", evidence_refs=["path.csv"], lessons="what we learned")

# Other reads
oracle.get_validation_requirements("game_slug")   # what to validate
oracle.get_edit_guardrails("parser")               # subsystem: parser|synth|routing|timing
oracle.list_recent_failures(game_slug="X")         # learn from mistakes
oracle.explain_route_choice("game_slug")           # why this extraction route

# Proposing hypotheses (always starts as 'proposed', never auto-promotes)
oracle.propose_claim("game", "slug", "statement", confidence=0.7, evidence_ids=[1,2])
```

**Rules:** No raw SQL. No hardware fact writes. No claim auto-promotion. Always preflight before work.
