#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compute and cache global SHAP explanations for the current model.
Run once after each model retrain.

Usage: python scripts/compute_shap_explanations.py
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

for env_name in (".env", ".env.postgres.local"):
    env_path = PROJECT_ROOT / env_name
    if env_path.exists():
        load_dotenv(env_path)
        break

if not os.environ.get("DATABASE_URL", "").startswith("postgresql"):
    raise SystemExit("Refusing SHAP computation: DATABASE_URL is not PostgreSQL")

from datetime import datetime
import json
import numpy as np

from src.backend.database import SessionLocal
from src.backend.models import Property
from src.ml.pipeline import MLPipeline


def compute_and_cache():
    print("[1/4] Loading model...")
    pipeline = MLPipeline()
    pipeline.load()
    model_version = pipeline.metadata.get("trained_at", datetime.now().strftime("%Y%m%d_%H%M%S"))

    print("[2/4] Loading data...")
    db = SessionLocal()
    props = db.query(Property).filter(
        Property.record_status != "archived",
        Property.price > 0,
        Property.area_m2 > 0,
        Property.price_per_m2 > 0,
    ).all()
    db.close()

    print(f"[3/4] Computing SHAP on {len(props)} records...")
    # Stratified sample: max 500 rows, proportional by property_type
    import random
    from collections import defaultdict

    clusters = defaultdict(list)
    for i, p in enumerate(props):
        key = p.property_type
        clusters[key].append(i)

    sample_indices = []
    max_per_cluster = max(1, 500 // len(clusters))
    for indices in clusters.values():
        sample = random.sample(indices, min(len(indices), max_per_cluster))
        sample_indices.extend(sample)

    # Build feature matrix
    X_sample = []
    for idx in sample_indices:
        p = props[idx]
        try:
            feat = pipeline._build_features(p)
            X_sample.append(feat)
        except Exception:
            pass

    if not X_sample:
        print("[WARN] No features could be built — skipping SHAP")
        return

    X = np.array(X_sample)
    print(f"  Feature matrix shape: {X.shape}")

    print("  Computing SHAP TreeExplainer (this may take ~30s)...")
    import shap
    explainer = shap.TreeExplainer(pipeline.best_model)
    shap_values = explainer.shap_values(X)

    # Global feature importance
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    importance = list(zip(pipeline.feature_names, mean_abs_shap.tolist()))
    importance.sort(key=lambda x: x[1], reverse=True)

    # Beeswarm data (top 20 features × top 100 samples by abs SHAP)
    top_features = [f for f, _ in importance[:20]]
    beeswarm_data = []
    for feat_name in top_features:
        feat_idx = pipeline.feature_names.index(feat_name)
        beeswarm_data.append({
            "feature": feat_name,
            "values": X[:, feat_idx].tolist()[:200],
            "shap_values": shap_values[:200, feat_idx].tolist(),
        })

    cache = {
        "model_version": model_version,
        "feature_importance": [{"feature": f, "importance": float(v)} for f, v in importance[:30]],
        "beeswarm_data": beeswarm_data,
        "sample_size": len(X),
        "n_features": len(pipeline.feature_names),
        "computed_at": datetime.now().isoformat(),
    }

    print("[4/4] Saving cache...")
    cache_path = Path(pipeline.model_dir) / "shap_global_cache.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

    print(f"[OK] SHAP cache saved: {cache_path}")
    print(f"     Top 10 features:")
    for f, v in importance[:10]:
        print(f"       {f:40s}: {v:.4f}")

    return cache


if __name__ == "__main__":
    compute_and_cache()
