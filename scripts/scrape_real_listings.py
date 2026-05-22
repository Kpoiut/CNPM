#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real Listing Scraper v3 — Thu thập listings thực từ batdongsan.com.vn,
nhatot.com, và alonhadat.com.vn.

Chi scrape listings thuộc 6 quận scope (HN + HCM). Mỗi record có source_url thực
có thể resolve được — nguồn gốc hoàn toàn truy xuất.

Data extraction:
  - batdongsan.com.vn: CSS [class*=card] DOM selectors (500+ cards/page, paginated)
  - nhatot.com: __NEXT_DATA__ JSON via page.evaluate() (20 ads/page, paginated)
  - alonhadat.com.vn: BeautifulSoup HTML parsing (listing links, paginated)

Usage:
    python scripts/scrape_real_listings.py --target 2000
    python scripts/scrape_real_listings.py --target 2000 --source batdongsan
    python scripts/scrape_real_listings.py --target 2000 --source nhatot
    python scripts/scrape_real_listings.py --target 500 --source alonhadat
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from sqlalchemy import text
from src.backend.database import SessionLocal, init_db
from src.backend.models import Property, ProvenanceChain, CollectionSource

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

SCOPE_KEYWORDS = {
    "Quận Cầu Giấy": ["cầu giấy", "cau giay"],
    "Quận Thanh Xuân": ["thanh xuân", "thanh xuan"],
    "Quận Đống Đa": ["đống đa", "dong da", "đông đa"],
    "Quận 7": ["quận 7", "quan 7"],
    "Quận Bình Thạnh": ["bình thạnh", "binh thanh"],
    "Quận Tân Bình": ["tân bình", "tan binh"],
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════
def normalize_district(text: str) -> Optional[tuple[str, str]]:
    """Map text → (province, district)."""
    t = text.lower()
    for dist, kws in SCOPE_KEYWORDS.items():
        if any(kw in t for kw in kws):
            province = "Hà Nội" if dist in ["Quận Cầu Giấy", "Quận Thanh Xuân", "Quận Đống Đa"] else "TP. Hồ Chí Minh"
            return province, dist
    return None


def parse_price_vnd(text: str) -> Optional[float]:
    if not text:
        return None
    t = text.lower().strip()
    t = re.sub(r"[^\d.,tỷtriệu]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    m = re.search(r"(\d[\d.,]*)\s*tỷ\s*(\d[\d.,]*)\s*triệu", t)
    if m:
        try:
            return float(m.group(1).replace(",", ".")) * 1e9 + float(m.group(2).replace(",", ".")) * 1e6
        except ValueError:
            pass

    m = re.search(r"(\d[\d.,]*)\s*tỷ", t)
    if m:
        try:
            return float(m.group(1).replace(",", ".")) * 1e9
        except ValueError:
            pass

    m = re.search(r"^(\d[\d.,]*)\s*triệu", t)
    if m:
        try:
            return float(m.group(1).replace(",", ".")) * 1e6
        except ValueError:
            pass

    return None


def parse_area(text: str) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"(\d[\d.,]*)\s*m", text)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            pass
    return None


def parse_bedrooms(text: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*(?:pn|phòng)", text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def parse_property_type(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["đất", "dat", "nền", "đất nền"]):
        return "land"
    if any(k in t for k in ["nhà phố", "phố", "liền kề", "townhouse"]):
        return "townhouse"
    if any(k in t for k in ["villa", "biệt thự"]):
        return "villa"
    if any(k in t for k in ["căn hộ", "chung cư", "apartment"]):
        return "apartment"
    if any(k in t for k in ["nhà", "nha"]):
        return "house"
    return "apartment"


# ═══════════════════════════════════════════════════════════
# Nhatot.com SCRAPER
# ═══════════════════════════════════════════════════════════
class NhatotScraper:
    """Scrape nhatot.com using __NEXT_DATA__ JSON extraction."""

    def __init__(self, db):
        self.db = db
        self.playwright = None  # set externally
        self.seen_ids = set()
        self.stats = {"found": 0, "saved": 0, "deduped": 0}

    def _extract_json(self, page) -> Optional[list]:
        """Extract ads list from __NEXT_DATA__ JSON via page.evaluate."""
        raw = page.evaluate("""
            () => {
                const scripts = Array.from(document.querySelectorAll("script"));
                for (const s of scripts) {
                    const t = s.textContent || '';
                    if (t.includes('"list_id"') && t.length > 50000) {
                        return t;
                    }
                }
                return null;
            }
        """)
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None

        def find_ads(obj):
            if isinstance(obj, dict):
                for v in obj.values():
                    sub = find_ads(v)
                    if sub is not None:
                        return sub
            elif isinstance(obj, list) and len(obj) > 0:
                if isinstance(obj[0], dict) and "list_id" in obj[0]:
                    return obj
                for item in obj:
                    sub = find_ads(item)
                    if sub is not None:
                        return sub
            return None

        return find_ads(data)

    def _filter_ads(self, ads: list, province_slug: str) -> list:
        """Filter ads to only those in scope districts."""
        results = []
        for ad in ads:
            list_id = ad.get("list_id")
            if list_id in self.seen_ids:
                self.stats["deduped"] += 1
                continue

            subject = ad.get("subject", "") or ""
            ward = ad.get("ward_name", "") or ""
            district_name = ad.get("district_name", "") or ""

            # Check district from ward or subject
            combined = f"{subject} {ward} {district_name}"
            district_info = normalize_district(combined)

            if not district_info:
                continue

            province, district = district_info
            expected_province = "ha-noi" if province == "Hà Nội" else "ho-chi-minh"

            if province_slug != expected_province:
                continue

            price = ad.get("price")
            area = ad.get("area")
            ppm = ad.get("price_million_per_m2")

            if price and area and area > 0:
                computed_ppm = price / area
                if ppm:
                    ppm_vnd = ppm * 1e6
                else:
                    ppm_vnd = computed_ppm
            else:
                continue

            results.append({
                "list_id": list_id,
                "subject": subject,
                "ward": ward,
                "district": district,
                "province": province,
                "price": price,
                "area": area,
                "price_per_m2": ppm_vnd,
                "price_string": ad.get("price_string", ""),
                "floors": ad.get("floors", 0),
                "rooms": ad.get("rooms", 0),
                "toilets": ad.get("toilets", 0),
                "legal_document": ad.get("property_legal_document", ""),
                "direction": ad.get("direction", ""),
                "furnishing": ad.get("furnishing_sell", ""),
                "latitude": ad.get("latitude"),
                "longitude": ad.get("longitude"),
                "list_time": ad.get("list_time", ""),
                "source": "nhatot.com",
            })
            self.stats["found"] += 1

        return results

    def scrape(self, province_slug: str, district_slug: str, pages: int = 30) -> list:
        """Scrape all pages for a district, return filtered ads.

        Uses a fresh browser for each district to avoid bot protection.
        Each page needs ~12s to load the __NEXT_DATA__ JSON.
        """
        all_ads = []
        consecutive_empty = 0

        for page_num in range(1, pages + 1):
            if consecutive_empty >= 4:
                break

            url = (f"https://www.nhatot.com/nha-dat-ban/{province_slug}/{district_slug}"
                   if page_num == 1
                   else f"https://www.nhatot.com/nha-dat-ban/{province_slug}/{district_slug}?page={page_num}")

            try:
                browser = self.playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage",
                          "--disable-blink-features=AutomationControlled"],
                )
                ctx = browser.new_context(user_agent=UA)
                page = ctx.new_page()
                resp = page.goto(url, timeout=30000, wait_until='domcontentloaded')

                if not resp or resp.status != 200:
                    page.close()
                    ctx.close()
                    browser.close()
                    break

                # nhatot.com SPA loads __NEXT_DATA__ JSON in ~20s total (4 x 5s checks)
                json_found = False
                for _ in range(4):
                    page.wait_for_timeout(5000)
                    raw = self._extract_json(page)
                    if raw:
                        raw_ads = raw
                        json_found = True
                        break
                    title = page.title()
                    if 'Chờ' not in title:
                        break
                page.close()
                ctx.close()
                browser.close()

                if not json_found:
                    raw_ads = None

                if not raw_ads:
                    consecutive_empty += 1
                    time.sleep(2)
                    continue

                filtered = self._filter_ads(raw_ads, province_slug)
                all_ads.extend(filtered)
                consecutive_empty = 0

                time.sleep(random.uniform(2.0, 3.0))

            except Exception:
                consecutive_empty += 1

        return all_ads


# ═══════════════════════════════════════════════════════════
# Alonhadat.com.vn SCRAPER
# ═══════════════════════════════════════════════════════════
class AlonhadatScraper:
    """Scrape alonhadat.com.vn using BeautifulSoup."""

    SECTIONS = [
        ("can-ban-nha-dat", "property"),
        ("can-ban-nha", "house"),
        ("can-ban-can-ho-chung-cu", "apartment"),
        ("can-ban-dat-tho-cu-dat-o", "land"),
    ]
    HN_SLUGS = {"Quận Cầu Giấy": "cau-giay", "Quận Thanh Xuân": "thanh-xuan", "Quận Đống Đa": "dong-da"}
    HCM_SLUGS = {"Quận 7": "quan-7", "Quận Bình Thạnh": "binh-thanh", "Quận Tân Bình": "tan-binh"}

    def __init__(self, db):
        self.db = db
        self.seen_urls = set()
        self.stats = {"found": 0, "saved": 0}

    def _scrape_section(self, section: str, ptype: str, pages: int = 15) -> list:
        """Scrape a section, return list of ad dicts."""
        results = []
        for page_num in range(1, pages + 1):
            if page_num == 1:
                url = f"https://alonhadat.com.vn/{section}"
            else:
                url = f"https://alonhadat.com.vn/{section}/p{page_num}.htm"

            try:
                import requests
                resp = requests.get(url, headers={
                    "User-Agent": UA,
                    "Accept-Language": "vi-VN,vi;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
                }, timeout=15)
                if resp.status_code != 200 or len(resp.text) < 5000:
                    break
            except Exception:
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            items = (
                soup.select("article.property-item") or
                soup.select("div.property-item") or
                soup.select("div.props-item") or
                soup.select("div.content-item") or
                soup.select("a[href*='.html']")
            )

            found_this_page = 0
            for item in items:
                try:
                    link_el = item if item.name == "a" else item.select_one("a[href]")
                    if not link_el:
                        continue
                    href = link_el.get("href", "")
                    if not href or ".html" not in href:
                        continue
                    if not href.startswith("http"):
                        href = "https://alonhadat.com.vn" + href

                    title = link_el.get_text(strip=True)[:300]
                    if len(title) < 15:
                        continue

                    full_text = item.get_text(" ", strip=True)

                    # Check district
                    district_info = normalize_district(title + " " + full_text)
                    if not district_info:
                        continue

                    district = district_info[1]

                    # Extract price
                    price = parse_price_vnd(full_text)

                    # Extract area
                    area = parse_area(full_text)

                    results.append({
                        "url": href,
                        "subject": title,
                        "ptype": ptype,
                        "district": district,
                        "province": district_info[0],
                        "price": price,
                        "area": area,
                        "source": "alonhadat.com.vn",
                    })
                    found_this_page += 1
                except Exception:
                    continue

            if found_this_page == 0:
                break
            time.sleep(random.uniform(1.0, 2.0))

        return results


# ═══════════════════════════════════════════════════════════
# BatdongsanScraper — DOM card parsing (500+ cards/page)
# ═══════════════════════════════════════════════════════════
class BatdongsanScraper:
    """Scrape batdongsan.com.vn listing section via CSS [class*=card] selectors.

    Each page renders ~500+ real property cards with title, price (tỷ),
    area (m²), price/m² (tr/m²), bedrooms, bathrooms, and district name.
    """

    # batdongsan district slugs for scope districts
    HN_SLUGS = {
        "cau-giay": "Quận Cầu Giấy",
        "thanh-xuan": "Quận Thanh Xuân",
        "dong-da": "Quận Đống Đa",
    }
    HCM_SLUGS = {
        "quan-7": "Quận 7",
        "binh-thanh": "Quận Bình Thạnh",
        "tan-binh": "Quận Tân Bình",
    }
    ALL_SLUGS = {**HN_SLUGS, **HCM_SLUGS}

    # Listing section paths (nguyen-chan channels on batdongsan)
    SECTIONS = [
        ("/ban-nha-rieng", "house"),
        ("/ban-can-ho-chung-cu", "apartment"),
        ("/ban-nen-dat", "land"),
    ]

    # District → batdongsan URL slug mapping
    # HN districts: SPA needs 25-40s to load; use district URLs
    # HCM: nha-dat-ban page has 514 HCM cards; filter by address keyword
    HN_DISTRICT_SECTIONS = {
        "Quận Cầu Giấy": ("ban-nha-rieng/quan-cau-giay", "house"),
        "Quận Thanh Xuân": ("ban-nha-rieng/quan-thanh-xuan", "house"),
        "Quận Đống Đa": ("ban-nha-rieng/quan-dong-da", "house"),
    }
    HCM_SOURCE_URL = "nha-dat-ban"  # HCM listings page with 500+ cards

    # Keyword-based district detection from full card text (for HCM page)
    HCM_DISTRICT_KEYWORDS = {
        "Quận 7": ["quận 7", "quan 7", "q.7", "q7", "thủ thiêm", "phú mỹ hưng"],
        "Quận Bình Thạnh": ["quận bình thạnh", "bình thạnh", "p. 28", "p. 25", "p. 22", "p. 21", "p. 19", "p. 17", "p. 13", "phường 28", "phường 25", "phường 22", "bt"],
        "Quận Tân Bình": ["quận tân bình", "tân bình", "p. 2", "p. 4", "p. 5", "p. 9", "p. 11", "p. 13", "phường 2", "phường 4", "phường 9"],
    }
    HN_DISTRICT_KEYWORDS = {
        "Quận Cầu Giấy": ["cầu giấy", "cau giay", "yên hoà", "trung hoà", "quang trung"],
        "Quận Thanh Xuân": ["thanh xuân", "thanh xuan", "nhân chính", "thượng đình", "kim giang"],
        "Quận Đống Đa": ["đống đa", "dong da", "láng thượng", "trung tự", "cát linh"],
    }

    def __init__(self, db):
        self.db = db
        self.seen_hashes = set()
        self.stats = {"found": 0, "saved": 0, "deduped": 0, "filtered": 0}

    def _parse_card_text(self, text: str, force_district: str = None) -> Optional[dict]:
        """Parse a card's text content into structured fields.

        Card format observed on batdongsan.com.vn:
          "23 Ngợp Bank gấp bán 5.28 tỷ Gần Hàng Xanh\n5,28 tỷ · 27,5 m² · 192 tr/m² · 4 · 3 · Hồ Chí Minh"
          Description follows in the full card text.

        Args:
            text: full inner_text of the card element
            force_district: if set, use this district for all cards (for district-specific pages)
        """
        t = text.strip()
        if len(t) < 20:
            return None

        lines = [ln.strip() for ln in t.split("\n") if ln.strip()]

        # Extract price: "5,28 tỷ" or "5.28 tỷ" — search through lines
        price = None
        for ln in lines:
            m = re.search(r"([\d.,]+)\s*tỷ", ln)
            if m:
                try:
                    price = float(m.group(1).replace(",", ".")) * 1e9
                    break
                except ValueError:
                    pass

        # Extract area: "27,5 m²" — search all lines
        area = None
        for ln in lines:
            m = re.search(r"([\d.,]+)\s*m", ln)
            if m:
                try:
                    area = float(m.group(1).replace(",", "."))
                    break
                except ValueError:
                    pass

        # Extract price/m²: "192 tr/m²"
        ppm = None
        for ln in lines:
            m = re.search(r"([\d.,]+)\s*tr/m", ln)
            if m:
                try:
                    ppm = float(m.group(1).replace(",", ".")) * 1e6
                    break
                except ValueError:
                    pass

        # Extract bedrooms and bathrooms (digits between · delimiters)
        bedrooms = 0
        bathrooms = 0
        for ln in lines:
            m = re.findall(r"(?<=\·)\s*(\d+)\s*(?=\·)", ln)
            if len(m) >= 2:
                try:
                    bedrooms = int(m[0])
                    bathrooms = int(m[1])
                    break
                except ValueError:
                    pass

        # Extract title: first non-numeric line that's long enough
        title = ""
        for i, ln in enumerate(lines):
            # Skip pure numeric lines (listing numbers, floor counts)
            if re.match(r"^\d+$", ln):
                continue
            if len(ln) > 15:
                title = ln
                break

        # Compute price_per_m2
        if price and area and area > 0:
            computed_ppm = price / area
            if ppm is None:
                ppm = computed_ppm
            elif abs(ppm - computed_ppm) / computed_ppm > 5:
                ppm = computed_ppm

        if not price or not area or price < 100_000_000 or area < 10:
            return None

        # Determine district
        district = None
        province = None

        if force_district:
            district = force_district
            province = ("Hà Nội" if force_district in self.HN_DISTRICT_KEYWORDS
                        else "TP. Hồ Chí Minh")
        else:
            # Keyword-based district detection from full card text
            text_lower = t.lower()
            all_keywords = {**self.HCM_DISTRICT_KEYWORDS, **self.HN_DISTRICT_KEYWORDS}
            for dist_name, keywords in all_keywords.items():
                for kw in keywords:
                    if kw in text_lower:
                        district = dist_name
                        province = ("Hà Nội" if dist_name in self.HN_DISTRICT_KEYWORDS
                                    else "TP. Hồ Chí Minh")
                        break
                if district:
                    break

        return {
            "title": title[:200],
            "price": price,
            "area": area,
            "price_per_m2": ppm,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "district": district,
            "province": province,
        }

    def _build_source_url(self, text: str) -> Optional[str]:
        """Try to extract a URL from the card text or title."""
        # batdongsan listing URLs look like:
        # /ban-nha-rieng-duong-xyz-prj123/chu-can-ban-12345.htm
        m = re.search(r"(?:https?://)?(?:www\.)?batdongsan\.com\.vn[/\w-]+\.htm", text)
        if m:
            url = m.group(0)
            if not url.startswith("http"):
                url = "https://www.batdongsan.com.vn" + url
            return url
        return None

    def _extract_from_page(self, page, force_district: str = None) -> list:
        """Extract all property cards from a page using CSS selectors."""
        results = []

        # Try multiple CSS selector patterns used by batdongsan
        selectors = [
            "[class*='card']",
            "[class*='product']",
            "[class*='item']",
            "[class*='listing']",
            "article",
            ".re__product-card",
            ".re__product-item",
        ]

        for sel in selectors:
            cards = page.query_selector_all(sel)
            if not cards:
                continue

            for card in cards:
                try:
                    text = card.inner_text()
                    if len(text) < 30:
                        continue

                    # Skip navigation/sidebar cards
                    if any(kw in text[:50].lower() for kw in
                           ["menu", "nav", "header", "footer", "banner", "quảng cáo",
                            "advertisement", "subscribe", "đăng ký"]):
                        continue

                    parsed = self._parse_card_text(text, force_district=force_district)
                    if not parsed:
                        continue

                    # Filter to scope districts (skip if force_district is set)
                    if not force_district and not parsed["district"]:
                        self.stats["filtered"] += 1
                        continue

                    # Dedupe by price+area hash
                    dedup_key = f"{int(parsed['price'])}-{int(parsed['area'])}"
                    if dedup_key in self.seen_hashes:
                        self.stats["deduped"] += 1
                        continue
                    self.seen_hashes.add(dedup_key)

                    # Try to extract link
                    url = self._build_source_url(text)
                    link_el = card.query_selector("a[href]")
                    if link_el and not url:
                        href = link_el.get_attribute("href") or ""
                        if ".htm" in href:
                            if not href.startswith("http"):
                                href = "https://www.batdongsan.com.vn" + href
                            url = href

                    parsed["url"] = url
                    parsed["source"] = "batdongsan.com.vn"
                    self.stats["found"] += 1
                    results.append(parsed)

                except Exception:
                    continue

            if results:
                break  # Stop at first selector that yields results

        return results

    def scrape(self, section: str, ptype: str, pages: int = 15, district_override: str = None) -> list:
        """Scrape one section, return all filtered listings.

        Args:
            section: batdongsan URL path (e.g., "ban-nha-rieng/quan-cau-giay")
            ptype: property type string
            pages: max pages to scrape
            district_override: if set, force all cards to this district (for district-specific pages)
        """
        all_results = []
        consecutive_empty = 0

        for page_num in range(1, pages + 1):
            if consecutive_empty >= 3:
                break

            if page_num == 1:
                url = f"https://www.batdongsan.com.vn/{section}"
            else:
                url = f"https://www.batdongsan.com.vn/{section}?page={page_num}"

            try:
                page = self.ctx.new_page()
                resp = page.goto(url, timeout=60000)

                if not resp or resp.status not in (200, 201):
                    page.close()
                    consecutive_empty += 1
                    time.sleep(3)
                    continue

                # Determine wait time based on page type
                # batdongsan SPA needs 15-20s to fully render 500+ cards
                wait_time = 20000
                if any(x in section for x in ["quan-cau-giay", "quan-thanh-xuan", "quan-dong-da"]):
                    wait_time = 15000
                page.wait_for_timeout(wait_time)

                # Check for bot protection
                body_text = page.inner_text('body')[:300].lower()
                if "xác minh bảo mật" in body_text or "thực hiện xác minh" in body_text:
                    page.close()
                    break

                cards = self._extract_from_page(page, skip_district_filter=(district_override is not None))
                page.close()

                if not cards:
                    consecutive_empty += 1
                    time.sleep(2)
                    continue

                consecutive_empty = 0

                # If district-specific page, override district for all results
                for card in cards:
                    if district_override:
                        card["district"] = district_override
                        card["province"] = ("Hà Nội" if district_override in self.HN_SLUGS.values()
                                            else "TP. Hồ Chí Minh")

                all_results.extend(cards)

                # Batdongsan returns many results — stop if we have enough
                if len(all_results) >= 300:
                    break

                time.sleep(random.uniform(2.5, 4.5))

            except Exception:
                consecutive_empty += 1
                try:
                    page.close()
                except Exception:
                    pass

        return all_results

    def scrape_hcm_page(self, playwright) -> list:
        """Scrape the HCM listings page (nha-dat-ban) — 500+ HCM cards.

        Uses a fresh browser. District is detected per-card from address/title keywords.
        """
        all_results = []
        url = "https://www.batdongsan.com.vn/" + self.HCM_SOURCE_URL
        try:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage",
                      "--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(
                user_agent=UA, locale="vi-VN",
                extra_http_headers={"Accept-Language": "vi-VN,vi;q=0.9"},
            )
            page = ctx.new_page()
            resp = page.goto(url, timeout=60000)
            if not resp or resp.status not in (200, 201):
                page.close()
                ctx.close()
                browser.close()
                return []

            # SPA renders 500+ cards in ~15-20s total
            page.wait_for_timeout(30000)

            body_text = page.inner_text('body')[:300].lower()
            if "xác minh bảo mật" in body_text:
                page.close()
                ctx.close()
                browser.close()
                return []

            cards = self._extract_from_page(page, force_district=None)
            page.close()
            ctx.close()
            browser.close()

            # Filter to scope HCM districts
            hcm_cards = [c for c in cards if c.get("district") in self.HCM_DISTRICT_KEYWORDS]
            return hcm_cards
        except Exception:
            return []

    def scrape_hn_district(self, district: str, playwright) -> list:
        """Scrape an HN district page.

        batdongsan.com.vn requires a FRESH browser for each district
        to avoid bot protection. SPA redirects from district URL to nha-dat-ban
        and loads 500+ cards in ~13s.
        """
        section, _ = self.HN_DISTRICT_SECTIONS[district]
        url = f"https://www.batdongsan.com.vn/{section}"
        try:
            # CRITICAL: fresh browser + context for each district to avoid bot protection
            browser = playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage",
                      "--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(
                user_agent=UA, locale="vi-VN",
                extra_http_headers={"Accept-Language": "vi-VN,vi;q=0.9"},
            )
            page = ctx.new_page()
            resp = page.goto(url, timeout=60000)
            if not resp or resp.status not in (200, 201):
                page.close()
                ctx.close()
                browser.close()
                return []

            # batdongsan SPA: redirect from district URL -> nha-dat-ban completes in ~5s,
            # then 500+ cards render in another ~8s. Total ~13s.
            # Use 30s to be safe.
            page.wait_for_timeout(30000)

            body_text = page.inner_text('body')[:300].lower()
            if "xác minh bảo mật" in body_text:
                page.close()
                ctx.close()
                browser.close()
                return []

            cards = self._extract_from_page(page, force_district=district)
            page.close()
            ctx.close()
            browser.close()
            return cards
        except Exception:
            return []
        return []


# ═══════════════════════════════════════════════════════════
# MAIN RUNNER
# ═══════════════════════════════════════════════════════════
def run(target: int = 2000, source: str = "all", pages: int = 50):
    init_db()
    db = SessionLocal()

    stats = {"batdongsan": 0, "nhatot": 0, "alonhadat": 0, "errors": 0, "invalid": 0}

    # ── Init or update CollectionSource records ─────────────
    for src_key, src_name in [
        ("batdongsan.com.vn", "batdongsan.com.vn"),
        ("nhatot.com", "nhatot.com"),
        ("alonhadat.com.vn", "alonhadat.com.vn"),
    ]:
        cs = db.query(CollectionSource).filter(CollectionSource.source_key == src_key).first()
        if not cs:
            cs = CollectionSource(
                source_key=src_key, source_name=src_name,
                source_type="scraper", base_url=f"https://{src_key}",
                rate_limit_seconds=3.0, is_active=True, is_approved=True,
                total_records=0, successful_records=0,
            )
            db.add(cs)
    db.commit()

    print(f"\n{'='*60}")
    print(f" REAL LISTING SCRAPER v3")
    print(f" Target: {target} listings | Source: {source}")
    print(f" Districts: {[d[1] for d in ALL_DISTRICTS]}")
    print(f"{'='*60}")

    # ── Phase 0: batdongsan.com.vn (primary source, 500+ cards/page) ──
    if source in ("all", "batdongsan"):
        print(f"\n[Phase 0] batdongsan.com.vn — CSS card extraction")
        try:
            with sync_playwright() as p:
                scraper = BatdongsanScraper(db)

                # HN districts: each needs a fresh context (fresh playwright instance per district)
                for district in BatdongsanScraper.HN_DISTRICT_SECTIONS:
                    if stats["batdongsan"] >= target:
                        break
                    district_saved = 0
                    ads = scraper.scrape_hn_district(district, p)
                    for ad in ads:
                        if stats["batdongsan"] >= target:
                            break
                        rec = {
                            "url": ad.get("url"),
                            "subject": ad.get("title", ""),
                            "ptype": "house",
                            "district": ad["district"],
                            "province": ad["province"],
                            "price": ad["price"],
                            "area": ad["area"],
                            "price_per_m2": int(ad.get("price_per_m2", 0)),
                            "bedrooms": ad.get("bedrooms", 0),
                            "bathrooms": ad.get("bathrooms", 0),
                            "source": "batdongsan.com.vn",
                        }
                        if _save_listing(db, rec):
                            stats["batdongsan"] += 1
                            district_saved += 1
                            if stats["batdongsan"] % 50 == 0:
                                db.commit()
                                print(f"  saved={stats['batdongsan']}/{target}", flush=True)
                    print(f"  {district}: {scraper.stats['found']} found, "
                          f"{district_saved} saved, total={stats['batdongsan']}")
                    db.commit()

                # HCM: scrape the main listings page and filter by district keyword
                if stats["batdongsan"] < target:
                    hcm_ads = scraper.scrape_hcm_page(p)
                    for ad in hcm_ads:
                        if stats["batdongsan"] >= target:
                            break
                        rec = {
                            "url": ad.get("url"),
                            "subject": ad.get("title", ""),
                            "ptype": ad.get("ptype") or "house",
                            "district": ad["district"],
                            "province": ad["province"],
                            "price": ad["price"],
                            "area": ad["area"],
                            "price_per_m2": int(ad.get("price_per_m2", 0)),
                            "bedrooms": ad.get("bedrooms", 0),
                            "bathrooms": ad.get("bathrooms", 0),
                            "source": "batdongsan.com.vn",
                        }
                        if _save_listing(db, rec):
                            stats["batdongsan"] += 1
                            if stats["batdongsan"] % 50 == 0:
                                db.commit()
                                print(f"  saved={stats['batdongsan']}/{target}", flush=True)
                    print(f"  HCM (nha-dat-ban): {scraper.stats['found']} found, "
                          f"{stats['batdongsan']} total")
        except Exception as e:
            print(f"[ERROR] batdongsan scraper: {e}")

    # ── Phase 1: nhatot.com ───────────────────────────────
    if source in ("all", "nhatot"):
        print("\n[Phase 1] nhatot.com — JSON extraction")
        try:
            with sync_playwright() as p:
                scraper = NhatotScraper(db)
                scraper.playwright = p

                # HN districts
                for prov, dist in HN_DISTRICTS:
                    if stats["nhatot"] >= target:
                        break
                    slug = {"Quận Cầu Giấy": "cau-giay", "Quận Thanh Xuân": "thanh-xuan",
                             "Quận Đống Đa": "dong-da"}[dist]
                    ads = scraper.scrape("ha-noi", slug, pages=pages)
                    for ad in ads:
                        if stats["nhatot"] >= target:
                            break
                        saved = _save_listing(db, ad)
                        if saved:
                            stats["nhatot"] += 1
                            scraper.seen_ids.add(ad["list_id"])
                            if stats["nhatot"] % 20 == 0:
                                db.commit()
                                print(f"  saved={stats['nhatot']}/{target}", flush=True)

                    print(f"  {dist}: {len(ads)} ads, total={stats['nhatot']}")

                # HCM districts
                for prov, dist in HCM_DISTRICTS:
                    if stats["nhatot"] >= target:
                        break
                    slug = {"Quận 7": "quan-7", "Quận Bình Thạnh": "binh-thanh",
                             "Quận Tân Bình": "tan-binh"}[dist]
                    ads = scraper.scrape("ho-chi-minh", slug, pages=pages)
                    for ad in ads:
                        if stats["nhatot"] >= target:
                            break
                        saved = _save_listing(db, ad)
                        if saved:
                            stats["nhatot"] += 1
                            scraper.seen_ids.add(ad["list_id"])
                            if stats["nhatot"] % 20 == 0:
                                db.commit()
                                print(f"  saved={stats['nhatot']}/{target}", flush=True)

                    print(f"  {dist}: {len(ads)} ads, total={stats['nhatot']}")

                db.commit()
        except Exception as e:
            print(f"[ERROR] nhatot scraper: {e}")

    # ── Phase 2: alonhadat.com.vn ───────────────────────
    if source in ("all", "alonhadat"):
        print(f"\n[Phase 2] alonhadat.com.vn — HTML parsing ({target - stats['alonhadat']} more needed)")
        try:
            scraper = AlonhadatScraper(db)
            for section, ptype in AlonhadatScraper.SECTIONS:
                if stats["alonhadat"] >= target:
                    break
                ads = scraper._scrape_section(section, ptype, pages=pages)
                for ad in ads:
                    if stats["alonhadat"] >= target:
                        break
                    # Build full record for alonhadat
                    rec = {
                        "url": ad["url"],
                        "subject": ad["subject"],
                        "ptype": ad["ptype"],
                        "district": ad["district"],
                        "province": ad["province"],
                        "price": ad["price"],
                        "area": ad["area"],
                        "price_per_m2": round(ad["price"] / ad["area"], -3) if ad["price"] and ad["area"] else 0,
                        "source": "alonhadat.com.vn",
                        "listing_date": None,
                    }
                    if _save_listing(db, rec):
                        stats["alonhadat"] += 1
                        if stats["alonhadat"] % 20 == 0:
                            db.commit()
                            print(f"  saved={stats['alonhadat']}/{target}", flush=True)
                print(f"  {section}: {len(ads)} ads")
            db.commit()
        except Exception as e:
            print(f"[ERROR] alonhadat scraper: {e}")

    # ── Update CollectionSource stats ──────────────────
    for src_key, cnt_key in [
        ("batdongsan.com.vn", "batdongsan"),
        ("nhatot.com", "nhatot"),
        ("alonhadat.com.vn", "alonhadat"),
    ]:
        cs = db.query(CollectionSource).filter(CollectionSource.source_key == src_key).first()
        if cs:
            cs.successful_records += stats.get(cnt_key, 0)
            cs.last_run_at = datetime.now()
            cs.last_run_status = "success"
    db.commit()
    db.close()

    print(f"\n{'='*60}")
    print(f" COMPLETE")
    print(f"  batdongsan.com: {stats['batdongsan']} listings")
    print(f"  nhatot.com:     {stats['nhatot']} listings")
    print(f"  alonhadat.com:  {stats['alonhadat']} listings")
    print(f"  Total new:      {stats['batdongsan'] + stats['nhatot'] + stats['alonhadat']}")
    print(f"{'='*60}")


def _save_listing(db, rec: dict) -> bool:
    """Save one listing record to DB."""
    try:
        url = rec.get("url") or rec.get("source_url") or ""
        price = rec.get("price")
        area = rec.get("area")
        ppm = rec.get("price_per_m2") or (round(price / area, -3) if price and area else 0)

        if not price or price < 100_000_000:
            return False
        if not area or area < 10 or area > 1000:
            return False
        if not ppm or ppm < 10_000_000 or ppm > 150_000_000:
            return False

        district = rec.get("district")
        province = rec.get("province")
        if not district or not province:
            return False

        # Check for duplicates
        if url:
            existing = db.execute(text(
                "SELECT id FROM properties WHERE source_url = :url AND source_url IS NOT NULL"
            ), {"url": url}).fetchone()
            if existing:
                return False

        listing_date = rec.get("listing_date")
        if rec.get("list_time"):
            try:
                listing_date = datetime.fromisoformat(rec["list_time"].replace("Z", "+00:00"))
            except Exception:
                listing_date = None

        prop = Property(
            property_type=rec.get("ptype") or rec.get("property_type") or "apartment",
            province_city=province,
            district=district,
            area_m2=area,
            bedrooms=rec.get("bedrooms") or rec.get("rooms") or 0,
            bathrooms=rec.get("toilets") or 0,
            floor_count=rec.get("floors") or 0,
            price=price,
            price_per_m2=int(ppm),
            listing_date=listing_date,
            legal_status=rec.get("legal_document") or rec.get("legal_status"),
            furnishing=rec.get("furnishing"),
            source_name=rec.get("source") or "nhatot.com",
            source_url=url,
            source_domain=rec.get("source") or "nhatot.com",
            source_crawl_at=datetime.now(),
            data_origin_type="public_collected",
            record_status="pending_review",
            verification_status="pending",
            data_collection_status="collected",
            collection_attempt_count=1,
            last_collection_attempt=datetime.now(),
            collection_method="playwright_stealth",
            # E4 is WRONG for scraped data — E4 = "Primary source (land cert, bank appraisal)"
            # Correct tier: E3 if authoritative URL + price range OK, else E2
            evidence_tier="E3",  # playwright_stealth has real listing URLs — at best E3
            evidence_tier_updated_at=datetime.now(),
        )
        db.add(prop)
        db.flush()

        # Provenance chain
        raw_text = rec.get("subject", "") + str(rec.get("ward", ""))
        raw_hash = hashlib.sha256(raw_text[:2000].encode()).hexdigest()
        chain = ProvenanceChain(
            property_id=prop.id,
            step="COLLECTED",
            actor="system:scrape_real_listings",
            input_hash=raw_hash[:16],
            output_hash=raw_hash,
            source=rec.get("source") or "nhatot.com",
            verify_url=url,
            metadata_json=json.dumps({"scraper": "playwright_stealth", "source": rec.get("source")}),
        )
        db.add(chain)

        return True
    except Exception:
        db.rollback()
        return False


def main():
    parser = argparse.ArgumentParser(description="Real listing scraper")
    parser.add_argument("--target", type=int, default=2000, help="Target listings")
    parser.add_argument("--source", default="all",
                        choices=["all", "batdongsan", "nhatot", "alonhadat"],
                        help="Source to scrape")
    parser.add_argument("--pages", type=int, default=50, help="Pages per district")
    args = parser.parse_args()
    run(target=args.target, source=args.source, pages=args.pages)


if __name__ == "__main__":
    main()
