#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migrate evidence_tier values — invert tier semantics.

OLD (E5=lowest, E1=highest):
  E1 → verified + field + real_evidence  (strongest)
  E2 → verified + evidence               (strong)
  E3 → partial validation               (medium)
  E4 → public listing                   (weak)
  E5 → minimal evidence                 (weakest)

NEW (E5=highest, E1=lowest):
  E5 → verified + 3+ evidence types     (most complete)
  E4 → verified + 2+ evidence types    (strong)
  E3 → verified + 1 evidence type      (partial)
  E2 → has source URL                   (minimal)
  E1 → no source, no verification      (least)

Inversion mapping:
  E1 → E5 (was strongest, now lowest → highest)
  E2 → E4 (was strong, now medium-high)
  E3 → E3 (stays same)
  E4 → E2 (was weak, now medium)
  E5 → E1 (was weakest, now lowest)

Usage:
    python scripts/migrate_evidence_tier_inversion.py --dry-run
    python scripts/migrate_evidence_tier_inversion.py --apply
"""
import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "real_estate_avm.db"

INVERSION = {
    "E1": "E5",
    "E2": "E4",
    "E3": "E3",
    "E4": "E2",
    "E5": "E1",
}

def invert_tier(tier):
    if not tier:
        return "E1"
    return INVERSION.get(tier, tier)


def main():
    parser = argparse.ArgumentParser(description="Migrate evidence_tier — invert E1↔E5, E2↔E4")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--apply", action="store_true", help="Apply changes to database")
    parser.add_argument("--db-path", default=None, help="DB path override")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.print_help()
        print("\n  python scripts/migrate_evidence_tier_inversion.py --dry-run")
        print("  python scripts/migrate_evidence_tier_inversion.py --apply")
        return

    db_path = Path(args.db_path) if args.db_path else DB_PATH
    if not db_path.exists():
        print(f"ERROR: DB not found: {db_path}")
        sys.exit(1)

    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Count by current tier
    tier_counts = {}
    for (tier,) in conn.execute("SELECT evidence_tier FROM properties WHERE evidence_tier IS NOT NULL"):
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    print(f"\n{'='*65}")
    print(f"  MIGRATE EVIDENCE TIER — INVERT SEMANTICS")
    print(f"  E5=highest (was lowest), E1=lowest (was highest)")
    print(f"{'='*65}")
    print(f"  Database: {db_path}")
    print(f"  Mode:     {'DRY RUN' if args.dry_run else 'APPLY'}")
    print(f"\n  Current tier distribution:")
    for tier in ["E1", "E2", "E3", "E4", "E5"]:
        count = tier_counts.get(tier, 0)
        new_tier = invert_tier(tier)
        arrow = f"→ {new_tier}"
        print(f"    {tier}: {count:>5} records  {arrow}")

    if args.dry_run:
        conn.close()
        return

    # Apply: recompute ALL tiers using the new classification logic
    # Import the quality assessment module
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.backend.quality_assessment import classify_evidence_tier

    props = conn.execute(
        "SELECT id, verification_status, data_origin_type, evidence_photo_path, "
        "field_notes, noise_level, gps_lat, latitude, source_name, source_url, "
        "source_screenshot_path, collected_by, verified_by, verified_at, "
        "collection_method, image_url "
        "FROM properties "
        "WHERE record_status != 'archived' AND price > 0 AND area_m2 > 0"
    ).fetchall()

    updated = 0
    unchanged = 0
    new_counts = {"E1": 0, "E2": 0, "E3": 0, "E4": 0, "E5": 0}

    for row in props:
        # Build record WITHOUT evidence_tier so classify_evidence_tier recomputes
        record = {
            "id": row[0],
            "verification_status": row[1],
            "data_origin_type": row[2],
            "evidence_photo_path": row[3],
            "field_notes": row[4],
            "noise_level": row[5],
            "gps_lat": row[6],
            "latitude": row[7],
            "source_name": row[8],
            "source_url": row[9],
            "source_screenshot_path": row[10],
            "collected_by": row[11],
            "verified_by": row[12],
            "verified_at": row[13],
            "collection_method": row[14],
            "image_url": row[15],
        }
        result = classify_evidence_tier(record)
        new_tier = result["tier"]
        old_tier = conn.execute(
            "SELECT evidence_tier FROM properties WHERE id = ?", (row[0],)
        ).fetchone()[0]

        if old_tier != new_tier:
            conn.execute(
                "UPDATE properties SET evidence_tier = ? WHERE id = ?",
                (new_tier, row[0])
            )
            updated += 1
        else:
            unchanged += 1
        new_counts[new_tier] = new_counts.get(new_tier, 0) + 1

    conn.commit()

    print(f"\n  Migration result (full recompute):")
    print(f"    Updated:   {updated}")
    print(f"    Unchanged: {unchanged}")
    print(f"\n  New tier distribution:")
    total = sum(new_counts.values())
    for tier in ["E1", "E2", "E3", "E4", "E5"]:
        count = new_counts[tier]
        pct = count / total * 100 if total > 0 else 0
        desc = TIER_DESCRIPTIONS.get(tier, "")
        print(f"    {tier}: {count:>5} ({pct:>5.1f}%)  {desc}")
    print(f"{'='*65}")
    print(f"  COMPLETE — tiers recomputed: E5=highest, E1=lowest")
    print(f"{'='*65}")

    conn.close()


TIER_DESCRIPTIONS = {
    "E1": "E1 — Ít bằng chứng nhất (no source, no verification)",
    "E2": "E2 — Có nguồn (has source URL)",
    "E3": "E3 — Một phần (verified + 1 evidence type)",
    "E4": "E4 — Nhiều bằng chứng (verified + 2+ evidence types)",
    "E5": "E5 — Đầy đủ nhất (verified + 3+ evidence types)",
}


if __name__ == "__main__":
    main()
