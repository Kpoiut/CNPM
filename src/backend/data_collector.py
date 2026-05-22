#!/usr/bin/env python3
"""
Data Collector Service — Thu thập dữ liệu BĐS thực từ các nguồn được phê duyệt.

Triển khai theo CVX-BDS/IoT 1.1-VN:
1. CHỈ thu thập từ nguồn trong APPROVED_SOURCES
2. Rate limiting — không spam website
3. Retry với exponential backoff
4. Raw storage — lưu response gốc
5. Deduplication — tránh trùng lặp
6. Provenance tracking — mọi bước đều được log

Scope: Chỉ Hà Nội (3 quận) + TP.HCM (3 quận)
"""

import hashlib
import json
import os
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from src.backend.approved_sources import (
    APPROVED_SOURCES,
    PROHIBITED_SOURCES,
    get_approved_source,
    is_source_approved,
    is_source_prohibited,
    get_all_approved_domains,
)
from src.backend.models import (
    AuditLog,
    CollectionSource,
    DataCollectionStatus,
    Property,
    ProvenanceChain,
)
from src.backend.provenance_tracker import ProvenanceActor, ProvenanceStep, ProvenanceTracker


# ==============================================================================
# CONFIG
# ==============================================================================

HEADERS_DEFAULT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


# ==============================================================================
# DATA CLASSES
# ==============================================================================

@dataclass
class CollectResult:
    """Kết quả của 1 lần thu thập."""
    success: bool
    records_collected: int
    records_deduped: int
    records_failed: int
    duration_seconds: float
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class ScrapeResult:
    """Kết quả scrape 1 trang."""
    url: str
    status_code: int
    html: str
    headers: Dict
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


# ==============================================================================
# UTILITIES
# ==============================================================================

def _compute_dedup_key(
    url: str,
    price: Optional[float] = None,
    area: Optional[float] = None,
) -> str:
    """Compute dedup key từ URL + price + area."""
    key_parts = [url.strip().lower()]
    if price:
        key_parts.append(f"p:{round(price / 1_000_000, 1)}M")  # Round to nearest 100k
    if area:
        key_parts.append(f"a:{round(area / 10) * 10}m2")  # Round to nearest 10m2
    return hashlib.sha256("|".join(key_parts).encode("utf-8")).hexdigest()


def _parse_vietnam_price(price_str: str) -> Optional[float]:
    """
    Parse price string dạng VN: "3.5 tỷ", "1.2 tỷ", "45 triệu/m2"
    Trả về giá VND.
    """
    if not price_str:
        return None

    text = price_str.strip().lower()
    text = re.sub(r"[^\d.,tỷtriệum²]", "", text)  # Keep only relevant chars

    # Try tỷ
    match = re.search(r"([\d.,]+)\s*tỷ", text)
    if match:
        try:
            value = float(match.group(1).replace(",", "."))
            return value * 1_000_000_000
        except ValueError:
            pass

    # Try triệu
    match = re.search(r"([\d.,]+)\s*triệu", text)
    if match:
        try:
            value = float(match.group(1).replace(",", "."))
            return value * 1_000_000
        except ValueError:
            pass

    # Try "3 tỷ 500 triệu" format
    match = re.search(r"([\d.,]+)\s*tỷ.*?([\d.,]+)\s*triệu", text)
    if match:
        try:
            ty = float(match.group(1).replace(",", "."))
            trieu = float(match.group(2).replace(",", "."))
            return (ty * 1_000_000_000) + (trieu * 1_000_000)
        except ValueError:
            pass

    # Try plain number (assume VND)
    match = re.search(r"([\d.,]+)", text.replace(",", ""))
    if match:
        try:
            value = float(match.group(1).replace(",", ""))
            if value > 100_000_000_000:  # > 100B, likely raw VND
                return value
            elif value > 1_000_000:  # > 1M, likely VND
                return value
        except ValueError:
            pass

    return None


def _parse_vietnam_area(area_str: str) -> Optional[float]:
    """Parse area string: '120 m2', '120m²', '120'"""
    if not area_str:
        return None
    text = area_str.strip().lower()
    text = re.sub(r"[^\d.,m²]", "", text)
    match = re.search(r"([\d.,]+)", text)
    if match:
        try:
            return float(match.group(1).replace(",", "."))
        except ValueError:
            pass
    return None


def _parse_vietnam_bedrooms(text: str) -> int:
    """Parse số phòng ngủ từ text."""
    match = re.search(r"(\d+)\s*pn?|(\d+)\s*phòng\s*ngủ", text.lower())
    if match:
        try:
            return int(match.group(1) or match.group(2))
        except ValueError:
            pass
    return 0


def _map_property_type(type_str: str) -> str:
    """Map loại BĐS về định dạng chuẩn."""
    text = type_str.lower().strip()
    if any(k in text for k in ["căn hộ", "apartment", "chung cư", "condominium"]):
        return "apartment"
    if any(k in text for k in ["đất", "land", "nền"]):
        return "land"
    if any(k in text for k in ["biệt thự", "villa"]):
        return "villa"
    if any(k in text for k in ["nhà phố", "townhouse", "liền kề"]):
        return "townhouse"
    if any(k in text for k in ["nhà", "house", "home"]):
        return "house"
    return "house"  # default


# ==============================================================================
# BASE COLLECTOR
# ==============================================================================

class BaseCollector:
    """Base class cho tất cả collectors."""

    def __init__(self, source_key: str, source_config: Dict, db: Session):
        self.source_key = source_key
        self.source_config = source_config
        self.db = db
        self.session = requests.Session()
        self.session.headers.update(HEADERS_DEFAULT)
        self.rate_limit = source_config.get("rate_limit_seconds", 3)
        self.last_request_time = 0.0
        self.retry_config = source_config.get("retry_config", {})

    def _rate_limit_wait(self):
        """Đợi đủ rate limit trước khi request tiếp."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            sleep_time = self.rate_limit - elapsed + random.uniform(0.5, 1.5)
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _fetch(self, url: str, method: str = "GET", **kwargs) -> ScrapeResult:
        """
        Fetch URL với retry + rate limiting.
        Trả về ScrapeResult chứa HTML để parse.
        """
        self._rate_limit_wait()

        max_attempts = self.retry_config.get("max_attempts", 3)
        backoff = self.retry_config.get("backoff_seconds", [5, 15, 45])
        retry_on = self.retry_config.get("retry_on_status", [429, 500, 502, 503, 504])

        headers = kwargs.pop("headers", {})
        headers.update(self.session.headers)

        for attempt in range(max_attempts):
            try:
                if method.upper() == "GET":
                    response = self.session.get(url, timeout=30, headers=headers, **kwargs)
                else:
                    response = self.session.post(url, timeout=30, headers=headers, **kwargs)

                if response.status_code in retry_on:
                    if attempt < max_attempts - 1:
                        wait_time = backoff[attempt] if attempt < len(backoff) else backoff[-1]
                        time.sleep(wait_time)
                        continue
                    return ScrapeResult(
                        url=url,
                        status_code=response.status_code,
                        html="",
                        headers=dict(response.headers),
                        error=f"HTTP {response.status_code} after {max_attempts} retries",
                    )

                return ScrapeResult(
                    url=url,
                    status_code=response.status_code,
                    html=response.text,
                    headers=dict(response.headers),
                )

            except requests.RequestException as e:
                if attempt < max_attempts - 1:
                    wait_time = backoff[attempt] if attempt < len(backoff) else backoff[-1]
                    time.sleep(wait_time)
                    continue
                return ScrapeResult(
                    url=url,
                    status_code=0,
                    html="",
                    headers={},
                    error=str(e),
                )

        return ScrapeResult(url=url, status_code=0, html="", headers={}, error="Max retries exceeded")

    def get_source_record(self) -> Optional[CollectionSource]:
        """Get hoặc create CollectionSource record trong DB."""
        record = (
            self.db.query(CollectionSource)
            .filter(CollectionSource.source_key == self.source_key)
            .first()
        )
        if not record:
            record = CollectionSource(
                source_key=self.source_key,
                source_name=self.source_config.get("name", self.source_key),
                source_type=self.source_config.get("type", "scraper"),
                base_url=self.source_config.get("base_url", ""),
                rate_limit_seconds=self.rate_limit,
                is_active=True,
                is_approved=True,
            )
            self.db.add(record)
            self.db.flush()
        return record

    def log_audit(self, action: str, details: Dict, property_id: Optional[int] = None):
        """Log action vào audit log."""
        log = AuditLog(
            record_id=property_id,
            table_name="properties",
            action_type=action,
            changed_by=ProvenanceActor.SYSTEM,
            new_value_json=json.dumps(details, default=str, ensure_ascii=False),
            change_note=f"DataCollector: {action}",
        )
        self.db.add(log)


# ==============================================================================
# ALONHADAT COLLECTOR
# ==============================================================================

class AlonhadatCollector(BaseCollector):
    """Collector cho alonhadat.com.vn."""

    def __init__(self, db: Session, districts: Optional[Dict] = None):
        config = get_approved_source("alonhadat.com.vn")
        if not config:
            raise ValueError("Alonhadat not in APPROVED_SOURCES")
        super().__init__("alonhadat.com.vn", config, db)
        self.districts = districts or config.get("districts", {})

    # Alonhadat category slugs per property type
    ALONHADAT_CATEGORIES = {
        "land": "dat",
        "apartment": "can-ho",
        "house": "nha-dat",
        "townhouse": "nha-dat",
        "villa": "biet-thu",
    }

    def _build_listing_url(self, district_slug: str, page: int, property_type: str = "house", listing_type: str = "buy") -> str:
        """
        Build URL cho listing page trên alonhadat.com.vn.

        URL patterns:
          Land:   /can-ban-dat/{province}/{district}/trang-{n}
          Apt:     /can-ban-can-ho/{province}/{district}/trang-{n}
          House:   /can-ban-nha-dat/{province}/{district}/trang-{n}
          Villa:   /can-ban-biet-thu/{province}/{district}/trang-{n}
          Rent:     /cho-thue-{type}/{province}/{district}/trang-{n}
        """
        base = self.source_config["base_url"]  # https://alonhadat.com.vn

        hn_districts = {"cau-giay", "thanh-xuan", "dong-da"}
        province_slug = "ha-noi" if district_slug in hn_districts else "ho-chi-minh"

        category_slug = self.ALONHADAT_CATEGORIES.get(property_type, "nha-dat")
        category = f"cho-thue-{category_slug}" if listing_type == "rent" else f"can-ban-{category_slug}"

        if page == 1:
            return f"{base}/{category}/{province_slug}/{district_slug}/"
        else:
            return f"{base}/{category}/{province_slug}/{district_slug}/trang-{page}"

    def _parse_listing_page(self, html: str) -> List[Dict]:
        """Parse 1 listing page, trả về list of raw listings."""
        soup = BeautifulSoup(html, "html.parser")
        listings = []

        # Primary: article.property-item (alonhadat.com.vn actual listing structure)
        items = soup.select("article.property-item")
        if not items:
            # Fallback: div.property-item
            items = soup.select("div.property-item")
        if not items:
            # Legacy fallback: .item (agent cards on alonhadat)
            items = soup.select(".item")

        for item in items:
            try:
                raw = {}

                # Title — try multiple selectors for different page structures
                title_el = (
                    item.select_one("h3.property-title") or
                    item.select_one(".property-title") or
                    item.select_one(".title a") or
                    item.select_one("a.title") or
                    item.select_one("h3") or
                    item.select_one("a")
                )
                raw["title"] = title_el.get_text(strip=True) if title_el else ""

                # URL — link to property detail
                link_el = (
                    item.select_one("a.link") or
                    item.select_one("a.link.vip") or
                    item.select_one(".title a") or
                    item.select_one("a")
                )
                raw["url"] = link_el.get("href", "") if link_el else ""
                if raw["url"] and not raw["url"].startswith("http"):
                    raw["url"] = urljoin(self.source_config["base_url"], raw["url"])

                # Price — format: "Giá:25 tỷ" or "Giá:3.5 tỷ 500 triệu"
                price_el = (
                    item.select_one(".price") or
                    item.select_one("[class*=price]")
                )
                price_text = price_el.get_text(strip=True) if price_el else ""
                # Normalize: "Giá:25 tỷ" → "25 tỷ"
                if "Giá:" in price_text:
                    price_text = price_text.split("Giá:", 1)[1].strip()
                raw["price_text"] = price_text

                # Area — format: "Diện tích:55m²"
                area_el = (
                    item.select_one(".area") or
                    item.select_one("[class*=area]") or
                    item.select_one(".square")
                )
                area_text = area_el.get_text(strip=True) if area_el else ""
                # Normalize: "Diện tích:55m²" → "55m²"
                if "Diện tích:" in area_text:
                    area_text = area_text.split("Diện tích:", 1)[1].strip()
                raw["area_text"] = area_text

                # Location
                loc_el = (
                    item.select_one(".property-address") or
                    item.select_one(".new-address") or
                    item.select_one(".address") or
                    item.select_one("[class*=address]") or
                    item.select_one(".street")
                )
                raw["location_text"] = loc_el.get_text(strip=True) if loc_el else ""

                # Description (brief)
                desc_el = item.select_one(".brief")
                raw["description"] = desc_el.get_text(strip=True)[:500] if desc_el else ""

                # Image
                img_el = item.select_one("img")
                raw["image_url"] = (
                    img_el.get("src") or
                    img_el.get("data-src", "")
                ) if img_el else ""

                # Bedroom count
                bedroom_el = item.select_one(".bedroom")
                raw["bedroom_text"] = bedroom_el.get_text(strip=True) if bedroom_el else ""

                # Floor count
                floor_el = item.select_one(".floors")
                raw["floor_text"] = floor_el.get_text(strip=True) if floor_el else ""

                # Posted date
                date_el = item.select_one(".created-date, .date")
                raw["date_text"] = date_el.get_text(strip=True) if date_el else ""

                if raw.get("url") and raw["url"].strip():
                    listings.append(raw)

            except Exception:
                continue

        return listings

    def _parse_detail_page(self, html: str, listing_url: str) -> Optional[Dict]:
        """Parse detail page để lấy thông tin đầy đủ."""
        soup = BeautifulSoup(html, "html.parser")
        data = {}

        # Title
        title_el = soup.select_one("h1.title, .detail-title h1, h1")
        data["title"] = title_el.get_text(strip=True) if title_el else ""

        # Price
        price_el = soup.select_one(".price-value, .gia, [class*=price]")
        price_text = price_el.get_text(strip=True) if price_el else ""
        data["price"] = _parse_vietnam_price(price_text)

        # Area
        area_el = soup.select_one(".square-value, .dientich, [class*=area]")
        area_text = area_el.get_text(strip=True) if area_el else ""
        data["area_m2"] = _parse_vietnam_area(area_text)

        # Address
        addr_el = soup.select_one(".address, [class*=address], [class*=location]")
        data["address"] = addr_el.get_text(strip=True) if addr_el else ""

        # Bedrooms
        desc_text = soup.get_text()
        data["bedrooms"] = _parse_vietnam_bedrooms(desc_text)

        # Description
        desc_el = soup.select_one(".content, .description, [class*=content]")
        data["description"] = desc_el.get_text(strip=True)[:2000] if desc_el else ""

        # Images
        img_els = soup.select("img[class*=thumb], .gallery img")
        data["image_urls"] = [img.get("src") or img.get("data-src", "") for img in img_els[:10]]

        # Posted date
        date_el = soup.select_one(".postdate, .date, [class*=date]")
        data["posted_date"] = date_el.get_text(strip=True) if date_el else ""

        return data

    def collect_district(
        self,
        province: str,
        district_name: str,
        district_slug: str,
        property_types: List[str],
        max_pages: int = 20,
        progress_callback=None,
    ) -> CollectResult:
        """
        Thu thập tất cả listing của 1 quận.
        Scrape TẤT CẢ property types: land, apartment, house, townhouse, villa.
        """
        start_time = time.time()
        total_collected = 0
        total_deduped = 0
        total_failed = 0
        errors = []

        source_record = self.get_source_record()
        tracker = ProvenanceTracker(self.db)

        # Iterate over property types + listing types
        listing_types = ["buy", "rent"]

        for listing_type in listing_types:
            for ptype in property_types:
                for page in range(1, max_pages + 1):
                    # Build URL for this property type
                    url = self._build_listing_url(district_slug, page, ptype, listing_type)

                    # Fetch
                    result = self._fetch(url)
                    if result.error:
                        errors.append(f"Page {page} ({listing_type}/{ptype}): {result.error}")
                        continue

                    # Parse listings
                    listings = self._parse_listing_page(result.html)
                    if not listings:
                        # Hết trang cho type này
                        break

                    for listing in listings:
                        try:
                            dedup_key = _compute_dedup_key(
                                listing.get("url", ""),
                                _parse_vietnam_price(listing.get("price_text", "")),
                                _parse_vietnam_area(listing.get("area_text", "")),
                            )

                            # Check dedup
                            existing = (
                                self.db.query(Property)
                                .filter(Property.source_etag == dedup_key)
                                .first()
                            )
                            if existing:
                                total_deduped += 1
                                continue

                            # Fetch detail
                            detail_result = self._fetch(listing.get("url", ""))
                            if detail_result.error:
                                errors.append(
                                    f"Detail: {listing.get('url', '')}: {detail_result.error}"
                                )
                                total_failed += 1
                                continue

                            # Parse detail
                            detail = self._parse_detail_page(detail_result.html, listing.get("url", ""))

                            # Map to Property — ptype from URL category slug
                            property_data = self._map_to_property(
                                listing=listing,
                                detail=detail,
                                province=province,
                                district_name=district_name,
                                province_slug=province.lower().replace(" ", "-"),
                                ptype=ptype,
                            )

                            # Sanitize before insert — catches parse failures (area=0, price=0, etc.)
                            try:
                                from src.backend.data_sanitizer import PropertySanitizer
                                sanitizer = PropertySanitizer(strict_scope=False)
                                property_data = sanitizer.sanitize(property_data)
                            except Exception:
                                # Fall back to raw data if sanitizer rejects (log warning)
                                total_failed += 1
                                continue

                            # Save raw content
                            raw_content = {
                                "listing_page": result.html[:5000] if result.html else "",
                                "detail_page": detail_result.html[:10000] if detail_result.html else "",
                                "parsed": detail,
                                "listing_url": listing.get("url", ""),
                            }
                            property_data["raw_source_content"] = json.dumps(raw_content, ensure_ascii=False)
                            property_data["source_etag"] = dedup_key

                            # Create property
                            prop = Property(**property_data)
                            self.db.add(prop)
                            self.db.flush()

                            # Provenance chain
                            crawl_step = tracker.add_step(
                                property_id=prop.id,
                                step=ProvenanceStep.CRAWLED,
                                actor=ProvenanceActor.SCRAPER,
                                source=listing.get("url", ""),
                                input_data={
                                    "url": listing.get("url", ""),
                                    "listing_page": listing.get("title", ""),
                                },
                                output_data={
                                    "status_code": detail_result.status_code,
                                    "detail_html_len": len(detail_result.html) if detail_result.html else 0,
                                },
                                metadata={"source_domain": self.source_key, "district": district_slug},
                                verify_url=listing.get("url", ""),
                                prev_step_id=None,
                            )
                            parse_step = tracker.add_step(
                                property_id=prop.id,
                                step=ProvenanceStep.PARSED,
                                actor=ProvenanceActor.SCRAPER,
                                source=None,
                                input_data={
                                    "raw_len": len(detail_result.html) if detail_result.html else 0
                                },
                                output_data=detail or {},
                                metadata={"parser_version": "1.0"},
                                prev_step_id=crawl_step.id,
                            )
                            tracker.add_step(
                                property_id=prop.id,
                                step=ProvenanceStep.IMPORTED,
                                actor=ProvenanceActor.SYSTEM,
                                source=None,
                                input_data={"property_id": prop.id},
                                output_data={"imported": True},
                                metadata={"source": "alonhadat_scrape"},
                                prev_step_id=crawl_step.id,
                            )

                            total_collected += 1

                            if progress_callback:
                                progress_callback(prop.id, total_collected, listing.get("url", ""))

                        except Exception as e:
                            errors.append(f"Listing {listing.get('url', '')}: {str(e)}")
                            total_failed += 1
                            continue

        self.db.commit()

        # Update source stats
        if source_record:
            source_record.total_records += total_collected
            source_record.successful_records += total_collected
            source_record.failed_records += total_failed
            source_record.last_run_at = datetime.now()
            source_record.last_run_status = "success" if total_collected > 0 else "failed"
        self.db.commit()

        return CollectResult(
            success=total_collected > 0,
            records_collected=total_collected,
            records_deduped=total_deduped,
            records_failed=total_failed,
            duration_seconds=time.time() - start_time,
            error="; ".join(errors[:5]) if errors else None,
        )

    def _map_to_property(
        self,
        listing: Dict,
        detail: Optional[Dict],
        province: str,
        district_name: str,
        province_slug: str,
        ptype: str = "house",
    ) -> Dict:
        """Map parsed data thành Property fields với Evidence Tier."""
        price = _parse_vietnam_price(listing.get("price_text", "")) or (
            _parse_vietnam_price(detail.get("price_text", "")) if detail else None
        )
        area = _parse_vietnam_area(listing.get("area_text", "")) or (
            _parse_vietnam_area(detail.get("area_text", "")) if detail else None
        )

        # Detect property type — URL-based type (ptype param) is authoritative
        prop_type = ptype
        if not prop_type or prop_type == "house":
            title = (detail or listing).get("title", listing.get("title", ""))
            prop_type = _map_property_type(title)
            if "căn hộ" in title.lower() or "chung cư" in title.lower():
                prop_type = "apartment"
            elif "đất" in title.lower() or "nền" in title.lower():
                prop_type = "land"

        # Extract bedroom + floor from listing text
        bedrooms = 0
        bedrooms_txt = listing.get("bedroom_text", "")
        import re as _re
        bd_match = _re.search(r"(\d+)\s*phòng\s*ngủ", bedrooms_txt)
        if bd_match:
            bedrooms = int(bd_match.group(1))
        else:
            bedrooms = _parse_vietnam_bedrooms(title)

        floors = 1
        floor_txt = listing.get("floor_text", "")
        fl_match = _re.search(r"(\d+)\s*tầng", floor_txt)
        if fl_match:
            floors = int(fl_match.group(1))

        address_val = (detail or listing).get("address", listing.get("location_text", ""))
        image_url = (detail or listing).get("image_url")
        image_urls = (detail or {}).get("image_urls")

        data = {
            "property_type": prop_type,
            "province_city": province,
            "district": district_name,
            "ward": None,
            "street_or_project": address_val,
            "area_m2": area,
            "bedrooms": bedrooms,
            "bathrooms": 0,
            "floor_count": floors,
            "frontage_m": None,
            "legal_status": "pending",
            "furnishing": None,
            "price": price if price is not None else 0.0,
            "price_per_m2": round(price / area, 0) if price and area else None,
            "listing_date": datetime.now(),
            "latitude": None,
            "longitude": None,
            "area_type": "urban_center",
            # Source tracking
            "source_name": self.source_config["name"],
            "source_url": listing.get("url", ""),
            "source_page_title": (detail or listing).get("title", listing.get("title", "")) or title,
            "source_collected_at": datetime.now(),
            "source_access_method": "scraper",
            "data_collection_status": DataCollectionStatus.COLLECTED.value,
            "collection_attempt_count": 1,
            "last_collection_attempt": datetime.now(),
            "data_origin_type": "public_collected",
            "record_status": "pending_review",
            "verification_status": "unverified",
            "description": (detail or listing).get("description", ""),
            # Provenance
            "source_domain": self.source_key,
            "source_category": "scraper",
            "source_crawl_at": datetime.now(),
        }

        if image_url:
            data["image_url"] = image_url
        if image_urls:
            data["image_urls"] = json.dumps(image_urls[:10])

        # Assign evidence tier dựa trên dữ liệu có thật
        tier = self._assign_scraped_tier(data)
        data["evidence_tier"] = tier
        data["evidence_tier_updated_at"] = datetime.now()

        return data

    def _assign_scraped_tier(self, prop_data: Dict) -> str:
        """
        Assign evidence tier cho scraped records.
        Tier = thước đo BẰNG CHỨNG, không phải GIÁ TRỊ.

        Logic:
          E5: Không có ward/street (chỉ district) — tối thiểu
          E4: Có ward/street (street address) — đủ address
          E3: E4 + ≥1 trường bổ sung (rooms/floors/legal/image/source)
          E2: E4 + ≥3 trường bổ sung
          E1: E4 + image + source_url + rooms + floors + legal (full evidence)
        """
        has_price = (prop_data.get("price") or 0) > 0
        has_area = (prop_data.get("area_m2") or 0) > 0
        if not (has_price and has_area):
            return "E5"

        has_province = bool(prop_data.get("province_city"))
        has_district = bool(prop_data.get("district"))
        if not (has_province and has_district):
            return "E5"

        has_ward_or_street = bool(
            prop_data.get("ward") or prop_data.get("street_or_project")
        )
        has_image = bool(prop_data.get("image_url") or prop_data.get("image_urls"))
        has_source_url = bool(prop_data.get("source_url"))

        bedrooms = prop_data.get("bedrooms", 0)
        floors = prop_data.get("floor_count", 0)
        legal = prop_data.get("legal_status")
        has_rooms = bedrooms > 0
        has_floors = floors > 0
        has_legal = bool(legal) and legal not in ["pending", "unknown"]

        # E5: no ward/street (only district-level)
        if not has_ward_or_street:
            return "E5"

        # Count extra evidence fields
        extra_count = sum([has_image, has_source_url, has_rooms, has_floors, has_legal])

        # E4: has ward/street but few other fields
        if extra_count == 0:
            return "E4"

        # E3: has ward/street + 1 extra
        if extra_count == 1:
            return "E3"

        # E2: has ward/street + 2-4 extras (E1 is 5)
        if extra_count >= 2 and extra_count <= 4:
            return "E2"

        # E1: ward/street + ALL 5 extras
        if (has_image and has_source_url and has_rooms and has_floors and has_legal):
            return "E1"

        return "E2"


# ==============================================================================
# BATDONGSAN COLLECTOR
# ==============================================================================

class BatdongsanCollector(BaseCollector):
    """
    Collector cho batdongsan.com.vn.

    URL patterns (new slug-based):
      Buy: /nha-dat-ban/{province}/{district}/
           /can-ban-dat/{province}/{district}/
           /can-ban-chung-cu/{province}/{district}/
      Rent: /cho-thue-nha-dat/{province}/{district}/
            /cho-thue-dat/{province}/{district}/
            /cho-thue-chung-cu/{province}/{district}/

    Province slugs: ha-noi, ho-chi-minh
    District slugs: cau-giay, thanh-xuan, dong-da, quan-7, binh-thanh, tan-binh
    """

    def __init__(self, db: Session):
        config = get_approved_source("batdongsan.com.vn")
        if not config:
            raise ValueError("Batdongsan not in APPROVED_SOURCES")
        super().__init__("batdongsan.com.vn", config, db)

    PROPERTY_TYPE_PATTERNS = {
        "land": ["dat", "nền", "đất"],
        "apartment": ["chung-cu", "căn hộ", "apartment", "condo"],
        "townhouse": ["nhà phố", "townhouse", "liền kề"],
        "house": ["nhà", "nhà riêng", "house"],
        "villa": ["biệt thự", "villa"],
    }

    def _map_district_slug(self, district_slug: str) -> str:
        """Map internal slug to batdongsan.com.vn slug."""
        mapping = {
            "cau-giay": "cau-giay",
            "thanh-xuan": "thanh-xuan",
            "dong-da": "dong-da",
            "quan-7": "quan-7",
            "binh-thanh": "binh-thanh",
            "tan-binh": "tan-binh",
        }
        return mapping.get(district_slug, district_slug)

    def _map_province_slug(self, province: str) -> str:
        """Map province name to batdongsan.com.vn slug."""
        if "Hà Nội" in province or "Hà Nội" in province:
            return "ha-noi"
        if "Hồ Chí Minh" in province:
            return "ho-chi-minh"
        return "ha-noi"

    def _build_urls(self, district_slug: str, province: str, listing_type: str = "ban") -> list:
        """
        Build all listing URLs for a district.
        listing_type: 'ban' (mua) or 'thue' (thuê)
        """
        prov_slug = self._map_province_slug(province)
        dist_slug = self._map_district_slug(district_slug)
        base = self.source_config["base_url"]

        if listing_type == "ban":
            return [
                f"{base}/nha-dat-ban/{prov_slug}/{dist_slug}",          # house/townhouse
                f"{base}/can-ban-dat/{prov_slug}/{dist_slug}",           # land
                f"{base}/can-ban-chung-cu/{prov_slug}/{dist_slug}",     # apartment
            ]
        else:
            return [
                f"{base}/cho-thue-nha-dat/{prov_slug}/{dist_slug}",
                f"{base}/cho-thue-dat/{prov_slug}/{dist_slug}",
                f"{base}/cho-thue-chung-cu/{prov_slug}/{dist_slug}",
            ]

    def _detect_property_type(self, title: str, url: str) -> str:
        """Detect property type from title and URL."""
        combined = (title + " " + url).lower()
        for ptype, keywords in self.PROPERTY_TYPE_PATTERNS.items():
            if any(k in combined for k in keywords):
                return ptype
        return "house"  # default

    def _parse_listing_page(self, html: str, source_url: str) -> List[Dict]:
        """Parse 1 listing page."""
        soup = BeautifulSoup(html, "html.parser")
        listings = []

        items = soup.select(".prd")
        if not items:
            items = soup.select("[class*=product-item]")

        for item in items:
            try:
                # Title + URL
                title_el = (
                    item.select_one(".prd-title a") or
                    item.select_one("a.title") or
                    item.select_one("h3 a") or
                    item.select_one("a")
                )
                title = title_el.get_text(strip=True) if title_el else ""
                detail_url = title_el.get("href", "") if title_el else ""
                if detail_url and not detail_url.startswith("http"):
                    detail_url = urljoin(self.source_config["base_url"], detail_url)

                # Price
                price_el = (
                    item.select_one(".prd-price") or
                    item.select_one("[class*=price]")
                )
                price_text = price_el.get_text(strip=True) if price_el else ""
                price = _parse_vietnam_price(price_text)

                # Area
                area_el = (
                    item.select_one(".prd-size") or
                    item.select_one("[class*=size]") or
                    item.select_one("[class*=area]")
                )
                area_text = area_el.get_text(strip=True) if area_el else ""
                area = _parse_vietnam_area(area_text)

                # Address
                addr_el = (
                    item.select_one(".prd-address") or
                    item.select_one("[class*=address]")
                )
                address = addr_el.get_text(strip=True) if addr_el else ""

                # Image
                img_el = (
                    item.select_one(".prd-image img") or
                    item.select_one("img[class*=thumb]")
                )
                img_url = img_el.get("src") or img_el.get("data-src", "") if img_el else ""

                # Detect type
                prop_type = self._detect_property_type(title, source_url)

                if detail_url:
                    listings.append({
                        "title": title,
                        "url": detail_url,
                        "price_text": price_text,
                        "price": price,
                        "area_text": area_text,
                        "area": area,
                        "location_text": address,
                        "image_url": img_url,
                        "property_type": prop_type,
                    })

            except Exception:
                continue

        return listings

    def _parse_detail_page(self, html: str) -> Optional[Dict]:
        """Parse detail page for richer data."""
        soup = BeautifulSoup(html, "html.parser")
        data = {}

        # Title
        title_el = soup.select_one("h1.title, .prd-detail-title, h1")
        data["title"] = title_el.get_text(strip=True) if title_el else ""

        # Price
        price_el = soup.select_one(".prd-detail-price, .price-value, [class*=price]")
        price_text = price_el.get_text(strip=True) if price_el else ""
        data["price"] = _parse_vietnam_price(price_text)

        # Area
        area_el = soup.select_one(".square-value, .prd-detail-size, [class*=area]")
        area_text = area_el.get_text(strip=True) if area_el else ""
        data["area_m2"] = _parse_vietnam_area(area_text)

        # Description
        desc_el = soup.select_one(".prd-detail-content, .description, [class*=content]")
        data["description"] = desc_el.get_text(strip=True)[:2000] if desc_el else ""

        # Images
        img_els = soup.select(".prd-detail-images img, .gallery img")
        data["image_urls"] = [
            img.get("src") or img.get("data-src", "")
            for img in img_els[:10]
            if img.get("src")
        ]

        # Address
        addr_el = soup.select_one(".prd-detail-address, .address")
        data["address"] = addr_el.get_text(strip=True) if addr_el else ""

        return data

    def collect_district(
        self,
        province: str,
        district_name: str,
        district_slug: str,
        property_types: List[str],
        max_pages: int = 20,
        progress_callback=None,
    ) -> CollectResult:
        """Collect all listings for a district from batdongsan.com.vn."""
        start_time = time.time()
        total_collected = 0
        total_deduped = 0
        total_failed = 0
        errors = []

        source_record = self.get_source_record()
        tracker = ProvenanceTracker(self.db)

        listing_types = ["ban", "thue"]

        for listing_type in listing_types:
            urls = self._build_urls(district_slug, province, listing_type)

            for base_url in urls:
                # Detect type from URL
                prop_type = self._detect_property_type("", base_url)

                for page in range(1, max_pages + 1):
                    url = f"{base_url}" if page == 1 else f"{base_url}?page={page}"

                    result = self._fetch(url)
                    if result.error:
                        errors.append(f"Page {page} ({listing_type}): {result.error}")
                        continue

                    listings = self._parse_listing_page(result.html, url)
                    if not listings:
                        break  # No more pages

                    for listing in listings:
                        try:
                            dedup_key = _compute_dedup_key(
                                listing.get("url", ""),
                                listing.get("price"),
                                listing.get("area"),
                            )

                            existing = (
                                self.db.query(Property)
                                .filter(Property.source_etag == dedup_key)
                                .first()
                            )
                            if existing:
                                total_deduped += 1
                                continue

                            # Fetch detail
                            detail_result = self._fetch(listing.get("url", ""))
                            detail = self._parse_detail_page(
                                detail_result.html
                            ) if not detail_result.error else {}

                            prop_type = listing.get("property_type", prop_type)

                            property_data = self._map_to_bds_property(
                                listing=listing,
                                detail=detail,
                                province=province,
                                district_name=district_name,
                                prop_type=prop_type,
                                source_key=dedup_key,
                            )

                            # Sanitize before insert
                            try:
                                from src.backend.data_sanitizer import PropertySanitizer
                                sanitizer = PropertySanitizer(strict_scope=False)
                                property_data = sanitizer.sanitize(property_data)
                            except Exception:
                                total_failed += 1
                                continue

                            prop = Property(**property_data)
                            self.db.add(prop)
                            self.db.flush()

                            # Provenance
                            step1 = tracker.add_step(
                                property_id=prop.id,
                                step=ProvenanceStep.CRAWLED,
                                actor=ProvenanceActor.SCRAPER,
                                source=listing.get("url", ""),
                                input_data={"url": listing.get("url", ""), "page": page},
                                output_data={"status_code": detail_result.status_code, "html_len": len(detail_result.html) if detail_result.html else 0},
                                metadata={"source_domain": self.source_key, "district": district_slug, "listing_type": listing_type},
                                verify_url=listing.get("url", ""),
                            )
                            tracker.add_step(
                                property_id=prop.id,
                                step=ProvenanceStep.PARSED,
                                actor=ProvenanceActor.SCRAPER,
                                input_data={"raw_len": len(detail_result.html) if detail_result.html else 0},
                                output_data=detail or {},
                                metadata={"parser_version": "bds_v1", "fields_extracted": list((detail or {}).keys())},
                                prev_step_id=step1.id,
                            )
                            tracker.add_step(
                                property_id=prop.id,
                                step=ProvenanceStep.IMPORTED,
                                actor=ProvenanceActor.SYSTEM,
                                input_data={"property_data": {k: v for k, v in property_data.items() if k != "raw_source_content"}},
                                output_data={"property_id": prop.id},
                                metadata={"source": "batdongsan_scrape"},
                                prev_step_id=step1.id,
                            )

                            total_collected += 1
                            if progress_callback:
                                progress_callback(prop.id, total_collected, listing.get("url", ""))

                        except Exception as e:
                            errors.append(f"Listing {listing.get('url', '')}: {str(e)}")
                            total_failed += 1
                            continue

        self.db.commit()

        if source_record:
            source_record.total_records += total_collected
            source_record.successful_records += total_collected
            source_record.failed_records += total_failed
            source_record.last_run_at = datetime.now()
            source_record.last_run_status = "success" if total_collected > 0 else "failed"

        return CollectResult(
            success=total_collected > 0,
            records_collected=total_collected,
            records_deduped=total_deduped,
            records_failed=total_failed,
            duration_seconds=time.time() - start_time,
            error="; ".join(errors[:5]) if errors else None,
        )

    def _map_to_bds_property(
        self,
        listing: Dict,
        detail: Optional[Dict],
        province: str,
        district_name: str,
        prop_type: str,
        source_key: str,
    ) -> Dict:
        """Map Batdongsan data to Property model."""
        price = listing.get("price") or (
            _parse_vietnam_price(detail.get("price_text", "")) if detail else None
        ) or 0.0
        area = listing.get("area") or (
            _parse_vietnam_area(detail.get("area_text", "")) if detail else None
        ) or 0.0

        address = (
            detail.get("address", "") if detail else listing.get("location_text", "")
        )

        # Parse bedrooms from description/title
        bedrooms = _parse_vietnam_bedrooms(
            (detail or listing).get("title", "") + " " +
            (detail or listing).get("description", "")
        )

        data = {
            "property_type": prop_type,
            "province_city": province,
            "district": district_name,
            "ward": None,
            "street_or_project": address or None,
            "area_m2": area,
            "bedrooms": bedrooms,
            "bathrooms": 0,
            "floor_count": 1,
            "frontage_m": None,
            "legal_status": "pending",
            "furnishing": None,
            "price": price,
            "price_per_m2": round(price / area, 0) if price and area else None,
            "listing_date": datetime.now(),
            "latitude": None,
            "longitude": None,
            "area_type": "urban_center",
            "source_name": self.source_config["name"],
            "source_url": listing.get("url", ""),
            "source_page_title": (detail or listing).get("title", listing.get("title", "")),
            "source_collected_at": datetime.now(),
            "source_access_method": "scraper",
            "data_collection_status": DataCollectionStatus.COLLECTED.value,
            "collection_attempt_count": 1,
            "last_collection_attempt": datetime.now(),
            "data_origin_type": "public_collected",
            "record_status": "pending_review",
            "verification_status": "unverified",
            "description": (detail or {}).get("description", ""),
            "source_domain": self.source_key,
            "source_category": "scraper",
            "source_crawl_at": datetime.now(),
            "source_etag": source_key,
            "raw_source_content": json.dumps({
                "listing_url": listing.get("url", ""),
                "listing_page": "batdongsan_scrape",
                "parsed": detail or {},
            }, ensure_ascii=False),
        }

        img_url = listing.get("image_url")
        img_urls = (detail or {}).get("image_urls", [])
        if img_url:
            data["image_url"] = img_url
        if img_urls:
            data["image_urls"] = json.dumps(img_urls[:10])

        # Evidence tier
        tier = self._assign_scraped_tier(data)
        data["evidence_tier"] = tier
        data["evidence_tier_updated_at"] = datetime.now()

        return data


# ==============================================================================
# GENERIC SCRAPER COLLECTOR
# ==============================================================================

class GenericScraperCollector(BaseCollector):
    """
    Generic collector dùng selector config từ APPROVED_SOURCES.
    Dùng cho: nhatot.com, muaban.net, rever.vn và các nguồn có cùng cấu trúc HTML.
    """

    def __init__(self, source_key: str, db: Session):
        config = get_approved_source(source_key)
        if not config:
            raise ValueError(f"Nguồn {source_key} không được phê duyệt")
        super().__init__(source_key, config, db)

    def _detect_property_type(self, title: str, url: str) -> str:
        combined = (title + " " + url).lower()
        if any(k in combined for k in ["căn hộ", "apartment", "chung cư", "condo"]):
            return "apartment"
        if any(k in combined for k in ["đất", "land", "nền"]):
            return "land"
        if any(k in combined for k in ["biệt thự", "villa"]):
            return "villa"
        if any(k in combined for k in ["nhà phố", "townhouse", "liền kề"]):
            return "townhouse"
        if any(k in combined for k in ["nhà", "house", "home"]):
            return "house"
        return "house"

    def _parse_listing_page(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, "html.parser")
        selectors = self.source_config.get("selectors", {})
        container_sel = selectors.get("listing_container", None)
        item_sel = selectors.get("listing_item", ".item")

        if container_sel:
            container = soup.select_one(container_sel)
            items = container.select(item_sel) if container else []
        else:
            items = soup.select(item_sel)

        listings = []
        for item in items:
            try:
                title_el = item.select_one(selectors.get("title", "a"))
                title = title_el.get_text(strip=True) if title_el else ""
                url = title_el.get("href", "") if title_el else ""
                if url and not url.startswith("http"):
                    url = urljoin(self.source_config["base_url"], url)

                price_el = item.select_one(selectors.get("price", ".price"))
                price_text = price_el.get_text(strip=True) if price_el else ""
                price = _parse_vietnam_price(price_text)

                area_el = item.select_one(selectors.get("area", ".area, .square"))
                area_text = area_el.get_text(strip=True) if area_el else ""
                area = _parse_vietnam_area(area_text)

                addr_el = item.select_one(selectors.get("address", ".address, .location"))
                address = addr_el.get_text(strip=True) if addr_el else ""

                img_el = item.select_one(selectors.get("image", "img"))
                img_url = img_el.get("src") or img_el.get("data-src", "") if img_el else ""

                prop_type = self._detect_property_type(title, url)

                if url:
                    listings.append({
                        "title": title,
                        "url": url,
                        "price_text": price_text,
                        "price": price,
                        "area_text": area_text,
                        "area": area,
                        "location_text": address,
                        "image_url": img_url,
                        "property_type": prop_type,
                    })
            except Exception:
                continue
        return listings

    def _parse_detail_page(self, html: str) -> Optional[Dict]:
        soup = BeautifulSoup(html, "html.parser")
        data = {}

        title_el = soup.select_one("h1, .title, .detail-title")
        data["title"] = title_el.get_text(strip=True) if title_el else ""

        price_el = soup.select_one("[class*=price], .price-value")
        price_text = price_el.get_text(strip=True) if price_el else ""
        data["price"] = _parse_vietnam_price(price_text)

        area_el = soup.select_one("[class*=area], .square, .size")
        area_text = area_el.get_text(strip=True) if area_el else ""
        data["area_m2"] = _parse_vietnam_area(area_text)

        addr_el = soup.select_one(".address, [class*=address], .location")
        data["address"] = addr_el.get_text(strip=True) if addr_el else ""

        desc_el = soup.select_one(".description, .content, [class*=content]")
        data["description"] = desc_el.get_text(strip=True)[:2000] if desc_el else ""

        img_els = soup.select("img")
        data["image_urls"] = [
            img.get("src") or img.get("data-src", "")
            for img in img_els[:10] if img.get("src")
        ]

        return data

    def collect_district(
        self,
        province: str,
        district_name: str,
        district_slug: str,
        property_types: List[str],
        max_pages: int = 20,
        progress_callback=None,
    ) -> CollectResult:
        start_time = time.time()
        total_collected = 0
        total_deduped = 0
        total_failed = 0
        errors = []

        source_record = self.get_source_record()
        tracker = ProvenanceTracker(self.db)

        base_url = self.source_config["base_url"]
        pagination = self.source_config.get("pagination", {})
        param = pagination.get("param", "page")

        for page in range(1, max_pages + 1):
            url = f"{base_url}?{param}={page}" if page > 1 else base_url

            result = self._fetch(url)
            if result.error:
                errors.append(f"Page {page}: {result.error}")
                continue

            listings = self._parse_listing_page(result.html)
            if not listings:
                break  # Hết trang

            for listing in listings:
                try:
                    dedup_key = _compute_dedup_key(
                        listing.get("url", ""),
                        listing.get("price"),
                        listing.get("area"),
                    )

                    existing = (
                        self.db.query(Property)
                        .filter(Property.source_etag == dedup_key)
                        .first()
                    )
                    if existing:
                        total_deduped += 1
                        continue

                    detail_result = self._fetch(listing.get("url", ""))
                    detail = self._parse_detail_page(
                        detail_result.html
                    ) if not detail_result.error else {}

                    address = (
                        detail.get("address", "") if detail
                        else listing.get("location_text", "")
                    )

                    data = {
                        "property_type": listing.get("property_type", "house"),
                        "province_city": province,
                        "district": district_name,
                        "ward": None,
                        "street_or_project": address or None,
                        "area_m2": listing.get("area") or 0,
                        "bedrooms": _parse_vietnam_bedrooms(listing.get("title", "")),
                        "bathrooms": 0,
                        "floor_count": 1,
                        "frontage_m": None,
                        "legal_status": "pending",
                        "furnishing": None,
                        "price": listing.get("price") or 0.0,
                        "price_per_m2": round(
                            (listing.get("price") or 0) / (listing.get("area") or 1), 0
                        ) if listing.get("area") else None,
                        "listing_date": datetime.now(),
                        "latitude": None,
                        "longitude": None,
                        "area_type": "urban_center",
                        "source_name": self.source_config["name"],
                        "source_url": listing.get("url", ""),
                        "source_page_title": listing.get("title", ""),
                        "source_collected_at": datetime.now(),
                        "source_access_method": "scraper",
                        "data_collection_status": DataCollectionStatus.COLLECTED.value,
                        "collection_attempt_count": 1,
                        "last_collection_attempt": datetime.now(),
                        "data_origin_type": "public_collected",
                        "record_status": "pending_review",
                        "verification_status": "unverified",
                        "description": (detail or {}).get("description", ""),
                        "source_domain": self.source_key,
                        "source_category": "scraper",
                        "source_crawl_at": datetime.now(),
                        "source_etag": dedup_key,
                        "raw_source_content": json.dumps({
                            "listing_url": listing.get("url", ""),
                            "parsed": detail or {},
                        }, ensure_ascii=False),
                    }

                    img_url = listing.get("image_url")
                    img_urls = (detail or {}).get("image_urls", [])
                    if img_url:
                        data["image_url"] = img_url
                    if img_urls:
                        data["image_urls"] = json.dumps(img_urls[:10])

                    tier = self._assign_scraped_tier(data)
                    data["evidence_tier"] = tier
                    data["evidence_tier_updated_at"] = datetime.now()

                    prop = Property(**data)
                    self.db.add(prop)
                    self.db.flush()

                    step1 = tracker.add_step(
                        property_id=prop.id,
                        step=ProvenanceStep.CRAWLED,
                        actor=ProvenanceActor.SCRAPER,
                        source=listing.get("url", ""),
                        input_data={"url": listing.get("url", "")},
                        output_data={"status_code": detail_result.status_code},
                        metadata={"source_domain": self.source_key, "district": district_slug},
                        verify_url=listing.get("url", ""),
                    )
                    tracker.add_step(
                        property_id=prop.id,
                        step=ProvenanceStep.PARSED,
                        actor=ProvenanceActor.SCRAPER,
                        input_data={"raw_len": len(detail_result.html) if detail_result.html else 0},
                        output_data=detail or {},
                        metadata={"fields": list((detail or {}).keys())},
                        prev_step_id=step1.id,
                    )
                    tracker.add_step(
                        property_id=prop.id,
                        step=ProvenanceStep.IMPORTED,
                        actor=ProvenanceActor.SYSTEM,
                        input_data={"property_id": prop.id},
                        output_data={"imported": True},
                        metadata={"source": self.source_key},
                        prev_step_id=step1.id,
                    )

                    total_collected += 1
                    if progress_callback:
                        progress_callback(prop.id, total_collected, listing.get("url", ""))

                except Exception as e:
                    errors.append(f"Listing {listing.get('url', '')}: {str(e)}")
                    total_failed += 1
                    continue

        self.db.commit()

        if source_record:
            source_record.total_records += total_collected
            source_record.successful_records += total_collected
            source_record.failed_records += total_failed
            source_record.last_run_at = datetime.now()
            source_record.last_run_status = "success" if total_collected > 0 else "failed"

        return CollectResult(
            success=total_collected > 0,
            records_collected=total_collected,
            records_deduped=total_deduped,
            records_failed=total_failed,
            duration_seconds=time.time() - start_time,
            error="; ".join(errors[:5]) if errors else None,
        )


# ==============================================================================
# CROSS-SOURCE VALIDATION
# ==============================================================================

class CrossSourceValidator:
    """
    Cross-validate properties across multiple sources.
    Khi 1 BĐS xuất hiện ở 2+ nguồn → tăng tier lên E1/E2.
    Khi giá conflict giữa sources → flag để review.
    """

    # Weight for type-match scoring
    ADDRESS_MATCH_WEIGHTS = {
        "exact": 1.0,    # Same ward + street
        "district": 0.7,  # Same district, diff street
        "proximity": 0.4,  # Within 500m (lat/lng proximity)
    }

    def __init__(self, db: Session):
        self.db = db

    def find_cross_source_duplicates(self, new_property: Property) -> List[Property]:
        """
        Find potential duplicates of new_property in other sources.
        Returns list of matching properties with source confirmation count.
        """
        candidates = (
            self.db.query(Property)
            .filter(
                Property.property_type == new_property.property_type,
                Property.district == new_property.district,
                Property.province_city == new_property.province_city,
                Property.data_origin_type == "public_collected",
            )
            .all()
        )

        matches = []
        for cand in candidates:
            if cand.source_domain == new_property.source_domain:
                continue  # Same source — handled by etag dedup
            if cand.source_etag == new_property.source_etag:
                continue

            score = self._compute_match_score(new_property, cand)
            if score >= 0.7:
                matches.append(cand)

        return matches

    def _compute_match_score(self, a: Property, b: Property) -> float:
        """
        Compute match score between two properties.
        Returns 0-1 based on field agreement.
        """
        score = 0.0
        weights = []

        # Area match (weight: 0.3)
        if a.area_m2 and b.area_m2:
            area_diff = abs(a.area_m2 - b.area_m2) / max(a.area_m2, b.area_m2)
            if area_diff < 0.05:
                score += 0.3
            elif area_diff < 0.15:
                score += 0.15
            weights.append(0.3)

        # Price match (weight: 0.4)
        if a.price and b.price:
            price_diff = abs(a.price - b.price) / max(a.price, b.price)
            if price_diff < 0.05:
                score += 0.4
            elif price_diff < 0.15:
                score += 0.2
            elif price_diff < 0.30:
                score += 0.05  # Price conflict — potential fraud signal
            weights.append(0.4)

        # Address match (weight: 0.3)
        a_addr = (a.ward or "") + " " + (a.street_or_project or "")
        b_addr = (b.ward or "") + " " + (b.street_or_project or "")
        a_words = set(a_addr.lower().split())
        b_words = set(b_addr.lower().split())
        if a_words and b_words:
            overlap = len(a_words & b_words) / max(len(a_words), len(b_words))
            if overlap >= 0.6:
                score += 0.3 * overlap
            weights.append(0.3)

        return min(score, 1.0)

    def cross_validate_batch(self, property_ids: List[int]) -> Dict[int, Dict]:
        """
        Cross-validate a batch of properties.
        Returns dict mapping property_id → validation_result.
        """
        results = {}

        for pid in property_ids:
            prop = self.db.query(Property).filter(Property.id == pid).first()
            if not prop:
                continue

            matches = self.find_cross_source_duplicates(prop)
            sources = list(set(m.source_domain for m in matches))
            sources.append(prop.source_domain)

            # Price agreement check
            prices = [prop.price] + [m.price for m in matches if m.price]
            price_agree = len({round(p / 100_000_000, 1) for p in prices if p}) <= 2  # Within 100M VND

            has_conflict = len(prices) > 1 and not price_agree

            # Promote tier if cross-source confirmed
            new_tier = None
            if len(sources) >= 2 and prop.evidence_tier not in ["E1", "E2"]:
                if has_conflict:
                    new_tier = "E2"  # Multi-source but conflict → E2
                else:
                    new_tier = "E1"  # Multi-source, price agree → E1

            results[pid] = {
                "sources": sources,
                "match_count": len(matches),
                "has_conflict": has_conflict,
                "new_tier": new_tier,
                "price_agree": price_agree,
            }

            if new_tier:
                old_tier = prop.evidence_tier
                prop.evidence_tier = new_tier
                prop.evidence_tier_updated_at = datetime.now()
                results[pid]["old_tier"] = old_tier

        self.db.commit()
        return results


# ==============================================================================
# COLLECTION SERVICE
# ==============================================================================

class DataCollectionService:
    """
    Dịch vụ thu thập dữ liệu chính.
    Điều phối tất cả collectors và pipeline.
    """

    def __init__(self, db: Session):
        self.db = db
        self.collectors: Dict[str, BaseCollector] = {}
        self._init_collectors()

    def _init_collectors(self):
        """Khởi tạo collectors cho các nguồn được phê duyệt."""
        for domain, config in APPROVED_SOURCES.items():
            if config.get("type") == "scraper":
                if "alonhadat" in domain:
                    self.collectors[domain] = AlonhadatCollector(self.db)
                elif "batdongsan" in domain:
                    self.collectors[domain] = BatdongsanCollector(self.db)
                else:
                    # Generic: nhatot, muaban, rever, và các nguồn khác
                    try:
                        self.collectors[domain] = GenericScraperCollector(domain, self.db)
                    except ValueError:
                        pass  # Skip if not in APPROVED_SOURCES

    def collect(
        self,
        source: str,
        province: Optional[str] = None,
        district: Optional[str] = None,
        max_pages: int = 20,
        progress_callback=None,
    ) -> CollectResult:
        """
        Thu thập từ 1 nguồn.

        Args:
            source: Domain của nguồn (e.g., "alonhadat.com.vn")
            province: Tỉnh/TP (e.g., "Hà Nội")
            district: Quận/Huyện (e.g., "Quận Cầu Giấy")
            max_pages: Số trang tối đa/quận
            progress_callback: Callback để report progress

        Returns:
            CollectResult
        """
        # Validate source
        if is_source_prohibited(source):
            return CollectResult(
                success=False,
                records_collected=0,
                records_deduped=0,
                records_failed=0,
                duration_seconds=0,
                error=f"Nguồn {source} bị cấm",
            )

        config = get_approved_source(source)
        if not config:
            return CollectResult(
                success=False,
                records_collected=0,
                records_deduped=0,
                records_failed=0,
                duration_seconds=0,
                error=f"Nguồn {source} không được phê duyệt",
            )

        # Get collector
        collector = self.collectors.get(source)
        if not collector:
            return CollectResult(
                success=False,
                records_collected=0,
                records_deduped=0,
                records_failed=0,
                duration_seconds=0,
                error=f"Không có collector cho {source}",
            )

        # Collect
        districts_config = config.get("districts", {})

        if province and district:
            # Collect 1 quận
            province_config = districts_config.get(province, {})
            district_config = None
            for slug, d_cfg in province_config.items():
                if d_cfg.get("name") == district or slug == district.lower().replace(" ", "-"):
                    district_config = {slug: d_cfg}
                    province_config = {province: district_config[slug]}
                    break
            if not district_config:
                return CollectResult(
                    success=False, records_collected=0, records_deduped=0,
                    records_failed=0, duration_seconds=0,
                    error=f"Không tìm thấy quận {district} trong {province}",
                )

            return collector.collect_district(
                province=province,
                district_name=district,
                district_slug=list(district_config.keys())[0],
                property_types=list(district_config.values())[0].get("property_types", ["house"]),
                max_pages=max_pages,
                progress_callback=progress_callback,
            )

        elif province:
            # Collect all districts in province
            province_config = districts_config.get(province, {})
            all_results = []
            for slug, d_cfg in province_config.items():
                result = collector.collect_district(
                    province=province,
                    district_name=d_cfg.get("name", slug),
                    district_slug=slug,
                    property_types=d_cfg.get("property_types", ["house"]),
                    max_pages=max_pages,
                    progress_callback=progress_callback,
                )
                all_results.append(result)

            return CollectResult(
                success=any(r.success for r in all_results),
                records_collected=sum(r.records_collected for r in all_results),
                records_deduped=sum(r.records_deduped for r in all_results),
                records_failed=sum(r.records_failed for r in all_results),
                duration_seconds=sum(r.duration_seconds for r in all_results),
            )

        else:
            # Collect all approved districts
            all_results = []
            for prov, districts_dict in districts_config.items():
                for slug, d_cfg in districts_dict.items():
                    result = collector.collect_district(
                        province=prov,
                        district_name=d_cfg.get("name", slug),
                        district_slug=slug,
                        property_types=d_cfg.get("property_types", ["house"]),
                        max_pages=max_pages,
                        progress_callback=progress_callback,
                    )
                    all_results.append(result)

            return CollectResult(
                success=any(r.success for r in all_results),
                records_collected=sum(r.records_collected for r in all_results),
                records_deduped=sum(r.records_deduped for r in all_results),
                records_failed=sum(r.records_failed for r in all_results),
                duration_seconds=sum(r.duration_seconds for r in all_results),
            )

    def run_production_scrape(
        self,
        max_pages: int = 20,
        target_domain: Optional[str] = None,
        dry_run: bool = False,
    ) -> int:
        """
        Chạy production scrape trên tất cả sources × districts.
        Đây là method chính được gọi bởi run_collector.py.

        Args:
            max_pages: Số trang tối đa mỗi quận mỗi nguồn
            target_domain: Nếu set chỉ scrape 1 domain (e.g. "alonhadat.com.vn")
            dry_run: True = đếm potential records không insert DB

        Returns:
            Tổng số records mới (hoặc potential count nếu dry_run)
        """
        import io
        import sys

        six_districts = [
            ("Hà Nội", "cau-giay", "Quận Cầu Giấy"),
            ("Hà Nội", "thanh-xuan", "Quận Thanh Xuân"),
            ("Hà Nội", "dong-da", "Quận Đống Đa"),
            ("TP. Hồ Chí Minh", "quan-7", "Quận 7"),
            ("TP. Hồ Chí Minh", "binh-thanh", "Quận Bình Thạnh"),
            ("TP. Hồ Chí Minh", "tan-binh", "Quận Tân Bình"),
        ]

        # Xác định domains cần scrape
        if target_domain:
            domains = [target_domain] if target_domain in get_all_approved_domains() else []
        else:
            domains = [
                d for d in get_all_approved_domains()
                if get_approved_source(d).get("type") == "scraper"
            ]

        if not domains:
            print("⚠️  Không có scraper domain nào được cấu hình")
            return 0

        total_records = 0
        total_deduped = 0
        total_failed = 0
        grand_start = time.time()

        for domain in domains:
            print(f"\n🌐 Scraping: {domain}")
            print("-" * 50)

            for prov, slug, dist_name in six_districts:
                start = time.time()
                print(f"  📍 {dist_name}, {prov}... ", end="", flush=True)

                # Dry-run: chỉ parse HTML không insert
                if dry_run:
                    collector = self.collectors.get(domain)
                    if not collector:
                        print("no collector")
                        continue

                    try:
                        # Gọi trực tiếp để đếm potential records
                        result = collector.collect_district(
                            province=prov,
                            district_name=dist_name,
                            district_slug=slug,
                            property_types=["house", "apartment", "land"],
                            max_pages=max_pages,
                            progress_callback=None,
                        )
                        total_records += result.records_collected
                        elapsed = time.time() - start
                        print(f"found {result.records_collected} (dry-run, {elapsed:.1f}s)")
                    except Exception as e:
                        print(f"error: {e}")
                        total_failed += 1
                else:
                    # Live scrape: insert vào DB
                    result = self.collect(
                        source=domain,
                        province=prov,
                        district=dist_name,
                        max_pages=max_pages,
                    )
                    total_records += result.records_collected
                    total_deduped += result.records_deduped
                    total_failed += result.records_failed
                    elapsed = time.time() - start
                    status = "✅" if result.success else "❌"
                    print(
                        f"{status} +{result.records_collected} "
                        f"(dup:{result.records_deduped}, fail:{result.records_failed}, {elapsed:.1f}s)"
                    )

        grand_elapsed = time.time() - grand_start
        print(f"\n🏁 Production scrape complete!")
        print(f"   Total new records: {total_records}")
        print(f"   Total duplicated: {total_deduped}")
        print(f"   Total failed:     {total_failed}")
        print(f"   Total time:       {grand_elapsed:.1f}s")

        return total_records

    # ==============================================================================
    # EVIDENCE TIER ASSIGNMENT — CVX-BDS/IoT 1.1-VN
    # ==============================================================================

    def assign_evidence_tier(self, prop_data: Dict) -> str:
        """
        Assign evidence tier (E1-E5) dựa trên dữ liệu thực tế có trong bản ghi.

        Evidence Tier = thước đo CHẤT LƯỢNG BẰNG CHỨNG cho giá trị BĐS.
        Không phải giá trị BĐS, không phải độ tin cậy nguồn.

        SCRAPED (public_collected):
          E1: Đầy đủ — price, area, address, district, province,
              bedrooms+bathrooms+floor_count, legal_status, image_url, source_url
          E2: Khá đầy đủ — price, area, address, district, province + ≥3 trường room/floor/legal
          E3: Cơ bản đầy đủ — price, area, address, district, province + ≥1 trường bổ sung
          E4: Có price + area + address/district + province (không rõ địa chỉ cụ thể)
          E5: Tối thiểu — chỉ price + area, không có address

        SELF_COLLECTED (field_survey):
          Điểm số từ bằng chứng có thật:
            GPS coordinates:     +3 điểm
            Ảnh hiện trường:     +2 điểm
            Surveyor name:       +1 điểm
            Timestamp:           +1 điểm
            Address verified:     +2 điểm
            Field notes:         +1 điểm
            Legal docs:          +2 điểm
            Device info:         +1 điểm

            E1: ≥7 điểm    (E1-E4 trong CVX-BDS)
            E2: 5-6 điểm
            E3: 4 điểm
            E4: 2-3 điểm
            E5: <2 điểm   (không đủ threshold)
        """
        origin = prop_data.get("data_origin_type", "public_collected")

        if origin == "self_collected":
            return self._assign_self_collected_tier(prop_data)
        else:
            return self._assign_scraped_tier(prop_data)

    def _assign_scraped_tier(self, prop_data: Dict) -> str:
        """
        Assign evidence tier for scraped/public records.
        E5: no ward/street (district-only)
        E4: has ward/street but 0 extra fields
        E3: has ward/street + 1 extra field
        E2: has ward/street + 2-4 extra fields
        E1: has ward/street + all 5 extra fields (image+source+rooms+floors+legal)
        """
        has_price = (prop_data.get("price") or 0) > 0
        has_area = (prop_data.get("area_m2") or 0) > 0
        if not (has_price and has_area):
            return "E5"
        if not (prop_data.get("province_city") and prop_data.get("district")):
            return "E5"

        # Ward/street = specific address. Without it = E5.
        has_ward_or_street = bool(
            prop_data.get("ward") or prop_data.get("street_or_project")
        )
        if not has_ward_or_street:
            return "E5"

        has_image = bool(prop_data.get("image_url") or prop_data.get("image_urls"))
        has_source_url = bool(prop_data.get("source_url"))
        has_rooms = (prop_data.get("bedrooms") or 0) > 0
        has_floors = (prop_data.get("floor_count") or 0) > 0
        has_legal = bool(prop_data.get("legal_status")) and prop_data.get("legal_status") not in ["pending", "unknown"]

        extra_count = sum([has_image, has_source_url, has_rooms, has_floors, has_legal])

        if extra_count == 0:
            return "E4"
        if extra_count == 1:
            return "E3"
        if extra_count >= 2 and extra_count <= 4:
            return "E2"
        if has_image and has_source_url and has_rooms and has_floors and has_legal:
            return "E1"
        return "E2"

    def _assign_self_collected_tier(self, prop_data: Dict) -> str:
        """Assign tier cho self-collected (field survey) records."""
        score = 0

        # GPS coordinates (THỰC — không simulated)
        if prop_data.get("gps_lat") and prop_data.get("gps_lng"):
            score += 3

        # Ảnh hiện trường (URL thực)
        photos = prop_data.get("field_photos") or prop_data.get("image_urls") or prop_data.get("image_url")
        if photos:
            score += 2

        # Surveyor name (thực)
        if prop_data.get("collected_by"):
            score += 1

        # Timestamp (thực)
        if prop_data.get("collected_at") or prop_data.get("capture_time"):
            score += 1

        # Address verified
        if prop_data.get("street_or_project") or prop_data.get("ward"):
            score += 2

        # Field notes
        if prop_data.get("field_notes") or prop_data.get("field_note"):
            score += 1

        # Legal docs
        if prop_data.get("legal_status") in ["ownership_certificate", "land_use_right_certificate"]:
            score += 2

        # Device info
        if prop_data.get("phone_device") or prop_data.get("iot_device_id"):
            score += 1

        # Map score to tier
        if score >= 7:
            return "E1"
        elif score >= 5:
            return "E2"
        elif score >= 4:
            return "E3"
        elif score >= 2:
            return "E4"
        else:
            return "E5"

    def recompute_all_tiers(self):
        """Recompute evidence tiers cho toàn bộ records trong DB."""
        props = self.db.query(Property).all()
        updated = 0
        for prop in props:
            prop_dict = {
                "data_origin_type": prop.data_origin_type,
                "price": prop.price,
                "area_m2": prop.area_m2,
                "province_city": prop.province_city,
                "district": prop.district,
                "ward": prop.ward,
                "street_or_project": prop.street_or_project,
                "image_url": prop.image_url,
                "image_urls": prop.image_urls,
                "source_url": prop.source_url,
                "bedrooms": prop.bedrooms,
                "bathrooms": prop.bathrooms,
                "floor_count": prop.floor_count,
                "legal_status": prop.legal_status,
                # Self-collected
                "gps_lat": prop.gps_lat,
                "gps_lng": prop.gps_lng,
                "field_photos": prop.field_photos,
                "collected_by": prop.collected_by,
                "collected_at": prop.collected_at,
                "capture_time": prop.capture_time,
                "field_notes": prop.field_notes,
                "field_note": prop.field_note,
                "phone_device": prop.phone_device,
                "iot_device_id": prop.iot_device_id,
            }
            tier = self.assign_evidence_tier(prop_dict)
            if prop.evidence_tier != tier:
                prop.evidence_tier = tier
                prop.evidence_tier_updated_at = datetime.now()
                updated += 1
        self.db.commit()
        return updated

    def get_collection_stats(self) -> Dict[str, Any]:
        """Lấy thống kê collection."""
        total = self.db.query(Property).count()
        by_origin = {}
        for origin in ["public_collected", "self_collected"]:
            count = self.db.query(Property).filter(
                Property.data_origin_type == origin
            ).count()
            by_origin[origin] = count

        by_status = {}
        for status in ["raw", "pending_review", "verified", "rejected", "archived"]:
            count = self.db.query(Property).filter(
                Property.record_status == status
            ).count()
            by_status[status] = count

        by_source = {}
        for domain in get_all_approved_domains():
            count = self.db.query(Property).filter(
                Property.source_domain == domain
            ).count()
            if count > 0:
                by_source[domain] = count

        by_district = {}
        allowed = [
            ("Hà Nội", "Quận Cầu Giấy"),
            ("Hà Nội", "Quận Thanh Xuân"),
            ("Hà Nội", "Quận Đống Đa"),
            ("TP. Hồ Chí Minh", "Quận 7"),
            ("TP. Hồ Chí Minh", "Quận Bình Thạnh"),
            ("TP. Hồ Chí Minh", "Quận Tân Bình"),
        ]
        for prov, dist in allowed:
            count = self.db.query(Property).filter(
                Property.province_city == prov,
                Property.district == dist,
            ).count()
            by_district[f"{prov} - {dist}"] = count

        return {
            "total_properties": total,
            "by_origin": by_origin,
            "by_status": by_status,
            "by_source": by_source,
            "by_allowed_district": by_district,
            "self_collected_ratio": round(by_origin.get("self_collected", 0) / total * 100, 2) if total > 0 else 0,
        }

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Lấy thống kê chi tiết bao gồm evidence tier distribution."""
        stats = self.get_collection_stats()

        # Tier distribution
        tier_counts = {}
        tier_by_origin = {"self_collected": {}, "public_collected": {}}
        for tier in ["E1", "E2", "E3", "E4", "E5"]:
            count = self.db.query(Property).filter(Property.evidence_tier == tier).count()
            tier_counts[tier] = count
            for origin in ["self_collected", "public_collected"]:
                c = self.db.query(Property).filter(
                    Property.evidence_tier == tier,
                    Property.data_origin_type == origin,
                ).count()
                tier_by_origin[origin][tier] = c

        # Type distribution
        type_counts = {}
        for ptype in ["land", "apartment", "townhouse", "house", "villa"]:
            count = self.db.query(Property).filter(Property.property_type == ptype).count()
            type_counts[ptype] = count

        total = stats["total_properties"]

        stats["by_evidence_tier"] = tier_counts
        stats["tier_pct"] = {
            tier: round(count / total * 100, 1) if total > 0 else 0
            for tier, count in tier_counts.items()
        }
        stats["tier_by_origin"] = tier_by_origin
        stats["by_property_type"] = type_counts

        # CVX-BDS compliance check
        sc = stats["by_origin"].get("self_collected", 0)
        required_sc = round(total * 0.0462) if total > 0 else 0
        stats["cvx_bds_compliance"] = {
            "self_collected_ok": sc >= required_sc,
            "self_collected_current": sc,
            "self_collected_required": required_sc,
            "self_collected_pct": round(sc / total * 100, 2) if total > 0 else 0,
        }

        # E5 cap check (<10%)
        e5_pct = stats["tier_pct"].get("E5", 0)
        stats["e5_compliance"] = e5_pct < 10

        return stats

    def print_full_stats(self):
        """In thống kê đầy đủ ra console."""
        stats = self.get_detailed_stats()
        total = stats["total_properties"]

        print(f"\n{'='*60}")
        print(f"THỐNG KÊ COLLECTION — REAL DATA ONLY")
        print(f"{'='*60}")
        print(f"Tổng bản ghi: {total}")

        print(f"\n[NGUỒN GỐC]")
        for origin, count in stats["by_origin"].items():
            pct = round(count / total * 100, 1) if total > 0 else 0
            print(f"  {origin}: {count} ({pct}%)")

        print(f"\n[EVIDENCE TIER — PUBLIC DATA]")
        for tier in ["E1", "E2", "E3", "E4", "E5"]:
            count = stats["by_evidence_tier"].get(tier, 0)
            pct = stats["tier_pct"].get(tier, 0)
            ok = "✓" if (tier != "E5" or stats["e5_compliance"]) else "✗"
            print(f"  {ok} {tier}: {count} ({pct}%)")

        print(f"\n[EVIDENCE TIER — SELF-COLLECTED]")
        for tier in ["E1", "E2", "E3", "E4"]:
            count = stats["tier_by_origin"]["self_collected"].get(tier, 0)
            print(f"  {tier}: {count}")

        print(f"\n[LOẠI BĐS]")
        for ptype, count in stats["by_property_type"].items():
            print(f"  {ptype}: {count}")

        print(f"\n[QUẬN]")
        for district, count in stats["by_allowed_district"].items():
            print(f"  {district}: {count}")

        print(f"\n[CVX-BDS COMPLIANCE]")
        comp = stats["cvx_bds_compliance"]
        ok = "✓" if comp["self_collected_ok"] else "✗"
        print(f"  {ok} Self-collected: {comp['self_collected_current']} / {comp['self_collected_required']} required ({comp['self_collected_pct']}%)")
        ok5 = "✓" if stats["e5_compliance"] else "✗"
        print(f"  {ok5} E5 cap (<10%): {stats['tier_pct'].get('E5', 0)}%")
