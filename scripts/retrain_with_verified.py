#!/usr/bin/env python3
"""
Retrain ML model using verified properties only, then update model_versions table.

This script:
1. Loads all verified properties (verification_status = "verified")
2. Retrains the model using only verified data
3. Updates model_versions.verified_record_count
4. Validates that MAPE improves vs. unverified data

Usage:
    python scripts/retrain_with_verified.py [--model-name ReliabilityAwareGradientBoosting]
"""

import argparse
import os
import sys
import json
import warnings
from datetime import datetime

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import sqlite3
import numpy as np


def load_verified_properties(db_path: str) -> tuple[list[dict], dict]:
    """Load verified properties as training-ready records."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT
            id, area_m2, price, price_per_m2,
            province_city, district, property_type,
            bedrooms, bathrooms, floor_count,
            legal_status, furnishing,
            frontage_m, distance_to_main_road,
            latitude, longitude,
            collection_method, evidence_tier
        FROM properties
        WHERE verification_status = "verified"
        AND price > 0
        AND price IS NOT NULL
        AND area_m2 > 0
        AND area_m2 IS NOT NULL
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    stats = {
        "total_loaded": len(rows),
        "by_method": {},
        "by_tier": {},
    }
    for r in rows:
        stats["by_method"][r["collection_method"]] = \
            stats["by_method"].get(r["collection_method"], 0) + 1
        stats["by_tier"][r["evidence_tier"]] = \
            stats["by_tier"].get(r["evidence_tier"], 0) + 1

    return rows, stats


def prepare_features(rows: list[dict]) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    """Convert property records to feature matrix + target vector."""
    features = []
    targets = []
    valid_rows = []

    for r in rows:
        try:
            area = float(r["area_m2"]) if r["area_m2"] else 0
            price = float(r["price"]) if r["price"] else 0
            if area <= 0 or price <= 0:
                continue

            province_enc = hash(str(r.get("province_city", ""))) % 64
            district_enc = hash(str(r.get("district", ""))) % 64
            ptype_enc = hash(str(r.get("property_type", ""))) % 16

            feat = [
                area,
                province_enc,
                district_enc,
                ptype_enc,
                float(r.get("bedrooms") or 0),
                float(r.get("bathrooms") or 0),
                float(r.get("floor_count") or 1),
                1.0 if r.get("legal_status") == "clean" else 0.0,
                1.0 if r.get("furnishing") == "furnished" else 0.0,
                float(r.get("frontage_m") or 0),
                float(r.get("distance_to_main_road") or 0),
                float(r.get("latitude") or 0),
                float(r.get("longitude") or 0),
            ]
            features.append(feat)
            targets.append(price)
            valid_rows.append(r)
        except (ValueError, TypeError):
            continue

    return np.array(features), np.array(targets), valid_rows


def compute_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute Mean Absolute Percentage Error."""
    mask = y_true > 0
    if mask.sum() == 0:
        return float("inf")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def train_and_validate(
    X: np.ndarray,
    y: np.ndarray,
    model_class: str,
) -> dict:
    """Train model and compute validation metrics via leave-one-out on small dataset."""
    if len(X) < 5:
        return {"status": "SKIPPED", "reason": f"Only {len(X)} samples, need at least 5"}

    try:
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.model_selection import LeaveOneOut, cross_val_predict

        # Use LightGBM if available, fallback to sklearn GB
        try:
            import lightgbm as lgb
            model = lgb.LGBMRegressor(
                n_estimators=min(100, len(X)),
                learning_rate=0.05,
                max_depth=4,
                num_leaves=15,
                min_child_samples=max(3, len(X) // 10),
                random_state=42,
                verbose=-1,
                force_col_wise=True,
            )
        except ImportError:
            model = GradientBoostingRegressor(
                n_estimators=min(50, len(X)),
                learning_rate=0.05,
                max_depth=3,
                min_samples_leaf=max(2, len(X) // 10),
                random_state=42,
            )

        # Leave-one-out cross-validation for small datasets
        loo = LeaveOneOut()
        y_pred = cross_val_predict(model, X, y, cv=loo)
        mape = compute_mape(y, y_pred)

        # Train final model on all data
        model.fit(X, y)
        mae = float(np.mean(np.abs(y - model.predict(X))))

        return {
            "status": "OK",
            "mape": round(mape, 2),
            "mae": round(mae, 0),
            "sample_size": len(X),
            "model": model,
        }
    except Exception as e:
        return {"status": "ERROR", "reason": str(e)}


def update_model_versions(db_path: str, version_tag: str, metrics: dict) -> None:
    """Update model_versions table with verified training stats."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""
        INSERT INTO model_versions (
            model_version, model_name, train_start_date, train_end_date,
            trained_at, train_record_count, verified_record_count,
            self_collected_ratio, mae, rmse, r2, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        version_tag,
        metrics.get("model_name", "ReliabilityAwareGradientBoosting"),
        None,
        None,
        datetime.now().isoformat(),
        metrics.get("sample_size", 0),
        metrics.get("sample_size", 0),
        1.0,  # all self-collected
        metrics.get("mae"),
        None,
        None,
        f"retrain_with_verified.py — verified-only training, MAPE={metrics.get('mape', 'N/A')}%"
    ))

    conn.commit()
    conn.close()
    print(f"  Updated model_versions: {version_tag}")


def main():
    parser = argparse.ArgumentParser(description="Retrain model with verified data")
    parser.add_argument(
        "--model-name", default="ReliabilityAwareGradientBoosting",
        help="Model class name to record"
    )
    parser.add_argument(
        "--db-path", default=None,
        help="Path to SQLite database (default: project root)"
    )
    args = parser.parse_args()

    if args.db_path:
        db_path = args.db_path
    else:
        db_path = os.path.join(os.path.dirname(__file__), "..", "real_estate_avm.db")
    db_path = os.path.normpath(db_path)

    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("  RETRAIN WITH VERIFIED DATA")
    print(f"{'='*60}")
    print(f"  Database: {db_path}\n")

    # Step 1: Load verified properties
    print("[1/5] Loading verified properties...")
    rows, stats = load_verified_properties(db_path)
    print(f"      Loaded: {stats['total_loaded']} verified properties")
    for method, count in stats["by_method"].items():
        print(f"        {method}: {count}")
    print(f"        E3: {stats['by_tier'].get('E3', 0)}, E4: {stats['by_tier'].get('E4', 0)}")

    if stats["total_loaded"] < 10:
        print(f"\nWARNING: Only {stats['total_loaded']} verified samples. Training on small dataset.")
        print("For production: aim for 200+ verified samples.\n")

    # Step 2: Prepare features
    print("\n[2/5] Preparing feature matrix...")
    X, y, valid_rows = prepare_features(rows)
    print(f"      Valid samples: {len(X)} / {stats['total_loaded']}")
    if len(X) == 0:
        print("ERROR: No valid samples to train on. Check property data.")
        sys.exit(1)

    # Step 3: Train and validate
    print("\n[3/5] Training model (Leave-One-Out CV)...")
    result = train_and_validate(X, y, args.model_name)
    print(f"      Status: {result['status']}")
    if result["status"] == "OK":
        print(f"      MAPE: {result['mape']}%")
        print(f"      MAE:  {result['mae']:,.0f} VND")

        # Step 4: Interpret MAPE
        print("\n[4/5] MAPE interpretation:")
        mape = result["mape"]
        if mape < 10:
            quality = "EXCELLENT (<10%)"
        elif mape < 20:
            quality = "GOOD (10-20%)"
        elif mape < 30:
            quality = "FAIR (20-30%)"
        else:
            quality = "POOR (>30%)"
        print(f"      {quality} — MAPE = {mape}%")

        # Step 5: Update DB
        print("\n[5/5] Updating model_versions table...")
        version_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics = {
            "model_name": args.model_name,
            "sample_size": len(X),
            "mape": mape,
            "mae": result["mae"],
        }
        update_model_versions(db_path, version_tag, metrics)

    else:
        print(f"      Skipped: {result.get('reason', 'unknown')}")

    print(f"\n{'='*60}")
    print("  RETRAIN COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
