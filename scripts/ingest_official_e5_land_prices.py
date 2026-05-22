#!/usr/bin/env python3
"""Ingest official land-price reference records.

These records are self-collected from official legal-document sources and are
stored as unit price references, not as market transactions. They are E4
reference-only records, not complete E5 auction/transaction evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "real_estate_avm.db"
DATA_PATH = PROJECT_ROOT / "data" / "official_e5_land_price_references_20260513.json"
REPORT_DIR = PROJECT_ROOT / "reports"

SCOPE_DISTRICTS = {
    "Quận Cầu Giấy",
    "Quận Thanh Xuân",
    "Quận Đống Đa",
    "Quận 7",
    "Quận Bình Thạnh",
    "Quận Tân Bình",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def max_property_id(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        """
        SELECT MAX(max_id) FROM (
            SELECT COALESCE(MAX(id), 0) AS max_id FROM properties
            UNION ALL
            SELECT COALESCE(MAX(property_id), 0) AS max_id FROM provenance_chains
        )
        """
    ).fetchone()
    return int(row[0] or 0)


def existing_submission_ids(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        """
        SELECT form_submission_id
        FROM properties
        WHERE form_submission_id LIKE 'official_e5_%'
        """
    ).fetchall()
    return {str(row[0]) for row in rows if row[0]}


def validate_record(record: dict[str, Any]) -> None:
    if record["district"] not in SCOPE_DISTRICTS:
        raise ValueError(f"Out-of-scope district: {record['district']}")
    if not str(record.get("official_source_url", "")).startswith("https://vbpl.vn/"):
        raise ValueError(f"Official source must be VBPL: {record['official_record_id']}")
    price = int(record["price_per_m2_vnd"])
    if not 5_000_000 <= price <= 500_000_000:
        raise ValueError(f"Price per m2 outside clean range: {record['official_record_id']}")
    if not record.get("not_market_transaction"):
        raise ValueError(f"Official reference must be marked non-transaction: {record['official_record_id']}")


def property_payload(prop_id: int, record: dict[str, Any], collected_at: str) -> dict[str, Any]:
    record_id = record["official_record_id"]
    source_url = f"{record['official_source_url']}#{record_id}"
    price_per_m2 = int(record["price_per_m2_vnd"])
    raw_source = {
        "record_type": "official_land_price_reference",
        "official_record_id": record_id,
        "official_document": record["official_document"],
        "official_source_url": record["official_source_url"],
        "structured_source_url": record["structured_source_url"],
        "source_page_or_section": record["source_page_or_section"],
        "effective_date": record["effective_date"],
        "province_city": record["province_city"],
        "district": record["district"],
        "street_or_project": record["street_or_project"],
        "segment_from": record["segment_from"],
        "segment_to": record["segment_to"],
        "land_use": record["land_use"],
        "position": record["position"],
        "source_unit": "1.000 VND/m2",
        "source_value_thousand_vnd_per_m2": record["source_value_thousand_vnd_per_m2"],
        "price_per_m2_vnd": price_per_m2,
        "not_market_transaction": True,
        "self_collection_basis": (
            "Collected and normalized by this project from an official legal document "
            "source with traceable URL and row-level metadata."
        ),
    }
    return {
        "id": prop_id,
        "data_origin_type": "self_collected",
        "record_status": "verified",
        "verification_status": "verified",
        "property_type": "land",
        "province_city": record["province_city"],
        "district": record["district"],
        "ward": None,
        "street_or_project": record["street_or_project"],
        "area_m2": 1.0,
        "price": float(price_per_m2),
        "price_per_m2": float(price_per_m2),
        "listing_date": record["effective_date"],
        "area_type": "urban",
        "legal_status": "official_land_price_table",
        "source_name": f"CSDL VBPL / {record['official_document']}",
        "source_url": source_url,
        "source_page_title": (
            f"{record['official_document']} - bảng giá đất 2026 - "
            f"{record['district']} - {record['street_or_project']}"
        ),
        "source_collected_at": collected_at,
        "source_access_method": "official_vbpl_document",
        "source_domain": "vbpl.vn",
        "source_category": "official_land_price_table",
        "source_crawl_at": collected_at,
        "raw_source_content": canonical_json(raw_source),
        "data_collection_status": "collected",
        "collection_attempt_count": 1,
        "last_collection_attempt": collected_at,
        "verification_note": (
            "E4 official legal-document land-price reference. This is not a public "
            "market transaction or auction anchor and must not be used as transaction evidence."
        ),
        "verified_by": "codex:official_e5_ingest",
        "verified_at": collected_at,
        "collected_by": "codex:official_e5_ingest",
        "collected_at": collected_at,
        "collection_method": "official_land_price_reference",
        "field_notes": (
            f"Self-collected official row from {record['official_document']}: "
            f"{record['street_or_project']} ({record['segment_from']} - "
            f"{record['segment_to'] or 'trọn đường'}), {record['position']}, "
            f"{price_per_m2:,} VND/m2. Not a market transaction."
        ),
        "verification_notes": "Official-source E4 reference record with transparent provenance chain.",
        "evidence_tier": "E4",
        "evidence_tier_updated_at": collected_at,
        "collection_timestamp": collected_at,
        "data_source_region": "official_vbpl_2026",
        "source_region": record["district"],
        "created_at": collected_at,
        "updated_at": collected_at,
        "last_updated_at": collected_at,
        "description": (
            "Official land-price-table unit reference (1 m2), not a sale listing "
            "or market transaction."
        ),
        "is_transacted": 0,
        "price_revision_count": 0,
        "initial_price": float(price_per_m2),
        "form_submission_id": f"official_e5_{record_id}",
    }


def insert_property(conn: sqlite3.Connection, payload: dict[str, Any]) -> None:
    columns = list(payload.keys())
    placeholders = ", ".join("?" for _ in columns)
    conn.execute(
        f"INSERT INTO properties ({', '.join(columns)}) VALUES ({placeholders})",
        [payload[column] for column in columns],
    )


def insert_provenance(
    conn: sqlite3.Connection,
    prop_id: int,
    record: dict[str, Any],
    payload: dict[str, Any],
    collected_at: str,
) -> None:
    source_url = payload["source_url"]
    steps = [
        {
            "step": "OFFICIAL_DOCUMENT_LOCATED",
            "actor": "codex:official_e5_ingest",
            "source": record["official_source_url"],
            "verify_url": record["official_source_url"],
            "metadata": {
                "official_document": record["official_document"],
                "effective_date": record["effective_date"],
                "structured_source_url": record["structured_source_url"],
            },
        },
        {
            "step": "OFFICIAL_TABLE_ROW_EXTRACTED",
            "actor": "codex:official_e5_ingest",
            "source": source_url,
            "verify_url": record["structured_source_url"],
            "metadata": {
                "official_record_id": record["official_record_id"],
                "street_or_project": record["street_or_project"],
                "segment_from": record["segment_from"],
                "segment_to": record["segment_to"],
                "position": record["position"],
                "price_per_m2_vnd": record["price_per_m2_vnd"],
            },
        },
        {
            "step": "SCOPE_AND_CLEANLINESS_VALIDATED",
            "actor": "codex:official_e5_ingest",
            "source": source_url,
            "verify_url": record["official_source_url"],
            "metadata": {
                "district": record["district"],
                "in_project_scope": True,
                "not_simulated": True,
                "not_market_transaction": True,
            },
        },
        {
            "step": "OFFICIAL_REFERENCE_APPROVED",
            "actor": "codex:official_e5_ingest",
            "source": source_url,
            "verify_url": record["official_source_url"],
            "metadata": {
                "evidence_tier": "E4",
                "collection_method": "official_land_price_reference",
                "data_origin_type": "self_collected",
            },
        },
    ]

    prev_id = None
    prev_hash = None
    for step in steps:
        material = {
            "property_id": prop_id,
            "step": step["step"],
            "source": step["source"],
            "metadata": step["metadata"],
        }
        out_hash = content_hash(material)
        cur = conn.execute(
            """
            INSERT INTO provenance_chains (
                property_id, step, timestamp, actor, input_hash, output_hash,
                source, verify_url, metadata_json, prev_step_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prop_id,
                step["step"],
                collected_at,
                step["actor"],
                prev_hash,
                out_hash,
                step["source"],
                step["verify_url"],
                canonical_json(step["metadata"]),
                prev_id,
            ),
        )
        prev_id = int(cur.lastrowid)
        prev_hash = out_hash


def insert_audit_log(
    conn: sqlite3.Connection,
    prop_id: int,
    record: dict[str, Any],
    payload: dict[str, Any],
    collected_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO audit_logs (
            record_id, table_name, action_type, changed_by, changed_at,
            old_value_json, new_value_json, change_note
        ) VALUES (?, 'properties', 'CREATE', 'codex:official_e5_ingest', ?, NULL, ?, ?)
        """,
        (
            prop_id,
            collected_at,
            canonical_json(
                {
                    "official_record_id": record["official_record_id"],
                    "source_url": payload["source_url"],
                    "price_per_m2_vnd": record["price_per_m2_vnd"],
                    "district": record["district"],
                }
            ),
            "Self-collected E4 official land-price-table reference; no simulation; reference-only.",
        ),
    )


def run(apply: bool) -> dict[str, Any]:
    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    for record in records:
        validate_record(record)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.row_factory = sqlite3.Row
    collected_at = utc_now()
    existing = existing_submission_ids(conn)
    next_id = max_property_id(conn) + 1

    stats = {
        "started_at": collected_at,
        "mode": "apply" if apply else "dry-run",
        "source_data_path": str(DATA_PATH),
        "records_seen": len(records),
        "inserted": 0,
        "skipped_existing": 0,
        "inserted_ids": [],
    }

    for record in records:
        submission_id = f"official_e5_{record['official_record_id']}"
        if submission_id in existing:
            stats["skipped_existing"] += 1
            continue
        payload = property_payload(next_id, record, collected_at)
        if apply:
            insert_property(conn, payload)
            insert_provenance(conn, next_id, record, payload, collected_at)
            insert_audit_log(conn, next_id, record, payload, collected_at)
        stats["inserted"] += 1
        stats["inserted_ids"].append(next_id)
        next_id += 1

    if apply:
        conn.commit()
    conn.close()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"official_e5_ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    stats["report_path"] = str(report_path)
    report_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest official land-price reference records")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(apply=args.apply), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
