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
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

for env_name in (".env", ".env.postgres.local"):
    env_path = PROJECT_ROOT / env_name
    if env_path.exists():
        load_dotenv(env_path)
        break

def main():
    parser = argparse.ArgumentParser(description="ML Retraining Orchestrator v2")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rollback", type=str, metavar="VERSION")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--test-size", type=float, default=0.15)
    parser.add_argument("--min-clean", type=int, default=500)
    args = parser.parse_args()

    if not os.environ.get("DATABASE_URL", "").startswith("postgresql"):
        raise SystemExit("Refusing retrain: DATABASE_URL is not PostgreSQL")

    if args.list:
        from scripts.mlops import cmd_experiments
        cmd_experiments(args)
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
    if validation["clean_count"] < args.min_clean:
        raise SystemExit(
            f"Refusing retrain: only {validation['clean_count']} clean records; "
            f"minimum is {args.min_clean}"
        )
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

    # Step 6: Synchronize the exact artifact stamp into canonical lineage.
    # Never create a second timestamp a few seconds later: that was the source
    # of duplicate model rows in the old registry.
    print("\n[Step 6/6] Synchronizing PostgreSQL ML lineage...")
    version_str = Path(model_path).stem.removeprefix("model_")
    from scripts.sync_ml_registry import sync_registry
    sync_result = sync_registry(PROJECT_ROOT / "models")
    print(
        f"[OK] Registered exact artifact version {version_str}; "
        f"metadata files={sync_result['metadata_files']}"
    )

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
