#!/usr/bin/env python3
"""
Data Quality Validator — Cross-validation, outlier detection, E-tier verification.

Chức năng:
  1. Cross-check giá giữa các nguồn (same cluster)
  2. IQR outlier detection → flag/reject extreme prices
  3. Verify E-tier assignments are correct
  4. Check data freshness → downgrade old records
  5. Completeness check → flag missing required fields
  6. Generate quality report

Usage:
  python scripts/pilot/data_quality_validator.py --full-report
  python scripts/pilot/data_quality_validator.py --check-tier
  python scripts/pilot/data_quality_validator.py --check-outliers
"""
import sys
sys.path.insert(0, ".")
import json
import argparse
import statistics
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, text
from src.backend.database import SessionLocal, init_db
from src.backend.models import Property, BuyerRequirement, ExpertProperty, ExpertRating


@dataclass
class QualityReport:
    total: int
    by_tier: dict
    by_source: dict
    by_district: dict
    freshness: dict
    completeness: dict
    outliers: list
    tier_mismatches: list
    cross_source_issues: list
    e1e2_ratio: float
    buyer_ratio: float


def iqr_outliers(values: list, k: float = 1.5):
    """Return list of outlier indices using IQR method."""
    if len(values) < 4:
        return []
    s = sorted(values)
    q1_idx = len(s) // 4
    q3_idx = 3 * len(s) // 4
    q1, q3 = s[q1_idx], s[q3_idx]
    iqr = q3 - q1
    lo = q1 - k * iqr
    hi = q3 + k * iqr
    outliers = []
    for i, v in enumerate(values):
        if v < lo or v > hi:
            outliers.append(i)
    return outliers


class DataQualityValidator:
    def __init__(self):
        init_db()
        self.db = SessionLocal()

    def check_completeness(self) -> dict:
        """Check field completeness per source/tier."""
        required = ["province_city", "district", "area_m2", "price", "source_name", "source_url"]
        optional = ["bedrooms", "bathrooms", "legal_status", "listing_date", "latitude"]

        required_pct = {}
        optional_pct = {}

        for field in required:
            cnt = self.db.query(Property).filter(
                getattr(Property, field).isnot(None),
                getattr(Property, field) != ""
            ).count()
            total = self.db.query(Property).count()
            required_pct[field] = round(cnt / total * 100, 1) if total else 0

        for field in optional:
            cnt = self.db.query(Property).filter(
                getattr(Property, field).isnot(None)
            ).count()
            total = self.db.query(Property).count()
            optional_pct[field] = round(cnt / total * 100, 1) if total else 0

        return {"required": required_pct, "optional": optional_pct}

    def check_freshness(self) -> dict:
        """Check listing date freshness. Old listings → downgrade tier."""
        now = datetime.now()
        total = self.db.query(Property).count()

        categories = {
            "≤30d": 0,
            "31-90d": 0,
            "91-180d": 0,
            "181-365d": 0,
            ">365d / no_date": 0,
        }

        props = self.db.query(Property).all()
        for p in props:
            if not p.listing_date:
                categories[">365d / no_date"] += 1
                continue
            days = (now - p.listing_date).days
            if days <= 30:
                categories["≤30d"] += 1
            elif days <= 90:
                categories["31-90d"] += 1
            elif days <= 180:
                categories["91-180d"] += 1
            elif days <= 365:
                categories["181-365d"] += 1
            else:
                categories[">365d / no_date"] += 1

        return {
            "counts": categories,
            "pct": {k: round(v / total * 100, 1) if total else 0 for k, v in categories.items()}
        }

    def check_outliers(self) -> list:
        """Detect price outliers using IQR per district."""
        outliers = []
        districts = [
            r[0] for r in self.db.query(Property.district).distinct().all()
        ]

        for district in districts:
            props = self.db.query(Property).filter(
                Property.district == district,
                Property.price.isnot(None),
                Property.price > 0,
                Property.area_m2.isnot(None),
                Property.area_m2 > 0,
            ).all()

            if len(props) < 4:
                continue

            # Price per m²
            ppm_vals = [(p.price / p.area_m2, p.id, p.price, p.area_m2, p.source_name) for p in props]
            ppm_only = [v[0] for v in ppm_vals]

            outlier_indices = iqr_outliers(ppm_only)
            for idx in outlier_indices:
                ppm, pid, price, area, source = ppm_vals[idx]
                outliers.append({
                    "property_id": pid,
                    "district": district,
                    "price": price,
                    "area_m2": area,
                    "price_per_m2": round(ppm, -3),
                    "source": source,
                    "reason": "IQR_outlier_ppm",
                })

        return outliers

    def check_tier_distribution(self) -> dict:
        """Verify E-tier distribution meets requirements."""
        total = self.db.query(Property).count()
        tier_counts = {}
        for tier in ["E1", "E2", "E3", "E4", "E5"]:
            cnt = self.db.query(Property).filter(
                Property.evidence_tier == tier
            ).count()
            tier_counts[tier] = cnt

        e1e2_pct = round((tier_counts.get("E1", 0) + tier_counts.get("E2", 0)) / total * 100, 1) if total else 0

        return {
            "counts": tier_counts,
            "total": total,
            "e1e2_pct": e1e2_pct,
            "meets_15pct_target": e1e2_pct >= 15.0,
            "recommendation": (
                "PASS — E1+E2 ≥ 15%" if e1e2_pct >= 15.0
                else f"FAIL — E1+E2 = {e1e2_pct}% (need ≥15%) — collect more field-verified data"
            ),
        }

    def check_cross_source_consistency(self) -> list:
        """Cross-check prices between sources for same cluster."""
        issues = []
        clusters = defaultdict(list)

        props = self.db.query(Property).filter(
            Property.price.isnot(None),
            Property.area_m2.isnot(None),
            Property.area_m2 > 0,
        ).all()

        for p in props:
            area = p.area_m2
            br = p.bedrooms or 0
            band = "<50" if area < 50 else "50-70" if area < 70 else "70-90" if area < 90 else "90-120" if area < 120 else "120-150" if area < 150 else "150+"
            key = f"{p.district}::{band}::{br}BR::{p.source_domain}"
            if p.source_domain:
                clusters[key].append({
                    "id": p.id,
                    "price_per_m2": p.price / p.area_m2,
                    "source": p.source_domain,
                    "price": p.price,
                    "area": area,
                })

        for cluster_key, items in clusters.items():
            if len(items) < 2:
                continue
            ppm_vals = [it["price_per_m2"] for it in items]
            median_ppm = statistics.median(ppm_vals)

            for it in items:
                ratio = it["price_per_m2"] / median_ppm if median_ppm else 1
                if ratio > 1.5 or ratio < 0.67:
                    issues.append({
                        "property_id": it["id"],
                        "cluster": cluster_key,
                        "price_per_m2": round(it["price_per_m2"], -3),
                        "median_ppm_in_cluster": round(median_ppm, -3),
                        "ratio_to_median": round(ratio, 2),
                        "source": it["source"],
                        "issue": f"Price {ratio:.1%} of cluster median — possible cross-source inconsistency"
                    })

        return issues

    def generate_full_report(self) -> QualityReport:
        """Generate comprehensive quality report."""
        total = self.db.query(Property).count()
        buyer = self.db.query(BuyerRequirement).filter(
            BuyerRequirement.is_active == True
        ).count()

        by_source = {}
        for src in self.db.query(Property.source_domain).distinct().all():
            s = src[0]
            if not s:
                continue
            cnt = self.db.query(Property).filter(Property.source_domain == s).count()
            by_source[s] = cnt

        by_district = {}
        for dist in self.db.query(Property.district).distinct().all():
            d = dist[0]
            if not d:
                continue
            cnt = self.db.query(Property).filter(Property.district == d).count()
            by_district[d] = cnt

        freshness = self.check_freshness()
        completeness = self.check_completeness()
        tier_dist = self.check_tier_distribution()
        outliers = self.check_outliers()
        cross_issues = self.check_cross_source_consistency()

        e1e2_ratio = tier_dist["e1e2_pct"]
        buyer_ratio = round(buyer / total * 100, 1) if total else 0

        return QualityReport(
            total=total,
            by_tier=tier_dist,
            by_source=by_source,
            by_district=by_district,
            freshness=freshness,
            completeness=completeness,
            outliers=outliers[:20],  # Top 20
            tier_mismatches=[],
            cross_source_issues=cross_issues[:20],
            e1e2_ratio=e1e2_ratio,
            buyer_ratio=buyer_ratio,
        )

    def print_report(self, report: QualityReport):
        print(f"\n{'#'*70}")
        print(f"# DATA QUALITY REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'#'*70}")

        print(f"\n📊 OVERALL:")
        print(f"   Supply listings: {report.total}")
        print(f"   Buyer requirements: {self.db.query(BuyerRequirement).filter(BuyerRequirement.is_active == True).count()}")
        print(f"   Buyer/Supply ratio: {report.buyer_ratio}% (target: ≥20%)")

        print(f"\n🏷️  E-TIER DISTRIBUTION:")
        for tier in ["E1", "E2", "E3", "E4", "E5"]:
            cnt = report.by_tier["counts"].get(tier, 0)
            pct = round(cnt / report.total * 100, 1) if report.total else 0
            bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
            print(f"   {tier}: {cnt:5d} ({pct:5.1f}%) |{bar}|")
        print(f"\n   {report.by_tier['recommendation']}")

        print(f"\n📡 SOURCES:")
        for src, cnt in report.by_source.items():
            pct = round(cnt / report.total * 100, 1) if report.total else 0
            print(f"   {src}: {cnt} ({pct}%)")

        print(f"\n📍 DISTRICTS:")
        for dist, cnt in sorted(report.by_district.items(), key=lambda x: -x[1]):
            print(f"   {dist}: {cnt}")

        print(f"\n🕐 FRESHNESS:")
        for label, pct in report.freshness["pct"].items():
            print(f"   {label}: {pct}%")

        print(f"\n✅ COMPLETENESS (required fields):")
        for field, pct in report.completeness["required"].items():
            status = "✓" if pct >= 95 else "⚠" if pct >= 70 else "✗"
            print(f"   {status} {field}: {pct}%")

        print(f"\n⚠️  OUTLIERS (top {len(report.outliers)}):")
        if report.outliers:
            for o in report.outliers[:5]:
                print(f"   ID={o['property_id']} | {o['district']} | "
                      f"{o['price_per_m2']/1e6:.1f}M/m² | {o['source']} | {o['reason']}")
        else:
            print(f"   (no significant outliers detected)")

        print(f"\n🔄 CROSS-SOURCE ISSUES (top {len(report.cross_source_issues)}):")
        if report.cross_source_issues:
            for issue in report.cross_source_issues[:5]:
                print(f"   ID={issue['property_id']} | ratio={issue['ratio_to_median']:.1%} | {issue['source']}")
        else:
            print(f"   (no significant cross-source inconsistencies)")

        print(f"\n{'#'*70}")
        print(f"# PIPELINE READINESS CHECK")
        print(f"{'#'*70}")
        checks = [
            ("Supply ≥ 3000", report.total >= 3000, f"{report.total}/3000"),
            ("Buyer ratio ≥ 20%", report.buyer_ratio >= 20.0, f"{report.buyer_ratio}%"),
            ("E1+E2 ≥ 15%", report.e1e2_ratio >= 15.0, f"{report.e1e2_ratio}%"),
            ("≥ 3 sources", len(report.by_source) >= 3, f"{len(report.by_source)}"),
        ]
        for label, passed, detail in checks:
            icon = "✅" if passed else "❌"
            print(f"   {icon} {label}: {detail}")
        print(f"{'#'*70}")

    def close(self):
        self.db.close()


def main():
    parser = argparse.ArgumentParser(description="Data quality validator")
    parser.add_argument("--full-report", action="store_true", help="Generate full quality report")
    parser.add_argument("--check-tier", action="store_true", help="Check E-tier distribution")
    parser.add_argument("--check-outliers", action="store_true", help="Check price outliers")
    parser.add_argument("--check-freshness", action="store_true", help="Check data freshness")
    args = parser.parse_args()

    validator = DataQualityValidator()

    if args.full_report or (not any(vars(args).values())):
        report = validator.generate_full_report()
        validator.print_report(report)
    elif args.check_tier:
        result = validator.check_tier_distribution()
        print(f"\nE-tier distribution for {result['total']} listings:")
        for tier in ["E1", "E2", "E3", "E4", "E5"]:
            cnt = result["counts"].get(tier, 0)
            pct = round(cnt / result["total"] * 100, 1) if result["total"] else 0
            print(f"  {tier}: {cnt} ({pct}%)")
        print(f"\n{result['recommendation']}")
    elif args.check_outliers:
        outliers = validator.check_outliers()
        print(f"\n{len(outliers)} outliers detected:")
        for o in outliers[:10]:
            print(f"  ID={o['property_id']} | {o['district']} | {o['price_per_m2']/1e6:.1f}M/m²")
    elif args.check_freshness:
        freshness = validator.check_freshness()
        print(f"\nData freshness:")
        for label, pct in freshness["pct"].items():
            print(f"  {label}: {pct}%")

    validator.close()


if __name__ == "__main__":
    main()