import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
db_path = os.path.join(os.path.dirname(__file__), "..", "real_estate_avm.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=== 13 records without provenance chains ===")
c.execute("""
SELECT id, collection_method, evidence_tier, source_url,
       evidence_photo_path, gps_lat, latitude, iot_device_id,
       field_notes, verification_status, price, area_m2
FROM properties p
WHERE p.price > 0
AND NOT EXISTS (SELECT 1 FROM provenance_chains pc WHERE pc.property_id = p.id)
""")

records = c.fetchall()
print(f"Count: {len(records)}")
for r in records:
    print(f"\nid={r[0]}, method={r[1]}, tier={r[2]}, verified={r[9]}")
    print(f"  url={str(r[3] or '')[:100]}")
    print(f"  price={r[10]}, area={r[11]}, photo={r[4]}, gps={r[5] or r[6]}, iot={r[7]}")
    print(f"  notes={str(r[8] or '')[:80]}")

conn.close()
