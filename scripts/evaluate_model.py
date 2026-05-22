#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Post-retrain model evaluation against expert ground truth.
So sanh ML predictions vs expert ratings.
"""
import sys
from pathlib import Path
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.database import SessionLocal
from src.backend.models import Property, ExpertRating, ExpertProperty


def evaluate():
    db = SessionLocal()

    # Load expert ground truth
    expert_props = db.query(ExpertProperty).filter(
        ExpertProperty.status == "completed"
    ).all()

    if not expert_props:
        print("[WARN] No completed expert evaluations found.")
        print("  Run expert evaluation first or seed demo ratings.")
        db.close()
        return

    # Aggregate expert ratings per property
    from statistics import median

    expert_mids = {}
    for ep in expert_props:
        ratings = db.query(ExpertRating).filter(
            ExpertRating.property_id == ep.property_id
        ).all()
        if ratings:
            mids = [r.expert_mid for r in ratings]
            expert_mids[ep.property_id] = median(mids)

    if not expert_mids:
        print("[WARN] No expert ratings found.")
        db.close()
        return

    # Load properties
    prop_ids = list(expert_mids.keys())
    props = db.query(Property).filter(Property.id.in_(prop_ids)).all()
    prop_map = {p.id: p for p in props}

    # Load model
    from src.ml.pipeline import MLPipeline
    pipeline = MLPipeline()
    pipeline.load()

    # Evaluate
    results = []
    for prop_id, expert_mid in expert_mids.items():
        prop = prop_map.get(prop_id)
        if not prop:
            continue

        try:
            features = pipeline._build_features(prop)
            X = np.array([features])
            pred = float(pipeline.best_model.predict(X)[0])
            # expert_mid is stored in VND per m² — multiply by area to get total price
            area = float(prop.area_m2 or 80)
            expert_total = expert_mid * area  # VND/m² * m² = VND
            error_pct = abs(pred - expert_total) / expert_total * 100
            results.append({
                "property_id": prop_id,
                "district": prop.district,
                "property_type": prop.property_type,
                "listing_price": prop.price,
                "expert_total": expert_total,
                "ml_pred": pred,
                "error_pct": error_pct,
            })
        except Exception as e:
            print(f"[WARN] Failed on property {prop_id}: {e}")

    if not results:
        print("[WARN] No successful evaluations")
        db.close()
        return

    # Compute metrics
    errors = [r["error_pct"] for r in results]
    mape = sum(errors) / len(errors)
    median_ape = sorted(errors)[len(errors) // 2]

    # MAPE by district
    districts = {}
    for r in results:
        d = r["district"]
        districts.setdefault(d, []).append(r["error_pct"])

    print(f"\n{'='*60}")
    print("MODEL EVALUATION vs EXPERT GROUND TRUTH")
    print('='*60)
    print(f"  Sample size:        {len(results)} properties")
    print(f"  Overall MAPE:      {mape:.1f}%")
    print(f"  Median APE:       {median_ape:.1f}%")
    print()
    print("  MAPE by district:")
    for dist, errs in sorted(districts.items()):
        d_mape = sum(errs) / len(errs)
        print(f"    {dist:25s}: {d_mape:5.1f}% (n={len(errs)})")
    print()

    # Per-property breakdown
    print("  Top 5 worst predictions:")
    worst = sorted(results, key=lambda x: -x["error_pct"])[:5]
    for r in worst:
        print(f"    id={r['property_id']:5d} district={r['district']:20s} "
              f"expert={r['expert_total']/1e9:.2f}B ml={r['ml_pred']/1e9:.2f}B error={r['error_pct']:.0f}%")

    db.close()
    print('='*60)
    return {"mape": mape, "median_ape": median_ape, "n": len(results)}


if __name__ == "__main__":
    evaluate()
