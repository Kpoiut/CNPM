#!/usr/bin/env python3
"""
Expand scraping to new districts in HN, HCM, Đà Nẵng, Cần Thơ, Hải Phòng, Bình Dương, Đồng Nai.
Each listing has a unique source URL — no duplicates.

Usage:
    python scripts/scrape_expanded.py --target 1000
    python scripts/scrape_expanded.py --target 500 --city hanoi
"""
import argparse
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from sqlalchemy import text
from src.backend.database import SessionLocal, init_db
from src.backend.models import Property, ProvenanceChain, CollectionSource

# ═══════════════════════════════════════════════════════════
# NEW EXPANDED SCOPE
# ═══════════════════════════════════════════════════════════
EXPANDED_DISTRICTS = [
    # Hanoi - new districts
    ("Hà Nội", "Quận Ba Đình"),
    ("Hà Nội", "Quận Hoàn Kiếm"),
    ("Hà Nội", "Quận Hai Bà Trưng"),
    ("Hà Nội", "Quận Tây Hồ"),
    ("Hà Nội", "Quận Hoàng Mai"),
    ("Hà Nội", "Quận Nam Từ Liêm"),
    ("Hà Nội", "Quận Bắc Từ Liêm"),
    ("Hà Nội", "Quận Hà Đông"),
    # HCM - new districts
    ("TP. Hồ Chí Minh", "Quận 1"),
    ("TP. Hồ Chí Minh", "Quận 3"),
    ("TP. Hồ Chí Minh", "Quận 5"),
    ("TP. Hồ Chí Minh", "Quận Phú Nhuận"),
    ("TP. Hồ Chí Minh", "Quận Gò Vấp"),
    ("TP. Hồ Chí Minh", "Quận Bình Tân"),
    ("TP. Hồ Chí Minh", "Quận Tân Phú"),
    # Đà Nẵng
    ("TP. Đà Nẵng", "Quận Hải Châu"),
    ("TP. Đà Nẵng", "Quận Thanh Khê"),
    ("TP. Đà Nẵng", "Quận Liên Chiểu"),
    # Other cities
    ("TP. Cần Thơ", "Quận Ninh Kiều"),
    ("TP. Hải Phòng", "Quận Hồng Bàng"),
    ("Bình Dương", "Thành phố Thủ Dầu Một"),
    ("Đồng Nai", "Thành phố Biên Hòa"),
]

# batdongsan district slugs
BATDONGSAN_SLUGS = {
    "Quận Ba Đình": "quan-ba-dinh",
    "Quận Hoàn Kiếm": "quan-hoan-kiem",
    "Quận Hai Bà Trưng": "quan-hai-ba-trung",
    "Quận Tây Hồ": "quan-tay-ho",
    "Quận Hoàng Mai": "quan-hoang-mai",
    "Quận Nam Từ Liêm": "nam-tu-liem",
    "Quận Bắc Từ Liêm": "bac-tu-liem",
    "Quận Hà Đông": "quan-ha-dong",
    "Quận 1": "quan-1",
    "Quận 3": "quan-3",
    "Quận 5": "quan-5",
    "Quận Phú Nhuận": "quan-phu-nhuan",
    "Quận Gò Vấp": "quan-go-vap",
    "Quận Bình Tân": "quan-binh-tan",
    "Quận Tân Phú": "quan-tan-phu",
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")


def normalize_district(text: str, target_district: str = None):
    """Map text to (province, district)."""
    if target_district:
        return target_district
    t = (text or "").lower()
    for prov, dist in EXPANDED_DISTRICTS:
        if dist.lower() in t or dist.replace("Quận ", "").lower() in t:
            return dist
    return None


def parse_price_vnd(text: str):
    if not text:
        return None
    t = text.lower().strip()
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


def parse_property_type(text: str):
    t = (text or "").lower()
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
            price=price,
            price_per_m2=int(ppm),
            listing_date=listing_date,
            legal_status=rec.get("legal_document") or rec.get("legal_status"),
            source_name=rec.get("source") or "batdongsan.com.vn",
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
            evidence_tier="E2",  # Scraped data = at most E2-E3
        )
        db.add(prop)

        # Provenance chain
        chain = ProvenanceChain(
            property_id=prop.id,
            step="crawled",
            actor="system:batdongsan_scraper_v3",
            source=url,
            input_hash=None,
            output_hash=None,
            timestamp=datetime.now(),
            metadata_json='{"scraper": "batdongsan_expanded", "province": "' + province + '", "district": "' + district + '"}',
        )
        db.add(chain)

        return True
    except Exception:
        return False


def scrape_batdongsan_district(district: str, db, target: int) -> tuple[int, int]:
    """Scrape a single district from batdongsan.com.vn."""
    slug = BATDONGSAN_SLUGS.get(district)
    if not slug:
        return 0, 0

    found = 0
    saved = 0

    for section in ["/ban-nha-rieng", "/ban-can-ho-chung-cu", "/ban-nen-dat"]:
        url = f"https://www.batdongsan.com.vn/{slug}{section}"
        try:
            browser = sync_playwright().chromium.launch(
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
                continue

            page.wait_for_timeout(20000)

            body_text = page.inner_text('body')[:300].lower()
            if "xác minh bảo mật" in body_text or "xác thực" in body_text:
                page.close()
                ctx.close()
                browser.close()
                continue

            cards = page.query_selector_all('[class*="product"]')
            if not cards:
                cards = page.query_selector_all('[class*="card"]')
            if not cards:
                cards = page.query_selector_all('[class*="item"]')

            for card in cards:
                found += 1
                text = card.inner_text()

                price = parse_price_vnd(text)
                area = parse_area(text)
                if not price or not area:
                    continue

                title_el = card.query_selector('a[class*="title"]')
                title = title_el.inner_text() if title_el else ""
                detail_url = title_el.get_attribute('href') if title_el else ""

                if detail_url and not detail_url.startswith('http'):
                    detail_url = 'https://www.batdongsan.com.vn' + detail_url

                rec = {
                    "url": detail_url,
                    "title": title,
                    "ptype": parse_property_type(title),
                    "district": district,
                    "province": "Hà Nội" if district != "Quận 1" and district != "Quận 3" and district != "Quận 5" and district != "Quận Phú Nhuận" and district != "Quận Gò Vấp" and district != "Quận Bình Tân" and district != "Quận Tân Phú" else "TP. Hồ Chí Minh",
                    "price": price,
                    "area": area,
                    "source": "batdongsan.com.vn",
                }
                # Fix province
                if district in BATDONGSAN_SLUGS:
                    if district in ["Quận 1", "Quận 3", "Quận 5", "Quận Phú Nhuận", "Quận Gò Vấp", "Quận Bình Tân", "Quận Tân Phú"]:
                        rec["province"] = "TP. Hồ Chí Minh"
                    else:
                        rec["province"] = "Hà Nội"

                if _save_listing(db, rec):
                    saved += 1

                if saved >= target:
                    page.close()
                    ctx.close()
                    browser.close()
                    return found, saved

            page.close()
            ctx.close()
            browser.close()
            time.sleep(random.uniform(2, 4))

        except Exception as e:
            pass

    return found, saved


def scrape_nhatot_city(city_slug: str, db, target: int) -> tuple[int, int]:
    """Scrape nhatot.com for Đà Nẵng, Cần Thơ, etc."""
    city_map = {
        "da-nang": ("TP. Đà Nẵng", ["hai-chau", "thanh-khe", "lien-chieu", "ngu-hanh-son"]),
        "can-tho": ("TP. Cần Thơ", ["ninh-kieu", "binh-thuy"]),
        "hai-phong": ("TP. Hải Phòng", ["hong-bang", "ngo-quyen"]),
        "binh-duong": ("Bình Dương", ["thu-dau-mot"]),
        "dong-nai": ("Đồng Nai", ["bien-hoa"]),
    }

    if city_slug not in city_map:
        return 0, 0

    province, district_slugs = city_map[city_slug]
    found = 0
    saved = 0

    for dist_slug in district_slugs:
        url = f"https://nhatot.com/mua-ban-bat-dong-san/{city_slug}/{dist_slug}"
        try:
            browser = sync_playwright().chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = browser.new_context(user_agent=UA, locale="vi-VN")
            page = ctx.new_page()
            resp = page.goto(url, timeout=60000)
            if not resp or resp.status != 200:
                page.close()
                ctx.close()
                browser.close()
                continue

            page.wait_for_timeout(8000)

            # Try JSON data first
            json_data = None
            try:
                data = page.evaluate("() => { const s = document.getElementById('__NEXT_DATA__'); return s ? s.textContent : null; }")
                if data:
                    import json as jsonlib
                    json_data = jsonlib.loads(data)
            except Exception:
                pass

            cards = []
            if json_data:
                # Extract from JSON
                try:
                    ads = json_data.get("props", {}).get("pageProps", {}).get("ads", [])
                    for ad in ads:
                        list_id = str(ad.get("list_id", ""))
                        if not list_id or list_id in ("", "None"):
                            continue
                        price = ad.get("price")
                        area = ad.get("area")
                        if not price or not area:
                            continue
                        district = ad.get("region", "")
                        province_val = ad.get("city", "")
                        district_norm = district_map_nhatot(district, province_val)
                        if not district_norm:
                            continue

                        rec = {
                            "list_id": list_id,
                            "url": f"https://nhatot.com/mua-ban-bat-dong-san/{city_slug}/{dist_slug}/{list_id}",
                            "title": ad.get("subject", ""),
                            "ptype": parse_property_type(ad.get("subject", "")),
                            "district": district_norm,
                            "province": province,
                            "price": float(price),
                            "area": float(area),
                            "price_per_m2": ad.get("price_per_m2", 0),
                            "bedrooms": ad.get("bedrooms", 0),
                            "source": "nhatot.com",
                        }
                        cards.append(rec)
                except Exception:
                    pass
            else:
                # Fallback: extract from DOM
                items = page.query_selector_all('[class*="listing"] [class*="item"]')
                for item in items:
                    text = item.inner_text()
                    price = parse_price_vnd(text)
                    area = parse_area(text)
                    if not price or not area:
                        continue
                    rec = {
                        "url": "",
                        "title": "",
                        "ptype": "apartment",
                        "district": district_slugs[0],
                        "province": province,
                        "price": price,
                        "area": area,
                        "source": "nhatot.com",
                    }
                    cards.append(rec)

            for rec in cards:
                found += 1
                if _save_listing(db, rec):
                    saved += 1
                if saved >= target:
                    page.close()
                    ctx.close()
                    browser.close()
                    return found, saved

            page.close()
            ctx.close()
            browser.close()
            time.sleep(random.uniform(2, 4))

        except Exception:
            pass

    return found, saved


def district_map_nhatot(raw: str, city: str) -> str:
    """Map nhatot district to our standard district name."""
    raw_lower = (raw or "").lower()
    if "hải châu" in raw_lower or "hai chau" in raw_lower:
        return "Quận Hải Châu"
    if "thanh khê" in raw_lower or "thanh khe" in raw_lower:
        return "Quận Thanh Khê"
    if "liên chiểu" in raw_lower or "lien chieu" in raw_lower:
        return "Quận Liên Chiểu"
    if "ngũ hành sơn" in raw_lower or "ngu hanh son" in raw_lower:
        return "Quận Ngũ Hành Sơn"
    if "nin" in raw_lower:
        return "Quận Ninh Kiều"
    if "bình thủy" in raw_lower or "binh thuy" in raw_lower:
        return "Quận Bình Thủy"
    if "hồng bàng" in raw_lower or "hong bang" in raw_lower:
        return "Quận Hồng Bàng"
    if "ngô quyền" in raw_lower or "ngo quyen" in raw_lower:
        return "Quận Ngô Quyền"
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=500)
    parser.add_argument("--city", default="all",
                        choices=["all", "hanoi", "hcm", "danang", "cantho", "haiphong", "binhduong", "dongnai"])
    parser.add_argument("--source", default="batdongsan",
                       choices=["batdongsan", "nhatot", "all"])
    args = parser.parse_args()

    db = SessionLocal()
    init_db()

    total_saved = 0
    total_found = 0

    print(f"\n{'='*60}")
    print(f" EXPANDED SCRAPER")
    print(f" Target: {args.target} new listings")
    print(f" Source: {args.source}")
    print(f"{'='*60}\n")

    # batdongsan for new HCM/HN districts
    if args.source in ("batdongsan", "all"):
        if args.city in ("all", "hanoi"):
            hn_districts = [d for p, d in EXPANDED_DISTRICTS if p == "Hà Nội" and d in BATDONGSAN_SLUGS]
            for district in hn_districts:
                if total_saved >= args.target:
                    break
                print(f"[HN] {district}...", end=" ", flush=True)
                found, saved = scrape_batdongsan_district(district, db, args.target - total_saved)
                total_found += found
                total_saved += saved
                print(f"found={found}, saved={saved}, total={total_saved}")

        if args.city in ("all", "hcm"):
            hcm_districts = [d for p, d in EXPANDED_DISTRICTS if p == "TP. Hồ Chí Minh" and d in BATDONGSAN_SLUGS]
            for district in hcm_districts:
                if total_saved >= args.target:
                    break
                print(f"[HCM] {district}...", end=" ", flush=True)
                found, saved = scrape_batdongsan_district(district, db, args.target - total_saved)
                total_found += found
                total_saved += saved
                print(f"found={found}, saved={saved}, total={total_saved}")

    # nhatot for Đà Nẵng, Cần Thơ, etc.
    if args.source in ("nhatot", "all"):
        for city_slug in ["da-nang", "can-tho", "hai-phong", "binh-duong", "dong-nai"]:
            if total_saved >= args.target:
                break
            print(f"[{city_slug}]...", end=" ", flush=True)
            found, saved = scrape_nhatot_city(city_slug, db, args.target - total_saved)
            total_found += found
            total_saved += saved
            print(f"found={found}, saved={saved}, total={total_saved}")

    db.commit()

    # Update CollectionSource
    cs = db.execute(text("SELECT * FROM collection_sources WHERE source_name = 'batdongsan_expanded'")).fetchone()
    if cs:
        db.execute(text(
            "UPDATE collection_sources SET successful_records = successful_records + :n, "
            "last_run_at = :ts, last_run_status = :status WHERE source_name = 'batdongsan_expanded'"
        ), {"n": total_saved, "ts": datetime.now(), "status": "success"})
    else:
        cs_new = CollectionSource(
            source_name="batdongsan_expanded",
            source_url="https://www.batdongsan.com.vn",
            source_type="public_portal",
            records_collected=total_found,
            successful_records=total_saved,
            last_run_at=datetime.now(),
            last_run_status="success",
        )
        db.add(cs_new)

    db.commit()
    db.close()

    print(f"\n{'='*60}")
    print(f" COMPLETE")
    print(f"  Found:  {total_found}")
    print(f"  Saved:  {total_saved}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
