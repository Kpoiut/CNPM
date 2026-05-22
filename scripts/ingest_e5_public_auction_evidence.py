#!/usr/bin/env python3
"""Ingest public auction asset evidence as self-collected E5 anchor records.

This importer is intentionally conservative:
- only public HTTPS sources are accepted;
- only the six configured project districts are accepted;
- owner names, phone numbers, account numbers, and identity-document details are
  not copied into the normalized database payload;
- official land-price-table rows are demoted from "complete E5" to reference-only
  E4, because they are legal price references rather than auction/transaction
  evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "real_estate_avm.db"
DATA_PATH = PROJECT_ROOT / "data" / "e5_public_auction_asset_evidence_20260513.json"
REPORT_DIR = PROJECT_ROOT / "reports"

SCOPE_DISTRICTS = {
    "Quận Cầu Giấy",
    "Quận Thanh Xuân",
    "Quận Đống Đa",
    "Quận 7",
    "Quận Bình Thạnh",
    "Quận Tân Bình",
}

ALLOWED_SOURCE_DOMAINS = {
    "agribank.com.vn",
    "www.agribank.com.vn",
    "baodauthau.vn",
    "www.baodauthau.vn",
}

PRICE_TYPES = {"official_starting_price", "public_winning_price"}


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
        WHERE form_submission_id LIKE 'e5_auction_%'
        """
    ).fetchall()
    return {str(row[0]) for row in rows if row[0]}


def submission_id(record: dict[str, Any]) -> str:
    return f"e5_auction_{record['auction_record_id']}"


def source_url(record: dict[str, Any]) -> str:
    return f"{record['source_url']}#{record['auction_record_id']}"


def parse_domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def validate_record(record: dict[str, Any]) -> None:
    record_id = record.get("auction_record_id", "")
    if not record_id:
        raise ValueError("Missing auction_record_id")
    if record["district"] not in SCOPE_DISTRICTS:
        raise ValueError(f"Out-of-scope district for {record_id}: {record['district']}")
    if record.get("price_type") not in PRICE_TYPES:
        raise ValueError(f"Invalid price_type for {record_id}: {record.get('price_type')}")
    if not record.get("not_simulated"):
        raise ValueError(f"Record must be explicitly non-simulated: {record_id}")
    if not record.get("pii_redacted"):
        raise ValueError(f"Record must be explicitly PII-redacted: {record_id}")
    if record.get("price_type") == "official_starting_price" and not record.get("not_private_transaction"):
        raise ValueError(f"Starting-price auction record must be non-private-transaction: {record_id}")

    url = str(record.get("source_url") or "")
    domain = parse_domain(url)
    if not url.startswith("https://") or domain not in ALLOWED_SOURCE_DOMAINS:
        raise ValueError(f"Source URL is not an allowed public HTTPS source for {record_id}: {url}")

    area = float(record.get("area_m2") or 0)
    price = int(record.get("price_vnd") or 0)
    if area <= 0 or price <= 0:
        raise ValueError(f"Missing positive price/area for {record_id}")
    price_per_m2 = price / area
    if not 5_000_000 <= price_per_m2 <= 500_000_000:
        raise ValueError(f"Price per m2 outside clean range for {record_id}: {price_per_m2:,.0f}")


def validate_records(records: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for record in records:
        validate_record(record)
        record_id = record["auction_record_id"]
        if record_id in seen:
            raise ValueError(f"Duplicate auction_record_id in data file: {record_id}")
        seen.add(record_id)


def raw_source_payload(record: dict[str, Any], price_per_m2: float) -> dict[str, Any]:
    return {
        "record_type": "public_auction_asset_evidence",
        "auction_record_id": record["auction_record_id"],
        "province_city": record["province_city"],
        "district": record["district"],
        "ward": record.get("ward"),
        "street_or_project": record["street_or_project"],
        "address": record["address"],
        "property_type": record["property_type"],
        "area_m2": float(record["area_m2"]),
        "price_vnd": int(record["price_vnd"]),
        "price_per_m2_vnd": round(price_per_m2, 2),
        "price_type": record["price_type"],
        "auction_status": record["auction_status"],
        "auction_date": record.get("auction_date"),
        "published_date": record.get("published_date"),
        "source_name": record["source_name"],
        "source_domain": record["source_domain"],
        "source_url": record["source_url"],
        "source_fact_summary": record["source_fact_summary"],
        "not_simulated": True,
        "not_private_transaction": bool(record.get("not_private_transaction", True)),
        "pii_redacted": True,
        "e5_interpretation": (
            "High-traceability public auction/secured-asset anchor. Starting-price "
            "records are not private market transactions and must be used as auction "
            "anchors, not as notarized sale-price evidence."
        ),
        "self_collection_basis": record["self_collection_basis"],
    }


def property_payload(prop_id: int, record: dict[str, Any], collected_at: str) -> dict[str, Any]:
    area = float(record["area_m2"])
    price = float(record["price_vnd"])
    price_per_m2 = price / area
    raw_source = raw_source_payload(record, price_per_m2)
    source = source_url(record)
    return {
        "id": prop_id,
        "data_origin_type": "self_collected",
        "record_status": "verified",
        "verification_status": "verified",
        "property_type": record["property_type"],
        "province_city": record["province_city"],
        "district": record["district"],
        "ward": record.get("ward"),
        "street_or_project": record["street_or_project"],
        "area_m2": area,
        "price": price,
        "price_per_m2": price_per_m2,
        "listing_date": record.get("published_date") or record.get("auction_date"),
        "area_type": "urban",
        "legal_status": "public_auction_asset_evidence",
        "source_name": record["source_name"],
        "source_url": source,
        "source_page_title": f"{record['source_name']} - {record['auction_record_id']}",
        "source_collected_at": collected_at,
        "source_access_method": record["source_access_method"],
        "source_domain": record["source_domain"],
        "source_category": "public_auction_asset_evidence",
        "source_crawl_at": collected_at,
        "raw_source_content": canonical_json(raw_source),
        "data_collection_status": "collected",
        "collection_attempt_count": 1,
        "last_collection_attempt": collected_at,
        "verification_note": (
            "Self-collected E5 public auction asset evidence. This is non-simulated, "
            "traceable, PII-redacted, and limited to auction anchor use."
        ),
        "verified_by": "codex:e5_public_auction_ingest",
        "verified_at": collected_at,
        "collected_by": "codex:e5_public_auction_ingest",
        "collected_at": collected_at,
        "collection_method": "public_auction_asset_evidence",
        "field_notes": (
            f"Self-collected public auction evidence: {record['address']}; "
            f"area={area:g} m2; price={int(price):,} VND; "
            f"price_type={record['price_type']}; source={record['source_name']}."
        ),
        "verification_notes": (
            "E5 public auction/secured-asset anchor with row-level source URL. "
            "No simulation; no private PII copied into normalized record."
        ),
        "evidence_tier": "E5",
        "evidence_tier_updated_at": collected_at,
        "collection_timestamp": collected_at,
        "data_source_region": "public_auction_anchor_20260513",
        "source_region": record["district"],
        "created_at": collected_at,
        "updated_at": collected_at,
        "last_updated_at": collected_at,
        "description": (
            "Public auction asset evidence normalized from a traceable public source; "
            "not a simulated or synthetic listing."
        ),
        "is_transacted": 1 if record["price_type"] == "public_winning_price" else 0,
        "price_revision_count": 0,
        "initial_price": price,
        "form_submission_id": submission_id(record),
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
    source = payload["source_url"]
    steps = [
        {
            "step": "PUBLIC_AUCTION_SOURCE_LOCATED",
            "source": source,
            "metadata": {
                "source_name": record["source_name"],
                "source_domain": record["source_domain"],
                "published_date": record.get("published_date"),
                "auction_date": record.get("auction_date"),
            },
        },
        {
            "step": "AUCTION_ASSET_FACTS_EXTRACTED",
            "source": source,
            "metadata": {
                "auction_record_id": record["auction_record_id"],
                "address": record["address"],
                "district": record["district"],
                "area_m2": record["area_m2"],
                "price_vnd": record["price_vnd"],
                "price_type": record["price_type"],
            },
        },
        {
            "step": "SCOPE_DEDUP_PII_VALIDATED",
            "source": source,
            "metadata": {
                "in_project_six_district_scope": True,
                "not_simulated": True,
                "pii_redacted": True,
                "not_private_transaction": bool(record.get("not_private_transaction", True)),
            },
        },
        {
            "step": "E5_AUCTION_ANCHOR_APPROVED",
            "source": source,
            "metadata": {
                "evidence_tier": "E5",
                "collection_method": "public_auction_asset_evidence",
                "data_origin_type": "self_collected",
                "limitation": "auction anchor, not notarized private transaction evidence",
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
                "codex:e5_public_auction_ingest",
                prev_hash,
                out_hash,
                step["source"],
                record["source_url"],
                canonical_json(step["metadata"]),
                prev_id,
            ),
        )
        prev_id = int(cur.lastrowid)
        prev_hash = out_hash


def insert_create_audit(
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
        ) VALUES (?, 'properties', 'CREATE', 'codex:e5_public_auction_ingest', ?, NULL, ?, ?)
        """,
        (
            prop_id,
            collected_at,
            canonical_json(
                {
                    "auction_record_id": record["auction_record_id"],
                    "source_url": payload["source_url"],
                    "district": record["district"],
                    "area_m2": record["area_m2"],
                    "price_vnd": record["price_vnd"],
                    "price_type": record["price_type"],
                }
            ),
            "Self-collected E5 public auction asset evidence; no simulation; PII redacted.",
        ),
    )


def demote_official_land_price_references(
    conn: sqlite3.Connection,
    now: str,
    apply: bool,
) -> list[int]:
    rows = conn.execute(
        """
        SELECT rowid, id, evidence_tier, verification_note, verification_notes
        FROM properties
        WHERE COALESCE(record_status, '') != 'archived'
          AND collection_method = 'official_land_price_reference'
          AND evidence_tier = 'E5'
        """
    ).fetchall()
    demoted_ids = [int(row["id"]) for row in rows]
    if not apply:
        return demoted_ids

    for row in rows:
        old_payload = {
            "id": row["id"],
            "evidence_tier": row["evidence_tier"],
            "verification_note": row["verification_note"],
            "verification_notes": row["verification_notes"],
        }
        note = (
            "Official land-price-table reference only; not transaction or auction "
            "evidence. Demoted from complete E5 to E4 reference during public "
            "auction E5 rework."
        )
        merged_notes = "; ".join(
            part for part in [row["verification_notes"], note] if part
        )
        conn.execute(
            """
            UPDATE properties
            SET evidence_tier = 'E4',
                evidence_tier_updated_at = ?,
                verification_note = ?,
                verification_notes = ?,
                updated_at = ?,
                last_updated_at = ?
            WHERE rowid = ?
            """,
            (now, note, merged_notes, now, now, row["rowid"]),
        )
        conn.execute(
            """
            INSERT INTO audit_logs (
                record_id, table_name, action_type, changed_by, changed_at,
                old_value_json, new_value_json, change_note
            ) VALUES (?, 'properties', 'UPDATE', 'codex:e5_public_auction_ingest', ?, ?, ?, ?)
            """,
            (
                row["id"],
                now,
                canonical_json(old_payload),
                canonical_json({"evidence_tier": "E4", "verification_note": note}),
                "Official price table is reference-only; not counted as complete E5 auction/transaction evidence.",
            ),
        )
    return demoted_ids


def run(apply: bool) -> dict[str, Any]:
    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    validate_records(records)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.row_factory = sqlite3.Row
    collected_at = utc_now()
    existing = existing_submission_ids(conn)
    next_id = max_property_id(conn) + 1

    stats: dict[str, Any] = {
        "started_at": collected_at,
        "mode": "apply" if apply else "dry-run",
        "source_data_path": str(DATA_PATH),
        "records_seen": len(records),
        "inserted": 0,
        "skipped_existing": 0,
        "inserted_ids": [],
        "official_land_price_references_demoted_from_e5_to_e4": [],
    }

    stats["official_land_price_references_demoted_from_e5_to_e4"] = (
        demote_official_land_price_references(conn, collected_at, apply)
    )

    for record in records:
        sid = submission_id(record)
        if sid in existing:
            stats["skipped_existing"] += 1
            continue
        payload = property_payload(next_id, record, collected_at)
        if apply:
            insert_property(conn, payload)
            insert_provenance(conn, next_id, record, payload, collected_at)
            insert_create_audit(conn, next_id, record, payload, collected_at)
        stats["inserted"] += 1
        stats["inserted_ids"].append(next_id)
        next_id += 1

    if apply:
        conn.commit()
    conn.close()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"e5_public_auction_ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    stats["report_path"] = str(report_path)
    report_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest public auction asset evidence as E5 records")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(apply=args.apply), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
