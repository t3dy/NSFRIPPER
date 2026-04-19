#!/usr/bin/env python3
"""Initialize the keyboard_lab SQLite database.

Single-purpose DB for the "play NES games live with a MIDI keyboard"
problem.  Tracks approaches, experiments, ear-tests, and decisions.

Schema (all tables 1-indexed):

  approaches       WHAT synthesizer/plugin technique is being evaluated.
                   e.g. "ReapNES_APU2_v2_priority3_ADSR",
                        "Plogue_chipsounds",
                        "FamiStudio_stems+live_ADSR",
                        "Triforce_VSTi".

  presets          Per-approach per-driver-family knob settings.
                   Each preset is a JSON blob of slider values
                   calibrated to match one driver family's character.

  experiments     A single ear-test session: keyboard + approach + preset
                   + game reference + rating.

  game_refs        Reference games for ear-testing, with expected
                   character notes (e.g. "Battletoads pulse1 bright,
                   fast decay, duty=2").

  keyboards        Physical MIDI keyboards tested with.  We care because
                   latency / CC-knob count / velocity curve all affect
                   the live experience.

  findings         Structured observations per experiment, tagged by
                   dimension (latency_feel, sound_accuracy,
                   playability, timbral_range, etc.).

The DB is the single source of truth for "what we've tried, what
worked, what didn't" on the live-play problem.
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "keyboard.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS approaches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,      -- 'jsfx', 'vsti', 'hardware', 'hybrid'
    cost_usd INTEGER DEFAULT 0,
    latency_ms REAL,
    sound_quality TEXT,          -- 'S', 'A', 'B', 'C'
    live_play_supported INTEGER DEFAULT 1,
    midi_keyboard_supported INTEGER DEFAULT 1,
    notes TEXT,
    added_date TEXT DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    approach_id INTEGER NOT NULL REFERENCES approaches(id),
    driver_family TEXT NOT NULL,  -- 'capcom_early', 'konami', 'rare', ...
    name TEXT NOT NULL,
    slider_json TEXT,             -- per-approach slider state as JSON
    calibration_game TEXT,        -- which game this was tuned against
    notes TEXT
);

CREATE TABLE IF NOT EXISTS game_refs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    driver_family TEXT NOT NULL,
    primary_channel TEXT,         -- 'pulse1', 'pulse2', 'triangle', 'noise', 'dmc'
    character_notes TEXT,         -- 'bright pulse, fast decay, duty=2'
    reference_song TEXT           -- canonical song to A/B with
);

CREATE TABLE IF NOT EXISTS keyboards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    brand TEXT,
    keys INTEGER,
    cc_knobs INTEGER,
    velocity_curve TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    approach_id INTEGER NOT NULL REFERENCES approaches(id),
    preset_id INTEGER REFERENCES presets(id),
    keyboard_id INTEGER REFERENCES keyboards(id),
    game_ref_id INTEGER NOT NULL REFERENCES game_refs(id),
    session_date TEXT DEFAULT CURRENT_DATE,
    overall_rating INTEGER,        -- 1-10
    tester TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER NOT NULL REFERENCES experiments(id),
    dimension TEXT NOT NULL,       -- 'latency_feel', 'sound_accuracy', ...
    score INTEGER,                 -- 1-10 per dimension
    detail TEXT
);

CREATE INDEX IF NOT EXISTS idx_experiments_approach
    ON experiments(approach_id);
CREATE INDEX IF NOT EXISTS idx_findings_experiment
    ON findings(experiment_id);
CREATE INDEX IF NOT EXISTS idx_game_refs_family
    ON game_refs(driver_family);
"""

SEED_APPROACHES = [
    # (name, category, cost, notes)
    ("ReapNES_APU2_v2_Priority1_SysEx",  "jsfx",     0,
     "File playback only; SysEx bit-accurate replay.  Not a live-play option."),
    ("ReapNES_APU2_v2_Priority2_CCauto", "jsfx",     0,
     "File playback with CC11/CC12 automation.  Layer keyboard on top limited."),
    ("ReapNES_APU2_v2_Priority3_ADSR",   "jsfx",     0,
     "The actual live-keyboard path.  ADSR envelope from slider presets."),
    ("Plogue_chipsounds",                 "vsti",    95,
     "Commercial reference-grade NES VSTi.  Not yet tested."),
    ("Tweakbench_Triforce",               "vsti",     0,
     "Free NES-style VSTi.  Not yet tested."),
    ("FamiStudio_live",                   "vsti",     0,
     "FamiStudio has a VST build.  Not yet tested."),
    ("NES_SoundFont_via_sforzando",       "vsti",     0,
     "Community SF2 NES samples.  Quick to test."),
    ("Vital_wavetable",                   "vsti",     0,
     "Custom NES-shaped wavetables in Vital.  Not yet tested."),
    ("MIDINES_hardware_bridge",           "hardware", 150,
     "USB-MIDI cartridge for real NES.  Highest fidelity; hardware cost."),
    ("Hybrid_JSFX_chipsounds_layer",      "hybrid",   95,
     "Layer JSFX for primary tone + chipsounds for color.  Untested."),
]

SEED_GAME_REFS = [
    # (slug, driver_family, primary_channel, character, reference_song)
    ("Battletoads",            "rare",           "pulse1",
     "Progressive prog-metal chiptune, fast duty animation, prominent noise",
     "Pause Theme"),
    ("Castlevania",            "konami_kondo",   "pulse1",
     "Classical-style leads, triangle staccato bass, clean pulse",
     "Vampire Killer"),
    ("Mega_Man_2",             "capcom_early",   "pulse1",
     "Melodic leads, distinctive duty choices, per-frame $4015 refresh",
     "Dr. Wily Stage 1"),
    ("Super_Mario_Bros",       "nintendo_kondo", "pulse1",
     "Warm duty=2, moderate decay, iconic triangle bass",
     "Overworld"),
    ("Zelda_II",               "nintendo_late",  "pulse1",
     "Arpeggiated leads, Continuous $4015 refresh",
     "Palace Theme"),
    ("DuckTales",              "capcom_early",   "pulse1",
     "Bright pulse leads, dense CC automation",
     "Moon Theme"),
    ("Journey_to_Silius",      "sunsoft_late",   "dmc",
     "Heavy DMC DAC bass + DPCM samples",
     "Stage 1"),
    ("Ninja_Gaiden",           "tecmo_follin",   "noise",
     "Extremely dense noise percussion",
     "Act 1-1"),
    ("Final_Fantasy",          "square",         "pulse1",
     "Sustained melodic leads, minimal drums",
     "Prelude"),
    ("Gimmick",                "sunsoft_5b",     "pulse1",
     "Follin-composed, 5B expansion audio, complex timbres",
     "Strange Memories"),
]


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(SCHEMA)
    conn.commit()

    # Seed approaches (idempotent via INSERT OR IGNORE)
    cur = conn.cursor()
    for name, cat, cost, notes in SEED_APPROACHES:
        cur.execute(
            "INSERT OR IGNORE INTO approaches (name, category, cost_usd, notes) "
            "VALUES (?, ?, ?, ?)",
            (name, cat, cost, notes)
        )
    for slug, fam, chan, char, ref in SEED_GAME_REFS:
        cur.execute(
            "INSERT OR IGNORE INTO game_refs "
            "(slug, driver_family, primary_channel, character_notes, reference_song) "
            "VALUES (?, ?, ?, ?, ?)",
            (slug, fam, chan, char, ref)
        )
    conn.commit()

    print(f"Initialized DB at {DB_PATH}")
    cur.execute("SELECT COUNT(*) FROM approaches")
    print(f"  approaches: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM game_refs")
    print(f"  game_refs:  {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM experiments")
    print(f"  experiments: {cur.fetchone()[0]}")

    conn.close()


if __name__ == "__main__":
    main()
