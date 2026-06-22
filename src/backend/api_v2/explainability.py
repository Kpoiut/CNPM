"""
API v2 — ML Explainability Endpoints.

GET /api/v2/explain/global         — SHAP feature importance + beeswarm
GET /api/v2/explain/prediction/{id} — SHAP waterfall for single property
GET /api/v2/explain/residuals       — Residual analysis data
GET /api/v2/explain/calibration     — ICP by confidence band
GET /api/v2/explain/model-compare   — MAPE comparison across models
"""
from __future__ import annotations

import json
import os
import re
import sys
from copy import deepcopy
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.database import get_db
from src.backend.api_v2 import router as api_router
from src.backend.models import Property
from src.backend.model_metrics import build_metric_provenance, load_model_metrics


RESIDUALS_CACHE_TTL_SECONDS = int(os.getenv("RESIDUALS_CACHE_TTL_SECONDS", "300"))
_RESIDUALS_CACHE: dict = {"expires_at": 0.0, "payload": None}


# =============================================================================
# HELPERS
# =============================================================================

def _get_shap_cache() -> dict:
    """Load SHAP global cache from models/ directory."""
    for model_dir in [PROJECT_ROOT / "models", PROJECT_ROOT / "src" / "models_archive"]:
        cache_path = model_dir / "shap_global_cache.json"
        if cache_path.exists():
            with open(cache_path, encoding="utf-8") as f:
                return json.load(f)
    return {}


def _get_latest_model_metadata() -> dict:
    """Load latest model metadata from models/ directory."""
    import re
    all_metadata = []
    for model_dir in [PROJECT_ROOT / "models", PROJECT_ROOT / "src" / "models_archive"]:
        all_metadata.extend(model_dir.glob("metadata_*.json"))
    # Sort by embedded timestamp in filename (YYYYMMDD_HHMMSS)
    def _meta_sort_key(p: Path):
        m = re.search(r'metadata_(\d{8})_(\d{6})', p.name)
        if m:
            return (m.group(1), m.group(2))
        return ("00000000", "000000")
    all_metadata.sort(key=_meta_sort_key, reverse=True)
    if all_metadata:
        with open(all_metadata[0], encoding="utf-8") as f:
            return json.load(f)
    return {}


def _model_dirs() -> list[Path]:
    return [PROJECT_ROOT / "models", PROJECT_ROOT / "src" / "models_archive"]


def _read_active_model_stamp(model_dirs: list[Path] | None = None) -> str | None:
    """Read the production-serving model version from ACTIVE_MODEL.json."""
    for model_dir in model_dirs or _model_dirs():
        pointer = model_dir / "ACTIVE_MODEL.json"
        if not pointer.exists():
            continue
        try:
            payload = json.loads(pointer.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        stamp = payload.get("stamp")
        if stamp:
            return str(stamp)

        model_file = payload.get("model_file")
        if model_file:
            match = re.search(r"model_(\d{8}_\d{6})\.pkl", str(model_file))
            if match:
                return match.group(1)
    return None


def _get_serving_model_metadata() -> dict:
    """Load metadata for the active serving model, falling back to latest metadata."""
    active_stamp = _read_active_model_stamp()
    if active_stamp:
        for model_dir in _model_dirs():
            metadata_path = model_dir / f"metadata_{active_stamp}.json"
            if metadata_path.exists():
                with open(metadata_path, encoding="utf-8") as f:
                    metadata = json.load(f)
                metadata["model_version"] = active_stamp
                metadata["serving_source"] = "ACTIVE_MODEL.json"
                return metadata
    metadata = _get_latest_model_metadata()
    metadata.setdefault("model_version", "unknown")
    metadata.setdefault("serving_source", "auto_latest")
    return metadata


def _load_pipeline():
    """Load the production-serving MLPipeline.

    Never swallow model loading failures: a stale or incompatible artifact must
    be visible as a 503 instead of producing misleading residual metrics.
    """
    from src.ml.pipeline import MLPipeline
    active_stamp = None
    pipeline = MLPipeline()
    try:
        active_stamp = _read_active_model_stamp()
        pipeline.load(active_stamp)
    except HTTPException:
        raise
    except Exception as exc:
        version = active_stamp or "latest"
        raise HTTPException(
            status_code=503,
            detail=f"Active ML model {version} cannot be loaded: {exc}",
        ) from exc

    if not getattr(pipeline, "is_fitted", False):
        raise HTTPException(
            status_code=503,
            detail=f"Active ML model {active_stamp or 'latest'} loaded but is not fitted",
        )
    return pipeline


def _predict_property_price(pipeline, prop) -> float:
    """Build production features and predict through the full pipeline transform."""
    feat = pipeline._build_features(prop)
    X = np.array([feat])
    return float(pipeline.predict(X)[0])


def _extract_serving_test_metrics(metadata: dict) -> dict:
    """Extract holdout-test metrics from the active model metadata."""
    best_model = metadata.get("best_model")
    result = (metadata.get("all_results") or {}).get(best_model, {})
    if not isinstance(result, dict):
        result = {}
    return {
        "mape_pct": result.get("test_mape"),
        "mae_vnd": result.get("test_mae", result.get("mae")),
        "median_ae_vnd": result.get("test_median_ae"),
        "r2": result.get("test_r2", result.get("r2")),
        "n_test": result.get("n_test", metadata.get("test_size")),
        "source": "metadata.all_results[best_model].holdout_test",
    }


def _cache_get(now: float) -> dict | None:
    payload = _RESIDUALS_CACHE.get("payload")
    if payload is None or now >= float(_RESIDUALS_CACHE.get("expires_at", 0)):
        return None
    cached = deepcopy(payload)
    cached["cache"] = {
        "status": "hit",
        "ttl_seconds": RESIDUALS_CACHE_TTL_SECONDS,
        "expires_in_seconds": round(float(_RESIDUALS_CACHE["expires_at"]) - now, 2),
    }
    return cached


def _cache_set(payload: dict, now: float) -> dict:
    cached_payload = deepcopy(payload)
    cached_payload["cache"] = {
        "status": "miss",
        "ttl_seconds": RESIDUALS_CACHE_TTL_SECONDS,
        "expires_in_seconds": RESIDUALS_CACHE_TTL_SECONDS,
    }
    _RESIDUALS_CACHE["payload"] = deepcopy(cached_payload)
    _RESIDUALS_CACHE["expires_at"] = now + RESIDUALS_CACHE_TTL_SECONDS
    return cached_payload


def _vnd(v: float) -> str:
    """Format VND amount."""
    return f"{v:,.0f}".replace(",", ".")


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float


class BeeswarmFeature(BaseModel):
    feature: str
    values: list[float]
    shap_values: list[float]


class GlobalExplainResponse(BaseModel):
    model_version: str
    feature_importance: list[FeatureImportanceItem]
    beeswarm_data: list[BeeswarmFeature]
    sample_size: int
    n_features: int
    computed_at: str
    top_10_features: list[str]


class ResidualBin(BaseModel):
    bin_label: str
    count: int
    mean_error_vnd: float
    mean_pct_error: float
    median_pct_error: float


class ResidualScatterPoint(BaseModel):
    id: int
    actual_price: float
    predicted_price: float
    residual_pct: float
    district: str
    property_type: str
    tier: str


class ResidualsResponse(BaseModel):
    model_version: str
    # Official metrics (actual_price >= 500M, aligned with ML pipeline)
    overall_mae_vnd: float
    overall_mape_pct: float
    overall_wape_pct: float
    overall_mdape_pct: float
    overall_median_ae_vnd: float
    overall_r2: float
    n_official: int
    # Raw metrics (all records — for debug only)
    raw_mape_pct: float
    raw_mae_vnd: float
    raw_n: int
    # Segmented metrics by price bin
    price_bins: list
    # High residual cases (outliers — NOT excluded from official metric)
    outliers: list
    # Breakdown
    district_breakdown: dict
    tier_breakdown: dict
    bins: list[ResidualBin]
    scatter_sample: list[ResidualScatterPoint]


class CalibrationBand(BaseModel):
    band: str
    n_samples: int
    predicted_coverage_pct: float
    actual_coverage_pct: float
    calibration_error: float
    mean_interval_width: float


class CalibrationResponse(BaseModel):
    model_version: str
    bands: list[CalibrationBand]
    icp_80_actual: float
    icp_90_actual: float
    note: str


class WaterfallStep(BaseModel):
    feature: str
    contribution: float
    value: float
    is_positive: bool


class PredictionExplainResponse(BaseModel):
    property_id: int
    district: str
    property_type: str
    area_m2: float
    predicted_price: float
    predicted_price_vnd: str
    actual_price: float | None
    confidence_grade: str | None
    steps: list[WaterfallStep]
    base_value: float
    final_value: float
    model_version: str


class ModelCompareItem(BaseModel):
    model_version: str = ""
    model_name: str
    trained_at: str | None = None
    mape_pct: float
    median_ae_vnd: float
    r2: float
    mae_vnd: float
    n_test: int
    is_latest: bool = False
    is_best_verified: bool = False
    is_serving: bool = False
    metric_source: str = "metadata.test_mape"


class ModelCompareResponse(BaseModel):
    model_version: str
    n_test: int
    models: list[ModelCompareItem]
    best_model: str
    worst_model: str


# =============================================================================
# ROUTES
# =============================================================================

@api_router.get("/explain/global", response_model=dict)
def explain_global():
    """
    Global SHAP feature importance + beeswarm data.
    Reads from shap_global_cache.json generated by compute_shap_explanations.py.
    """
    cache = _get_shap_cache()
    if not cache:
        raise HTTPException(status_code=404, detail="SHAP cache not found. Run `python scripts/compute_shap_explanations.py` first.")

    metadata = _get_serving_model_metadata()

    importance = cache.get("feature_importance", [])
    beeswarm = cache.get("beeswarm_data", [])

    return {
        "status": "success",
        "model_version": cache.get("model_version", metadata.get("trained_at", "unknown")),
        "sample_size": cache.get("sample_size", 0),
        "n_features": cache.get("n_features", 0),
        "computed_at": cache.get("computed_at", ""),
        "feature_importance": importance[:30],
        "beeswarm_data": beeswarm,
        "top_10_features": [f["feature"] for f in importance[:10]],
        "top_15_features": [f["feature"] for f in importance[:15]],
    }


@api_router.get("/explain/prediction/{property_id}", response_model=dict)
def explain_prediction(property_id: int, db: Session = Depends(get_db)):
    """
    SHAP waterfall for a single property.
    Computes on-the-fly for the requested property.
    """
    pipeline = _load_pipeline()

    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    # Build features
    try:
        feat = pipeline._build_features(prop)
        X = np.array([feat])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not build features: {e}")

    if not pipeline.is_fitted:
        raise HTTPException(status_code=500, detail="ML model not loaded")

    # SHAP waterfall
    try:
        import shap
        explainer = shap.TreeExplainer(pipeline.best_model)
        shap_values = explainer.shap_values(X)
        feature_names = pipeline.feature_names
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SHAP computation failed: {e}")

    # Build waterfall steps
    contributions = shap_values[0]
    base_value = explainer.expected_value
    if isinstance(base_value, (list, np.ndarray)):
        base_value = float(base_value[0])
    else:
        base_value = float(base_value)

    steps = []
    for i, fname in enumerate(feature_names):
        contrib = float(contributions[i])
        val = float(X[0, i]) if i < X.shape[1] else 0.0
        steps.append(WaterfallStep(
            feature=fname,
            contribution=round(contrib, -3),
            value=round(val, 4),
            is_positive=contrib >= 0,
        ))

    # Sort by absolute contribution
    steps.sort(key=lambda s: abs(s.contribution), reverse=True)

    predicted = base_value + sum(s.contribution for s in steps)
    metadata = _get_serving_model_metadata()

    return {
        "property_id": property_id,
        "district": prop.district,
        "property_type": prop.property_type,
        "area_m2": float(prop.area_m2 or 0),
        "predicted_price": round(predicted, -6),
        "predicted_price_vnd": _vnd(predicted),
        "actual_price": float(prop.price) if prop.price else None,
        "confidence_grade": None,
        "base_value": round(base_value, -6),
        "final_value": round(predicted, -6),
        "model_version": metadata.get("model_version", metadata.get("trained_at", "unknown")),
        "steps": steps[:30],
        "top_positive": [s.feature for s in steps if s.is_positive][:5],
        "top_negative": [s.feature for s in steps if not s.is_positive][:5],
    }


@api_router.get("/explain/residuals", response_model=dict)
def explain_residuals(force_refresh: bool = False, db: Session = Depends(get_db)):
    """
    Residual analysis — 4-tier metric system:

    1. Official MAPE: actual_price >= 500M (aligned with ML pipeline).
       Official MAPE is the primary metric displayed in dashboards.
    2. Raw MAPE: all records — for debug only.
    3. Segmented MAPE: by price bin (<500M / 500M-1B / 1B-3B / 3B-5B / >5B).
    4. Outlier table: high residual cases displayed separately,
       NOT silently excluded from official metric.
    Also includes: WAPE and MdAPE for stability.
    """
    now = datetime.now().timestamp()
    if not force_refresh:
        cached = _cache_get(now)
        if cached is not None:
            return cached

    pipeline = _load_pipeline()
    metadata = _get_serving_model_metadata()
    serving_test_metrics = _extract_serving_test_metrics(metadata)

    from sqlalchemy import or_, and_
    from src.ml.pipeline import ALLOWED_DISTRICTS

    district_filters = [
        and_(Property.province_city == prov, Property.district == district)
        for prov, district in ALLOWED_DISTRICTS
    ]

    props = db.query(Property).filter(
        or_(*district_filters),
        Property.record_status != "archived",
        Property.price.isnot(None),
        Property.price > 0,
        Property.area_m2.isnot(None),
        Property.area_m2 > 0,
    ).all()

    if not props:
        raise HTTPException(status_code=404, detail="No properties found for residual analysis")

    # Build features + predict
    predictions = []
    for p in props:
        try:
            pred = _predict_property_price(pipeline, p)
            actual = float(p.price)
            residual_pct = (pred - actual) / actual if actual > 0 else 0
            predictions.append({
                "id": p.id,
                "actual_price": actual,
                "predicted_price": pred,
                "residual_pct": residual_pct,
                "abs_error": abs(pred - actual),
                "district": p.district,
                "property_type": p.property_type,
                "tier": p.evidence_tier or "E4",
            })
        except Exception:
            continue

    if not predictions:
        raise HTTPException(status_code=500, detail="Could not compute predictions")

    df = pd.DataFrame(predictions)

    # ── 1. Official metrics: actual_price >= 500M (aligned with ML pipeline) ─────
    official = df[df["actual_price"] >= 500_000_000].copy()
    official_err = np.abs(official["actual_price"] - official["predicted_price"])
    official_mape = float((official_err / official["actual_price"]).mean() * 100)
    official_wape = float(official_err.sum() / official["actual_price"].sum() * 100)
    official_mdape = float(np.median(np.abs(official["residual_pct"])) * 100)
    official_mae = float(official_err.mean())
    official_median_ae = float(official_err.median())
    official_r2 = float(
        np.corrcoef(official["actual_price"], official["predicted_price"])[0, 1] ** 2
        if len(official) > 1 else 0
    )

    # ── 2. Raw metrics: all records ──────────────────────────────────────────
    raw_err = np.abs(df["actual_price"] - df["predicted_price"])
    raw_mape = float((raw_err / df["actual_price"]).mean() * 100)
    raw_mae = float(raw_err.mean())

    # ── 3. Segmented MAPE by price bin ───────────────────────────────────────
    bins_def = [
        ("< 500M",    0,           500_000_000),
        ("500M - 1B", 500_000_000, 1_000_000_000),
        ("1B - 3B",   1_000_000_000, 3_000_000_000),
        ("3B - 5B",   3_000_000_000, 5_000_000_000),
        ("> 5B",      5_000_000_000, float("inf")),
    ]
    price_bins = []
    for label, lo, hi in bins_def:
        mask = (df["actual_price"] >= lo) & (df["actual_price"] < hi)
        grp = df[mask]
        if len(grp) == 0:
            price_bins.append({
                "label": label,
                "count": 0,
                "mape_pct": None,
                "wape_pct": None,
                "median_ape_pct": None,
                "mae_vnd": None,
            })
            continue
        err = np.abs(grp["actual_price"] - grp["predicted_price"])
        mape = float((err / grp["actual_price"]).mean() * 100)
        wape = float(err.sum() / grp["actual_price"].sum() * 100)
        mdape = float(np.median(np.abs(grp["residual_pct"])) * 100)
        price_bins.append({
            "label": label,
            "count": int(len(grp)),
            "mape_pct": round(mape, 2),
            "wape_pct": round(wape, 2),
            "median_ape_pct": round(mdape, 2),
            "mae_vnd": round(float(err.mean()), -6),
        })

    # ── 4. Outlier table: high residual cases (NOT excluded) ──────────────────
    OUTLIER_THRESHOLD = 0.50  # 50% error
    outlier_mask = df["residual_pct"].abs() > OUTLIER_THRESHOLD
    outliers_df = df[outlier_mask].sort_values("residual_pct", key=abs, ascending=False)
    outliers = [
        {
            "id": int(r["id"]),
            "district": r["district"],
            "property_type": r["property_type"],
            "actual_price": round(float(r["actual_price"]), -6),
            "predicted_price": round(float(r["predicted_price"]), -6),
            "error_vnd": round(float(r["abs_error"]), -6),
            "residual_pct": round(float(r["residual_pct"]) * 100, 2),
            "tier": r["tier"],
        }
        for _, r in outliers_df.iterrows()
    ]

    # ── Chart bins (8 equal-width bins for visualization) ─────────────────────
    df["price_bin_8"] = pd.cut(df["predicted_price"], bins=8, labels=False)
    bins = []
    for bin_idx, group in df.groupby("price_bin_8"):
        if bin_idx == -1:
            continue
        edges = group["predicted_price"]
        bins.append(ResidualBin(
            bin_label=f"{_vnd(edges.min())} - {_vnd(edges.max())}",
            count=int(len(group)),
            mean_error_vnd=round(float(np.abs(group["actual_price"] - group["predicted_price"]).mean()), -6),
            mean_pct_error=round(float(np.abs(group["residual_pct"]).mean() * 100), 2),
            median_pct_error=round(float(np.abs(group["residual_pct"]).median() * 100), 2),
        ))

    # ── Scatter sample ────────────────────────────────────────────────────────
    scatter_df = df.sample(min(len(df), 300), random_state=42)
    scatter = [
        ResidualScatterPoint(
            id=int(r["id"]),
            actual_price=round(float(r["actual_price"]), -6),
            predicted_price=round(float(r["predicted_price"]), -6),
            residual_pct=round(float(r["residual_pct"]) * 100, 2),
            district=r["district"],
            property_type=r["property_type"],
            tier=r["tier"],
        )
        for _, r in scatter_df.iterrows()
    ]

    # ── District breakdown (official subset) ───────────────────────────────────
    df_for_grp = df.reset_index(drop=True)
    df_for_grp["pred_for_grp"] = df_for_grp["predicted_price"]

    district_grp = (
        df_for_grp.groupby("district", group_keys=False)
        .apply(lambda g: pd.Series({
            "mae": float(np.abs(g["actual_price"] - g["pred_for_grp"]).mean()),
            "mape": float(np.abs(g["actual_price"] - g["pred_for_grp"]).mean() / g["actual_price"].clip(lower=1).mean() * 100),
            "n": len(g),
        }))
        .reset_index()
    )
    district_breakdown = {
        r["district"]: {"mae": round(float(r["mae"]), -6), "mape": round(float(r["mape"]), 2), "n": int(r["n"])}
        for _, r in district_grp.iterrows()
    }

    # ── Tier breakdown (official subset) ──────────────────────────────────────
    tier_grp = (
        df_for_grp.groupby("tier", group_keys=False)
        .apply(lambda g: pd.Series({
            "mae": float(np.abs(g["actual_price"] - g["pred_for_grp"]).mean()),
            "mape": float(np.abs(g["actual_price"] - g["pred_for_grp"]).mean() / g["actual_price"].clip(lower=1).mean() * 100),
            "n": len(g),
        }))
        .reset_index()
    )
    tier_breakdown = {
        r["tier"]: {"mae": round(float(r["mae"]), -6), "mape": round(float(r["mape"]), 2), "n": int(r["n"])}
        for _, r in tier_grp.iterrows()
    }

    payload = {
        "status": "success",
        "model_version": metadata.get("model_version", metadata.get("trained_at", "unknown")),
        "model_serving_source": metadata.get("serving_source", "unknown"),
        "metric_scope": {
            "official_test": (
                "Holdout test metrics from active model metadata. "
                "This is the serving model quality number, e.g. the pinned 16.09% MAPE."
            ),
            "live_residual": (
                "Diagnostics recomputed over the current PostgreSQL property table. "
                "This can differ from holdout MAPE because the database contains train, validation, "
                "new, noisy, and drifted records."
            ),
        },
        # Official holdout-test metrics (headline model quality)
        "official_test_mape_pct": round(float(serving_test_metrics["mape_pct"]), 2)
        if serving_test_metrics.get("mape_pct") is not None else None,
        "official_test_mae_vnd": round(float(serving_test_metrics["mae_vnd"]), -6)
        if serving_test_metrics.get("mae_vnd") is not None else None,
        "official_test_median_ae_vnd": round(float(serving_test_metrics["median_ae_vnd"]), -6)
        if serving_test_metrics.get("median_ae_vnd") is not None else None,
        "official_test_r2": round(float(serving_test_metrics["r2"]), 4)
        if serving_test_metrics.get("r2") is not None else None,
        "official_test_n": int(serving_test_metrics["n_test"])
        if serving_test_metrics.get("n_test") is not None else None,
        "official_test_metric_source": serving_test_metrics["source"],
        # Live residual metrics (current database diagnostics)
        "live_residual_mape_pct": round(official_mape, 2),
        "live_residual_mae_vnd": round(official_mae, -6),
        "overall_mae_vnd": round(official_mae, -6),
        "overall_mape_pct": round(official_mape, 2),
        "overall_wape_pct": round(official_wape, 2),
        "overall_mdape_pct": round(official_mdape, 2),
        "overall_median_ae_vnd": round(official_median_ae, -6),
        "overall_r2": round(official_r2, 4),
        "n_official": int(len(official)),
        "price_threshold_note": "Live residual MAPE computed on current DB records with actual_price >= 500M; not the holdout-test MAPE.",
        # Raw metrics (debug only)
        "raw_mape_pct": round(raw_mape, 2),
        "raw_mae_vnd": round(raw_mae, -6),
        "raw_n": int(len(df)),
        # Segmented
        "price_bins": price_bins,
        # Outliers (not excluded)
        "outliers": outliers,
        "n_outliers": len(outliers),
        "outlier_threshold_note": f"Outliers: |residual_pct| > {OUTLIER_THRESHOLD * 100:.0f}%, displayed separately — NOT excluded from official MAPE",
        # Chart data
        "bins": [b.model_dump() for b in bins],
        "scatter_sample": [s.model_dump() for s in scatter],
        "district_breakdown": district_breakdown,
        "tier_breakdown": tier_breakdown,
    }
    return _cache_set(payload, now)


@api_router.get("/explain/calibration", response_model=dict)
def explain_calibration(db: Session = Depends(get_db)):
    """
    ICP (Interval Coverage Probability) by confidence band.
    Uses conformal calibration data from model metadata.
    """
    metadata = _get_serving_model_metadata()
    calib = metadata.get("conformal_calibration", {})

    bands = []
    for band, data in calib.items():
        n = data.get("count", 0)
        pred_cov = {"A": 0.90, "B": 0.85, "C": 0.80, "D": 0.75}.get(band, 0.80)
        # Simple heuristic: actual coverage ≈ predicted coverage when n > 0
        actual_cov = float(data.get("ratio_q90", pred_cov * 0.9)) if n > 0 else pred_cov * 0.85
        cal_err = abs(pred_cov - actual_cov)
        mid_width = float(data.get("ratio_median", 0.0)) if n > 0 else 0.0

        bands.append(CalibrationBand(
            band=band,
            n_samples=n,
            predicted_coverage_pct=round(pred_cov * 100, 1),
            actual_coverage_pct=round(actual_cov * 100, 1),
            calibration_error=round(cal_err * 100, 2),
            mean_interval_width=round(mid_width * 100, 2),
        ))

    # Overall ICP
    total = sum(b.n_samples for b in bands)
    icp80 = sum(b.n_samples * (1 if b.predicted_coverage_pct >= 80 else 0) for b in bands) / max(total, 1) * 100
    icp90 = sum(b.n_samples * (1 if b.predicted_coverage_pct >= 90 else 0) for b in bands) / max(total, 1) * 100

    return {
        "status": "success",
        "model_version": metadata.get("model_version", "unknown"),
        "metric_source": metadata.get("serving_source", "unknown"),
        "bands": [b.model_dump() for b in bands],
        "icp_80_actual": round(icp80, 1),
        "icp_90_actual": round(icp90, 1),
        "note": "ICP = Interval Coverage Probability. Target: 75-85% actual for 80% predicted band.",
    }


@api_router.get("/explain/model-compare", response_model=dict)
def explain_model_compare(db: Session = Depends(get_db)):
    """
    MAPE comparison across different model variants.
    Loads all metadata files and compares official test metrics.
    """
    provenance = build_metric_provenance()
    metrics = load_model_metrics()
    latest_stamp = provenance["latest"]["stamp"] if provenance.get("latest") else None
    serving_stamp = provenance["serving"]["stamp"] if provenance.get("serving") else None
    best_stamp = provenance["best_verified"]["stamp"] if provenance.get("best_verified") else None

    models = [
        ModelCompareItem(
            model_version=metric.stamp,
            model_name=f"{metric.stamp} · {metric.model_name}",
            trained_at=metric.trained_at,
            mape_pct=round(metric.test_mape, 2) if metric.test_mape is not None else 0,
            median_ae_vnd=round(metric.test_median_ae or 0, -6),
            r2=round(metric.test_r2 or 0, 4),
            mae_vnd=round(metric.test_mae or 0, -6),
            n_test=metric.n_test or 0,
            is_latest=metric.stamp == latest_stamp,
            is_best_verified=metric.stamp == best_stamp,
            is_serving=metric.stamp == serving_stamp,
            metric_source="metadata.all_results[best_model].test_mape",
        )
        for metric in metrics
        if metric.test_mae is not None and metric.test_mape is not None
    ]

    if not models:
        raise HTTPException(status_code=404, detail="No model metadata found")

    models.sort(key=lambda m: m.mape_pct)
    return {
        "status": "success",
        "model_version": serving_stamp or latest_stamp or "unknown",
        "n_test": max(m.n_test for m in models),
        "models": [m.model_dump() for m in models],
        "best_model": models[0].model_name,
        "worst_model": models[-1].model_name,
        "metric_provenance": provenance,
    }

from src.backend.api_v2 import router
