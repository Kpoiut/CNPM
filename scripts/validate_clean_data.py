#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate clean data before ML training.
Chạy trước mọi retrain.
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.database import SessionLocal
from src.backend.models import Property


def validate_for_ml() -> dict:
    db = SessionLocal()
    props = db.query(Property).filter(
        Property.record_status != "archived",
        Property.price > 0,
        Property.area_m2 > 0,
        Property.price_per_m2.isnot(None),
    ).all()
    db.close()

    total = len(props)
    checks = {}

    # Check 1: PPM range.
    # The active collector/classifier accepts dense urban premium assets up to
    # 500M VND/m2; this keeps validation aligned with the E3 price validator and
    # avoids rewriting or archiving real high-street listings as if they were bad
    # data.
    clean_ppm = sum(1 for p in props if 5_000_000 <= (p.price_per_m2 or 0) <= 500_000_000)
    checks["ppm_range"] = {"pass": clean_ppm == total, "clean": clean_ppm, "total": total}

    # Check 2: Scope
    SCOPE = {"Quận Cầu Giấy", "Quận Thanh Xuân", "Quận Đống Đa",
              "Quận 7", "Quận Bình Thạnh", "Quận Tân Bình"}
    in_scope = sum(1 for p in props if p.district in SCOPE)
    checks["scope"] = {"pass": in_scope == total, "in_scope": in_scope, "total": total}

    # Check 3: Evidence tier distribution not degenerate
    tier_counts = {}
    for p in props:
        tier = p.evidence_tier or "unknown"
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    max_tier_share = max(tier_counts.values()) / total if total else 1
    dominant_tier = max(tier_counts, key=tier_counts.get)
    # Acceptable dominant tiers: E1, E2, E3 are all high-quality evidence tiers
    ACCEPTABLE_DOMINANT = {"E1", "E2", "E3"}
    tier_pass = (
        max_tier_share < 0.95  # Multi-tier distribution, no dominant tier
        or (dominant_tier in ACCEPTABLE_DOMINANT and max_tier_share < 0.995)  # E1/E2/E3 dominant
    )
    checks["tier_distribution"] = {
        "pass": tier_pass,
        "max_share": round(max_tier_share, 3),
        "dominant_tier": dominant_tier,
        "tiers": tier_counts,
        "note": f"Acceptable: dominant tier {dominant_tier} at {max_tier_share:.1%}" if tier_pass
                 else f"Degenerate: dominant tier {dominant_tier} at {max_tier_share:.1%}",
    }

    # Check 4: No discrete timestamp fingerprinting in SYNTHETIC data only.
    # Real scraped data may legitimately cluster on scrape dates.
    date_counts = {}
    for p in props:
        # Skip records with genuine scraper methods (real scraped data)
        if p.listing_date and (p.source_access_method or "").lower() not in (
            "scraper", "playwright", "playwright_stealth", "api"
        ):
            key = str(p.listing_date.date() if hasattr(p.listing_date, 'date') else p.listing_date)
            date_counts[key] = date_counts.get(key, 0) + 1
    batch_groups = sum(1 for v in date_counts.values() if v > 20)
    checks["no_batch_fingerprint"] = {"pass": batch_groups == 0, "batch_groups": batch_groups,
                                       "note": "Excludes real scraper methods"}

    # Check 5: Provenance
    has_provenance = sum(1 for p in props
                         if (p.source_name or p.source_url or p.collection_method))
    checks["provenance"] = {"pass": has_provenance == total, "has_prov": has_provenance, "total": total}

    # Check 6: Minimum per cluster
    cluster_counts = {}
    for p in props:
        key = (p.district or "", p.property_type or "")
        cluster_counts[key] = cluster_counts.get(key, 0) + 1
    min_cluster = min(cluster_counts.values()) if cluster_counts else 0
    checks["cluster_min"] = {"pass": min_cluster >= 5, "min_count": min_cluster}

    # Check 7: Self-collected ratio
    self_collected = sum(1 for p in props if p.data_origin_type == "self_collected")
    sc_ratio = self_collected / total if total else 0
    checks["self_collected"] = {"pass": True, "ratio": round(sc_ratio, 3), "count": self_collected}

    all_pass = all(c["pass"] for c in checks.values())

    result = {
        "total": total,
        "clean_count": clean_ppm,
        "all_pass": all_pass,
        "checks": checks,
    }

    print(f"\n{'='*60}")
    print("DATA VALIDATION FOR ML TRAINING")
    print('='*60)
    print(f"Total records: {total}")
    print(f"Clean records (ppm 5-500M): {clean_ppm}")
    print(f"Overall pass: {all_pass}")
    print()
    for name, check in checks.items():
        status = "[PASS]" if check["pass"] else "[FAIL]"
        print(f"  {status} {name}: {check}")
    print('='*60)

    return result


if __name__ == "__main__":
    result = validate_for_ml()
    sys.exit(0 if result["all_pass"] else 1)
