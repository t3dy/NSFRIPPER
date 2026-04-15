"""Pipeline hooks for automatic evidence and decision recording.

Wired into nsf_to_reaper.py (per-song) and batch_nsf_all.py (per-game).
Every extraction produces evidence records; every batch run logs decisions.

Usage:
    from ANTIRIPPER.scripts.pipeline_hooks_v2 import PipelineHooks
    hooks = PipelineHooks()
    hooks.on_song_extracted(game_slug, song_num, midi_path, note_counts, cc_counts)
    hooks.on_game_completed(game_slug, success_count, total_count, route="nsf_emulation")
    hooks.on_game_failed(game_slug, reason="PLAY hangs on all tracks")
"""

import sqlite3
import json
import os
from pathlib import Path

# Default DB: antiripper_v2.db in the ANTIRIPPER/ directory
_DEFAULT_DB = Path(__file__).resolve().parent.parent / "antiripper_v2.db"


class PipelineHooks:
    """Automatic evidence and decision recording for the extraction pipeline.

    Designed to be zero-friction: import, instantiate, call after each step.
    Failures in the hooks themselves never crash the pipeline — they print
    a warning and continue.
    """

    def __init__(self, db_path=None):
        self.db_path = str(db_path or _DEFAULT_DB)
        if not os.path.exists(self.db_path):
            print(f"  [hooks] WARNING: DB not found at {self.db_path}, hooks disabled")
            self.enabled = False
        else:
            self.enabled = True

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def on_song_extracted(self, game_slug, song_num, midi_path,
                          note_counts=None, cc_counts=None,
                          frame_count=0, expansion_chips=None):
        """Record evidence for a single extracted song.

        Called from nsf_to_reaper.py after each successful process_song().
        """
        if not self.enabled:
            return None
        try:
            metrics = {
                "song_num": song_num,
                "frame_count": frame_count,
            }
            if note_counts:
                metrics["note_counts"] = {
                    "pulse1": note_counts[0] if len(note_counts) > 0 else 0,
                    "pulse2": note_counts[1] if len(note_counts) > 1 else 0,
                    "triangle": note_counts[2] if len(note_counts) > 2 else 0,
                    "noise": note_counts[3] if len(note_counts) > 3 else 0,
                }
                metrics["total_notes"] = sum(note_counts[:4])
            if cc_counts:
                metrics["cc_counts"] = {
                    "pulse1": cc_counts[0] if len(cc_counts) > 0 else 0,
                    "pulse2": cc_counts[1] if len(cc_counts) > 1 else 0,
                    "triangle": cc_counts[2] if len(cc_counts) > 2 else 0,
                }
            if expansion_chips:
                metrics["expansion_chips"] = expansion_chips

            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO evidence_items (game_slug, type, source_path, metrics_json) VALUES (?, ?, ?, ?)",
                (game_slug, "nsf", str(midi_path), json.dumps(metrics)),
            )
            conn.commit()
            eid = cur.lastrowid
            conn.close()
            return eid
        except Exception as e:
            print(f"  [hooks] WARNING: on_song_extracted failed: {e}")
            return None

    def on_game_completed(self, game_slug, success_count, total_count,
                          route="nsf_emulation", bankswitched=False,
                          expansion_chips=None):
        """Log a decision record when a game finishes extraction.

        Called from batch_nsf_all.py after all tracks for a game are done.
        """
        if not self.enabled:
            return
        try:
            route_detail = route
            if bankswitched:
                route_detail += "_bankswitched"

            rationale = f"{success_count}/{total_count} tracks extracted via {route_detail}"
            if expansion_chips:
                rationale += f" (expansion: {', '.join(expansion_chips)})"

            outcome = "complete" if success_count == total_count else "partial"

            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO decision_records (game_slug, decision_type, rationale, outcome) VALUES (?, ?, ?, ?)",
                (game_slug, "extraction_route", rationale, outcome),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"  [hooks] WARNING: on_game_completed failed: {e}")

    def on_game_failed(self, game_slug, reason="unknown"):
        """Log a decision record when a game fails extraction entirely.

        Called from batch_nsf_all.py when process_game() returns False.
        """
        if not self.enabled:
            return
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO decision_records (game_slug, decision_type, rationale, outcome) VALUES (?, ?, ?, ?)",
                (game_slug, "extraction_route", f"NSF extraction failed: {reason}", "failed"),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"  [hooks] WARNING: on_game_failed failed: {e}")

    def on_batch_summary(self, ok_count, fail_count, ok_games, fail_games):
        """Record batch run summary as evidence.

        Called once at the end of batch_nsf_all.py.
        """
        if not self.enabled:
            return
        try:
            metrics = {
                "ok_count": ok_count,
                "fail_count": fail_count,
                "ok_games": ok_games[:20],  # cap to avoid huge records
                "fail_games": fail_games,
            }
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO evidence_items (game_slug, type, source_path, metrics_json) VALUES (?, ?, ?, ?)",
                ("_batch", "metric", "scripts/batch_nsf_all.py", json.dumps(metrics)),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"  [hooks] WARNING: on_batch_summary failed: {e}")
