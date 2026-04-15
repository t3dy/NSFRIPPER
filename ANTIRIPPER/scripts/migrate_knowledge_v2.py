import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_selective_knowledge(db_path="antiripper_v2.db"):
    # Target only V2 Strict Schema Tables
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 1. Hardware Facts (Immutable)
    hardware_facts = [
        ("Triangle Channel Output", "freq = 1789773 / (32 * (period + 1))", "NESDev APU Ref"),
        ("Pulse Range Boundary", "Period < 8 silences the channel.", "NESDev Pulse Ref")
    ]
    cur.executemany("INSERT INTO hardware_facts (statement, formula, source_reference, locked) VALUES (?, ?, ?, 1)", hardware_facts)
    
    # 2. Driver Families 
    families = [
        ("minimal", "0.0 - 0.5", "0.0", 0, 0, 0, "Trace trace generally matches NSF", "High"),
        ("dense_automators", "5.1 - 15.0", "0.0", 1, 0, 1, "Requires highest precision per-frame timing.", "Low")
    ]
    cur.executemany("INSERT INTO driver_families (slug, cc11_range, cc12_range, uses_hardware_envelope, animates_duty, high_density_volume, validation_implications, nsf_trust_level) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", families)
    
    # 3. Critical Blunders -> Safeguards Layer
    safeguards = [
        ("Assume CC bounds mapped dynamically", "Any lookup table interpretation", "synth", "Ensure lookup arrays span proper indices preventing index Out Of Bounds", 5, "Castlevania blank frames")
    ]
    cur.executemany("INSERT INTO prevention_patterns (description, trigger_condition, affected_subsystem, recommended_action, prompt_cost, example_failure) VALUES (?, ?, ?, ?, ?, ?)", safeguards)
    
    conn.commit()
    conn.close()
    logger.info("Phase 2 Selective Migration completed.")

if __name__ == "__main__":
    import os
    if not os.path.exists("antiripper_v2.db"):
        conn = sqlite3.connect("antiripper_v2.db")
        with open("SCHEMA_V2.sql", "r") as f:
            conn.executescript(f.read())
        conn.close()
    migrate_selective_knowledge()
