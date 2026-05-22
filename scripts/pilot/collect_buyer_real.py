#!/usr/bin/env python3
"""
Real Buyer Requirement Collector v2 — Thu thập yêu cầu từ NGUỒN THỰC.
Không dùng dữ liệu seeded. Chỉ thu thật từ web thực hoặc form thực.
"""
import sys
sys.path.insert(0, ".")
import hashlib, re, time, random, argparse
from datetime import datetime
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from playwright.sync_api import sync_playwright

from src.backend.database import SessionLocal, init_db
from src.backend.models import BuyerRequirement

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
ALL = HN_DISTRICTS + HCM_DISTRICTS

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}


def parse_price(text):
    """Parse price range text → (min_vnd, max_vnd)"""
    if not text:
        return None, None
    t = text.strip().lower()
    t = re.sub(r"[^\d.,tỷtriệu]", " ", t)

    # Range "3-5 tỷ"
    m = re.search(r"([\d.,]+)\s*[-–]\s*([\d.,]+)\s*tỷ", t)
    if m:
        try:
            lo = float(m.group(1).replace(",", ".")) * 1e9
            hi = float(m.group(2).replace(",", ".")) * 1e9
            return lo, hi
        except ValueError:
            pass

    # Single "4.5 tỷ"
    m = re.search(r"([\d.,]+)\s*tỷ", t)
    if m:
        try:
            v = float(m.group(1).replace(",", ".")) * 1e9
            return v * 0.85, v * 1.15
        except ValueError:
            pass

    # "dưới X tỷ"
    m = re.search(r"dưới\s*([\d.,]+)\s*tỷ", t)
    if m:
        try:
            hi = float(m.group(1).replace(",", ".")) * 1e9
            return hi * 0.5, hi
        except ValueError:
            pass

    # "từ/trên X tỷ"
    m = re.search(r"(?:từ|trên)\s*([\d.,]+)\s*tỷ", t)
    if m:
        try:
            lo = float(m.group(1).replace(",", ".")) * 1e9
            return lo, lo * 2
        except ValueError:
            pass

    return None, None


def parse_area(text):
    if not text:
        return None, None
    t = text.strip().lower()
    m = re.search(r"([\d.,]+)\s*m", t)
    if m:
        try:
            v = float(m.group(1).replace(",", "."))
            return v * 0.85, v * 1.2
        except ValueError:
            pass
    return None, None


def parse_bedrooms(text):
    m = re.search(r"(\d+)\s*(?:pn|phòng)", text.lower())
    return int(m.group(1)) if m else None


def parse_district(text, url="", province_hint="Hà Nội"):
    """Map text → (province, district). Returns (None, None) if not found."""
    t = (text + " " + url).lower()
    m = {
        "cầu giấy": ("Hà Nội", "Quận Cầu Giấy"),
        "thanh xuân": ("Hà Nội", "Quận Thanh Xuân"),
        "đống đa": ("Hà Nội", "Quận Đống Đa"),
        "quận 7": ("TP. Hồ Chí Minh", "Quận 7"),
        "bình thạnh": ("TP. Hồ Chí Minh", "Quận Bình Thạnh"),
        "tân bình": ("TP. Hồ Chí Minh", "Quận Tân Bình"),
    }
    for kw, (prov, dist) in m.items():
        if kw in t:
            return prov, dist
    return None, None


def bds_buyer_urls(district_slug, province_hint):
    """Build batdongsan.com.vn buyer search URLs.

    Probe confirmed: /mua-nha-rieng/ha-noi/thanh-xuan → 200 + buyer links.
    Buyer links have pattern: /mua-nha-rieng/... (intent keyword: mua)
    """
    prov_path = "ha-noi" if province_hint == "Hà Nội" else "tp-ho-chi-minh"
    base = f"https://batdongsan.com.vn/mua-nha-rieng/{prov_path}/{district_slug}"
    urls = [base]
    # Pages 2-10
    for p in range(2, 11):
        urls.append(f"{base}/p{p}")
    return urls


def nhatot_buyer_urls(district_slug, province_hint):
    """Build buyer search URLs.

    nhatot.com redirected to chotot.com — buyer section lives at chotot.com.
    Also probe direct nhatot.com with mua-ban-nha-dat-tai-{slug} pattern (confirmed 200).
    """
    slugs = {
        "cau-giay": "quan-cau-giay",
        "thanh-xuan": "thanh-xuan",
        "dong-da": "dong-da",
        "quan-7": "quan-7",
        "binh-thanh": "quan-binh-thanh",
        "tan-binh": "quan-tan-binh",
    }
    slug = slugs.get(district_slug, district_slug)

    # nhatot.com direct (confirmed 200 with buyer links)
    nhatot_base = f"https://www.nhatot.com/mua-ban-nha-dat-tai-{slug}"
    nhatot_urls = [nhatot_base]
    for p in range(2, 8):
        nhatot_urls.append(f"{nhatot_base}?page={p}")

    # chotot.com fallback (nhatot domain now redirects here)
    chotot_slug = slug.replace("quan-", "")
    chotot_base = f"https://www.chotot.com/tp-ho-chi-minh/mua-ban-nha-dat/{chotot_slug}"
    chotot_urls = [chotot_base]
    for p in range(2, 6):
        chotot_urls.append(f"{chotot_base}?page={p}")

    return nhatot_urls + chotot_urls


def alonhadat_buyer_urls(district_slug, province_hint, ptype="nha-dat"):
    """Build alonhadat buyer listing URLs.

    /can-mua/ha-noi → 404 (path not valid).
    Try /dang-tin/ posting form + /tin-dang/ listing path.
    """
    prov = "ha-noi" if province_hint == "Hà Nội" else "ho-chi-minh"

    # Try direct can-mua paths (might work for some categories)
    base_canmua = f"https://alonhadat.com.vn/can-mua-{ptype}/{prov}/{district_slug}"
    urls = [base_canmua]
    for p in range(2, 8):
        urls.append(f"{base_canmua}/trang-{p}.htm")

    # Posting form fallback
    urls.append("https://alonhadat.com.vn/dang-tin-nha-dat.html")

    return urls


def scrape_bds_buyer_realtime(url, province, district, db, stats):
    """Scrape batdongsan.com.vn buyer posts (mua-nha-rieng section).

    Probe confirmed: /mua-nha-rieng/ha-noi/thanh-xuan → 200 + buyer links found.
    Buyer intent links: href contains 'mua-nha-rieng' or 'mua-'.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # Find buyer-post links: href contains 'mua-nha-rieng' or 'mua-nha-dat'
    for a in soup.select("a"):
        href = a.get("href", "") or ""
        if not href:
            continue

        # Only buyer-intent links
        href_lower = href.lower()
        if not ("mua-nha-rieng" in href_lower or "mua-nha-dat" in href_lower):
            continue

        if not href.startswith("http"):
            if href.startswith("/"):
                href = "https://batdongsan.com.vn" + href
            else:
                continue

        title = a.get_text(strip=True)
        if len(title) < 15:
            continue

        min_b, max_b = parse_price(title)
        if not min_b or min_b < 100_000_000:
            continue

        prov, dist = parse_district(title, href, province)
        if not dist:
            dist = district
            prov = province

        bedrooms = parse_bedrooms(title)

        existing = db.query(BuyerRequirement).filter(
            BuyerRequirement.source_url == href
        ).first()
        if existing:
            continue

        req = BuyerRequirement(
            property_type="apartment",
            province_city=prov or province,
            district=dist or district,
            min_budget=min_b,
            max_budget=max_b,
            bedrooms=bedrooms,
            legal_requirement="any",
            urgency="normal",
            source_type="tin_can_mua",
            source_url=href,
            source_description=title[:200],
            is_active=True,
        )
        db.add(req)
        results.append(req)
        stats["saved"] += 1
    return results


def scrape_nhatot_realtime(url, province, district, db, stats):
    """Scrape nhatot.com / chotot.com buyer posts.

    Filter: links containing 'mua-nha' or 'mua-ban' (buyer intent).
    """
    is_chotot = "chotot.com" in url
    host = "https://www.chotot.com" if is_chotot else "https://www.nhatot.com"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for a in soup.select("a"):
        href = a.get("href", "") or ""
        if not href:
            continue

        # Buyer-intent filter
        href_lower = href.lower()
        if not ("mua-nha" in href_lower or "mua-ban" in href_lower):
            continue

        if not href.startswith("http"):
            if href.startswith("/"):
                href = host + href
            else:
                continue

        title = a.get_text(strip=True)
        if len(title) < 15:
            continue

        min_b, max_b = parse_price(title)
        if not min_b or min_b < 100_000_000:
            continue

        prov, dist = parse_district(title, href, province or "Hà Nội")
        if not dist:
            dist = district
            prov = province

        bedrooms = parse_bedrooms(title)

        existing = db.query(BuyerRequirement).filter(
            BuyerRequirement.source_url == href
        ).first()
        if existing:
            continue

        req = BuyerRequirement(
            property_type="apartment",
            province_city=prov or province,
            district=dist or district,
            min_budget=min_b,
            max_budget=max_b,
            bedrooms=bedrooms,
            legal_requirement="any",
            urgency="normal",
            source_type="tin_can_mua",
            source_url=href,
            source_description=title[:200],
            is_active=True,
        )
        db.add(req)
        results.append(req)
        stats["saved"] += 1
    return results


def scrape_alonhadat_realtime(url, province, district, db, stats):
    """Scrape alonhadat.com.vn buyer posts with requests."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        if resp.status_code != 200:
            return []
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for item in soup.select("article, .property-item, .content-item, div[class*=item]"):
        link = item.select_one("a[href]")
        if not link:
            continue
        href = link.get("href", "")
        if href and not href.startswith("http"):
            href = "https://alonhadat.com.vn" + href

        title = link.get_text(strip=True)
        if len(title) < 15:
            continue

        full = item.get_text(" ", strip=True)
        min_b, max_b = parse_price(full)
        if not min_b or min_b < 100_000_000:
            continue

        prov, dist = parse_district(full, href, province)
        if not dist:
            dist = district
            prov = province

        bedrooms = parse_bedrooms(full)

        existing = db.query(BuyerRequirement).filter(
            BuyerRequirement.source_url == href
        ).first()
        if existing:
            continue

        req = BuyerRequirement(
            property_type="apartment",
            province_city=prov or province,
            district=dist or district,
            min_budget=min_b,
            max_budget=max_b,
            bedrooms=bedrooms,
            legal_requirement="any",
            urgency="normal",
            source_type="tin_can_mua",
            source_url=href,
            source_description=title[:200],
            is_active=True,
        )
        db.add(req)
        results.append(req)
        stats["saved"] += 1

    return results


def run(target=200):
    init_db()
    db = SessionLocal()
    stats = {"saved": 0, "skipped": 0, "errors": 0}
    print(f"\n{'='*60}")
    print(f" REAL BUYER REQUIREMENT COLLECTOR v3")
    print(f" Target: {target} | ONLY real scraped/form submissions accepted")
    print(f"{'='*60}")

    current = db.query(BuyerRequirement).filter(
        BuyerRequirement.source_type == "tin_can_mua"
    ).filter(BuyerRequirement.notes.notlike("%GENERATED%")).count()
    print(f"Current REAL buyer requirements: {current}")

    SLUG_MAP = {
        "Quận Cầu Giấy": "cau-giay",
        "Quận Thanh Xuân": "thanh-xuan",
        "Quận Đống Đa": "dong-da",
        "Quận 7": "quan-7",
        "Quận Bình Thạnh": "binh-thanh",
        "Quận Tân Bình": "tan-binh",
    }

    # ── Phase 1: Requests-based scraping ──────────────────────────────
    print("\n[Phase 1] Requests-based scraping")

    # 1a. batdongsan.com.vn buyer section (confirmed working: 200 + buyer links)
    print("  [batdongsan] buyer section (confirmed 200)")
    for prov, dist in ALL:
        if stats["saved"] >= target:
            break
        slug = SLUG_MAP.get(dist, "")
        for url in bds_buyer_urls(slug, prov)[:8]:
            if stats["saved"] >= target:
                break
            try:
                results = scrape_bds_buyer_realtime(url, prov, dist, db, stats)
                if results:
                    db.commit()
                    print(f"    batdongsan | {dist}: +{len(results)} saved ({stats['saved']}/{target})")
                time.sleep(random.uniform(1.5, 3.0))
            except Exception as e:
                stats["errors"] += 1

    # 1b. nhatot.com / chotot.com buyer section
    print("  [nhatot/chotot] buyer section")
    for prov, dist in ALL:
        if stats["saved"] >= target:
            break
        slug = SLUG_MAP.get(dist, "")
        for url in nhatot_buyer_urls(slug, prov)[:8]:
            if stats["saved"] >= target:
                break
            try:
                results = scrape_nhatot_realtime(url, prov, dist, db, stats)
                if results:
                    db.commit()
                    print(f"    nhatot/chotot | {dist}: +{len(results)} saved ({stats['saved']}/{target})")
                time.sleep(random.uniform(1.0, 2.0))
            except Exception as e:
                stats["errors"] += 1

    # 1c. alonhadat buyer posts (path may be limited)
    print("  [alonhadat] buyer posts")
    for prov, dist in ALL:
        if stats["saved"] >= target:
            break
        slug = SLUG_MAP.get(dist, "")
        for url in alonhadat_buyer_urls(slug, prov)[:4]:
            if stats["saved"] >= target:
                break
            try:
                results = scrape_alonhadat_realtime(url, prov, dist, db, stats)
                if results:
                    db.commit()
                    print(f"    alonhadat | {dist}: +{len(results)} saved ({stats['saved']}/{target})")
                time.sleep(random.uniform(1.0, 2.0))
            except Exception as e:
                stats["errors"] += 1

    # ── Phase 2: Playwright stealth for Cloudflare-protected sites ───
    if stats["saved"] < target:
        remaining = target - stats["saved"]
        print(f"\n[Phase 2] Playwright stealth browser ({remaining} more needed)")
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            ctx = browser.new_context(
                user_agent=UA,
                locale="vi-VN",
                extra_http_headers={"Accept-Language": "vi-VN,vi;q=0.9"},
            )
            page = ctx.new_page()

            for prov, dist in ALL:
                if stats["saved"] >= target:
                    break
                slug = SLUG_MAP.get(dist, dist.lower().replace("quận ", "").replace(" ", "-"))

                # batdongsan buyer section via browser
                for page_num in range(1, 6):
                    if stats["saved"] >= target:
                        break
                    bds_url = f"https://batdongsan.com.vn/mua-nha-rieng/ha-noi/{slug}"
                    url = bds_url if page_num == 1 else f"{bds_url}/p{page_num}"
                    try:
                        resp = page.goto(url, timeout=25000, wait_until="domcontentloaded")
                        time.sleep(random.uniform(2, 4))
                        if resp and resp.status == 200:
                            results = scrape_bds_buyer_realtime(url, prov, dist, db, stats)
                            if results:
                                db.commit()
                                print(f"    PW-bds | {dist} p{page_num}: +{len(results)} saved")
                            elif page_num > 2:
                                break
                        else:
                            break
                    except Exception:
                        stats["errors"] += 1
                        continue

    db.commit()
    db.close()

    # Summary
    print(f"\n{'='*60}")
    print(f"RESULT: {stats['saved']} real buyer requirements collected")
    print(f"  Errors: {stats['errors']}, Skipped: {stats['skipped']}")
    print(f"{'='*60}")
    print(f"Survey form: http://localhost:5173/buyer-survey")
    print(f"API endpoint: POST /api/research/buyer-requirement")
    return stats["saved"]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=200)
    args = ap.parse_args()
    run(target=args.target)
