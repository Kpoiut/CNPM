#!/usr/bin/env python3
"""Top up clean public records from traceable local cache and public HTTPS pages.

Security posture:
- uses only local JSONL cache files and HTTPS GET requests to approved public pages;
- does not execute downloaded code, use credentials, or bypass access controls;
- caps inserts, runtime, and working-set memory;
- writes provenance and audit logs for every imported record.
"""

from __future__ import annotations

import argparse
import gc
import json
import re
import sqlite3
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.complete_traceable_dataset import (  # noqa: E402
    DB_PATH,
    DISTRICTS,
    HEADERS,
    RUN_DIR,
    add_audit_log,
    add_provenance,
    classify_property_type,
    current_rss_mb,
    insert_property,
    listing_id_from_url,
    parse_float,
    parse_price,
    stable_hash,
    utc_now,
)

SCOPE_DISTRICTS = set(DISTRICTS)
CAFELAND_BASE = "https://nhadat.cafeland.vn/nha-dat-ban/"
CAFELAND_DOMAIN = "nhadat.cafeland.vn"

DISTRICT_PATTERNS = {
    "Quận Cầu Giấy": ("cau giay", "cau-giay"),
    "Quận Thanh Xuân": ("thanh xuan", "thanh-xuan"),
    "Quận Đống Đa": ("dong da", "dong-da"),
    "Quận 7": ("quan 7", "quan-7", "q7", "q.7"),
    "Quận Bình Thạnh": ("binh thanh", "binh-thanh"),
    "Quận Tân Bình": ("tan binh", "tan-binh"),
}

OUT_OF_SCOPE_URL_MARKERS = (
    "bai-chay",
    "ha-long",
    "quang-ninh",
    "phuong-binh-thang",
    "binh-thang-the-gio-riverside",
    "xa-long-hung",
    "vinhomes-ocean-park-2",
    "hado-centrosa",
    "vinhomes-central-park",
)

OUT_OF_SCOPE_TEXT_MARKERS = (
    "bai chay",
    "ha long",
    "quang ninh",
    "di an",
    "binh duong",
    "thao dien",
    "quan 2",
    "thu duc",
    "hoc mon",
    "nha be",
    "quan 8",
    "quan tan phu",
    "long hung",
    "vinhomes ocean park",
    "vinhomes central park",
    "ha dong",
    "hoai duc",
)


def normalize_text(text: str) -> str:
    text = (text or "").lower().replace("đ", "d")
    text = "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"[^a-z0-9.-]+", " ", text)


def detect_district(text: str) -> str | None:
    normalized = f" {normalize_text(text)} "
    for district, patterns in DISTRICT_PATTERNS.items():
        for pattern in patterns:
            if f" {pattern} " in normalized or pattern in normalized:
                return district
    return None


def public_count(conn: sqlite3.Connection) -> int:
    return int(conn.execute(
        """
        SELECT COUNT(*) FROM properties
        WHERE COALESCE(record_status, '') != 'archived'
          AND data_origin_type = 'public_collected'
          AND price > 0
        """
    ).fetchone()[0])


def source_exists_any(conn: sqlite3.Connection, source_url: str, form_id: str | None = None) -> bool:
    if form_id:
        row = conn.execute(
            "SELECT 1 FROM properties WHERE form_submission_id = ? LIMIT 1",
            (form_id,),
        ).fetchone()
        if row:
            return True
    row = conn.execute(
        "SELECT 1 FROM properties WHERE source_url = ? LIMIT 1",
        (source_url,),
    ).fetchone()
    return row is not None


def is_clean_record(record: dict) -> bool:
    source_url = str(record.get("source_url") or "")
    if not source_url.startswith("https://"):
        return False
    if any(marker in source_url.lower() for marker in OUT_OF_SCOPE_URL_MARKERS):
        return False
    if record.get("district") not in SCOPE_DISTRICTS:
        return False
    try:
        price = float(record["price"])
        area = float(record["area_m2"])
        ppm = float(record["price_per_m2"])
    except (KeyError, TypeError, ValueError):
        return False
    return (
        100_000_000 <= price <= 2_000_000_000_000
        and 10 <= area <= 20_000
        and 5_000_000 <= ppm <= 500_000_000
    )


def location_text_contradicts_scope(record: dict) -> bool:
    facts = record.get("extracted_facts") if isinstance(record.get("extracted_facts"), dict) else {}
    text = normalize_text(
        " ".join(
            str(value or "")
            for value in (
                record.get("ward"),
                record.get("street_or_project"),
                record.get("source_page_title"),
                record.get("title"),
                facts.get("location_text"),
                facts.get("title"),
            )
        )
    )
    return any(marker in text for marker in OUT_OF_SCOPE_TEXT_MARKERS)


def normalized_fact_key_from_values(
    district: str | None,
    ward: str | None,
    street_or_project: str | None,
    area_m2: Any,
    price: Any,
    source_domain: str | None,
) -> str | None:
    street = normalize_text(str(street_or_project or ""))
    if len(street) < 8:
        return None
    try:
        area_value = float(area_m2 or 0)
        price_value = float(price or 0)
    except (TypeError, ValueError):
        return None
    if area_value <= 0 or price_value <= 0:
        return None
    return "|".join(
        [
            normalize_text(str(district or "")),
            normalize_text(str(ward or "")),
            street,
            f"{area_value:.2f}",
            f"{price_value:.0f}",
            normalize_text(str(source_domain or "")),
        ]
    )


def normalized_fact_key(record: dict) -> str | None:
    return normalized_fact_key_from_values(
        record.get("district"),
        record.get("ward"),
        record.get("street_or_project"),
        record.get("area_m2"),
        record.get("price"),
        record.get("source_domain"),
    )


def active_fact_keys(conn: sqlite3.Connection) -> set[str]:
    keys: set[str] = set()
    rows = conn.execute(
        """
        SELECT district, ward, street_or_project, area_m2, price, source_domain
        FROM properties
        WHERE COALESCE(record_status, '') != 'archived'
          AND COALESCE(collection_method, '') != 'official_land_price_reference'
          AND street_or_project IS NOT NULL
          AND TRIM(street_or_project) != ''
          AND area_m2 IS NOT NULL
          AND price IS NOT NULL
        """
    ).fetchall()
    for row in rows:
        key = normalized_fact_key_from_values(*row)
        if key:
            keys.add(key)
    return keys


def cache_records() -> list[dict]:
    records: list[dict] = []
    seen_urls: set[str] = set()
    for path in sorted(RUN_DIR.glob("raw_candidates_*.jsonl")):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                url = str(record.get("source_url") or "").strip()
                if not url or url in seen_urls:
                    continue
                record.setdefault("source_name", "alonhadat.com.vn")
                record.setdefault("source_domain", "alonhadat.com.vn")
                record.setdefault("source_access_method", "cached_public_html_candidate")
                if is_clean_record(record):
                    records.append(record)
                    seen_urls.add(url)
    return records


def cafeland_page_url(page_num: int) -> str:
    if page_num == 1:
        return CAFELAND_BASE
    return f"{CAFELAND_BASE}page-{page_num}/"


def find_row_item(node):
    current = node
    for _ in range(8):
        if current is None:
            return None
        classes = current.get("class") or []
        if any("row-item" == cls or str(cls).startswith("row-item") for cls in classes):
            return current
        current = current.parent
    return None


def title_from_lines(lines: list[str], price_idx: int) -> str:
    for i in range(price_idx - 1, -1, -1):
        value = lines[i].strip()
        lower = normalize_text(value)
        if not value or lower in {"uy tin"} or re.fullmatch(r"\d+", lower):
            continue
        return value[:255]
    return ""


def parse_cafeland_records(html: str, list_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    page_title = soup.title.get_text(" ", strip=True) if soup.title else ""
    records: list[dict] = []
    seen_urls: set[str] = set()

    for a in soup.select('a[href$=".html"]'):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        source_url = urljoin(CAFELAND_BASE, href).split("#", 1)[0]
        if CAFELAND_DOMAIN not in source_url or source_url in seen_urls:
            continue

        row = find_row_item(a)
        if row is None:
            continue
        lines = [line.strip() for line in row.get_text("\n", strip=True).splitlines() if line.strip()]
        if len(lines) < 5:
            continue

        area_idx = None
        for idx, line in enumerate(lines):
            if re.fullmatch(r"\d+(?:[.,]\d+)?\s*m2", normalize_text(line).replace(" ", "")):
                area_idx = idx
                break
            if re.search(r"\d+(?:[.,]\d+)?\s*m2", normalize_text(line)) and idx > 0:
                area_idx = idx
                break
        if area_idx is None or area_idx < 1:
            continue

        price_text = lines[area_idx - 1]
        price = parse_price(price_text)
        area = parse_float(lines[area_idx])
        if not price or not area:
            continue

        title = title_from_lines(lines, area_idx - 1)
        full_text = row.get_text(" ", strip=True)
        district = detect_district(f"{title} {full_text} {source_url}")
        if not district:
            continue

        province = DISTRICTS[district]["province"]
        ppm = price / area
        location = lines[area_idx + 1] if area_idx + 1 < len(lines) else district
        legal_status = "ownership_certificate" if re.search(r"sổ|pháp lý", full_text, re.I) else "unknown"

        record = {
            "source_listing_key": f"CFL-{listing_id_from_url(source_url)}",
            "source_url": source_url,
            "source_list_page": list_url,
            "source_page_title": page_title[:255],
            "title": title or source_url.rsplit("/", 1)[-1][:255],
            "property_type": classify_property_type(full_text),
            "province_city": province,
            "district": district,
            "street_or_project": location[:255],
            "area_m2": round(area, 2),
            "price": float(price),
            "price_per_m2": round(ppm, -3),
            "bedrooms": 0,
            "bathrooms": 0,
            "floor_count": 1,
            "frontage_m": None,
            "legal_status": legal_status,
            "furnishing": "unknown",
            "source_name": CAFELAND_DOMAIN,
            "source_domain": CAFELAND_DOMAIN,
            "source_access_method": "https_get_public_html",
            "extracted_facts": {
                "title": title,
                "price_text": price_text,
                "area_text": lines[area_idx],
                "location_text": location,
                "list_page": list_url,
                "row_hash": stable_hash(full_text[:5000]),
            },
        }
        if is_clean_record(record):
            records.append(record)
            seen_urls.add(source_url)
    return records


def fetch_html(url: str, timeout: int = 15) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
    except requests.RequestException:
        return None
    if resp.status_code != 200 or len(resp.text) < 10_000:
        return None
    return resp.text


def import_records(conn: sqlite3.Connection, records: list[dict], args: argparse.Namespace,
                   fact_keys: set[str],
                   stats: dict, source_bucket: str, collected_at: str) -> None:
    for record in records:
        if public_count(conn) >= args.target_public:
            stats["stop_reason"] = "target_public_reached"
            return
        if args.max_inserts and stats["inserted"] >= args.max_inserts:
            stats["stop_reason"] = f"max_inserts={args.max_inserts}"
            return
        if args.max_runtime_seconds and time.monotonic() - stats["_started"] >= args.max_runtime_seconds:
            stats["stop_reason"] = f"max_runtime_seconds={args.max_runtime_seconds}"
            return
        rss = current_rss_mb()
        if rss:
            stats["max_rss_mb"] = max(stats["max_rss_mb"], round(rss, 1))
            if args.max_memory_mb and rss >= args.max_memory_mb:
                stats["stop_reason"] = f"max_memory_mb={args.max_memory_mb}"
                return

        form_id = record.get("source_listing_key")
        if source_exists_any(conn, record["source_url"], form_id):
            stats["duplicates"] += 1
            continue
        if not is_clean_record(record):
            stats["invalid"] += 1
            continue
        if location_text_contradicts_scope(record):
            stats["invalid"] += 1
            continue
        fact_key = normalized_fact_key(record)
        if fact_key and fact_key in fact_keys:
            stats["duplicates"] += 1
            continue
        if args.apply:
            prop_id = insert_property(conn, record, "public_collected", collected_at)
            add_provenance(conn, prop_id, record, "public_collected", collected_at)
            add_audit_log(conn, prop_id, record, "public_collected", collected_at)
            if stats["inserted"] % 50 == 0:
                conn.commit()
        if fact_key:
            fact_keys.add(fact_key)
        stats["inserted"] += 1
        stats["by_source"][source_bucket] = stats["by_source"].get(source_bucket, 0) + 1


def run(args: argparse.Namespace) -> dict:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    collected_at = utc_now()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=60000")
    stats = {
        "started_at": collected_at,
        "mode": "apply" if args.apply else "dry-run",
        "before_public": public_count(conn),
        "target_public": args.target_public,
        "cache_candidates": 0,
        "cafeland_pages_seen": 0,
        "cafeland_records_seen": 0,
        "inserted": 0,
        "duplicates": 0,
        "invalid": 0,
        "fetch_errors": 0,
        "by_source": {},
        "max_rss_mb": 0.0,
        "stop_reason": None,
        "_started": time.monotonic(),
    }
    fact_keys = active_fact_keys(conn)

    if args.use_cache:
        cached = cache_records()
        stats["cache_candidates"] = len(cached)
        import_records(conn, cached, args, fact_keys, stats, "cached_alonhadat", collected_at)

    page_num = 1
    while not stats["stop_reason"] and public_count(conn) < args.target_public and page_num <= args.cafeland_pages:
        if args.max_runtime_seconds and time.monotonic() - stats["_started"] >= args.max_runtime_seconds:
            stats["stop_reason"] = f"max_runtime_seconds={args.max_runtime_seconds}"
            break
        url = cafeland_page_url(page_num)
        html = fetch_html(url)
        stats["cafeland_pages_seen"] += 1
        if not html:
            stats["fetch_errors"] += 1
            page_num += 1
            continue
        records = parse_cafeland_records(html, url)
        stats["cafeland_records_seen"] += len(records)
        import_records(conn, records, args, fact_keys, stats, "nhadat_cafeland", collected_at)
        del html, records
        if page_num % args.gc_every_pages == 0:
            gc.collect()
        page_num += 1
        time.sleep(args.delay)

    if args.apply:
        conn.commit()
    stats["after_public"] = public_count(conn)
    stats.pop("_started", None)
    conn.close()

    report_path = RUN_DIR / f"topup_clean_public_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    stats["report_path"] = str(report_path)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Top up clean traceable public dataset")
    parser.add_argument("--target-public", type=int, default=3000)
    parser.add_argument("--cafeland-pages", type=int, default=80)
    parser.add_argument("--delay", type=float, default=0.1)
    parser.add_argument("--max-inserts", type=int, default=250)
    parser.add_argument("--max-runtime-seconds", type=int, default=600)
    parser.add_argument("--max-memory-mb", type=int, default=650)
    parser.add_argument("--gc-every-pages", type=int, default=5)
    parser.add_argument("--use-cache", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.apply and args.dry_run:
        raise SystemExit("Choose only one of --apply or --dry-run")
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["after_public"] < args.target_public:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
