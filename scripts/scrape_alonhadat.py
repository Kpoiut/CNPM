#!/usr/bin/env python3
"""
Scrape real estate listings from alonhadat.com.vn.
batdongsan.com.vn: 403/redirect everywhere → skip
alonhadat.com.vn: WORKING, ~3-5 valid listings/page after filtering

URL patterns:
  HN:   https://alonhadat.com.vn/can-ban-nha-dat/ha-noi/<slug>/
  HCM:  https://alonhadat.com.vn/nha-dat/can-ban/nha-dat/ho-chi-minh/<id>/<slug>.html
  Pagination: /trang-N

Usage:
    python scripts/scrape_alonhadat.py --district "Quận Cầu Giấy" --target 50
    python scripts/scrape_alonhadat.py --all --target 100
"""
import argparse
import json
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

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
    "Quận Cầu Giấy": {
        "province": "Hà Nội",
        "url": "https://alonhadat.com.vn/can-ban-nha-dat/ha-noi/cau-giay",
    },
    "Quận Thanh Xuân": {
        "province": "Hà Nội",
        "url": "https://alonhadat.com.vn/can-ban-nha-dat/ha-noi/thanh-xuan",
    },
    "Quận Đống Đa": {
        "province": "Hà Nội",
        "url": "https://alonhadat.com.vn/can-ban-nha-dat/ha-noi/dong-da",
    },
    "Quận 7": {
        "province": "TP. Hồ Chí Minh",
        "url": "https://alonhadat.com.vn/nha-dat/can-ban/nha-dat/ho-chi-minh/138/quan-7.html",
    },
    "Quận Bình Thạnh": {
        "province": "TP. Hồ Chí Minh",
        "url": "https://alonhadat.com.vn/nha-dat/can-ban/nha-dat/ho-chi-minh/145/quan-binh-thanh.html",
    },
    "Quận Tân Bình": {
        "province": "TP. Hồ Chí Minh",
        "url": "https://alonhadat.com.vn/nha-dat/can-ban/nha-dat/ho-chi-minh/148/quan-tan-binh.html",
    },
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


def parse_type(address: str):
    t = (address or "").lower()
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


def extract_listings_from_page(page):
    """Extract all listings from a list page using body text splitting."""
    all_links = page.query_selector_all('a[href]')
    # Collect listing URLs in order
    listing_urls = []
    seen = set()
    for a in all_links:
        href = a.get_attribute('href') or ""
        if not re.search(r'\d{6,}\.html$', href):
            continue
        if href in seen:
            continue
        seen.add(href)
        if href.startswith('/'):
            listing_urls.append(f"https://alonhadat.com.vn{href}")
        else:
            listing_urls.append(href)

    body_text = page.inner_text('body')
    parts = body_text.split('Giá:')

    listings = []
    for i, part in enumerate(parts[1:], 1):
        first_line = part.split('\n')[0].strip()
        price = parse_price(first_line)
        area_m = re.search(r'Diện tích:\s*([\d.,]+)\s*m', part)
        area = float(area_m.group(1).replace(",", ".")) if area_m else None
        addr_m = re.search(r'Địa chỉ tài sản:\s*\n*(.+?)(?:\n\n|\nĐường|\n )', part)
        address = addr_m.group(1).strip()[:200] if addr_m else ""
        url = listing_urls[i - 1] if i <= len(listing_urls) else ""
        listings.append({"url": url, "price": price, "area": area, "address": address})

    return listings


def scrape_district(district: str, db, target: int, verbose: bool = False):
    """Scrape alonhadat for a specific district."""
    info = ALONHADAT_DISTRICTS.get(district)
    if not info:
        if verbose:
            print(f"  Unknown district: {district}")
        return 0, 0

    province = info["province"]
    base_url = info["url"]
    found = 0
    saved = 0
    skipped_dup = 0
    skipped_filter = 0
    page_num = 1
    errors_in_row = 0

    while saved < target and page_num <= 30:
        if page_num == 1:
            url = base_url
        else:
            url = f"{base_url}/trang-{page_num}"

        if verbose:
            print(f"  [{district}] Page {page_num}: {url}")

        listings = []
        status_code = None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                ctx = browser.new_context(
                    user_agent=UA,
                    locale="vi-VN",
                    extra_http_headers={"Accept-Language": "vi-VN,vi;q=0.9"},
                )
                page = ctx.new_page()
                page.set_default_timeout(90000)
                resp = page.goto(url, timeout=90000)
                status_code = resp.status if resp else None
                page.wait_for_timeout(8000)
                listings = extract_listings_from_page(page)
                browser.close()

        except Exception as e:
            if verbose:
                print(f"    Navigation/extract error: {e}")
            # Rollback any broken transaction
            try:
                db.rollback()
            except Exception:
                pass
            time.sleep(2)
            page_num += 1
            continue

        if verbose:
            print(f"    Status: {status_code}, listings: {len(listings)}")

        if status_code not in (200, 201) or not listings:
            break

        # Process each listing
        for listing in listings:
            if saved >= target:
                break

            url_l = listing["url"]
            price = listing["price"]
            area = listing["area"]
            address = listing.get("address", "")
            found += 1

            # Filters
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

            ptype = parse_type(address)

            # Check duplicate by URL
            try:
                existing = db.execute(
                    text("SELECT id FROM properties WHERE source_url = :url AND source_url IS NOT NULL"),
                    {"url": url_l}
                ).fetchone()
                if existing:
                    skipped_dup += 1
                    continue
            except Exception as e:
                if verbose:
                    print(f"    DB check error: {e}")
                db.rollback()
                continue

            # Insert record
            try:
                prop = Property(
                    property_type=ptype,
                    province_city=province,
                    district=district,
                    area_m2=area,
                    price=price,
                    price_per_m2=int(ppm),
                    source_name="alonhadat.com.vn",
                    source_url=url_l,
                    source_domain="alonhadat.com.vn",
                    source_crawl_at=datetime.now(),
                    data_origin_type="public_collected",
                    record_status="pending_review",
                    verification_status="pending",
                    data_collection_status="collected",
                    collection_attempt_count=1,
                    last_collection_attempt=datetime.now(),
                    collection_method="playwright_stealth",
                    evidence_tier="E2",
                )
                db.add(prop)
                db.flush()

                chain = ProvenanceChain(
                    property_id=prop.id,
                    step="crawled",
                    actor="system:scrape_alonhadat_v1",
                    source=url_l,
                    input_hash=None,
                    output_hash=None,
                    timestamp=datetime.now(),
                    metadata_json=json.dumps({
                        "scraper": "scrape_alonhadat",
                        "district": district,
                        "province": province,
                        "page": page_num,
                    }),
                )
                db.add(chain)
                saved += 1
                errors_in_row = 0

            except Exception as e:
                if verbose:
                    print(f"    DB insert error: {e}")
                db.rollback()
                errors_in_row += 1
                if errors_in_row >= 3:
                    break
                continue

        page_num += 1
        time.sleep(random.uniform(2, 4))

    if verbose:
        print(f"  -> found={found}, saved={saved}, dup={skipped_dup}, filtered={skipped_filter}")
    return found, saved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--district", default=None)
    parser.add_argument("--target", type=int, default=100)
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
        print("Specify --district <name> or --all")
        print(f"Available: {list(ALONHADAT_DISTRICTS.keys())}")
        db.close()
        return

    total_found = 0
    total_saved = 0

    print(f"\n{'='*60}")
    print(f" SCRAPE ALONHADAT")
    print(f" Target: {args.target}/district, Districts: {len(districts)}")
    print(f"{'='*60}\n")

    for district in districts:
        print(f"[{district}]...", end=" ", flush=True)
        found, saved = scrape_district(district, db, args.target, verbose=args.verbose)
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
