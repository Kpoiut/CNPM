#!/usr/bin/env python3
"""
Scrape ALONHADAT detail pages for E3-quality data.
Strategy:
1. Get listing URLs from list pages (existing scrape logic)
2. Visit each detail page → extract full specs table + description
3. Build comprehensive field_notes from structured data
4. Save with evidence_tier=E3

Detail page provides:
  - Chiều ngang, chiều dài (dimensions)
  - Số lầu, số phòng ngủ, số phòng vệ sinh
  - Đường trước nhà (frontage width)
  - Hướng nhà
  - Pháp lý (legal status)
  - Mô tả chi tiết (description)
  - Ảnh (image URLs)

Usage:
    python scripts/scrape_alonhadat_detail.py --urls-file urls_to_scrape.txt
    python scripts/scrape_alonhadat_detail.py --scrape-list "Quận Cầu Giấy" --target 30
"""
import argparse
import json
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
import urllib.request
import os

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from playwright.sync_api import sync_playwright
from sqlalchemy import text
from src.backend.database import SessionLocal, init_db
from src.backend.models import Property, ProvenanceChain

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

ALONHADAT_DISTRICTS = {
    "Quận Cầu Giấy": {"province": "Hà Nội", "url": "https://alonhadat.com.vn/can-ban-nha-dat/ha-noi/cau-giay"},
    "Quận Thanh Xuân": {"province": "Hà Nội", "url": "https://alonhadat.com.vn/can-ban-nha-dat/ha-noi/thanh-xuan"},
    "Quận Đống Đa": {"province": "Hà Nội", "url": "https://alonhadat.com.vn/can-ban-nha-dat/ha-noi/dong-da"},
    "Quận 7": {"province": "TP. Hồ Chí Minh", "url": "https://alonhadat.com.vn/nha-dat/can-ban/nha-dat/ho-chi-minh/138/quan-7.html"},
    "Quận Bình Thạnh": {"province": "TP. Hồ Chí Minh", "url": "https://alonhadat.com.vn/nha-dat/can-ban/nha-dat/ho-chi-minh/145/quan-binh-thanh.html"},
    "Quận Tân Bình": {"province": "TP. Hồ Chí Minh", "url": "https://alonhadat.com.vn/nha-dat/can-ban/nha-dat/ho-chi-minh/148/quan-tan-binh.html"},
}


def parse_price(t: str):
    if not t:
        return None
    t = t.lower().strip()
    t = re.sub(r"[^\d.,tỷtriệu]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    m = re.search(r"([\d.,]+)\s*tỷ\s*(\d[\d.,]*)\s*triệu", t)
    if m:
        try:
            return float(m.group(1).replace(",", ".")) * 1e9 + float(m.group(2).replace(",", ".")) * 1e6
        except ValueError:
            pass
    m = re.search(r"([\d.,]+)\s*tỷ", t)
    if m:
        try:
            return float(m.group(1).replace(",", ".")) * 1e9
        except ValueError:
            pass
    m = re.search(r"^([\d.,]+)\s*triệu", t)
    if m:
        try:
            return float(m.group(1).replace(",", ".")) * 1e6
        except ValueError:
            pass
    return None


def parse_area(t: str):
    if not t:
        return None
    m = re.search(r"([\d.,]+)\s*m", t)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            pass
    return None


def parse_specs_table(body_text: str) -> dict:
    """Extract structured specs from the detail page's table."""
    specs = {}

    # Match: Label value pattern (e.g., "Chiều ngang 4,5m")
    patterns = {
        "chiều ngang": r"Chiều ngang\s*([\d.,]+)\s*m",
        "chiều dài": r"Chiều dài\s*([\d.,]+)\s*m",
        "đường trước nhà": r"Đường trước nhà\s*([\d.,]+)\s*m",
        "hướng": r"Hướng\s*(.+)",
        "số lầu": r"Số lầu\s*(\d+)",
        "số tầng": r"Số tầng\s*(\d+)",
        "số phòng ngủ": r"Số phòng ngủ\s*(\d+)",
        "phòng ngủ": r"(\d+)\s*pn|(\d+)\s*phòng ngủ",
        "số phòng vệ sinh": r"Số phòng vệ sinh\s*(\d+)",
        "pháp lý": r"Pháp lý\s*(.+)",
        "loại BDS": r"Loại BDS\s*(.+)",
        "sân thượng": r"Sân thượng\s*(.+)",
        "nhà bếp": r"Nhà bếp\s*(.+)",
        "chỗ để xe": r"Chổ để xe\s*(.+)",
    }

    for key, pattern in patterns.items():
        m = re.search(pattern, body_text, re.IGNORECASE)
        if m:
            specs[key] = m.group(1).strip() if m.lastindex else m.group(0).split(maxsplit=1)[-1].strip()

    return specs


def build_field_notes(specs: dict, description: str, address: str) -> str:
    """Build comprehensive field_notes from extracted data."""
    parts = []

    # Address
    if address:
        parts.append(f"Địa chỉ: {address}")

    # Dimensions
    if specs.get("chiều ngang"):
        parts.append(f"Chiều ngang: {specs['chiều ngang']}m")
    if specs.get("chiều dài"):
        parts.append(f"Chiều dài: {specs['chiều dài']}m")
    if specs.get("đường trước nhà"):
        parts.append(f"Đường trước nhà: {specs['đường trước nhà']}m")

    # Structure
    if specs.get("số lầu") or specs.get("số tầng"):
        parts.append(f"Số tầng: {specs.get('số lầu') or specs.get('số tầng')}")
    if specs.get("số phòng ngủ"):
        parts.append(f"Số phòng ngủ: {specs['số phòng ngủ']}")
    if specs.get("số phòng vệ sinh"):
        parts.append(f"Số phòng vệ sinh: {specs['số phòng vệ sinh']}")

    # Legal
    if specs.get("pháp lý"):
        parts.append(f"Pháp lý: {specs['pháp lý']}")

    # Description (truncated to 500 chars)
    if description:
        desc_clean = description.replace("\n", " ").replace("  ", " ").strip()
        if len(desc_clean) > 500:
            desc_clean = desc_clean[:500] + "..."
        parts.append(f"Mô tả: {desc_clean}")

    return " | ".join(parts)


def parse_type(specs: dict, address: str, description: str) -> str:
    t = (str(specs.get("loại BDS", "")) + " " + (address or "") + " " + (description or "")).lower()
    if any(k in t for k in ["đất", "dat", "nền"]):
        return "land"
    if any(k in t for k in ["nhà phố", "phố", "mặt tiền", "mặt phố"]):
        return "townhouse"
    if any(k in t for k in ["villa", "biệt thự"]):
        return "villa"
    if any(k in t for k in ["căn hộ", "chung cư"]):
        return "apartment"
    if any(k in t for k in ["nhà", "nha"]):
        return "house"
    return "apartment"


def scrape_detail_page(url: str, district: str, province: str, browser_ctx=None) -> dict | None:
    """Visit a detail page and extract all available data."""
    result = {
        "url": url,
        "price": None,
        "area": None,
        "address": "",
        "description": "",
        "specs": {},
        "image_urls": [],
        "listing_date": None,
    }

    if browser_ctx:
        page = browser_ctx
        try:
            page.goto(url, timeout=60000)
            page.wait_for_timeout(6000)
        except Exception:
            return None
    else:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(user_agent=UA, locale="vi-VN")
            page = ctx.new_page()
            page.set_default_timeout(60000)
            try:
                page.goto(url, timeout=60000)
                page.wait_for_timeout(6000)
            except Exception:
                browser.close()
                return None
            browser.close()

    body_text = page.inner_text('body')

    # Price: find "Giá:" pattern
    price_m = re.search(r'Giá:\s*([^\n]+)', body_text)
    if price_m:
        result["price"] = parse_price(price_m.group(1))

    # Area
    area_m = re.search(r'Diện tích:\s*([\d.,]+)\s*m', body_text)
    if area_m:
        result["area"] = float(area_m.group(1).replace(",", "."))

    # Address
    addr_m = re.search(r'Địa chỉ tài sản:\s*\n(.+?)(?:\n\n|\nCác)', body_text, re.DOTALL)
    if addr_m:
        result["address"] = addr_m.group(1).strip().replace("\n", ", ")[:200]

    # Description (between "Thông tin chi tiết" and "Giá:")
    desc_m = re.search(r'Thông tin chi tiết\s*\n\n(.+?)(?=\nGiá:|\nCác thông tin)', body_text, re.DOTALL)
    if desc_m:
        result["description"] = desc_m.group(1).strip()

    # Specs table
    result["specs"] = parse_specs_table(body_text)

    # Images
    imgs = page.query_selector_all('img[src]')
    for img in imgs:
        src = img.get_attribute('src') or ""
        if 'logo' not in src.lower() and 'icon' not in src.lower() and 'banner' not in src.lower():
            if src.startswith('/files/') or 'properties' in src:
                if src.startswith('/'):
                    src = f"https://alonhadat.com.vn{src}"
                result["image_urls"].append(src)

    # Listing date
    date_m = re.search(r'Ngày đăng:\s*(.+)', body_text)
    if date_m:
        result["listing_date"] = date_m.group(1).strip()

    return result


def extract_listing_urls(page, max_count: int = 50) -> list[str]:
    """Extract listing URLs from a list page."""
    all_links = page.query_selector_all('a[href]')
    urls = []
    seen = set()
    for a in all_links:
        href = a.get_attribute('href') or ""
        if not re.search(r'\d{6,}\.html$', href):
            continue
        if href in seen:
            continue
        seen.add(href)
        if href.startswith('/'):
            urls.append(f"https://alonhadat.com.vn{href}")
        else:
            urls.append(href)
        if len(urls) >= max_count:
            break
    return urls


def scrape_district_detail(district: str, db, target: int, verbose: bool = False):
    """Collect detail page data from a district."""
    info = ALONHADAT_DISTRICTS.get(district)
    if not info:
        return 0, 0

    province = info["province"]
    base_url = info["url"]
    found = 0
    saved = 0
    skipped_dup = 0
    skipped_filter = 0
    skipped_no_data = 0
    page_num = 1

    while saved < target and page_num <= 20:
        if page_num == 1:
            url = base_url
        else:
            url = f"{base_url}/trang-{page_num}"

        if verbose:
            print(f"  [{district}] List page {page_num}...", flush=True)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
                )
                ctx = browser.new_context(user_agent=UA, locale="vi-VN")
                page = ctx.new_page()
                page.set_default_timeout(90000)
                resp = page.goto(url, timeout=90000)

                if resp.status not in (200, 201):
                    browser.close()
                    break

                page.wait_for_timeout(8000)

                # Get listing URLs from this page
                listing_urls = extract_listing_urls(page)

                # Also extract price/area from body text for each
                body_text = page.inner_text('body')
                price_area_map = {}
                parts = body_text.split('Giá:')
                for i, part in enumerate(parts[1:], 1):
                    first_line = part.split('\n')[0].strip()
                    price = parse_price(first_line)
                    area_m = re.search(r'Diện tích:\s*([\d.,]+)\s*m', part)
                    area = float(area_m.group(1).replace(",", ".")) if area_m else None
                    price_area_map[i] = (price, area)

                browser.close()

        except Exception as e:
            if verbose:
                print(f"    List page error: {e}")
            page_num += 1
            time.sleep(2)
            continue

        if verbose:
            print(f"    {len(listing_urls)} URLs found")

        if not listing_urls:
            break

        # Now visit each listing URL for detail data
        for listing_url in listing_urls:
            if saved >= target:
                break

            idx = listing_urls.index(listing_url) + 1
            list_price, list_area = price_area_map.get(idx, (None, None))

            if verbose:
                print(f"    [{district}] Visiting: {listing_url[-60:]}")

            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True,
                        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
                    )
                    ctx = browser.new_context(user_agent=UA, locale="vi-VN")
                    detail_page = ctx.new_page()
                    detail_page.set_default_timeout(60000)
                    detail_page.goto(listing_url, timeout=60000)
                    detail_page.wait_for_timeout(5000)

                    data = scrape_detail_page(listing_url, district, province, browser_ctx=detail_page)
                    browser.close()

            except Exception as e:
                if verbose:
                    print(f"      Detail error: {e}")
                continue

            if not data:
                skipped_no_data += 1
                continue

            found += 1

            # Use price/area from list page if detail page didn't extract
            price = data.get("price") or list_price
            area = data.get("area") or list_area

            if not price or price < 100_000_000:
                skipped_filter += 1
                continue
            if not area or area < 10 or area > 1000:
                skipped_filter += 1
                continue

            ppm = round(price / area, -3) if area > 0 else 0
            if ppm < 10_000_000 or ppm > 150_000_000:
                skipped_filter += 1
                continue

            ptype = parse_type(data.get("specs", {}), data.get("address", ""), data.get("description", ""))

            # Build comprehensive field_notes
            field_notes = build_field_notes(
                data.get("specs", {}),
                data.get("description", ""),
                data.get("address", "")
            )

            # Determine tier: E3 if has meaningful measurements, E2 otherwise
            specs = data.get("specs", {})
            has_measurements = any([
                specs.get("chiều ngang"),
                specs.get("chiều dài"),
                specs.get("đường trước nhà"),
                specs.get("số lầu") or specs.get("số tầng"),
                specs.get("số phòng ngủ"),
                specs.get("pháp lý"),
            ])
            tier = "E3" if has_measurements else "E2"

            # Check duplicate
            try:
                existing = db.execute(
                    text("SELECT id FROM properties WHERE source_url = :url"),
                    {"url": listing_url}
                ).fetchone()
                if existing:
                    skipped_dup += 1
                    continue
            except Exception:
                db.rollback()
                continue

            # Save
            try:
                prop = Property(
                    property_type=ptype,
                    province_city=province,
                    district=district,
                    area_m2=area,
                    price=price,
                    price_per_m2=int(ppm),
                    source_name="alonhadat.com.vn",
                    source_url=listing_url,
                    source_domain="alonhadat.com.vn",
                    source_crawl_at=datetime.now(),
                    field_notes=field_notes,
                    data_origin_type="public_collected",
                    record_status="pending_review",
                    verification_status="pending",
                    data_collection_status="collected",
                    collection_attempt_count=1,
                    last_collection_attempt=datetime.now(),
                    collection_method="playwright_stealth",
                    evidence_tier=tier,
                )
                db.add(prop)
                db.flush()

                chain = ProvenanceChain(
                    property_id=prop.id,
                    step="crawled",
                    actor="system:scrape_alonhadat_detail_v1",
                    source=listing_url,
                    input_hash=None,
                    output_hash=None,
                    timestamp=datetime.now(),
                    metadata_json=json.dumps({
                        "scraper": "scrape_alonhadat_detail",
                        "district": district,
                        "province": province,
                        "list_page": page_num,
                        "specs": specs,
                        "listing_date": data.get("listing_date"),
                        "images": data.get("image_urls", [])[:3],
                    }),
                )
                db.add(chain)
                saved += 1

                if verbose:
                    print(f"      -> SAVED ({tier}): price={price/1e9:.2f}t, area={area}m2, ppm={ppm/1e6:.1f}M/m2")
                    print(f"      field_notes: {field_notes[:100]}...")

            except Exception as e:
                if verbose:
                    print(f"      DB error: {e}")
                db.rollback()
                continue

            time.sleep(random.uniform(1.5, 3))

        page_num += 1
        time.sleep(random.uniform(2, 4))

    if verbose:
        print(f"  -> found={found}, saved={saved}, dup={skipped_dup}, filter={skipped_filter}, no_data={skipped_no_data}")
    return found, saved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--district", default=None)
    parser.add_argument("--target", type=int, default=30)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    init_db()

    if args.district:
        districts = [args.district]
    elif args.all:
        districts = list(ALONHADAT_DISTRICTS.keys())
    else:
        print("Specify --district or --all")
        print(f"Available: {list(ALONHADAT_DISTRICTS.keys())}")
        db.close()
        return

    total_found = 0
    total_saved = 0

    print(f"\n{'='*60}")
    print(f" SCRAPE ALONHADAT DETAIL (E3 focus)")
    print(f" Target: {args.target}/district, Districts: {len(districts)}")
    print(f"{'='*60}\n")

    for district in districts:
        print(f"[{district}]...", end=" ", flush=True)
        found, saved = scrape_district_detail(district, db, args.target, verbose=args.verbose)
        total_found += found
        total_saved += saved
        print(f"found={found}, saved={saved}, total={total_saved}")
        try:
            db.commit()
        except Exception as e:
            print(f"  Commit error: {e}")
            db.rollback()

    db.close()

    print(f"\n{'='*60}")
    print(f" COMPLETE: found={total_found}, saved={total_saved}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
