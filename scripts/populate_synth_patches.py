"""Populate synth_patches table with family-level presets from DRIVER_FAMILIES research.

Run once:
    python scripts/populate_synth_patches.py
"""

import sqlite3
import json
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "ANTIRIPPER" / "antiripper_v2.db"


def main():
    db = sqlite3.connect(str(DB_PATH))
    c = db.cursor()

    # Add target_id column if missing
    try:
        c.execute('ALTER TABLE synth_patches ADD COLUMN target_id TEXT NOT NULL DEFAULT ""')
        print("Added target_id column to synth_patches")
    except Exception:
        pass  # already exists

    # Clear existing family presets (idempotent)
    c.execute("DELETE FROM synth_patches WHERE target_scope = 'family'")

    families = [
        {
            "target_id": "hardware_envelope",
            "confidence": 0.85,
            "parameters": {
                "family_id": 1,
                "family_name": "Hardware Envelope",
                "cc11_per_note": "0.1-2.8",
                "cc12_per_note": "0.0-0.6",
                "pulse": {
                    "attack_frames": 1,
                    "decay_frames": 8,
                    "sustain_vol": 7,
                    "release_frames": 0,
                    "duty_default": 1,
                    "duty_animated": False,
                    "envelope_mode": "hw_decay",
                },
                "triangle": {"gate_only": True},
                "noise": {"velocity_driven": True, "decay_frames": 6},
                "cc11_behavior": "hold_last_value",
                "cc12_behavior": "set_once_at_onset",
                "example_games": ["Mega Man", "Mega Man 2", "DuckTales", "Wizards & Warriors"],
                "notes": "Simple ADSR. Short attack, linear decay. Do not interpolate sparse CC11.",
            },
        },
        {
            "target_id": "standard_envelope",
            "confidence": 0.90,
            "parameters": {
                "family_id": 2,
                "family_name": "Standard Envelope",
                "cc11_per_note": "3.5-5.6",
                "cc12_per_note": "<0.5",
                "pulse": {
                    "attack_frames": 0,
                    "decay_frames": 4,
                    "sustain_vol": 8,
                    "release_frames": 0,
                    "duty_default": 1,
                    "duty_animated": False,
                    "envelope_mode": "sw_per_frame",
                },
                "triangle": {"gate_only": True},
                "noise": {"velocity_driven": True, "decay_frames": 4},
                "cc11_behavior": "primary_envelope_source",
                "cc12_behavior": "set_once_at_onset",
                "example_games": ["Castlevania", "Contra", "Battletoads", "Ninja Gaiden"],
                "notes": "CC11 IS the envelope. ADSR bypassed when CC11 present.",
                "game_variants": {
                    "castlevania": {"decay_frames": 3, "sustain_vol": 8},
                    "contra": {"decay_frames": 4, "sustain_vol": 6},
                    "battletoads": {"decay_frames": 6, "sustain_vol": 4},
                },
            },
        },
        {
            "target_id": "duty_animators",
            "confidence": 0.85,
            "parameters": {
                "family_id": 3,
                "family_name": "Duty Animators",
                "cc11_per_note": "3.7-4.9",
                "cc12_per_note": "0.7-1.0",
                "pulse": {
                    "attack_frames": 0,
                    "decay_frames": 3,
                    "sustain_vol": 8,
                    "release_frames": 0,
                    "duty_default": 1,
                    "duty_animated": True,
                    "duty_sequence": [1, 1, 2, 2, 2],
                    "envelope_mode": "sw_vol_plus_duty",
                },
                "triangle": {"gate_only": True},
                "noise": {"velocity_driven": True, "decay_frames": 4},
                "cc11_behavior": "per_frame_apply",
                "cc12_behavior": "per_frame_apply",
                "example_games": ["Super Mario Bros", "Castlevania 3 US", "Kirbys Adventure"],
                "notes": "Both CC11 and CC12 per-frame. Ignoring CC12 = audibly wrong.",
                "game_variants": {
                    "smb1": {"duty_sequence": [1, 1, 2, 2, 2]},
                    "kirby": {"duty_sequence": [1, 2, 1, 2]},
                },
            },
        },
        {
            "target_id": "dense_automators",
            "confidence": 0.80,
            "parameters": {
                "family_id": 4,
                "family_name": "Dense Automators",
                "cc11_per_note": "5.1-14.9",
                "cc12_per_note": "<0.5",
                "pulse": {
                    "attack_frames": 0,
                    "decay_frames": 2,
                    "sustain_vol": 6,
                    "release_frames": 2,
                    "duty_default": 2,
                    "duty_animated": False,
                    "envelope_mode": "sw_obsessive",
                },
                "triangle": {"gate_only": True},
                "noise": {"velocity_driven": True, "decay_frames": 3},
                "cc11_behavior": "high_frequency_stream",
                "cc12_behavior": "set_once_at_onset",
                "example_games": ["Final Fantasy", "Batman", "Blaster Master", "Metroid"],
                "notes": "Near-continuous CC11. Single ADSR insufficient for keyboard — use multi-stage.",
                "game_variants": {
                    "final_fantasy": {"sustain_fade": True, "sustain_vol": 6},
                    "batman": {"decay_frames": 1, "sustain_vol": 3, "sustain_modulation": True},
                    "metroid": {"decay_frames": 3, "sustain_vol": 7},
                },
            },
        },
        {
            "target_id": "full_animation",
            "confidence": 0.85,
            "parameters": {
                "family_id": 5,
                "family_name": "Full Animation",
                "cc11_per_note": ">7.0",
                "cc12_per_note": ">1.0",
                "pulse": {
                    "attack_frames": 0,
                    "attack_vol": 15,
                    "decay_frames": 2,
                    "sustain_vol": 8,
                    "sustain_modulation": True,
                    "release_frames": 0,
                    "duty_default": 1,
                    "duty_animated": True,
                    "duty_sequence": [1, 2, 2, 2],
                    "envelope_mode": "sw_both_axes",
                },
                "triangle": {"gate_only": True},
                "noise": {"velocity_driven": True, "decay_frames": 3},
                "cc11_behavior": "full_frame_rate",
                "cc12_behavior": "full_frame_rate",
                "example_games": ["Super Mario Bros 3"],
                "notes": "Both axes full frame rate. Most complex preset. Benchmark for synth testing.",
                "game_variants": {
                    "smb3": {
                        "attack_vol": 15,
                        "decay_frames": 2,
                        "sustain_vol": 8,
                        "duty_sequence": [1, 2, 2, 2],
                    },
                },
            },
        },
    ]

    for f in families:
        c.execute(
            "INSERT INTO synth_patches (target_scope, target_id, parameters_json, provenance, confidence) VALUES (?, ?, ?, ?, ?)",
            ("family", f["target_id"], json.dumps(f["parameters"], indent=2), "trace-derived", f["confidence"]),
        )

    db.commit()
    print(f"Inserted {len(families)} family presets into synth_patches")

    # Verify
    c.execute("SELECT id, target_scope, target_id, confidence FROM synth_patches")
    for row in c.fetchall():
        print(f"  #{row[0]}: {row[1]}/{row[2]} (confidence={row[3]})")

    db.close()


if __name__ == "__main__":
    main()
