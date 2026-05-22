#!/usr/bin/env python3
"""
Fix self-collected property fields and generate provenance chains.

Issues addressed:
1. Verified properties (181) have NO provenance chains — generate chains
2. Field columns may be swapped (collection_method vs collected_by)
3. Self-collected properties need proper provenance tracking

Usage:
    python scripts/fix_self_collected_fields.py --dry-run
    python scripts/fix_self_collected_fields.py --apply
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "real_estate_avm.db")


def compute_hash(data: dict) -> str:
    """Compute deterministic SHA256 hash for a record."""
    serializable = {k: str(v) for k, v in data.items() if v is not None}
    return hashlib.sha256(
        json.dumps(serializable, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def generate_provenance_for_verified(conn: sqlite3.Connection, dry_run: bool = True) -> dict:
    """Generate provenance chains for all verified properties that are missing them."""
    c = conn.cursor()
    result = {
        "verified_total": 0,
        "missing_chains": 0,
        "to_generate": 0,
        "chains_to_insert": [],
        "errors": [],
    }

    # Get verified properties without chains
    c.execute("""
        SELECT id, collection_method, property_type, province_city, district,
               area_m2, price, collected_by, collected_at, evidence_tier
        FROM properties
        WHERE verification_status = "verified"
        AND id NOT IN (SELECT DISTINCT property_id FROM provenance_chains)
    """)
    missing = [dict(r) for r in c.fetchall()]
    result["verified_total"] = c.execute(
        'SELECT COUNT(*) FROM properties WHERE verification_status = "verified"'
    ).fetchone()[0]
    result["missing_chains"] = len(missing)

    for prop in missing:
        # Determine the correct step type and source
        method = prop["collection_method"] or "manual_entry"

        if method == "field_survey":
            step = "COLLECTED"
            actor = prop["collected_by"] or "field_agent"
            source = f"field_survey:{prop['id']}"
        elif method == "smartphone_sensor_capture":
            step = "COLLECTED"
            actor = "smartphone_sensor"
            source = f"smartphone:{prop['id']}"
        elif method == "manual_entry":
            step = "COLLECTED"
            actor = prop["collected_by"] or "manual_entry"
            source = f"manual_entry:{prop['id']}"
        else:
            step = "imported"
            actor = "data_team"
            source = f"import:{prop['id']}"

        # Compute input hash from property fields
        input_data = {
            "id": prop["id"],
            "area_m2": prop["area_m2"],
            "price": prop["price"],
            "province_city": prop["province_city"],
            "district": prop["district"],
            "property_type": prop["property_type"],
            "collection_method": method,
        }
        input_hash = compute_hash(input_data)
        output_hash = compute_hash({
            **input_data,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "evidence_tier": prop["evidence_tier"],
        })

        chain_record = {
            "property_id": prop["id"],
            "step": step,
            "actor": actor,
            "source": source,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": json.dumps({
                "collection_method": method,
                "evidence_tier": prop["evidence_tier"],
                "verified": True,
                "collected_at": prop["collected_at"],
                "script": "fix_self_collected_fields.py",
            }, ensure_ascii=False),
        }
        result["chains_to_insert"].append(chain_record)

    result["to_generate"] = len(result["chains_to_insert"])

    if not dry_run and result["to_generate"] > 0:
        c.executemany("""
            INSERT INTO provenance_chains
                (property_id, step, actor, source, input_hash, output_hash, timestamp, metadata_json)
            VALUES
                (:property_id, :step, :actor, :source, :input_hash, :output_hash, :timestamp, :metadata)
        """, result["chains_to_insert"])
        conn.commit()

    return result


def fix_field_mappings(conn: sqlite3.Connection, dry_run: bool = True) -> dict:
    """Check and fix swapped collection_method / collected_by fields."""
    c = conn.cursor()
    result = {
        "total_checked": 0,
        "swapped_found": 0,
        "fixed": 0,
        "issues": [],
    }

    # Look for records where collected_by contains a collection_method-like value
    # and collection_method contains a person-like value
    suspicious_methods = {"field_survey", "smartphone_sensor_capture", "manual_entry",
                         "public_scraped", "playwright_stealth", "batch_generator"}
    suspicious_by = {"admin", "system", "scraper", "system:Scraper"}

    c.execute("""
        SELECT id, collection_method, collected_by
        FROM properties
        WHERE collection_method IN ('field_survey', 'smartphone_sensor_capture', 'manual_entry')
        AND collected_by IS NOT NULL
    """)
    rows = [dict(r) for r in c.fetchall()]
    result["total_checked"] = len(rows)

    swaps_needed = []
    for r in rows:
        # If collected_by looks like a method name and collection_method looks like a name
        if r["collected_by"] in suspicious_methods and r["collection_method"] not in suspicious_methods:
            swaps_needed.append({
                "id": r["id"],
                "current_method": r["collection_method"],
                "current_by": r["collected_by"],
                "swap_method": r["collected_by"],
                "swap_by": r["collection_method"],
            })
            result["swapped_found"] += 1

    if swaps_needed:
        result["issues"].append(
            f"  Found {result['swapped_found']} records with swapped collection_method/collected_by"
        )
        for swap in swaps_needed[:5]:
            result["issues"].append(
                f"    Property {swap['id']}: "
                f"method='{swap['current_method']}' by='{swap['current_by']}' "
                f"→ method='{swap['swap_method']}' by='{swap['swap_by']}'"
            )

        if not dry_run:
            c.executemany("""
                UPDATE properties
                SET collection_method = :swap_method, collected_by = :swap_by
                WHERE id = :id
            """, swaps_needed)
            conn.commit()
            result["fixed"] = len(swaps_needed)

    return result


def main():
    parser = argparse.ArgumentParser(description="Fix self-collected property fields and provenance")
    parser.add_argument(
        "--apply", action="store_true",
        help="Apply fixes (default is dry-run)"
    )
    parser.add_argument(
        "--db-path", default=None,
        help="Path to SQLite database (default: project root)"
    )
    args = parser.parse_args()

    dry_run = not args.apply

    if args.db_path:
        db_path = os.path.normpath(args.db_path)
    else:
        db_path = os.path.normpath(DB_PATH)

    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        sys.exit(1)

    mode = "DRY-RUN" if dry_run else "APPLYING"
    print(f"\n{'='*60}")
    print(f"  FIX SELF-COLLECTED FIELDS — {mode}")
    print(f"{'='*60}")
    print(f"  Database: {db_path}\n")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Check 1: Generate provenance for verified
    print("[1/2] Generating provenance chains for verified properties...")
    prov_result = generate_provenance_for_verified(conn, dry_run=dry_run)
    print(f"      Verified total:   {prov_result['verified_total']}")
    print(f"      Missing chains:   {prov_result['missing_chains']}")
    print(f"      Chains to insert: {prov_result['to_generate']}")

    if prov_result["errors"]:
        for err in prov_result["errors"]:
            print(f"      ERROR: {err}")

    if dry_run:
        print(f"\n      (Would insert {prov_result['to_generate']} provenance chains)")
        print(f"      Sample chain:")
        if prov_result["chains_to_insert"]:
            c0 = prov_result["chains_to_insert"][0]
            print(f"        property_id: {c0['property_id']}")
            print(f"        step:        {c0['step']}")
            print(f"        actor:       {c0['actor']}")
            print(f"        input_hash:  {c0['input_hash'][:32]}...")
            print(f"        output_hash: {c0['output_hash'][:32]}...")

    # Check 2: Field mapping
    print(f"\n[2/2] Checking field mappings...")
    field_result = fix_field_mappings(conn, dry_run=dry_run)
    print(f"      Total self-collected checked: {field_result['total_checked']}")
    print(f"      Swapped fields found:         {field_result['swapped_found']}")
    if field_result["fixed"] > 0:
        print(f"      Fixed:                      {field_result['fixed']}")
    for issue in field_result["issues"]:
        print(f"      {issue}")

    conn.close()

    print(f"\n{'='*60}")
    if dry_run:
        print("  Mode: DRY-RUN — no changes applied")
        print("  Run with --apply to apply fixes")
    else:
        print("  COMPLETE — changes applied")
    print(f"{'='*60}\n")

    if prov_result["to_generate"] > 0 and dry_run:
        print(f"NOTE: Run with --apply to generate {prov_result['to_generate']} provenance chains")
        print(f"      for verified properties.")


if __name__ == "__main__":
    main()
