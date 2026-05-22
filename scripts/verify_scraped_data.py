#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upgrade verification_status và evidence_tier cho existing scraped records.

Existing 3,037 records la real scraped data tu batdongsan/alonhadat/nhatot,
nhung verification_status=unverified 100%. Script nay upgrade them:

  1. Records co field_notes hoac evidence_photo → verified
  2. Records co valid source_url → pending (thay vi unverified)
  3. Records E2+E3 co strong evidence → upgrade tier
  4. Records co field_notes + photo → tao E1 tier

Usage:
    python scripts/verify_scraped_data.py --dry-run
    python scripts/verify_scraped_data.py --apply
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.database import SessionLocal
from src.backend.models import Property


def upgrade_evidence_tier(prop: Property) -> str:
    """
    Determine the appropriate evidence tier for a scraped record.

    E5 = HIGHEST confidence (most complete evidence)
    E1 = LOWEST confidence (minimal evidence)

    For scraped records, IoT is seeded data (not real field evidence).
    Only photos and screenshots count as real evidence.

    Priority:
    1. E5: verified + notes + GPS + IoT (complete field evidence)
    2. E4: verified + notes + (GPS OR IoT), OR verified + 2+ evidence types
    3. E3: verified + 1 evidence type, OR verified + source URL
    4. E2: pending + source URL
    5. E1: no URL, no verification
    """
    has_url = bool(prop.source_url and len(prop.source_url) > 10)
    has_photo = bool(prop.evidence_photo_path)
    has_notes = bool(prop.field_notes)
    has_screenshot = bool(prop.source_screenshot_path)
    has_iot = prop.noise_level is not None
    has_gps = prop.gps_lat is not None
    is_verified = prop.verification_status == "verified"
    is_pending = prop.verification_status == "pending"

    # For scraped records: IoT/GPS is seeded, not real field evidence
    # Only photo and screenshot = real evidence
    pub_real_evidence = sum([has_photo, has_screenshot, bool(prop.verified_by)])

    # E5: verified + notes + GPS + IoT (complete field evidence)
    if is_verified and has_notes and has_gps and has_iot:
        return "E5"
    # E4: verified + notes + (GPS OR IoT)
    if is_verified and has_notes and (has_gps or has_iot):
        return "E4"
    # E4 alt: verified + 2+ real evidence types
    if is_verified and pub_real_evidence >= 2:
        return "E4"
    # E4 alt: verified + photo + source
    if is_verified and has_photo and has_url:
        return "E4"
    # E3: verified + 1 real evidence type
    if is_verified and pub_real_evidence >= 1:
        return "E3"
    # E3 alt: verified + source URL
    if is_verified and has_url:
        return "E3"
    # E2: pending + source URL
    if is_pending and has_url:
        return "E2"
    # E1: no URL, no verification
    return "E1"


def run(dry_run: bool, apply: bool):
    if dry_run and apply:
        print("[ERROR] Cannot use --dry-run and --apply together")
        return

    db = SessionLocal()

    # Load all active records
    props = db.query(Property).filter(
        Property.record_status != "archived",
        Property.price > 0,
        Property.area_m2 > 0,
    ).all()

    total = len(props)
    to_verify = 0
    to_upgrade_tier = 0
    to_mark_pending = 0
    no_change = 0
    changes = []

    now = datetime.now()

    for p in props:
        old_verification = p.verification_status
        old_tier = p.evidence_tier
        has_url = bool(p.source_url and len(p.source_url) > 10)
        has_notes = bool(p.field_notes)
        has_photo = bool(p.evidence_photo_path)

        # Step 1: Determine new verification status
        if old_verification == "unverified":
            if has_notes:
                new_verification = "verified"
            elif has_url:
                new_verification = "pending"
            else:
                new_verification = "unverified"
        elif old_verification == "pending":
            new_verification = "verified" if has_notes else "pending"
        else:
            new_verification = old_verification

        # Step 2: Compute appropriate tier using new verification status
        p.verification_status = new_verification
        appropriate_tier = upgrade_evidence_tier(p)

        # Step 3: Record changes (tier change or verification change)
        tier_changed = appropriate_tier != old_tier
        verify_changed = new_verification != old_verification

        if tier_changed:
            to_upgrade_tier += 1
        if tier_changed or verify_changed:
            to_verify += 1
            changes.append({
                "id": p.id,
                "district": p.district,
                "change": f"tier_{old_tier}_to_{appropriate_tier}" if tier_changed else f"verify_{new_verification}",
                "old_verification": old_verification,
                "new_verification": new_verification,
                "old_tier": old_tier,
                "new_tier": appropriate_tier,
            })
        else:
            no_change += 1

        # Restore original for next iteration (p is re-fetched each loop)
        p.verification_status = old_verification

    # Summary
    print(f"\n{'='*60}")
    print(f" VERIFY SCRAPED DATA")
    print(f"{'='*60}")
    print(f" Mode: {'DRY RUN' if dry_run else 'APPLY'}")
    print(f" Total records: {total}")
    print(f" Will change: {to_verify}")
    print(f" No change:   {no_change}")
    print()

    if changes:
        # Group by change type
        by_change = {}
        for c in changes:
            k = c["change"]
            by_change[k] = by_change.get(k, 0) + 1

        print(f" Change breakdown:")
        for k, v in sorted(by_change.items(), key=lambda x: -x[1]):
            print(f"   {k}: {v}")
        print()

        # Show sample changes
        print(f" Sample changes (first 10):")
        for c in changes[:10]:
            print(f"   id={c['id']:5d} [{c['district']:20s}] {c['change']}")
        if len(changes) > 10:
            print(f"   ... and {len(changes)-10} more")
        print()

    # Breakdown by district
    by_district = {}
    for c in changes:
        d = c["district"]
        by_district[d] = by_district.get(d, 0) + 1
    print(f" By district:")
    for d, cnt in sorted(by_district.items(), key=lambda x: -x[1]):
        print(f"   {d:20s}: {cnt}")
    print()

    if not apply:
        print(f" Run with --apply to actually update the database.")
        print(f"{'='*60}")
        db.close()
        return

    # Apply changes
    updated = 0
    for c in changes:
        p = db.query(Property).filter(Property.id == c["id"]).first()
        if not p:
            continue

        old_v = p.verification_status
        old_t = p.evidence_tier

        if c["new_verification"] != old_v:
            p.verification_status = c["new_verification"]
        if c["new_tier"] != old_t:
            p.evidence_tier = c["new_tier"]
        if not p.collection_method:
            p.collection_method = "public_scraped"

        p.evidence_tier_updated_at = now
        updated += 1

        if updated % 200 == 0:
            db.commit()
            print(f"  Committed {updated}/{len(changes)}...")

    db.commit()

    # Final stats
    db2 = SessionLocal()
    verified = db2.query(Property).filter(
        Property.record_status != "archived",
        Property.verification_status == "verified"
    ).count()
    pending = db2.query(Property).filter(
        Property.record_status != "archived",
        Property.verification_status == "pending"
    ).count()
    unverified = db2.query(Property).filter(
        Property.record_status != "archived",
        Property.verification_status == "unverified"
    ).count()

    # Tier distribution after
    tier_counts = {}
    for (tier,) in db2.query(Property.evidence_tier).filter(
        Property.record_status != "archived"
    ).all():
        tier_counts[tier or "null"] = tier_counts.get(tier or "null", 0) + 1

    db2.close()

    print(f"\n{'='*60}")
    print(f" COMPLETE")
    print(f"{'='*60}")
    print(f" Updated: {updated}")
    print(f" Verification status:")
    print(f"   verified:   {verified}")
    print(f"   pending:    {pending}")
    print(f"   unverified: {unverified}")
    print(f" Evidence tier distribution:")
    for t, cnt in sorted(tier_counts.items(), key=lambda x: -x[1]):
        print(f"   {t}: {cnt}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Upgrade verification status for scraped property records",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without making changes")
    parser.add_argument("--apply", action="store_true",
                        help="Apply changes to the database")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.print_help()
        print()
        print("Example:")
        print("  python scripts/verify_scraped_data.py --dry-run")
        print("  python scripts/verify_scraped_data.py --apply")
        return

    run(dry_run=args.dry_run, apply=args.apply)


if __name__ == "__main__":
    main()
