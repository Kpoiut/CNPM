"""
Backend shared dependencies — DI helpers thay thế global state.

Dùng Depends() trong route handlers thay vì global _cached_model.
Thread-safe, lazily-loaded, cached singleton.
"""

from __future__ import annotations

import pickle
import json
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

    Production policy: chỉ load artifact được pin bởi ACTIVE_MODEL.json.
    Không tự chọn latest candidate vì điều đó có thể phục vụ model retrain kém
    hơn production chỉ do timestamp mới hơn.

    Thread-safe: chỉ load 1 lần, reuse cho mọi request.
    """
    global _cached_model
    if _cached_model is not None:
        return _cached_model

    project_root = Path(__file__).parent.parent.parent

    model_dir = project_root / "models"
    _cached_model = _load_active_model(model_dir)
    return _cached_model


def _load_active_model(model_dir: Path) -> Dict[str, Any]:
    """Load đúng artifact được pin bởi ACTIVE_MODEL.json hoặc fail closed."""
    pointer = model_dir / "ACTIVE_MODEL.json"
    if not pointer.is_file():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ACTIVE_MODEL.json is required before serving predictions.",
        )

    try:
        active = json.loads(pointer.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ACTIVE_MODEL.json is invalid; refusing to serve an unpinned model.",
        ) from exc

    stamp = str(active.get("stamp") or "").strip()
    model_file = str(active.get("model_file") or "").strip()
    if not stamp or model_file != f"model_{stamp}.pkl":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ACTIVE_MODEL.json must point to the exact model_<stamp>.pkl artifact.",
        )

    active_path = (model_dir / model_file).resolve()
    model_root = model_dir.resolve()
    if active_path.parent != model_root:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ACTIVE_MODEL.json contains an unsafe artifact path.",
        )
    if not active_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ACTIVE_MODEL artifact is missing; refusing to select latest candidate.",
        )

    try:
        with active_path.open("rb") as f:
            data = pickle.load(f)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ACTIVE_MODEL artifact cannot be loaded; refusing to fallback to candidates.",
        ) from exc

    return _build_model_cache(data)


def _build_model_cache(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build standardized model cache dict from pipeline pickle."""
    metadata = data.get("metadata", {}) or {}
    version = data.get("version") or metadata.get("model_version")
    return {
        "model": data.get("model"),
        "model_version": version,
        "feature_cols": data.get("feature_names", []),
        "scaler": data.get("scaler"),
        "quantile_models": data.get("quantile_models", {}),
        "conformal_calibration": data.get("conformal_calibration", {}),
        "confidence_best_model": data.get("confidence_best_model"),
        "confidence_best_model_name": data.get("confidence_best_model_name"),
        "confidence_feature_names": data.get("confidence_feature_names", []),
        "confidence_metadata": data.get("confidence_metadata", {}),
        "metadata": metadata,
        "metrics": (
            metadata
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
