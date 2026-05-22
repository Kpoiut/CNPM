#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit & Repair Database — Quét toàn bộ DB, báo cáo violations, và sửa nếu --fix.

Báo cáo:
  1. Schema compliance: kiểm tra nullable vs NOT NULL
  2. Domain violations: giá trị nằm ngoài canonical enum
  3. NULL violations: trường bắt buộc có NULL
  4. Scope violations: quận ngoài 6 quận scope
  5. Data integrity: price/area consistency

Repair:
  --dry-run (default): chỉ báo cáo
  --fix: áp dụng fixes cho enum normalization

Usage:
    python scripts/audit_and_repair_db.py              # dry-run audit
    python scripts/audit_and_repair_db.py --fix       # fix + report
    python scripts/audit_and_repair_db.py --fix --dry-run  # show what would be fixed
    python scripts/audit_and_repair_db.py --users    # seed users table
"""

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.database import SessionLocal, engine
from src.backend.models import Property, AuditLog
from src.backend.auth.models import User
from src.backend.data_sanitizer import (
    DatabaseValidator,
    PropertySanitizer,
    UserSanitizer,
    CANONICAL_PROPERTY_TYPES,
    CANONICAL_PROVINCES,
    SCOPE_6_DISTRICTS,
    CANONICAL_LEGAL_STATUS,
    LEGAL_STATUS_VN_TO_EN,
    FURNISHING_TO_CANONICAL,
    CANONICAL_FURNISHING,
    CANONICAL_SOURCE_ACCESS_METHODS,
    SOURCE_METHOD_TO_CANONICAL,
    CANONICAL_EVIDENCE_TIERS,
    CANONICAL_RECORD_STATUS,
    ValidationError,
)


# ==============================================================================
# REPAIR HELPERS
# ==============================================================================

def fix_legal_status(value: str) -> str:
    """Map VN → EN canonical legal_status."""
    if value is None:
        return "pending"
    key = str(value).strip().lower()
    return LEGAL_STATUS_VN_TO_EN.get(key, value)


def fix_furnishing(value: str) -> str:
    """Map furnishing → canonical."""
    if value is None:
        return "null"
    key = str(value).strip().lower()
    return FURNISHING_TO_CANONICAL.get(key, "null")


def fix_source_method(value: str) -> str:
    """Map source_access_method → canonical."""
    if value is None:
        return "batch_generator"
    key = str(value).strip().lower()
    return SOURCE_METHOD_TO_CANONICAL.get(key, "batch_generator")


# ==============================================================================
# AUDIT
# ==============================================================================

def audit_properties(db, *, fix: bool = False) -> dict:
    """Audit all property records. Returns summary dict."""
    props = db.query(Property).all()
    total = len(props)

    # Counters
    v_property_type = 0
    v_province = 0
    v_scope = 0
    v_area = 0
    v_price = 0
    v_source_method_null = 0
    v_source_method_bad = 0
    v_legal_status = 0
    v_furnishing = 0
    v_evidence_tier = 0
    v_record_status = 0
    v_price_per_m2_missing = 0
    v_price_per_m2_wrong = 0
    v_verification_status_dup = 0

    # Track records to fix
    records_to_fix: list[tuple[int, str, str, str]] = []  # (id, field, old, new)

    for prop in props:
        dirty = False
        fixes: list[str] = []

        # property_type
        if prop.property_type not in CANONICAL_PROPERTY_TYPES:
            v_property_type += 1
            dirty = True

        # province_city
        if prop.province_city not in CANONICAL_PROVINCES:
            v_province += 1
            dirty = True

        # Scope
        if (prop.province_city, prop.district) not in SCOPE_6_DISTRICTS:
            v_scope += 1

        # Area
        if prop.area_m2 is None or prop.area_m2 <= 0:
            v_area += 1
            dirty = True
        elif prop.area_m2 < 10 or prop.area_m2 > 20000:
            v_area += 1

        # Price
        if prop.price is None or prop.price <= 0:
            v_price += 1
            dirty = True
        elif prop.price < 100_000_000:
            v_price += 1

        # source_access_method NULL
        if prop.source_access_method is None:
            v_source_method_null += 1
            records_to_fix.append((prop.id, "source_access_method", None, "batch_generator"))
            dirty = True
        elif prop.source_access_method not in CANONICAL_SOURCE_ACCESS_METHODS:
            v_source_method_bad += 1
            new_val = fix_source_method(prop.source_access_method)
            records_to_fix.append((prop.id, "source_access_method", prop.source_access_method, new_val))
            dirty = True

        # legal_status: VN → EN canonical, or unknown → 'unknown'
        if prop.legal_status in LEGAL_STATUS_VN_TO_EN:
            new_val = fix_legal_status(prop.legal_status)
            if new_val != prop.legal_status:  # Only count/fix if actually different
                v_legal_status += 1
                records_to_fix.append((prop.id, "legal_status", prop.legal_status, new_val))
                dirty = True
        elif prop.legal_status is not None and prop.legal_status not in CANONICAL_LEGAL_STATUS:
            v_legal_status += 1
            new_val = "unknown"
            records_to_fix.append((prop.id, "legal_status", prop.legal_status, new_val))
            dirty = True

        # furnishing
        if prop.furnishing is not None:
            f_key = str(prop.furnishing).strip().lower()
            if f_key not in CANONICAL_FURNISHING and f_key not in FURNISHING_TO_CANONICAL:
                v_furnishing += 1
            elif f_key in FURNISHING_TO_CANONICAL:
                canonical = FURNISHING_TO_CANONICAL[f_key]
                if str(prop.furnishing) != canonical:
                    records_to_fix.append((prop.id, "furnishing", prop.furnishing, canonical))
                    dirty = True

        # evidence_tier
        if prop.evidence_tier not in CANONICAL_EVIDENCE_TIERS:
            v_evidence_tier += 1

        # record_status
        if prop.record_status not in CANONICAL_RECORD_STATUS:
            v_record_status += 1

        # price_per_m2 missing
        if prop.price and prop.area_m2 and (prop.price > 0 and prop.area_m2 > 0):
            expected_ppm = round(prop.price / prop.area_m2, -3)
            if prop.price_per_m2 is None:
                v_price_per_m2_missing += 1
                records_to_fix.append((prop.id, "price_per_m2", None, expected_ppm))
                dirty = True
            elif abs(prop.price_per_m2 - expected_ppm) > 1_000_000:
                v_price_per_m2_wrong += 1
                records_to_fix.append((prop.id, "price_per_m2", prop.price_per_m2, expected_ppm))
                dirty = True

    # Apply fixes
    if fix and records_to_fix:
        print(f"\n  Applying {len(records_to_fix)} field fixes...")
        # Group by field
        by_field: dict[str, list] = {}
        for rec_id, field, old, new in records_to_fix:
            by_field.setdefault(field, []).append((rec_id, old, new))

        for field, fixes_list in by_field.items():
            prop_ids = [f[0] for f in fixes_list]
            props_to_update = db.query(Property).filter(Property.id.in_(prop_ids)).all()
            id_to_prop = {p.id: p for p in props_to_update}

            for rec_id, old, new in fixes_list:
                prop = id_to_prop.get(rec_id)
                if prop is None:
                    continue
                old_val = getattr(prop, field)
                setattr(prop, field, new)
                # Audit log
                log = AuditLog(
                    record_id=rec_id,
                    table_name="properties",
                    action_type="DATA_REPAIR",
                    changed_by="system:audit_repair",
                    old_value_json=str(old_val),
                    new_value_json=str(new),
                    change_note=f"audit_repair: canonicalize {field}",
                )
                db.add(log)

        db.commit()
        print(f"  ✅ Applied {len(records_to_fix)} fixes")

    return {
        "total": total,
        "v_property_type": v_property_type,
        "v_province": v_province,
        "v_scope_outside": v_scope,
        "v_area": v_area,
        "v_price": v_price,
        "v_source_method_null": v_source_method_null,
        "v_source_method_bad": v_source_method_bad,
        "v_legal_status": v_legal_status,
        "v_furnishing": v_furnishing,
        "v_evidence_tier": v_evidence_tier,
        "v_record_status": v_record_status,
        "v_price_per_m2_missing": v_price_per_m2_missing,
        "v_price_per_m2_wrong": v_price_per_m2_wrong,
        "fixes_available": len(records_to_fix),
    }


def audit_schema(db) -> dict:
    """Audit actual DB schema vs expected constraints."""
    from sqlalchemy import text

    results = {}

    # Check properties table constraints
    result = db.execute(text("PRAGMA table_info(properties)"))
    columns = {r[1]: r for r in result}

    results["properties_not_null"] = []
    results["properties_null_ok"] = []

    # Fields that SHOULD be NOT NULL per design
    required_not_null = [
        "property_type", "province_city", "district", "area_m2", "price",
        "source_name", "source_access_method",
    ]

    for col in required_not_null:
        if col in columns:
            info = columns[col]
            nullable = info[3]  # PRAGMA: 0 = NOT NULL, 1 = NULL
            if nullable == 1:
                results["properties_not_null"].append(
                    f"  ❌ {col}: is NULL but should be NOT NULL"
                )
            else:
                results["properties_null_ok"].append(f"  ✅ {col}: NOT NULL")
        else:
            results["properties_not_null"].append(f"  ❌ {col}: MISSING from table")

    return results


def audit_users(db) -> dict:
    """Audit users table."""
    users = db.query(User).all()
    return {
        "count": len(users),
        "has_admin": any(u.role == "admin" for u in users),
        "usernames": [u.username for u in users],
    }


# ==============================================================================
# USER SEEDING
# ==============================================================================

def seed_admin_user(db, username: str = "admin", password: str = "admin123") -> bool:
    """Seed admin user if not exists. Returns True if created."""
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        print(f"  ⏭️  User '{username}' already exists")
        return False

    # Hash password
    from src.backend.auth.service import hash_password
    hashed = hash_password(password)

    user = User(
        username=username,
        email=None,
        hashed_password=hashed,
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.flush()

    # Audit log
    log = AuditLog(
        record_id=user.id,
        table_name="users",
        action_type="SEED_ADMIN",
        changed_by="system:audit_repair",
        new_value_json=f'{{"username": "{username}", "role": "admin"}}',
        change_note="Initial admin seed via audit_repair script",
    )
    db.add(log)
    db.commit()
    print(f"  ✅ Created admin user: {username}")
    return True


# ==============================================================================
# MAIN
# ==============================================================================

def print_report(summary: dict):
    total = summary["total"]
    if total == 0:
        print("  No records to audit.")
        return

    print(f"\n{'='*70}")
    print(f" DATABASE AUDIT REPORT — {total} properties")
    print(f"{'='*70}")

    print(f"\n[1] CRITICAL — source_access_method NULL")
    print(f"    Violations: {summary['v_source_method_null']}/{total}")
    if summary["v_source_method_null"] > 0:
        print(f"    → Fix available: --fix will set to 'batch_generator'")

    print(f"\n[2] source_access_method non-canonical")
    print(f"    Violations: {summary['v_source_method_bad']}/{total}")
    print(f"    → Fix available: playwright→scraper, others→batch_generator")

    print(f"\n[3] legal_status: VN values (should be EN canonical)")
    print(f"    Violations: {summary['v_legal_status']}/{total}")
    print(f"    VN values: Sổ đỏ, Sổ hồng, Hợp đồng mua bán")
    print(f"    → Fix available: map to EN canonical")

    print(f"\n[4] furnishing: non-canonical values")
    print(f"    Violations: {summary['v_furnishing']}/{total}")

    print(f"\n[5] property_type: out of canonical domain")
    print(f"    Violations: {summary['v_property_type']}/{total}")
    print(f"    Canonical: {sorted(CANONICAL_PROPERTY_TYPES)}")

    print(f"\n[6] province_city: out of canonical domain")
    print(f"    Violations: {summary['v_province']}/{total}")
    print(f"    Canonical: {sorted(CANONICAL_PROVINCES)}")

    print(f"\n[7] Scope: (province, district) not in 6-district scope")
    print(f"    Violations: {summary['v_scope_outside']}/{total}")

    print(f"\n[8] area_m2: NULL, 0, or out of range (10-20000)")
    print(f"    Violations: {summary['v_area']}/{total}")

    print(f"\n[9] price: NULL, 0, or < 100M VND")
    print(f"    Violations: {summary['v_price']}/{total}")

    print(f"\n[10] price_per_m2: missing or inconsistent")
    print(f"    Missing: {summary['v_price_per_m2_missing']}")
    print(f"    Wrong: {summary['v_price_per_m2_wrong']}")
    if summary["v_price_per_m2_missing"] + summary["v_price_per_m2_wrong"] > 0:
        print(f"    → Fix available: --fix will recompute from price/area_m2")

    print(f"\n[11] evidence_tier: not in E1-E5")
    print(f"    Violations: {summary['v_evidence_tier']}/{total}")

    print(f"\n[12] record_status: not in canonical domain")
    print(f"    Violations: {summary['v_record_status']}/{total}")
    print(f"    Canonical: {sorted(CANONICAL_RECORD_STATUS)}")

    total_violations = sum(v for k, v in summary.items() if k.startswith("v_"))
    print(f"\n{'='*70}")
    print(f" Total field violations: {total_violations}")
    print(f" Fixes available (auto-fixable): {summary['fixes_available']}")
    print(f"{'='*70}")
    print(f"\n  To auto-fix: python scripts/audit_and_repair_db.py --fix")


def main():
    parser = argparse.ArgumentParser(description="Audit & repair real-estate-avm database")
    parser.add_argument("--fix", action="store_true", help="Apply fixes to DB")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fixed (default)")
    parser.add_argument("--users", action="store_true", help="Seed admin user")
    parser.add_argument("--admin-user", default="admin", help="Admin username")
    parser.add_argument("--admin-password", default="admin123", help="Admin password")
    args = parser.parse_args()

    db = SessionLocal()

    # ── Schema audit ──
    print("\n" + "=" * 70)
    print(" SCHEMA AUDIT")
    print("=" * 70)
    schema_results = audit_schema(db)
    if schema_results["properties_not_null"]:
        print("\n Columns needing NOT NULL constraints:")
        for msg in schema_results["properties_not_null"]:
            print(msg)
    if schema_results["properties_null_ok"]:
        print("\n Columns with correct NOT NULL:")
        for msg in schema_results["properties_null_ok"]:
            print(msg)

    # ── User audit ──
    print("\n" + "=" * 70)
    print(" USERS TABLE AUDIT")
    print("=" * 70)
    user_results = audit_users(db)
    print(f"  Total users: {user_results['count']}")
    print(f"  Has admin: {user_results['has_admin']}")
    if user_results["usernames"]:
        print(f"  Usernames: {user_results['usernames']}")
    else:
        print("  ⚠️  No users — auth will fail!")
        if args.users or args.fix:
            print(f"\n  Seeding admin user '{args.admin_user}'...")
            seed_admin_user(db, args.admin_user, args.admin_password)

    # ── Properties audit ──
    print("\n" + "=" * 70)
    print(" PROPERTIES AUDIT")
    print("=" * 70)
    summary = audit_properties(db, fix=args.fix)
    print_report(summary)

    db.close()


if __name__ == "__main__":
    main()
