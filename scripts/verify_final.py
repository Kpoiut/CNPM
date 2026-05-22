import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")

import os
db_path = os.path.join(os.path.dirname(__file__), "..", "real_estate_avm.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=== TOTAL properties ===")
c.execute("SELECT COUNT(*) FROM properties WHERE price > 0")
print(f"  {c.fetchone()[0]} priced properties")

print("\n=== verification_status distribution ===")
c.execute("SELECT verification_status, COUNT(*) FROM properties WHERE price > 0 GROUP BY verification_status")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")

print("\n=== verified properties: chain coverage (corrected query) ===")
c.execute("""
SELECT COUNT(*)
FROM properties p
WHERE p.verification_status = "verified"
AND EXISTS (SELECT 1 FROM provenance_chains pc WHERE pc.property_id = p.id)
""")
print(f"  verified WITH chains: {c.fetchone()[0]}")

c.execute("""
SELECT COUNT(*)
FROM properties p
WHERE p.verification_status = "verified"
AND NOT EXISTS (SELECT 1 FROM provenance_chains pc WHERE pc.property_id = p.id)
""")
print(f"  verified WITHOUT chains: {c.fetchone()[0]}")

print("\n=== evidence_tier breakdown ===")
c.execute("SELECT evidence_tier, COUNT(*) FROM properties WHERE price > 0 GROUP BY evidence_tier ORDER BY evidence_tier")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")

print("\n=== provenance chains summary ===")
c.execute("SELECT COUNT(*) FROM provenance_chains")
print(f"  {c.fetchone()[0]} total chain entries")
c.execute("SELECT COUNT(DISTINCT property_id) FROM provenance_chains")
print(f"  {c.fetchone()[0]} unique properties with chains")
c.execute("""
SELECT COUNT(*)
FROM properties p
WHERE p.price > 0
AND NOT EXISTS (SELECT 1 FROM provenance_chains pc WHERE pc.property_id = p.id)
""")
print(f"  priced properties WITHOUT chains: {c.fetchone()[0]}")

print("\n=== SELF_COLLECTED methods: chain coverage ===")
for method in ('field_survey', 'smartphone_sensor_capture', 'manual_entry'):
    c.execute("""
        SELECT COUNT(*) FROM properties p
        WHERE p.collection_method = ? AND p.price > 0
    """, (method,))
    total = c.fetchone()[0]
    c.execute("""
        SELECT COUNT(*) FROM properties p
        WHERE p.collection_method = ? AND p.price > 0
        AND EXISTS (SELECT 1 FROM provenance_chains pc WHERE pc.property_id = p.id)
    """, (method,))
    with_chain = c.fetchone()[0]
    print(f"  {method}: {with_chain}/{total} with chains")

print("\n=== E3+ SELF_COLLECTED sample ===")
c.execute("""
SELECT p.id, p.collection_method, p.evidence_tier,
       p.evidence_photo_path IS NOT NULL and p.evidence_photo_path != '' as has_photo,
       (p.gps_lat IS NOT NULL and p.gps_lat != 0) or (p.latitude IS NOT NULL and p.latitude != 0) as has_gps,
       p.iot_device_id IS NOT NULL and p.iot_device_id != '' as has_iot,
       p.verification_status,
       EXISTS (SELECT 1 FROM provenance_chains pc WHERE pc.property_id = p.id) as has_chain,
       SUBSTR(p.field_notes, 1, 80) as notes_preview
FROM properties p
WHERE p.evidence_tier IN ('E3','E4')
AND p.collection_method IN ('field_survey','smartphone_sensor_capture','manual_entry')
LIMIT 8
""")
print(f"  {'id':<6} {'method':<28} {'tier':<4} {'photo':<6} {'gps':<4} {'iot':<4} {'verified':<9} {'chain':<6} notes")
for r in c.fetchall():
    print(f"  {r[0]:<6} {r[1]:<28} {r[2]:<4} {str(r[3]):<6} {str(r[4]):<4} {str(r[5]):<4} {r[6]:<9} {str(r[7]):<6} {r[8]}")

print("\n=== borderlines (verified but E1): sample ===")
c.execute("""
SELECT p.id, p.collection_method, p.field_notes,
       p.verification_status, p.evidence_tier,
       EXISTS (SELECT 1 FROM provenance_chains pc WHERE pc.property_id = p.id) as has_chain
FROM properties p
WHERE p.verification_status = "verified"
AND p.evidence_tier = "E1"
LIMIT 5
""")
for r in c.fetchall():
    print(f"  id={r[0]}, method={r[1]}, verified={r[3]}, tier={r[4]}, chain={r[6]}")
    print(f"    notes: {str(r[2] or '')[:100]}")

conn.close()
