"""ANTIRIPPER Agent Oracle — policy-enforcing access layer over the knowledge DB.

Agents MUST NOT query the database directly. All context flows through
this module's functions. The oracle enforces this workflow:

    preflight context -> record attempt -> do work -> record outcome

This is not an AI system, not a service, and not a generic database
browser. It is a thin Python API that forces agents into safe,
traceable workflows.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ANTIRIPPER_DIR = Path(__file__).resolve().parent
DEFAULT_DB = ANTIRIPPER_DIR / "antiripper_v2.db"
SCHEMA_PATH = ANTIRIPPER_DIR / "SCHEMA_V2.sql"

# Subsystem inference from task types
_TASK_SUBSYSTEM_MAP = {
    "rom_parsing": "parser",
    "nsf_extraction": "routing",
    "trace_capture": "routing",
    "synth_tuning": "synth",
    "synth_preset": "synth",
    "midi_generation": "routing",
    "timing_validation": "timing",
    "reaper_project": "routing",
    "driver_survey": "routing",
    "expansion_detect": "routing",
}


# ---------------------------------------------------------------------------
# Return types (simple dataclasses, not ORM)
# ---------------------------------------------------------------------------

@dataclass
class PreflightContext:
    game_slug: str
    task_type: str
    driver_family: dict | None = None
    prevention_patterns: list[dict] = field(default_factory=list)
    hardware_facts: list[dict] = field(default_factory=list)
    claims: list[dict] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    validation_requirements: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Schema bootstrap (ensures attempts table exists)
# ---------------------------------------------------------------------------

_ATTEMPTS_DDL = """
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY,
    game_slug TEXT NOT NULL,
    task_type TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    planned_change TEXT NOT NULL,
    result TEXT,
    evidence_refs TEXT,
    lessons TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);
"""


# ---------------------------------------------------------------------------
# Oracle
# ---------------------------------------------------------------------------

class AgentOracle:
    """Policy-enforcing interface to the ANTIRIPPER knowledge base.

    Agents MUST NOT query the database directly.
    All context MUST be routed through these functions.
    """

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or DEFAULT_DB)
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self):
        """Ensure the DB exists and has the attempts table."""
        db = Path(self.db_path)
        if not db.exists():
            logger.info("Creating database at %s", self.db_path)
            conn = sqlite3.connect(self.db_path)
            if SCHEMA_PATH.exists():
                conn.executescript(SCHEMA_PATH.read_text())
            conn.executescript(_ATTEMPTS_DDL)
            conn.close()
        else:
            conn = sqlite3.connect(self.db_path)
            conn.executescript(_ATTEMPTS_DDL)
            conn.close()

    def _table_exists(self, conn: sqlite3.Connection, table: str) -> bool:
        cur = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        return cur.fetchone() is not None

    # ---------------------------------------------------------
    # READ: Preflight & Context
    # ---------------------------------------------------------

    def get_preflight_context(
        self, game_slug: str, task_type: str = "general"
    ) -> dict[str, Any]:
        """Return the minimum context an agent needs before starting work.

        Gathers driver family, prevention patterns, hardware facts,
        accepted claims, and decision records for a specific game/task.
        Returns a compact structured dict. Never crashes on missing data.
        """
        conn = self._get_connection()
        ctx = PreflightContext(game_slug=game_slug, task_type=task_type)

        try:
            # Infer subsystem from task type
            subsystem = _TASK_SUBSYSTEM_MAP.get(task_type, "routing")

            # 1. Driver family
            ctx.driver_family = self._get_driver_family(conn, game_slug)

            # 2. Prevention patterns (match subsystem + game-specific)
            ctx.prevention_patterns = self._get_prevention_patterns(
                conn, subsystem, game_slug
            )

            # 3. Hardware facts (filtered by task subsystem)
            ctx.hardware_facts = self._get_hardware_facts(conn, subsystem)

            # 4. Claims (accepted/reviewed only)
            ctx.claims = self._get_claims(conn, game_slug)

            # 5. Decision records
            ctx.decisions = self._get_decisions(conn, game_slug)

            # 6. Validation requirements
            ctx.validation_requirements = self.get_validation_requirements(
                game_slug
            )
        finally:
            conn.close()

        return ctx.to_dict()

    def _get_driver_family(
        self, conn: sqlite3.Connection, game_slug: str
    ) -> dict | None:
        """Look up driver family for a game.

        First checks decision_records for an explicit family assignment,
        then falls back to checking if the game_slug matches a known
        family pattern.
        """
        if not self._table_exists(conn, "driver_families"):
            return None

        # Check decision records for explicit family assignment
        if self._table_exists(conn, "decision_records"):
            cur = conn.execute(
                """SELECT rationale FROM decision_records
                   WHERE game_slug = ? AND decision_type = 'extraction_route'
                   ORDER BY created_at DESC LIMIT 1""",
                (game_slug,),
            )
            row = cur.fetchone()
            if row:
                # Try to extract family slug from rationale
                rationale = row["rationale"]
                cur2 = conn.execute("SELECT * FROM driver_families")
                for fam in cur2.fetchall():
                    if fam["slug"] in rationale.lower():
                        return dict(fam)

        # Return all families for reference if no specific match
        cur = conn.execute("SELECT * FROM driver_families")
        families = [dict(r) for r in cur.fetchall()]
        if len(families) == 1:
            return families[0]
        return None

    def _get_prevention_patterns(
        self, conn: sqlite3.Connection, subsystem: str, game_slug: str
    ) -> list[dict]:
        if not self._table_exists(conn, "prevention_patterns"):
            return []
        cur = conn.execute(
            """SELECT description, trigger_condition, affected_subsystem,
                      recommended_action, prompt_cost, example_failure
               FROM prevention_patterns
               WHERE affected_subsystem = ?
                  OR example_failure LIKE ?""",
            (subsystem, f"%{game_slug}%"),
        )
        return [dict(r) for r in cur.fetchall()]

    def _get_hardware_facts(
        self, conn: sqlite3.Connection, subsystem: str = "all"
    ) -> list[dict]:
        if not self._table_exists(conn, "hardware_facts"):
            return []

        # Check if relevant_subsystems column exists
        pragma = conn.execute("PRAGMA table_info(hardware_facts)").fetchall()
        has_subsystems = any(col["name"] == "relevant_subsystems" for col in pragma)

        if has_subsystems and subsystem != "all":
            cur = conn.execute(
                """SELECT statement, formula, source_reference
                   FROM hardware_facts
                   WHERE locked = 1
                     AND (relevant_subsystems LIKE ? OR relevant_subsystems = 'all')""",
                (f"%{subsystem}%",),
            )
        else:
            cur = conn.execute(
                "SELECT statement, formula, source_reference FROM hardware_facts WHERE locked = 1"
            )
        return [dict(r) for r in cur.fetchall()]

    def _get_claims(
        self, conn: sqlite3.Connection, game_slug: str
    ) -> list[dict]:
        if not self._table_exists(conn, "claims"):
            return []
        cur = conn.execute(
            """SELECT id, subject_type, subject_id, statement, confidence, status
               FROM claims
               WHERE subject_id = ? AND status IN ('reviewed', 'accepted')
               ORDER BY confidence DESC""",
            (game_slug,),
        )
        return [dict(r) for r in cur.fetchall()]

    def _get_decisions(
        self, conn: sqlite3.Connection, game_slug: str
    ) -> list[dict]:
        if not self._table_exists(conn, "decision_records"):
            return []
        cur = conn.execute(
            """SELECT decision_type, rationale, outcome, created_at
               FROM decision_records
               WHERE game_slug = ?
               ORDER BY created_at DESC LIMIT 10""",
            (game_slug,),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_validation_requirements(self, game_slug: str) -> dict:
        """Return what validation is required for this game.

        Checks driver family trust level and expansion audio status
        to determine the validation bar.
        """
        conn = self._get_connection()
        try:
            family = self._get_driver_family(conn, game_slug)

            # Defaults
            reqs = {
                "nsf_acceptable": True,
                "mesen_trace_required": False,
                "vgm_cross_validation": False,
                "expansion_audio": False,
                "dpcm_special_handling": False,
                "notes": [],
            }

            if family:
                trust = family.get("nsf_trust_level", "High")
                if trust.lower() in ("low", "suspect"):
                    reqs["mesen_trace_required"] = True
                    reqs["vgm_cross_validation"] = True
                    reqs["notes"].append(
                        f"Driver family '{family.get('slug')}' has {trust} NSF trust"
                    )
                if family.get("high_density_volume"):
                    reqs["notes"].append(
                        "Dense volume automation — check for MIDI size explosion"
                    )

            # Check for expansion audio via evidence or decisions
            if self._table_exists(conn, "evidence_items"):
                cur = conn.execute(
                    """SELECT metrics_json FROM evidence_items
                       WHERE game_slug = ? AND type = 'nsf'
                       ORDER BY created_at DESC LIMIT 1""",
                    (game_slug,),
                )
                row = cur.fetchone()
                if row:
                    try:
                        metrics = json.loads(row["metrics_json"])
                        exp_byte = metrics.get("expansion_byte", 0)
                        if exp_byte:
                            reqs["expansion_audio"] = True
                            reqs["notes"].append(
                                f"Expansion byte 0x{exp_byte:02X} — channels may be missing"
                            )
                    except (json.JSONDecodeError, TypeError):
                        pass

            return reqs
        finally:
            conn.close()

    def get_edit_guardrails(self, target_subsystem: str) -> dict:
        """Return prevention patterns and hardware facts before editing a subsystem.

        Subsystems: parser, synth, routing, timing, metadata
        """
        conn = self._get_connection()
        try:
            patterns = self._get_prevention_patterns(conn, target_subsystem, "")
            facts = self._get_hardware_facts(conn)

            return {
                "target_subsystem": target_subsystem,
                "prevention_patterns": patterns,
                "hardware_facts": facts,
                "warnings": [
                    p["description"]
                    for p in patterns
                    if p.get("prompt_cost", 0) >= 3
                ],
            }
        finally:
            conn.close()

    # ---------------------------------------------------------
    # WRITE: Attempt Tracking (append-only)
    # ---------------------------------------------------------

    def record_attempt(
        self,
        game_slug: str,
        task_type: str,
        hypothesis: str,
        planned_change: str,
    ) -> int:
        """Log what the agent is about to try BEFORE changing code.

        Returns an attempt_id for later use with record_outcome.
        """
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """INSERT INTO attempts
                   (game_slug, task_type, hypothesis, planned_change)
                   VALUES (?, ?, ?, ?)""",
                (game_slug, task_type, hypothesis, planned_change),
            )
            conn.commit()
            attempt_id = cur.lastrowid
            logger.info(
                "Recorded attempt #%d: %s/%s — %s",
                attempt_id, game_slug, task_type, hypothesis[:60],
            )
            return attempt_id
        finally:
            conn.close()

    def record_outcome(
        self,
        attempt_id: int,
        result: str,
        evidence_refs: list[str] | None = None,
        lessons: str | None = None,
    ) -> None:
        """Record what happened after the attempt.

        Does NOT promote claims to accepted — that requires human review.
        """
        conn = self._get_connection()
        try:
            now = datetime.now(timezone.utc).isoformat()
            refs_json = json.dumps(evidence_refs) if evidence_refs else None
            conn.execute(
                """UPDATE attempts
                   SET result = ?, evidence_refs = ?, lessons = ?, completed_at = ?
                   WHERE id = ?""",
                (result, refs_json, lessons, now, attempt_id),
            )
            conn.commit()
            logger.info("Recorded outcome for attempt #%d: %s", attempt_id, result)
        finally:
            conn.close()

    # ---------------------------------------------------------
    # WRITE: Claims (append-only, never auto-promote)
    # ---------------------------------------------------------

    def propose_claim(
        self,
        subject_type: str,
        subject_id: str,
        statement: str,
        confidence: float,
        evidence_ids: list[int] | None = None,
    ) -> int:
        """Propose a new claim. Always starts as 'proposed'.

        Agents can propose claims but NEVER promote them to accepted.
        Only human review changes status to reviewed/accepted.
        """
        conn = self._get_connection()
        try:
            if not self._table_exists(conn, "claims"):
                raise RuntimeError("claims table does not exist")

            confidence = max(0.0, min(1.0, confidence))
            cur = conn.execute(
                """INSERT INTO claims
                   (subject_type, subject_id, statement, confidence, status)
                   VALUES (?, ?, ?, ?, 'proposed')""",
                (subject_type, subject_id, statement, confidence),
            )
            claim_id = cur.lastrowid

            if evidence_ids and self._table_exists(conn, "claim_evidence_links"):
                for eid in evidence_ids:
                    conn.execute(
                        """INSERT OR IGNORE INTO claim_evidence_links
                           (claim_id, evidence_id) VALUES (?, ?)""",
                        (claim_id, eid),
                    )

            conn.commit()
            logger.info("Proposed claim #%d: %s", claim_id, statement[:60])
            return claim_id
        finally:
            conn.close()

    # ---------------------------------------------------------
    # READ: Failure history
    # ---------------------------------------------------------

    def list_recent_failures(
        self,
        game_slug: str | None = None,
        task_type: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """List recent failed attempts for learning from mistakes."""
        conn = self._get_connection()
        try:
            conditions = ["result IS NOT NULL", "result != 'success'"]
            params: list[Any] = []

            if game_slug:
                conditions.append("game_slug = ?")
                params.append(game_slug)
            if task_type:
                conditions.append("task_type = ?")
                params.append(task_type)

            where = " AND ".join(conditions)
            params.append(limit)

            cur = conn.execute(
                f"""SELECT id, game_slug, task_type, hypothesis,
                           result, lessons, created_at
                    FROM attempts
                    WHERE {where}
                    ORDER BY created_at DESC
                    LIMIT ?""",
                params,
            )
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def explain_route_choice(self, game_slug: str) -> dict:
        """Explain why a particular extraction route was chosen for a game."""
        conn = self._get_connection()
        try:
            result: dict[str, Any] = {
                "game_slug": game_slug,
                "route_decisions": [],
                "driver_family": None,
            }

            result["driver_family"] = self._get_driver_family(conn, game_slug)

            if self._table_exists(conn, "decision_records"):
                cur = conn.execute(
                    """SELECT decision_type, rationale, outcome, created_at
                       FROM decision_records
                       WHERE game_slug = ?
                       ORDER BY created_at DESC""",
                    (game_slug,),
                )
                result["route_decisions"] = [dict(r) for r in cur.fetchall()]

            return result
        finally:
            conn.close()

    # ---------------------------------------------------------
    # READ: Evidence registration (for pipeline hooks)
    # ---------------------------------------------------------

    def register_evidence(
        self,
        game_slug: str,
        evidence_type: str,
        source_path: str,
        metrics: dict | None = None,
    ) -> int:
        """Register a new evidence item from the extraction pipeline.

        This is called by pipeline hooks, not directly by agents.
        """
        conn = self._get_connection()
        try:
            if not self._table_exists(conn, "evidence_items"):
                raise RuntimeError("evidence_items table does not exist")

            metrics_json = json.dumps(metrics) if metrics else "{}"
            cur = conn.execute(
                """INSERT INTO evidence_items
                   (game_slug, type, source_path, metrics_json)
                   VALUES (?, ?, ?, ?)""",
                (game_slug, evidence_type, source_path, metrics_json),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def log_decision(
        self,
        game_slug: str,
        decision_type: str,
        rationale: str,
        outcome: str | None = None,
    ) -> int:
        """Log a pipeline decision for audit trail."""
        conn = self._get_connection()
        try:
            if not self._table_exists(conn, "decision_records"):
                raise RuntimeError("decision_records table does not exist")

            cur = conn.execute(
                """INSERT INTO decision_records
                   (game_slug, decision_type, rationale, outcome)
                   VALUES (?, ?, ?, ?)""",
                (game_slug, decision_type, rationale, outcome),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()
