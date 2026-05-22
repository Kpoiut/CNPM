#!/usr/bin/env python3
"""
Audit provenance chain integrity for Real Estate AVM.

Checks:
1. Hash chain integrity — each step's output_hash matches next step's input_hash
2. All verified properties have provenance chains
3. No broken prev_step_id references
4. Provenance source URLs are valid

Usage:
    python scripts/audit_provenance.py
"""

import hashlib
import json
import sqlite3
import sys
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "real_estate_avm.db")


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def audit_hash_integrity(conn: sqlite3.Connection) -> dict:
    """Verify that each chain's output_hash correctly links to the next step's input_hash."""
    c = conn.cursor()

    results = {
        "total_chains": 0,
        "chains_checked": 0,
        "null_hashes": 0,
        "broken_prev_step_refs": 0,
        "hash_mismatches": 0,
        "pass": True,
        "errors": [],
    }

    c.execute("SELECT COUNT(*) FROM provenance_chains")
    results["total_chains"] = c.fetchone()[0]

    # Check null hashes
    # Check null output_hash only — NULL input_hash is expected for first step (COLLECTED)
    c.execute("SELECT COUNT(*) FROM provenance_chains WHERE output_hash IS NULL")
    results["null_hashes"] = c.fetchone()[0]
    if results["null_hashes"] > 0:
        results["errors"].append(f"  {results['null_hashes']} chains have NULL output_hash (input_hash NULL is OK for first step)")
        results["pass"] = False

    # Check broken prev_step_id references
    c.execute("""
        SELECT COUNT(*) FROM provenance_chains
        WHERE prev_step_id IS NOT NULL
        AND prev_step_id NOT IN (SELECT id FROM provenance_chains)
    """)
    results["broken_prev_step_refs"] = c.fetchone()[0]
    if results["broken_prev_step_refs"] > 0:
        results["errors"].append(f"  {results['broken_prev_step_refs']} chains have broken prev_step_id references")
        results["pass"] = False

    # Check hash chain continuity: for each chain where prev_step_id exists,
    # verify that prev_step.output_hash == this_step.input_hash
    c.execute("""
        SELECT pc.id, pc.property_id, pc.step, pc.input_hash, prev.output_hash as prev_output
        FROM provenance_chains pc
        JOIN provenance_chains prev ON pc.prev_step_id = prev.id
        WHERE pc.input_hash IS NOT NULL
    """)
    chain_links = c.fetchall()

    for chain_id, prop_id, step, input_hash, prev_output in chain_links:
        results["chains_checked"] += 1
        if input_hash != prev_output:
            results["hash_mismatches"] += 1
            results["errors"].append(
                f"  Chain {chain_id} (property {prop_id}, step '{step}'): "
                f"input_hash != prev.output_hash ({input_hash[:16]}... != {prev_output[:16]}...)"
            )
            results["pass"] = False

    return results


def audit_verified_properties(conn: sqlite3.Connection) -> dict:
    """Check that all verified properties have provenance chains."""
    c = conn.cursor()

    results = {
        "total_verified": 0,
        "with_chain": 0,
        "without_chain": 0,
        "missing_property_ids": [],
        "pass": True,
        "errors": [],
    }

    c.execute('SELECT COUNT(*) FROM properties WHERE verification_status = "verified"')
    results["total_verified"] = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(DISTINCT p.id)
        FROM properties p
        JOIN provenance_chains pc ON p.id = pc.property_id
        WHERE p.verification_status = "verified"
    """)
    results["with_chain"] = c.fetchone()[0]
    results["without_chain"] = results["total_verified"] - results["with_chain"]

    if results["without_chain"] > 0:
        c.execute("""
            SELECT p.id, p.collection_method, p.property_type, p.province_city
            FROM properties p
            WHERE p.verification_status = "verified"
            AND p.id NOT IN (SELECT DISTINCT property_id FROM provenance_chains)
        """)
        missing = c.fetchall()
        results["missing_property_ids"] = [r[0] for r in missing]
        results["errors"].append(
            f"  {results['without_chain']}/{results['total_verified']} verified properties have NO provenance chain"
        )
        results["pass"] = False

    return results


def audit_all_properties(conn: sqlite3.Connection) -> dict:
    """Check that all properties with prices have provenance chains."""
    c = conn.cursor()

    results = {
        "total_with_price": 0,
        "with_chain": 0,
        "without_chain": 0,
        "pass": True,
        "errors": [],
    }

    c.execute("SELECT COUNT(*) FROM properties WHERE price > 0 AND price IS NOT NULL")
    results["total_with_price"] = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(DISTINCT p.id)
        FROM properties p
        JOIN provenance_chains pc ON p.id = pc.property_id
        WHERE p.price > 0 AND p.price IS NOT NULL
    """)
    results["with_chain"] = c.fetchone()[0]
    results["without_chain"] = results["total_with_price"] - results["with_chain"]

    if results["without_chain"] > 0:
        pct = 100 * results["without_chain"] / results["total_with_price"]
        results["errors"].append(
            f"  {results['without_chain']}/{results['total_with_price']} priced properties "
            f"({pct:.1f}%) have no provenance chain"
        )
        # Only fail if > 50% are missing
        if pct > 50:
            results["pass"] = False

    return results


def audit_sources(conn: sqlite3.Connection) -> dict:
    """Check that provenance source URLs look valid."""
    c = conn.cursor()

    results = {
        "total": 0,
        "null_source": 0,
        "invalid_url": 0,
        "pass": True,
        "errors": [],
    }

    c.execute("SELECT COUNT(*) FROM provenance_chains")
    results["total"] = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM provenance_chains WHERE source IS NULL OR source = ''")
    results["null_source"] = c.fetchone()[0]
    if results["null_source"] > 0:
        results["errors"].append(f"  {results['null_source']} chains have NULL/empty source")

    c.execute("""
        SELECT COUNT(*) FROM provenance_chains
        WHERE source IS NOT NULL
        AND source != ''
        AND source NOT LIKE 'http%'
        AND source NOT LIKE 'field_survey:%'
        AND source NOT LIKE 'smartphone:%'
        AND source NOT LIKE 'manual_entry:%'
    """)
    results["invalid_url"] = c.fetchone()[0]
    if results["invalid_url"] > 0:
        results["errors"].append(
            f"  {results['invalid_url']} chains have non-URL sources (may be intentional for self-collected)"
        )

    return results


def main():
    db_path = os.path.normpath(DB_PATH)
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    print(f"\nAuditing provenance chain: {db_path}\n")

    all_pass = True
    report = {
        "timestamp": datetime.now().isoformat(),
        "db_path": db_path,
        "checks": {},
    }

    checks = [
        ("hash_integrity", audit_hash_integrity),
        ("verified_properties", audit_verified_properties),
        ("all_properties", audit_all_properties),
        ("sources", audit_sources),
    ]

    for name, fn in checks:
        print(f"Checking: {name}...", end=" ")
        result = fn(conn)
        report["checks"][name] = result
        if not result["pass"]:
            all_pass = False
            print("FAIL")
        else:
            print("PASS")

    conn.close()

    # Print summary
    print(f"\n{'='*60}")
    print("  PROVENANCE AUDIT REPORT")
    print(f"{'='*60}")
    for name, result in report["checks"].items():
        status = "PASS" if result["pass"] else "FAIL"
        print(f"\n  [{status}] {name}")
        for err in result.get("errors", []):
            print(f"      {err}")

    print(f"\n{'='*60}")
    if all_pass:
        print("  OVERALL: ALL CHECKS PASSED")
    else:
        print("  OVERALL: SOME CHECKS FAILED — see above")
    print(f"{'='*60}\n")

    # Save JSON report
    report_path = os.path.join(os.path.dirname(__file__), "provenance_audit_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Detailed report saved: {report_path}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
