#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Model registry — track model versions in DB.
"""
import sys
import json
from pathlib import Path
from datetime import datetime
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.database import SessionLocal
from src.backend.models import ModelVersion


def register_version(metadata: dict, model_path: str, notes: str = "") -> int:
    """Register a new model version in the DB."""
    from datetime import datetime as dt
    db = SessionLocal()
    mv = ModelVersion(
        model_version=metadata.get("trained_at", dt.now().strftime("%Y%m%d_%H%M%S")),
        model_name=metadata.get("best_model", "unknown"),
        train_start_date=metadata.get("train_start_date") if isinstance(metadata.get("train_start_date"), dt) else None,
        train_end_date=metadata.get("train_end_date") if isinstance(metadata.get("train_end_date"), dt) else None,
        train_record_count=metadata.get("n_train", 0),
        verified_record_count=metadata.get("verified_count", 0),
        self_collected_ratio=float(metadata.get("self_collected_ratio", 0.0)),
        mae=metadata.get("test_mae"),
        rmse=metadata.get("test_rmse"),
        r2=metadata.get("test_r2"),
        model_path=model_path,
        notes=notes,
    )
    db.add(mv)
    db.commit()
    vid = mv.id
    db.close()
    return vid


def list_versions(limit: int = 10) -> list:
    """List recent model versions."""
    db = SessionLocal()
    versions = db.query(ModelVersion).order_by(
        ModelVersion.trained_at.desc()
    ).limit(limit).all()
    db.close()
    return [{"id": v.id, "version": v.model_version, "name": v.model_name,
             "mae": v.mae, "r2": v.r2, "trained_at": v.trained_at}
            for v in versions]


def get_latest_version() -> dict:
    """Get the most recent model version."""
    db = SessionLocal()
    v = db.query(ModelVersion).order_by(ModelVersion.trained_at.desc()).first()
    db.close()
    if v:
        return {"id": v.id, "version": v.model_version, "name": v.model_name,
                "mae": v.mae, "r2": v.r2, "path": v.model_path,
                "trained_at": v.trained_at, "notes": v.notes}
    return {}


if __name__ == "__main__":
    print("\nMODEL REGISTRY")
    print("=" * 50)
    for v in list_versions():
        print(f"  {v['version']} | {v['name']} | MAE={v.get('mae','?')} | R2={v.get('r2','?')}")
