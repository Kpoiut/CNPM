"""Synchronize file-based ML artifacts into the PostgreSQL lineage tables."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
for env_name in (".env", ".env.postgres.local"):
    env_path = PROJECT_ROOT / env_name
    if env_path.exists():
        load_dotenv(env_path)
        break


def _number(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _integer(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _stamp(path: Path) -> str:
    return path.stem.removeprefix("metadata_")


def _parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metadata_to_lineage(path: Path, active_stamp: str | None = None) -> dict:
    metadata = json.loads(path.read_text(encoding="utf-8"))
    stamp = _stamp(path)
    model_name = str(metadata.get("best_model") or "unknown")
    result = metadata.get("all_results", {}).get(model_name, {}) or {}
    train_count = _integer(metadata.get("train_size")) or 0
    validation_count = _integer(metadata.get("validation_size")) or 0
    test_count = _integer(metadata.get("test_size", result.get("n_test"))) or 0
    total_count = train_count + validation_count + test_count
    if total_count == 0:
        total_count = _integer(metadata.get("training_quality_summary", {}).get("profile_count")) or 0
    split_manifest = metadata.get("split_manifest", {}) or {}
    split_notes = {
        key: split_manifest.get(key)
        for key in (
            "record_order",
            "random_state",
            "train_sha256",
            "validation_sha256",
            "test_sha256",
        )
        if split_manifest.get(key) is not None
    }

    metric_values = {
        "mae": _number(result.get("test_mae", result.get("mae"))),
        "mape": _number(result.get("test_mape")),
        "rmse": _number(result.get("test_rmse", result.get("rmse"))),
        "r2": _number(result.get("test_r2", result.get("r2"))),
        "median_ae": _number(result.get("test_median_ae")),
    }
    metrics = [
        {"split": "test", "name": name, "value": value, "is_primary": name == "mape"}
        for name, value in metric_values.items()
        if value is not None
    ]
    is_active = stamp == active_stamp

    return {
        "dataset": {
            "snapshot_key": f"properties-{stamp}",
            "source_table": "properties",
            "record_count": total_count,
            "eligible_record_count": total_count,
            "selection_query": (
                "6 configured districts AND record_status <> 'archived' "
                "AND price > 0 AND area_m2 > 0 ORDER BY properties.id ASC"
            ),
            "checksum_sha256": split_manifest.get("dataset_sha256"),
            "notes": (
                "Exact ordered dataset checksum from split manifest."
                if split_manifest.get("dataset_sha256")
                else "Historical snapshot reconstructed from metadata; exact row IDs unavailable."
            ),
        },
        "training_run": {
            "run_version": stamp,
            "status": "completed",
            "algorithm": model_name,
            "random_seed": 42,
            "train_record_count": train_count,
            "validation_record_count": validation_count,
            "test_record_count": test_count,
            "finished_at": _parse_datetime(metadata.get("trained_at")),
            "artifact_path": f"models/model_{stamp}.pkl",
            "metadata_path": f"models/{path.name}",
            "notes": json.dumps(split_notes, ensure_ascii=False) if split_notes else (
                "Historical run: exact train/validation/test membership unavailable."
            ),
        },
        "model": {
            "model_version": stamp,
            "model_name": model_name,
            "trained_at": _parse_datetime(metadata.get("trained_at")),
            "train_record_count": train_count,
            "mae": metric_values["mae"],
            "mape": metric_values["mape"],
            "rmse": metric_values["rmse"],
            "r2": metric_values["r2"],
            "median_ae": metric_values["median_ae"],
            "status": "production" if is_active else "candidate",
            "is_active": is_active,
            "activated_at": datetime.now() if is_active else None,
            "model_path": f"models/model_{stamp}.pkl",
            "metadata_path": f"models/{path.name}",
        },
        "metrics": metrics,
    }


def _active_stamp(models_dir: Path) -> str | None:
    pointer = models_dir / "ACTIVE_MODEL.json"
    if not pointer.exists():
        return None
    try:
        return str(json.loads(pointer.read_text(encoding="utf-8")).get("stamp") or "") or None
    except (OSError, json.JSONDecodeError):
        return None


def sync_registry(models_dir: Path) -> dict:
    from src.backend.database import SessionLocal
    from src.backend.models import DatasetVersion, ModelVersion, TrainingMetric, TrainingRun

    if not os.environ.get("DATABASE_URL", "").startswith("postgresql"):
        raise RuntimeError("Refusing registry sync: DATABASE_URL is not PostgreSQL")

    active = _active_stamp(models_dir)
    metadata_files = sorted(models_dir.glob("metadata_*.json"))
    db = SessionLocal()
    previous_run = None
    previous_model = None
    previous_mape = None

    try:
        db.query(ModelVersion).update({ModelVersion.is_active: False}, synchronize_session=False)
        for path in metadata_files:
            lineage = metadata_to_lineage(path, active)

            dataset_data = lineage["dataset"]
            dataset = db.query(DatasetVersion).filter_by(snapshot_key=dataset_data["snapshot_key"]).first()
            if dataset is None:
                dataset = DatasetVersion(**dataset_data)
                db.add(dataset)
                db.flush()
            else:
                for key, value in dataset_data.items():
                    setattr(dataset, key, value)

            run_data = lineage["training_run"]
            run = db.query(TrainingRun).filter_by(run_version=run_data["run_version"]).first()
            if run is None:
                run = TrainingRun(run_version=run_data["run_version"], dataset_version_id=dataset.id)
                db.add(run)
                db.flush()
            for key, value in run_data.items():
                setattr(run, key, value)
            run.dataset_version_id = dataset.id
            run.parent_training_run_id = previous_run.id if previous_run else None

            for metric_data in lineage["metrics"]:
                metric = db.query(TrainingMetric).filter_by(
                    training_run_id=run.id,
                    split_name=metric_data["split"],
                    metric_name=metric_data["name"],
                ).first()
                if metric is None:
                    metric = TrainingMetric(
                        training_run_id=run.id,
                        split_name=metric_data["split"],
                        metric_name=metric_data["name"],
                    )
                    db.add(metric)
                metric.metric_value = metric_data["value"]
                metric.is_primary = metric_data["is_primary"]

            model_data = lineage["model"]
            model = db.query(ModelVersion).filter_by(model_version=model_data["model_version"]).first()
            if model is None:
                model = ModelVersion(model_version=model_data["model_version"])
                db.add(model)
                db.flush()
            for key, value in model_data.items():
                setattr(model, key, value)
            model.training_run_id = run.id
            model.parent_model_version_id = previous_model.id if previous_model else None
            model.artifact_sha256 = _sha256(PROJECT_ROOT / str(model.model_path))
            model.improvement_mape_pct_points = (
                previous_mape - model.mape
                if previous_mape is not None and model.mape is not None
                else None
            )

            previous_run = run
            previous_model = model
            if model.mape is not None:
                previous_mape = model.mape

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {"metadata_files": len(metadata_files), "active_stamp": active}


def main() -> int:
    result = sync_registry(PROJECT_ROOT / "models")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
