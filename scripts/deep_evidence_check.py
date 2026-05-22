import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
db_path = os.path.join(os.path.dirname(__file__), "..", "real_estate_avm.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=== IoT device details for PUBLIC_SCRAPED records ===")
c.execute("""
SELECT id, collection_method, evidence_tier, iot_device_id,
       SUBSTR(field_notes, 1, 50) as notes,
       source_domain
FROM properties
WHERE iot_device_id IS NOT NULL AND iot_device_id != ''
AND collection_method IN ('public_scraped', 'playwright_stealth')
LIMIT 10
""")
for r in c.fetchall():
    print(f"id={r[0]}, method={r[1]}, tier={r[2]}, iot={r[3]}, notes={r[4]}, domain={r[5]}")

print("\n=== IoT device details for SELF_COLLECTED records ===")
c.execute("""
SELECT id, collection_method, evidence_tier, iot_device_id,
       SUBSTR(field_notes, 1, 80) as notes
FROM properties
WHERE iot_device_id IS NOT NULL AND iot_device_id != ''
AND collection_method IN ('field_survey', 'smartphone_sensor_capture', 'manual_entry')
LIMIT 10
""")
for r in c.fetchall():
    print(f"id={r[0]}, method={r[1]}, tier={r[2]}, iot={r[3]}, notes={r[4]}")

print("\n=== Photo path analysis ===")
c.execute("""
SELECT collection_method, COUNT(*) as cnt,
       SUM(CASE WHEN evidence_photo_path LIKE 'D:/FieldSurvey%' THEN 1 ELSE 0 END) as real_path,
       SUM(CASE WHEN evidence_photo_path LIKE 'D:/FieldSurvey%' THEN 0 ELSE 1 END) as other_path
FROM properties
WHERE evidence_photo_path IS NOT NULL AND evidence_photo_path != ''
GROUP BY collection_method
""")
print("Photo paths by collection_method:")
for r in c.fetchall():
    print(f"  {r[0]}: total={r[1]}, real_D:/FieldSurvey={r[2]}, other={r[3]}")

print("\n=== SELF_COLLECTED: E4 records (photo + GPS) ===")
c.execute("""
SELECT id, collection_method, evidence_tier, evidence_photo_path,
       latitude, gps_lat,
       SUBSTR(field_notes, 1, 80) as notes
FROM properties
WHERE collection_method IN ('field_survey', 'smartphone_sensor_capture', 'manual_entry')
AND evidence_tier = 'E4'
LIMIT 10
""")
print("E4 SELF_COLLECTED records:")
for r in c.fetchall():
    print(f"  id={r[0]}, method={r[1]}, tier={r[2]}")
    print(f"    photo={r[3]}, lat={r[4] or r[5]}")
    print(f"    notes: {r[6]}")

print("\n=== SELF_COLLECTED: E3 records with notes quality ===")
c.execute("""
SELECT id, collection_method, evidence_tier,
       LENGTH(field_notes) as notes_len,
       evidence_photo_path IS NOT NULL AND evidence_photo_path != '' as has_photo,
       (latitude IS NOT NULL AND latitude != 0) as has_lat,
       SUBSTR(field_notes, 1, 80) as notes
FROM properties
WHERE collection_method IN ('field_survey', 'smartphone_sensor_capture', 'manual_entry')
AND evidence_tier = 'E3'
ORDER BY LENGTH(field_notes) DESC
LIMIT 10
""")
print("E3 SELF_COLLECTED records (sorted by notes length):")
for r in c.fetchall():
    print(f"  id={r[0]}, method={r[1]}, tier={r[2]}, len={r[3]}, photo={r[4]}, lat={r[5]}")
    print(f"    notes: {r[6]}")

print("\n=== SELF_COLLECTED: E2 records ===")
c.execute("""
SELECT id, collection_method, evidence_tier,
       LENGTH(field_notes) as notes_len,
       evidence_photo_path IS NOT NULL AND evidence_photo_path != '' as has_photo,
       (latitude IS NOT NULL AND latitude != 0) as has_lat,
       SUBSTR(field_notes, 1, 80) as notes
FROM properties
WHERE collection_method IN ('field_survey', 'smartphone_sensor_capture', 'manual_entry')
AND evidence_tier = 'E2'
LIMIT 5
""")
print("E2 SELF_COLLECTED records:")
for r in c.fetchall():
    print(f"  id={r[0]}, method={r[1]}, tier={r[2]}, len={r[3]}, photo={r[4]}, lat={r[5]}")
    print(f"    notes: {r[6]}")

conn.close()
