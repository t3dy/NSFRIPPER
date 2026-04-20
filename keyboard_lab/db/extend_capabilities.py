#!/usr/bin/env python3
"""Extend keyboard.db with PAL capability tracking.

Adds two tables that track, per approach, which of the 17 PAL
dimensions (docs/PERFORMANCE_ABSTRACTION_LAYER.md) the approach
supports and at what coverage level.

Schema:

  capabilities
    id, code, name, pal_class, description
    -- seeded with the 17 dimensions from the PAL doc

  approach_capabilities
    approach_id, capability_id, coverage, notes, verified_date
    -- coverage is one of: exact, approximate, preset_only, unsupported
    -- verified_date is the ear-test date when coverage was confirmed

Run this AFTER init_keyboard_db.py to extend the existing DB.
Idempotent: re-running only adds new tables / rows.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "keyboard.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS capabilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,       -- 'pitch', 'duty_static', etc.
    name TEXT NOT NULL,
    pal_class TEXT NOT NULL,         -- 'A' (live), 'B' (macro), 'C' (preset), 'D' (non-performable)
    description TEXT
);

CREATE TABLE IF NOT EXISTS approach_capabilities (
    approach_id INTEGER NOT NULL REFERENCES approaches(id),
    capability_id INTEGER NOT NULL REFERENCES capabilities(id),
    coverage TEXT NOT NULL CHECK (
        coverage IN ('exact', 'approximate', 'preset_only', 'unsupported')
    ),
    notes TEXT,
    verified_date TEXT,
    PRIMARY KEY (approach_id, capability_id)
);

CREATE INDEX IF NOT EXISTS idx_capabilities_class
    ON capabilities(pal_class);
CREATE INDEX IF NOT EXISTS idx_ac_approach
    ON approach_capabilities(approach_id);
CREATE INDEX IF NOT EXISTS idx_ac_capability
    ON approach_capabilities(capability_id);
"""

# Seeded capabilities, directly from
# docs/PERFORMANCE_ABSTRACTION_LAYER.md §"The seventeen performable
# dimensions - classification".  code, name, pal_class, description.
CAPABILITIES = [
    ("pitch",              "Note pitch (period register)",         "A",
     "Keyboard note_on pitch maps to NES period register"),
    ("timing",             "Note timing (attack/release)",         "A",
     "note_on / note_off directly drive gate"),
    ("volume",             "Volume amplitude",                     "A",
     "Velocity sets initial volume; aftertouch modulates held volume"),
    ("duty_static",        "Duty cycle value (static)",            "C",
     "Default duty cycle set by preset slider; not live-changeable"),
    ("duty_animation",     "Duty cycle animation (per-frame)",     "B",
     "Driver-style per-frame duty flipping; triggered by pad/macro"),
    ("attack_transient",   "Attack transient / phase reset",       "A",
     "Velocity-scaled 1-2 ms spike + optional phase reset on note-on"),
    ("envelope_shape",     "Envelope decay curve shape",           "C",
     "ADSR slider values per preset"),
    ("release",            "Envelope release",                     "C",
     "Preset slider"),
    ("sweep_pitch",        "Sweep unit pitch modulation",          "B",
     "Pitch bend (coarse) + preset-shaped sweep rate"),
    ("vibrato",            "Vibrato (software tremolo)",           "A",
     "Aftertouch depth; automatic note-age-based ramp available"),
    ("arpeggio",           "Arpeggio / chord illusion",            "B",
     "Multi-note hold + mod-wheel rate = arp engine output"),
    ("noise_pitch",        "Noise period index (pitch)",           "A",
     "Note-to-period mapping in live preset; non-tonal semantics"),
    ("noise_mode",         "Noise mode (long/short LFSR)",         "C",
     "Preset switch; can't change mode on a held note"),
    ("noise_length",       "Noise length-counter silencing",       "B",
     "Velocity → burst length or pad → preset-silence macro"),
    ("dmc_trigger",        "DMC sample trigger",                   "B",
     "Per-sample pad keyswitch fires a DPCM sample"),
    ("dmc_dac_value",      "DMC DAC direct value",                 "D",
     "Not performable live; requires file SysEx"),
    ("frame_sequencing",   "Frame-accurate register sequencing",   "D",
     "Not performable live; requires file SysEx"),
]

# Initial approach_capabilities seed: what the CURRENT JSFX supports
# honestly in Priority 3 mode.  This is the baseline the PAL measures
# against.  Coverage verified 2026-04-19 by code inspection
# (ReapNES_APU2_v2.jsfx); ear-test flags in keyboard_lab/db/experiments.
#
# Format: (approach_name, capability_code, coverage, notes)
JSFX_P3_BASELINE = [
    ("ReapNES_APU2_v2_Priority3_ADSR", "pitch",            "exact",
     "Direct note_on → period calculation"),
    ("ReapNES_APU2_v2_Priority3_ADSR", "timing",           "exact",
     "Direct note_on/note_off → gate"),
    ("ReapNES_APU2_v2_Priority3_ADSR", "volume",           "approximate",
     "Velocity-driven ADSR; loses per-frame register-level envelope quirks"),
    ("ReapNES_APU2_v2_Priority3_ADSR", "duty_static",      "preset_only",
     "Sliders 3/9 per-channel duty; not CC-mappable yet"),
    ("ReapNES_APU2_v2_Priority3_ADSR", "duty_animation",   "unsupported",
     "No macro subsystem yet.  Class B dimension awaiting implementation."),
    ("ReapNES_APU2_v2_Priority3_ADSR", "attack_transient", "approximate",
     "Slider 20 two-phase attack exists; velocity-scaling not yet wired."),
    ("ReapNES_APU2_v2_Priority3_ADSR", "envelope_shape",   "preset_only",
     "Sliders 5-8/11-14 per pulse ADSR."),
    ("ReapNES_APU2_v2_Priority3_ADSR", "release",          "preset_only",
     "Sliders 8/14."),
    ("ReapNES_APU2_v2_Priority3_ADSR", "sweep_pitch",      "unsupported",
     "No sweep in P3 yet; SysEx-only in P1."),
    ("ReapNES_APU2_v2_Priority3_ADSR", "vibrato",          "unsupported",
     "Aftertouch not yet routed.  Class A dimension awaiting implementation."),
    ("ReapNES_APU2_v2_Priority3_ADSR", "arpeggio",         "unsupported",
     "No arp engine yet.  Class B dimension awaiting implementation."),
    ("ReapNES_APU2_v2_Priority3_ADSR", "noise_pitch",      "approximate",
     "Note-to-period via natural mapping in noise channel mode."),
    ("ReapNES_APU2_v2_Priority3_ADSR", "noise_mode",       "preset_only",
     "Part of preset."),
    ("ReapNES_APU2_v2_Priority3_ADSR", "noise_length",     "unsupported",
     "No burst-length control.  Class B dimension awaiting implementation."),
    ("ReapNES_APU2_v2_Priority3_ADSR", "dmc_trigger",      "unsupported",
     "DMC in Priority 3 not implemented.  Class B dimension."),
    ("ReapNES_APU2_v2_Priority3_ADSR", "dmc_dac_value",    "unsupported",
     "Correctly unsupported (Class D)."),
    ("ReapNES_APU2_v2_Priority3_ADSR", "frame_sequencing", "unsupported",
     "Correctly unsupported (Class D)."),
]


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(SCHEMA)

    cur = conn.cursor()
    for code, name, pal_class, desc in CAPABILITIES:
        cur.execute(
            "INSERT OR IGNORE INTO capabilities (code, name, pal_class, description) "
            "VALUES (?, ?, ?, ?)",
            (code, name, pal_class, desc)
        )

    # Seed JSFX P3 baseline coverage
    for approach_name, cap_code, coverage, notes in JSFX_P3_BASELINE:
        approach_row = cur.execute(
            "SELECT id FROM approaches WHERE name = ?",
            (approach_name,)
        ).fetchone()
        cap_row = cur.execute(
            "SELECT id FROM capabilities WHERE code = ?",
            (cap_code,)
        ).fetchone()
        if approach_row and cap_row:
            cur.execute(
                "INSERT OR IGNORE INTO approach_capabilities "
                "(approach_id, capability_id, coverage, notes, verified_date) "
                "VALUES (?, ?, ?, ?, '2026-04-19')",
                (approach_row[0], cap_row[0], coverage, notes)
            )

    conn.commit()

    # Summary
    cur.execute("SELECT COUNT(*) FROM capabilities")
    n_caps = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM approach_capabilities")
    n_ac = cur.fetchone()[0]
    print(f"Capabilities: {n_caps}")
    print(f"Approach-capability rows: {n_ac}")

    # Coverage matrix for the one approach seeded
    print("\nJSFX Priority 3 ADSR coverage by PAL class:")
    for cls in ("A", "B", "C", "D"):
        cur.execute(
            "SELECT ac.coverage, COUNT(*) FROM approach_capabilities ac "
            "JOIN capabilities c ON ac.capability_id = c.id "
            "WHERE c.pal_class = ? GROUP BY ac.coverage",
            (cls,)
        )
        rows = list(cur.fetchall())
        rstr = ", ".join(f"{cov}={n}" for cov, n in rows)
        print(f"  Class {cls}: {rstr}")

    conn.close()


if __name__ == "__main__":
    main()
