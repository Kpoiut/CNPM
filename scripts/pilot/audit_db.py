#!/usr/bin/env python3
"""Audit database for data authenticity, fake detection, and quality."""
import sys
sys.path.insert(0, ".")
from src.backend.database import SessionLocal
from src.backend.models import Property, BuyerRequirement
from sqlalchemy import func

db = SessionLocal()

print("=== DATABASE AUTHENTICITY AUDIT ===")
print()

# --- SUPPLY LISTINGS ---
total = db.query(Property).count()
real_source = db.query(Property).filter(Property.data_origin_type == "public_collected").count()
fake_source = db.query(Property).filter(
    Property.data_origin_type.in_(["system_demo", "demo", "seeded"])
).count()
with_url = db.query(Property).filter(
    Property.source_url.isnot(None), Property.source_url != ""
).count()
without_url = db.query(Property).filter(
    (Property.source_url == None) | (Property.source_url == "")
).count()

alonhadat = db.query(Property).filter(Property.source_domain == "alonhadat.com.vn").count()
nhatot = db.query(Property).filter(Property.source_domain == "nhatot.com").count()
bds = db.query(Property).filter(Property.source_domain == "batdongsan.com.vn").count()
other_src = total - alonhadat - nhatot - bds

print("SUPPLY LISTINGS:")
print(f"  Total: {total}")
print(f"  public_collected: {real_source}")
print(f"  system_demo/seeded: {fake_source}")
print(f"  With source_url: {with_url}")
print(f"  Without source_url: {without_url}")
print(f"  alonhadat.com.vn: {alonhadat}")
print(f"  nhatot.com: {nhatot}")
print(f"  batdongsan.com.vn: {bds}")
print(f"  Other/unknown: {other_src}")
print()

# --- BUYER REQUIREMENTS ---
buyer_total = db.query(BuyerRequirement).count()
real_src_br = db.query(BuyerRequirement).filter(
    BuyerRequirement.source_type == "tin_can_mua"
).count()
survey_br = db.query(BuyerRequirement).filter(
    BuyerRequirement.source_type == "survey"
).count()
other_br = buyer_total - real_src_br - survey_br

survey_with_notes = db.query(BuyerRequirement).filter(
    BuyerRequirement.source_type == "survey"
).filter(BuyerRequirement.notes.isnot(None)).filter(
    BuyerRequirement.notes != ""
).count()
survey_no_notes = db.query(BuyerRequirement).filter(
    BuyerRequirement.source_type == "survey"
).filter(
    (BuyerRequirement.notes == None) | (BuyerRequirement.notes == "")
).count()

print("BUYER REQUIREMENTS:")
print(f"  Total: {buyer_total}")
print(f"  tin_can_mua (web scraped): {real_src_br}")
print(f"  survey (form/seeded): {survey_br}")
print(f"  Other: {other_br}")
print(f"  Survey with notes: {survey_with_notes}")
print(f"  Survey without notes: {survey_no_notes}")
print()

# --- PRICE DIVERSITY ---
ppm_q = db.query(Property.price_per_m2).filter(Property.price_per_m2.isnot(None)).all()
unique_ppm = len(set(p[0] for p in ppm_q if p[0]))
dup_prices = db.query(
    Property.price, func.count(Property.id).label("cnt")
).filter(Property.price.isnot(None)).group_by(
    Property.price
).having(func.count(Property.id) > 5).all()

dup_combos = db.query(
    Property.price, Property.area_m2, func.count(Property.id).label("cnt")
).filter(Property.price.isnot(None), Property.area_m2.isnot(None)).group_by(
    Property.price, Property.area_m2
).having(func.count(Property.id) > 3).all()

print("PRICE DIVERSITY:")
print(f"  Unique price/m2 values: {unique_ppm}/{total} ({unique_ppm/total*100:.1f}%)")
print(f"  Prices appearing >5x: {len(dup_prices)}")
print(f"  Price+Area combos >3x: {len(dup_combos)}")
if dup_combos:
    print("  Top suspicious combos:")
    for p, a, c in sorted(dup_combos, key=lambda x: -x[2])[:5]:
        print(f"    {p/1e9:.2f}B @ {a:.0f}m2: {c}x")
print()

# --- DUPLICATE BUYER REQUIREMENTS ---
dup_br = db.query(
    BuyerRequirement.min_budget, BuyerRequirement.max_budget,
    BuyerRequirement.district, func.count(BuyerRequirement.id).label("cnt")
).group_by(
    BuyerRequirement.min_budget, BuyerRequirement.max_budget,
    BuyerRequirement.district
).having(func.count(BuyerRequirement.id) > 5).all()
print("BUYER REQUIREMENTS DUPLICATES:")
print(f"  Budget+District combos appearing >5x: {len(dup_br)}")
for lo, hi, dist, cnt in sorted(dup_br, key=lambda x: -x[3])[:5]:
    print(f"    {dist}: {lo/1e9:.1f}-{hi/1e9:.1f}B: {cnt}x")
print()

# --- VALIDATION SCORE ---
quality_ppm = db.query(
    func.round(Property.price_per_m2 / 1e6, 0).label("rounded_ppm"),
    func.count(Property.id).label("cnt")
).filter(Property.price_per_m2.isnot(None)).group_by(
    func.round(Property.price_per_m2 / 1e6, 0)
).order_by(func.count(Property.id).desc()).limit(10).all()

print("TOP 10 most common price/m2 values:")
for rounded_ppm, cnt in quality_ppm:
    print(f"  {rounded_ppm}M/m2: {cnt} records ({cnt/total*100:.1f}%)")
print()

# --- EVIDENCE TIER AUDIT ---
print("EVIDENCE TIER AUDIT:")
for tier in ["E1", "E2", "E3", "E4", "E5"]:
    cnt = db.query(Property).filter(Property.evidence_tier == tier).count()
    print(f"  {tier}: {cnt} ({cnt/total*100:.1f}%)")
print()

# --- FRESHNESS AUDIT ---
from datetime import datetime, timedelta
recent = db.query(Property).filter(
    Property.source_crawl_at.isnot(None),
    Property.source_crawl_at >= datetime.now() - timedelta(days=7)
).count()
print(f"RECENT (<7 days): {recent}/{total}")
print()

# --- FINAL VERDICT ---
print("=" * 50)
print("VERDICT:")
print(f"  Supply real (public_collected + URL): {real_source} ({real_source/total*100:.1f}%)")
print(f"  Supply fake/seeded: {fake_source} ({fake_source/total*100:.1f}%)")
print(f"  Supply missing source_url: {without_url}")
print(f"  Buyer real (web scraped): {real_src_br} ({real_src_br/buyer_total*100:.1f}%)")
print(f"  Buyer survey/seeded: {survey_br} ({survey_br/buyer_total*100:.1f}%)")
print(f"  Price diversity: {unique_ppm/total*100:.1f}% unique ppm")
print(f"  Duplicate price+area combos >3x: {len(dup_combos)}")
print(f"  Buyer duplicate budget+district combos >5x: {len(dup_br)}")
print()

# DEMAND: Buyer requirements
# 600 survey records are SEEDED — need to check if tin_can_mua is the REAL data
print("CRITICAL FINDINGS:")
if fake_source > 0:
    print(f"  ISSUE: {fake_source} supply records are system_demo/seeded — NOT real scraped data")
if without_url > 0:
    print(f"  ISSUE: {without_url} supply records have no source_url — untraceable")
if unique_ppm / total < 0.3:
    print(f"  ISSUE: Low price diversity ({unique_ppm/total*100:.1f}%) — possible fake/generated data")
if len(dup_combos) > 10:
    print(f"  ISSUE: {len(dup_combos)} duplicate price+area combos — possible batch-generated data")
if survey_br > buyer_total * 0.8:
    pct = survey_br / buyer_total * 100
    print(f"  ISSUE: {pct:.0f}% of buyer requirements are survey/seeded (NOT real web scraped)")

db.close()
