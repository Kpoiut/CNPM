#!/usr/bin/env python3
"""
STEP 3: Fix tier misclassifications caused by compute_tier() bug.

Bug: records with generic notes but no photo/GPS were assigned E2
instead of E1. Fixed logic:

  E4: photo + GPS + meaningful notes
  E3: photo OR GPS OR meaningful notes
  E2: has source URL, but NO photo/GPS/meaningful notes
  E1: no source URL, no real evidence

Usage:
    python scripts/step3_fix_tiers.py --dry-run
    python scripts/step3_fix_tiers.py --apply
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
    """Compute evidence tier based on ACTUAL evidence — fixed logic."""
    has_url = bool(prop.get("source_url"))
    has_photo = bool(prop.get("evidence_photo_path"))
    has_gps = bool(prop.get("gps_lat") or prop.get("latitude"))
    meaningful, _ = check_notes(prop.get("field_notes"))
    method = prop.get("collection_method") or ""

    # E4: photo + GPS + meaningful notes (real field survey)
    if has_photo and has_gps and meaningful:
        return "E4"

    # E3: photo OR GPS OR meaningful notes
    if has_photo or has_gps or meaningful:
        return "E3"

    # E2: has source URL, but NO photo/GPS/meaningful notes
    if has_url:
        return "E2"

    # E1: no source, no real evidence
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
    print(f"  STEP 3: FIX TIER MISCLASSIFICATIONS")
    print(f"{'='*70}\n")

    c.execute("""
        SELECT id, collection_method, evidence_tier, source_url,
               evidence_photo_path, gps_lat, latitude, iot_device_id, field_notes
        FROM properties
        WHERE price > 0
    """)
    props = [dict(r) for r in c.fetchall()]

    # Count proposed tiers
    tier_preview = {"E1": 0, "E2": 0, "E3": 0, "E4": 0, "E5": 0}
    tier_changes = []
    for p in props:
        new_tier = compute_tier(p)
        old_tier = p.get("evidence_tier") or "E1"
        tier_preview[new_tier] += 1
        if new_tier != old_tier:
            tier_changes.append((p["id"], old_tier, new_tier, p.get("collection_method") or "?"))

    print(f"Proposed tier distribution:")
    for tier in ["E5", "E4", "E3", "E2", "E1"]:
        cnt = tier_preview.get(tier, 0)
        pct = 100 * cnt / len(props) if props else 0
        bar = "█" * int(pct / 2)
        print(f"  {tier}: {cnt:4d} ({pct:5.1f}%) {bar}")

    print(f"\nTier changes: {len(tier_changes)}")
    print(f"\nChanged records:")
    # Group by change type
    changes_by_type = {}
    for prop_id, old, new, method in tier_changes:
        key = f"{old} → {new}"
        if key not in changes_by_type:
            changes_by_type[key] = []
        changes_by_type[key].append((prop_id, method))

    for change, records in sorted(changes_by_type.items()):
        print(f"  {change}: {len(records)} records")
        for prop_id, method in records[:3]:
            print(f"    id={prop_id}, method={method}")
        if len(records) > 3:
            print(f"    ... and {len(records) - 3} more")

    if args.dry_run and not args.apply:
        print(f"\n[DRY RUN] No changes applied.")
        conn.close()
        return

    if args.apply:
        ts = datetime.now(timezone.utc).isoformat()
        updates = 0
        for prop_id, old_tier, new_tier, _ in tier_changes:
            c.execute(
                "UPDATE properties SET evidence_tier = ?, evidence_tier_updated_at = ? WHERE id = ?",
                (new_tier, ts, prop_id)
            )
            updates += 1

        conn.commit()
        print(f"\n[APPLIED] Updated {updates} tier assignments")

        # Show final distribution
        print(f"\nFinal tier distribution:")
        c.execute("SELECT evidence_tier, COUNT(*) FROM properties WHERE price > 0 GROUP BY evidence_tier ORDER BY evidence_tier")
        total = sum(r[1] for r in c.fetchall())
        c.execute("SELECT evidence_tier, COUNT(*) FROM properties WHERE price > 0 GROUP BY evidence_tier ORDER BY evidence_tier")
        for r in c.fetchall():
            tier = r[0] or "E1"
            cnt = r[1]
            pct = 100 * cnt / total
            bar = "█" * int(pct / 2)
            print(f"  {tier}: {cnt:4d} ({pct:5.1f}%) {bar}")

        print(f"\n[DONE]")
        conn.close()


if __name__ == "__main__":
    main()
