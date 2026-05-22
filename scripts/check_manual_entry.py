import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
db_path = os.path.join(os.path.dirname(__file__), "..", "real_estate_avm.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("""
SELECT p.id, p.collection_method, p.evidence_tier, p.field_notes,
       p.evidence_photo_path IS NOT NULL and p.evidence_photo_path != "" as photo,
       (p.gps_lat IS NOT NULL and p.gps_lat != 0) or (p.latitude IS NOT NULL and p.latitude != 0) as gps,
       p.iot_device_id IS NOT NULL and p.iot_device_id != "" as iot,
       EXISTS (SELECT 1 FROM provenance_chains pc WHERE pc.property_id = p.id) as has_chain
FROM properties p
WHERE p.collection_method = "manual_entry"
AND p.price > 0
AND NOT EXISTS (SELECT 1 FROM provenance_chains pc WHERE pc.property_id = p.id)
LIMIT 20
""")
print("Manual_entry records WITHOUT chains:")
for r in c.fetchall():
    print(f"id={r[0]}, tier={r[2]}, photo={r[4]}, gps={r[5]}, iot={r[6]}, chain={r[7]}")
    print(f"  notes: {str(r[3] or '')[:120]}")
conn.close()
