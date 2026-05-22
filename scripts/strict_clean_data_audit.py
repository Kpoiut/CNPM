#!/usr/bin/env python3
"""Strict data cleanliness audit and archival.

The script archives, rather than deletes, records that are outside the six
project districts, transparently synthetic/fake, source-location contradictory,
or duplicate listing rows. Official land-price reference records are allowed to
share one legal-document URL because their row identity is in raw_source_content.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "real_estate_avm.db"
REPORT_DIR = PROJECT_ROOT / "reports"

SCOPE_DISTRICTS = {
    "Quận Cầu Giấy",
    "Quận Thanh Xuân",
    "Quận Đống Đa",
    "Quận 7",
    "Quận Bình Thạnh",
    "Quận Tân Bình",
}

# Markers that clearly contradict the configured six-district scope. These are
# intentionally conservative so real ambiguous records are not archived by name
# matching alone.
OUT_OF_SCOPE_URL_MARKERS = (
    "bai-chay",
    "ha-long",
    "quang-ninh",
    "phuong-binh-thang",
    "binh-thang-the-gio-riverside",
    "xa-long-hung",
    "vinhomes-ocean-park-2",
    "hado-centrosa",
    "phuong-12-5-hado",
    "vinhomes-central-park",
)

OUT_OF_SCOPE_TEXT_MARKERS = (
    "bãi cháy",
    "bai chay",
    "hạ long",
    "ha long",
    "quảng ninh",
    "quang ninh",
    "dĩ an",
    "di an",
    "bình dương",
    "binh duong",
    "thảo điền",
    "thao dien",
    "quận 2",
    "quan 2",
    "thủ đức",
    "thu duc",
    "hóc môn",
    "hoc mon",
    "nhà bè",
    "nha be",
    "quận 8",
    "quan 8",
    "quận tân phú",
    "quan tan phu",
    "long hưng",
    "long hung",
    "vinhomes ocean park",
    "vinhomes central park",
    "hà đông",
    "ha dong",
    "hoài đức",
    "hoai duc",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def active_where() -> str:
    return "COALESCE(record_status, '') != 'archived'"


def norm_url(url: str | None) -> str:
    return (url or "").strip().lower()


def norm_text(value: str | None) -> str:
    text = (value or "").strip().lower()
    decomposed = unicodedata.normalize("NFD", text)
    ascii_text = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return f"{text} {ascii_text}"


def is_official_reference(row: sqlite3.Row) -> bool:
    return (row["collection_method"] or "") == "official_land_price_reference"


def row_text(row: sqlite3.Row) -> str:
    parts = [
        row["source_url"],
        row["source_page_title"],
        row["source_name"],
        row["source_access_method"],
        row["source_category"],
        row["collection_method"],
        row["raw_source_content"],
        row["field_notes"],
        row["verification_notes"],
    ]
    return " ".join(str(part or "") for part in parts).lower()


def has_out_of_scope_text_marker(row: sqlite3.Row) -> bool:
    if is_official_reference(row):
        return False
    raw_location_text = row["raw_source_content"] or ""
    try:
        raw_json = json.loads(raw_location_text)
        if isinstance(raw_json, dict):
            raw_location_text = " ".join(
                str(raw_json.get(key) or "")
                for key in (
                    "address",
                    "ward",
                    "street_or_project",
                    "district",
                    "source_fact_summary",
                    "property_location",
                    "location",
                )
            )
    except json.JSONDecodeError:
        pass

    field_notes = row["field_notes"] or ""
    source_marker_index = field_notes.lower().find("source=")
    if source_marker_index >= 0:
        field_notes = field_notes[:source_marker_index]

    text = norm_text(
        " ".join(
            [
                str(row["ward"] or ""),
                str(row["street_or_project"] or ""),
                str(raw_location_text or ""),
                str(field_notes or ""),
                str(row["verification_notes"] or ""),
            ]
        )
    )
    return any(marker in text for marker in OUT_OF_SCOPE_TEXT_MARKERS)


def has_positive_synthetic_marker(row: sqlite3.Row) -> bool:
    method = (row["collection_method"] or "").strip().lower()
    source_access = (row["source_access_method"] or "").strip().lower()
    source_category = (row["source_category"] or "").strip().lower()
    if method in {"batch_generator", "synthetic_generator", "demo_seed"}:
        return True
    if source_access in {"batch_generator", "synthetic_generator", "demo_seed"}:
        return True
    if source_category in {"system_demo", "synthetic", "demo_seed"}:
        return True

    raw = (row["raw_source_content"] or "").lower()
    positive_json_flags = (
        r'"synthetic"\s*:\s*true',
        r'"is_synthetic"\s*:\s*true',
        r'"simulated"\s*:\s*true',
        r'"is_simulated"\s*:\s*true',
        r'"fake"\s*:\s*true',
        r'"is_fake"\s*:\s*true',
    )
    return any(re.search(pattern, raw) for pattern in positive_json_flags)


def load_active_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        f"""
        SELECT
            rowid AS _rowid, id, data_origin_type, record_status,
            verification_status, property_type, province_city, district,
            ward, street_or_project, area_m2, price, price_per_m2, source_name,
            source_url, source_page_title, source_access_method, source_domain,
            source_category, raw_source_content, collection_method,
            evidence_tier, field_notes, verification_notes, collected_at,
            verified_at, updated_at
        FROM properties
        WHERE {active_where()}
        """
    ).fetchall()


def evidence_rank(tier: str | None, official: bool = False) -> int:
    return {"E1": 5, "E2": 4, "E3": 3, "E4": 2, "E5": 1}.get(tier or "", 0)


def provenance_count(conn: sqlite3.Connection, prop_id: int | None) -> int:
    if prop_id is None:
        return 0
    row = conn.execute(
        "SELECT COUNT(*) FROM provenance_chains WHERE property_id = ?",
        (prop_id,),
    ).fetchone()
    return int(row[0] or 0)


def keep_score(conn: sqlite3.Connection, row: sqlite3.Row) -> tuple[Any, ...]:
    origin = 3 if row["data_origin_type"] == "self_collected" else 2
    verified = 2 if row["verification_status"] == "verified" else 1
    official = is_official_reference(row)
    pcount = provenance_count(conn, row["id"])
    return (
        official,
        origin,
        verified,
        evidence_rank(row["evidence_tier"], official=official),
        pcount,
        row["verified_at"] or "",
        row["updated_at"] or "",
        row["id"] or 0,
    )


def find_archive_candidates(conn: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    rows = load_active_rows(conn)
    candidates: dict[int, dict[str, Any]] = {}

    def add(row: sqlite3.Row, reason: str, detail: dict[str, Any] | None = None) -> None:
        candidates.setdefault(
            int(row["_rowid"]),
            {
                "property_id": row["id"],
                "reason": reason,
                "detail": detail or {},
            },
        )

    for row in rows:
        if row["district"] not in SCOPE_DISTRICTS:
            add(row, "outside_configured_six_district_scope", {"district": row["district"]})
            continue

        if row["id"] is None:
            add(row, "null_property_id")
            continue

        if row["price"] and (
            not row["area_m2"]
            or float(row["area_m2"] or 0) <= 0
            or not row["price_per_m2"]
            or float(row["price_per_m2"] or 0) <= 0
        ):
            add(row, "priced_record_missing_clean_area_or_ppm")
            continue

        if not is_official_reference(row) and has_positive_synthetic_marker(row):
            add(row, "synthetic_or_fake_marker_detected")
            continue

        text = row_text(row)
        url = norm_url(row["source_url"])
        if has_out_of_scope_text_marker(row):
            add(row, "address_text_contradicts_project_scope")
            continue

        if not is_official_reference(row) and url.startswith("/"):
            add(row, "relative_listing_url_without_traceable_domain", {"source_url": row["source_url"]})
            continue

        if not is_official_reference(row) and any(marker in url for marker in OUT_OF_SCOPE_URL_MARKERS):
            add(row, "source_url_location_contradicts_project_scope", {"source_url": row["source_url"]})

    duplicate_groups: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        if int(row["_rowid"]) in candidates or is_official_reference(row):
            continue
        url = norm_url(row["source_url"])
        if url:
            duplicate_groups[url].append(row)

    for url, group in duplicate_groups.items():
        if len(group) <= 1:
            continue
        keeper = max(group, key=lambda item: keep_score(conn, item))
        for row in group:
            if int(row["_rowid"]) == int(keeper["_rowid"]):
                continue
            add(
                row,
                "duplicate_listing_source_url",
                {
                    "source_url": url,
                    "kept_property_id": keeper["id"],
                    "kept_rowid": keeper["_rowid"],
                },
            )

    duplicate_fact_groups: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        if int(row["_rowid"]) in candidates or is_official_reference(row):
            continue
        street = norm_text(row["street_or_project"])
        if len(street) < 8 or not row["area_m2"] or not row["price"]:
            continue
        key = "|".join(
            [
                norm_text(row["district"]),
                norm_text(row["ward"]),
                street,
                f"{float(row['area_m2']):.2f}",
                f"{float(row['price']):.0f}",
                norm_text(row["source_domain"]),
            ]
        )
        duplicate_fact_groups[key].append(row)

    for key, group in duplicate_fact_groups.items():
        if len(group) <= 1:
            continue
        keeper = max(group, key=lambda item: keep_score(conn, item))
        for row in group:
            if int(row["_rowid"]) == int(keeper["_rowid"]):
                continue
            add(
                row,
                "duplicate_normalized_address_area_price_source",
                {
                    "group_key_hash": hashlib.sha256(key.encode("utf-8")).hexdigest(),
                    "kept_property_id": keeper["id"],
                    "kept_rowid": keeper["_rowid"],
                },
            )

    return candidates


def archive_rows(conn: sqlite3.Connection, candidates: dict[int, dict[str, Any]], now: str) -> None:
    for rowid, info in sorted(candidates.items()):
        old = conn.execute(
            "SELECT * FROM properties WHERE rowid = ?",
            (rowid,),
        ).fetchone()
        reason = f"strict_clean_data_audit:{info['reason']}"
        conn.execute(
            """
            UPDATE properties
            SET record_status = 'archived',
                archive_reason = ?,
                archived_at = ?,
                updated_at = ?,
                last_updated_at = ?
            WHERE rowid = ?
            """,
            (reason, now, now, now, rowid),
        )
        conn.execute(
            """
            INSERT INTO audit_logs (
                record_id, table_name, action_type, changed_by, changed_at,
                old_value_json, new_value_json, change_note
            ) VALUES (?, 'properties', 'ARCHIVE', 'codex:strict_clean_data_audit', ?, ?, ?, ?)
            """,
            (
                info["property_id"],
                now,
                canonical_json(
                    {
                        "rowid": rowid,
                        "id": old["id"],
                        "record_status": old["record_status"],
                        "source_url": old["source_url"],
                        "district": old["district"],
                    }
                ),
                canonical_json({"record_status": "archived", "archive_reason": reason}),
                canonical_json(info),
            ),
        )


def summarize(conn: sqlite3.Connection) -> dict[str, Any]:
    scope_placeholders = ",".join("?" for _ in SCOPE_DISTRICTS)
    active = active_where()
    active_total = conn.execute(f"SELECT COUNT(*) FROM properties WHERE {active}").fetchone()[0]
    by_origin = {
        row["data_origin_type"] or "NULL": row["n"]
        for row in conn.execute(
            f"""
            SELECT data_origin_type, COUNT(*) AS n
            FROM properties
            WHERE {active}
            GROUP BY data_origin_type
            """
        )
    }
    by_tier = {
        row["evidence_tier"] or "NULL": row["n"]
        for row in conn.execute(
            f"""
            SELECT evidence_tier, COUNT(*) AS n
            FROM properties
            WHERE {active}
            GROUP BY evidence_tier
            """
        )
    }
    outside_scope = conn.execute(
        f"""
        SELECT COUNT(*) FROM properties
        WHERE {active}
        AND (district IS NULL OR district NOT IN ({scope_placeholders}))
        """,
        tuple(SCOPE_DISTRICTS),
    ).fetchone()[0]
    duplicate_listing_groups = conn.execute(
        f"""
        SELECT COUNT(*) FROM (
            SELECT LOWER(source_url) AS u, COUNT(*) AS c
            FROM properties
            WHERE {active}
            AND COALESCE(collection_method, '') != 'official_land_price_reference'
            AND source_url IS NOT NULL
            AND TRIM(source_url) != ''
            GROUP BY LOWER(source_url)
            HAVING c > 1
        )
        """
    ).fetchone()[0]
    official_e5 = conn.execute(
        f"""
        SELECT COUNT(*) FROM properties
        WHERE {active}
        AND data_origin_type = 'self_collected'
        AND evidence_tier = 'E5'
        AND collection_method = 'official_land_price_reference'
        """
    ).fetchone()[0]
    auction_e5 = conn.execute(
        f"""
        SELECT COUNT(*) FROM properties
        WHERE {active}
        AND data_origin_type = 'self_collected'
        AND evidence_tier = 'E5'
        AND collection_method = 'public_auction_asset_evidence'
        """
    ).fetchone()[0]
    return {
        "active_total": active_total,
        "by_origin": by_origin,
        "by_tier": by_tier,
        "outside_scope": outside_scope,
        "duplicate_listing_source_url_groups": duplicate_listing_groups,
        "official_e5_active": official_e5,
        "auction_e5_active": auction_e5,
    }


def run(apply: bool) -> dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=60000")
    now = utc_now()
    before = summarize(conn)
    candidates = find_archive_candidates(conn)
    reason_counts: dict[str, int] = defaultdict(int)
    for info in candidates.values():
        reason_counts[info["reason"]] += 1

    if apply and candidates:
        archive_rows(conn, candidates, now)
        conn.commit()
    after = summarize(conn)
    conn.close()

    report = {
        "timestamp": now,
        "mode": "apply" if apply else "dry-run",
        "before": before,
        "archive_candidate_count": len(candidates),
        "archive_reason_counts": dict(sorted(reason_counts.items())),
        "archive_candidates": [
            {"rowid": rowid, **info}
            for rowid, info in sorted(candidates.items())
        ],
        "after": after,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"strict_clean_data_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report["report_path"] = str(report_path)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive unclean or duplicate active records")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--full-output", action="store_true", help="Print full candidate list to stdout")
    args = parser.parse_args()
    report = run(apply=args.apply)
    output = report if args.full_output else {k: v for k, v in report.items() if k != "archive_candidates"}
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
