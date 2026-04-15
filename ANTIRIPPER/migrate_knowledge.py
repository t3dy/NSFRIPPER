import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_driver_families(cur):
    logger.info("Migrating driver families...")
    families = [
        {
            "slug": "minimal",
            "name": "Minimal Drivers",
            "cc11_per_note": 1.45, # 0.1 to 2.8 average
            "cc12_per_note": 0.0,
            "description": "Writes volume once per note and lets NES hardware decay handle it. Music sounds clean and simple. Extraction is easy and NSF pipeline handles it perfectly.",
            "fidelity_concern": "Low — simple audio",
            "examples": "Dragon Warrior, Mega Man 1-2, DuckTales, Bionic Commando, Wizards & Warriors"
        },
        {
            "slug": "sunsoft_style",
            "name": "Sunsoft-style",
            "cc11_per_note": 4.5, # 3.5 to 5.6
            "cc12_per_note": 0.2, # < 0.5
            "description": "Detailed volume envelopes via lookup tables, but duty cycle static. Music is punchy and aggressive. Requires CC mode for CC11 playback.",
            "fidelity_concern": "Medium — envelope tables",
            "examples": "Castlevania 1, Mega Man 3-4, Battletoads, Gargoyle's Quest II, Ninja Gaiden III"
        },
        {
            "slug": "capcom_duty",
            "name": "Capcom Duty Switchers",
            "cc11_per_note": 4.3, # 3.7 to 4.9
            "cc12_per_note": 1.0, # 0.7 to 1.3
            "description": "Actively switches duty cycle DURING notes for timbral animation. Animated and shimmering. Both CC11 and CC12 must play back faithfully.",
            "fidelity_concern": "High — CC12 matters",
            "examples": "Kirby's Adventure, Castlevania 3 US/JP, Super Mario Bros 1"
        },
        {
            "slug": "dense_automators",
            "name": "Dense Automators",
            "cc11_per_note": 10.0, # 5.1 to 15.0
            "cc12_per_note": 0.0,
            "description": "Continuous stream of per-frame values. Smooth volume curves, echo effects. Needs sample-accurate playback.",
            "fidelity_concern": "High — lots of data",
            "examples": "Final Fantasy, Blaster Master, Ninja Gaiden II, Super Mario Bros 2, Batman, Journey to Silius, Contra"
        },
        {
            "slug": "konami_full",
            "name": "Konami Full Animation",
            "cc11_per_note": 7.7, # > 6.0
            "cc12_per_note": 1.3, # > 1.0
            "description": "Both volume AND duty are animated per-frame. SysEx register replay is the only lossless way.",
            "fidelity_concern": "Highest — both streams per frame",
            "examples": "Super Mario Bros 3"
        }
    ]

    for f in families:
        cur.execute("""
            INSERT OR IGNORE INTO driver_families (slug, name, cc11_per_note, cc12_per_note, description, fidelity_concern, examples)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (f['slug'], f['name'], f['cc11_per_note'], f['cc12_per_note'], f['description'], f['fidelity_concern'], f['examples']))

def migrate_apu_facts(cur):
    logger.info("Migrating APU hardware facts...")
    facts = [
        {
            "component": "triangle",
            "fact": "Triangle outputs a frequency one octave lower than pulse for the same timber period",
            "formula": "freq = 1789773 / (32 * (period + 1))",
            "domain": "period: 2-2047",
            "gotchas": "triangle divider is 32, not 16. Has no volume envelope, only gating."
        },
        {
            "component": "pulse",
            "fact": "Two distinct pulse channels with 4 duty cycle options",
            "formula": "freq = 1789773 / (16 * (period + 1))",
            "domain": "period: 8-2047",
            "gotchas": "Period values below 8 are ultrasonic/silent."
        }
    ]

    for f in facts:
        cur.execute("""
            INSERT OR IGNORE INTO apu_hardware_facts (component, fact, formula, domain, gotchas)
            VALUES (?, ?, ?, ?, ?)
        """, (f['component'], f['fact'], f['formula'], f['domain'], f['gotchas']))

def migrate_blunders_and_patterns(cur):
    logger.info("Migrating fix patterns and blunders...")
    cur.execute("""
        INSERT OR IGNORE INTO blunders (id, game_slug, symptom, root_cause, fix, category, prompts_wasted, prevention)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (1, None, "Silent output but JSFX compiles without syntax errors", "Reaper serves old cached code or JSFX has empty else branches", "Add '0;' no-op to empty else branches and reload FX", "synth", 15, "Check FX Window for error banners directly; never assume structural code functions without tone-testing."))

    cur.execute("""
        INSERT OR IGNORE INTO fix_patterns (pattern_id, trigger_condition, action, cost_if_skipped, derived_from_blunder)
        VALUES (?, ?, ?, ?, ?)
    """, ("check_reaper_fx_first", "Before beginning any REAPER MIDI logic debugging", "Verify there is not a silent compilation error in JSFX UI.", "10-20 loops of LLM guessing wrong layer.", 1))

def main():
    db_path = "antiripper.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    migrate_driver_families(cur)
    migrate_apu_facts(cur)
    migrate_blunders_and_patterns(cur)

    conn.commit()
    conn.close()
    logger.info("Static migration payload executed successfully.")

if __name__ == "__main__":
    main()
