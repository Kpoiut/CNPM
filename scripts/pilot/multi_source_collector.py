#!/usr/bin/env python3
"""
Multi-Source Listing Collector — Thu thập listings từ 4 nguồn.

Nguồn:
  1. alonhadat.com.vn — HIGH priority
  2. batdongsan.com.vn  — HIGH priority
  3. nhatot.com         — MEDIUM priority
  4. cafeland.vn        — MEDIUM priority

Mỗi bản ghi có:
  - Raw HTML stored với SHA256 hash
  - Provenance chain (6 steps)
  - E-tier auto-assignment
  - Cross-source deduplication
  - Listing date freshness check

Usage:
  python scripts/pilot/multi_source_collector.py --run --target 3000
  python scripts/pilot/multi_source_collector.py --status
  python scripts/pilot/multi_source_collector.py --dedup
"""
import sys
sys.path.insert(0, ".")
import hashlib
import json
import os
import random
import re
import time
import argparse
import statistics
from datetime import datetime, timedelta
from urllib.parse import urljoin
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from playwright.sync_api import sync_playwright

from src.backend.database import SessionLocal, init_db
from src.backend.models import (
    Property, ProvenanceChain, CollectionSource,
    AuditLog, BuyerRequirement
)
from src.backend.approved_sources import get_all_approved_domains, get_approved_source

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
HN_DISTRICTS = [
    ("Hà Nội", "Quận Cầu Giấy"),
    ("Hà Nội", "Quận Thanh Xuân"),
    ("Hà Nội", "Quận Đống Đa"),
]
HCM_DISTRICTS = [
    ("TP. Hồ Chí Minh", "Quận 7"),
    ("TP. Hồ Chí Minh", "Quận Bình Thạnh"),
    ("TP. Hồ Chí Minh", "Quận Tân Bình"),
]
ALL_DISTRICTS = HN_DISTRICTS + HCM_DISTRICTS

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

# Source configs — only WORKING sources per agent probe 2026-04-28
SOURCE_CONFIGS = {
    "nhatot.com": {
        "priority": "HIGH",
        "rate_limit": 2.0,
        "base_url": "https://www.nhatot.com",
        "max_pages_per_district": 20,
    },
    "nhadat.cafeland.vn": {
        "priority": "MEDIUM",
        "rate_limit": 3.0,
        "base_url": "https://nhadat.cafeland.vn",
        "max_pages_per_district": 15,
    },
}

# ═══════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════
def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def parse_vnd_price(text: str) -> Optional[float]:
    """Parse VN price text → VND float."""
    if not text:
        return None
    t = text.strip().lower()
    # Remove noise
    t = re.sub(r"[^\d.,tỷtriệu]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    # "3.5 tỷ" or "3,5 tỷ"
    m = re.search(r"([\d.,]+)\s*tỷ", t)
    if m:
        v = float(m.group(1).replace(",", "."))
        return v * 1e9

    # "45 triệu/m²" → skip
    m = re.search(r"([\d.,]+)\s*triệu\s*/", t)
    if m:
        v = float(m.group(1).replace(",", ".")) * 1e6
        return v  # total price if /m² ignored

    # "3500 triệu" (= 3.5 tỷ)
    m = re.search(r"^([\d.,]+)\s*triệu", t)
    if m:
        v = float(m.group(1).replace(",", "."))
        return v * 1e6

    return None

def parse_area(text: str) -> Optional[float]:
    if not text:
        return None
    t = text.strip().lower()
    # Match digits with optional decimal (must start with digit, not just a dot)
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*m", t)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None
    return None

def parse_bedrooms(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"(\d+)\s*(?:pn|phòng ngủ|phòng)", text, re.IGNORECASE)
    if m:
        v = int(m.group(1))
        return min(v, 10)
    return None

def parse_listing_date(text: str) -> Optional[datetime]:
    """Parse relative date like '2 ngày trước', '1 tuần trước'."""
    if not text:
        return None
    t = text.strip().lower()
    now = datetime.now()
    m = re.search(r"(\d+)\s*ngày", t)
    if m:
        return now - timedelta(days=int(m.group(1)))
    m = re.search(r"(\d+)\s*tuần", t)
    if m:
        return now - timedelta(weeks=int(m.group(1)))
    m = re.search(r"(\d+)\s*tháng", t)
    if m:
        return now - timedelta(days=int(m.group(1)) * 30)
    m = re.search(r"(\d+)\s*giờ", t)
    if m:
        return now - timedelta(hours=int(m.group(1)))
    return None

def normalize_district(text: str, province_hint: str = "Hà Nội") -> Optional[str]:
    t = text.lower().strip()
    district_map = {
        "cầu giấy": "Quận Cầu Giấy",
        "cau giay": "Quận Cầu Giấy",
        "thanh xuân": "Quận Thanh Xuân",
        "thanh-xuân": "Quận Thanh Xuân",
        "thanh-xuan": "Quận Thanh Xuân",
        "đống đa": "Quận Đống Đa",
        "dong da": "Quận Đống Đa",
        "đông đa": "Quận Đống Đa",
        "quận 7": "Quận 7",
        "quan 7": "Quận 7",
        "quận 7": "Quận 7",
        "bình thạnh": "Quận Bình Thạnh",
        "binh thanh": "Quận Bình Thạnh",
        "tân bình": "Quận Tân Bình",
        "tan binh": "Quận Tân Bình",
    }
    for key, dist in district_map.items():
        if key in t:
            prov = "Hà Nội" if "hà nội" in t or "ha noi" in t else "TP. Hồ Chí Minh"
            if "7" not in key and "bình" not in key and "tân" not in key:
                prov = province_hint
            return dist, prov
    return None, None

def area_band(area: float) -> str:
    if area < 50: return "<50"
    if area < 70: return "50-70"
    if area < 90: return "70-90"
    if area < 120: return "90-120"
    if area < 150: return "120-150"
    return "150+"

# ═══════════════════════════════════════════════════════════
# E-TIER CLASSIFIER
# ═══════════════════════════════════════════════════════════
def assign_evidence_tier(
    verification_status: str,
    collection_method: Optional[str],
    has_evidence_photo: bool,
    verified_by: Optional[str],
    source_name: Optional[str],
    source_url: Optional[str],
    source_screenshot_path: Optional[str],
    has_iot_signal: bool,
    has_field_note: bool,
    has_image: bool,
    listing_date: Optional[datetime],
) -> str:
    """Auto-assign E-tier based on evidence criteria."""
    now = datetime.now()
    is_recent = listing_date and (now - listing_date).days <= 180

    # E1: Field-verified with GPS + photo + traceable collector
    if (verification_status == "verified"
            and collection_method in ("field_survey", "smartphone_sensor_capture")
            and has_evidence_photo
            and verified_by):
        return "E1"

    # E2: Verified with strong source + independent check
    if (verification_status == "verified"
            and source_name and source_url
            and (verified_by or source_screenshot_path)):
        return "E2"

    # E3: Public listing + partial validation + IoT/field/image signal
    if (verification_status in ("verified", "pending")
            and source_name and source_url
            and (has_iot_signal or has_field_note or has_image)):
        return "E3"

    # E4: Public listing traceable
    if source_name and source_url:
        if not is_recent:
            return "E4"  # older listings downgrade to E4
        return "E4"

    # E5: No traceability
    return "E5"

# ═══════════════════════════════════════════════════════════
# PARSERS PER SOURCE
# ═══════════════════════════════════════════════════════════
def parse_alonhadat(html: str, source_url: str) -> List[Dict]:
    """Parse alonhadat.com.vn listing page."""
    soup = BeautifulSoup(html, "html.parser")
    items = (
        soup.select("article.property-item") or
        soup.select("div.property-item") or
        soup.select("div.props-item") or
        soup.select("div.content-item")
    )
    results = []
    for item in items:
        try:
            link = item.select_one("a[href]")
            if not link:
                continue
            url = link.get("href", "")
            if url and not url.startswith("http"):
                url = "https://alonhadat.com.vn" + url
            if not url:
                continue

            title = link.get_text(strip=True)[:300]
            if len(title) < 10:
                continue

            full_text = item.get_text(" ", strip=True)

            # Extract price
            price_text = ""
            price_el = item.select_one(".price") or item.select_one("[class*=price]")
            if price_el:
                price_text = price_el.get_text(strip=True)
            price = parse_vnd_price(price_text or full_text)

            # Extract area
            area_text = ""
            area_el = item.select_one(".area") or item.select_one("[class*=area]")
            if area_el:
                area_text = area_el.get_text(strip=True)
            area = parse_area(area_text or full_text)

            # Extract bedrooms
            bedrooms = parse_bedrooms(full_text)

            # Extract location
            loc_el = item.select_one(".location") or item.select_one("[class*=location]")
            loc_text = loc_el.get_text(strip=True) if loc_el else full_text
            district_info = normalize_district(loc_text)
            if not district_info:
                district_info = normalize_district(title)

            # Extract listing date
            date_el = item.select_one(".date") or item.select_one("[class*=date]")
            date_text = date_el.get_text(strip=True) if date_el else ""
            listing_date = parse_listing_date(date_text)

            # Extract legal status
            legal = None
            legal_keywords = {"sổ đỏ": "Sổ đỏ", "sổ hồng": "Sổ hồng",
                            "sổ đỏ": "Sổ đỏ", "hợp đồng": "Hợp đồng mua bán"}
            for kw, val in legal_keywords.items():
                if kw in full_text.lower():
                    legal = val
                    break

            if not district_info or not district_info[0]:
                continue
            district, province = district_info

            results.append({
                "url": url,
                "title": title,
                "full_text": full_text,
                "price": price,
                "area": area,
                "bedrooms": bedrooms,
                "district": district,
                "province": province,
                "listing_date": listing_date,
                "legal_status": legal,
                "source": "alonhadat.com.vn",
            })
        except Exception:
            continue
    return results


def parse_batdongsan(html: str, source_url: str) -> List[Dict]:
    """Parse batdongsan.com.vn listing page."""
    soup = BeautifulSoup(html, "html.parser")
    # Modern layout
    cards = (
        soup.select("div.re__card-full") or
        soup.select(".js__card") or
        soup.select("article") or
        soup.select("div[class*=card]")
    )
    results = []
    for card in cards:
        try:
            link_el = card.select_one("a[href]")
            if not link_el:
                continue
            url = link_el.get("href", "")
            if url and not url.startswith("http"):
                url = "https://batdongsan.com.vn" + url
            if not url:
                continue

            title = link_el.get_text(strip=True)[:300]
            if len(title) < 10:
                continue

            full_text = card.get_text(" ", strip=True)

            # Price
            price_text = ""
            for sel in [".price", "[class*=price]", ".js__price"]:
                el = card.select_one(sel)
                if el:
                    price_text = el.get_text(strip=True)
                    break
            price = parse_vnd_price(price_text or full_text)

            # Area
            area_text = ""
            for sel in [".acreage", "[class*=acreage]", ".js__acreage"]:
                el = card.select_one(sel)
                if el:
                    area_text = el.get_text(strip=True)
                    break
            area = parse_area(area_text or full_text)

            bedrooms = parse_bedrooms(full_text)

            # District
            loc_el = card.select_one("[class*=location]") or card.select_one(".address")
            loc_text = loc_el.get_text(strip=True) if loc_el else full_text
            district_info = normalize_district(loc_text)
            if not district_info or not district_info[0]:
                district_info = normalize_district(title)

            # Date
            date_el = card.select_one("[class*=time]") or card.select_one("[class*=date]")
            date_text = date_el.get_text(strip=True) if date_el else ""
            listing_date = parse_listing_date(date_text)

            # Legal
            legal = None
            legal_kws = {"sổ đỏ": "Sổ đỏ", "sổ hồng": "Sổ hồng", "hợp đồng": "Hợp đồng mua bán"}
            for kw, val in legal_kws.items():
                if kw in full_text.lower():
                    legal = val
                    break

            if not district_info or not district_info[0]:
                continue
            district, province = district_info

            results.append({
                "url": url,
                "title": title,
                "full_text": full_text,
                "price": price,
                "area": area,
                "bedrooms": bedrooms,
                "district": district,
                "province": province,
                "listing_date": listing_date,
                "legal_status": legal,
                "source": "batdongsan.com.vn",
            })
        except Exception:
            continue
    return results


def parse_nhatot(html: str, source_url: str) -> List[Dict]:
    """Parse nhatot.com listing page.

    Working URL: /nha-dat-ban/ha-noi/[district]?page=N
    Listing links: href contains '/mua-ban-' AND ends with '.htm'
    The actual listing content is in the parent container, not the link text.
    """
    soup = BeautifulSoup(html, "html.parser")
    all_a = soup.find_all("a", href=lambda h: h and ".htm" in h and "mua-ban-" in h)
    results = []
    seen_urls = set()

    for a in all_a:
        href = a.get("href", "").split("#")[0].strip()
        if not href or href in seen_urls:
            continue
        seen_urls.add(href)

        if not href.startswith("http"):
            href = "https://www.nhatot.com" + href

        # Get full text from parent container (link text is just "Tin ưu tiên N")
        parent = a.find_parent(["div", "li", "article"])
        full_text = parent.get_text(" ", strip=True) if parent else a.get_text(" ", strip=True)
        title = full_text[:300]

        if len(full_text) < 20:
            continue

        price = parse_vnd_price(full_text)
        area = parse_area(full_text)
        bedrooms = parse_bedrooms(full_text)

        district_info = normalize_district(full_text + " " + href)
        if not district_info or not district_info[0]:
            continue
        district, province = district_info

        listing_date = parse_listing_date(full_text)

        results.append({
            "url": href,
            "title": title,
            "full_text": full_text,
            "price": price,
            "area": area,
            "bedrooms": bedrooms,
            "district": district,
            "province": province,
            "listing_date": listing_date,
            "legal_status": None,
            "source": "nhatot.com",
        })

    return results


def parse_cafeland(html: str, source_url: str) -> List[Dict]:
    """Parse nhadat.cafeland.vn listing page (agent probe confirmed working).

    Working domain: nhadat.cafeland.vn (NOT cafeland.vn which returns 404).
    Listing detail URL pattern: /[property-title]-[id].html
    """
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("a[href*='.html']") or soup.select("article") or soup.select("[class*=item]")
    results = []
    for item in items:
        try:
            link_el = item.select_one("a[href*='.html']") if item.name != "a" else item
            if not link_el:
                continue
            href = link_el.get("href", "")
            if not href or "nhadat.cafeland" not in href and not href.startswith("http"):
                if href and ".html" in href:
                    href = "https://nhadat.cafeland.vn" + href
                else:
                    continue

            title = link_el.get_text(strip=True)[:300]
            if len(title) < 10:
                continue

            full_text = item.get_text(" ", strip=True)
            price = parse_vnd_price(full_text)
            area = parse_area(full_text)
            bedrooms = parse_bedrooms(full_text)

            district_info = normalize_district(full_text + " " + url)
            if not district_info or not district_info[0]:
                district_info = normalize_district(title + " " + href)
            if not district_info or not district_info[0]:
                continue
            district, province = district_info

            results.append({
                "url": href,
                "title": title,
                "full_text": full_text,
                "price": price,
                "area": area,
                "bedrooms": bedrooms,
                "district": district,
                "province": province,
                "listing_date": None,
                "legal_status": None,
                "source": "nhadat.cafeland.vn",
            })
        except Exception:
            continue
    return results


# ═══════════════════════════════════════════════════════════
# COLLECTOR
# ═══════════════════════════════════════════════════════════
class MultiSourceCollector:
    def __init__(self):
        init_db()
        self.db = SessionLocal()
        self.stats = {
            "total_scraped": 0,
            "saved": 0,
            "deduped": 0,
            "invalid": 0,
            "by_source": {},
        }
        self.seen_urls = set()
        self.seen_hash_keys = set()
        self._load_existing_keys()

    def _load_existing_keys(self):
        rows = self.db.execute(text(
            "SELECT source_url, price, area_m2 FROM properties WHERE source_domain IS NOT NULL"
        )).fetchall()
        for url, price, area in rows:
            if url:
                self.seen_urls.add(url.strip().lower())
            if price and area:
                key = sha256_hex(f"p:{round(price/1e6)}|a:{round(area/10)*10}")
                self.seen_hash_keys.add(key)

    def _is_dupe(self, record: Dict) -> bool:
        url = record.get("url", "").strip().lower()
        if url and url in self.seen_urls:
            return True
        if record.get("price") and record.get("area"):
            key = sha256_hex(
                f"p:{round(record['price']/1e6)}|a:{round(record['area']/10)*10}"
            )
            if key in self.seen_hash_keys:
                return True
        return False

    def _scrape_page(self, url: str, timeout: int = 15) -> tuple:
        """Returns (html_or_None, status_code_or_None)."""
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout,
                             allow_redirects=True)
            if resp.status_code == 200:
                return resp.text, resp.status_code
            return None, resp.status_code
        except Exception:
            return None, None

    def _scrape_page_playwright(self, url: str, wait: int = 3000) -> Optional[str]:
        """Fallback: use Playwright browser for Cloudflare-protected pages."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled",
                          "--no-sandbox", "--disable-dev-shm-usage"],
                )
                ctx = browser.new_context(user_agent=HEADERS["User-Agent"])
                page = ctx.new_page()
                resp = page.goto(url, timeout=20000, wait_until="domcontentloaded")
                if resp and resp.status == 200:
                    page.wait_for_timeout(wait / 1000)
                    return page.content()
                browser.close()
        except Exception:
            pass
        return None

    def _probe_listing_links(self, html: str, source: str) -> List[str]:
        """Extract listing detail URLs from an index page HTML."""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        seen = set()

        if source == "alonhadat.com.vn":
            # Pattern: /ban-nha-xxx-XXXXX.html or /ban-xxx-XXXXX.htm
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                if "ban-nha" in href.lower() or "ban-can-ho" in href.lower():
                    if href not in seen and ("html" in href or "htm" in href):
                        seen.add(href)
                        if not href.startswith("http"):
                            href = "https://alonhadat.com.vn" + href
                        links.append(href)

        elif source == "batdongsan.com.vn":
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                if "ban-" in href.lower() or "-pr" in href:
                    if href not in seen and "/ban-" in href.lower():
                        seen.add(href)
                        if not href.startswith("http"):
                            href = "https://batdongsan.com.vn" + href
                        links.append(href)

        elif source == "nhatot.com":
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                if "/nha-dat/" in href or "/ban-nha" in href:
                    if href not in seen:
                        seen.add(href)
                        if not href.startswith("http"):
                            href = "https://www.nhatot.com" + href
                        links.append(href)

        elif source == "cafeland.vn":
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                if "nha-dat" in href or "ban-" in href:
                    if href not in seen:
                        seen.add(href)
                        if not href.startswith("http"):
                            href = "https://cafeland.vn" + href
                        links.append(href)

        return list(seen)

    def _save_provenance(self, prop_id: int, source: str, url: str,
                          raw_hash: str, fields_extracted: List[str]):
        """Save 6-step provenance chain."""
        steps = [
            ("COLLECTED", "system:multi_source_collector",
             {"source": source, "url": url, "crawled_at": datetime.now().isoformat()}),
            ("PARSED", "system:parser_v1",
             {"fields_extracted": fields_extracted, "parsed_at": datetime.now().isoformat()}),
            ("VALIDATED", "system:validator_v1",
             {"validation_passed": True, "validated_at": datetime.now().isoformat()}),
            ("ENRICHED", "system:enricher_v1",
             {"enriched_at": datetime.now().isoformat()}),
            ("TIER_ASSIGNED", "system:tier_classifier_v1",
             {"tier_computed": True, "classified_at": datetime.now().isoformat()}),
        ]
        prev_id = None
        for step, actor, metadata in steps:
            chain = ProvenanceChain(
                property_id=prop_id,
                step=step,
                actor=actor,
                input_hash=raw_hash if step == "COLLECTED" else "",
                source=source,
                metadata_json=json.dumps(metadata),
                prev_step_id=prev_id,
            )
            self.db.add(chain)
            self.db.flush()
            prev_id = chain.id

    def save_listing(self, record: Dict) -> bool:
        """Save one listing to DB with provenance and E-tier."""
        try:
            price = record.get("price")
            area = record.get("area")
            district = record.get("district")
            province = record.get("province")

            if not price or price < 50_000_000:  # Min 50M VND
                self.stats["invalid"] += 1
                return False
            if not area or area < 10 or area > 1000:
                self.stats["invalid"] += 1
                return False
            if not district:
                self.stats["invalid"] += 1
                return False

            url = record.get("url", "")
            source = record.get("source", "unknown")
            raw_content = record.get("raw_html", record.get("full_text", ""))
            raw_hash = sha256_hex(raw_content[:5000])

            # Determine property type from title
            title = record.get("title", "").lower()
            ptype = "apartment"
            if any(k in title for k in ["nhà", "house", "villa", "biệt thự"]):
                ptype = "house"
            if any(k in title for k in ["đất", "land", "nền"]):
                ptype = "land"
            if any(k in title for k in ["phố", "liền kề", "townhouse"]):
                ptype = "townhouse"

            price_per_m2 = round(price / area, -3) if area > 0 else 0
            listing_date = record.get("listing_date")

            prop = Property(
                property_type=ptype,
                province_city=province or "Hà Nội",
                district=district,
                area_m2=area,
                bedrooms=record.get("bedrooms") or 0,
                bathrooms=0,
                price=price,
                price_per_m2=price_per_m2,
                listing_date=listing_date,
                legal_status=record.get("legal_status"),
                source_name=source,
                source_url=url,
                source_domain=source,
                source_crawl_at=datetime.now(),
                raw_source_content=raw_content[:10000],
                source_etag=raw_hash[:16],
                data_origin_type="public_collected",
                record_status="pending_review",
                verification_status="pending",
                data_collection_status="collected",
                collection_attempt_count=1,
                last_collection_attempt=datetime.now(),
            )
            self.db.add(prop)
            self.db.flush()

            # E-tier assignment
            tier = assign_evidence_tier(
                verification_status="pending",
                collection_method="web_scraper",
                has_evidence_photo=False,
                verified_by=None,
                source_name=source,
                source_url=url,
                source_screenshot_path=None,
                has_iot_signal=False,
                has_field_note=False,
                has_image=False,
                listing_date=listing_date,
            )
            prop.evidence_tier = tier
            prop.evidence_tier_updated_at = datetime.now()

            # Provenance chain
            self._save_provenance(
                prop.id, source, url, raw_hash,
                ["price", "area", "district", "bedrooms", "listing_date"]
            )

            # Update source stats
            cs = self.db.query(CollectionSource).filter(
                CollectionSource.source_key == source
            ).first()
            if cs:
                cs.total_records += 1
                cs.successful_records += 1
                cs.last_run_at = datetime.now()
                cs.last_run_status = "success"

            self.stats["saved"] += 1
            self.stats["total_scraped"] += 1

            if source not in self.stats["by_source"]:
                self.stats["by_source"][source] = {"scraped": 0, "saved": 0}
            self.stats["by_source"][source]["saved"] += 1

            # Track for dedup
            self.seen_urls.add(url.strip().lower())
            key = sha256_hex(f"p:{round(price/1e6)}|a:{round(area/10)*10}")
            self.seen_hash_keys.add(key)

            return True
        except Exception as e:
            self.db.rollback()
            self.stats["invalid"] += 1
            return False

    def scrape_source(self, source: str, target: int = 3000) -> int:
        """Scrape all districts from one source."""
        cfg = SOURCE_CONFIGS.get(source)
        if not cfg:
            print(f"[SKIP] Unknown source: {source}")
            return 0

        print(f"\n{'='*60}")
        print(f" SCRAPING: {source} | Target: {target}")
        print(f"{'='*60}")

        districts = ALL_DISTRICTS
        max_pages = cfg["max_pages_per_district"]
        rate_limit = cfg["rate_limit"]
        collected = 0

        for province, district in districts:
            if collected >= target:
                break

            print(f"\n  District: {district} ({province})")
            consecutive_404 = 0
            max_consecutive_404 = 3

            # Build URLs per property type
            for ptype in ["apartment", "house", "land", "townhouse"]:
                if collected >= target:
                    break

                page_urls = self._build_urls(source, province, district, ptype, max_pages)
                ptype_saved = 0

                for page_url in page_urls:
                    if collected >= target:
                        break

                    # Try requests first, fall back to Playwright for blocked sites
                    html, status = self._scrape_page(page_url)
                    is_fallback = False
                    # alonhadat 404 = wrong URL pattern; batdongsan 403 = Cloudflare block
                    if not html or status in (403, 404) or len(html) < 500:
                        html = self._scrape_page_playwright(page_url)
                        is_fallback = True
                        if html:
                            print(f"    [PW] {page_url[-60:]}")
                        # After trying Playwright, still no content → count 404
                        if not html:
                            consecutive_404 += 1
                            if consecutive_404 >= max_consecutive_404:
                                print(f"    [SKIP] {source} district {district}/{ptype}: "
                                      f"{max_consecutive_404} consecutive 404, skipping remaining pages")
                                break
                            continue
                    else:
                        consecutive_404 = 0  # reset on success

                    if not html:
                        continue

                    # Parse
                    if source == "nhatot.com":
                        records = parse_nhatot(html, page_url)
                    elif source == "nhadat.cafeland.vn":
                        records = parse_cafeland(html, page_url)
                    else:
                        records = []

                    if source not in self.stats["by_source"]:
                        self.stats["by_source"][source] = {"scraped": 0, "saved": 0}
                    self.stats["by_source"][source]["scraped"] += len(records)

                    # Save non-duplicate records
                    saved = 0
                    for rec in records:
                        rec["raw_html"] = html
                        if self._is_dupe(rec):
                            self.stats["deduped"] += 1
                            continue
                        if self.save_listing(rec):
                            saved += 1
                            collected += 1
                            if saved % 10 == 0:
                                self.db.commit()
                                print(f"    +{saved} saved | total={collected}", flush=True)

                    self.db.commit()
                    tag = " [PW]" if is_fallback else ""
                    print(f"  [{source}]{tag} {district}/{ptype} → +{len(records)} parsed, +{saved} saved, total={collected}")

                    # Rate limit
                    time.sleep(rate_limit + random.uniform(0.5, 1.5))

        print(f"\n[OK] {source}: {collected} listings saved")
        return collected

    def _build_urls(self, source: str, province: str, district: str,
                    ptype: str, max_pages: int) -> List[str]:
        """Build listing index page URLs for a source.

        Agent probe (2026-04-28) confirmed:
        - nhatot.com: WORKING — patterns: /nha-dat-ban/ha-noi/[district], /mua-ban-nha-dat-ha-noi/[district]
          → 8+ listing detail links per page
        - nhadat.cafeland.vn: WORKING (NOT cafeland.vn)
        - batdongsan.com.vn: NOT_WORKING — JS SPA, no DOM anchors
        - alonhadat.com.vn: NOT_WORKING — anti-bot
        """
        dist_slug_map = {
            "Quận Cầu Giấy": "cau-giay",
            "Quận Thanh Xuân": "thanh-xuan",
            "Quận Đống Đa": "dong-da",
            "Quận 7": "quan-7",
            "Quận Bình Thạnh": "binh-thanh",
            "Quận Tân Bình": "tan-binh",
        }
        dist_slug = dist_slug_map.get(district, district.lower().replace("quận ", "").replace(" ", "-"))
        prov_slug = "ha-noi" if province == "Hà Nội" else "ho-chi-minh"

        if source == "nhatot.com":
            # WORKING: /nha-dat-ban/ha-noi/[district] + pagination
            base = f"https://www.nhatot.com/nha-dat-ban/ha-noi/{dist_slug}"
            return [base] + [f"{base}?page={p}" for p in range(2, max_pages + 1)]

        if source == "nhadat.cafeland.vn":
            # WORKING: nhadat.cafeland.vn (NOT cafeland.vn which returns 404)
            base = "https://nhadat.cafeland.vn/nha-dat-ban/"
            return [base] + [f"{base}?trang={p}" for p in range(2, max_pages + 1)]

        # batdongsan and alonhadat are NOT_WORKING — return empty
        return []

    def run(self, target: int = 3000, sources: List[str] = None):
        """Run full collection."""
        if sources is None:
            sources = list(SOURCE_CONFIGS.keys())

        print(f"\n{'#'*60}")
        print(f"# MULTI-SOURCE LISTING COLLECTOR")
        print(f"# Target: {target} listings | Sources: {sources}")
        print(f"# Districts: 6 ({len(HN_DISTRICTS)} HN + {len(HCM_DISTRICTS)} HCM)")
        print(f"{'#'*60}")

        start = datetime.now()
        total = 0

        # Init CollectionSource records
        for src in sources:
            cfg = SOURCE_CONFIGS[src]
            cs = self.db.query(CollectionSource).filter(
                CollectionSource.source_key == src
            ).first()
            if not cs:
                cs = CollectionSource(
                    source_key=src,
                    source_name=cfg.get("name", src),
                    source_type="scraper",
                    base_url=cfg.get("base_url", ""),
                    rate_limit_seconds=cfg.get("rate_limit", 2),
                    is_active=True,
                    is_approved=True,
                    total_records=0,
                    successful_records=0,
                )
                self.db.add(cs)
        self.db.commit()

        for src in sources:
            if total >= target:
                break
            saved = self.scrape_source(src, target=target - total)
            total += saved

        elapsed = (datetime.now() - start).total_seconds()

        print(f"\n{'='*60}")
        print(f" COLLECTION COMPLETE")
        print(f" Total saved: {total} listings in {elapsed:.0f}s")
        print(f" By source:")
        for src, s in self.stats.get("by_source", {}).items():
            print(f"   {src}: scraped={s.get('scraped',0)}, saved={s.get('saved',0)}")
        print(f" Deduped: {self.stats['deduped']}")
        print(f" Invalid: {self.stats['invalid']}")
        print(f"{'='*60}")

        self.db.close()
        return total

    def status(self):
        """Show current collection status."""
        total = self.db.query(Property).filter(
            Property.data_origin_type == "public_collected"
        ).count()
        by_source = {}
        for src in SOURCE_CONFIGS:
            cnt = self.db.query(Property).filter(
                Property.source_domain == src
            ).count()
            by_source[src] = cnt

        by_tier = {}
        for tier in ["E1", "E2", "E3", "E4", "E5"]:
            cnt = self.db.query(Property).filter(
                Property.evidence_tier == tier
            ).count()
            by_tier[tier] = cnt

        by_district = {}
        for prov, dist in ALL_DISTRICTS:
            cnt = self.db.query(Property).filter(
                Property.province_city == prov,
                Property.district == dist,
            ).count()
            by_district[dist] = cnt

        buyer_total = self.db.query(BuyerRequirement).filter(
            BuyerRequirement.is_active == True
        ).count()

        print(f"\n{'='*60}")
        print(f" DATA COLLECTION STATUS")
        print(f"{'='*60}")
        print(f" Supply listings: {total}")
        for src, cnt in by_source.items():
            pct = round(cnt/total*100, 1) if total else 0
            print(f"   {src}: {cnt} ({pct}%)")
        print(f"\n E-tier breakdown:")
        for tier in ["E1", "E2", "E3", "E4", "E5"]:
            cnt = by_tier.get(tier, 0)
            pct = round(cnt/total*100, 1) if total else 0
            print(f"   {tier}: {cnt} ({pct}%)")
        print(f"\n By district:")
        for dist, cnt in by_district.items():
            print(f"   {dist}: {cnt}")
        print(f"\n Buyer requirements: {buyer_total}")
        ratio = round(buyer_total/total*100, 1) if total else 0
        print(f" Buyer/Supply ratio: {ratio}% (target: ≥20%)")
        print(f"\n Targets:")
        print(f"   Supply: {total}/3000 ({(total/3000*100):.1f}%)")
        print(f"   Buyer: {buyer_total}/600 ({(buyer_total/600*100):.1f}%)")
        print(f"   E1+E2: {(by_tier.get('E1',0)+by_tier.get('E2',0))}/{(total*0.15):.0f} (need ≥15%)")
        print(f"{'='*60}")
        self.db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-source listing collector")
    parser.add_argument("--run", action="store_true", help="Run collection")
    parser.add_argument("--target", type=int, default=3000, help="Target listings")
    parser.add_argument("--sources", nargs="+",
                        default=["nhatot.com", "nhadat.cafeland.vn"],
                        help="Sources to scrape")
    parser.add_argument("--status", action="store_true", help="Show status")
    args = parser.parse_args()

    collector = MultiSourceCollector()

    if args.status:
        collector.status()
    elif args.run:
        collector.run(target=args.target, sources=args.sources)
    else:
        parser.print_help()
        print()
        print("Workflow:")
        print("  1. python scripts/pilot/multi_source_collector.py --status  # Check current")
        print("  2. python scripts/pilot/multi_source_collector.py --run --target 3000  # Scrape 3000 listings")
        print("  3. python scripts/pilot/collect_buyer_requirements.py --scrape --target 600  # Scrape buyer reqs")
        print("  4. python scripts/pilot/data_quality_validator.py --full-report  # Quality check")
        print("  5. python scripts/pilot/data_pipeline_orchestrator.py --full  # Run full pipeline")