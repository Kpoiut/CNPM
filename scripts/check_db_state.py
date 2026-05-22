import sqlite3
import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
db_path = os.path.join(os.path.dirname(__file__), "..", "real_estate_avm.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=== verification_status ===")
c.execute('SELECT verification_status, COUNT(*) FROM properties WHERE price > 0 GROUP BY verification_status')
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")
print()

print("=== evidence_tier ===")
c.execute('SELECT evidence_tier, COUNT(*) FROM properties WHERE price > 0 GROUP BY evidence_tier ORDER BY evidence_tier')
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")
print()

print("=== collection_method ===")
c.execute('SELECT collection_method, COUNT(*) FROM properties WHERE price > 0 GROUP BY collection_method ORDER BY COUNT(*) DESC')
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")
print()

print("=== verified + chain status ===")
c.execute("""
SELECT
    CASE WHEN pc.id IS NOT NULL THEN "has_chain" ELSE "no_chain" END as chain_status,
    COUNT(*)
FROM properties p
LEFT JOIN provenance_chains pc ON p.id = pc.property_id
WHERE p.verification_status = "verified"
GROUP BY chain_status
""")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")
print()

print("=== verified + no_chain: evidence breakdown ===")
c.execute("""
SELECT
    p.id, p.collection_method, p.field_notes, p.evidence_photo_path, p.field_photos,
    p.gps_lat, p.latitude, p.iot_device_id, p.evidence_tier,
    LENGTH(p.field_notes) as notes_len,
    p.source_url
FROM properties p
LEFT JOIN provenance_chains pc ON p.id = pc.property_id
WHERE p.verification_status = "verified" AND pc.id IS NULL
LIMIT 10
""")
for r in c.fetchall():
    print(f"  id={r[0]}, method={r[1]}, notes_len={r[9]}, photo={bool(r[3] or r[4])}, gps={bool(r[5] or r[6])}, iot={bool(r[7])}, tier={r[8]}")
    notes = (r[2] or '')[:120].replace('\n', ' ')
    print(f"    notes: {notes}")
    print(f"    url: {r[10]}")
print()

print("=== total chains ===")
c.execute("SELECT COUNT(*) FROM provenance_chains")
print(f"  {c.fetchone()[0]} chains total")
print()

print("=== unique properties with chains ===")
c.execute("SELECT COUNT(DISTINCT property_id) FROM provenance_chains")
print(f"  {c.fetchone()[0]} properties with chains")
print()

# Check self-collected method records + chain status
print("=== SELF_COLLECTED methods + chain status ===")
c.execute("""
SELECT
    p.collection_method,
    CASE WHEN pc.id IS NOT NULL THEN "has_chain" ELSE "no_chain" END as chain_status,
    COUNT(*)
FROM properties p
LEFT JOIN provenance_chains pc ON p.id = pc.property_id
WHERE p.collection_method IN ('field_survey', 'smartphone_sensor_capture', 'manual_entry')
AND p.price > 0
GROUP BY p.collection_method, chain_status
ORDER BY p.collection_method, chain_status
""")
for r in c.fetchall():
    print(f"  {r[0]} / {r[1]}: {r[2]}")

conn.close()
