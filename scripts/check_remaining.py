import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
db_path = os.path.join(os.path.dirname(__file__), "..", "real_estate_avm.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=== Records without provenance chains ===")
c.execute("""
SELECT p.id, p.collection_method, p.evidence_tier, p.field_notes,
       p.source_url, p.verification_status
FROM properties p
WHERE p.price > 0
AND NOT EXISTS (SELECT 1 FROM provenance_chains pc WHERE pc.property_id = p.id)
LIMIT 20
""")
for r in c.fetchall():
    print(f"id={r[0]}, method={r[1]}, tier={r[2]}, verified={r[5]}")
    print(f"  url={r[4] or 'NONE'}")
    print(f"  notes={str(r[3] or '')[:80]}")

print("\n=== Current DB state ===")
c.execute("SELECT COUNT(*) FROM properties WHERE price > 0")
print(f"Total properties: {c.fetchone()[0]}")
c.execute("SELECT evidence_tier, COUNT(*) FROM properties WHERE price > 0 GROUP BY evidence_tier ORDER BY evidence_tier")
print("Tier distribution:")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")
c.execute("SELECT COUNT(DISTINCT collection_method) FROM properties WHERE price > 0")
print(f"Collection methods: {c.fetchone()[0]}")
c.execute("SELECT collection_method, COUNT(*) FROM properties WHERE price > 0 GROUP BY collection_method ORDER BY COUNT(*) DESC")
print("By method:")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")

print("\n=== Evidence breakdown by tier ===")
c.execute("""
SELECT p.evidence_tier, p.collection_method,
       SUM(CASE WHEN evidence_photo_path IS NOT NULL THEN 1 ELSE 0 END) as photo,
       SUM(CASE WHEN (gps_lat IS NOT NULL AND gps_lat != 0) OR (latitude IS NOT NULL AND latitude != 0) THEN 1 ELSE 0 END) as gps,
       SUM(CASE WHEN iot_device_id IS NOT NULL AND iot_device_id != '' THEN 1 ELSE 0 END) as iot,
       SUM(CASE WHEN field_notes IS NOT NULL AND LENGTH(field_notes) > 20 THEN 1 ELSE 0 END) as notes,
       COUNT(*) as total
FROM properties p
WHERE p.price > 0
GROUP BY p.evidence_tier, p.collection_method
ORDER BY p.evidence_tier, p.collection_method
""")
print(f"{'Tier':<5} {'Method':<25} {'Photo':<7} {'GPS':<5} {'IoT':<5} {'Notes':<6} {'Total':<6}")
for r in c.fetchall():
    print(f"{str(r[0]):<5} {str(r[1]):<25} {r[2]:<7} {r[3]:<5} {r[4]:<5} {r[5]:<6} {r[6]:<6}")

print("\n=== Provenance chain coverage ===")
c.execute("SELECT COUNT(*) FROM provenance_chains")
print(f"Total chain entries: {c.fetchone()[0]}")
c.execute("SELECT COUNT(DISTINCT property_id) FROM provenance_chains")
print(f"Properties with chains: {c.fetchone()[0]}")
c.execute("""
SELECT step, COUNT(*) FROM provenance_chains GROUP BY step ORDER BY COUNT(*) DESC
""")
print("Chain steps:")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")

conn.close()
