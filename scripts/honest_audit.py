#!/usr/bin/env python3
"""
HONEST DATABASE AUDIT — Real Estate AVM

Mục tiêu: Đánh giá TRUNG THỰC toàn bộ cơ sở dữ liệu.
Không che giấu, không mô phỏng bù đắp.

Câu hỏi cần trả lời:
1. Bao nhiêu record là DỮ LIỆU THẬT, bao nhiêu là TỔNG HỢP (procedural)?
2. Bao nhiêu record có EVIDENCE THỰC (photo/GPS/IoT/notes)?
3. Tier hiện tại (E1-E5) có CHÍNH XÁC không?
4. Những gì đang bị MÔ PHỎNG thay thế?

Định nghĩa trung thực:
- REAL: Dữ liệu từ nguồn thực (listing URL, field survey thực, sensor thực)
- SYNTHETIC: Tạo bằng thuật toán, không có nguồn thực
- SIMULATED FILL: Thiếu evidence → mô phỏng provenance chain/field notes để "lấp đầy"

Usage:
    python scripts/honest_audit.py
"""

import sqlite3
import sys
import os
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = Path(__file__).parent.parent / "real_estate_avm.db"


GENERIC_PATTERNS = [
    "khảo sát sơ bộ",
    "thu thập thông tin qua",
    "hỏi hàng xóm",
    "quan sát bên ngoài",
    "cần xác minh thêm",
    "placeholder",
    "test",
    "sample",
    "chưa xác minh",
    "sơ bộ",
]
MEASUREMENT_PATTERNS = [
    "m2", "mét vuông", "mặt tiền", "mat tien", "mat_tien",
    "rộng", "sâu", "dài", "cao", "ngõ", "đường",
    "tầng", "diện tích",
]


def check_notes(notes):
    """Return (is_meaningful, reason)."""
    if not notes or len((notes or "").strip()) < 30:
        return False, "too_short"
    text_lower = notes.lower()
    if any(p in text_lower for p in GENERIC_PATTERNS):
        return False, "generic"
    if not any(p in text_lower for p in MEASUREMENT_PATTERNS):
        return False, "no_measurement"
    return True, "meaningful"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print(f"\n{'='*70}")
    print(f"  HONEST DATABASE AUDIT — Real Estate AVM")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Database: {DB_PATH}")
    print(f"{'='*70}\n")

    # Load all properties
    c.execute("""
        SELECT id, collection_method, evidence_tier, field_notes,
               evidence_photo_path, field_photos,
               gps_lat, latitude, longitude, gps_lng,
               iot_device_id,
               source_url, source_domain, source_screenshot_path,
               price, area_m2, province_city, district,
               listing_date, collection_timestamp,
               verification_status,
               collected_by, collected_at,
               created_at
        FROM properties
        WHERE price > 0 AND price IS NOT NULL
    """)
    properties = [dict(r) for r in c.fetchall()]
    total = len(properties)

    print(f"TOTAL RECORDS: {total}\n")

    # =========================================================================
    # CATEGORY 1: SYNTHETIC (batch_generator) — 100% fake
    # =========================================================================
    synthetic = [p for p in properties if p["collection_method"] == "batch_generator"]
    print(f"{'─'*70}")
    print(f"  CATEGORY 1: SYNTHETIC / PROCEDURAL ({len(synthetic)} records)")
    print(f"  Method: batch_generator — 100% tạo bằng thuật toán")
    print(f"  Evidence: KHÔNG CÓ nguồn thực")
    print(f"  → TRUE TIER: E1 (không có source, không có verification)")
    print(f"  → OVERRIDE needed: evidence_tier should be E1, provenance is fake")
    fake_tier_count = sum(1 for p in synthetic if p["evidence_tier"] not in (None, "E1"))
    print(f"  → MISCLASSIFIED: {fake_tier_count} records declared E2-E5 but are E1")

    # =========================================================================
    # CATEGORY 2: PUBLIC SCRAPED — scraped from websites
    # =========================================================================
    scraped = [p for p in properties
               if p["collection_method"] in ("public_scraped", "playwright_stealth")]
    print(f"\n{'─'*70}")
    print(f"  CATEGORY 2: PUBLIC SCRAPED ({len(scraped)} records)")

    scraped_real_source = []
    scraped_no_source = []
    for p in scraped:
        if p["source_url"]:
            scraped_real_source.append(p)
        else:
            scraped_no_source.append(p)

    print(f"  - Có source_url (scrape thực): {len(scraped_real_source)}")
    print(f"  - Không có source_url: {len(scraped_no_source)}")
    print(f"  Evidence thực tế:")
    print(f"    Photo: {sum(1 for p in scraped if p['evidence_photo_path'])}")
    print(f"    GPS: {sum(1 for p in scraped if (p['gps_lat'] or p['latitude']))}")
    print(f"    IoT: {sum(1 for p in scraped if p['iot_device_id'])}")
    print(f"    Field notes: {sum(1 for p in scraped if p['field_notes'])}")
    print(f"  → TRUE TIER: E2-E3 tùy source authority + price verification")
    print(f"  → NOTE: IoT device IDs 'IOT-Hà-Quậ-*' trên public scraped records")
    print(f"           có thể là MÔ PHỎNG, không phải thiết bị thực")

    # Check IoT on scraped records
    iot_on_scraped = [p for p in scraped if p["iot_device_id"]]
    print(f"\n  IoT analysis on scraped records:")
    for p in iot_on_scraped[:5]:
        print(f"    id={p['id']}, method={p['collection_method']}, "
              f"iot={p['iot_device_id']}, domain={p['source_domain']}")

    # =========================================================================
    # CATEGORY 3: FIELD_SURVEY — supposed to be real
    # =========================================================================
    field = [p for p in properties if p["collection_method"] == "field_survey"]
    print(f"\n{'─'*70}")
    print(f"  CATEGORY 3: FIELD_SURVEY ({len(field)} records)")
    print(f"  Evidence thực tế:")

    for p in field:
        has_photo = bool(p["evidence_photo_path"])
        has_gps = bool(p["gps_lat"] or p["latitude"])
        has_notes = bool(p["field_notes"])
        meaningful, reason = check_notes(p["field_notes"])
        print(f"    id={p['id']}, tier={p['evidence_tier']}, "
              f"photo={'✓' if has_photo else '✗'}, "
              f"gps={'✓' if has_gps else '✗'}, "
              f"notes={'✓' if has_notes else '✗'}, "
              f"meaningful={meaningful} ({reason}), "
              f"verified={p['verification_status']}")

    # Count evidence
    fs_photo = sum(1 for p in field if p["evidence_photo_path"])
    fs_gps = sum(1 for p in field if (p["gps_lat"] or p["latitude"]))
    fs_meaningful = sum(1 for p in field if check_notes(p["field_notes"])[0])
    fs_notes_only = sum(1 for p in field if p["field_notes"] and not check_notes(p["field_notes"])[0])
    fs_no_evidence = sum(1 for p in field if not p["evidence_photo_path"]
                         and not (p["gps_lat"] or p["latitude"])
                         and not p["field_notes"])
    print(f"\n  Summary:")
    print(f"    Photo thực: {fs_photo}/{len(field)}")
    print(f"    GPS thực: {fs_gps}/{len(field)}")
    print(f"    Notes meaningful: {fs_meaningful}/{len(field)}")
    print(f"    Notes generic/placeholder: {fs_notes_only}/{len(field)}")
    print(f"    Không có evidence gì: {fs_no_evidence}/{len(field)}")

    # Check photo paths
    fs_with_photo = [p for p in field if p["evidence_photo_path"]]
    print(f"\n  Photo paths:")
    for p in fs_with_photo:
        print(f"    id={p['id']}: {p['evidence_photo_path']}")

    # =========================================================================
    # CATEGORY 4: SMARTPHONE_SENSOR_CAPTURE
    # =========================================================================
    sensor = [p for p in properties if p["collection_method"] == "smartphone_sensor_capture"]
    print(f"\n{'─'*70}")
    print(f"  CATEGORY 4: SMARTPHONE_SENSOR_CAPTURE ({len(sensor)} records)")
    print(f"  Evidence thực tế:")
    for p in sensor:
        has_photo = bool(p["evidence_photo_path"])
        has_gps = bool(p["gps_lat"] or p["latitude"])
        meaningful, reason = check_notes(p["field_notes"])
        print(f"    id={p['id']}, tier={p['evidence_tier']}, "
              f"photo={'✓' if has_photo else '✗'}, "
              f"gps={'✓' if has_gps else '✗'}, "
              f"meaningful={meaningful}, "
              f"verified={p['verification_status']}")

    # =========================================================================
    # CATEGORY 5: MANUAL_ENTRY
    # =========================================================================
    manual = [p for p in properties if p["collection_method"] == "manual_entry"]
    print(f"\n{'─'*70}")
    print(f"  CATEGORY 5: MANUAL_ENTRY ({len(manual)} records)")
    me_photo = sum(1 for p in manual if p["evidence_photo_path"])
    me_gps = sum(1 for p in manual if (p["gps_lat"] or p["latitude"]))
    me_meaningful = sum(1 for p in manual if check_notes(p["field_notes"])[0])
    me_generic = sum(1 for p in manual if p["field_notes"] and not check_notes(p["field_notes"])[0])
    me_no_notes = sum(1 for p in manual if not p["field_notes"])
    print(f"  Photo: {me_photo}, GPS: {me_gps}")
    print(f"  Notes meaningful: {me_meaningful}, generic: {me_generic}, no notes: {me_no_notes}")
    print(f"  Meaningful notes samples:")
    for p in manual:
        meaningful, reason = check_notes(p["field_notes"])
        if meaningful:
            print(f"    id={p['id']}, tier={p['evidence_tier']}, "
                  f"notes={str(p['field_notes'] or '')[:100]}")
            break

    # =========================================================================
    # CATEGORY 6: NULL / UNKNOWN METHOD
    # =========================================================================
    null_method = [p for p in properties if not p["collection_method"]]
    print(f"\n{'─'*70}")
    print(f"  CATEGORY 6: UNKNOWN METHOD / NULL ({len(null_method)} records)")
    for p in null_method[:5]:
        print(f"    id={p['id']}, tier={p['evidence_tier']}, "
              f"verified={p['verification_status']}, "
              f"source_url={p['source_url'] or 'NONE'}")

    # =========================================================================
    # PROVENANCE CHAIN AUDIT
    # =========================================================================
    print(f"\n{'─'*70}")
    print(f"  PROVENANCE CHAIN AUDIT")

    c.execute("SELECT COUNT(*) FROM provenance_chains")
    total_chains = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT property_id) FROM provenance_chains")
    props_with_chains = c.fetchone()[0]

    print(f"  Total chain entries: {total_chains}")
    print(f"  Properties with chains: {props_with_chains}/{total}")

    # Check which property categories have chains
    for label, methods in [
        ("batch_generator (SYNTHETIC)", ["batch_generator"]),
        ("public scraped", ["public_scraped", "playwright_stealth"]),
        ("field_survey", ["field_survey"]),
        ("smartphone_sensor_capture", ["smartphone_sensor_capture"]),
        ("manual_entry", ["manual_entry"]),
    ]:
        placeholders = ",".join(["?"] * len(methods))
        c.execute(f"""
            SELECT COUNT(DISTINCT p.id)
            FROM properties p
            JOIN provenance_chains pc ON p.id = pc.property_id
            WHERE p.collection_method IN ({placeholders})
        """, methods)
        with_chain = c.fetchone()[0]
        c.execute(f"""
            SELECT COUNT(*)
            FROM properties
            WHERE collection_method IN ({placeholders})
        """, methods)
        total_method = c.fetchone()[0]
        print(f"  {label}: {with_chain}/{total_method} with provenance chains")

    # Check chain step distribution
    c.execute("""
        SELECT step, COUNT(*) as cnt
        FROM provenance_chains
        GROUP BY step
        ORDER BY cnt DESC
    """)
    print(f"\n  Chain steps:")
    for r in c.fetchall():
        print(f"    {r[0]}: {r[1]}")

    # Check for simulated chains (batch_generator records with chains)
    c.execute("""
        SELECT COUNT(DISTINCT p.id)
        FROM properties p
        JOIN provenance_chains pc ON p.id = pc.property_id
        WHERE p.collection_method = 'batch_generator'
    """)
    synthetic_with_chains = c.fetchone()[0]
    print(f"\n  ⚠️  SYNTHETIC records with provenance chains: {synthetic_with_chains}")
    print(f"      → These provenance chains are SIMULATED (added to synthetic data)")

    # =========================================================================
    # VERIFICATION STATUS AUDIT
    # =========================================================================
    print(f"\n{'─'*70}")
    print(f"  VERIFICATION STATUS AUDIT")
    c.execute("""
        SELECT verification_status, collection_method, COUNT(*) as cnt
        FROM properties
        WHERE price > 0
        GROUP BY verification_status, collection_method
        ORDER BY verification_status, collection_method
    """)
    for r in c.fetchall():
        print(f"  {r[0]}: {r[1]} = {r[2]}")

    # =========================================================================
    # TIER ACCURACY AUDIT
    # =========================================================================
    print(f"\n{'─'*70}")
    print(f"  TIER ACCURACY AUDIT")

    tier_audit = {}
    for p in properties:
        tier = p["evidence_tier"] or "E1"
        if tier not in tier_audit:
            tier_audit[tier] = {
                "total": 0, "has_source": 0, "has_photo": 0,
                "has_gps": 0, "has_iot": 0, "meaningful_notes": 0,
                "generic_notes": 0, "no_notes": 0,
                "synthetic": 0, "verified": 0,
            }
        tier_audit[tier]["total"] += 1
        if p["source_url"]:
            tier_audit[tier]["has_source"] += 1
        if p["evidence_photo_path"]:
            tier_audit[tier]["has_photo"] += 1
        if p["gps_lat"] or p["latitude"]:
            tier_audit[tier]["has_gps"] += 1
        if p["iot_device_id"]:
            tier_audit[tier]["has_iot"] += 1
        meaningful, reason = check_notes(p["field_notes"])
        if meaningful:
            tier_audit[tier]["meaningful_notes"] += 1
        elif p["field_notes"]:
            tier_audit[tier]["generic_notes"] += 1
        else:
            tier_audit[tier]["no_notes"] += 1
        if p["collection_method"] == "batch_generator":
            tier_audit[tier]["synthetic"] += 1
        if p["verification_status"] == "verified":
            tier_audit[tier]["verified"] += 1

    for tier in ["E5", "E4", "E3", "E2", "E1"]:
        if tier not in tier_audit:
            continue
        a = tier_audit[tier]
        n = a["total"]
        print(f"\n  {tier} ({n} records):")
        print(f"    Synthetic: {a['synthetic']} ({100*a['synthetic']/n:.1f}%)")
        print(f"    Verified: {a['verified']} ({100*a['verified']/n:.1f}%)")
        print(f"    Has source_url: {a['has_source']} ({100*a['has_source']/n:.1f}%)")
        print(f"    Has photo: {a['has_photo']} ({100*a['has_photo']/n:.1f}%)")
        print(f"    Has GPS: {a['has_gps']} ({100*a['has_gps']/n:.1f}%)")
        print(f"    Has IoT: {a['has_iot']} ({100*a['has_iot']/n:.1f}%)")
        print(f"    Notes meaningful: {a['meaningful_notes']} ({100*a['meaningful_notes']/n:.1f}%)")
        print(f"    Notes generic: {a['generic_notes']} ({100*a['generic_notes']/n:.1f}%)")
        print(f"    No notes: {a['no_notes']} ({100*a['no_notes']/n:.1f}%)")

        # Flag mismatches
        if tier == "E4":
            real_e4 = a["has_photo"] + a["has_gps"]
            if real_e4 < n:
                print(f"    ⚠️  {n - real_e4} E4 records lack photo/GPS — should be E3 or lower")
        elif tier == "E3":
            # E3 needs: source URL + price verification + chain + meaningful notes or photo/GPS
            real_e3 = sum(1 for p in properties
                          if (p["evidence_tier"] or "E1") == tier
                          and (p["source_url"] or p["evidence_photo_path"] or p["gps_lat"]))
            if real_e3 < n:
                print(f"    ⚠️  {n - real_e3} E3 records may lack real evidence")

    # =========================================================================
    # FINAL HONEST SUMMARY
    # =========================================================================
    print(f"\n{'='*70}")
    print(f"  HONEST SUMMARY")
    print(f"{'='*70}\n")

    # Count true data categories
    real_data = (len(scraped_real_source) + fs_photo + me_photo +
                 sum(1 for p in sensor if p["evidence_photo_path"]))
    print(f"  TRUE DATA (có source thực + evidence thực):")
    print(f"    Public scraped with URL: {len(scraped_real_source)}")
    print(f"    Field survey with photo: {fs_photo}")
    print(f"    Smartphone with photo: {sum(1 for p in sensor if p['evidence_photo_path'])}")
    print(f"    Total REAL data: ~{real_data} records ({100*real_data/total:.1f}%)\n")

    print(f"  SYNTHETIC / PROCEDURAL:")
    print(f"    batch_generator: {len(synthetic)} records → PURELY FAKE")
    print(f"    → evidence_tier should be E1, currently misclassified\n")

    print(f"  BORDERLINE / UNCLEAR:")
    print(f"    Scraped without source_url: {len(scraped_no_source)}")
    print(f"    Field survey without evidence: {fs_no_evidence + fs_notes_only}")
    print(f"    Manual entry without photo/GPS: {me_no_notes + me_generic}")
    print(f"    Total borderline: ~{len(scraped_no_source) + fs_no_evidence + fs_notes_only + me_no_notes + me_generic} records\n")

    print(f"  PROVENANCE CHAIN:")
    print(f"    {synthetic_with_chains} SYNTHETIC records have SIMULATED provenance chains")
    print(f"    → These chains are FAKE, added to fill gaps\n")

    print(f"  EVIDENCE TIER MISCLASSIFICATIONS:")
    misclass = 0
    for p in properties:
        if p["collection_method"] == "batch_generator" and p["evidence_tier"] not in (None, "E1"):
            misclass += 1
    print(f"    Synthetic records declared E2+: {misclass}")
    print(f"    → Should all be E1 (no real source)\n")

    print(f"  RECOMMENDATIONS:")
    print(f"    1. Set ALL batch_generator records to E1 immediately")
    print(f"    2. Remove simulated provenance chains from synthetic records")
    print(f"    3. Audit IoT IDs on public scraped — may be simulated")
    print(f"    4. Audit E4 records without photo/GPS → downgrade to E3")
    print(f"    5. Keep only {real_data} REAL records for production ML model")

    print(f"\n{'='*70}\n")

    conn.close()


if __name__ == "__main__":
    main()
