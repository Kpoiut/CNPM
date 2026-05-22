#!/usr/bin/env python3
"""
Expand dataset with NEW districts and cities.
Check which areas are NOT yet scraped, then scrape them.
"""
import sqlite3
import sys
import os
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
db_path = Path(__file__).parent.parent / "real_estate_avm.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Check current scope
print("=== Current scope ===")
c.execute("""
    SELECT province_city, district, COUNT(*) as cnt
    FROM properties
    WHERE price > 0 AND province_city IS NOT NULL
    GROUP BY province_city, district
    ORDER BY province_city, district
""")
for r in c.fetchall():
    print(f"  {r[0]} / {r[1]}: {r[2]} records")

print()

# Check unique provinces
c.execute("SELECT DISTINCT province_city FROM properties WHERE province_city IS NOT NULL")
existing_provinces = set(r[0] for r in c.fetchall())
print(f"Existing provinces: {existing_provinces}")

# VN major cities to expand
all_vn_cities = [
    ("Hà Nội", "Quận Ba Đình"),
    ("Hà Nội", "Quận Hoàn Kiếm"),
    ("Hà Nội", "Quận Hai Bà Trưng"),
    ("Hà Nội", "Quận Đống Đa"),
    ("Hà Nội", "Quận Tây Hồ"),
    ("Hà Nội", "Quận Cầu Giấy"),
    ("Hà Nội", "Quận Thanh Xuân"),
    ("Hà Nội", "Quận Hoàng Mai"),
    ("Hà Nội", "Quận Nam Từ Liêm"),
    ("Hà Nội", "Quận Bắc Từ Liêm"),
    ("Hà Nội", "Quận Hà Đông"),
    ("TP. Hồ Chí Minh", "Quận 1"),
    ("TP. Hồ Chí Minh", "Quận 3"),
    ("TP. Hồ Chí Minh", "Quận 5"),
    ("TP. Hồ Chí Minh", "Quận 7"),
    ("TP. Hồ Chí Minh", "Quận Bình Thạnh"),
    ("TP. Hồ Chí Minh", "Quận Tân Bình"),
    ("TP. Hồ Chí Minh", "Quận Phú Nhuận"),
    ("TP. Hồ Chí Minh", "Quận Gò Vấp"),
    ("TP. Hồ Chí Minh", "Quận Bình Tân"),
    ("TP. Hồ Chí Minh", "Quận Tân Phú"),
    ("TP. Đà Nẵng", "Quận Hải Châu"),
    ("TP. Đà Nẵng", "Quận Thanh Khê"),
    ("TP. Đà Nẵng", "Quận Liên Chiểu"),
    ("TP. Đà Nẵng", "Quận Ngũ Hành Sơn"),
    ("TP. Cần Thơ", "Quận Ninh Kiều"),
    ("TP. Cần Thơ", "Quận Bình Thủy"),
    ("TP. Hải Phòng", "Quận Hồng Bàng"),
    ("TP. Hải Phòng", "Quận Ngô Quyền"),
    ("Bình Dương", "Thành phố Thủ Dầu Một"),
    ("Đồng Nai", "Thành phố Biên Hòa"),
]

# Which ones are NOT yet in DB?
existing_combos = set()
c.execute("SELECT province_city, district FROM properties WHERE province_city IS NOT NULL AND district IS NOT NULL")
for r in c.fetchall():
    existing_combos.add((r[0], r[1]))

print("\n=== Districts NOT yet in DB ===")
new_districts = [(p, d) for p, d in all_vn_cities if (p, d) not in existing_combos]
for p, d in new_districts:
    print(f"  {p} / {d}")
print(f"\nTotal new districts: {len(new_districts)}")

conn.close()
