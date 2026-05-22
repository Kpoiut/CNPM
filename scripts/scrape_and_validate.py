#!/usr/bin/env python3
"""
Diagnostic + Scraper for real estate data collection.

Key insight: existing 856 records are mostly E2 (URL only, no photo/GPS).
To improve to E3+, need: photo + GPS + meaningful notes OR cross-source verification.

This script:
1. Tries to scrape batdongsan with verbose output to see what's happening
2. Uses a fresh browser session per page to avoid bot detection
3. Extracts ALL listing URLs from the page, not just first batch

Usage:
    python scripts/scrape_and_validate.py --district "Quận Cầu Giấy"
    python scripts/scrape_and_validate.py --test-parse
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

DISTRICT_SLUGS = {
    "Quận Cầu Giấy": "quan-cau-giay",
    "Quận Thanh Xuân": "quan-thanh-xuan",
    "Quận Đống Đa": "quan-dong-da",
    "Quận 7": "quan-7",
    "Quận Bình Thạnh": "quan-binh-thanh",
    "Quận Tân Bình": "quan-tan-binh",
}


def parse_price(text: str):
    if not text:
        return None
    t = text.lower().strip()
    t = re.sub(r"[^\d.,tỷtriệu]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    # Pattern: "X tỷ Y triệu"
    m = re.search(r"([\d.,]+)\s*tỷ\s*(\d[\d.,]*)\s*triệu", t)
    if m:
        try:
            return float(m.group(1).replace(",", ".")) * 1e9 + float(m.group(2).replace(",", ".")) * 1e6
        except ValueError:
            pass
    # Pattern: "X tỷ"
    m = re.search(r"([\d.,]+)\s*tỷ", t)
    if m:
        try:
            return float(m.group(1).replace(",", ".")) * 1e9
        except ValueError:
            pass
    # Pattern: "X triệu" (standalone)
    m = re.search(r"^([\d.,]+)\s*triệu", t)
    if m:
        try:
            return float(m.group(1).replace(",", ".")) * 1e6
        except ValueError:
            pass
    return None


def parse_area(text: str):
    if not text:
        return None
    m = re.search(r"([\d.,]+)\s*m", text)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            pass
    return None


def parse_type(text: str):
    t = (text or "").lower()
    if any(k in t for k in ["đất", "dat", "nền"]):
        return "land"
    if any(k in t for k in ["nhà phố", "phố"]):
        return "townhouse"
    if any(k in t for k in ["villa", "biệt thự"]):
        return "villa"
    if any(k in t for k in ["căn hộ", "chung cư"]):
        return "apartment"
    if any(k in t for k in ["nhà", "nha"]):
        return "house"
    return "apartment"


def test_parse():
    """Test parsing on sample batdongsan page content."""
    test_texts = [
        "5,28 tỷ · 27,5 m² · 192 tr/m² · 4 · 3",
        "3.5 tỷ 200 triệu · 68 m² · Nam · 2 · 2",
        "2.1 tỷ · 55m2 · 4PN 2PN",
        "Giá: 8.5 tỷ | 120 m²",
    ]
    for t in test_texts:
        price = parse_price(t)
        area = parse_area(t)
        ptype = parse_type(t)
        print(f"  Input: {t}")
        print(f"  -> price={price}, area={area}, type={ptype}")
        if price:
            print(f"  -> price/m2={price/area:.0f}" if area else "  -> price/m2=N/A")
        print()


def scrape_district(district: str, db, target: int, verbose: bool = False):
    """Scrape batdongsan for a specific district."""
    slug = DISTRICT_SLUGS.get(district)
    if not slug:
        print(f"  Unknown district: {district}")
        return 0, 0

    province = "Hà Nội" if district in ["Quận Cầu Giấy", "Quận Thanh Xuân", "Quận Đống Đa"] else "TP. Hồ Chí Minh"
    found = 0
    saved = 0
    skipped_dup = 0
    skipped_filter = 0

    for section in ["/ban-nha-rieng", "/ban-can-ho-chung-cu", "/ban-nen-dat"]:
        if saved >= target:
            break

        url = f"https://www.batdongsan.com.vn/{slug}{section}"
        if verbose:
            print(f"  URL: {url}")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-web-security",
                    ],
                )
                try:
                    ctx = browser.new_context(
                        user_agent=UA,
                        locale="vi-VN",
                        extra_http_headers={"Accept-Language": "vi-VN,vi;q=0.9"},
                    )
                    page = ctx.new_page()
                    page.set_default_timeout(60000)

                    resp = page.goto(url, timeout=60000)
                    if verbose:
                        print(f"  Status: {resp.status if resp else 'None'}")

                    if not resp or resp.status not in (200, 201):
                        page.close()
                        ctx.close()
                        browser.close()
                        if verbose:
                            print(f"  -> Failed (status)")
                        continue

                    # Wait for SPA to render
                    page.wait_for_timeout(15000)

                    # Check for bot detection
                    body_short = page.inner_text('body')[:500].lower()
                    if "xác minh bảo mật" in body_short or "xác thực" in body_short or "robot" in body_short:
                        if verbose:
                            print(f"  -> Bot detected!")
                        page.close()
                        ctx.close()
                        browser.close()
                        continue

                    # Extract all card URLs first
                    all_links = page.query_selector_all('a[href*="/ban-"]')
                    if verbose:
                        print(f"  Found {len(all_links)} links")

                    # Get all unique URLs
                    seen_urls = set()
                    cards_data = []
                    for link in all_links:
                        href = link.get_attribute('href') or ""
                        if "/ban-" not in href or "javascript" in href:
                            continue
                        full_url = href if href.startswith('http') else f'https://www.batdongsan.com.vn{href}'
                        if full_url in seen_urls:
                            continue
                        seen_urls.add(full_url)

                        try:
                            card_text = link.inner_text()[:300]
                        except Exception:
                            card_text = ""

                        cards_data.append({
                            "url": full_url,
                            "text": card_text,
                        })

                    if verbose:
                        print(f"  Processed {len(cards_data)} unique cards")

                    # Process each card
                    for card in cards_data:
                        if saved >= target:
                            break

                        text = card["text"]
                        url = card["url"]
                        found += 1

                        price = parse_price(text)
                        area = parse_area(text)

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

                        ptype = parse_type(text)

                        # Check duplicate
                        existing = db.execute(text(
                            "SELECT id FROM properties WHERE source_url = :url AND source_url IS NOT NULL"
                        ), {"url": url}).fetchone()
                        if existing:
                            skipped_dup += 1
                            continue

                        prop = Property(
                            property_type=ptype,
                            province_city=province,
                            district=district,
                            area_m2=area,
                            price=price,
                            price_per_m2=int(ppm),
                            source_name="batdongsan.com.vn",
                            source_url=url,
                            source_domain="batdongsan.com.vn",
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
                            actor="system:scrape_validate_v1",
                            source=url,
                            input_hash=None,
                            output_hash=None,
                            timestamp=datetime.now(),
                            metadata_json=json.dumps({
                                "scraper": "scrape_validate",
                                "district": district,
                                "province": province,
                                "section": section,
                            }),
                        )
                        db.add(chain)
                        saved += 1

                    page.close()
                    ctx.close()
                    browser.close()
                    time.sleep(random.uniform(2, 4))

                except Exception as e:
                    browser.close()
                    if verbose:
                        print(f"  Error: {e}")

        except Exception as e:
            if verbose:
                print(f"  Error: {e}")

    if verbose:
        print(f"  -> found={found}, saved={saved}, dup={skipped_dup}, filtered={skipped_filter}")
    return found, saved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--district", default=None)
    parser.add_argument("--target", type=int, default=200)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--test-parse", action="store_true")
    args = parser.parse_args()

    if args.test_parse:
        test_parse()
        return

    db = SessionLocal()
    init_db()

    if args.district:
        districts = [args.district]
    else:
        districts = list(DISTRICT_SLUGS.keys())

    total_found = 0
    total_saved = 0

    print(f"\n{'='*60}")
    print(f" SCRAPE + VALIDATE")
    print(f" Target: {args.target} per district, Districts: {len(districts)}")
    print(f"{'='*60}\n")

    for district in districts:
        print(f"[{district}]...", end=" ", flush=True)
        found, saved = scrape_district(district, db, args.target, verbose=args.verbose)
        total_found += found
        total_saved += saved
        print(f"found={found}, saved={saved}, total={total_saved}")
        db.commit()

    db.close()

    print(f"\n{'='*60}")
    print(f" COMPLETE: found={total_found}, saved={total_saved}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
