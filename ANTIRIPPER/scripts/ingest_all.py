#!/usr/bin/env python3
"""Ingest all project documentation, game data, and knowledge into antiripper_v2.db.

Populates:
- hardware_facts: immutable NES APU truths from architecture.md
- driver_families: all 5 families from driver_survey.py classification
- prevention_patterns: guardrails from MISTAKEBAKED.md
- evidence_items: all game output directories + expansion audit
- decision_records: route decisions for surveyed games
- concept_bridges: human-to-NES term mappings

Safe to re-run: uses INSERT OR IGNORE / INSERT OR REPLACE where appropriate.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

ANTIRIPPER_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = ANTIRIPPER_DIR.parent
DB_PATH = ANTIRIPPER_DIR / "antiripper_v2.db"
SCHEMA_PATH = ANTIRIPPER_DIR / "SCHEMA_V2.sql"

# Add repo root to path for imports
sys.path.insert(0, str(REPO_ROOT))


def ensure_db():
    """Create DB and schema if needed."""
    if not DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        conn.executescript(SCHEMA_PATH.read_text())
        conn.close()
        print(f"Created {DB_PATH}")

    # Ensure attempts table exists
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript("""
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
    """)
    conn.close()


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ingest_hardware_facts(conn):
    """Insert immutable NES APU hardware facts with subsystem tags."""
    # (statement, formula, source_reference, relevant_subsystems)
    facts = [
        ("Triangle channel divisor is 32 (not 16)",
         "freq = 1789773 / (32 * (period + 1))",
         "NESDev APU Ref, architecture.md Rule 5",
         "parser,synth,routing"),
        ("Pulse channel divisor is 16",
         "freq = 1789773 / (16 * (period + 1))",
         "NESDev APU Ref, architecture.md Rule 22",
         "parser,synth,routing"),
        ("Triangle is always 1 octave lower than pulse for same period",
         "32-step sequencer (triangle) vs 16-step (pulse)",
         "NESDev APU Ref, architecture.md Rule 5",
         "parser,routing"),
        ("Period < 8 silences pulse channels",
         "Timer periods below 8 produce ultrasonic output filtered by the DAC",
         "NESDev Pulse Channel Reference",
         "synth,routing"),
        ("NTSC CPU clock is 1,789,773 Hz",
         "CPU_CLK = 1789773",
         "NESDev wiki",
         "all"),
        ("APU frame rate is 60 Hz (NTSC)",
         "1 frame = 1/60 second = 29829.55 CPU cycles",
         "NESDev APU Frame Counter",
         "timing"),
        ("Pulse duty cycle has 4 settings",
         "Bits 6-7 of $4000/$4004: 12.5%, 25%, 50%, 75%",
         "NESDev APU Pulse",
         "synth"),
        ("Noise period index is XORed with 0x0F before APU write",
         "Index 0 = longest period (lowest pitch), 15 = shortest (highest)",
         "FamiTracker source, synth_fidelity.md Rule 9",
         "synth,parser"),
        ("APU non-linear pulse mixing",
         "95.88 / ((8128.0 / (sq1 + sq2)) + 100.0)",
         "FamiTracker source, NESDev wiki, architecture.md Rule 20",
         "synth"),
        ("APU non-linear TND mixing",
         "159.79 / ((1.0 / ((tri/8227) + (noise/12241) + (dpcm/22638))) + 100.0)",
         "FamiTracker source, NESDev wiki, architecture.md Rule 20",
         "synth"),
        ("$4000 bit 5 controls envelope mode",
         "0 = hardware decay (linear), 1 = constant volume (software)",
         "NESDev APU Envelope",
         "parser,synth"),
        ("$400E bit 7 controls noise mode",
         "0 = long LFSR (hissy/white), 1 = short LFSR (tonal/metallic)",
         "NESDev APU Noise",
         "synth,parser"),
        ("VRC6 pulse has 8 duty settings (3-bit)",
         "Pulse width from 1/16 to 8/16 (6.25% to 50%)",
         "NESDev VRC6 Audio",
         "synth"),
        ("VRC6 sawtooth uses 6-bit accumulator",
         "Rate added 2x per step, 7 steps per cycle. Output = top 5 bits.",
         "NESDev VRC6 Audio",
         "synth"),
        ("FDS wavetable is 64 samples x 6-bit",
         "Volume gain 0-63 clamped at 32. Output ~2.4x single APU pulse.",
         "NESDev FDS Audio",
         "synth"),
        ("VRC7 volume is inverted (0=loudest, 15=silent)",
         "4-bit volume, 3dB per step. Built-in per-operator ADSR.",
         "NESDev VRC7 Audio",
         "synth"),
    ]

    # Add column if missing (safe migration for existing DBs)
    try:
        conn.execute("ALTER TABLE hardware_facts ADD COLUMN relevant_subsystems TEXT NOT NULL DEFAULT 'all'")
    except sqlite3.OperationalError:
        pass  # column already exists

    conn.execute("DELETE FROM hardware_facts")
    conn.executemany(
        "INSERT INTO hardware_facts (statement, formula, source_reference, relevant_subsystems, locked) VALUES (?, ?, ?, ?, 1)",
        facts,
    )
    print(f"  hardware_facts: {len(facts)} rows")


def ingest_driver_families(conn):
    """Insert all 5 driver families."""
    families = [
        ("hardware_envelope", "0.0 - 2.8", "< 0.5", True, False, False,
         "NSF sufficient. Low automation = little to go wrong. ADSR synth mode.",
         "High"),
        ("standard_envelope", "2.8 - 5.6", "< 0.5", False, False, False,
         "NSF sufficient. Check CC11 envelope shape per note. CC11 synth mode.",
         "High"),
        ("duty_animators", "3.7 - 4.9", "0.7 - 1.0", False, True, False,
         "NSF sufficient. Check CC12 duty animation. CC11+CC12 synth mode.",
         "High"),
        ("dense_automators", "5.1 - 14.9", "< 0.5", False, False, True,
         "NSF may diverge. Many CC events. Risk of MIDI size explosion. Seek VGM/Mesen cross-validation.",
         "Low"),
        ("full_animation", "> 7.0", "> 1.0", False, True, True,
         "NSF may diverge. Both axes dense. Highest risk of extraction artifacts. CC11+CC12 synth mode.",
         "Low"),
    ]

    conn.execute("DELETE FROM driver_families")
    conn.executemany(
        """INSERT INTO driver_families
           (slug, cc11_range, cc12_range, uses_hardware_envelope, animates_duty,
            high_density_volume, validation_implications, nsf_trust_level)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        families,
    )
    print(f"  driver_families: {len(families)} rows")


def ingest_prevention_patterns(conn):
    """Insert prevention patterns from MISTAKEBAKED.md and architecture rules."""
    patterns = [
        # From MISTAKEBAKED.md
        ("Dump trace data before modeling",
         "Starting to model envelope behavior for a new game",
         "parser",
         "Extract actual APU register values for specific frames before hypothesizing",
         5, "Guessed 3 envelope hypotheses before looking at actual frame data"),
        ("Same driver does not mean same ROM layout",
         "Applying parser from one game to another",
         "parser",
         "Check manifest, verify pointer table format, DX byte count, percussion system",
         3, "Ran CV1 parser on 4 other ROMs expecting it to work"),
        ("Same period table does not prove same driver",
         "Finding matching period table in a new ROM",
         "parser",
         "Period tables are shared across drivers. Check command format, not just data tables.",
         4, "Spent rounds scanning CV2 for Maezawa pointer table that doesn't exist"),
        ("Read the disassembly before guessing",
         "Starting to parse any ROM or driver",
         "parser",
         "Check references/ for existing disassembly. Read before writing code.",
         3, "Assumed Contra DX reads 2 bytes (CV1 format) instead of 3"),
        ("Check all channels not just one",
         "Validating parser output",
         "parser",
         "Test every channel. Bugs may be channel-specific.",
         2, "E8 envelope gate looked correct on Sq1, was wrong for Sq2"),
        ("Automated tests cannot catch systematic errors",
         "Claiming correctness from test results alone",
         "routing",
         "An octave-wide pitch error produces zero trace mismatches. User must compare to game.",
         3, "Octave was wrong by exactly 12 semitones but trace comparison showed zero mismatches"),
        ("Always version output files",
         "Generating MIDI, RPP, or WAV output",
         "routing",
         "Use v1, v2 suffixes. Never overwrite a tested file.",
         2, "Overwrote Contra MIDI/RPP files, user couldn't compare versions"),
        ("Triangle is one octave lower than pulse",
         "Any pitch mapping involving triangle channel",
         "routing",
         "Subtract 12 semitones for triangle. This is hardware fact, not convention.",
         2, "Changed BASE_MIDI_OCTAVE4 and broke triangle pitch"),
        # From architecture.md rules
        ("Zero parse errors is not musical correctness",
         "Parser reports zero errors or zero desync",
         "parser",
         "Zero errors proves byte-stream structure only. Run execution semantics validation.",
         5, "Battletoads v3: 955 notes, 0 errors, but duration 1.52x wrong and arpeggio unmodeled"),
        ("Parser output is a hypothesis until validated",
         "Generating MIDI from parsed ROM data",
         "routing",
         "Label as hypothesis output. Do not claim correctness until Rung 3+ validation.",
         4, "Treated 955 notes 0 errors as proof when base notes never sounded as parsed"),
        ("Never skip Frame IR between trace and MIDI",
         "Converting trace data to MIDI",
         "routing",
         "Raw register changes are not musical events. Frame IR interprets hardware into music.",
         3, "Direct period-change-to-note conversion (Battletoads v3-v5 failure mode)"),
        ("Do not assume CC12 maps dynamically for Sunsoft drivers",
         "Any lookup table interpretation in synth",
         "synth",
         "Ensure lookup arrays span proper indices preventing index out of bounds.",
         5, "Castlevania blank frames from CC12 mapping error"),
        ("Different ROMs use different music engines",
         "Applying any universal decoding model",
         "parser",
         "Support per-game/per-engine profiles. Konami, Rare, Capcom all differ.",
         3, "Assumed one decoder model would work across all games"),
        ("Noise is a separate semantic domain",
         "Validating noise channel through melodic pipeline",
         "parser",
         "Noise has period index, mode bit, hit detection — not pitch contour.",
         2, "W&W: 48/48 melodic matches coexisted with partial noise semantics"),
    ]

    conn.execute("DELETE FROM prevention_patterns")
    conn.executemany(
        """INSERT INTO prevention_patterns
           (description, trigger_condition, affected_subsystem,
            recommended_action, prompt_cost, example_failure)
           VALUES (?, ?, ?, ?, ?, ?)""",
        patterns,
    )
    print(f"  prevention_patterns: {len(patterns)} rows")


def ingest_concept_bridges(conn):
    """Insert human-to-NES term mappings."""
    bridges = [
        ("volume", "$4000/$4004 bits 0-3", "4-bit volume (0-15). Mapped to CC11 (0-127) in MIDI."),
        ("duty cycle", "$4000/$4004 bits 6-7", "Pulse wave shape. 4 settings: 12.5%, 25%, 50%, 75%. Mapped to CC12."),
        ("pitch", "timer period register", "NES uses timer period (inverse of frequency). Lower period = higher pitch."),
        ("envelope", "$4000 bit 5 + bits 0-3", "Bit 5=0: hardware linear decay. Bit 5=1: constant (software controls volume)."),
        ("note duration", "frames at constant period", "A note lasts as long as the period register holds the same value."),
        ("triangle gate", "$4008 linear counter", "Triangle has no volume control — only on/off via linear counter."),
        ("noise hit", "$400E period index + $400C volume", "Noise drum: set period index for pitch, volume for attack, let decay."),
        ("sweep", "$4001/$4005", "Hardware pitch slide on pulse channels. Period changes automatically."),
        ("DPCM sample", "$4010-$4013 + $4015 bit 4", "Delta-modulated audio from ROM. Used for drums, bass, vocal clips."),
        ("DAC write", "$4011 direct", "Software writes 7-bit value to output. Used for algorithmic synthesis."),
        ("frame", "1/60 second (NTSC)", "The fundamental time unit. All NES audio is quantized to frames."),
        ("driver", "sound engine code in ROM", "The software that reads music data and writes APU registers every frame."),
        ("NSF", "NES Sound Format", "Container that wraps just the sound driver + music data from a ROM."),
        ("CC11", "MIDI Control Change 11", "Expression. Maps to NES per-frame volume. Our primary envelope encoding."),
        ("CC12", "MIDI Control Change 12", "Effect Control 1. Maps to NES per-frame duty cycle."),
        ("SysEx", "MIDI System Exclusive", "Raw APU register state encoded in MIDI. Lossless but needs custom synth."),
        ("Frame IR", "intermediate representation", "Interpreted musical events between raw traces and MIDI output."),
    ]

    conn.execute("DELETE FROM concept_bridges")
    conn.executemany(
        "INSERT INTO concept_bridges (human_term, nes_equivalent, explanation) VALUES (?, ?, ?)",
        bridges,
    )
    print(f"  concept_bridges: {len(bridges)} rows")


def classify_family(cc11, cc12):
    """Classify a game into a driver family slug."""
    if cc11 > 7.0 and cc12 > 1.0:
        return "full_animation"
    elif cc11 > 5.0 and cc12 < 0.5:
        return "dense_automators"
    elif 3.5 <= cc11 <= 5.0 and cc12 >= 0.5:
        return "duty_animators"
    elif cc11 > 2.8:
        return "standard_envelope"
    else:
        return "hardware_envelope"


def ingest_game_evidence(conn):
    """Register all game output directories and survey data as evidence."""
    output_dir = REPO_ROOT / "output"
    survey_path = REPO_ROOT / "data" / "driver_survey.json"
    expansion_path = REPO_ROOT / "data" / "expansion_audit.json"

    # Load survey data
    survey_by_slug = {}
    if survey_path.exists():
        survey = json.loads(survey_path.read_text())
        for g in survey:
            survey_by_slug[g["game"]] = g

    # Load expansion audit
    expansion_by_slug = {}
    if expansion_path.exists():
        audit = json.loads(expansion_path.read_text())
        # Build lookup from per_chip lists
        for chip, games in audit.get("per_chip", {}).items():
            for g in games:
                slug = g["game_slug"]
                if slug not in expansion_by_slug:
                    expansion_by_slug[slug] = []
                expansion_by_slug[slug].append(chip)

    # Clear and rebuild evidence
    conn.execute("DELETE FROM evidence_items")
    conn.execute("DELETE FROM decision_records")

    evidence_count = 0
    decision_count = 0

    for game_dir in sorted(output_dir.iterdir()):
        if not game_dir.is_dir():
            continue
        slug = game_dir.name

        # Check what output exists
        has_nsf = (game_dir / "nsf").is_dir() and any((game_dir / "nsf").glob("*.nsf"))
        has_midi = (game_dir / "midi").is_dir() and any((game_dir / "midi").glob("*.mid"))
        has_reaper = (game_dir / "reaper").is_dir() and any((game_dir / "reaper").glob("*.rpp"))
        has_wav = (game_dir / "wav").is_dir() and any((game_dir / "wav").glob("*.wav"))
        has_trace = (game_dir / "rom_capture").is_dir()

        # Build metrics
        survey_data = survey_by_slug.get(slug, {})
        nsf_info = survey_data.get("nsf", {})
        profile = survey_data.get("driver_profile", {})

        # Register NSF evidence
        if has_nsf:
            nsf_files = list((game_dir / "nsf").glob("*.nsf"))
            expansion_chips = expansion_by_slug.get(slug, [])
            metrics = {
                "total_songs": nsf_info.get("total_songs", len(nsf_files)),
                "title": nsf_info.get("title", slug),
                "artist": nsf_info.get("artist", ""),
                "expansion_chips": expansion_chips,
                "expansion_byte": sum(
                    1 << {"VRC6": 0, "VRC7": 1, "FDS": 2, "MMC5": 3, "N163": 4, "5B": 5}.get(c, 0)
                    for c in expansion_chips
                ) if expansion_chips else 0,
            }
            conn.execute(
                "INSERT INTO evidence_items (game_slug, type, source_path, metrics_json) VALUES (?, ?, ?, ?)",
                (slug, "nsf", str(nsf_files[0]), json.dumps(metrics)),
            )
            evidence_count += 1

        # Register MIDI evidence
        if has_midi:
            midi_files = list((game_dir / "midi").glob("*.mid"))
            metrics = {
                "midi_count": len(midi_files),
                "songs_extracted": survey_data.get("songs_extracted", len(midi_files)),
                "total_notes": survey_data.get("total_notes", 0),
            }
            if profile:
                metrics["avg_cc11_per_note"] = profile.get("avg_cc11_per_note", 0)
                metrics["avg_cc12_per_note"] = profile.get("avg_cc12_per_note", 0)
                metrics["envelope_type"] = profile.get("envelope_type", "")
                metrics["driver_family"] = classify_family(
                    profile.get("avg_cc11_per_note", 0),
                    profile.get("avg_cc12_per_note", 0),
                )
            conn.execute(
                "INSERT INTO evidence_items (game_slug, type, source_path, metrics_json) VALUES (?, ?, ?, ?)",
                (slug, "metric", str(game_dir / "midi"), json.dumps(metrics)),
            )
            evidence_count += 1

        # Register trace evidence
        if has_trace:
            conn.execute(
                "INSERT INTO evidence_items (game_slug, type, source_path, metrics_json) VALUES (?, ?, ?, ?)",
                (slug, "trace", str(game_dir / "rom_capture"), "{}"),
            )
            evidence_count += 1

        # Log extraction route decision based on what exists
        if profile:
            family = classify_family(
                profile.get("avg_cc11_per_note", 0),
                profile.get("avg_cc12_per_note", 0),
            )
            trust = "High" if family in ("hardware_envelope", "standard_envelope", "duty_animators") else "Low"
            route = "nsf" if trust == "High" else "nsf (cross-validation recommended)"
            if has_trace:
                route = "nsf + mesen trace"

            conn.execute(
                """INSERT INTO decision_records
                   (game_slug, decision_type, rationale, outcome)
                   VALUES (?, 'extraction_route', ?, ?)""",
                (slug,
                 f"Family: {family}, NSF trust: {trust}. Route: {route}.",
                 "extracted" if has_midi else "pending"),
            )
            decision_count += 1

    print(f"  evidence_items: {evidence_count} rows")
    print(f"  decision_records: {decision_count} rows")
    return evidence_count


def main():
    ensure_db()
    conn = get_connection()

    print("Ingesting into antiripper_v2.db...")
    print()

    ingest_hardware_facts(conn)
    ingest_driver_families(conn)
    ingest_prevention_patterns(conn)
    ingest_concept_bridges(conn)
    ingest_game_evidence(conn)

    conn.commit()
    conn.close()

    # Summary
    print()
    conn = get_connection()
    for table in ["hardware_facts", "driver_families", "prevention_patterns",
                   "concept_bridges", "evidence_items", "decision_records",
                   "claims", "attempts"]:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table:25s} {count:5d} rows")
        except Exception:
            print(f"  {table:25s} TABLE MISSING")
    conn.close()
    print()
    print("Done.")


if __name__ == "__main__":
    main()
