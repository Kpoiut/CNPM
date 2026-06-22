"""Model metric provenance helpers.

The project has multiple trained model snapshots. Production code must not
confuse the newest retrain with the best verified evaluation result.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ModelMetric:
    stamp: str
    model_name: str
    trained_at: str | None
    test_mae: float | None
    test_mape: float | None
    test_r2: float | None
    test_median_ae: float | None
    n_test: int | None
    train_size: int | None
    source_path: str

    def to_public_dict(self) -> dict:
        data = asdict(self)
        if self.test_mae is not None:
            data["test_mae"] = round(self.test_mae, 3)
        if self.test_mape is not None:
            data["test_mape"] = round(self.test_mape, 6)
        if self.test_r2 is not None:
            data["test_r2"] = round(self.test_r2, 6)
        if self.test_median_ae is not None:
            data["test_median_ae"] = round(self.test_median_ae, 3)
        return data


def _default_model_dirs() -> list[Path]:
    return [
        PROJECT_ROOT / "models",
        PROJECT_ROOT / "src" / "models_archive",
    ]


def _stamp_from_path(path: Path) -> str:
    match = re.search(r"metadata_(\d{8}_\d{6})", path.name)
    return match.group(1) if match else path.stem.replace("metadata_", "")


def _float_or_none(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _metric_from_metadata(path: Path) -> ModelMetric | None:
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    best_model = metadata.get("best_model") or "unknown"
    best_result = metadata.get("all_results", {}).get(best_model, {})
    if not isinstance(best_result, dict):
        best_result = {}

    return ModelMetric(
        stamp=_stamp_from_path(path),
        model_name=str(best_model),
        trained_at=metadata.get("trained_at"),
        test_mae=_float_or_none(best_result.get("test_mae", best_result.get("mae"))),
        test_mape=_float_or_none(best_result.get("test_mape")),
        test_r2=_float_or_none(best_result.get("test_r2", best_result.get("r2"))),
        test_median_ae=_float_or_none(best_result.get("test_median_ae")),
        n_test=_int_or_none(best_result.get("n_test", metadata.get("test_size"))),
        train_size=_int_or_none(metadata.get("train_size")),
        source_path=str(path),
    )


def load_model_metrics(model_dirs: Iterable[Path | str] | None = None) -> list[ModelMetric]:
    """Load all model metadata sorted newest first by embedded timestamp."""
    dirs = [Path(p) for p in (model_dirs or _default_model_dirs())]
    metadata_files: list[Path] = []
    for directory in dirs:
        if directory.exists():
            metadata_files.extend(directory.glob("metadata_*.json"))

    metrics = [
        metric
        for path in metadata_files
        if (metric := _metric_from_metadata(path)) is not None
    ]
    metrics.sort(key=lambda metric: metric.stamp, reverse=True)
    return metrics


def select_latest_metric(metrics: Iterable[ModelMetric]) -> ModelMetric | None:
    metrics = list(metrics)
    return metrics[0] if metrics else None


def select_best_verified_metric(metrics: Iterable[ModelMetric]) -> ModelMetric | None:
    verified = [metric for metric in metrics if metric.test_mape is not None]
    if verified:
        return min(verified, key=lambda metric: metric.test_mape or float("inf"))
    with_mae = [metric for metric in metrics if metric.test_mae is not None]
    if with_mae:
        return min(with_mae, key=lambda metric: metric.test_mae or float("inf"))
    return None


def _read_active_model_stamp(model_dirs: Iterable[Path | str] | None = None) -> tuple[str | None, str]:
    dirs = [Path(p) for p in (model_dirs or _default_model_dirs())]
    for directory in dirs:
        pointer = directory / "ACTIVE_MODEL.json"
        if not pointer.exists():
            continue
        try:
            data = json.loads(pointer.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        stamp = data.get("stamp")
        if stamp:
            return str(stamp), "ACTIVE_MODEL.json"
        model_file = data.get("model_file")
        if model_file:
            match = re.search(r"model_(\d{8}_\d{6})\.pkl", str(model_file))
            if match:
                return match.group(1), "ACTIVE_MODEL.json"
    return None, "auto_latest"


def select_serving_metric(
    metrics: Iterable[ModelMetric],
    model_dirs: Iterable[Path | str] | None = None,
) -> ModelMetric | None:
    metrics = list(metrics)
    active_stamp, _source = _read_active_model_stamp(model_dirs)
    if active_stamp:
        active = next((metric for metric in metrics if metric.stamp == active_stamp), None)
        if active:
            return active
    return select_latest_metric(metrics)


def build_metric_provenance(model_dirs: Iterable[Path | str] | None = None) -> dict:
    metrics = load_model_metrics(model_dirs)
    latest = select_latest_metric(metrics)
    best = select_best_verified_metric(metrics)
    serving = select_serving_metric(metrics, model_dirs)
    _active_stamp, serving_source = _read_active_model_stamp(model_dirs)
    latest_is_best = bool(latest and best and latest.stamp == best.stamp)

    mape_gap = None
    mae_gap = None
    if latest and best:
        if latest.test_mape is not None and best.test_mape is not None:
            mape_gap = round(latest.test_mape - best.test_mape, 2)
        if latest.test_mae is not None and best.test_mae is not None:
            mae_gap = round(latest.test_mae - best.test_mae, 3)

    warning = None
    if latest and best and not latest_is_best:
        warning = (
            "latest retrain is not the best verified model; display both "
            "version/timestamp and metric source before comparing percentages"
        )

    serving_warning = None
    if serving and best and serving.stamp != best.stamp:
        serving_warning = (
            "serving model is pinned by ACTIVE_MODEL.json and is not the lowest-MAPE "
            "historical snapshot; compare MAE, R2, n_test, data policy and activation "
            "reason before changing production"
        )

    return {
        "latest": latest.to_public_dict() if latest else None,
        "serving": serving.to_public_dict() if serving else None,
        "serving_source": serving_source,
        "best_verified": best.to_public_dict() if best else None,
        "latest_is_best_verified": latest_is_best,
        "mape_gap_percentage_points": mape_gap,
        "mae_gap_vnd": mae_gap,
        "metric_policy": "best_verified_by_lowest_official_test_mape; serving_by_ACTIVE_MODEL_pointer",
        "warning": warning,
        "serving_warning": serving_warning,
    }


def serving_calibration_metric(
    model_dirs: Iterable[Path | str] | None = None,
) -> dict:
    """Return the only MAPE allowed for serving-time calibration displays."""
    provenance = build_metric_provenance(model_dirs)
    serving = provenance.get("serving") or {}
    return {
        "model_version": serving.get("stamp"),
        "metric_name": "official_test_mape",
        "mape_pct": serving.get("test_mape"),
        "source": provenance.get("serving_source"),
    }
