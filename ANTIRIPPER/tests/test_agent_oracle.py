"""Tests for the ANTIRIPPER Agent Oracle.

Uses a temporary in-memory database with the V2 schema seeded
with test data. Tests verify the policy-enforcing interface works
correctly without touching the production database.
"""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest
import sys

# Add ANTIRIPPER to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_oracle import AgentOracle

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "SCHEMA_V2.sql"


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database with V2 schema and test data."""
    db_file = tmp_path / "test_oracle.db"
    conn = sqlite3.connect(str(db_file))

    # Create schema
    if SCHEMA_PATH.exists():
        conn.executescript(SCHEMA_PATH.read_text())

    # Seed test data
    conn.executescript("""
        INSERT INTO hardware_facts (statement, formula, source_reference, locked)
        VALUES
            ('Triangle divisor is 32', 'freq = CPU / (32 * (P+1))', 'NESDev APU Ref', 1),
            ('Pulse divisor is 16', 'freq = CPU / (16 * (P+1))', 'NESDev APU Ref', 1);

        INSERT INTO driver_families (slug, cc11_range, cc12_range, uses_hardware_envelope,
                                     animates_duty, high_density_volume,
                                     validation_implications, nsf_trust_level)
        VALUES
            ('minimal', '0.0 - 2.8', '0.0', 1, 0, 0, 'NSF sufficient', 'High'),
            ('dense_automators', '5.1 - 15.0', '0.0', 0, 0, 1,
             'Requires per-frame timing validation', 'Low');

        INSERT INTO prevention_patterns (description, trigger_condition,
                                         affected_subsystem, recommended_action,
                                         prompt_cost, example_failure)
        VALUES
            ('Do not assume CC12 maps dynamically', 'Sunsoft driver parsing',
             'parser', 'Check lookup table bounds', 5, 'Castlevania blank frames'),
            ('Triangle is 1 octave lower', 'Any pitch mapping',
             'routing', 'Subtract 12 semitones for triangle', 2, 'CV1 triangle wrong');

        INSERT INTO claims (subject_type, subject_id, statement, confidence, status)
        VALUES
            ('game', 'contra', 'Uses lookup table envelopes', 0.95, 'accepted'),
            ('game', 'contra', 'DX reads 3 bytes', 0.90, 'reviewed'),
            ('game', 'battletoads', 'Arpeggio system unmodeled', 0.3, 'proposed');

        INSERT INTO decision_records (game_slug, decision_type, rationale, outcome)
        VALUES
            ('contra', 'extraction_route', 'NSF + Mesen trace for dense_automators family', 'success'),
            ('castlevania', 'extraction_route', 'NSF only — minimal family, high trust', 'success');

        INSERT INTO evidence_items (game_slug, type, source_path, metrics_json)
        VALUES
            ('contra', 'trace', 'output/Contra/rom_capture/trace.csv',
             '{"frames": 5000, "channels": 4}'),
            ('contra', 'nsf', 'output/Contra/nsf/Contra.nsf',
             '{"expansion_byte": 0, "total_songs": 12}');
    """)

    conn.commit()
    conn.close()
    return str(db_file)


@pytest.fixture
def oracle(db_path):
    """Create an oracle instance pointing at the test database."""
    return AgentOracle(db_path=db_path)


# ---------------------------------------------------------
# Preflight context
# ---------------------------------------------------------

class TestPreflightContext:
    def test_returns_structured_output(self, oracle):
        ctx = oracle.get_preflight_context("contra", "rom_parsing")
        assert isinstance(ctx, dict)
        assert ctx["game_slug"] == "contra"
        assert ctx["task_type"] == "rom_parsing"
        assert "prevention_patterns" in ctx
        assert "hardware_facts" in ctx
        assert "claims" in ctx
        assert "decisions" in ctx
        assert "validation_requirements" in ctx

    def test_returns_claims_for_known_game(self, oracle):
        ctx = oracle.get_preflight_context("contra", "rom_parsing")
        # Only accepted/reviewed claims, not proposed
        assert len(ctx["claims"]) == 2
        statements = [c["statement"] for c in ctx["claims"]]
        assert "Uses lookup table envelopes" in statements

    def test_returns_decisions_for_known_game(self, oracle):
        ctx = oracle.get_preflight_context("contra", "rom_parsing")
        assert len(ctx["decisions"]) >= 1

    def test_returns_hardware_facts(self, oracle):
        ctx = oracle.get_preflight_context("contra", "rom_parsing")
        assert len(ctx["hardware_facts"]) == 2
        statements = [f["statement"] for f in ctx["hardware_facts"]]
        assert "Triangle divisor is 32" in statements

    def test_returns_prevention_patterns_for_subsystem(self, oracle):
        ctx = oracle.get_preflight_context("castlevania", "rom_parsing")
        # Should match 'parser' subsystem
        descriptions = [p["description"] for p in ctx["prevention_patterns"]]
        assert "Do not assume CC12 maps dynamically" in descriptions

    def test_unknown_game_returns_empty_context(self, oracle):
        ctx = oracle.get_preflight_context("unknown_game_xyz", "general")
        assert ctx["game_slug"] == "unknown_game_xyz"
        assert ctx["claims"] == []
        assert ctx["decisions"] == []
        # Should still return hardware facts and general patterns
        assert len(ctx["hardware_facts"]) == 2

    def test_proposed_claims_excluded(self, oracle):
        ctx = oracle.get_preflight_context("battletoads", "rom_parsing")
        # Battletoads has only a 'proposed' claim — should be excluded
        assert len(ctx["claims"]) == 0


# ---------------------------------------------------------
# Attempt tracking
# ---------------------------------------------------------

class TestAttemptTracking:
    def test_record_attempt_returns_id(self, oracle):
        aid = oracle.record_attempt(
            "contra", "rom_parsing",
            "DX reads 3 bytes in this driver",
            "Modify parser to read 3 bytes after DX opcode",
        )
        assert isinstance(aid, int)
        assert aid > 0

    def test_record_outcome_updates_attempt(self, oracle):
        aid = oracle.record_attempt(
            "contra", "rom_parsing",
            "Test hypothesis", "Test change",
        )
        oracle.record_outcome(
            aid, "success",
            evidence_refs=["trace.csv", "comparison_report.txt"],
            lessons="DX byte count confirmed via disassembly",
        )
        # Verify by reading back
        conn = sqlite3.connect(oracle.db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM attempts WHERE id = ?", (aid,)).fetchone()
        conn.close()
        assert row["result"] == "success"
        assert "DX byte count" in row["lessons"]
        assert row["completed_at"] is not None

    def test_record_outcome_failure(self, oracle):
        aid = oracle.record_attempt(
            "battletoads", "rom_parsing",
            "Arpeggio uses simple table", "Add arpeggio table lookup",
        )
        oracle.record_outcome(
            aid, "failure",
            lessons="Arpeggio system is frame-driven, not table-driven",
        )
        conn = sqlite3.connect(oracle.db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM attempts WHERE id = ?", (aid,)).fetchone()
        conn.close()
        assert row["result"] == "failure"


# ---------------------------------------------------------
# Validation requirements
# ---------------------------------------------------------

class TestValidationRequirements:
    def test_returns_dict(self, oracle):
        reqs = oracle.get_validation_requirements("contra")
        assert isinstance(reqs, dict)
        assert "nsf_acceptable" in reqs
        assert "mesen_trace_required" in reqs

    def test_unknown_game_has_defaults(self, oracle):
        reqs = oracle.get_validation_requirements("unknown_xyz")
        assert reqs["nsf_acceptable"] is True
        assert reqs["mesen_trace_required"] is False


# ---------------------------------------------------------
# Edit guardrails
# ---------------------------------------------------------

class TestEditGuardrails:
    def test_returns_structured_guardrails(self, oracle):
        guards = oracle.get_edit_guardrails("parser")
        assert isinstance(guards, dict)
        assert guards["target_subsystem"] == "parser"
        assert "prevention_patterns" in guards
        assert "hardware_facts" in guards
        assert "warnings" in guards

    def test_parser_guardrails_include_cc12_warning(self, oracle):
        guards = oracle.get_edit_guardrails("parser")
        descriptions = [p["description"] for p in guards["prevention_patterns"]]
        assert "Do not assume CC12 maps dynamically" in descriptions

    def test_high_cost_patterns_appear_in_warnings(self, oracle):
        guards = oracle.get_edit_guardrails("parser")
        # Pattern with prompt_cost=5 should appear in warnings
        assert len(guards["warnings"]) >= 1


# ---------------------------------------------------------
# Claims
# ---------------------------------------------------------

class TestClaims:
    def test_propose_claim_returns_id(self, oracle):
        cid = oracle.propose_claim(
            "game", "mega_man", "Uses hardware envelope", 0.8
        )
        assert isinstance(cid, int)
        assert cid > 0

    def test_proposed_claim_starts_as_proposed(self, oracle):
        cid = oracle.propose_claim(
            "game", "mega_man", "Test claim", 0.5
        )
        conn = sqlite3.connect(oracle.db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT status FROM claims WHERE id = ?", (cid,)).fetchone()
        conn.close()
        assert row["status"] == "proposed"

    def test_confidence_clamped(self, oracle):
        cid = oracle.propose_claim(
            "game", "test", "Overconfident", 1.5
        )
        conn = sqlite3.connect(oracle.db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT confidence FROM claims WHERE id = ?", (cid,)).fetchone()
        conn.close()
        assert row["confidence"] <= 1.0


# ---------------------------------------------------------
# Hardware facts are read-only
# ---------------------------------------------------------

class TestHardwareFactsReadOnly:
    def test_no_write_method_for_hardware_facts(self, oracle):
        """Oracle has no method to insert or update hardware facts."""
        assert not hasattr(oracle, "add_hardware_fact")
        assert not hasattr(oracle, "update_hardware_fact")
        assert not hasattr(oracle, "delete_hardware_fact")


# ---------------------------------------------------------
# Failure history
# ---------------------------------------------------------

class TestFailureHistory:
    def test_list_recent_failures_empty(self, oracle):
        failures = oracle.list_recent_failures()
        assert isinstance(failures, list)
        assert len(failures) == 0  # No failed attempts yet

    def test_list_recent_failures_after_failure(self, oracle):
        aid = oracle.record_attempt(
            "battletoads", "rom_parsing", "Bad hypothesis", "Bad change",
        )
        oracle.record_outcome(aid, "failure", lessons="Wrong approach")
        failures = oracle.list_recent_failures(game_slug="battletoads")
        assert len(failures) == 1
        assert failures[0]["result"] == "failure"

    def test_successes_excluded_from_failures(self, oracle):
        aid = oracle.record_attempt(
            "contra", "rom_parsing", "Good hypothesis", "Good change",
        )
        oracle.record_outcome(aid, "success")
        failures = oracle.list_recent_failures(game_slug="contra")
        assert len(failures) == 0


# ---------------------------------------------------------
# Route explanation
# ---------------------------------------------------------

class TestRouteExplanation:
    def test_explain_route_returns_decisions(self, oracle):
        result = oracle.explain_route_choice("contra")
        assert result["game_slug"] == "contra"
        assert len(result["route_decisions"]) >= 1

    def test_unknown_game_returns_empty(self, oracle):
        result = oracle.explain_route_choice("unknown_xyz")
        assert result["route_decisions"] == []
