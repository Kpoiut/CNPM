#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML Retraining Orchestrator v2.
Full retrain pipeline với clean data + model registry.

Usage:
    python scripts/retrain_v2.py                    # Full retrain
    python scripts/retrain_v2.py --dry-run          # Validate data only
    python scripts/retrain_v2.py --rollback VERSION # Rollback
    python scripts/retrain_v2.py --list            # List versions
"""
import argparse
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, timezone
import scripts.model_registry as registry


def _normalize_dt(value):
    if not value:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def main():
    parser = argparse.ArgumentParser(description="ML Retraining Orchestrator v2")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rollback", type=str, metavar="VERSION")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--test-size", type=float, default=0.15)
    parser.add_argument("--min-clean", type=int, default=500)
    args = parser.parse_args()

    if args.list:
        for v in registry.list_versions():
            print(f"  {v['version']} | {v['name']} | MAE={v.get('mae','?')} | R2={v.get('r2','?')}")
        return

    if args.rollback:
        print(f"[INFO] Rollback to {args.rollback} — not implemented (use model_versions table)")
        return

    # Step 1: Validate data
    print("\n[Step 1/6] Validating data quality...")
    from scripts.validate_clean_data import validate_for_ml
    validation = validate_for_ml()
    if not validation["all_pass"]:
        print(f"[FAIL] Data validation failed. Fix issues before retraining.")
        print(f"  Clean records: {validation['clean_count']}/{validation['total']}")
        sys.exit(1)
    print(f"[OK] Data validation passed — {validation['clean_count']} clean records")

    if args.dry_run:
        print("\n[Dry run — no training performed]")
        return

    # Step 2: Load data
    print("\n[Step 2/6] Loading data from DB...")
    from src.backend.database import SessionLocal
    from src.backend.models import Property

    db = SessionLocal()
    props = db.query(Property).filter(
        Property.record_status != "archived",
        Property.price > 0,
        Property.area_m2 > 0,
        Property.price_per_m2 > 0,
    ).all()
    verified_count = sum(1 for prop in props if prop.verification_status == "verified")
    self_collected_count = sum(1 for prop in props if prop.data_origin_type == "self_collected")
    train_start_date = min((_normalize_dt(prop.created_at) for prop in props if prop.created_at), default=None)
    train_end_date = max((_normalize_dt(prop.updated_at or prop.created_at) for prop in props if prop.updated_at or prop.created_at), default=None)
    db.close()
    print(f"[OK] Loaded {len(props)} properties")

    # Step 3: Run ML pipeline using the direct train_model approach
    print("\n[Step 3/6] Running ML training pipeline...")
    from src.ml.pipeline import MLPipeline
    from src.backend.database import SessionLocal
    from src.backend.models import Property

    pipeline = MLPipeline()
    db = SessionLocal()
    try:
        df, y = pipeline.load_data_from_db(db, include_self_collected=True)
        X = pipeline.preprocess(df, y=y.values)
        train_result = pipeline.train(X, y.values, test_size=args.test_size)
    finally:
        db.close()

    # Extract best model metrics — train() returns results dict keyed by model name
    best_name = train_result.get("best_model")
    if not best_name:
        best_name = min(
            (k for k in train_result if k not in ("best_model",)),  # filter meta keys
            key=lambda k: train_result[k].get("test_mae", float("inf"))
        )
    best_result = train_result.get(best_name, {})
    print(f"[OK] Training complete: {best_name}")
    print(f"     Test MAE: {best_result.get('test_mae', 'N/A'):,.0f} VND" if best_result.get('test_mae') else "     Test MAE: N/A")
    print(f"     Test MAPE: {best_result.get('test_mape', 'N/A'):.1f}%" if best_result.get('test_mape') else "     Test MAPE: N/A")
    print(f"     Test R2: {best_result.get('test_r2', 'N/A')}")

    # Step 4: Save model
    print("\n[Step 4/6] Saving model...")
    model_path = pipeline.save()
    print(f"[OK] Model saved: {model_path}")

    # Step 5: Compute SHAP
    print("\n[Step 5/6] Computing SHAP explanations...")
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "compute_shap_explanations.py")],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            print("[OK] SHAP explanations computed and cached")
        else:
            print(f"[WARN] SHAP computation failed: {result.stderr[:200]}")
    except Exception as e:
        print(f"[WARN] SHAP computation skipped: {e}")

    # Step 6: Register version
    print("\n[Step 6/6] Registering model version...")
    version_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    metadata = {
        "trained_at": version_str,
        "best_model": best_name,
        "n_train": len(props),
        "fit_train_size": train_result.get("train_size"),
        "validation_size": train_result.get("validation_size"),
        "test_size": train_result.get("test_size"),
        "verified_count": verified_count,
        "test_mae": best_result.get("test_mae"),
        "test_rmse": best_result.get("test_rmse"),
        "test_r2": best_result.get("test_r2"),
        "test_mape": best_result.get("test_mape"),
        "self_collected_ratio": round(self_collected_count / len(props), 4) if props else 0.0,
        "train_start_date": train_start_date,
        "train_end_date": train_end_date,
    }
    vid = registry.register_version(metadata, model_path, "post-cleanup-full-retrain")
    print(f"[OK] Registered as version {version_str} (id={vid})")

    # Clear model cache
    try:
        from src.ml.pipeline import _MODEL_CACHE
        _MODEL_CACHE.clear()
        print("[OK] Model cache cleared")
    except Exception:
        pass

    print(f"\n{'='*60}")
    print(f"Retrain complete!")
    print(f"  Model: {best_name}")
    print(f"  Version: {version_str}")
    print(f"  Records: {len(props)}")
    print(f"  MAE: {best_result.get('test_mae', 'N/A'):,.0f} VND" if best_result.get('test_mae') else "  MAE: N/A")
    print(f"  R2: {best_result.get('test_r2', 'N/A')}")
    print(f"  MAPE: {best_result.get('test_mape', 'N/A'):.1f}%" if best_result.get('test_mape') else "")
    print('='*60)


if __name__ == "__main__":
    main()
