#!/usr/bin/env python3
"""
STEP 2: Clean database - delete synthetic data, reset provenance, re-evaluate tiers.

Operations:
1. Delete all batch_generator records (2500 fake records)
2. Delete provenance chains for deleted records
3. Reset evidence tiers based on ACTUAL evidence present

Evidence-based tier evaluation:
  E1: No source, no verification
  E2: Single source (URL), no physical evidence
  E3: Source URL + at least 1 of: photo, GPS, meaningful notes
  E4: Source URL + photo + GPS + meaningful notes (real field survey)
  E5: Government records (not applicable to scraped data)

Usage:
    python scripts/step2_clean.py --dry-run
    python scripts/step2_clean.py --apply
"""
import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = Path(__file__).parent.parent / "real_estate_avm.db"
GENERIC_PATTERNS = [
    "khảo sát sơ bộ", "thu thập thông tin qua", "hỏi hàng xóm",
    "quan sát bên ngoài", "cần xác minh thêm", "placeholder",
    "test", "sample", "chưa xác minh", "sơ bộ",
]
MEASUREMENT_PATTERNS = [
    "m2", "mét vuông", "mặt tiền", "mat tien", "mat_tien",
    "rộng", "sâu", "dài", "cao", "ngõ", "đường", "tầng", "diện tích",
]


def check_notes(notes):
    if not notes or len((notes or "").strip()) < 30:
        return False, "too_short"
    text_lower = notes.lower()
    if any(p in text_lower for p in GENERIC_PATTERNS):
        return False, "generic"
    if not any(p in text_lower for p in MEASUREMENT_PATTERNS):
        return False, "no_measurement"
    return True, "meaningful"


def compute_tier(prop: dict) -> str:
    """Compute evidence tier based on ACTUAL evidence present."""
    has_url = bool(prop.get("source_url"))
    has_photo = bool(prop.get("evidence_photo_path"))
    has_gps = bool(prop.get("gps_lat") or prop.get("latitude"))
    has_iot = bool(prop.get("iot_device_id"))
    meaningful, _ = check_notes(prop.get("field_notes"))
    method = prop.get("collection_method") or ""

    # batch_generator is always E1 (already deleted)
    # IoT on public scraped: treat as NOT physical evidence (likely simulated)
    # True physical evidence: photo + GPS from field survey

    if method in ("field_survey", "smartphone_sensor_capture", "manual_entry"):
        # Self-collected: needs photo AND GPS for E4
        if has_photo and has_gps and meaningful:
            return "E4"
        # E3: photo OR GPS OR meaningful notes
        if has_photo or has_gps or meaningful:
            return "E3"
        return "E2"
    else:
        # Public scraped: E2-E3 based on evidence
        if has_url and (has_photo or has_gps or meaningful):
            return "E3"
        if has_url:
            return "E2"
        return "E1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print(f"\n{'='*70}")
    print(f"  STEP 2: CLEAN DATABASE")
    print(f"{'='*70}\n")

    # Count before
    c.execute("SELECT COUNT(*) FROM properties WHERE price > 0")
    total_before = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM provenance_chains")
    chains_before = c.fetchone()[0]

    print(f"Before: {total_before} properties, {chains_before} provenance chains\n")

    # Count batch_generator
    c.execute("SELECT COUNT(*) FROM properties WHERE collection_method = 'batch_generator'")
    synthetic_count = c.fetchone()[0]
    print(f"Synthetic records to delete: {synthetic_count}")

    # Get IDs of batch_generator records
    c.execute("SELECT id FROM properties WHERE collection_method = 'batch_generator'")
    synthetic_ids = [r[0] for r in c.fetchall()]
    print(f"Synthetic property IDs: {synthetic_ids[:5]}... ({len(synthetic_ids)} total)")

    # Count real records
    c.execute("SELECT COUNT(*) FROM properties WHERE collection_method != 'batch_generator' AND price > 0")
    real_count = c.fetchone()[0]
    print(f"Real records to keep: {real_count}\n")

    # Show tier reassignment preview for real records
    print(f"Tier reassignment preview for real records:")
    c.execute("""
        SELECT id, collection_method, evidence_tier, source_url,
               evidence_photo_path, gps_lat, latitude, iot_device_id, field_notes
        FROM properties
        WHERE collection_method != 'batch_generator'
        AND price > 0
    """)
    real_props = [dict(r) for r in c.fetchall()]

    tier_preview = {"E1": 0, "E2": 0, "E3": 0, "E4": 0, "E5": 0}
    tier_changes = 0
    for p in real_props:
        new_tier = compute_tier(p)
        old_tier = p.get("evidence_tier") or "E1"
        tier_preview[new_tier] += 1
        if new_tier != old_tier:
            tier_changes += 1

    print(f"  Proposed tier distribution after cleanup:")
    for tier in ["E5", "E4", "E3", "E2", "E1"]:
        cnt = tier_preview.get(tier, 0)
        pct = 100 * cnt / len(real_props) if real_props else 0
        bar = "█" * int(pct / 2)
        print(f"    {tier}: {cnt:4d} ({pct:5.1f}%) {bar}")

    print(f"\n  Tier changes: {tier_changes}/{len(real_props)}")

    # Show records with tier changes
    print(f"\n  Records changing tier (sample):")
    shown = 0
    for p in real_props:
        new_tier = compute_tier(p)
        old_tier = p.get("evidence_tier") or "E1"
        if new_tier != old_tier and shown < 15:
            method = p.get("collection_method") or "?"
            url = bool(p.get("source_url"))
            photo = bool(p.get("evidence_photo_path"))
            gps = bool(p.get("gps_lat") or p.get("latitude"))
            notes_m, _ = check_notes(p.get("field_notes"))
            print(f"    id={p['id']}: {old_tier} → {new_tier} (method={method}, "
                  f"url={url}, photo={photo}, gps={gps}, notes={notes_m})")
            shown += 1

    if args.dry_run and not args.apply:
        print(f"\n[DRY RUN] No changes applied.")
        print(f"Run with --apply to execute cleanup.")
        conn.close()
        return

    if args.apply:
        print(f"\n[APPLYING] Executing cleanup...")
        ts = datetime.now(timezone.utc).isoformat()

        # Step 2a: Delete provenance chains for batch_generator records
        placeholders = ",".join(["?"] * len(synthetic_ids))
        c.execute(f"DELETE FROM provenance_chains WHERE property_id IN ({placeholders})",
                   synthetic_ids)
        chains_deleted = c.rowcount
        print(f"  Deleted {chains_deleted} provenance chains from synthetic records")

        # Step 2b: Delete batch_generator records
        c.execute("DELETE FROM properties WHERE collection_method = 'batch_generator'")
        records_deleted = c.rowcount
        print(f"  Deleted {records_deleted} synthetic records")

        # Step 2c: Re-evaluate tiers for remaining real records
        c.execute("""
            SELECT id, collection_method, evidence_tier, source_url,
                   evidence_photo_path, gps_lat, latitude, iot_device_id, field_notes
            FROM properties
            WHERE price > 0
        """)
        real_props = [dict(r) for r in c.fetchall()]

        tier_updates = 0
        for p in real_props:
            new_tier = compute_tier(p)
            old_tier = p.get("evidence_tier") or "E1"
            if new_tier != old_tier:
                c.execute(
                    "UPDATE properties SET evidence_tier = ?, evidence_tier_updated_at = ? WHERE id = ?",
                    (new_tier, ts, p["id"])
                )
                tier_updates += 1

        conn.commit()

        # Count after
        c.execute("SELECT COUNT(*) FROM properties WHERE price > 0")
        total_after = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM provenance_chains")
        chains_after = c.fetchone()[0]

        print(f"\n  Updated tiers for {tier_updates} records")
        print(f"\nAfter: {total_after} properties, {chains_after} provenance chains")

        # Final tier distribution
        print(f"\nFinal tier distribution:")
        c.execute("SELECT evidence_tier, COUNT(*) FROM properties WHERE price > 0 GROUP BY evidence_tier ORDER BY evidence_tier")
        for r in c.fetchall():
            tier = r[0] or "E1"
            cnt = r[1]
            pct = 100 * cnt / total_after
            bar = "█" * int(pct / 2)
            print(f"  {tier}: {cnt:4d} ({pct:5.1f}%) {bar}")

        print(f"\n[DONE] Cleanup complete.")
        conn.close()


if __name__ == "__main__":
    main()
