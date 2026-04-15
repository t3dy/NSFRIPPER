import sqlite3
import json

class V2PipelineHook:
    """
    To satisfy Phase 4 Integration Guidelines:
    Import this module into `nes_rom_capture.py`, extraction scripts, and validation tools.
    Every output MUST generate an EvidenceItem.
    """
    def __init__(self, db_path="antiripper_v2.db"):
        self.db_path = db_path

    def register_evidence(self, game_slug: str, e_type: str, source_path: str, metrics: dict) -> int:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO evidence_items (game_slug, type, source_path, metrics_json) VALUES (?, ?, ?, ?)",
            (game_slug, e_type, source_path, json.dumps(metrics))
        )
        conn.commit()
        e_id = cur.lastrowid
        conn.close()
        return e_id

    def log_decision(self, game_slug: str, d_type: str, rationale: str, outcome: str):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO decision_records (game_slug, decision_type, rationale, outcome) VALUES (?, ?, ?, ?)",
            (game_slug, d_type, rationale, outcome)
        )
        conn.commit()
        conn.close()
