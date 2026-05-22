#!/usr/bin/env python3
"""
Analyze gaps in current dataset to find where to collect more data.
Check: price distribution, missing property types, data quality per district.
"""
import sqlite3
import sys
import os
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
db_path = Path(__file__).parent.parent / "real_estate_avm.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=" * 70)
print("  DATA GAP ANALYSIS")
print("=" * 70)

# 1. Records per district
print("\n[1] Records per district:")
c.execute("""
    SELECT province_city, district, COUNT(*) as cnt,
           AVG(price) as avg_price,
           AVG(area_m2) as avg_area,
           MIN(price) as min_price,
           MAX(price) as max_price
    FROM properties
    WHERE price > 0
    GROUP BY province_city, district
    ORDER BY cnt DESC
""")
for r in c.fetchall():
    print(f"  {r[0]} / {r[1]}: {r[2]:4d} records, "
          f"avg={r[3]/1e9:.2f}t, area={r[4]:.1f}m2, "
          f"range={r[5]/1e9:.1f}t-{r[6]/1e9:.0f}t")

# 2. Records per property type
print("\n[2] Records per property type:")
c.execute("""
    SELECT property_type, COUNT(*) as cnt
    FROM properties WHERE price > 0
    GROUP BY property_type ORDER BY cnt DESC
""")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")

# 3. Price per m2 distribution
print("\n[3] Price/m2 distribution by district:")
c.execute("""
    SELECT province_city, district,
           COUNT(*) as cnt,
           AVG(price_per_m2) as avg_ppm,
           MIN(price_per_m2) as min_ppm,
           MAX(price_per_m2) as max_ppm
    FROM properties
    WHERE price > 0 AND price_per_m2 > 0
    GROUP BY province_city, district
    ORDER BY avg_ppm DESC
""")
print(f"  {'District':<30} {'Count':>6} {'Avg/m2':>8} {'Min':>8} {'Max':>8}")
for r in c.fetchall():
    print(f"  {r[0]} / {r[1]:<18} {r[2]:>6} {r[3]/1e6:>7.1f}M  {r[4]/1e6:>7.1f}M  {r[5]/1e6:>7.1f}M")

# 4. Data quality per district
print("\n[4] Evidence quality per district:")
c.execute("""
    SELECT province_city, district,
           COUNT(*) as total,
           SUM(CASE WHEN evidence_tier = 'E4' THEN 1 ELSE 0 END) as e4,
           SUM(CASE WHEN evidence_tier = 'E3' THEN 1 ELSE 0 END) as e3,
           SUM(CASE WHEN evidence_tier = 'E2' THEN 1 ELSE 0 END) as e2,
           SUM(CASE WHEN evidence_tier = 'E1' THEN 1 ELSE 0 END) as e1,
           SUM(CASE WHEN evidence_photo_path IS NOT NULL THEN 1 ELSE 0 END) as photo,
           SUM(CASE WHEN gps_lat IS NOT NULL OR latitude IS NOT NULL THEN 1 ELSE 0 END) as gps,
           SUM(CASE WHEN field_notes IS NOT NULL AND LENGTH(field_notes) > 20 THEN 1 ELSE 0 END) as notes,
           SUM(CASE WHEN source_url IS NOT NULL AND source_url != '' THEN 1 ELSE 0 END) as url
    FROM properties WHERE price > 0
    GROUP BY province_city, district
    ORDER BY district
""")
print(f"  {'District':<22} {'Tot':>4} {'E4':>3} {'E3':>3} {'E2':>3} {'E1':>3} "
      f"{'Photo':>5} {'GPS':>4} {'Notes':>5} {'URL':>4}")
for r in c.fetchall():
    print(f"  {r[0][:6]} / {r[1]:<14} {r[2]:>4} {r[3]:>3} {r[4]:>3} {r[5]:>3} {r[6]:>3} "
          f"{r[7]:>5} {r[8]:>4} {r[9]:>5} {r[10]:>4}")

# 5. Check source domain distribution
print("\n[5] Source domains:")
c.execute("""
    SELECT source_domain, COUNT(*) as cnt
    FROM properties WHERE price > 0 AND source_domain IS NOT NULL AND source_domain != ''
    GROUP BY source_domain ORDER BY cnt DESC
""")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")

# 6. Missing data analysis
print("\n[6] Missing data analysis:")
c.execute("SELECT COUNT(*) FROM properties WHERE price > 0")
total = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM properties WHERE price > 0 AND source_url IS NOT NULL AND source_url != ''")
with_url = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM properties WHERE price > 0 AND (source_url IS NULL OR source_url = '')")
no_url = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM properties WHERE price > 0 AND listing_date IS NOT NULL")
with_date = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM properties WHERE price > 0 AND legal_status IS NOT NULL AND legal_status != ''")
with_legal = c.fetchone()[0]
print(f"  Total: {total}")
print(f"  With source_url: {with_url} ({100*with_url/total:.1f}%)")
print(f"  Without source_url: {no_url} ({100*no_url/total:.1f}%)")
print(f"  With listing_date: {with_date} ({100*with_date/total:.1f}%)")
print(f"  With legal_status: {with_legal} ({100*with_legal/total:.1f}%)")

# 7. Summary: what makes data "incomplete"
print("\n[7] Data completeness by tier:")
c.execute("""
    SELECT evidence_tier,
           COUNT(*) as total,
           SUM(CASE WHEN source_url IS NOT NULL AND source_url != '' THEN 1 ELSE 0 END) as has_url,
           SUM(CASE WHEN listing_date IS NOT NULL THEN 1 ELSE 0 END) as has_date,
           SUM(CASE WHEN legal_status IS NOT NULL AND legal_status != '' THEN 1 ELSE 0 END) as has_legal,
           SUM(CASE WHEN bedrooms > 0 THEN 1 ELSE 0 END) as has_bedrooms,
           SUM(CASE WHEN bathrooms > 0 THEN 1 ELSE 0 END) as has_bathrooms,
           SUM(CASE WHEN floor_count > 0 THEN 1 ELSE 0 END) as has_floors,
           SUM(CASE WHEN furnishing IS NOT NULL AND furnishing != '' THEN 1 ELSE 0 END) as has_furnishing
    FROM properties WHERE price > 0
    GROUP BY evidence_tier ORDER BY evidence_tier
""")
print(f"  {'Tier':>4} {'Total':>5} {'URL':>5} {'Date':>5} {'Legal':>6} {'Bed':>4} {'Bath':>5} {'Floor':>5} {'Furn':>5}")
for r in c.fetchall():
    n = r[1]
    print(f"  {r[0]:>4} {r[1]:>5} {100*r[2]/n:>4.0f}% {100*r[3]/n:>4.0f}% "
          f"{100*r[4]/n:>5.0f}% {100*r[5]/n:>3.0f}% {100*r[6]/n:>4.0f}% "
          f"{100*r[7]/n:>4.0f}% {100*r[8]/n:>4.0f}%")

conn.close()
print("\n" + "=" * 70)
