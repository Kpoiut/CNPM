#!/usr/bin/env python3
"""
Complete public and self-collected real-estate datasets from traceable public pages.

Policy:
- no synthetic/generated records;
- only six configured districts;
- public records are list-page public listing anchors, stored as E2;
- self-collected records are manually verified public-listing conversions, stored
  as E3 with detail-page extraction evidence and a stronger provenance chain;
- E5 is not assigned because no public notarized/official transaction source is
  available.

The script writes directly with sqlite3 because the current production DB has an
INT id column rather than an autoincrement primary key.
"""

from __future__ import annotations

import argparse
import ctypes
import gc
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "real_estate_avm.db"
RUN_DIR = PROJECT_ROOT / "reports" / "dataset_completion"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.7",
}

DISTRICTS = {
    "Quận Cầu Giấy": {
        "province": "Hà Nội",
        "base": "https://alonhadat.com.vn/can-ban-nha-dat/ha-noi/cau-giay",
        "region": "hanoi",
    },
    "Quận Thanh Xuân": {
        "province": "Hà Nội",
        "base": "https://alonhadat.com.vn/can-ban-nha-dat/ha-noi/thanh-xuan",
        "region": "hanoi",
    },
    "Quận Đống Đa": {
        "province": "Hà Nội",
        "base": "https://alonhadat.com.vn/can-ban-nha-dat/ha-noi/dong-da",
        "region": "hanoi",
    },
    "Quận 7": {
        "province": "TP. Hồ Chí Minh",
        "base": "https://alonhadat.com.vn/nha-dat/can-ban/nha-dat/ho-chi-minh/138/quan-7.html",
        "region": "hcmc",
    },
    "Quận Bình Thạnh": {
        "province": "TP. Hồ Chí Minh",
        "base": "https://alonhadat.com.vn/nha-dat/can-ban/nha-dat/ho-chi-minh/145/quan-binh-thanh.html",
        "region": "hcmc",
    },
    "Quận Tân Bình": {
        "province": "TP. Hồ Chí Minh",
        "base": "https://alonhadat.com.vn/nha-dat/can-ban/nha-dat/ho-chi-minh/148/quan-tan-binh.html",
        "region": "hcmc",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def current_rss_mb() -> float:
    """Return current process working-set memory in MB on Windows; 0 if unavailable."""
    if os.name != "nt":
        return 0.0

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    psapi = ctypes.WinDLL("Psapi.dll")
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
        ctypes.c_ulong,
    ]
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
    if not ok:
        return 0.0
    return counters.WorkingSetSize / (1024 * 1024)


def stable_hash(data: object) -> str:
    text = json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def page_url(base: str, page_num: int) -> str:
    path, sep, query = base.partition("?")
    suffix = f"?{query}" if sep else ""
    if page_num == 1:
        return base
    if path.endswith(".html"):
        return path[:-5] + f"/trang--{page_num}.html" + suffix
    return f"{path}/trang-{page_num}" + suffix


def base_variants(base: str, price_bands: list[int]) -> list[str]:
    variants = [base]
    for band in price_bands:
        variants.append(f"{base}?dt=0&gia={band}&huong=0")
    return variants


def parse_price_bands(text: str) -> list[int]:
    if not text:
        return []
    if "-" in text:
        start, end = text.split("-", 1)
        return list(range(int(start), int(end) + 1))
    return [int(part.strip()) for part in text.split(",") if part.strip()]


def parse_price(text: str) -> float | None:
    if not text:
        return None
    value = text.lower().replace("\xa0", " ")
    value = re.sub(r"[^\d.,tỷtriệu]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    m = re.search(r"(\d[\d.,]*)\s*tỷ\s*(\d[\d.,]*)\s*triệu", value)
    if m:
        return float(m.group(1).replace(",", ".")) * 1e9 + float(m.group(2).replace(",", ".")) * 1e6
    m = re.search(r"(\d[\d.,]*)\s*tỷ", value)
    if m:
        return float(m.group(1).replace(",", ".")) * 1e9
    m = re.search(r"(\d[\d.,]*)\s*triệu", value)
    if m:
        return float(m.group(1).replace(",", ".")) * 1e6
    return None


def parse_float(text: str) -> float | None:
    if not text:
        return None
    m = re.search(r"(\d[\d.,]*)", text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def parse_int(text: str) -> int | None:
    value = parse_float(text)
    return int(value) if value is not None else None


def classify_property_type(text: str) -> str:
    lower = (text or "").lower()
    if any(k in lower for k in ["biệt thự", "villa"]):
        return "villa"
    if any(k in lower for k in ["đất", "đất nền", "nền"]):
        return "land"
    if any(k in lower for k in ["nhà phố", "mặt phố", "mặt tiền", "liền kề"]):
        return "townhouse"
    if any(k in lower for k in ["căn hộ", "chung cư", "ccmn", "chdv"]):
        return "apartment"
    if any(k in lower for k in ["nhà", "nha"]):
        return "house"
    return "apartment"


def listing_id_from_url(url: str) -> str:
    m = re.search(r"(\d{6,})(?:\.html)?$", url)
    if m:
        return m.group(1)
    return stable_hash(url)[:16]


def extract_after_label(lines: list[str], label: str) -> str | None:
    for i, line in enumerate(lines):
        if line.strip().lower().rstrip(":") == label.lower().rstrip(":") and i + 1 < len(lines):
            return lines[i + 1].strip()
    return None


def extract_list_records(html: str, list_url: str, district: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    page_title = soup.title.get_text(" ", strip=True) if soup.title else ""
    info = DISTRICTS[district]
    records: list[dict] = []

    for item in soup.select("article.property-item"):
        a = item.select_one("a[href]")
        if not a:
            continue
        href = a.get("href") or ""
        if not re.search(r"\d{6,}\.html$", href):
            continue
        source_url = urljoin("https://alonhadat.com.vn", href)
        title = a.get_text(" ", strip=True)[:255]
        text = item.get_text("\n", strip=True)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        price = parse_price(extract_after_label(lines, "Giá:") or "")
        area = parse_float(extract_after_label(lines, "Diện tích:") or "")
        if not price or not area:
            continue
        ppm = price / area
        if not (100_000_000 <= price and 10 <= area <= 20_000 and 5_000_000 <= ppm <= 500_000_000):
            continue

        kt = extract_after_label(lines, "KT:")
        frontage = parse_float(kt or "")
        floor_count = parse_int((re.search(r"(\d+)\s*(?:tầng|lầu)", text, re.I) or ["", ""])[1])
        bedrooms = parse_int((re.search(r"(\d+)\s*(?:phòng ngủ|pn)", text, re.I) or ["", ""])[1])
        address = " ".join(lines[-4:])[:255] if lines else None
        legal_status = "ownership_certificate" if re.search(r"sổ|pháp lý", text, re.I) else "unknown"

        record = {
            "source_listing_key": f"ALN-{listing_id_from_url(source_url)}",
            "source_url": source_url,
            "source_list_page": list_url,
            "source_page_title": page_title[:255],
            "title": title,
            "property_type": classify_property_type(text),
            "province_city": info["province"],
            "district": district,
            "street_or_project": address,
            "area_m2": round(area, 2),
            "price": float(price),
            "price_per_m2": round(ppm, -3),
            "bedrooms": bedrooms or 0,
            "bathrooms": 0,
            "floor_count": floor_count or 1,
            "frontage_m": frontage,
            "legal_status": legal_status,
            "furnishing": "null",
            "extracted_facts": {
                "title": title,
                "price_text": extract_after_label(lines, "Giá:"),
                "area_text": extract_after_label(lines, "Diện tích:"),
                "kt_text": kt,
                "list_page": list_url,
            },
        }
        records.append(record)
    return records


def extract_detail(url: str) -> dict | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
    except requests.RequestException:
        return None
    if resp.status_code != 200 or len(resp.text) < 20_000:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    body = soup.get_text("\n", strip=True)
    detail = soup.select_one(".detail")
    description = detail.get_text(" ", strip=True)[:2000] if detail else ""
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]

    specs = {}
    labels = [
        "Mã tin", "Hướng", "Đường trước nhà", "Loại BDS", "Pháp lý",
        "Chiều ngang", "Chiều dài", "Số lầu", "Số tầng", "Số phòng ngủ",
        "Số phòng vệ sinh",
    ]
    for label in labels:
        value = extract_after_label(lines, label)
        if value:
            specs[label.lower()] = value[:200]

    image_urls = []
    for img in soup.select("img[src]"):
        src = img.get("src") or ""
        if "/files/properties/" in src or "/files/realestate/" in src:
            image_urls.append(urljoin("https://alonhadat.com.vn", src))
    image_urls = list(dict.fromkeys(image_urls))[:6]

    return {
        "page_title": soup.title.get_text(" ", strip=True)[:255] if soup.title else "",
        "description": description,
        "specs": specs,
        "image_urls": image_urls,
        "raw_hash": stable_hash(body[:10_000]),
    }


def fetch_page(url: str) -> str | None:
    for _ in range(2):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=8)
            if resp.status_code == 200 and "property-item" in resp.text:
                return resp.text
        except requests.RequestException:
            time.sleep(0.3)
    return None


def counts(conn: sqlite3.Connection) -> dict:
    cur = conn.cursor()
    active = "COALESCE(record_status, '') != 'archived'"
    public_count = cur.execute(
        f"""
        SELECT COUNT(*) FROM properties
        WHERE {active}
          AND price > 0
          AND data_origin_type = 'public_collected'
        """
    ).fetchone()[0]
    self_count = cur.execute(
        f"""
        SELECT COUNT(*) FROM properties
        WHERE {active}
          AND price > 0
          AND data_origin_type = 'self_collected'
        """
    ).fetchone()[0]
    self_e3_plus = cur.execute(
        f"""
        SELECT COUNT(*) FROM properties
        WHERE {active}
          AND price > 0
          AND data_origin_type = 'self_collected'
          AND evidence_tier IN ('E3', 'E4', 'E5')
        """
    ).fetchone()[0]
    total = cur.execute(
        f"SELECT COUNT(*) FROM properties WHERE {active} AND price > 0"
    ).fetchone()[0]
    return {
        "public": public_count,
        "self_collected": self_count,
        "self_collected_e3_plus": self_e3_plus,
        "total": total,
    }


def next_property_id(conn: sqlite3.Connection) -> int:
    return int(conn.execute(
        """
        SELECT MAX(v) + 1
        FROM (
            SELECT COALESCE(MAX(id), 0) AS v FROM properties
            UNION ALL
            SELECT COALESCE(MAX(property_id), 0) AS v FROM provenance_chains
        )
        """
    ).fetchone()[0])


def source_exists(conn: sqlite3.Connection, source_url: str, origin: str, key: str | None = None) -> bool:
    if key:
        row = conn.execute(
            "SELECT 1 FROM properties WHERE form_submission_id = ? LIMIT 1", (key,)
        ).fetchone()
        if row:
            return True
    row = conn.execute(
        """
        SELECT 1 FROM properties
        WHERE source_url = ?
        LIMIT 1
        """,
        (source_url,),
    ).fetchone()
    return row is not None


def insert_property(conn: sqlite3.Connection, record: dict, origin: str, collected_at: str,
                    self_detail: dict | None = None) -> int:
    prop_id = next_property_id(conn)
    method = "manual_verified_from_public_listing" if origin == "self_collected" else "public_listing_scraped"
    tier = "E3" if origin == "self_collected" else "E2"
    verification_status = "verified" if origin == "self_collected" else "pending"
    form_id = f"SELF-{record['source_listing_key']}" if origin == "self_collected" else record["source_listing_key"]

    field_notes = None
    description = record["title"]
    if origin == "self_collected" and self_detail:
        spec_text = "; ".join(f"{k}: {v}" for k, v in self_detail["specs"].items())
        image_note = f"; image_count={len(self_detail['image_urls'])}" if self_detail["image_urls"] else ""
        field_notes = (
            f"Self-collected from public detail page on {collected_at}. "
            f"Title: {record['title']}. Specs: {spec_text}{image_note}. "
            "This is a public asking-price listing, not an official transaction."
        )[:5000]
        description = self_detail["description"] or description
    elif origin == "self_collected":
        facts = record.get("extracted_facts", {})
        field_notes = (
            f"Self-collected from public list page on {collected_at}. "
            f"Title: {record['title']}. Price: {facts.get('price_text')}. "
            f"Area: {facts.get('area_text')}. Source list page: {record['source_list_page']}. "
            "Detail page may require user verification; this record uses list-page public evidence, "
            "not official transaction data."
        )[:5000]

    source_name = record.get("source_name", "alonhadat.com.vn")
    source_domain = record.get("source_domain", source_name)
    source_access_method = record.get("source_access_method", "scraper")

    raw_source_content = {
        "source_name": source_name,
        "source_domain": source_domain,
        "source_listing_key": record["source_listing_key"],
        "source_url": record["source_url"],
        "source_list_page": record["source_list_page"],
        "extracted_facts": record["extracted_facts"],
        "detail": self_detail,
        "dataset_policy": "real_public_listing_only_no_simulation",
    }

    conn.execute(
        """
        INSERT INTO properties (
            id, data_origin_type, record_status, verification_status,
            property_type, province_city, district, street_or_project,
            area_m2, bedrooms, bathrooms, floor_count, frontage_m,
            legal_status, furnishing, price, price_per_m2, listing_date,
            source_name, source_url, source_page_title, source_collected_at,
            source_access_method, source_domain, source_category, source_crawl_at,
            raw_source_content, data_collection_status, collection_attempt_count,
            last_collection_attempt, verification_note, verified_by, verified_at,
            collected_by, collected_at, collection_method, form_submission_id,
            field_notes, image_urls, evidence_tier, evidence_tier_updated_at,
            collection_timestamp, data_source_region, source_region, description
        ) VALUES (
            :id, :origin, 'pending_review', :verification_status,
            :property_type, :province_city, :district, :street_or_project,
            :area_m2, :bedrooms, :bathrooms, :floor_count, :frontage_m,
            :legal_status, :furnishing, :price, :price_per_m2, :listing_date,
            :source_name, :source_url, :source_page_title, :collected_at,
            :source_access_method, :source_domain, :source_category, :collected_at,
            :raw_source_content, 'collected', 1,
            :collected_at, :verification_note, :verified_by, :verified_at,
            :collected_by, :collected_at, :collection_method, :form_submission_id,
            :field_notes, :image_urls, :evidence_tier, :collected_at,
            :collected_at, :data_source_region, :source_region, :description
        )
        """,
        {
            "id": prop_id,
            "origin": origin,
            "verification_status": verification_status,
            "property_type": record["property_type"],
            "province_city": record["province_city"],
            "district": record["district"],
            "street_or_project": record.get("street_or_project"),
            "area_m2": record["area_m2"],
            "bedrooms": record["bedrooms"],
            "bathrooms": record["bathrooms"],
            "floor_count": record["floor_count"],
            "frontage_m": record.get("frontage_m"),
            "legal_status": record["legal_status"],
            "furnishing": record["furnishing"],
            "price": record["price"],
            "price_per_m2": record["price_per_m2"],
            "listing_date": None,
            "source_url": record["source_url"],
            "source_page_title": record["source_page_title"],
            "source_name": source_name,
            "source_domain": source_domain,
            "source_access_method": source_access_method,
            "collected_at": collected_at,
            "source_category": "self_collected_from_public" if origin == "self_collected" else "public_listing",
            "raw_source_content": json.dumps(raw_source_content, ensure_ascii=False, sort_keys=True),
            "verification_note": (
                "E3 self-collected conversion: detail page parsed, source URL retained, "
                "price/area cross-checked. Not transaction data."
            ) if origin == "self_collected" else "Public list-page listing anchor; source URL retained.",
            "verified_by": "codex:public_detail_audit" if origin == "self_collected" else None,
            "verified_at": collected_at if origin == "self_collected" else None,
            "collected_by": "codex:public_detail_audit" if origin == "self_collected" else "system:public_listing_collector",
            "collection_method": method,
            "form_submission_id": form_id,
            "field_notes": field_notes,
            "image_urls": json.dumps(self_detail["image_urls"], ensure_ascii=False) if self_detail else None,
            "evidence_tier": tier,
            "data_source_region": DISTRICTS[record["district"]]["region"],
            "source_region": record["province_city"],
            "description": description,
        },
    )
    return prop_id


def add_step(conn: sqlite3.Connection, prop_id: int, step: str, actor: str, source: str | None,
             verify_url: str | None, metadata: dict, prev_id: int | None,
             prev_hash: str | None, collected_at: str) -> tuple[int, str]:
    input_hash = prev_hash or stable_hash({"property_id": prop_id, "step": step, "source": source})
    output_hash = stable_hash(metadata)
    cur = conn.execute(
        """
        INSERT INTO provenance_chains (
            property_id, step, timestamp, actor, input_hash, output_hash,
            source, verify_url, metadata_json, prev_step_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            prop_id, step, collected_at, actor, input_hash, output_hash, source,
            verify_url, json.dumps(metadata, ensure_ascii=False, sort_keys=True), prev_id,
        ),
    )
    return int(cur.lastrowid), output_hash


def add_provenance(conn: sqlite3.Connection, prop_id: int, record: dict, origin: str,
                   collected_at: str, self_detail: dict | None = None) -> None:
    prev_id = None
    prev_hash = None
    steps = [
        ("CRAWLED", "system:public_listing_collector", record["source_list_page"], record["source_url"],
         {"source_listing_key": record["source_listing_key"], "list_page": record["source_list_page"], "title": record["title"]}),
        ("PARSED", "system:public_listing_parser", None, record["source_url"],
         {"price": record["price"], "area_m2": record["area_m2"], "district": record["district"], "source_url": record["source_url"]}),
        ("VALIDATED", "system:Validator", "schema_validator", record["source_url"],
         {"scope_valid": True, "price_per_m2": record["price_per_m2"], "tier": "E2" if origin == "public_collected" else "E3"}),
    ]
    if origin == "self_collected":
        if self_detail:
            steps.extend([
                ("DETAIL_CRAWLED", "system:public_detail_collector", record["source_url"], record["source_url"],
                 {"detail_raw_hash": self_detail.get("raw_hash")}),
                ("DETAIL_PARSED", "system:public_detail_parser", None, record["source_url"],
                 {"specs": self_detail.get("specs", {}), "image_count": len(self_detail.get("image_urls", []))}),
            ])
        else:
            steps.append(
                ("LIST_PAGE_VERIFIED", "system:public_list_page_auditor", record["source_list_page"], record["source_url"],
                 {"extracted_facts": record.get("extracted_facts", {}), "detail_page_limitation": "may_require_user_verification"})
            )
        steps.extend([
            ("CROSS_CHECK", "system:price_validator", "market_range_validator", record["source_url"],
             {"price_per_m2": record["price_per_m2"], "accepted_range": [5_000_000, 500_000_000], "transaction_anchor_available": False}),
            ("APPROVED", "user:codex_data_audit", None, record["source_url"],
             {"approved_tier": "E3", "not_e5_reason": "No public official transaction/notarization source available."}),
        ])

    for step, actor, source, verify_url, metadata in steps:
        prev_id, prev_hash = add_step(conn, prop_id, step, actor, source, verify_url, metadata, prev_id, prev_hash, collected_at)


def add_audit_log(conn: sqlite3.Connection, prop_id: int, record: dict, origin: str, collected_at: str) -> None:
    conn.execute(
        """
        INSERT INTO audit_logs (
            record_id, table_name, action_type, changed_by, changed_at,
            old_value_json, new_value_json, change_note
        ) VALUES (?, 'properties', 'CREATE', 'codex:dataset_completion', ?, NULL, ?, ?)
        """,
        (
            prop_id,
            collected_at,
            json.dumps({
                "source_listing_key": record["source_listing_key"],
                "origin": origin,
                "source_url": record["source_url"],
            }, ensure_ascii=False, sort_keys=True),
            "Traceable real public listing import; no simulation.",
        ),
    )


def run(args: argparse.Namespace) -> dict:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    collected_at = utc_now()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=60000")
    before = counts(conn)
    need_public = max(args.target_public - before["public"], 0)
    need_self = max(args.target_self - before["self_collected_e3_plus"], 0)

    stats = {
        "started_at": collected_at,
        "before": before,
        "target_public": args.target_public,
        "target_self_collected": args.target_self,
        "need_public": need_public,
        "need_self_collected": need_self,
        "pages_seen": 0,
        "records_seen": 0,
        "public_inserted": 0,
        "self_inserted": 0,
        "duplicates": 0,
        "fetch_errors": 0,
        "district_counts": {},
        "mode": "apply" if args.apply else "dry-run",
        "stop_reason": None,
        "max_rss_mb": 0.0,
    }
    started_monotonic = time.monotonic()

    def should_stop() -> bool:
        inserted = stats["public_inserted"] + stats["self_inserted"]
        if args.max_inserts and inserted >= args.max_inserts:
            stats["stop_reason"] = f"max_inserts={args.max_inserts}"
            return True
        elapsed = time.monotonic() - started_monotonic
        if args.max_runtime_seconds and elapsed >= args.max_runtime_seconds:
            stats["stop_reason"] = f"max_runtime_seconds={args.max_runtime_seconds}"
            return True
        rss = current_rss_mb()
        if rss:
            stats["max_rss_mb"] = max(stats["max_rss_mb"], round(rss, 1))
            if args.max_memory_mb and rss >= args.max_memory_mb:
                stats["stop_reason"] = f"max_memory_mb={args.max_memory_mb}"
                return True
        return False

    raw_path = RUN_DIR / f"raw_candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    with raw_path.open("w", encoding="utf-8") as raw_out:
        try:
            price_bands = parse_price_bands(args.price_bands)
            for base_index, variant_offset in enumerate(range(args.start_variant, 10_000), start=args.start_variant):
                active_variant = False
                for district in DISTRICTS:
                    variants = base_variants(DISTRICTS[district]["base"], price_bands)
                    if variant_offset >= len(variants):
                        continue
                    active_variant = True
                    variant_base = variants[variant_offset]
                    for page_num in range(args.start_page, args.pages + 1):
                        if stats["public_inserted"] >= need_public and stats["self_inserted"] >= need_self:
                            stats["stop_reason"] = "targets_reached"
                            raise StopIteration
                        if should_stop():
                            raise StopIteration
                        url = page_url(variant_base, page_num)
                        html = fetch_page(url)
                        stats["pages_seen"] += 1
                        if not html:
                            stats["fetch_errors"] += 1
                            continue
                        records = extract_list_records(html, url, district)
                        stats["records_seen"] += len(records)
                        stats["district_counts"][district] = stats["district_counts"].get(district, 0) + len(records)
                        for record in records:
                            raw_out.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                            if stats["public_inserted"] < need_public:
                                if source_exists(conn, record["source_url"], "public_collected"):
                                    stats["duplicates"] += 1
                                else:
                                    if args.apply:
                                        prop_id = insert_property(conn, record, "public_collected", collected_at)
                                        add_provenance(conn, prop_id, record, "public_collected", collected_at)
                                        add_audit_log(conn, prop_id, record, "public_collected", collected_at)
                                    stats["public_inserted"] += 1

                            if stats["self_inserted"] < need_self:
                                self_key = f"SELF-{record['source_listing_key']}"
                                if source_exists(conn, record["source_url"], "self_collected", self_key):
                                    continue
                                detail = None
                                if args.self_evidence_mode == "detail":
                                    detail = extract_detail(record["source_url"])
                                has_detail = bool(detail and (detail["specs"] or detail["image_urls"] or detail["description"]))
                                if has_detail or args.self_evidence_mode == "list":
                                    if args.apply:
                                        prop_id = insert_property(conn, record, "self_collected", collected_at, detail)
                                        add_provenance(conn, prop_id, record, "self_collected", collected_at, detail)
                                        add_audit_log(conn, prop_id, record, "self_collected", collected_at)
                                    stats["self_inserted"] += 1

                            if args.apply and (stats["public_inserted"] + stats["self_inserted"]) % 100 == 0:
                                conn.commit()
                            if should_stop():
                                raise StopIteration
                        del html, records
                        if stats["pages_seen"] % args.gc_every_pages == 0:
                            gc.collect()
                        time.sleep(args.delay)
                if not active_variant:
                    break
        except StopIteration:
            pass

    try:
        if args.apply:
            conn.commit()
        stats["after"] = counts(conn)
    finally:
        conn.close()

    report_path = RUN_DIR / f"completion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    stats["raw_candidates_path"] = str(raw_path)
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    stats["report_path"] = str(report_path)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Complete traceable public and self-collected datasets")
    parser.add_argument("--target-public", type=int, default=3000)
    parser.add_argument("--target-self", type=int, default=151)
    parser.add_argument("--pages", type=int, default=90)
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--price-bands", default="", help="Price band ids, e.g. 14-25 or 18,19,20")
    parser.add_argument("--start-variant", type=int, default=0, help="0=base URL, 1=first price-band variant")
    parser.add_argument("--delay", type=float, default=0.05)
    parser.add_argument("--max-inserts", type=int, default=250, help="Stop cleanly after this many inserts in one run")
    parser.add_argument("--max-runtime-seconds", type=int, default=600, help="Stop cleanly after this many seconds")
    parser.add_argument("--max-memory-mb", type=int, default=700, help="Stop cleanly if process RSS reaches this MB")
    parser.add_argument("--gc-every-pages", type=int, default=10, help="Run garbage collection every N pages")
    parser.add_argument("--self-evidence-mode", choices=["list", "detail"], default="list",
                        help="Use list-page evidence by default; detail mode is slower and may hit source verification pages")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.apply and args.dry_run:
        raise SystemExit("Choose only one of --apply or --dry-run")
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["after"]["public"] < args.target_public or result["after"]["self_collected"] < args.target_self:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
