#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
Database Cleanup Script - Real Estate AVM
Xoa du lieu gia, trung lap, khong co nguon goc, ngoai scope.

Usage:
    python scripts/cleanup_database.py --dry-run    # Xem report truoc
    python scripts/cleanup_database.py --apply      # Thuc hien xoa
    python scripts/cleanup_database.py --stats      # Chi hien thi thong ke
"""
import argparse
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config.province_config import SCOPE_DISTRICTS

DB_PATH = PROJECT_ROOT / "real_estate_avm.db"
REPORT_DIR = PROJECT_ROOT / "data"


# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
SCOPE_DISTRICT_SET = set()
for districts in SCOPE_DISTRICTS.values():
    for d in districts:
        SCOPE_DISTRICT_SET.add(d)
SCOPE_DISTRICT_SET.add("Quận Cầu Giấy")  # alias variants
SCOPE_DISTRICT_SET.add("Quận Thanh Xuân")
SCOPE_DISTRICT_SET.add("Quận Đống Đa")
SCOPE_DISTRICT_SET.add("Quận 7")
SCOPE_DISTRICT_SET.add("Quận Bình Thạnh")
SCOPE_DISTRICT_SET.add("Quận Tân Bình")

# Market ceiling: 120M/m² for Vietnam urban apartment/house market (Q1/2026)
PPM_MAX = 120_000_000
# Floor: minimum viable price for urban property
PRICE_MIN = 200_000_000
# Area limits
AREA_MIN = 15.0
AREA_MAX = 1000.0
# IQR multiplier for outlier detection
IQR_K = 3.0


# -----------------------------------------------------------------------------
# DATABASE HELPERS
# -----------------------------------------------------------------------------
def get_conn():
    return sqlite3.connect(str(DB_PATH))


def load_all_props(conn: sqlite3.Connection) -> List[Dict]:
    """Load all non-archived properties as dicts."""
    c = conn.cursor()
    c.execute("""
        SELECT id, property_type, province_city, district, ward,
               area_m2, bedrooms, bathrooms, floor_count,
               price, price_per_m2, listing_date,
               legal_status, furnishing,
               latitude, longitude, data_origin_type,
               evidence_tier, source_name, source_url,
               collection_method, source_access_method,
               verification_status, record_status
        FROM properties
        WHERE record_status != 'archived'
    """)
    cols = [desc[0] for desc in c.description]
    rows = c.fetchall()
    return [dict(zip(cols, r)) for r in rows]


# -----------------------------------------------------------------------------
# CLEANUP RULES
# -----------------------------------------------------------------------------
def rule_r1_ppm_too_high(props: List[Dict]) -> List[int]:
    """R1: Price-per-m² vượt market ceiling (> 120M/m²)."""
    return [p["id"] for p in props if p["price_per_m2"] and p["price_per_m2"] > PPM_MAX]


def rule_r2_iqr_outlier(props: List[Dict]) -> List[int]:
    """R2: IQR outlier (k=3) per (district, property_type) cluster."""
    import statistics
    ids = []
    clusters: Dict[Tuple, List[float]] = {}
    for p in props:
        if p["price_per_m2"] is None:
            continue
        key = (p["district"], p["property_type"])
        clusters.setdefault(key, []).append(p["price_per_m2"])

    for key, vals in clusters.items():
        if len(vals) < 4:
            continue
        vals_sorted = sorted(vals)
        n = len(vals_sorted)
        q1 = vals_sorted[n // 4]
        q3 = vals_sorted[3 * n // 4]
        iqr = q3 - q1
        upper = q3 + IQR_K * iqr
        for p in props:
            if (p["district"], p["property_type"]) == key and p["price_per_m2"] and p["price_per_m2"] > upper:
                ids.append(p["id"])
    return list(dict.fromkeys(ids))  # deduplicate


def rule_r3_no_provenance(props: List[Dict]) -> List[int]:
    """R3: No source_name AND no source_url AND no collection_method."""
    return [
        p["id"] for p in props
        if (not p.get("source_name") or p["source_name"].strip() == "")
        and (not p.get("source_url") or p["source_url"].strip() == "")
        and (not p.get("collection_method") or p["collection_method"].strip() == "")
    ]


def rule_r4_outside_scope(props: List[Dict]) -> List[int]:
    """R4: District not in 6-scope list."""
    return [p["id"] for p in props if p["district"] not in SCOPE_DISTRICT_SET]


def rule_r5_batch_fingerprint(props: List[Dict]) -> List[int]:
    """R5: Batch-generated records (many same listing_date + source)."""
    from collections import defaultdict
    date_source_groups: Dict[Tuple, List[int]] = defaultdict(list)
    for p in props:
        if p["listing_date"]:
            key = (str(p["listing_date"]), p.get("source_name", ""))
            date_source_groups[key].append(p["id"])

    ids = []
    for (date, src), pid_list in date_source_groups.items():
        if len(pid_list) > 20:
            ids.extend(pid_list)
    return ids


def rule_r6_duplicates(props: List[Dict]) -> List[int]:
    """R6: Duplicate (area_m2, price, district, property_type) - keep 1."""
    from collections import defaultdict
    groups: Dict[Tuple, List[int]] = defaultdict(list)
    for p in props:
        if p["area_m2"] and p["price"] and p["district"] and p["property_type"]:
            key = (round(p["area_m2"], 1), round(p["price"], -6), p["district"], p["property_type"])
            groups[key].append(p["id"])

    ids = []
    for key, pid_list in groups.items():
        if len(pid_list) > 1:
            ids.extend(pid_list[1:])  # keep first, remove rest
    return ids


def rule_r7_e5_suspicious(props: List[Dict]) -> List[int]:
    """R7: E5 tier + high ppm (>= 80M/m²) = suspicious."""
    return [
        p["id"] for p in props
        if p.get("evidence_tier") == "E5"
        and p.get("price_per_m2") and p["price_per_m2"] >= 80_000_000
    ]


def rule_r8_system_demo(props: List[Dict]) -> List[int]:
    """R8: system_demo seeded records."""
    return [p["id"] for p in props if p.get("data_origin_type") == "system_demo"]


def rule_r9_unverifiable_cheap_high_ppm(props: List[Dict]) -> List[int]:
    """R9: Unverified + price < 500M + ppm > 50M = suspicious."""
    return [
        p["id"] for p in props
        if p.get("verification_status") in ("unverified", None, "")
        and p.get("price") and p["price"] < 500_000_000
        and p.get("price_per_m2") and p["price_per_m2"] > 50_000_000
        and p.get("evidence_tier") in ("E4", "E5", None, "")
    ]


def rule_r10_price_too_low(props: List[Dict]) -> List[int]:
    """R10: Total price < 200M VND - impossible for urban property."""
    return [p["id"] for p in props if p.get("price") and p["price"] < PRICE_MIN]


# -----------------------------------------------------------------------------
# ANALYSIS & REPORT
# -----------------------------------------------------------------------------
def analyze(props: List[Dict]) -> Dict:
    """Run all rules, return analysis report."""
    rules = {
        "R1_ppm_too_high": rule_r1_ppm_too_high,
        "R2_iqr_outlier": rule_r2_iqr_outlier,
        "R3_no_provenance": rule_r3_no_provenance,
        "R4_outside_scope": rule_r4_outside_scope,
        "R5_batch_fingerprint": rule_r5_batch_fingerprint,
        "R6_duplicates": rule_r6_duplicates,
        "R7_e5_suspicious": rule_r7_e5_suspicious,
        "R8_system_demo": rule_r8_system_demo,
        "R9_unverifiable_cheap_high_ppm": rule_r9_unverifiable_cheap_high_ppm,
        "R10_price_too_low": rule_r10_price_too_low,
    }

    rule_results = {}
    for name, fn in rules.items():
        ids = fn(props)
        rule_results[name] = sorted(set(ids))

    # Merge overlapping IDs
    all_delete_ids: set = set()
    for ids in rule_results.values():
        all_delete_ids.update(ids)

    # Per-record reason tracking
    record_reasons: Dict[int, List[str]] = {}
    for name, ids in rule_results.items():
        for pid in ids:
            record_reasons.setdefault(pid, []).append(name)

    # Stats
    ppm_bands = {"0-30M": 0, "30-50M": 0, "50-80M": 0, "80-120M": 0, "120-300M": 0, "300M+": 0}
    for p in props:
        if p["price_per_m2"] is None:
            continue
        ppm = p["price_per_m2"]
        if ppm < 30_000_000:
            ppm_bands["0-30M"] += 1
        elif ppm < 50_000_000:
            ppm_bands["30-50M"] += 1
        elif ppm < 80_000_000:
            ppm_bands["50-80M"] += 1
        elif ppm < 120_000_000:
            ppm_bands["80-120M"] += 1
        elif ppm < 300_000_000:
            ppm_bands["120-300M"] += 1
        else:
            ppm_bands["300M+"] += 1

    district_counts = {}
    for p in props:
        if p["district"]:
            district_counts[p["district"]] = district_counts.get(p["district"], 0) + 1

    return {
        "total_records": len(props),
        "records_to_delete": len(all_delete_ids),
        "records_to_keep": len(props) - len(all_delete_ids),
        "rule_results": {k: len(v) for k, v in rule_results.items()},
        "rule_detail": {k: v for k, v in rule_results.items()},
        "record_reasons": {str(k): v for k, v in record_reasons.items()},
        "ppm_distribution": ppm_bands,
        "district_counts": district_counts,
    }


def safe(s: str) -> str:
    """Encode to ASCII with replacement for Vietnamese chars."""
    return s.encode("ascii", errors="replace").decode("ascii")


def print_report(report: Dict):
    print("\n" + "=" * 70)
    print("DATABASE CLEANUP REPORT")
    print(f"Generated: {datetime.now().isoformat()}")
    print("=" * 70)

    print(f"\nTotal non-archived records: {report['total_records']}")
    print(f"Records to DELETE:           {report['records_to_delete']}")
    print(f"Records to KEEP:             {report['records_to_keep']}")

    print("\n--- DELETE COUNT BY RULE ---")
    for rule, count in report["rule_results"].items():
        pct = count / report["total_records"] * 100
        bar = "*" * min(int(pct / 2), 50)
        print(f"  {rule}: {count:5d} ({pct:5.1f}%) {bar}")

    print("\n--- PPM DISTRIBUTION (current) ---")
    for band, count in report["ppm_distribution"].items():
        pct = count / report["total_records"] * 100
        bar = "*" * min(int(pct / 2), 50)
        print(f"  {band:12s}: {count:5d} ({pct:5.1f}%) {bar}")

    print("\n--- DISTRICT DISTRIBUTION (current) ---")
    for dist, count in sorted(report["district_counts"].items(), key=lambda x: -x[1]):
        pct = count / report["total_records"] * 100
        print(f"  {safe(dist):25s}: {count:5d} ({pct:5.1f}%)")

    # Show sample records that will be deleted
    print("\n--- SAMPLE RECORDS TO BE DELETED (ppm > 300M/m²) ---")
    deleted_ppm = report["rule_detail"].get("R1_ppm_too_high", [])
    sample = [int(k) for k in list(report["record_reasons"].keys())[:10] if int(k) in deleted_ppm][:10]
    print(f"  (Showing up to 10, total R1 hits: {len(deleted_ppm)})")


# -----------------------------------------------------------------------------
# APPLY CLEANUP
# -----------------------------------------------------------------------------
def apply_cleanup(report: Dict, conn: sqlite3.Connection):
    """Delete all flagged records from DB, write audit logs."""
    all_ids = set()
    for ids in report["rule_detail"].values():
        all_ids.update(ids)

    deleted_reasons = report["record_reasons"]

    c = conn.cursor()
    audit_rows = []
    for pid in sorted(all_ids):
        reasons = deleted_reasons.get(str(pid), [])
        audit_rows.append((
            pid,
            "properties",
            "CLEANUP_DELETE",
            "system:cleanup",
            json.dumps({"cleanup_rules": reasons}),
            None,
            f"R1-R10 cleanup | Rules: {', '.join(reasons)}",
        ))

    # Bulk insert audit logs
    c.executemany(
        "INSERT INTO audit_logs (record_id, table_name, action_type, changed_by, old_value_json, new_value_json, change_note) VALUES (?, ?, ?, ?, ?, ?, ?)",
        audit_rows
    )

    # Delete properties
    c.execute(f"DELETE FROM properties WHERE id IN ({','.join('?' * len(all_ids))})", sorted(all_ids))
    deleted_count = c.rowcount

    # Delete orphaned provenance chains
    c.execute(f"DELETE FROM provenance_chains WHERE property_id IN ({','.join('?' * len(all_ids))})", sorted(all_ids))

    # Reset sequence
    c.execute("DELETE FROM sqlite_sequence WHERE name='properties'")

    conn.commit()

    print(f"\n[OK] Deleted {deleted_count} property records")
    print(f"[OK] Deleted orphaned provenance chains")
    print(f"[OK] Wrote {len(audit_rows)} audit log entries")

    return deleted_count


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Clean database - remove fake/suspicious data")
    parser.add_argument("--dry-run", action="store_true", help="Show report without deleting")
    parser.add_argument("--apply", action="store_true", help="Apply deletions")
    parser.add_argument("--stats", action="store_true", help="Show current DB stats only")
    args = parser.parse_args()

    if not args.dry_run and not args.apply and not args.stats:
        parser.print_help()
        return

    os.makedirs(REPORT_DIR, exist_ok=True)
    conn = get_conn()
    props = load_all_props(conn)

    report = analyze(props)
    print_report(report)

    # Save report to disk
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"cleanup_report_{ts}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nReport saved to: {report_path}")

    if args.stats:
        return

    if args.dry_run:
        print("\n[Dry run - no changes made]")
        return

    if args.apply:
        print(f"\n[WARN]  ABOUT TO DELETE {report['records_to_delete']} RECORDS")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.strip().lower() != "yes":
            print("Cancelled.")
            return

        deleted = apply_cleanup(report, conn)
        print(f"\n[OK] Cleanup complete. {deleted} records removed.")
        print(f"  Remaining records: {report['records_to_keep']}")

        # Show final stats
        conn.close()
        conn2 = get_conn()
        c = conn2.cursor()
        c.execute("SELECT COUNT(*) FROM properties WHERE record_status != 'archived'")
        print(f"  DB now has {c.fetchone()[0]} active records")

        # PPM distribution after cleanup
        c.execute("""
            SELECT
                CASE
                    WHEN price_per_m2 < 30000000 THEN '0-30M'
                    WHEN price_per_m2 < 50000000 THEN '30-50M'
                    WHEN price_per_m2 < 80000000 THEN '50-80M'
                    WHEN price_per_m2 < 120000000 THEN '80-120M'
                    WHEN price_per_m2 < 300000000 THEN '120-300M'
                    ELSE '300M+'
                END as band, COUNT(*) as cnt
            FROM properties WHERE record_status != 'archived'
            GROUP BY band
        """)
        print("\n  PPM DISTRIBUTION AFTER CLEANUP:")
        for row in c.fetchall():
            print(f"    {row[0]:12s}: {row[1]} records")
        conn2.close()


if __name__ == "__main__":
    main()
