import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
db_path = os.path.join(os.path.dirname(__file__), "..", "real_estate_avm.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=== FIELD EVIDENCE comparison: SELF_COLLECTED vs PUBLIC_SCRAPED ===\n")

for label, methods in [
    ("SELF_COLLECTED methods (field_survey/sensor/manual_entry)", ["field_survey", "smartphone_sensor_capture", "manual_entry"]),
    ("PUBLIC_SCRAPED methods (public_scraped/playwright)", ["public_scraped", "playwright_stealth"]),
]:
    print(f"{label}:")
    placeholders = ",".join(["?"] * len(methods))
    c.execute(f"""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN evidence_photo_path IS NOT NULL AND evidence_photo_path != '' THEN 1 ELSE 0 END) as has_photo_path,
            SUM(CASE WHEN field_photos IS NOT NULL AND field_photos != '' THEN 1 ELSE 0 END) as has_field_photos,
            SUM(CASE WHEN (gps_lat IS NOT NULL AND gps_lat != 0) OR (latitude IS NOT NULL AND latitude != 0) THEN 1 ELSE 0 END) as has_gps,
            SUM(CASE WHEN iot_device_id IS NOT NULL AND iot_device_id != '' THEN 1 ELSE 0 END) as has_iot,
            SUM(CASE WHEN field_notes IS NOT NULL AND LENGTH(field_notes) > 20 THEN 1 ELSE 0 END) as has_notes,
            SUM(CASE WHEN evidence_tier IN ('E3','E4') THEN 1 ELSE 0 END) as e3_plus
        FROM properties
        WHERE collection_method IN ({placeholders})
        AND price > 0
    """, methods)
    r = c.fetchone()
    print(f"  Total: {r[0]}")
    print(f"  Has photo (path): {r[1]} ({100*r[1]/r[0]:.1f}%)")
    print(f"  Has field_photos: {r[2]} ({100*r[2]/r[0]:.1f}%)")
    print(f"  Has GPS: {r[3]} ({100*r[3]/r[0]:.1f}%)")
    print(f"  Has IoT: {r[4]} ({100*r[4]/r[0]:.1f}%)")
    print(f"  Has field_notes (>20 chars): {r[5]} ({100*r[5]/r[0]:.1f}%)")
    print(f"  E3+ tier: {r[6]} ({100*r[6]/r[0]:.1f}%)")
    print()

print("=== Sample SELF_COLLECTED with photo/GPS evidence ===\n")
c.execute("""
SELECT id, collection_method, evidence_tier,
       evidence_photo_path, field_photos,
       gps_lat, latitude,
       iot_device_id,
       SUBSTR(field_notes, 1, 100) as notes
FROM properties
WHERE collection_method IN ('field_survey', 'smartphone_sensor_capture', 'manual_entry')
AND price > 0
AND (evidence_photo_path IS NOT NULL OR field_photos IS NOT NULL
     OR gps_lat IS NOT NULL OR latitude IS NOT NULL
     OR iot_device_id IS NOT NULL)
LIMIT 5
""")
for r in c.fetchall():
    print(f"id={r[0]}, method={r[1]}, tier={r[2]}")
    print(f"  photo_path={r[3]}, field_photos={r[4]}")
    print(f"  gps_lat={r[5]}, latitude={r[6]}")
    print(f"  iot={r[7]}")
    print(f"  notes: {r[8]}")
    print()

print("=== What makes SELF_COLLECTED different from PUBLIC_SCRAPED? ===\n")
# Check if SELF_COLLECTED records with meaningful notes have evidence photo/GPS
c.execute("""
SELECT
    SUM(CASE WHEN
        field_notes IS NOT NULL AND LENGTH(field_notes) > 20
        AND (evidence_photo_path IS NOT NULL OR gps_lat IS NOT NULL OR iot_device_id IS NOT NULL)
    THEN 1 ELSE 0 END) as notes_plus_physical,
    SUM(CASE WHEN
        field_notes IS NOT NULL AND LENGTH(field_notes) > 20
        AND evidence_photo_path IS NULL AND gps_lat IS NULL AND iot_device_id IS NULL
    THEN 1 ELSE 0 END) as notes_only,
    SUM(CASE WHEN
        (evidence_photo_path IS NOT NULL OR gps_lat IS NOT NULL OR iot_device_id IS NOT NULL)
        AND (field_notes IS NULL OR LENGTH(field_notes) <= 20)
    THEN 1 ELSE 0 END) as physical_only
FROM properties
WHERE collection_method IN ('field_survey', 'smartphone_sensor_capture', 'manual_entry')
AND price > 0
""")
r = c.fetchone()
print(f"SELF_COLLECTED (self-collected methods):")
print(f"  notes + physical evidence (photo/GPS/IoT): {r[0]}")
print(f"  notes ONLY (no physical evidence): {r[1]}")
print(f"  physical ONLY (no notes): {r[2]}")
print()
print(f"  => {r[0]} records have BOTH notes AND physical evidence")
print(f"  => {r[1]} records have notes but NO physical evidence")
print(f"     (these are differentiated by detailed notes, not photos/GPS)")

conn.close()
