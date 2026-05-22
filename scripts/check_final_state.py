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

print("\n=== verified properties: chain coverage ===")
c.execute("""
SELECT
    CASE WHEN pc.id IS NOT NULL THEN "has_chain" ELSE "no_chain" END,
    COUNT(*)
FROM properties p
LEFT JOIN provenance_chains pc ON p.id = pc.property_id
WHERE p.verification_status = "verified"
GROUP BY CASE WHEN pc.id IS NOT NULL THEN "has_chain" ELSE "no_chain" END
""")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")

print("\n=== evidence_tier breakdown ===")
c.execute("SELECT evidence_tier, COUNT(*) FROM properties WHERE price > 0 GROUP BY evidence_tier ORDER BY evidence_tier")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")

print("\n=== provenance chains by collection_method ===")
c.execute("""
SELECT p.collection_method,
       COUNT(DISTINCT p.id) as props,
       COUNT(pc.id) as chains
FROM properties p
LEFT JOIN provenance_chains pc ON p.id = pc.property_id
WHERE p.price > 0
GROUP BY p.collection_method
ORDER BY props DESC
""")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]} props, {r[2]} chains")

print("\n=== total provenance chains ===")
c.execute("SELECT COUNT(*) FROM provenance_chains")
print(f"  {c.fetchone()[0]} total chain entries")
c.execute("SELECT COUNT(DISTINCT property_id) FROM provenance_chains")
print(f"  {c.fetchone()[0]} unique properties with chains")

print("\n=== E3+ SELF_COLLECTED: sample records ===")
c.execute("""
SELECT p.id, p.collection_method, p.evidence_tier, p.field_notes, p.evidence_photo_path,
       p.gps_lat, p.latitude, p.iot_device_id, p.verification_status,
       pc.id as chain_id
FROM properties p
LEFT JOIN provenance_chains pc ON p.id = pc.property_id
WHERE p.evidence_tier IN ('E3','E4')
AND p.collection_method IN ('field_survey','smartphone_sensor_capture','manual_entry')
LIMIT 5
""")
for r in c.fetchall():
    print(f"  id={r[0]}, method={r[1]}, tier={r[2]}, photo={bool(r[4])}, gps={bool(r[5] or r[6])}, iot={bool(r[7])}, verified={r[8]}")
    print(f"    notes: {str(r[3] or '')[:100]}")
    print(f"    has_chain: {bool(r[9])}")

print("\n=== borderlines (verified but E1): sample ===")
c.execute("""
SELECT p.id, p.collection_method, p.field_notes, p.verification_status, p.evidence_tier,
       pc.id as chain_id
FROM properties p
LEFT JOIN provenance_chains pc ON p.id = pc.property_id
WHERE p.verification_status = "verified"
AND p.evidence_tier = "E1"
LIMIT 5
""")
for r in c.fetchall():
    print(f"  id={r[0]}, method={r[1]}, verified={r[3]}, tier={r[4]}, has_chain={bool(r[5])}")
    print(f"    notes: {str(r[2] or '')[:100]}")

conn.close()
