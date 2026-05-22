#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import real property data từ CSV hoặc JSON.

Cho phep nhap tay du lieu BDS thuc te voi nguon goc xuat xu ro rang.
Co the nhap tu:
  - File CSV (template: data/manual_entry_template.csv)
  - File JSON
  - API (POST /api/data-entry/submit)

Usage:
    python scripts/import_real_data.py --template       # Tao CSV template
    python scripts/import_real_data.py --import data/real_transactions.csv
    python scripts/import_real_data.py --import data/real_transactions.json

Template CSV columns:
    province_city, district, property_type, area_m2, bedrooms, bathrooms,
    floor_count, frontage_m, price, price_per_m2, legal_status, furnishing,
    street_or_project, ward, latitude, longitude, listing_date,
    source_name, source_url, source_page_title, collection_method,
    verification_status, evidence_photo_path, field_notes, notes
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import re
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.database import SessionLocal
from src.backend.models import Property
from src.backend.data_sanitizer import PropertySanitizer, ValidationError


DISTRICT_SCOPE = {
    ("Hà Nội", "Quận Cầu Giấy"),
    ("Hà Nội", "Quận Thanh Xuân"),
    ("Hà Nội", "Quận Đống Đa"),
    ("TP. Hồ Chí Minh", "Quận 7"),
    ("TP. Hồ Chí Minh", "Quận Bình Thạnh"),
    ("TP. Hồ Chí Minh", "Quận Tân Bình"),
}


def parse_vnd(text: str) -> float | None:
    if not text:
        return None
    t = text.strip().lower()
    t = re.sub(r"[^\d.,tỷ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    m = re.search(r"([\d.,]+)\s*tỷ", t)
    if m:
        v = float(m.group(1).replace(",", "."))
        return v * 1e9
    m = re.search(r"([\d.,]+)\s*triệu", t)
    if m:
        v = float(m.group(1).replace(",", "."))
        return v * 1e6
    m = re.search(r"^([\d.,]+)\s*triệu", t)
    if m:
        v = float(m.group(1).replace(",", "."))
        return v * 1e6
    try:
        return float(text.replace(",", "").replace(".", ""))
    except (ValueError, AttributeError):
        return None


def parse_date(text: str) -> datetime | None:
    if not text:
        return None
    t = text.strip()
    # YYYY-MM-DD
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # DD/MM/YYYY
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", t)
    if m:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    # relative: "2 weeks ago", "1 month ago"
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
    return None


def assign_tier(
    source_name: str | None,
    source_url: str | None,
    verification_status: str | None,
    collection_method: str | None,
    evidence_photo: str | None,
    field_notes: str | None,
) -> str:
    """Assign evidence tier based on traceability."""
    has_url = bool(source_url and len(str(source_url)) > 10)
    has_source = bool(source_name)
    is_verified = verification_status in ("verified", "pending")
    has_photo = bool(evidence_photo)
    has_notes = bool(field_notes)
    is_self_collected = collection_method in (
        "field_survey", "smartphone_sensor_capture", "manual_entry"
    )
    is_manual_verified_public = collection_method == "manual_verified_from_public_listing"

    # E1: Self-collected with photo + notes + verified
    if is_self_collected and has_photo and has_notes and is_verified:
        return "E1"
    # E2: Self-collected with notes + verified (no photo), OR scraped with URL + verified
    if is_self_collected and has_notes and is_verified:
        return "E2"
    if has_source and has_url and is_verified:
        return "E2"
    # E3: Self-collected with notes (pending), OR manually verified public listing.
    if is_manual_verified_public and has_source and has_url and (has_notes or has_photo):
        return "E3"
    if is_self_collected and has_notes:
        return "E3"
    if has_source and has_url and (has_notes or has_photo):
        return "E3"
    # E4: Scrapped with URL
    if has_source and has_url:
        return "E4"
    # E5: Everything else
    return "E5"


def validate_row(row: dict) -> tuple[bool, str]:
    """Validate a row using PropertySanitizer. Returns (valid, message)."""
    try:
        # Pre-process: parse Vietnamese price/area formats
        row = dict(row)
        price_val = parse_vnd(str(row.get("price", "")))
        if price_val is not None:
            row["price"] = price_val
        area_val = _parse_area(str(row.get("area_m2", "")))
        if area_val is not None:
            row["area_m2"] = area_val

        sanitizer = PropertySanitizer(strict_scope=True)
        sanitizer.sanitize(row)
        return True, "OK"
    except ValidationError as e:
        return False, e.reason


def _parse_area(text: str) -> float | None:
    """Parse area string → float m2."""
    if not text:
        return None
    t = str(text).strip().lower()
    t = re.sub(r"[^\d.,m²]", "", t)
    m = re.search(r"([\d.,]+)", t)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None
    return None


def row_to_property(row: dict, seq: int) -> Property:
    """Convert a validated row dict to a Property ORM object via sanitizer."""
    # Pre-process: parse Vietnamese price/area formats before sanitization
    row = dict(row)  # copy to avoid mutating original
    price_val = parse_vnd(str(row.get("price", "")))
    if price_val is not None:
        row["price"] = price_val
    area_val = _parse_area(row.get("area_m2", ""))
    if area_val is not None:
        row["area_m2"] = area_val

    # Use sanitizer for all field normalization
    sanitizer = PropertySanitizer(strict_scope=True)
    cleaned = sanitizer.sanitize(row)

    # Compute tier from evidence fields (manual logic kept for semantic richness)
    tier = assign_tier(
        cleaned.get("source_name"),
        cleaned.get("source_url"),
        row.get("verification_status", "pending"),
        row.get("collection_method", "manual_entry"),
        row.get("evidence_photo_path"),
        row.get("field_notes"),
    )

    # Source tracking (manual entry specifics)
    source_url = cleaned.get("source_url")
    source_domain = cleaned.get("source_domain")
    if not source_domain and source_url:
        m = re.search(r"https?://([^/]+)", str(source_url))
        if m:
            source_domain = m.group(1)

    listing_date = parse_date(row.get("listing_date", ""))
    evidence_photo = row.get("evidence_photo_path", "").strip() or None
    field_notes = row.get("field_notes", "").strip() or None

    prop = Property(
        property_type=cleaned["property_type"],
        province_city=cleaned["province_city"],
        district=cleaned["district"],
        ward=cleaned["ward"],
        street_or_project=cleaned["street_or_project"],
        area_m2=cleaned["area_m2"],
        bedrooms=cleaned["bedrooms"],
        bathrooms=cleaned["bathrooms"],
        floor_count=cleaned["floor_count"],
        frontage_m=cleaned["frontage_m"],
        price=cleaned["price"],
        price_per_m2=cleaned["price_per_m2"],
        legal_status=cleaned["legal_status"],
        furnishing=cleaned["furnishing"],
        latitude=cleaned["latitude"],
        longitude=cleaned["longitude"],
        area_type=cleaned.get("area_type"),
        listing_date=listing_date,
        source_name=cleaned["source_name"],
        source_url=source_url,
        source_page_title=row.get("source_page_title", "").strip() or None,
        source_domain=source_domain,
        source_access_method="manual_entry",
        collection_method=cleaned.get("collection_method", "manual_entry"),
        verification_status=row.get("verification_status", "pending").strip() or "pending",
        record_status="pending_review",
        data_origin_type="self_collected",
        data_collection_status="collected",
        evidence_tier=tier,
        evidence_tier_updated_at=datetime.now(),
        evidence_photo_path=evidence_photo,
        field_notes=field_notes,
        collection_timestamp=datetime.now(),
        source_crawl_at=datetime.now(),
        source_collected_at=listing_date or datetime.now(),
    )
    return prop


def check_dupe(db: SessionLocal, row: dict, exclude_self_collected: bool = False,
              exclude_same_type: bool = True) -> tuple[bool, str]:
    """
    Check if a row is a duplicate of an existing record.

    Args:
        exclude_self_collected: Exclude self_collected records from dupe check
        exclude_same_type: Exclude records with same data_origin_type as the new row
    """
    row_origin = row.get("data_origin_type", "")
    price = parse_vnd(str(row.get("price", ""))) or float(row.get("price", 0))
    area = float(row.get("area_m2", 0))
    district = row.get("district", "").strip()

    if price and area and district:
        ppm = price / area
        # Within 5% of same district
        q = db.query(Property).filter(
            Property.district == district,
            Property.area_m2.between(area * 0.95, area * 1.05),
            Property.price_per_m2.between(ppm * 0.95, ppm * 1.05),
            Property.record_status != "archived",
        )
        if exclude_same_type and row_origin:
            q = q.filter(Property.data_origin_type == row_origin)
        elif exclude_self_collected:
            q = q.filter(Property.data_origin_type != "self_collected")
        existing = q.first()
        if existing:
            return True, f"DUPLICATE: similar price+area+district exists (id={existing.id})"

    # Check URL dedup (only for records with actual URLs)
    source_url = row.get("source_url", "").strip()
    if source_url:
        q = db.query(Property).filter(
            Property.source_url == source_url,
            Property.record_status != "archived",
        )
        if exclude_same_type and row_origin:
            q = q.filter(Property.data_origin_type == row_origin)
        elif exclude_self_collected:
            q = q.filter(Property.data_origin_type != "self_collected")
        existing = q.first()
        if existing:
            return True, f"DUPLICATE: same source_url exists (id={existing.id})"

    return False, ""


def create_template(output_path: str):
    """Create a CSV template file."""
    headers = [
        "province_city", "district", "property_type", "area_m2",
        "bedrooms", "bathrooms", "floor_count", "frontage_m",
        "price", "price_per_m2", "legal_status", "furnishing",
        "street_or_project", "ward",
        "latitude", "longitude", "listing_date",
        "source_name", "source_url", "source_page_title",
        "collection_method", "verification_status",
        "evidence_photo_path", "field_notes", "notes",
    ]
    example_row = {
        "province_city": "Hà Nội",
        "district": "Quận Cầu Giấy",
        "property_type": "apartment",
        "area_m2": "75.5",
        "bedrooms": "2",
        "bathrooms": "2",
        "floor_count": "10",
        "frontage_m": "5.5",
        "price": "6.5 tỷ",
        "price_per_m2": "86000000",
        "legal_status": "Sổ hồng",
        "furnishing": "full",
        "street_or_project": "Chung cư The Mark",
        "ward": "Phường Yên Hoà",
        "latitude": "21.0325",
        "longitude": "105.7873",
        "listing_date": "2026-04-15",
        "source_name": "alonhadat.com.vn",
        "source_url": "https://alonhadat.com.vn/ban-can-ho-cau-giay-...",
        "source_page_title": "Căn hộ cao cấp Cầu Giấy 75m2",
        "collection_method": "manual_entry",
        "verification_status": "verified",
        "evidence_photo_path": "D:/Photos/property_001.jpg",
        "field_notes": "Đã đi thực địa, chủ nhà xác nhận giá. Sổ hồng photo.",
        "notes": "Giá chợ đen thực tế có thể thấp hơn 5%",
    }
    examples = [
        example_row,
        {
            "province_city": "TP. Hồ Chí Minh", "district": "Quận 7",
            "property_type": "house", "area_m2": "120",
            "bedrooms": "3", "bathrooms": "2", "floor_count": "3",
            "frontage_m": "5", "price": "8.2 tỷ",
            "legal_status": "Sổ đỏ", "furnishing": "none",
            "listing_date": "2026-03-20",
            "source_name": "batdongsan.com.vn",
            "source_url": "https://batdongsan.com.vn/ban-nha-...",
            "collection_method": "manual_entry",
            "verification_status": "pending",
            "field_notes": "Gọi điện chủ nhà xác nhận đang rao bán",
        },
        {
            "province_city": "Hà Nội", "district": "Quận Đống Đa",
            "property_type": "townhouse", "area_m2": "55",
            "bedrooms": "4", "bathrooms": "3", "floor_count": "4",
            "frontage_m": "5", "price": "4.8 tỷ",
            "legal_status": "Sổ hồng", "furnishing": "full",
            "listing_date": "2026-02-10",
            "source_name": "Khảo sát thực địa",
            "source_url": "",
            "collection_method": "field_survey",
            "verification_status": "verified",
            "evidence_photo_path": "D:/Survey/townhouse_đongda.jpg",
            "field_notes": "Đã đo thực tế, chụp ảnh mặt tiền và sổ đỏ",
        },
    ]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for ex in examples:
            writer.writerow(ex)

    print(f"[OK] Template created: {output_path}")
    print(f"     Rows: 1 header + {len(examples)} examples")
    print(f"     Scope: Only 6 districts: Cau Giay, Thanh Xuan, Dong Da, Quan 7, Binh Thanh, Tan Binh")
    print()
    print("  price format: '6.5 tỷ' or '6500000000' or '650 triệu'")
    print("  collection_method: field_survey | manual_entry | smartphone_sensor_capture")
    print("  verification_status: verified | pending | unverified")


def import_csv(filepath: str, db: SessionLocal) -> dict:
    """Import real data from CSV file."""
    stats = {"total": 0, "saved": 0, "dupe": 0, "invalid": 0, "errors": []}
    rows = []

    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            rows.append((i, row))

    stats["total"] = len(rows)

    for seq, (line_num, row) in enumerate(rows, 1):
        try:
            # Validate
            valid, msg = validate_row(row)
            if not valid:
                stats["invalid"] += 1
                stats["errors"].append(f"Line {line_num}: {msg}")
                continue

            # Check duplicate
            is_dupe, dup_msg = check_dupe(db, row)
            if is_dupe:
                stats["dupe"] += 1
                continue

            # Create property
            prop = row_to_property(row, seq)
            db.add(prop)
            db.flush()

            # Log
            print(
                f"  [OK] {prop.district} | {prop.property_type} | "
                f"{prop.area_m2}m2 | {prop.price/1e9:.1f}tỷ | "
                f"tier={prop.evidence_tier}"
            )

            stats["saved"] += 1

            if stats["saved"] % 50 == 0:
                db.commit()

        except Exception as e:
            stats["invalid"] += 1
            stats["errors"].append(f"Line {line_num}: {e}")

    db.commit()
    return stats


def import_json(filepath: str, db: SessionLocal) -> dict:
    """Import real data from JSON file."""
    stats = {"total": 0, "saved": 0, "dupe": 0, "invalid": 0, "errors": []}

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        records = data.get("transactions", data.get("records", [data]))
    else:
        records = data

    stats["total"] = len(records)

    for i, row in enumerate(records, 1):
        try:
            valid, msg = validate_row(row)
            if not valid:
                stats["invalid"] += 1
                stats["errors"].append(f"Record {i}: {msg}")
                continue

            is_dupe, _ = check_dupe(db, row)
            if is_dupe:
                stats["dupe"] += 1
                continue

            prop = row_to_property(row, i)
            db.add(prop)
            db.flush()

            print(
                f"  [OK] {prop.district} | {prop.property_type} | "
                f"{prop.area_m2}m2 | {prop.price/1e9:.1f}tỷ | tier={prop.evidence_tier}"
            )
            stats["saved"] += 1

            if stats["saved"] % 50 == 0:
                db.commit()

        except Exception as e:
            stats["invalid"] += 1
            stats["errors"].append(f"Record {i}: {e}")

    db.commit()
    return stats


def print_report(stats: dict):
    print(f"\n{'='*60}")
    print(f" IMPORT RESULT")
    print(f"{'='*60}")
    print(f"  Total records:     {stats['total']}")
    print(f"  Saved:            {stats['saved']}")
    print(f"  Duplicate:         {stats['dupe']}")
    print(f"  Invalid:          {stats['invalid']}")

    if stats["saved"] > 0:
        print(f"\n  All {stats['saved']} records imported with:")
        print(f"    - data_origin_type = 'self_collected'")
        print(f"    - collection_method = 'manual_entry' or 'field_survey'")
        print(f"    - record_status = 'pending_review'")
        print(f"    - evidence_tier assigned based on traceability")

    if stats["errors"]:
        print(f"\n  Errors ({len(stats['errors'])}):")
        for err in stats["errors"][:10]:
            print(f"    - {err}")
        if len(stats["errors"]) > 10:
            print(f"    ... and {len(stats['errors'])-10} more")

    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Import real property data with traceable provenance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--template", action="store_true",
                        help="Create CSV template for manual entry")
    parser.add_argument("--import", dest="import_file", metavar="FILE",
                        help="Import from CSV or JSON file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate only, do not save")
    args = parser.parse_args()

    if args.template:
        out = PROJECT_ROOT / "data" / "manual_entry_template.csv"
        out.parent.mkdir(exist_ok=True)
        create_template(str(out))
        return

    if not args.import_file:
        parser.print_help()
        print()
        print("Workflow:")
        print("  1. python scripts/import_real_data.py --template")
        print("  2. Edit data/manual_entry_template.csv with real data")
        print("  3. python scripts/import_real_data.py --import data/manual_entry_template.csv")
        return

    filepath = Path(args.import_file)
    if not filepath.exists():
        print(f"[ERROR] File not found: {filepath}")
        return

    db = SessionLocal()
    print(f"\n{'='*60}")
    print(f" IMPORTING: {filepath.name}")
    print(f" Mode: {'DRY RUN' if args.dry_run else 'APPLY'}")
    print(f"{'='*60}\n")

    if filepath.suffix.lower() == ".csv":
        stats = import_csv(str(filepath), db)
    elif filepath.suffix.lower() == ".json":
        stats = import_json(str(filepath), db)
    else:
        print(f"[ERROR] Unsupported file type: {filepath.suffix}")
        print(f"  Supported: .csv, .json")
        db.close()
        return

    db.close()
    print_report(stats)


if __name__ == "__main__":
    main()
