"""
Backend shared dependencies — DI helpers thay thế global state.

Dùng Depends() trong route handlers thay vì global _cached_model.
Thread-safe, lazily-loaded, cached singleton.
"""

from __future__ import annotations

import pickle
import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Generator, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.backend.database import SessionLocal


# ==============================================================================
# Database Session — thay thế get_db() inline trong main.py
# ==============================================================================

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield DB session per request, auto-close."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==============================================================================
# Cached ML Model — thay thế global _cached_model trong main.py
# ==============================================================================

_cached_model: Optional[Dict[str, Any]] = None


def get_cached_model() -> Dict[str, Any]:
    """
    Load và cache ML model pipeline.

    Priority:
    1. Latest model_*.pkl trong src/models/
    2. src/models/model_pipeline.pkl
    3. Legacy models/randomforest_model.pkl
    4. Raise HTTPException 503

    Thread-safe: chỉ load 1 lần, reuse cho mọi request.
    """
    global _cached_model
    if _cached_model is not None:
        return _cached_model

    project_root = Path(__file__).parent.parent.parent

    # 1. New pipeline models (model_YYYYMMDD_HHMMSS.pkl)
    # models/ is at the project root (same level as src/), not under src/
    model_dir = project_root / "models"
    if model_dir.exists():
        pkl_files = sorted(model_dir.glob("model_*.pkl"), key=lambda f: f.stat().st_mtime, reverse=True)
        for pkl_path in pkl_files:
            try:
                with open(pkl_path, "rb") as f:
                    data = pickle.load(f)
                _cached_model = _build_model_cache(data)
                return _cached_model
            except Exception:
                continue

    # 2. Pipeline bundle
    pipeline_path = model_dir / "model_pipeline.pkl"
    if pipeline_path.exists():
        try:
            with open(pipeline_path, "rb") as f:
                data = pickle.load(f)
            _cached_model = _build_model_cache(data)
            return _cached_model
        except Exception:
            pass

    # 3. Legacy
    legacy_path = project_root / "models" / "randomforest_model.pkl"
    if legacy_path.exists():
        try:
            with open(legacy_path, "rb") as f:
                data = {"model": pickle.load(f), "metadata": {}, "pipeline": None}
            _cached_model = data
            return _cached_model
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="ML model not found. Run: python scripts/retrain_v2.py",
    )


def _build_model_cache(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build standardized model cache dict from pipeline pickle."""
    return {
        "model": data.get("model"),
        "feature_cols": data.get("feature_names", []),
        "scaler": data.get("scaler"),
        "quantile_models": data.get("quantile_models", {}),
        "conformal_calibration": data.get("conformal_calibration", {}),
        "confidence_best_model": data.get("confidence_best_model"),
        "confidence_best_model_name": data.get("confidence_best_model_name"),
        "confidence_feature_names": data.get("confidence_feature_names", []),
        "confidence_metadata": data.get("confidence_metadata", {}),
        "metadata": data.get("metadata", {}),
        "metrics": (
            data.get("metadata", {})
            .get("all_results", {})
            .get(data.get("best_model_name", "GradientBoosting"), {})
        ),
        "pipeline": data,
    }


def clear_model_cache() -> None:
    """Clear cached model (useful for hot-reload in dev)."""
    global _cached_model
    _cached_model = None


# ==============================================================================
# Research Lab Auth — token-based access
# ==============================================================================

_research_tokens: set = set()
_research_lab_access_code: str = os.getenv("RESEARCH_LAB_ACCESS_CODE", "CVX-BDS-RESEARCH-2026")


def verify_research_token(token: str) -> bool:
    """Verify research lab token."""
    return token in _research_tokens


def generate_research_token() -> str:
    """Generate and store a new research lab token."""
    token = secrets.token_urlsafe(32)
    _research_tokens.add(token)
    return token


def verify_access_code(code: str) -> tuple[bool, str]:
    """
    Verify research lab access code.
    Returns: (granted, message)
    """
    if code == _research_lab_access_code:
        return True, "Access granted"
    return False, "Invalid access code"
