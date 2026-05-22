import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
db_path = os.path.join(os.path.dirname(__file__), "..", "real_estate_avm.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=== E1 playwright_stealth records ===")
c.execute("""
SELECT id, source_url, evidence_photo_path, gps_lat, latitude, iot_device_id, field_notes,
       verification_status, evidence_tier
FROM properties
WHERE collection_method = 'playwright_stealth'
AND evidence_tier = 'E1'
LIMIT 10
""")
for r in c.fetchall():
    print(f"id={r[0]}, tier={r[8]}, verified={r[7]}")
    print(f"  url={str(r[1])[:100]}")
    print(f"  photo={r[2]}, gps={r[3] or r[4]}, iot={r[5]}")
    print(f"  notes={str(r[6] or '')[:50]}")
    print()

print("\n=== manual_entry E2 with GENERIC notes ===")
c.execute("""
SELECT id, field_notes, evidence_photo_path, gps_lat, latitude, evidence_tier
FROM properties
WHERE collection_method = 'manual_entry'
AND evidence_tier = 'E2'
AND field_notes IS NOT NULL
LIMIT 10
""")
for r in c.fetchall():
    print(f"id={r[0]}, tier={r[5]}")
    print(f"  notes: {str(r[1] or '')[:100]}")
    print(f"  photo={r[2]}, gps={r[3] or r[4]}")
    print()

print("\n=== field_survey E2 with no evidence ===")
c.execute("""
SELECT id, field_notes, evidence_photo_path, gps_lat, latitude, evidence_tier,
       verification_status
FROM properties
WHERE collection_method = 'field_survey'
AND evidence_tier = 'E2'
LIMIT 10
""")
for r in c.fetchall():
    print(f"id={r[0]}, tier={r[5]}, verified={r[6]}")
    print(f"  notes: {str(r[1] or '')[:100]}")
    print(f"  photo={r[2]}, gps={r[3] or r[4]}")
    print()

print("\n=== 13 records with NULL method ===")
c.execute("""
SELECT id, field_notes, source_url, evidence_photo_path, gps_lat, latitude,
       iot_device_id, evidence_tier, verification_status
FROM properties
WHERE collection_method IS NULL
LIMIT 13
""")
for r in c.fetchall():
    print(f"id={r[0]}, tier={r[7]}, verified={r[8]}")
    print(f"  url={str(r[2] or '')[:80]}")
    print(f"  photo={r[3]}, gps={r[4] or r[5]}, iot={r[6]}")
    print(f"  notes={str(r[1] or '')[:80]}")
    print()

conn.close()
