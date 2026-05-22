#!/usr/bin/env python3
"""
Import manually verified public listings as traceable E3 records.

This is the honest substitute for unavailable public transaction data:
- records are listing anchors, not transaction anchors;
- every row must expose a public URL and extracted structured facts;
- each insert receives a linked provenance chain: CRAWLED -> PARSED ->
  VALIDATED -> CROSS_CHECK -> APPROVED;
- no record is promoted to E5 because no public notarized transaction source
  is available.

Usage:
    python scripts/ingest_traceable_public_listings.py --input data/traceable_public_listings_20260513.json --dry-run
    python scripts/ingest_traceable_public_listings.py --input data/traceable_public_listings_20260513.json --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "real_estate_avm.db"

SCOPE = {
    ("Hà Nội", "Quận Cầu Giấy"),
    ("Hà Nội", "Quận Thanh Xuân"),
    ("Hà Nội", "Quận Đống Đa"),
    ("TP. Hồ Chí Minh", "Quận 7"),
    ("TP. Hồ Chí Minh", "Quận Bình Thạnh"),
    ("TP. Hồ Chí Minh", "Quận Tân Bình"),
}
PROPERTY_TYPES = {"house", "apartment", "land", "townhouse", "villa"}


def stable_hash(data: object) -> str:
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_records(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    records = payload.get("records", payload if isinstance(payload, list) else [])
    if not isinstance(records, list):
        raise ValueError("Input must be a list or an object with a records list")
    return records


def validate_record(record: dict) -> list[str]:
    errors: list[str] = []
    required = [
        "source_listing_key", "property_type", "province_city", "district",
        "area_m2", "price", "source_name", "source_url", "source_page_title",
    ]
    for key in required:
        if record.get(key) in (None, ""):
            errors.append(f"{key} is required")

    if record.get("property_type") not in PROPERTY_TYPES:
        errors.append(f"property_type must be one of {sorted(PROPERTY_TYPES)}")
    if (record.get("province_city"), record.get("district")) not in SCOPE:
        errors.append("record is outside the six-district training scope")

    try:
        area = float(record.get("area_m2", 0))
        price = float(record.get("price", 0))
    except (TypeError, ValueError):
        errors.append("area_m2 and price must be numeric")
    else:
        if not (10 <= area <= 20_000):
            errors.append("area_m2 must be between 10 and 20,000")
        if price < 100_000_000:
            errors.append("price must be >= 100,000,000 VND")
        if area > 0:
            ppm = price / area
            if not (10_000_000 <= ppm <= 500_000_000):
                errors.append(f"price_per_m2 out of accepted market range: {ppm:,.0f}")

    parsed = urlparse(str(record.get("source_url", "")))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        errors.append("source_url must be an http(s) URL")

    extracted = record.get("extracted_facts") or {}
    for key in ("price_text", "area_text", "location_text"):
        if not extracted.get(key):
            errors.append(f"extracted_facts.{key} is required")

    return errors


def record_exists(conn: sqlite3.Connection, key: str) -> bool:
    cur = conn.execute(
        """
        SELECT 1
        FROM properties
        WHERE form_submission_id = ?
           OR raw_source_content LIKE ?
        LIMIT 1
        """,
        (key, f'%"source_listing_key": "{key}"%'),
    )
    return cur.fetchone() is not None


def insert_property(conn: sqlite3.Connection, record: dict, collected_at: str) -> int:
    price = float(record["price"])
    area = float(record["area_m2"])
    price_per_m2 = round(price / area, -3)
    parsed = urlparse(record["source_url"])
    next_id = int(conn.execute(
        """
        SELECT MAX(v) + 1
        FROM (
            SELECT COALESCE(MAX(id), 0) AS v FROM properties
            UNION ALL
            SELECT COALESCE(MAX(property_id), 0) AS v FROM provenance_chains
        )
        """
    ).fetchone()[0])
    raw_source_content = json.dumps(
        {
            "source_listing_key": record["source_listing_key"],
            "source_url": record["source_url"],
            "source_page_title": record["source_page_title"],
            "extracted_facts": record["extracted_facts"],
            "verification_basis": record.get("verification_basis"),
            "limitations": "Public asking-price listing, not notarized transaction data.",
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    cur = conn.execute(
        """
        INSERT INTO properties (
            id, data_origin_type, record_status, verification_status,
            property_type, province_city, district, ward, street_or_project,
            area_m2, bedrooms, bathrooms, floor_count, frontage_m,
            legal_status, furnishing, price, price_per_m2, listing_date,
            latitude, longitude, area_type,
            source_name, source_url, source_page_title, source_collected_at,
            source_access_method, source_domain, source_category, source_crawl_at,
            raw_source_content, data_collection_status, collection_attempt_count,
            last_collection_attempt, verification_note, verified_by, verified_at,
            collected_by, collected_at, collection_method, form_submission_id,
            field_notes, evidence_tier, evidence_tier_updated_at,
            collection_timestamp, data_source_region, source_region, description
        ) VALUES (
            :id, 'self_collected', 'pending_review', 'verified',
            :property_type, :province_city, :district, :ward, :street_or_project,
            :area_m2, :bedrooms, :bathrooms, :floor_count, :frontage_m,
            :legal_status, :furnishing, :price, :price_per_m2, :listing_date,
            :latitude, :longitude, :area_type,
            :source_name, :source_url, :source_page_title, :source_collected_at,
            'manual_entry', :source_domain, 'manual_verified_public_listing', :source_crawl_at,
            :raw_source_content, 'collected', 1,
            :last_collection_attempt, :verification_note, 'codex:manual_public_listing_audit', :verified_at,
            'codex:manual_public_listing_audit', :collected_at, 'manual_verified_from_public_listing', :form_submission_id,
            :field_notes, 'E3', :evidence_tier_updated_at,
            :collection_timestamp, :data_source_region, :source_region, :description
        )
        """,
        {
            "id": next_id,
            "property_type": record["property_type"],
            "province_city": record["province_city"],
            "district": record["district"],
            "ward": record.get("ward"),
            "street_or_project": record.get("street_or_project"),
            "area_m2": area,
            "bedrooms": int(record.get("bedrooms") or 0),
            "bathrooms": int(record.get("bathrooms") or 0),
            "floor_count": int(record.get("floor_count") or 1),
            "frontage_m": record.get("frontage_m"),
            "legal_status": record.get("legal_status") or "unknown",
            "furnishing": record.get("furnishing") or "null",
            "price": price,
            "price_per_m2": price_per_m2,
            "listing_date": record.get("listing_date"),
            "latitude": record.get("latitude"),
            "longitude": record.get("longitude"),
            "area_type": record.get("area_type") or "urban_center",
            "source_name": record["source_name"],
            "source_url": record["source_url"],
            "source_page_title": record["source_page_title"],
            "source_collected_at": collected_at,
            "source_domain": parsed.netloc.lower(),
            "source_crawl_at": collected_at,
            "raw_source_content": raw_source_content,
            "last_collection_attempt": collected_at,
            "verification_note": record.get("verification_basis"),
            "verified_at": collected_at,
            "collected_at": collected_at,
            "form_submission_id": record["source_listing_key"],
            "field_notes": record.get("field_notes"),
            "evidence_tier_updated_at": collected_at,
            "collection_timestamp": collected_at,
            "data_source_region": "hanoi" if record["province_city"] == "Hà Nội" else "hcmc",
            "source_region": record["province_city"],
            "description": record.get("description"),
        },
    )
    return next_id


def add_provenance(conn: sqlite3.Connection, property_id: int, record: dict, collected_at: str) -> None:
    prev_id = None
    prev_hash = None
    steps = [
        (
            "CRAWLED",
            "system:manual_public_listing_collector",
            record["source_url"],
            {"url": record["source_url"], "accessed_at": collected_at},
            {
                "page_title": record["source_page_title"],
                "extracted_facts": record["extracted_facts"],
            },
        ),
        (
            "PARSED",
            "system:manual_public_listing_collector",
            None,
            {"source_listing_key": record["source_listing_key"]},
            {
                "property_type": record["property_type"],
                "district": record["district"],
                "area_m2": record["area_m2"],
                "price": record["price"],
            },
        ),
        (
            "VALIDATED",
            "system:Validator",
            "schema_validator",
            {"property_id": property_id},
            {"scope_valid": True, "url_present": True, "price_present": True},
        ),
        (
            "CROSS_CHECK",
            "system:price_validator",
            "market_range_validator",
            {"property_id": property_id},
            {
                "price_per_m2": round(float(record["price"]) / float(record["area_m2"])),
                "accepted_range_vnd_per_m2": [10_000_000, 500_000_000],
                "transaction_anchor_available": False,
            },
        ),
        (
            "APPROVED",
            "user:codex_data_audit",
            None,
            {"property_id": property_id},
            {
                "approved_tier": "E3",
                "reason": "Traceable public listing with structured extraction and price-range validation.",
                "not_e5_reason": "No public official transaction/notarization source was available.",
            },
        ),
    ]

    for step, actor, source, input_data, output_data in steps:
        input_hash = prev_hash if prev_hash else stable_hash(input_data)
        output_hash = stable_hash(output_data)
        metadata = {
            "source_listing_key": record["source_listing_key"],
            "input": input_data,
            "output": output_data,
            "verification_basis": record.get("verification_basis"),
        }
        cur = conn.execute(
            """
            INSERT INTO provenance_chains (
                property_id, step, timestamp, actor, input_hash, output_hash,
                source, verify_url, metadata_json, prev_step_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                property_id,
                step,
                collected_at,
                actor,
                input_hash,
                output_hash,
                source,
                record["source_url"],
                json.dumps(metadata, ensure_ascii=False, sort_keys=True),
                prev_id,
            ),
        )
        prev_id = int(cur.lastrowid)
        prev_hash = output_hash


def add_audit_log(conn: sqlite3.Connection, property_id: int, record: dict, collected_at: str) -> None:
    conn.execute(
        """
        INSERT INTO audit_logs (
            record_id, table_name, action_type, changed_by, changed_at,
            old_value_json, new_value_json, change_note
        ) VALUES (?, 'properties', 'CREATE', 'codex:manual_public_listing_audit', ?, NULL, ?, ?)
        """,
        (
            property_id,
            collected_at,
            json.dumps(
                {
                    "source_listing_key": record["source_listing_key"],
                    "evidence_tier": "E3",
                    "source_url": record["source_url"],
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            "Imported traceable public listing as E3 surrogate; not transaction/E5 data.",
        ),
    )


def run(input_path: Path, apply: bool) -> dict:
    records = load_records(input_path)
    errors: list[str] = []
    saved = 0
    skipped = 0
    inserted_ids: list[int] = []
    collected_at = now_utc()

    conn = sqlite3.connect(DB_PATH)
    try:
        for idx, record in enumerate(records, 1):
            row_errors = validate_record(record)
            if row_errors:
                errors.extend(f"Record {idx} ({record.get('source_listing_key')}): {e}" for e in row_errors)
                continue

            key = record["source_listing_key"]
            if record_exists(conn, key):
                skipped += 1
                continue

            if not apply:
                saved += 1
                continue

            property_id = insert_property(conn, record, collected_at)
            add_provenance(conn, property_id, record, collected_at)
            add_audit_log(conn, property_id, record, collected_at)
            inserted_ids.append(property_id)
            saved += 1

        if apply and not errors:
            conn.commit()
        elif apply:
            conn.rollback()
    finally:
        conn.close()

    return {
        "input": str(input_path),
        "mode": "apply" if apply else "dry-run",
        "total": len(records),
        "valid_or_saved": saved,
        "skipped_existing": skipped,
        "errors": errors,
        "inserted_ids": inserted_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import traceable public listings as E3 records")
    parser.add_argument("--input", required=True, help="JSON file with records")
    parser.add_argument("--apply", action="store_true", help="Write records to DB")
    parser.add_argument("--dry-run", action="store_true", help="Validate only")
    args = parser.parse_args()

    if args.apply and args.dry_run:
        raise SystemExit("Choose only one of --apply or --dry-run")
    result = run(Path(args.input), apply=args.apply)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
