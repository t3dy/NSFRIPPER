import sqlite3
import pprint

db = r'c:\Dev\NSFRIPPER\ANTIRIPPER\antiripper_v2.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

tables = ['evidence_items', 'claims', 'claim_evidence_links', 'decision_records', 'prevention_patterns', 'hardware_facts', 'concept_bridges', 'driver_families', 'synth_patches']

for t in tables:
    count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"{t} count: {count}")

print("\nhardware_facts:")
for row in cur.execute("SELECT statement FROM hardware_facts LIMIT 3"):
    print("-", row[0])

print("\nprevention_patterns:")
for row in cur.execute("SELECT description FROM prevention_patterns LIMIT 3"):
    print("-", row[0])

print("\nclaims:")
for row in cur.execute("SELECT statement FROM claims LIMIT 3"):
    print("-", row[0])
