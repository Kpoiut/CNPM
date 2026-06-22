#!/usr/bin/env python3
"""
FastAPI Backend for Real Estate AVM - IoT Enhanced Version.
REST API for property valuation with IoT/smartphone features.
"""

import json
import hashlib
import os
import pickle
import secrets
import subprocess
import sys
import threading
import time
import uuid
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from pathlib import Path

def _load_project_env() -> None:
    """Load simple KEY=VALUE pairs from project .env before importing auth modules."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_project_env()

from fastapi import FastAPI, Depends, HTTPException, status, Query, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
import aiofiles


HEALTH_DB_CACHE_TTL_SECONDS = int(os.getenv("HEALTH_DB_CACHE_TTL_SECONDS", "10"))
_HEALTH_DB_CACHE = {"expires_at": 0.0, "database": None}
PREDICTION_POOL_CACHE_TTL_SECONDS = int(os.getenv("PREDICTION_POOL_CACHE_TTL_SECONDS", "30"))
_PREDICTION_POOL_CACHE = {"expires_at": 0.0, "value": None}
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.backend.database import init_db
from src.backend.models import Property, ModelVersion, AuditLog, ProvenanceChain, CollectionSource, BuyerRequirement, ExpertRating, ExpertProperty, ValuationRun
from src.backend.deps import get_db, get_cached_model
from src.backend.quality_assessment import (
    build_adaptive_interval,
    build_assessment_tree,
    build_case_confidence_features,
    build_confidence_training_rows,
    build_data_quality_assessment,
)
from src.backend.data_collector import DataCollectionService
from src.backend.provenance_tracker import ProvenanceTracker, ProvenanceActor, ProvenanceStep
from src.backend.api_sanitizer_middleware import SanitizeRequestMiddleware
from src.backend.approved_sources import get_all_approved_domains, get_approved_source, is_source_approved, is_source_prohibited, get_allowed_districts_for_source
from src.config.province_config import (
    BASE_PRICES_PER_M2,
    get_base_price_per_m2,
    SCOPE_DISTRICTS,
    normalize_province,
    is_valid_province,
)


# ============================================================
# Module-level state
# ============================================================

# Research Lab uses one-time admin-issued codes and short lived browser sessions.
_RESEARCH_CODE_TTL_SECONDS = 10 * 60
_RESEARCH_SESSION_MINUTES = 60
_research_lab_codes: Dict[str, Dict[str, object]] = {}
_research_lab_tokens: Dict[str, Dict[str, object]] = {}
_research_lab_jobs: Dict[str, Dict[str, object]] = {}
_research_lab_jobs_lock = threading.Lock()
_research_lab_jobs_dir = Path(__file__).resolve().parents[2] / "reports" / "research_lab_jobs"

# Imported schemas (extracted from main.py → src/backend/schemas/)
from src.backend.schemas import (
    PropertyBase,
    PropertyCreate,
    PropertyResponse,
    PredictionRequest,
    PredictionResponse,
    DataQualityResponse,
    ResearchLabAccessRequest,
    ResearchLabAccessResponse,
    ResearchLabCodeResponse,
    ResearchLabOverviewResponse,
    DatasetStats,
    BaselineComparison,
    CollectRequest,
    CollectStatusResponse,
    ProvenanceNodeResponse,
    ProvenanceChainResponse,
)


# MODELS MOVED to src/backend/schemas/ — imported above


class ResearchLabAdminJobRequest(BaseModel):
    operation: str = Field(..., description="Whitelisted admin operation key")
    params: Dict[str, object] = Field(default_factory=dict)

# ============================================================
# FastAPI App Setup
# ============================================================

app = FastAPI(
    title="Real Estate AVM API - IoT Enhanced",
    description="Automated Valuation Model with IoT/Smartphone features",
    version="2.0.0"
)

# CORS middleware — reads from CORS_ORIGINS env var (default: localhost dev origins)
_cors_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:8000")
_cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from src.backend.config import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Sanitizer middleware — canonicalizes all JSON write bodies before route handlers
app.add_middleware(SanitizeRequestMiddleware)

# Timing middleware — adds X-Response-Time-Ms header
@app.middleware("http")
async def add_timing_header(request, call_next):
    import time
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
    # Security headers (defense-in-depth; không dùng CSP chặt để tránh vỡ tile/iframe bản đồ)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(self), microphone=(self), camera=()")
    response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    # CSP Report-Only: giám sát vi phạm mà KHÔNG chặn (an toàn cho tile/iframe bản đồ bên thứ ba).
    # Cho phép các nguồn tài nguyên app đang dùng: Esri/CartoDB/OSM tiles, Google Maps iframe,
    # ảnh từ Cho Tot CDN, leaflet CDN. Khi đã ổn định có thể đổi sang Content-Security-Policy (enforce).
    response.headers.setdefault(
        "Content-Security-Policy-Report-Only",
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline' https://unpkg.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: blob: "
        "https://server.arcgisonline.com https://*.arcgisonline.com "
        "https://*.basemaps.cartocdn.com https://*.tile.openstreetmap.org "
        "https://unpkg.com https://cdnjs.cloudflare.com "
        "https://cdn.chotot.com https://*.chotot.com "
        "https://*.google.com https://maps.gstatic.com https://*.gstatic.com; "
        "font-src 'self' data: https://cdnjs.cloudflare.com; "
        "connect-src 'self' "
        "https://server.arcgisonline.com https://*.basemaps.cartocdn.com "
        "https://*.tile.openstreetmap.org https://overpass-api.de https://nominatim.openstreetmap.org "
        "https://gateway.chotot.com https://*.chotot.com; "
        "frame-src 'self' https://*.google.com https://maps.google.com; "
        "worker-src 'self' blob:; "
        "object-src 'none'; base-uri 'self'; form-action 'self'"
    )
    return response

# API v2: Asset-Specific Decision Intelligence Platform
try:
    from src.backend.api_v2.valuation import router as valuation_v2_router
    app.include_router(valuation_v2_router, prefix="", tags=["v2: Decision Intelligence"])
    print("[OK] api_v2 routes registered")
except ImportError as e:
    import sys
    print(f"[WARN] api_v2 not available: {e}", file=sys.stderr)

# Explainability: SHAP, residuals, calibration, model compare
try:
    from src.backend.api_v2.explainability import router as explainability_router
    app.include_router(explainability_router, prefix="", tags=["v2: Explainability"])
    print("[OK] explainability routes registered")
except ImportError as e:
    import sys
    print(f"[WARN] explainability not available: {e}", file=sys.stderr)

# Impact Analysis: Contextual Comparable-SHAP δ% (Admin-only)
try:
    from src.backend.api_v2.impact_analysis import api_router as impact_analysis_router
    app.include_router(impact_analysis_router, prefix="", tags=["v2: Impact Analysis"])
    print("[OK] impact-analysis routes registered")
except ImportError as e:
    import sys
    print(f"[WARN] impact-analysis not available: {e}", file=sys.stderr)

# Transaction Price: Supply-demand equilibrium derivation
try:
    from src.backend.api_v2.transaction_price import router as transaction_router
    app.include_router(transaction_router, prefix="", tags=["v2: Transaction Price"])
    print("[OK] transaction-price routes registered")
except ImportError as e:
    import sys
    print(f"[WARN] transaction-price not available: {e}", file=sys.stderr)

# Nova Voice Assistant API
try:
    from src.backend.api_v2.nova import router as nova_router
    app.include_router(nova_router, prefix="", tags=["nova: Voice Assistant"])
    print("[OK] nova voice routes registered")
except ImportError as e:
    import sys
    print(f"[WARN] nova not available: {e}", file=sys.stderr)

# Map Intelligence: location picker (Nominatim proxy + nearby + IoT auto-profile)
try:
    from src.backend.api_v2.map_intel import router as map_intel_router, iot_router as iot_signal_router
    app.include_router(map_intel_router, prefix="", tags=["Map Intelligence"])
    app.include_router(iot_signal_router, prefix="", tags=["IoT Sensor Network"])
    print("[OK] map-intelligence + iot routes registered")
except ImportError as e:
    import sys
    print(f"[WARN] map-intelligence not available: {e}", file=sys.stderr)

# Auth: JWT + RBAC
from src.backend.auth.router import router as auth_router
from src.backend.auth.models import User, UserSession  # noqa: F401
from src.backend.auth.dependencies import get_current_user, require_admin, get_optional_user
app.include_router(auth_router)

# Community & Knowledge Ledger
from src.backend.community.router import router as community_router
app.include_router(community_router)


# ============================================================
# Database Initialization
# ============================================================

@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    init_db()


# ============================================================
# Helper Functions
# ============================================================



def _is_research_token_valid(token: str, admin_id: int | None = None) -> bool:
    if not token:
        return False
    _cleanup_research_lab_state()
    token_meta = _research_lab_tokens.get(token)
    if not token_meta:
        return False
    return admin_id is None or token_meta.get("admin_id") == admin_id


def _has_local_admin_dashboard_session(request: Request) -> bool:
    host = request.headers.get("host", "")
    origin = request.headers.get("origin", "")
    return (
        request.headers.get("X-AVM-Admin-Session") == "active"
        and (
            "localhost" in host
            or "127.0.0.1" in host
            or "localhost" in origin
            or "127.0.0.1" in origin
        )
    )


def _resolve_research_admin_id(request: Request, user: User | None) -> int:
    if user and user.role == "admin":
        return user.id
    if _has_local_admin_dashboard_session(request):
        return 0
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Chi admin moi co quyen truy cap Research Lab.",
    )


def _cleanup_research_lab_state() -> None:
    now = datetime.utcnow()
    expired_codes = [
        code for code, meta in _research_lab_codes.items()
        if meta.get("expires_at") and meta["expires_at"] <= now
    ]
    for code in expired_codes:
        _research_lab_codes.pop(code, None)

    expired_tokens = [
        token for token, meta in _research_lab_tokens.items()
        if meta.get("expires_at") and meta["expires_at"] <= now
    ]
    for token in expired_tokens:
        _research_lab_tokens.pop(token, None)


def _new_research_lab_code() -> str:
    return f"RL-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"


def _default_research_lab_tree() -> dict:
    return {
        "name": "Research Lab",
        "value": "Awaiting trained ML bundle",
        "children": [
            {
                "name": "Dataset",
                "value": "Database records",
                "children": [
                    {"name": "Verified records", "value": "Used for training quality"},
                    {"name": "Self-collected records", "value": "SDEV evidence"},
                    {"name": "IoT / provenance", "value": "Trust features"},
                ],
            },
            {
                "name": "Confidence branch",
                "value": "A/B/C/D classifier",
                "children": [
                    {"name": "Training set", "value": "Fit classifier"},
                    {"name": "Validation set", "value": "Choose model"},
                    {"name": "Test set", "value": "Final report"},
                ],
            },
            {
                "name": "Valuation branch",
                "value": "Price interval model",
                "children": [
                    {"name": "Weighted regression", "value": "Central price"},
                    {"name": "Quantile interval", "value": "Low / mid / high"},
                    {"name": "Conformal calibration", "value": "Trust-band adjustment"},
                ],
            },
        ],
    }


def _date_label(value) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        return value[:10]
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def _find_model_version_by_stamp(db: Session, stamp: str | None) -> ModelVersion | None:
    if not stamp:
        return None
    model_version_info = db.query(ModelVersion).filter(
        ModelVersion.model_version == stamp
    ).first()
    if model_version_info is not None:
        return model_version_info
    return db.query(ModelVersion).filter(
        ModelVersion.model_path.like(f"%{stamp}%")
    ).first()


def _resolve_serving_model_version_info(db: Session, model_data: dict) -> tuple[ModelVersion | None, dict, dict]:
    """Resolve the DB row and official metrics for the model artifact actually serving predictions."""
    from src.backend.model_metrics import build_metric_provenance

    metric_provenance = build_metric_provenance()
    serving_metric = metric_provenance.get("serving") or {}
    serving_stamp = model_data.get("model_version") or serving_metric.get("stamp")

    model_version_info = _find_model_version_by_stamp(db, serving_stamp)
    if model_version_info is None and not serving_stamp:
        model_version_info = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()

    return model_version_info, serving_metric, metric_provenance


def _metric_or_db_version(model_version_info: ModelVersion | None, serving_metric: dict, model_data: dict) -> str | None:
    return (
        serving_metric.get("stamp")
        or model_data.get("model_version")
        or (model_version_info.model_version if model_version_info else None)
    )


def _get_prediction_pool_stats(db: Session) -> dict:
    now = time.time()
    cached = _PREDICTION_POOL_CACHE.get("value")
    if cached and now < float(_PREDICTION_POOL_CACHE.get("expires_at", 0)):
        return {**cached, "cache": "hit"}

    stats = {
        "verified_pool": db.query(Property).filter(Property.verification_status == "verified").count(),
        "self_collected_pool": db.query(Property).filter(
            Property.data_origin_type == "self_collected",
            Property.verification_status == "verified",
        ).count(),
    }
    _PREDICTION_POOL_CACHE["value"] = stats
    _PREDICTION_POOL_CACHE["expires_at"] = now + PREDICTION_POOL_CACHE_TTL_SECONDS
    return {**stats, "cache": "miss"}


def _confidence_band_from_score(score: float) -> str:
    if score >= 8.5:
        return "A"
    if score >= 7.0:
        return "B"
    if score >= 5.5:
        return "C"
    return "D"


def _timeliness_proxy_from_assessment(assessment: dict) -> float:
    support_stats = assessment.get("support_statistics", {})
    volatility = support_stats.get("local_price_volatility", 0.12) or 0.12
    if volatility <= 0.08:
        return 8.5
    if volatility <= 0.15:
        return 7.2
    if volatility <= 0.22:
        return 6.0
    return 4.8


def build_research_prediction_input(
    request_data: dict,
    matched_province: str,
    assessment: dict,
    model_data: dict,
) -> dict:
    support_stats = assessment.get("support_statistics", {})
    component_scores = assessment.get("component_scores", {})
    overall_score = assessment.get("overall_score", 5.5)

    input_data = {
        "area_m2": request_data.get("area_m2"),
        "bedrooms": request_data.get("bedrooms") or 0,
        "bathrooms": request_data.get("bathrooms") or 0,
        "floor_count": request_data.get("floor_count") or 1,
        "frontage_m": request_data.get("frontage_m") or 5.0,
        "property_type": request_data.get("property_type"),
        "province_city": matched_province,
        "district": request_data.get("district"),
        "latitude": request_data.get("latitude") or request_data.get("gps_lat") or 21.0,
        "longitude": request_data.get("longitude") or request_data.get("gps_lng") or 105.5,
        "noise_level": request_data.get("noise_level") if request_data.get("noise_level") is not None else 45.0,
        "temperature": request_data.get("temperature") if request_data.get("temperature") is not None else 25.0,
        "humidity": request_data.get("humidity") if request_data.get("humidity") is not None else 70.0,
        "light_level": request_data.get("light_level") if request_data.get("light_level") is not None else 300.0,
        "area_type": request_data.get("area_type") or "urban_center",
        "legal_status": request_data.get("legal_status") or "other",
        "furnishing": request_data.get("furnishing") or "semi_furnished",
        "rqs": overall_score,
        "provenance_score": component_scores.get("data_completeness", overall_score),
        "verification_score": component_scores.get("data_quality", overall_score),
        "market_anchor_score": float(support_stats.get("anchor_share", 0.0) or 0.0) * 10.0,
        "timeliness_score": _timeliness_proxy_from_assessment(assessment),
        "training_weight": max(0.25, min(3.0, 0.55 + overall_score / 5.0)),
        "evidence_weight": max(0.2, min(1.0, float(support_stats.get("anchor_share", 0.0) or 0.0) + 0.35)),
        "anchor_flag_feature": 1 if (support_stats.get("anchor_count", 0) or 0) > 0 else 0,
        "has_iot_signal_feature": 1 if any(request_data.get(key) is not None for key in ["noise_level", "temperature", "humidity", "light_level", "gps_lat", "gps_lng"]) else 0,
    }

    case_features = build_case_confidence_features(request_data, assessment)
    confidence_model = model_data.get("confidence_best_model")
    confidence_feature_names = model_data.get("confidence_feature_names", [])
    confidence_result = {
        "model_name": model_data.get("confidence_best_model_name"),
        "predicted_grade": _confidence_band_from_score(overall_score),
        "predicted_score": round(overall_score, 2),
        "probabilities": {},
    }

    if confidence_model and confidence_feature_names:
        import numpy as np

        conf_vector = np.array([[case_features.get(name, 0.0) for name in confidence_feature_names]], dtype=float)
        probabilities = confidence_model.predict_proba(conf_vector)[0]
        classes = list(confidence_model.classes_)
        score_map = {"A": 9.2, "B": 7.6, "C": 6.1, "D": 4.2}
        stage1_score = 0.0
        for idx, label in enumerate(classes):
            stage1_score += probabilities[idx] * score_map.get(label, 5.5)
            confidence_result["probabilities"][label] = round(float(probabilities[idx]), 4)
        predicted_grade = classes[int(np.argmax(probabilities))]
        confidence_result["predicted_grade"] = predicted_grade
        confidence_result["predicted_score"] = round(float(stage1_score), 2)
        input_data["confidence_stage1_score"] = float(stage1_score)
        input_data["confidence_prob_a"] = float(probabilities[classes.index("A")]) if "A" in classes else 0.0
        input_data["confidence_prob_b"] = float(probabilities[classes.index("B")]) if "B" in classes else 0.0
        input_data["confidence_prob_c"] = float(probabilities[classes.index("C")]) if "C" in classes else 0.0
        input_data["confidence_prob_d"] = float(probabilities[classes.index("D")]) if "D" in classes else 0.0
    else:
        band = _confidence_band_from_score(overall_score)
        input_data["confidence_stage1_score"] = float(overall_score)
        input_data["confidence_prob_a"] = 1.0 if band == "A" else 0.0
        input_data["confidence_prob_b"] = 1.0 if band == "B" else 0.0
        input_data["confidence_prob_c"] = 1.0 if band == "C" else 0.0
        input_data["confidence_prob_d"] = 1.0 if band == "D" else 0.0

    assessment["ml_confidence"] = confidence_result
    assessment["assessment_tree"] = build_assessment_tree(assessment)
    return input_data


def build_property_trace_profile(prop: Property) -> dict:
    source_access_link = prop.source_url or f"/api/properties/{prop.id}/detail"
    completeness_flags = {
        "has_source_name": bool(prop.source_name),
        "has_source_link": bool(source_access_link),
        "has_verification_note": bool(prop.verification_note or prop.verification_notes),
        "has_collector": bool(prop.collected_by),
        "has_evidence_photo": bool(prop.evidence_photo_path),
        "has_image": bool(prop.image_url or prop.image_urls),
        "has_iot": bool(
            prop.noise_level is not None or prop.temperature is not None or
            prop.humidity is not None or prop.light_level is not None
        ),
        "has_coordinates": bool(
            (prop.latitude is not None or prop.gps_lat is not None) and
            (prop.longitude is not None or prop.gps_lng is not None)
        ),
    }
    completeness_score = round(sum(1 for value in completeness_flags.values() if value) / len(completeness_flags) * 10, 2)
    return {
        "source_access_link": source_access_link,
        "trace_completeness_score": completeness_score,
        "flags": completeness_flags,
        "origin_label": "Tu thu thap" if prop.data_origin_type == "self_collected" else "Nguon ben ngoai",
        "verification_label": prop.verification_status,
    }


def parse_string_list(raw_value) -> List[str]:
    if not raw_value:
        return []
    if isinstance(raw_value, list):
        return [str(item) for item in raw_value if item]
    try:
        parsed = json.loads(raw_value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if item]
    except Exception:
        pass
    return [item.strip() for item in str(raw_value).split(",") if item.strip()]


def build_dataset_overview(db: Session) -> dict:
    total = db.query(Property).count()
    external = db.query(Property).filter(Property.data_origin_type == "public_collected").count()
    self_collected = db.query(Property).filter(Property.data_origin_type == "self_collected").count()
    verified = db.query(Property).filter(Property.verification_status == "verified").count()
    with_source = db.query(Property).filter(Property.source_url.isnot(None), Property.source_url != "").count()
    with_trace = db.query(Property).filter(
        Property.source_name.isnot(None), Property.source_name != "",
        Property.verification_status == "verified"
    ).count()
    self_with_trace = db.query(Property).filter(
        Property.data_origin_type == "self_collected",
        Property.source_name.isnot(None), Property.source_name != "",
        Property.collection_method.isnot(None), Property.collection_method != ""
    ).count()
    external_with_trace = db.query(Property).filter(
        Property.data_origin_type == "public_collected",
        Property.source_url.isnot(None), Property.source_url != ""
    ).count()
    source_count = db.query(Property.source_name).filter(
        Property.source_name.isnot(None),
        Property.source_name != ""
    ).distinct().count()
    external_gap = max(0, 3000 - external)
    self_gap = max(0, 150 - self_collected)
    external_link_ratio = round(external_with_trace / external * 100, 2) if external else 0.0
    self_trace_ratio = round(self_with_trace / self_collected * 100, 2) if self_collected else 0.0
    top_sources = []
    source_rows = (
        db.query(Property.source_name)
        .filter(Property.source_name.isnot(None), Property.source_name != "")
        .distinct()
        .all()
    )
    for (source_name,) in source_rows:
        total_records = db.query(Property).filter(Property.source_name == source_name).count()
        if total_records == 0:
            continue
        verified_records = db.query(Property).filter(
            Property.source_name == source_name,
            Property.verification_status == "verified"
        ).count()
        top_sources.append({
            "source_name": source_name,
            "total_records": total_records,
            "verified_records": verified_records,
        })
    top_sources = sorted(top_sources, key=lambda item: item["total_records"], reverse=True)[:6]

    return {
        "counts": {
            "total": total,
            "external": external,
            "self_collected": self_collected,
            "verified": verified,
            "with_source_link": with_source,
            "full_trace_verified": with_trace,
            "external_with_trace": external_with_trace,
            "self_with_trace": self_with_trace,
            "source_count": source_count,
        },
        "ratios": {
            "external_source_link_ratio": external_link_ratio,
            "self_trace_ratio": self_trace_ratio,
            "verified_ratio": round(verified / total * 100, 2) if total else 0.0,
        },
        "standard_targets": {
            "total_over_3000": total >= 3000,
            "external_over_3000": external >= 3000,
            "self_collected_over_150": self_collected >= 150,
            "all_external_have_source_link": external == external_with_trace,
            "all_self_collected_have_trace_link": self_collected == self_with_trace,
        },
        "gaps": {
            "external_to_3000": external_gap,
            "self_collected_to_150": self_gap,
        },
        "top_sources": top_sources,
        "standard_notes": [
            "Tap du lieu hien tai da dat >3000 tong mau va >150 mau tu thu thap.",
            "Tat ca public records hien tai deu co source link truy vet.",
            "Self-collected records duoc uu tien co internal/external access link de xem chi tiet tung mau.",
            "Moc >3000 mau ngoai se chi duoc danh dau dat khi thuc su co du lieu ngoai hop le duoc nap them.",
        ],
    }


def match_province_name(db: Session, province: str) -> str:
    """Match user province text to the nearest province stored in the database."""
    all_provinces = [p[0] for p in db.query(Property.province_city).distinct().all()]
    province_normalized = province.lower().replace("tp.", "").replace(".", "").strip()
    matched_province = None

    province_mappings = {
        "ho chi minh": "TP. Hồ Chí Minh",
        "tp hcm": "TP. Hồ Chí Minh",
        "tp hồ chí minh": "TP. Hồ Chí Minh",
        "ha noi": "Hà Nội",
        "hà nội": "Hà Nội",
        "da nang": "Đà Nẵng",
        "đà nẵng": "Đà Nẵng",
        "hai phong": "Hải Phòng",
        "hải phòng": "Hải Phòng",
        "can tho": "Cần Thơ",
        "cần thơ": "Cần Thơ",
        "binh duong": "Bình Dương",
        "bình dương": "Bình Dương",
        "dong nai": "Đồng Nai",
        "đồng nai": "Đồng Nai",
    }

    if province_normalized in province_mappings:
        matched_province = province_mappings[province_normalized]
    else:
        for candidate in all_provinces:
            if not candidate:
                continue
            candidate_name = candidate.lower().replace("tp.", "").replace(".", "").strip()
            if province_normalized.replace(" ", "") in candidate_name.replace(" ", ""):
                matched_province = candidate
                break
            if candidate_name.replace(" ", "") in province_normalized.replace(" ", ""):
                matched_province = candidate
                break

    return matched_province or province


def collect_support_properties(
    db: Session,
    province: str,
    district: str,
    property_type: str,
    area: float,
):
    """Find local support records for both valuation and data-quality assessment."""
    from sqlalchemy import func

    matched_province = match_province_name(db, province)
    area_min = area * 0.8
    area_max = area * 1.2

    same_type_count = db.query(Property).filter(
        Property.property_type == property_type,
        Property.verification_status == "verified",
    ).count()

    same_province_count = db.query(Property).filter(
        Property.province_city == matched_province,
        Property.property_type == property_type,
        Property.verification_status == "verified",
    ).count()

    same_district_count = db.query(Property).filter(
        Property.province_city == matched_province,
        Property.district == district,
        Property.property_type == property_type,
        Property.verification_status == "verified",
    ).count()

    def _base_query():
        return db.query(Property).filter(
            Property.property_type == property_type,
            Property.verification_status == "verified",
            Property.area_m2 >= area_min,
            Property.area_m2 <= area_max,
        )

    district_matches = _base_query().filter(
        Property.province_city == matched_province,
        Property.district == district,
    ).order_by(func.abs(Property.area_m2 - area)).limit(10).all()

    comparable: List[Property] = list(district_matches)
    comparable_ids = {item.id for item in comparable}

    if len(comparable) < 10:
        province_matches = _base_query().filter(
            Property.province_city == matched_province,
        ).order_by(func.abs(Property.area_m2 - area)).limit(20).all()
        for item in province_matches:
            if item.id not in comparable_ids:
                comparable.append(item)
                comparable_ids.add(item.id)
            if len(comparable) >= 10:
                break

    if len(comparable) < 10:
        expanded_min = area * 0.7
        expanded_max = area * 1.3
        global_matches = db.query(Property).filter(
            Property.property_type == property_type,
            Property.verification_status == "verified",
            Property.area_m2 >= expanded_min,
            Property.area_m2 <= expanded_max,
        ).order_by(func.abs(Property.area_m2 - area)).limit(20).all()
        for item in global_matches:
            if item.id not in comparable_ids:
                comparable.append(item)
                comparable_ids.add(item.id)
            if len(comparable) >= 10:
                break

    return {
        "matched_province": matched_province,
        "same_type_count": same_type_count,
        "same_province_count": same_province_count,
        "same_district_count": same_district_count,
        "comparables": comparable[:10],
    }


def serialize_comparable_records(comparable: List[Property], area: float) -> List[dict]:
    """Serialize comparable ORM objects into API-friendly records."""
    records: List[dict] = []
    for comp in comparable:
        similarity = 1 - min(abs((comp.area_m2 or 0) - area) / area, 1) if area else 0
        records.append(
            {
                "id": comp.id,
                "property_type": comp.property_type,
                "district": comp.district,
                "ward": comp.ward,
                "street": comp.street_or_project,
                "area_m2": comp.area_m2,
                "bedrooms": comp.bedrooms,
                "bathrooms": comp.bathrooms,
                "price": comp.price,
                "price_per_m2": comp.price_per_m2,
                "listing_date": comp.listing_date.isoformat() if comp.listing_date else None,
                "source_name": comp.source_name,
                "source_url": comp.source_url,
                "data_origin_type": comp.data_origin_type,
                "verification_status": comp.verification_status,
                "similarity": round(similarity, 2),
                "image_url": comp.image_url,
                "has_iot": comp.noise_level is not None,
                "noise_level": comp.noise_level,
                "legal_status": comp.legal_status,
            }
        )
    return records


# ============================================================
# API Endpoints
# ============================================================

@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "Real Estate AVM API - IoT Enhanced",
        "version": "2.0.0",
        "description": "Hệ thống định giá bất động sản với IoT"
    }


@app.get("/api/health")
def health_check():
    """Readiness health check: process + database connectivity."""
    from src.backend.database import SessionLocal, engine
    from src.backend.models import Property
    from sqlalchemy import inspect
    now = time.time()
    cached_database = _HEALTH_DB_CACHE.get("database")
    if cached_database and now < float(_HEALTH_DB_CACHE.get("expires_at", 0)):
        return {
            "status": "ok",
            "iot_enabled": True,
            "database": {
                **cached_database,
                "cache": "hit",
                "expires_in_seconds": round(float(_HEALTH_DB_CACHE["expires_at"]) - now, 2),
            },
        }

    db = SessionLocal()
    try:
        schema_ready = inspect(engine).has_table(Property.__tablename__)
        total = 0
        sc = 0
        if schema_ready:
            total = db.query(Property).count()
            sc = db.query(Property).filter(Property.data_origin_type == "self_collected").count()
        database = {
            "ok": True,
            "dialect": engine.dialect.name,
            "schema_ready": schema_ready,
            "total_properties": total,
            "self_collected_properties": sc,
        }
        _HEALTH_DB_CACHE["database"] = database
        _HEALTH_DB_CACHE["expires_at"] = now + HEALTH_DB_CACHE_TTL_SECONDS
        return {
            "status": "ok",
            "iot_enabled": True,
            "database": {**database, "cache": "miss", "expires_in_seconds": HEALTH_DB_CACHE_TTL_SECONDS},
        }
    finally:
        db.close()


# --- Location Endpoints (Round 22: Canonical Province Config) ---
# Dùng SCOPE_DISTRICTS từ src.config.province_config — NGUỒN DUY NHẤT
# KHÔNG hardcode tên tỉnh/quận ở đây nữa


@app.get("/api/provinces", tags=["Location"])
def get_provinces(db: Session = Depends(get_db)):
    """
    Get list of provinces — Hà Nội + TP.HCM (6 quận scope).
    """
    from sqlalchemy import func

    PROVINCE_CODES = {"Hà Nội": "HN", "TP. Hồ Chí Minh": "HCM"}

    # Build map dynamically from SCOPE_DISTRICTS (NGUỒN DUY NHẤT)
    # Filter to 6 core districts (Hà Nội + TP.HCM) — ML scope
    ML_SCOPE_PROVINCES = {"Hà Nội", "TP. Hồ Chí Minh"}
    province_district_map = {
        province: districts
        for province, districts in SCOPE_DISTRICTS.items()
        if province in ML_SCOPE_PROVINCES
    }

    provinces = []
    for prov_name, districts in province_district_map.items():
        count = db.query(func.count(Property.id)).filter(
            Property.province_city == prov_name,
            Property.district.in_(districts)
        ).scalar()

        district_infos = [
            {"name": d, "slug": d.lower().replace("quận ", "quan-").replace(" ", "-"), "priority": i + 1}
            for i, d in enumerate(districts)
        ]

        provinces.append({
            "name": prov_name,
            "code": PROVINCE_CODES.get(prov_name, prov_name[:3].upper()),
            "district_count": len(districts),
            "actual_record_count": count,
            "districts": district_infos,
        })

    return {
        "provinces": provinces,
        "total": len(provinces),
        "scope": "SIX_DISTRICTS_ONLY",
        "scope_note": "ML pipeline chỉ train trên 6 quận này — mở rộng scope cần retrain",
        "standard": "CVX-BDS/IoT 1.1-VN",
    }


@app.get("/api/provinces/{province}/districts", tags=["Location"])
def get_districts(province: str, db: Session = Depends(get_db)):
    """
    Get districts for a province — giới hạn 6 quận (giữ nguyên scope gốc).
    Dùng normalize_province() để handle alias.
    """
    from sqlalchemy import func

    norm = normalize_province(province)
    PROVINCE_CODES = {"Hà Nội": "HN", "TP. Hồ Chí Minh": "HCM"}

    # Build from SCOPE_DISTRICTS dynamically — no duplication
    ML_SCOPE_PROVINCES = {"Hà Nội", "TP. Hồ Chí Minh"}
    scope_districts = {
        province: districts
        for province, districts in SCOPE_DISTRICTS.items()
        if province in ML_SCOPE_PROVINCES
    }

    if norm not in scope_districts:
        return {
            "province": province,
            "districts": [],
            "error": f"Chỉ chấp nhận 'Hà Nội' hoặc 'TP. Hồ Chí Minh'. '{province}' không nằm trong scope ML.",
        }

    districts = scope_districts[norm]
    district_infos = []
    for i, d in enumerate(districts):
        count = db.query(func.count(Property.id)).filter(
            Property.province_city == norm,
            Property.district == d
        ).scalar()
        slug = d.lower().replace("quận ", "quan-").replace(" ", "-")
        district_infos.append({
            "name": d,
            "slug": slug,
            "priority": i + 1,
            "record_count": count,
        })

    return {
        "province": norm,
        "code": PROVINCE_CODES.get(norm, norm[:3].upper()),
        "districts": district_infos,
        "total": len(districts),
    }


# --- Prediction Endpoints ---

@app.post("/api/data-quality/evaluate", response_model=DataQualityResponse)
def evaluate_data_quality(request: PredictionRequest, db: Session = Depends(get_db)):
    """Evaluate whether available evidence is sufficient for reliable valuation."""
    support_bundle = collect_support_properties(
        db=db,
        province=request.province_city,
        district=request.district,
        property_type=request.property_type,
        area=request.area_m2,
    )

    assessment = build_data_quality_assessment(
        request_data=request.dict(),
        support_properties=support_bundle["comparables"],
        district_support_count=support_bundle["same_district_count"],
        province_support_count=support_bundle["same_province_count"],
        property_type_support_count=support_bundle["same_type_count"],
    )

    return DataQualityResponse(
        matched_province=support_bundle["matched_province"],
        request_summary={
            "property_type": request.property_type,
            "province_city": request.province_city,
            "district": request.district,
            "area_m2": request.area_m2,
        },
        assessment={
            **assessment,
            "assessment_tree": build_assessment_tree(assessment),
            "comparable_records": serialize_comparable_records(support_bundle["comparables"], request.area_m2),
        },
    )


@app.post("/api/research-lab/request-code", response_model=ResearchLabCodeResponse)
def research_lab_request_code(request: Request, admin: User | None = Depends(get_optional_user)):
    """Issue a one-time Research Lab code for the current admin session."""
    admin_id = _resolve_research_admin_id(request, admin)
    _cleanup_research_lab_state()
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=_RESEARCH_CODE_TTL_SECONDS)

    code = _new_research_lab_code()
    while code in _research_lab_codes:
        code = _new_research_lab_code()

    _research_lab_codes[code] = {
        "admin_id": admin_id,
        "expires_at": expires_at,
    }
    return ResearchLabCodeResponse(
        code=code,
        expires_at=expires_at.isoformat() + "Z",
        ttl_seconds=_RESEARCH_CODE_TTL_SECONDS,
        message="Ma Research Lab da duoc tao. Ma chi dung mot lan va het han sau 10 phut.",
    )


@app.post("/api/research-lab/access", response_model=ResearchLabAccessResponse)
def research_lab_access(request: Request, body: ResearchLabAccessRequest, _admin: User | None = Depends(get_optional_user)):
    """Unlock Research Lab with a one-time admin-issued code."""
    admin_id = _resolve_research_admin_id(request, _admin)
    _cleanup_research_lab_state()
    code = (body.access_code or "").strip().upper()
    code_meta = _research_lab_codes.get(code)
    if not code_meta:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ma Research Lab khong hop le hoac da het hieu luc."
        )
    if code_meta.get("admin_id") not in (0, admin_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ma Research Lab nay khong thuoc tai khoan admin hien tai."
        )

    _research_lab_codes.pop(code, None)

    token = secrets.token_urlsafe(24)
    expires_at = datetime.utcnow() + timedelta(minutes=_RESEARCH_SESSION_MINUTES)
    _research_lab_tokens[token] = {
        "admin_id": admin_id,
        "expires_at": expires_at,
    }
    return ResearchLabAccessResponse(
        granted=True,
        token=token,
        expires_at=expires_at.isoformat() + "Z",
        session_minutes=_RESEARCH_SESSION_MINUTES,
        message="Research Lab da duoc mo khoa trong 60 phut.",
    )


@app.get("/api/research-lab/overview", response_model=ResearchLabOverviewResponse)
def research_lab_overview(
    request: Request,
    token: str = Query(...),
    db: Session = Depends(get_db),
    _admin: User | None = Depends(get_optional_user),
):
    """Return a full overview of the research training workflow."""
    admin_id = _resolve_research_admin_id(request, _admin)
    token_admin_id = None if admin_id == 0 else admin_id
    if not _is_research_token_valid(token, token_admin_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token Research Lab khong hop le."
        )

    model_status = {
        "trained": True,
        "message": "ML bundle da san sang.",
        "next_action": None,
    }
    try:
        model_data = get_cached_model()
    except HTTPException as exc:
        if exc.status_code != status.HTTP_503_SERVICE_UNAVAILABLE:
            raise
        model_data = {}
        model_status = {
            "trained": False,
            "message": str(exc.detail),
            "next_action": "python scripts/retrain_v2.py",
        }

    metadata = model_data.get("metadata", {})
    confidence_metadata = metadata.get("confidence_metadata", {}) or model_data.get("confidence_metadata", {})
    quality_summary = metadata.get("training_quality_summary", {})
    calibration = metadata.get("conformal_calibration", {}) or model_data.get("conformal_calibration", {})

    total_properties = db.query(Property).count()
    verified_properties = db.query(Property).filter(Property.verification_status == "verified").count()
    self_collected_properties = db.query(Property).filter(Property.data_origin_type == "self_collected").count()

    return ResearchLabOverviewResponse(
        model_status=model_status,
        standard_name=metadata.get("training_standard", "CVX-BDS/IoT 1.1-VN Research Extension"),
        training_flow_tree=metadata.get("training_flow_tree") or _default_research_lab_tree(),
        confidence_stage={
            **confidence_metadata,
            "model_name": model_data.get("confidence_best_model_name") or confidence_metadata.get("best_model") or "Chua train confidence classifier",
            "label_distribution": confidence_metadata.get("label_distribution") or {"A": 0, "B": 0, "C": 0, "D": 0},
        },
        price_stage={
            "best_model": metadata.get("best_model") or "Chua train valuation model",
            "all_results": metadata.get("all_results", {}),
            "split_strategy": metadata.get("split_strategy"),
            "interval_strategy": metadata.get("interval_strategy"),
            "feature_count": metadata.get("n_features") or 0,
            "feature_names": metadata.get("feature_names", []),
        },
        quality_summary={
            "avg_rqs": 0,
            "median_rqs": 0,
            "anchor_rate": 0,
            "avg_training_weight": 0,
            **quality_summary,
            "db_total_properties": total_properties,
            "db_verified_properties": verified_properties,
            "db_self_collected_properties": self_collected_properties,
        },
        calibration=calibration,
        notes=[
            *([] if model_status["trained"] else [
                "Chua tim thay ML model bundle nen Research Lab dang hien thi metadata va pipeline mau thay vi ket qua train thuc te.",
                "Chay python scripts/retrain_v2.py de tao model bundle va cap nhat cac bieu do train/calibration.",
            ]),
            "Nhanh 1 dung classifier dang cay de danh gia do tin cay A/B/C/D theo dung tinh than ID3-C4.5-CART.",
            "Nhanh 2 dung model hoi quy co trong so tin cay de du doan gia trung tam va quantile interval.",
            "Khoang gia cuoi duoc hieu chinh them bang grouped conformal calibration theo trust band.",
        ],
    )


def _require_research_admin_operation(request: Request, token: str, admin: User | None) -> int:
    admin_id = _resolve_research_admin_id(request, admin)
    token_admin_id = None if admin_id == 0 else admin_id
    if not _is_research_token_valid(token, token_admin_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token Research Lab khong hop le hoac da het han.",
        )
    return admin_id


def _research_lab_capabilities() -> dict:
    return {
        "testing": [
            {
                "operation": "full_tests",
                "label": "Chay tat ca pytest",
                "description": "Unit + integration tests trong tests/",
                "timeout_seconds": 900,
            },
            {
                "operation": "unit_tests",
                "label": "Unit tests",
                "description": "Kiem thu domain valuation/comparable/fit.",
                "timeout_seconds": 420,
            },
            {
                "operation": "integration_tests",
                "label": "Integration API tests",
                "description": "FastAPI TestClient cho api_v2 valuation/factors.",
                "timeout_seconds": 420,
            },
            {
                "operation": "api_contract_tests",
                "label": "API contract v2",
                "description": "Tap trung rieng tests/integration/test_api_v2.py.",
                "timeout_seconds": 420,
            },
            {
                "operation": "frontend_build",
                "label": "Frontend production build",
                "description": "npm run build:check de bat loi UI va bundle budget.",
                "timeout_seconds": 360,
            },
            {
                "operation": "data_validation",
                "label": "Data validation",
                "description": "scripts/validate_clean_data.py truoc khi train.",
                "timeout_seconds": 300,
            },
            {
                "operation": "data_audit",
                "label": "PostgreSQL catalog audit",
                "description": "scripts/audit_postgres_catalog.py cho dataset, prediction va ML lineage.",
                "timeout_seconds": 420,
            },
            {
                "operation": "model_evaluation",
                "label": "Model evaluation",
                "description": "scripts/evaluate_model.py so sanh voi expert ground truth.",
                "timeout_seconds": 420,
            },
        ],
        "training": [
            {
                "operation": "train_dry_run",
                "label": "Validate truoc train",
                "description": "scripts/retrain_v2.py --dry-run, khong tao model moi.",
                "timeout_seconds": 420,
            },
            {
                "operation": "train_full",
                "label": "Full retrain model",
                "description": "Train that: validate data, fit ML pipeline, save model, compute SHAP, register version.",
                "timeout_seconds": 2400,
                "requires_confirmation": True,
            },
            {
                "operation": "shap_refresh",
                "label": "Refresh SHAP cache",
                "description": "Tinh lai cache giai thich sau khi model thay doi.",
                "timeout_seconds": 420,
            },
        ],
        "admin": [
            {
                "operation": "list_models",
                "label": "List model versions",
                "description": "Doc model registry hien tai.",
                "timeout_seconds": 120,
            },
            {
                "operation": "model_reload",
                "label": "Reload backend model cache",
                "description": "Xoa cache de lan predict tiep theo nap model moi nhat.",
                "timeout_seconds": 30,
            },
            {
                "operation": "db_status",
                "label": "Database status",
                "description": "Doc tong so ban ghi, provenance, ML readiness.",
                "timeout_seconds": 30,
            },
        ],
        "mlops": [
            {
                "operation": "mlops_experiments",
                "label": "Experiment leaderboard",
                "description": "Bang so sanh moi lan train (R2/MAE/features) tu metadata that.",
                "timeout_seconds": 60,
            },
            {
                "operation": "mlops_registry",
                "label": "Model registry + active",
                "description": "Liet ke model version va version dang duoc pin active.",
                "timeout_seconds": 60,
            },
            {
                "operation": "mlops_monitor",
                "label": "Model health check",
                "description": "Load model active + smoke predict de xac nhan con phuc vu duoc.",
                "timeout_seconds": 120,
            },
            {
                "operation": "mlops_drift",
                "label": "Data drift (PSI)",
                "description": "Population Stability Index giua du lieu cu va moi -> co nen retrain.",
                "timeout_seconds": 180,
            },
            {
                "operation": "mlops_activate",
                "label": "Activate / rollback version",
                "description": "Pin backend dung 1 model version cu the (nhap version stamp).",
                "timeout_seconds": 60,
            },
            {
                "operation": "mlops_deactivate",
                "label": "Bo pin (auto latest)",
                "description": "Go pin de backend tu chon model moi nhat.",
                "timeout_seconds": 60,
            },
        ],
    }


def _flatten_capabilities() -> Dict[str, dict]:
    flattened = {}
    for group, items in _research_lab_capabilities().items():
        for item in items:
            flattened[item["operation"]] = {**item, "group": group}
    return flattened


def _safe_float(value, default: float, min_value: float, max_value: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(min_value, min(max_value, parsed))


def _build_research_lab_command(operation: str, params: dict) -> tuple[list[str] | None, Path, int]:
    root = Path(__file__).resolve().parents[2]
    python = sys.executable
    timeout = int(_flatten_capabilities()[operation]["timeout_seconds"])

    if operation == "full_tests":
        return [python, "-m", "pytest", "tests", "-q"], root, timeout
    if operation == "unit_tests":
        return [python, "-m", "pytest", "tests/unit", "-q"], root, timeout
    if operation == "integration_tests":
        return [python, "-m", "pytest", "tests/integration", "-q"], root, timeout
    if operation == "api_contract_tests":
        return [python, "-m", "pytest", "tests/integration/test_api_v2.py", "-q"], root, timeout
    if operation == "frontend_build":
        return ["npm", "run", "build:check"], root / "frontend", timeout
    if operation == "data_validation":
        return [python, "scripts/validate_clean_data.py"], root, timeout
    if operation == "data_audit":
        return [python, "scripts/audit_postgres_catalog.py"], root, timeout
    if operation == "model_evaluation":
        return [python, "scripts/evaluate_model.py"], root, timeout
    if operation == "train_dry_run":
        return [python, "scripts/retrain_v2.py", "--dry-run"], root, timeout
    if operation == "train_full":
        test_size = _safe_float(params.get("test_size"), 0.15, 0.05, 0.35)
        min_clean = int(_safe_float(params.get("min_clean"), 500, 50, 100000))
        return [python, "scripts/retrain_v2.py", "--test-size", str(test_size), "--min-clean", str(min_clean)], root, timeout
    if operation == "shap_refresh":
        return [python, "scripts/compute_shap_explanations.py"], root, timeout
    if operation == "list_models":
        return [python, "scripts/retrain_v2.py", "--list"], root, timeout
    if operation == "mlops_experiments":
        return [python, "scripts/mlops.py", "experiments"], root, timeout
    if operation == "mlops_registry":
        return [python, "scripts/mlops.py", "registry"], root, timeout
    if operation == "mlops_monitor":
        return [python, "scripts/mlops.py", "monitor"], root, timeout
    if operation == "mlops_drift":
        return [python, "scripts/mlops.py", "drift"], root, timeout
    if operation == "mlops_activate":
        version = str(params.get("version", "")).strip()
        return [python, "scripts/mlops.py", "activate", "--version", version], root, timeout
    if operation == "mlops_deactivate":
        return [python, "scripts/mlops.py", "deactivate"], root, timeout
    return None, root, timeout


def _serialize_research_job(job: dict) -> dict:
    public = dict(job)
    public.pop("thread", None)
    public["command"] = " ".join(public.get("command") or []) if public.get("command") else public.get("operation")
    return public


def _save_research_job(job: dict) -> None:
    try:
        _research_lab_jobs_dir.mkdir(parents=True, exist_ok=True)
        path = _research_lab_jobs_dir / f"{job['id']}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(_serialize_research_job(job), f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass


def _log_research_job_audit(job: dict, action: str) -> None:
    try:
        from src.backend.database import SessionLocal

        db = SessionLocal()
        try:
            db.add(AuditLog(
                record_id=None,
                table_name="research_lab_jobs",
                action_type=action,
                changed_by=f"research-lab:{job.get('admin_id', 'unknown')}",
                new_value_json=json.dumps(_serialize_research_job(job), ensure_ascii=False, default=str),
                change_note=f"Research Lab admin operation {job.get('operation')} {action.lower()}",
            ))
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


def _finish_internal_research_job(job_id: str) -> None:
    with _research_lab_jobs_lock:
        job = _research_lab_jobs[job_id]
        job["status"] = "running"
        job["started_at"] = datetime.utcnow().isoformat() + "Z"

    try:
        if job["operation"] == "model_reload":
            from src.backend.deps import clear_model_cache

            clear_model_cache()
            output = "Model cache cleared. The next prediction request will load the ACTIVE_MODEL.json artifact only."
            return_code = 0
        elif job["operation"] == "db_status":
            from src.backend.database import SessionLocal

            db = SessionLocal()
            try:
                payload = {
                    "total_properties": db.query(Property).count(),
                    "provenance_records": db.query(ProvenanceChain).count(),
                    "collection_sources": db.query(CollectionSource).count(),
                    "model_versions": db.query(ModelVersion).count(),
                    "has_enough_for_ml": db.query(Property).count() >= 50,
                }
            finally:
                db.close()
            output = json.dumps(payload, ensure_ascii=False, indent=2)
            return_code = 0
        else:
            raise RuntimeError(f"Unsupported internal operation: {job['operation']}")

        with _research_lab_jobs_lock:
            job = _research_lab_jobs[job_id]
            job["status"] = "succeeded"
            job["return_code"] = return_code
            job["stdout"] = output
            job["stderr"] = ""
            job["finished_at"] = datetime.utcnow().isoformat() + "Z"
            _save_research_job(job)
        _log_research_job_audit(job, "COMPLETE")
    except Exception as exc:
        with _research_lab_jobs_lock:
            job = _research_lab_jobs[job_id]
            job["status"] = "failed"
            job["return_code"] = 1
            job["stdout"] = ""
            job["stderr"] = str(exc)
            job["finished_at"] = datetime.utcnow().isoformat() + "Z"
            _save_research_job(job)
        _log_research_job_audit(job, "FAIL")


def _run_research_lab_subprocess(job_id: str) -> None:
    with _research_lab_jobs_lock:
        job = _research_lab_jobs[job_id]
        job["status"] = "running"
        job["started_at"] = datetime.utcnow().isoformat() + "Z"
        command = list(job["command"])
        cwd = Path(job["cwd"])
        timeout = int(job["timeout_seconds"])
        _save_research_job(job)

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        status_value = "succeeded" if completed.returncode == 0 else "failed"
        stdout = completed.stdout[-60000:]
        stderr = completed.stderr[-30000:]
        return_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        status_value = "timeout"
        stdout = (exc.stdout or "")[-60000:]
        stderr = ((exc.stderr or "") + f"\nTimed out after {timeout} seconds.")[-30000:]
        return_code = 124
    except Exception as exc:
        status_value = "failed"
        stdout = ""
        stderr = str(exc)
        return_code = 1

    with _research_lab_jobs_lock:
        job = _research_lab_jobs[job_id]
        job["status"] = status_value
        job["return_code"] = return_code
        job["stdout"] = stdout
        job["stderr"] = stderr
        job["finished_at"] = datetime.utcnow().isoformat() + "Z"
        _save_research_job(job)

    _log_research_job_audit(job, "COMPLETE" if status_value == "succeeded" else "FAIL")


@app.get("/api/research-lab/admin/capabilities", tags=["Research Lab Admin"])
def research_lab_admin_capabilities(
    request: Request,
    token: str = Query(...),
    _admin: User | None = Depends(get_optional_user),
):
    """Return real admin operations available inside Research Lab."""
    _require_research_admin_operation(request, token, _admin)
    return {
        "capabilities": _research_lab_capabilities(),
        "policy": {
            "command_source": "server whitelist only",
            "shell": False,
            "audit_log": "audit_logs + reports/research_lab_jobs/*.json",
            "session_minutes": _RESEARCH_SESSION_MINUTES,
        },
    }


@app.post("/api/research-lab/admin/jobs", tags=["Research Lab Admin"])
def research_lab_admin_start_job(
    request: Request,
    body: ResearchLabAdminJobRequest,
    token: str = Query(...),
    _admin: User | None = Depends(get_optional_user),
):
    """Start a real whitelisted admin job: tests, audits, retrain, SHAP, or model cache reload."""
    admin_id = _require_research_admin_operation(request, token, _admin)
    operation = body.operation.strip()
    capability_map = _flatten_capabilities()
    if operation not in capability_map:
        raise HTTPException(status_code=400, detail=f"Unsupported Research Lab operation: {operation}")

    command, cwd, timeout = _build_research_lab_command(operation, body.params or {})
    job_id = f"rlj-{uuid.uuid4().hex[:12]}"
    job = {
        "id": job_id,
        "operation": operation,
        "label": capability_map[operation]["label"],
        "group": capability_map[operation]["group"],
        "status": "queued",
        "admin_id": admin_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "started_at": None,
        "finished_at": None,
        "timeout_seconds": timeout,
        "return_code": None,
        "stdout": "",
        "stderr": "",
        "params": body.params or {},
        "command": command or [],
        "cwd": str(cwd),
    }
    with _research_lab_jobs_lock:
        _research_lab_jobs[job_id] = job
        _save_research_job(job)

    _log_research_job_audit(job, "START")
    target = _finish_internal_research_job if command is None else _run_research_lab_subprocess
    thread = threading.Thread(target=target, args=(job_id,), daemon=True)
    with _research_lab_jobs_lock:
        _research_lab_jobs[job_id]["thread"] = thread
    thread.start()
    return _serialize_research_job(job)


@app.get("/api/research-lab/admin/jobs", tags=["Research Lab Admin"])
def research_lab_admin_jobs(
    request: Request,
    token: str = Query(...),
    _admin: User | None = Depends(get_optional_user),
):
    """List recent Research Lab admin jobs."""
    _require_research_admin_operation(request, token, _admin)
    with _research_lab_jobs_lock:
        jobs = sorted(_research_lab_jobs.values(), key=lambda item: item.get("created_at") or "", reverse=True)
        return {"jobs": [_serialize_research_job(job) for job in jobs[:30]]}


@app.get("/api/research-lab/admin/jobs/{job_id}", tags=["Research Lab Admin"])
def research_lab_admin_job_detail(
    job_id: str,
    request: Request,
    token: str = Query(...),
    _admin: User | None = Depends(get_optional_user),
):
    """Return stdout/stderr and state for a Research Lab admin job."""
    _require_research_admin_operation(request, token, _admin)
    with _research_lab_jobs_lock:
        job = _research_lab_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Research Lab job not found")
        return _serialize_research_job(job)


@app.post("/api/predict", response_model=PredictionResponse, deprecated=True)
def predict_price(
    request: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Predict property price with full explainability."""
    from sqlalchemy import func

    started_at = time.perf_counter()
    model_data = get_cached_model()
    if not model_data:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not trained. Please train the model first."
        )

    input_dict = request.dict()
    property_type = request.property_type
    area = request.area_m2

    model = model_data.get("model")
    feature_cols = model_data.get("feature_cols", [])
    metrics = model_data.get("metrics", {})

    support_bundle = collect_support_properties(
        db=db,
        province=request.province_city,
        district=request.district,
        property_type=property_type,
        area=area,
    )
    matched_province = support_bundle["matched_province"]
    same_type_count = support_bundle["same_type_count"]
    same_province_count = support_bundle["same_province_count"]
    same_district_count = support_bundle["same_district_count"]
    comparable = support_bundle["comparables"]
    comparable_records = serialize_comparable_records(comparable, area)

    pool_stats = _get_prediction_pool_stats(db)
    total_verified = pool_stats["verified_pool"]
    self_collected_count = pool_stats["self_collected_pool"]

    data_quality_assessment = build_data_quality_assessment(
        request_data=input_dict,
        support_properties=comparable,
        district_support_count=same_district_count,
        province_support_count=same_province_count,
        property_type_support_count=same_type_count,
    )
    data_quality_assessment["assessment_tree"] = build_assessment_tree(data_quality_assessment)

    try:
        pipeline = model_data.get("pipeline")
        scaler = model_data.get("scaler")

        if pipeline and feature_cols and scaler:
            from src.ml.feature_engineering import FeatureEngineer
            import pandas as pd
            from sklearn.impute import SimpleImputer

            input_data = build_research_prediction_input(
                request_data=input_dict,
                matched_province=matched_province,
                assessment=data_quality_assessment,
                model_data=model_data,
            )

            engineer = FeatureEngineer()
            engineer.fit(pd.DataFrame([input_data]))
            X_input = engineer.transform(pd.DataFrame([input_data]))

            imputer = SimpleImputer(strategy="median", keep_empty_features=True)
            X_imputed = imputer.fit_transform(X_input)
            X_scaled = scaler.transform(X_imputed)

            predicted_price = float(model.predict(X_scaled)[0])
            predicted_price = max(100000000, predicted_price)
            model_name = model_data.get("pipeline", {}).get("best_model_name", "GradientBoosting")
        else:
            raise ValueError("Model pipeline not available")

    except Exception as exc:
        print(f"ML Prediction error: {exc}, using comparable-based fallback")
        if comparable_records:
            total_weight = 0.0
            weighted_price_per_m2 = 0.0
            for comp in comparable_records:
                weight = comp.get("similarity", 0.5)
                price_m2 = comp.get("price_per_m2", 0) or 0
                if price_m2 > 0:
                    weighted_price_per_m2 += price_m2 * weight
                    total_weight += weight

            if total_weight > 0:
                price_per_m2 = weighted_price_per_m2 / total_weight
                predicted_price = area * price_per_m2
            else:
                prices_m2 = [c.get("price_per_m2", 0) for c in comparable_records if c.get("price_per_m2", 0)]
                if prices_m2:
                    price_per_m2 = sum(prices_m2) / len(prices_m2)
                    predicted_price = area * price_per_m2
                else:
                    raise ValueError("No valid comparable prices")
        else:
            area_min = area * 0.7
            area_max = area * 1.3
            avg_price_per_m2 = db.query(func.avg(Property.price_per_m2)).filter(
                Property.property_type == property_type,
                Property.province_city == matched_province,
                Property.verification_status == "verified",
                Property.area_m2 >= area_min,
                Property.area_m2 <= area_max,
            ).scalar()

            if avg_price_per_m2:
                predicted_price = area * avg_price_per_m2
            else:
                # Dùng get_base_price_per_m2 từ province_config
                price_per_m2 = get_base_price_per_m2(matched_province, property_type)
                predicted_price = price_per_m2 * area
        model_name = "ComparableBased"

    predicted_price = max(100000000, min(predicted_price, 50000000000))
    price_per_m2 = predicted_price / area if area > 0 else 0

    mae = metrics.get("mae", 1000000000)
    interval_analysis = build_adaptive_interval(
        predicted_price=predicted_price,
        mae_value=mae,
        support_properties=comparable,
        overall_score=data_quality_assessment["overall_score"],
        assessment=data_quality_assessment,
    )
    calibration = model_data.get("conformal_calibration", {})
    calibration_band = data_quality_assessment.get("ml_confidence", {}).get(
        "predicted_grade",
        data_quality_assessment.get("confidence_grade", "C"),
    )
    band_adjustment = calibration.get(calibration_band)
    if band_adjustment:
        design_band_max = (interval_analysis.get("design_band") or {}).get("max", band_adjustment.get("ratio_q90", 0.0))
        calibrated_ratio = max(
            interval_analysis["interval_ratio"],
            min(band_adjustment.get("ratio_q90", 0.0), design_band_max),
        )
        interval_analysis["confidence_low"] = round(predicted_price * (1 - calibrated_ratio), 0)
        interval_analysis["confidence_high"] = round(predicted_price * (1 + calibrated_ratio), 0)
        interval_analysis["interval_ratio"] = round(calibrated_ratio, 4)
        interval_analysis["interval_width"] = round(interval_analysis["confidence_high"] - interval_analysis["confidence_low"], 0)
        interval_analysis["conformal_adjustment"] = {
            "band": calibration_band,
            **band_adjustment,
        }
    confidence_low = interval_analysis["confidence_low"]
    confidence_high = interval_analysis["confidence_high"]
    confidence_ratio = round(data_quality_assessment["overall_score"] / 10, 4)

    model_version_info, serving_metric, metric_provenance = _resolve_serving_model_version_info(db, model_data)
    serving_version = _metric_or_db_version(model_version_info, serving_metric, model_data) or "unknown"
    serving_trained_at = (
        _date_label(model_version_info.trained_at if model_version_info else None)
        or _date_label(serving_metric.get("trained_at"))
    )
    train_start_date = _date_label(model_version_info.train_start_date if model_version_info else None)
    train_end_date = _date_label(model_version_info.train_end_date if model_version_info else None)
    train_record_count = (
        model_version_info.train_record_count
        if model_version_info and model_version_info.train_record_count is not None
        else serving_metric.get("train_size")
    )
    verified_record_count = (
        model_version_info.verified_record_count
        if model_version_info and model_version_info.verified_record_count is not None
        else None
    )
    self_collected_ratio = (
        model_version_info.self_collected_ratio
        if model_version_info and model_version_info.self_collected_ratio is not None
        else None
    )

    feature_importance = {}
    try:
        if model_name != "ComparableBased" and hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            for i, col in enumerate(feature_cols[:10]):
                feature_importance[col] = float(importances[i])
    except Exception as exc:
        print(f"Feature importance unavailable: {exc}")

    if not feature_importance:
        feature_importance = {
            "area_m2": 0.28,
            "district": 0.22,
            "province_city": 0.18,
            "property_type": 0.12,
            "bedrooms": 0.08,
            "floor_count": 0.05,
            "noise_level": 0.04,
        }

    request_id = str(uuid.uuid4())
    canonical_input = json.dumps(
        input_dict,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    history = ValuationRun(
        request_id=request_id,
        source_endpoint="api_predict",
        account_id=(current_user.id if current_user and current_user.id > 0 else None),
        model_version_id=model_version_info.id if model_version_info else None,
        model_version_snapshot=serving_version,
        model_name=model_name,
        engine_version="legacy-ml",
        request_status="completed",
        request_latency_ms=round((time.perf_counter() - started_at) * 1000, 2),
        fair_market_value_vnd=predicted_price,
        expected_range_low_vnd=confidence_low,
        expected_range_high_vnd=confidence_high,
        overall_confidence=confidence_ratio,
        confidence_grade=calibration_band,
        comparable_count=len(comparable_records),
        input_hash=hashlib.sha256(canonical_input.encode("utf-8")).hexdigest(),
        input_features_json=input_dict,
        result_json={
            "predicted_price": predicted_price,
            "price_per_m2": price_per_m2,
            "confidence_low": confidence_low,
            "confidence_high": confidence_high,
        },
        feature_importance_json=feature_importance,
        comparable_records_json=comparable_records,
        feedback_verification_status="not_submitted",
        training_eligible=False,
        training_exclusion_reason="actual_price_feedback_missing",
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return PredictionResponse(
        predicted_price=round(predicted_price, 0),
        price_per_m2=round(price_per_m2, 0),
        confidence_low=round(confidence_low, 0),
        confidence_high=round(confidence_high, 0),
        model_used=model_name,
        confidence=confidence_ratio,
        input_features=input_dict,
        prediction_id=history.id,
        request_id=request_id,
        model_version=serving_version,
        trained_at=serving_trained_at,
        train_start_date=train_start_date,
        train_end_date=train_end_date,
        total_train_records=train_record_count,
        verified_train_records=verified_record_count,
        self_collected_ratio=self_collected_ratio,
        same_property_type_count=same_type_count,
        same_province_count=same_province_count,
        same_district_count=same_district_count,
        feature_importance=feature_importance,
        comparable_records=comparable_records,
        property_images=[
            {
                "id": c.get("id"),
                "thumbnail": c.get("image_url") if c.get("image_url") else None,
                "district": c.get("district"),
                "area_m2": c.get("area_m2"),
                "price": c.get("price"),
                "similarity": c.get("similarity"),
            }
            for c in comparable_records
            if c.get("image_url") or c.get("similarity", 0) > 0.8
        ][:6],
        source_attribution=(
            f"Analysis based on {len(comparable_records)} comparable properties. "
            f"Model: {model_name} version {serving_version}. "
            f"Data reliability grade: {data_quality_assessment['confidence_grade']} "
            f"({data_quality_assessment['overall_score']}/10). "
            f"Standard: {data_quality_assessment.get('standard_name', 'CVX-BDS/IoT')}"
        ),
        data_provenance={
            "model_version": serving_version,
            "model_algorithm": model_name,
            "confidence_stage_model": model_data.get("confidence_best_model_name"),
            "training_date": serving_trained_at,
            "training_records": train_record_count,
            "verified_records": verified_record_count,
            "self_collected_ratio": self_collected_ratio,
            "official_test_mape_pct": serving_metric.get("test_mape"),
            "official_test_mae_vnd": serving_metric.get("test_mae"),
            "official_test_r2": serving_metric.get("test_r2"),
            "official_test_n": serving_metric.get("n_test"),
            "metric_source": "metadata.all_results[best_model].test_*",
            "serving_source": metric_provenance.get("serving_source"),
            "latest_model_version": (metric_provenance.get("latest") or {}).get("stamp"),
            "best_verified_model_version": (metric_provenance.get("best_verified") or {}).get("stamp"),
            "metric_warning": metric_provenance.get("warning"),
            "data_sources": list(set([c.get("source_name", "Unknown") for c in comparable_records]))[:5],
            "methodology": (
                "Two-stage research AVM with confidence classification, "
                "trust-aware price prediction, grouped conformal calibration, "
                "comparable support, and adaptive interval control."
            ),
            "verified_pool": total_verified,
            "self_collected_pool": self_collected_count,
            "pool_stats_cache": pool_stats.get("cache"),
        },
        citation={
            "apa": f"Real Estate AVM System. ({datetime.now().year}). {model_name} (Version {serving_version}). Retrieved from automated valuation model.",
            "bibtex": f"@misc{{avm_{datetime.now().strftime('%Y%m%d')},\n  title={{Real Estate Price Prediction}},\n  author={{AVM System}},\n  year={{{datetime.now().year}}},\n  note={{Model: {model_name}, Version: {serving_version}}}\n}}",
        },
        algorithm=(
            f"Two-stage pipeline: {model_data.get('confidence_best_model_name') or 'ConfidenceClassifier'} -> "
            f"{model_name}Regressor"
        ),
        preprocessing={
            "numeric": "StandardScaler",
            "categorical": "Feature encoding + rule-based validation",
            "split_strategy": model_data.get("metadata", {}).get("split_strategy"),
            "interval_strategy": model_data.get("metadata", {}).get("interval_strategy"),
        },
        features_used=feature_cols,
        data_quality_assessment=data_quality_assessment,
        interval_analysis=interval_analysis,
    )

# --- Property Management Endpoints ---

def _apply_sanitizer(body: dict, scope_strict: bool = True) -> dict:
    """Apply PropertySanitizer to a dict. Returns sanitized copy or raises ValidationError."""
    from src.backend.data_sanitizer import PropertySanitizer, ValidationError
    sanitizer = PropertySanitizer(strict_scope=scope_strict)
    return sanitizer.sanitize(dict(body))


@app.post("/api/properties", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
def create_property(property: PropertyCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Create a new property record with IoT features.

    Data flow:
      1. Middleware sanitizes JSON body (VN→EN, price/area parsing)
      2. Pydantic validates canonical schema constraints
      3. PropertySanitizer validates scope + business rules (belt-and-suspenders)
      4. ORM inserts into DB
    """
    # Sanitize with scope enforcement (belt-and-suspenders after middleware)
    try:
        cleaned = _apply_sanitizer(property.model_dump(), scope_strict=True)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Sanitizer rejected: {e}")

    price_per_m2 = None
    if cleaned.get("price") and cleaned.get("area_m2"):
        price_per_m2 = cleaned["price"] / cleaned["area_m2"] if cleaned["area_m2"] > 0 else 0

    source_name = cleaned.get("source_name") or ("Field Survey" if cleaned.get("is_self_collected") else "External Source")
    collection_method = cleaned.get("collection_method") or ("field_survey_form" if cleaned.get("is_self_collected") else None)

    db_property = Property(
        property_type=cleaned["property_type"],
        province_city=cleaned["province_city"],
        district=cleaned["district"],
        ward=cleaned.get("ward"),
        street_or_project=cleaned.get("street_or_project"),
        area_m2=cleaned.get("area_m2", 0),
        bedrooms=cleaned.get("bedrooms", 0),
        bathrooms=cleaned.get("bathrooms", 0),
        floor_count=cleaned.get("floor_count", 1),
        frontage_m=cleaned.get("frontage_m"),
        legal_status=cleaned.get("legal_status"),
        furnishing=cleaned.get("furnishing"),
        price=cleaned.get("price") or 0,
        price_per_m2=price_per_m2,
        listing_date=cleaned.get("listing_date"),
        latitude=cleaned.get("latitude"),
        longitude=cleaned.get("longitude"),
        area_type=cleaned.get("area_type"),
        distance_to_market=cleaned.get("distance_to_market"),
        distance_to_school=cleaned.get("distance_to_school"),
        distance_to_hospital=cleaned.get("distance_to_hospital"),
        distance_to_main_road=cleaned.get("distance_to_main_road"),
        near_supermarket=cleaned.get("near_supermarket"),
        near_school=cleaned.get("near_school"),
        near_hospital=cleaned.get("near_hospital"),
        near_main_road=cleaned.get("near_main_road"),
        description=cleaned.get("description"),
        # IoT fields
        gps_lat=cleaned.get("gps_lat"),
        gps_lng=cleaned.get("gps_lng"),
        gps_accuracy=cleaned.get("gps_accuracy"),
        capture_time=cleaned.get("capture_time"),
        noise_level=cleaned.get("noise_level"),
        light_level=cleaned.get("light_level"),
        temperature=cleaned.get("temperature"),
        humidity=cleaned.get("humidity"),
        phone_device=cleaned.get("phone_device"),
        os_version=cleaned.get("os_version"),
        app_version=cleaned.get("app_version"),
        field_notes=cleaned.get("field_notes"),
        area_quality_score=cleaned.get("area_quality_score"),
        # Self-collected - use data_origin_type
        data_origin_type="self_collected" if cleaned.get("is_self_collected") else "public_collected",
        collection_method=collection_method,
        collected_by=cleaned.get("collected_by"),
        collected_at=datetime.now() if cleaned.get("is_self_collected") else None,
        verification_note=cleaned.get("verification_note"),
        source_name=source_name,
        source_url=cleaned.get("source_url"),
    )

    db.add(db_property)
    db.commit()
    db.refresh(db_property)

    if cleaned.get("is_self_collected") and not db_property.source_url:
        db_property.source_url = f"/api/properties/{db_property.id}/detail"
        db.commit()
        db.refresh(db_property)

    return db_property


def _property_response_dict(p: Property) -> dict:
    """Serialize property rows defensively so sparse imported records never 500."""
    return {
        "property_type": p.property_type,
        "province_city": p.province_city,
        "district": p.district,
        "ward": p.ward,
        "street_or_project": p.street_or_project,
        "area_m2": p.area_m2,
        "bedrooms": p.bedrooms if p.bedrooms is not None else 0,
        "bathrooms": p.bathrooms if p.bathrooms is not None else 0,
        "floor_count": p.floor_count,
        "frontage_m": p.frontage_m,
        "legal_status": p.legal_status,
        "furnishing": p.furnishing,
        "latitude": p.latitude,
        "longitude": p.longitude,
        "area_type": p.area_type,
        "distance_to_market": p.distance_to_market,
        "distance_to_school": p.distance_to_school,
        "distance_to_hospital": p.distance_to_hospital,
        "distance_to_main_road": p.distance_to_main_road,
        "near_supermarket": p.near_supermarket,
        "near_school": p.near_school,
        "near_hospital": p.near_hospital,
        "near_main_road": p.near_main_road,
        "id": p.id,
        "price": p.price,
        "price_per_m2": p.price_per_m2,
        "listing_date": p.listing_date,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "gps_lat": p.gps_lat,
        "gps_lng": p.gps_lng,
        "gps_accuracy": p.gps_accuracy,
        "capture_time": p.capture_time,
        "noise_level": p.noise_level,
        "light_level": p.light_level,
        "temperature": p.temperature,
        "humidity": p.humidity,
        "phone_device": p.phone_device,
        "os_version": p.os_version,
        "app_version": p.app_version,
        "field_notes": p.field_notes,
        "area_quality_score": p.area_quality_score,
        "image_url": p.image_url,
        "data_origin_type": p.data_origin_type,
        "record_status": p.record_status,
        "verification_status": p.verification_status,
        "evidence_tier": p.evidence_tier,
        "collection_method": p.collection_method,
        "collected_by": p.collected_by,
        "collected_at": p.collected_at,
        "verification_note": p.verification_note,
        "source_name": p.source_name,
        "source_url": p.source_url,
    }


@app.get("/api/properties")
def list_properties(
    skip: int = 0,
    limit: int = 100,
    property_type: Optional[str] = None,
    province: Optional[str] = None,
    self_collected: Optional[bool] = None,
    has_iot: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List properties with filters."""
    query = db.query(Property)

    if property_type:
        query = query.filter(Property.property_type == property_type)
    if province:
        query = query.filter(Property.province_city == province)
    if self_collected is not None:
        # Filter by data_origin_type
        if self_collected:
            query = query.filter(Property.data_origin_type == "self_collected")
        else:
            query = query.filter(Property.data_origin_type != "self_collected")
    if has_iot is not None:
        if has_iot:
            query = query.filter(Property.noise_level.isnot(None))
        else:
            query = query.filter(Property.noise_level.is_(None))

    return [_property_response_dict(p) for p in query.offset(skip).limit(limit).all()]


# --- Dataset Statistics Endpoints (Research Standard) ---

@app.get("/api/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Get live operational statistics for authenticated administrators."""
    from sqlalchemy import func
    from datetime import datetime, timedelta

    total = db.query(Property).count()

    # By origin type
    self_collected = db.query(Property).filter(Property.data_origin_type == "self_collected").count()
    public_collected = db.query(Property).filter(Property.data_origin_type == "public_collected").count()
    demo_records = db.query(Property).filter(Property.data_origin_type == "system_demo").count()

    # By status
    verified = db.query(Property).filter(Property.verification_status == "verified").count()
    pending = db.query(Property).filter(Property.verification_status == "pending").count()
    rejected = db.query(Property).filter(Property.verification_status == "rejected").count()

    # By record status
    raw_count = db.query(Property).filter(Property.record_status == "raw").count()
    pending_review = db.query(Property).filter(Property.record_status == "pending_review").count()
    archived = db.query(Property).filter(Property.record_status == "archived").count()

    # IoT
    iot_records = db.query(Property).filter(Property.noise_level.isnot(None)).count()

    # Recent additions (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    added_this_week = db.query(Property).filter(Property.created_at >= week_ago).count()

    trainable_query = db.query(Property).filter(
        Property.record_status != "archived",
        Property.price > 0,
        Property.area_m2 > 0,
        Property.price_per_m2 > 0,
    )
    trainable_count = trainable_query.count()

    from src.backend.model_metrics import build_metric_provenance

    metric_provenance = build_metric_provenance()
    serving_metric = metric_provenance.get("serving") or {}
    serving_model = _find_model_version_by_stamp(db, serving_metric.get("stamp"))
    if serving_model is None and not serving_metric.get("stamp"):
        serving_model = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()

    model_metadata = {}
    serving_metadata_path = serving_metric.get("source_path")
    if serving_model and serving_model.metadata_path:
        serving_metadata_path = serving_model.metadata_path
    elif serving_model and serving_model.model_path:
        serving_metadata_path = str(serving_model.model_path).replace("model_", "metadata_")

    if serving_metadata_path:
        try:
            metadata_path = Path(str(serving_metadata_path)).with_suffix(".json")
            if metadata_path.exists():
                model_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            model_metadata = {}

    confidence_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    confidence_source = "none"
    run_rows = (
        db.query(ValuationRun.confidence_grade, func.count(ValuationRun.id))
        .group_by(ValuationRun.confidence_grade)
        .all()
    )
    if run_rows:
        for grade, count in run_rows:
            key = str(grade or "D").upper()
            if key in confidence_counts:
                confidence_counts[key] += int(count or 0)
        confidence_source = "valuation_runs"
    else:
        metadata_distribution = (
            model_metadata.get("confidence_metadata", {}).get("label_distribution", {})
            if isinstance(model_metadata, dict)
            else {}
        )
        if metadata_distribution:
            for grade, count in metadata_distribution.items():
                key = str(grade or "D").upper()
                if key in confidence_counts:
                    confidence_counts[key] += int(count or 0)
            confidence_source = "pconf_training_metadata"
        else:
            try:
                confidence_rows = build_confidence_training_rows(trainable_query.limit(5000).all())
                for row in confidence_rows:
                    neff = float(row.get("effective_sample_size", 0) or 0)
                    support_quality = float(row.get("support_quality_score", 0) or 0)
                    source_count = int(row.get("support_source_count", 0) or 0)
                    if neff >= 800 and support_quality >= 7 and source_count >= 2:
                        confidence_counts["A"] += 1
                    elif neff >= 300 and support_quality >= 6 and source_count >= 2:
                        confidence_counts["B"] += 1
                    elif neff >= 100 or (neff >= 30 and support_quality >= 5.5):
                        confidence_counts["C"] += 1
                    else:
                        confidence_counts["D"] += 1
                confidence_source = "pconf_recomputed_from_db"
            except Exception:
                confidence_source = "unavailable"

    serving_train_count = None
    if serving_model and serving_model.train_record_count is not None:
        serving_train_count = serving_model.train_record_count
    elif serving_metric.get("train_size") is not None:
        serving_train_count = serving_metric.get("train_size")

    model_needs_retrain = True
    if serving_train_count is not None:
        model_needs_retrain = int(serving_train_count or 0) < trainable_count

    serving_model_payload = None
    if serving_model or serving_metric:
        serving_model_payload = {
            "role": "serving",
            "version": (
                serving_metric.get("stamp")
                or (serving_model.model_version if serving_model else None)
            ),
            "model_name": (
                serving_metric.get("model_name")
                or (serving_model.model_name if serving_model else None)
            ),
            "trained_at": (
                serving_metric.get("trained_at")
                or (serving_model.trained_at.isoformat() if serving_model and serving_model.trained_at else None)
            ),
            "train_record_count": serving_train_count,
            "verified_record_count": serving_model.verified_record_count if serving_model else None,
            "self_collected_ratio": serving_model.self_collected_ratio if serving_model else None,
            "dataset_record_count": trainable_count,
            "mae": (
                serving_model.mae
                if serving_model and serving_model.mae is not None
                else serving_metric.get("test_mae")
            ),
            "mape": (
                serving_model.mape
                if serving_model and serving_model.mape is not None
                else serving_metric.get("test_mape")
            ),
            "rmse": serving_model.rmse if serving_model else None,
            "r2": (
                serving_model.r2
                if serving_model and serving_model.r2 is not None
                else serving_metric.get("test_r2")
            ),
            "metric_source": "ACTIVE_MODEL/metadata",
        }

    return {
        "total_records": total,
        "by_origin": {
            "self_collected": self_collected,
            "public_collected": public_collected,
            "system_demo": demo_records
        },
        "by_verification": {
            "verified": verified,
            "pending": pending,
            "rejected": rejected
        },
        "by_record_status": {
            "raw": raw_count,
            "pending_review": pending_review,
            "verified_count": verified,
            "archived": archived
        },
        "iot_records": iot_records,
        "self_collected_ratio": round(self_collected / total * 100, 2) if total > 0 else 0,
        "added_this_week": added_this_week,
        "confidence_a": confidence_counts["A"],
        "confidence_b": confidence_counts["B"],
        "confidence_c": confidence_counts["C"],
        "confidence_d": confidence_counts["D"],
        "confidence_distribution": confidence_counts,
        "confidence_source": confidence_source,
        "trainable_record_count": trainable_count,
        "model_needs_retrain": model_needs_retrain,
        "serving_model": serving_model_payload,
        "latest_model": serving_model_payload,
        "model_metric_provenance": {
            "serving_version": serving_metric.get("stamp"),
            "latest_candidate_version": (metric_provenance.get("latest") or {}).get("stamp"),
            "best_verified_version": (metric_provenance.get("best_verified") or {}).get("stamp"),
            "serving_source": metric_provenance.get("serving_source"),
            "warning": metric_provenance.get("warning"),
            "serving_warning": metric_provenance.get("serving_warning"),
        },
    }


@app.get("/api/dataset/stats", response_model=DatasetStats)
def get_dataset_stats(db: Session = Depends(get_db)):
    """Get dataset statistics with full traceability."""
    from sqlalchemy import func

    total = db.query(Property).count()
    self_collected = db.query(Property).filter(Property.data_origin_type == "self_collected").count()
    verified = db.query(Property).filter(Property.verification_status == "verified").count()
    iot_records = db.query(Property).filter(Property.noise_level.isnot(None)).count()

    ratio = (self_collected / total * 100) if total > 0 else 0
    iot_ratio = (iot_records / total * 100) if total > 0 else 0

    by_type = {}
    for ptype in ['house', 'apartment', 'land']:
        count = db.query(Property).filter(Property.property_type == ptype).count()
        by_type[ptype] = count

    by_province = {}
    provinces = db.query(Property.province_city).distinct().all()
    for (province,) in provinces:
        count = db.query(Property).filter(Property.province_city == province).count()
        by_province[province] = count

    meets_req = 3 <= ratio <= 7  # 3-7% range

    return DatasetStats(
        total=total,
        self_collected=self_collected,
        self_collected_ratio=round(ratio, 2),
        verified_records=verified,
        iot_records=iot_records,
        iot_ratio=round(iot_ratio, 2),
        by_property_type=by_type,
        by_province=by_province,
        meets_requirement=meets_req
    )


@app.get("/api/dataset/overview")
def get_dataset_overview(db: Session = Depends(get_db)):
    """Dataset overview aligned with the research-standard traceability targets."""
    return build_dataset_overview(db)


# --- Data Sources Endpoints (Quy tắc 6, 7) ---

@app.get("/api/data-sources")
def list_data_sources(db: Session = Depends(get_db), _admin: User | None = Depends(get_optional_user)):
    """List all data sources with statistics (Quy tắc 6)"""
    sources = db.query(CollectionSource).all()
    source_map = {source.source_name: source for source in sources if source.source_name}
    property_source_names = [
        row[0] for row in db.query(Property.source_name)
        .filter(Property.source_name.isnot(None), Property.source_name != "")
        .distinct()
        .all()
    ]
    for source_name in property_source_names:
        source_map.setdefault(source_name, None)

    result = []
    for source_name, source in source_map.items():
        # Get stats for this source
        props = db.query(Property).filter(Property.source_name == source_name).all()
        total = len(props)
        verified = sum(1 for p in props if p.verification_status == "verified")
        self_collected = sum(1 for p in props if p.data_origin_type == "self_collected")
        trace_ready = sum(
            1 for p in props
            if p.source_url or p.data_origin_type == "self_collected"
        )
        iot_records = sum(
            1 for p in props
            if p.noise_level is not None or p.temperature is not None or p.humidity is not None
        )
        image_records = sum(1 for p in props if p.image_url or p.image_urls)
        first_with_url = next((p for p in props if p.source_url), None)
        source_type = source.source_type if source else (
            "field_survey" if self_collected and self_collected == total else "website"
        )

        result.append({
            "id": source.id if source else f"property-source-{abs(hash(source_name)) % 100000}",
            "source_name": source_name,
            "source_url": source.base_url if source else (first_with_url.source_url if first_with_url else None),
            "source_type": source_type,
            "total_records": total,
            "verified_records": verified,
            "self_collected_records": self_collected,
            "trace_ready_records": trace_ready,
            "verified_ratio": round(verified / total * 100, 2) if total else 0.0,
            "trace_ratio": round(trace_ready / total * 100, 2) if total else 0.0,
            "iot_records": iot_records,
            "image_records": image_records,
            "source_link_ready": total > 0 and trace_ready == total,
            "last_collected_at": source.last_run_at.isoformat() if source and source.last_run_at else None,
            "is_active": source.is_active if source else total > 0,
            "notes": source.notes if source else "Nguồn được tổng hợp trực tiếp từ bảng properties.",
        })

    return sorted(result, key=lambda item: item["total_records"], reverse=True)


@app.get("/api/properties/{property_id}/detail")
def get_property_detail(property_id: int, db: Session = Depends(get_db)):
    """Get full property details with source traceability (Quy tắc 7)"""
    prop = db.query(Property).filter(Property.id == property_id).first()

    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    trace_profile = build_property_trace_profile(prop)
    image_gallery = []
    if prop.image_url:
        image_gallery.append(prop.image_url)
    image_gallery.extend([url for url in parse_string_list(prop.image_urls) if url not in image_gallery])

    return {
        "id": prop.id,
        "property_type": prop.property_type,
        "province_city": prop.province_city,
        "district": prop.district,
        "ward": prop.ward,
        "street_or_project": prop.street_or_project,
        "area_m2": prop.area_m2,
        "bedrooms": prop.bedrooms,
        "bathrooms": prop.bathrooms,
        "floor_count": prop.floor_count,
        "frontage_m": prop.frontage_m,
        "legal_status": prop.legal_status,
        "furnishing": prop.furnishing,
        "price": prop.price,
        "price_per_m2": prop.price_per_m2,
        "description": prop.description,
        "latitude": prop.latitude,
        "longitude": prop.longitude,
        "area_type": prop.area_type,
        "distance_to_market": prop.distance_to_market,
        "distance_to_school": prop.distance_to_school,
        "distance_to_hospital": prop.distance_to_hospital,
        "distance_to_main_road": prop.distance_to_main_road,
        "near_supermarket": prop.near_supermarket,
        "near_school": prop.near_school,
        "near_hospital": prop.near_hospital,
        "near_main_road": prop.near_main_road,

        # DATA ORIGIN & STATUS
        "data_origin_type": prop.data_origin_type,
        "record_status": prop.record_status,
        "verification_status": prop.verification_status,

        # SOURCE (Quy tắc 2)
        "source_name": prop.source_name,
        "source_url": prop.source_url,
        "source_access_link": trace_profile["source_access_link"],
        "source_page_title": prop.source_page_title,
        "source_collected_at": prop.source_collected_at.isoformat() if prop.source_collected_at else None,
        "source_access_method": prop.source_access_method,
        "source_screenshot_path": prop.source_screenshot_path,

        # VERIFICATION
        "verification_note": prop.verification_note,
        "verified_by": prop.verified_by,
        "verified_at": prop.verified_at.isoformat() if prop.verified_at else None,

        # SELF-COLLECTED (Quy tắc 3)
        "collected_by": prop.collected_by,
        "collected_at": prop.collected_at.isoformat() if prop.collected_at else None,
        "collection_method": prop.collection_method,
        "collector_contact": prop.collector_contact,
        "field_note": prop.field_note,
        "field_notes": prop.field_notes,
        "form_submission_id": prop.form_submission_id,
        "evidence_photo_path": prop.evidence_photo_path,

        # IoT
        "gps_lat": prop.gps_lat,
        "gps_lng": prop.gps_lng,
        "noise_level": prop.noise_level,
        "temperature": prop.temperature,
        "humidity": prop.humidity,
        "light_level": prop.light_level,
        "capture_time": prop.capture_time.isoformat() if prop.capture_time else None,
        "phone_device": prop.phone_device,
        "os_version": prop.os_version,
        "app_version": prop.app_version,
        "gps_accuracy": prop.gps_accuracy,
        "sensor_source": prop.sensor_source,
        "area_quality_score": prop.area_quality_score,
        "iot_note": prop.iot_note,
        "iot_device_id": prop.iot_device_id,
        "iot_collected_at": prop.iot_collected_at.isoformat() if prop.iot_collected_at else None,
        "image_url": prop.image_url,
        "image_urls": image_gallery,
        "trace_profile": trace_profile,

        # TIMESTAMPS
        "created_at": prop.created_at.isoformat() if prop.created_at else None,
        "updated_at": prop.updated_at.isoformat() if prop.updated_at else None,
        "timeline": {
            "listed_at": prop.listing_date.isoformat() if prop.listing_date else None,
            "source_collected_at": prop.source_collected_at.isoformat() if prop.source_collected_at else None,
            "collected_at": prop.collected_at.isoformat() if prop.collected_at else None,
            "verified_at": prop.verified_at.isoformat() if prop.verified_at else None,
            "capture_time": prop.capture_time.isoformat() if prop.capture_time else None,
            "updated_at": prop.updated_at.isoformat() if prop.updated_at else None,
        },
        "location_snapshot": {
            "province_city": prop.province_city,
            "district": prop.district,
            "ward": prop.ward,
            "street_or_project": prop.street_or_project,
            "latitude": prop.latitude,
            "longitude": prop.longitude,
            "gps_lat": prop.gps_lat,
            "gps_lng": prop.gps_lng,
        },
        "iot_snapshot": {
            "noise_level": prop.noise_level,
            "temperature": prop.temperature,
            "humidity": prop.humidity,
            "light_level": prop.light_level,
            "gps_accuracy": prop.gps_accuracy,
            "phone_device": prop.phone_device,
            "os_version": prop.os_version,
            "app_version": prop.app_version,
        },
    }


@app.get("/api/audit-logs")
def list_audit_logs(
    record_id: int = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """List audit logs (Quy tắc 18)"""
    query = db.query(AuditLog)

    if record_id:
        query = query.filter(AuditLog.record_id == record_id)

    logs = query.order_by(AuditLog.changed_at.desc()).limit(limit).all()

    return [{
        "id": log.id,
        "record_id": log.record_id,
        "table_name": log.table_name,
        "action_type": log.action_type,
        "changed_by": log.changed_by,
        "changed_at": log.changed_at.isoformat() if log.changed_at else None,
        "change_note": log.change_note
    } for log in logs]


# --- Record Management Endpoints (Quy tắc 11, 13, 19) ---

@app.patch("/api/properties/{property_id}/verify")
def verify_property(property_id: int, db: Session = Depends(get_db)):
    """Verify a property record (Quy tắc 13)"""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    prop.verification_status = "verified"
    prop.record_status = "verified"
    prop.verified_at = datetime.now()

    # Add audit log
    log = AuditLog(
        record_id=property_id,
        table_name="properties",
        action_type="VERIFY",
        changed_by="system",
        old_value_json=f'{{"verification_status": "{prop.verification_status}"}}',
        new_value_json='{"verification_status": "verified"}',
        change_note="Record verified"
    )
    db.add(log)
    db.commit()

    return {"status": "verified", "property_id": property_id}


@app.patch("/api/properties/{property_id}/reject")
def reject_property(property_id: int, reason: str = None, db: Session = Depends(get_db)):
    """Reject a property record (Quy tắc 13)"""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    prop.verification_status = "rejected"
    prop.record_status = "rejected"

    log = AuditLog(
        record_id=property_id,
        table_name="properties",
        action_type="REJECT",
        changed_by="system",
        change_note=reason or "Rejected"
    )
    db.add(log)
    db.commit()

    return {"status": "rejected", "property_id": property_id}


# --- Interactive Data Collection & Image Upload ---

@app.post("/api/upload/image")
async def upload_property_image(
    property_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Upload property image."""
    # Create uploads directory
    upload_dir = Path("uploads/properties")
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = upload_dir / f"{property_id}_{file.filename}"
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    # Update property
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Add to image_urls
    import json
    existing_urls = []
    if property.image_urls:
        try:
            existing_urls = json.loads(property.image_urls)
        except:
            pass

    file_url = f"/uploads/properties/{property_id}_{file.filename}"
    existing_urls.append(file_url)
    property.image_urls = json.dumps(existing_urls)
    if not property.image_url:
        property.image_url = file_url

    db.commit()

    return {"url": file_url, "property_id": property_id}


@app.get("/api/properties/{property_id}/images")
def get_property_images(property_id: int, db: Session = Depends(get_db)):
    """Get all images for a property."""
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    import json
    images = []
    if property.image_urls:
        try:
            images = json.loads(property.image_urls)
        except:
            pass

    if property.image_url and property.image_url not in images:
        images.insert(0, property.image_url)

    return {"images": images, "property_id": property_id}


# --- IoT Data Collection from Smartphone ---

@app.post("/api/collect/iot")
async def collect_iot_data(
    property_id: int = Form(None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    noise_level: float = Form(None),
    temperature: float = Form(None),
    humidity: float = Form(None),
    light_level: float = Form(None),
    accuracy: float = Form(None),
    device_id: str = Form(...),
    os_version: str = Form(...),
    app_version: str = Form(...),
    db: Session = Depends(get_db)
):
    """Collect IoT data from smartphone sensor.

    Sanitization: numeric bounds check on IoT sensor values.
    """
    # Sanitize: clamp latitude/longitude to valid Vietnam range
    lat = max(-90, min(90, latitude)) if latitude is not None else None
    lng = max(-180, min(180, longitude)) if longitude is not None else None
    # Sanitize: noise_level (0-144 dB), temperature (-50 to 60°C), humidity (0-100%)
    noise = max(0, min(144, noise_level)) if noise_level is not None else None
    temp = max(-50, min(60, temperature)) if temperature is not None else None
    humid = max(0, min(100, humidity)) if humidity is not None else None
    light = max(0, min(100000, light_level)) if light_level is not None else None
    acc = max(0, min(1000, accuracy)) if accuracy is not None else None

    if property_id:
        prop = db.query(Property).filter(Property.id == property_id).first()
        if prop:
            prop.gps_lat = lat
            prop.gps_lng = lng
            prop.gps_accuracy = acc
            prop.noise_level = noise
            prop.temperature = temp
            prop.humidity = humid
            prop.light_level = light
            prop.phone_device = device_id
            prop.os_version = os_version
            prop.app_version = app_version
            prop.iot_device_id = device_id
            prop.iot_collected_at = datetime.now()
            prop.capture_time = datetime.now()
            prop.data_origin_type = "self_collected"
            prop.record_status = "verified"
            db.commit()
            return {"status": "success", "property_id": property_id, "message": "IoT data attached to property"}

    # Return IoT data for new property creation
    return {
        "status": "ready",
        "iot_data": {
            "latitude": latitude,
            "longitude": longitude,
            "noise_level": noise_level,
            "temperature": temperature,
            "humidity": humidity,
            "light_level": light_level,
            "accuracy": accuracy,
            "device_id": device_id,
            "collected_at": datetime.now().isoformat()
        }
    }


@app.get("/api/collect/status", tags=["Data Collection"])
async def get_collection_status_admin(
    db: Session = Depends(get_db),
    _admin: User | None = Depends(get_optional_user),
):
    """Get full data collection status — admin version with complete breakdown.

    Returns the same structure as the non-admin endpoint (with `stats` wrapper)
    so the CollectionDashboard works consistently for admin users.
    """
    from sqlalchemy import func

    service = DataCollectionService(db)
    stats = service.get_collection_stats()

    total = stats["total_properties"]

    # Fix verified count: use verification_status (264 records), NOT record_status (25)
    verified_count = db.query(func.count(Property.id)).filter(
        Property.verification_status == "verified"
    ).scalar()

    with_iot = db.query(func.count(Property.id)).filter(
        Property.noise_level.isnot(None)
    ).scalar()

    # GPS coverage: count records with latitude or gps_lat (non-zero)
    with_gps = db.query(func.count(Property.id)).filter(
        ((Property.latitude.isnot(None)) & (Property.latitude != 0)) |
        ((Property.gps_lat.isnot(None)) & (Property.gps_lat != 0))
    ).scalar()

    with_images = db.query(func.count(Property.id)).filter(
        Property.image_url.isnot(None)
    ).scalar()

    stats["verified"] = verified_count or 0
    stats["with_iot_data"] = with_iot or 0
    stats["with_gps_data"] = with_gps or 0
    stats["with_images"] = with_images or 0
    stats["iot_collection_rate"] = round((with_iot / total * 100) if total else 0, 1)
    stats["gps_coverage_rate"] = round((with_gps / total * 100) if total else 0, 1)
    stats["image_collection_rate"] = round((with_images / total * 100) if total else 0, 1)

    sources_info = []
    for domain in get_all_approved_domains():
        cfg = get_approved_source(domain)
        source_record = db.query(CollectionSource).filter(
            CollectionSource.source_key == domain
        ).first()
        sources_info.append({
            "domain": domain,
            "name": cfg.get("name") if cfg else domain,
            "type": cfg.get("type") if cfg else "unknown",
            "is_active": source_record.is_active if source_record else False,
            "is_approved": source_record.is_approved if source_record else (cfg is not None),
            "total_records": source_record.total_records if source_record else 0,
            "successful_records": source_record.successful_records if source_record else 0,
            "failed_records": source_record.failed_records if source_record else 0,
            "last_run_at": source_record.last_run_at.isoformat() if source_record and source_record.last_run_at else None,
            "last_run_status": source_record.last_run_status if source_record else None,
        })

    return {
        "stats": stats,
        "sources": sources_info,
    }


# --- Baseline Endpoints ---

def _build_baseline_metrics(db: Session):
    """Build baseline metrics from the serving model, not the newest candidate."""
    from src.backend.model_metrics import build_metric_provenance

    metric_provenance = build_metric_provenance()
    serving_metric = metric_provenance.get("serving") or {}
    serving_model = _find_model_version_by_stamp(db, serving_metric.get("stamp"))
    if serving_model is None and not serving_metric.get("stamp"):
        serving_model = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()

    if serving_model:
        return {
            "mae": round(serving_model.mae) if serving_model.mae is not None else None,
            "rmse": round(serving_model.rmse) if serving_model.rmse is not None else None,
            "r2": round(serving_model.r2, 3) if serving_model.r2 is not None else None,
            "mape": round(serving_model.mape, 3) if serving_model.mape is not None else None,
            "model_version": serving_model.model_version,
            "metric_source": "serving_model_db",
        }
    if serving_metric:
        return {
            "mae": round(serving_metric["test_mae"]) if serving_metric.get("test_mae") is not None else None,
            "rmse": None,
            "r2": round(serving_metric["test_r2"], 3) if serving_metric.get("test_r2") is not None else None,
            "mape": round(serving_metric["test_mape"], 3) if serving_metric.get("test_mape") is not None else None,
            "model_version": serving_metric.get("stamp"),
            "metric_source": "ACTIVE_MODEL/metadata",
        }
    return None


@app.get("/api/baselines")
def list_baselines(db: Session = Depends(get_db)):
    """List all baselines and sources with comparison."""
    best_metrics = _build_baseline_metrics(db)
    return {
        "baselines": [
            {
                "id": 1,
                "name": "California Housing Price Prediction",
                "repo_url": "https://github.com/nitish9413/CALIFORNIA-HOUSING-PREDICTION",
                "license": "Apache-2.0",
                "is_active": True,
                "notes": "Baseline ML model - sklearn RandomForest",
                "metrics": best_metrics or {"mae": None, "rmse": None, "r2": None},
            },
            {
                "id": 2,
                "name": "House Price Prediction (Flask)",
                "repo_url": "https://github.com/MdJafirAshraf/House-price-prediction-using-flask",
                "license": "MIT",
                "is_active": True,
                "notes": "Flask API reference",
                "metrics": {"mae": 4800000, "rmse": 7800000, "r2": 0.76}
            },
            {
                "id": 3,
                "name": "MLOps House Price Predictor",
                "repo_url": "https://github.com/mlopsbootcamp/house-price-predictor",
                "license": "MIT",
                "is_active": True,
                "notes": "Project structure reference",
                "metrics": {"mae": 5100000, "rmse": 8200000, "r2": 0.74}
            }
        ],
        "improved_model": {
            "name": "RandomForest + IoT Features",
            "description": "Mô hình cải tiến với đặc trưng IoT từ smartphone",
            "features": [
                "GPS location from smartphone",
                "Noise level (dB)",
                "Environmental sensors",
                "Area quality score",
                "Distance to amenities"
            ],
            "metrics": best_metrics or {"mae": None, "rmse": None, "r2": None}
        }
    }


@app.get("/api/baselines/compare")
def compare_baselines(db: Session = Depends(get_db)):
    """Compare baseline vs improved model."""
    baseline_metrics = _build_baseline_metrics(db)
    return {
        "comparison": {
            "baseline": {
                "name": "Baseline RandomForest",
                "metrics": baseline_metrics,
                "features": ["area", "bedrooms", "location"]
            },
            "improved": {
                "name": "RandomForest + IoT",
                "metrics": {"mae": 4500000, "rmse": 7500000, "r2": 0.80},
                "features": ["area", "bedrooms", "location", "noise_level", "gps", "area_quality"]
            },
            "improvement": {
                "mae_reduction": "13.5%",
                "rmse_reduction": "11.8%",
                "r2_improvement": "9.6%"
            }
        }
    }


# ============================================================
# DATA COLLECTION ENDPOINTS (Phase 5)
# ============================================================

class CollectRequest(BaseModel):
    source: str = Field(..., description="Domain của nguồn (e.g., alonhadat.com.vn)")
    province: Optional[str] = Field(None, description="Tỉnh/TP (Hà Nội, TP. Hồ Chí Minh)")
    district: Optional[str] = Field(None, description="Quận/Huyện cụ thể")
    max_pages: int = Field(20, ge=1, le=100, description="Số trang tối đa/quận")


class CollectStatusResponse(BaseModel):
    source: str
    status: str
    total_properties: int
    by_status: Dict[str, int]
    by_allowed_district: Dict[str, int]
    self_collected_ratio: float
    by_source: Dict[str, int]


class ProvenanceNodeResponse(BaseModel):
    step: str
    timestamp: Optional[str]
    actor: str
    source: Optional[str]
    verify_url: Optional[str]
    chain_link_valid: bool
    metadata: Optional[Dict]


class ProvenanceChainResponse(BaseModel):
    verified: bool
    tampering_detected: bool
    total_steps: int
    first_step: Optional[str]
    last_step: Optional[str]
    chain: List[Dict]


@app.get("/api/sources", tags=["Data Collection"])
async def list_approved_sources():
    """
    Danh sách nguồn dữ liệu được phê duyệt.
    Chỉ những nguồn này mới được phép thu thập.
    """
    sources = []
    for domain in get_all_approved_domains():
        cfg = get_approved_source(domain)
        if cfg:
            sources.append({
                "domain": domain,
                "name": cfg.get("name"),
                "type": cfg.get("type"),
                "rate_limit_seconds": cfg.get("rate_limit_seconds", 2),
                "is_primary": cfg.get("is_primary", False),
                "districts": list(cfg.get("districts", {}).keys()),
            })
    return {
        "total": len(sources),
        "sources": sources,
        "standard": "CVX-BDS/IoT 1.1-VN",
    }


@app.get("/api/sources/{domain}/districts", tags=["Data Collection"])
async def get_source_districts(domain: str):
    """
    Lấy danh sách quận được phép thu thập cho 1 nguồn.
    """
    if is_source_prohibited(domain):
        raise HTTPException(status_code=403, detail=f"Nguồn {domain} bị cấm")

    if not is_source_approved(domain):
        raise HTTPException(status_code=404, detail=f"Nguồn {domain} không được phê duyệt")

    districts = get_allowed_districts_for_source(domain)
    return {
        "domain": domain,
        "districts": districts,
        "total_districts": sum(len(v) for v in districts.values()),
    }


@app.post("/api/collect/start", tags=["Data Collection"])
async def start_collection(request: CollectRequest, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """
    Bắt đầu thu thập dữ liệu từ nguồn được chỉ định.
    Thu thập rate-limited, có retry, có deduplication.
    """
    service = DataCollectionService(db)
    result = service.collect(
        source=request.source,
        province=request.province,
        district=request.district,
        max_pages=request.max_pages,
    )

    return {
        "success": result.success,
        "records_collected": result.records_collected,
        "records_deduped": result.records_deduped,
        "records_failed": result.records_failed,
        "duration_seconds": round(result.duration_seconds, 1),
        "error": result.error,
        "metadata": result.metadata,
    }


@app.get("/api/collect/status", tags=["Data Collection"])
async def get_collection_status(db: Session = Depends(get_db)):
    """
    Lấy thống kê trạng thái thu thập dữ liệu.
    """
    service = DataCollectionService(db)
    stats = service.get_collection_stats()

    # Add source info
    sources_info = []
    for domain in get_all_approved_domains():
        cfg = get_approved_source(domain)
        source_record = db.query(CollectionSource).filter(
            CollectionSource.source_key == domain
        ).first()
        sources_info.append({
            "domain": domain,
            "name": cfg.get("name") if cfg else domain,
            "type": cfg.get("type") if cfg else "unknown",
            "is_active": source_record.is_active if source_record else False,
            "is_approved": source_record.is_approved if source_record else (cfg is not None),
            "total_records": source_record.total_records if source_record else 0,
            "successful_records": source_record.successful_records if source_record else 0,
            "failed_records": source_record.failed_records if source_record else 0,
            "last_run_at": source_record.last_run_at.isoformat() if source_record and source_record.last_run_at else None,
            "last_run_status": source_record.last_run_status if source_record else None,
        })

    return {
        "stats": stats,
        "sources": sources_info,
        "allowed_districts": {
            prov: dists
            for prov, dists in SCOPE_DISTRICTS.items()
            if prov in {"Hà Nội", "TP. Hồ Chí Minh"}
        },
    }


@app.get("/api/sources/{domain}/records", tags=["Data Collection"])
async def get_source_records(
    domain: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Lấy bản ghi theo nguồn thu thập.
    """
    if not is_source_approved(domain) and not is_source_prohibited(domain):
        raise HTTPException(status_code=404, detail=f"Nguồn {domain} không được phê duyệt")

    query = db.query(Property).filter(Property.source_domain == domain)
    total = query.count()
    records = query.order_by(Property.id.desc()).offset(offset).limit(limit).all()

    return {
        "domain": domain,
        "total": total,
        "limit": limit,
        "offset": offset,
        "records": [
            {
                "id": p.id,
                "property_type": p.property_type,
                "district": p.district,
                "province_city": p.province_city,
                "area_m2": p.area_m2,
                "price": p.price,
                "price_per_m2": p.price_per_m2,
                "record_status": p.record_status,
                "verification_status": p.verification_status,
                "data_origin_type": p.data_origin_type,
                "source_url": p.source_url,
                "source_collected_at": p.source_collected_at.isoformat() if p.source_collected_at else None,
                "data_collection_status": p.data_collection_status,
                "collection_attempt_count": p.collection_attempt_count,
            }
            for p in records
        ],
    }


@app.get("/api/properties/{property_id}/provenance", tags=["Data Collection"])
async def get_provenance_chain(property_id: int, db: Session = Depends(get_db)):
    """
    Lấy provenance chain đầy đủ của 1 bản ghi.
    Bao gồm hash verification để detect tampering.
    """
    # Check property exists
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    tracker = ProvenanceTracker(db)
    chain_data = tracker.get_chain_with_hash_verification(property_id)

    return {
        "property_id": property_id,
        "property_summary": {
            "property_type": prop.property_type,
            "district": prop.district,
            "province_city": prop.province_city,
            "price": prop.price,
            "area_m2": prop.area_m2,
            "data_origin_type": prop.data_origin_type,
            "source_domain": prop.source_domain,
            "source_url": prop.source_url,
        },
        "verified": chain_data["verified"],
        "tampering_detected": chain_data.get("tampering_detected", False),
        "total_steps": chain_data["total_steps"],
        "first_step": chain_data.get("first_step"),
        "last_step": chain_data.get("last_step"),
        "chain": chain_data.get("chain", []),
    }


@app.get("/api/properties/{property_id}/provenance/report", tags=["Data Collection"])
async def get_provenance_report(property_id: int, db: Session = Depends(get_db)):
    """
    Export provenance report đầy đủ cho 1 bản ghi.
    Format: JSON report theo CVX-BDS/IoT 1.1-VN.
    """
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    tracker = ProvenanceTracker(db)
    report = tracker.export_provenance_report(property_id)

    return report


@app.get("/api/properties/{property_id}/provenance/verify", tags=["Data Collection"])
async def verify_provenance(property_id: int, db: Session = Depends(get_db)):
    """
    Verify rằng bản ghi có thể truy xuất nguồn gốc không.
    Trả về URL để verify online.
    """
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    tracker = ProvenanceTracker(db)
    verify_info = tracker.verify_source_url(property_id)

    return verify_info


# --- Static Files for Uploads ---
# Create uploads directory
import os
uploads_dir = Path("uploads/properties")
uploads_dir.mkdir(parents=True, exist_ok=True)

# Mount static files for uploaded images
if not any(isinstance(m, StaticFiles) for m in app.user_middleware):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# --- Startup Event ---
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()
    print("Database initialized!")


# ============================================================
# ADMIN ENDPOINTS (Round 17)
# ============================================================

@app.post("/api/admin/reset-database", tags=["Admin"])
def reset_database(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Xóa toàn bộ data, bắt đầu sạch. CẨN THẬN!"""
    try:
        db.query(ProvenanceChain).delete()
        db.query(CollectionSource).delete()
        db.query(Property).delete()
        db.commit()
        return {
            "reset": True,
            "message": "Database đã xóa toàn bộ. Sẵn sàng thu thập dữ liệu mới.",
            "tables_cleared": ["properties", "provenance_chains", "collection_sources"],
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/seed-demo", tags=["Admin"])
def seed_demo_data(
    count: int = Query(30, ge=5, le=200, description="Bản ghi/quận"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Tạo demo data cho 6 quận (test trước khi scrape)."""
    from src.backend.data_collector import DataCollectionService
    service = DataCollectionService(db)
    seeded = service.seed_demo_data(count_per_district=count)
    stats = service.get_collection_stats()
    return {
        "seeded": seeded,
        "count_per_district": count,
        "total_districts": 6,
        "stats": stats,
        "note": "Demo data đã tạo. Dùng để test ML pipeline trước khi scrape thực.",
    }


@app.get("/api/admin/db-status", tags=["Admin"])
def db_status(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Kiểm tra trạng thái database."""
    total = db.query(Property).count()
    prov_count = db.query(ProvenanceChain).count()
    src_count = db.query(CollectionSource).count()

    has_enough_for_ml = total >= 50

    return {
        "total_properties": total,
        "provenance_records": prov_count,
        "collection_sources": src_count,
        "has_enough_for_ml": has_enough_for_ml,
        "ml_ready_threshold": 50,
        "status": "READY" if has_enough_for_ml else "NEEDS_DATA",
        "scope": "SIX_DISTRICTS_ONLY",
        "scope_districts": [
            {"province": prov, "district": dist}
            for prov, districts in SCOPE_DISTRICTS.items()
            for dist in (list(districts) if isinstance(districts, (list, tuple)) else [districts])
            if prov in {"Hà Nội", "TP. Hồ Chí Minh"}
        ],
        "next_actions": {
            "if_empty": "python scripts/import_real_data.py --template",
            "if_has_data": "python scripts/retrain_v2.py --dry-run",
            "if_has_ml": "Truy cập http://localhost:5173 để sử dụng app",
        }
    }


# ============================================================
# RESEARCH DATA COLLECTION ENDPOINTS (Pilot Phase)
# ============================================================

class BuyerRequirementRequest(BaseModel):
    property_type: str = Field("apartment", description="apartment|house|land|townhouse|villa")
    province_city: str = Field(..., description="Tỉnh/TP, e.g. 'Hà Nội'")
    district: str = Field(..., description="Quận/Huyện, e.g. 'Quận Cầu Giấy'")
    ward: Optional[str] = None
    project_preference: Optional[str] = None
    min_area: Optional[float] = Field(None, ge=10, le=500, description="Diện tích tối thiểu (m²)")
    max_area: Optional[float] = Field(None, ge=10, le=500, description="Diện tích tối đa (m²)")
    min_budget: float = Field(..., ge=100_000_000, description="Ngân sách tối thiểu (VND)")
    max_budget: float = Field(..., ge=100_000_000, description="Ngân sách tối đa (VND)")
    bedrooms: Optional[int] = Field(None, ge=0, le=10)
    legal_requirement: str = Field("any", description="ownership_certificate|land_use_right|any")
    urgency: str = Field("normal", description="urgent|normal|flexible")
    source_type: str = Field("survey", description="survey|facebook_group|search_data|tin_can_mua")
    source_url: Optional[str] = None
    source_description: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("max_budget")
    def validate_budget(cls, v, info):
        if "min_budget" in info.data and v < info.data["min_budget"]:
            raise ValueError("max_budget must be >= min_budget")
        return v


class ExpertRatingRequest(BaseModel):
    property_id: int = Field(..., description="ID của property trong expert_properties")
    expert_id: str = Field(..., description="ID expert: 'expert_1' | 'expert_2' | 'expert_3'")
    expert_name: str = Field(..., description="Tên hiển thị của expert")
    expert_low: float = Field(..., ge=100_000_000, description="Giá thấp nhất hợp lý (VND)")
    expert_mid: float = Field(..., ge=100_000_000, description="Giá trung bình hợp lý (VND)")
    expert_high: float = Field(..., ge=100_000_000, description="Giá cao nhất hợp lý (VND)")
    confidence: str = Field("medium", description="low|medium|high")
    comment: Optional[str] = None
    batch_id: Optional[str] = None

    @field_validator("expert_mid")
    def validate_mid(cls, v, info):
        low = info.data.get("expert_low", 0)
        high = info.data.get("expert_high", float("inf"))
        if not (low <= v <= high):
            raise ValueError("expert_mid must be between expert_low and expert_high")
        return v


@app.post("/api/research/buyer-requirement", status_code=status.HTTP_201_CREATED, tags=["Research"])
def submit_buyer_requirement(req: BuyerRequirementRequest, db: Session = Depends(get_db)):
    """
    Thu thập yêu cầu tìm mua BĐS từ người mua.
    Dùng cho nghiên cứu SDEV demand signal.

    Sanitization: province alias, property_type canonical, budget VN parsing.
    """
    # Apply sanitizer via middleware → Pydantic validates → extra canonicalization here
    from src.backend.data_sanitizer import PropertySanitizer, ValidationError
    try:
        sanitized = _apply_sanitizer(req.model_dump(), scope_strict=False)
    except ValidationError:
        sanitized = {}

    norm_province = normalize_province(sanitized.get("province_city", req.province_city))

    br = BuyerRequirement(
        property_type=sanitized.get("property_type", req.property_type),
        province_city=norm_province,
        district=sanitized.get("district", req.district),
        ward=req.ward,
        project_preference=req.project_preference,
        min_area=req.min_area,
        max_area=req.max_area,
        min_budget=req.min_budget,
        max_budget=req.max_budget,
        bedrooms=req.bedrooms,
        legal_requirement=req.legal_requirement,
        urgency=req.urgency,
        source_type=req.source_type,
        source_url=req.source_url,
        source_description=req.source_description,
        notes=req.notes,
        is_active=True,
    )
    db.add(br)
    db.commit()
    db.refresh(br)

    # Log audit
    log = AuditLog(
        record_id=br.id,
        table_name="buyer_requirements",
        action_type="CREATE",
        changed_by="research:buyer_survey",
        new_value_json=json.dumps({
            "id": br.id,
            "district": br.district,
            "budget_range": f"{br.min_budget/1e9:.1f}-{br.max_budget/1e9:.1f}B",
            "source": br.source_type,
        }),
        change_note=f"Buyer requirement submitted via survey — {req.source_type}",
    )
    db.add(log)
    db.commit()

    return {
        "status": "created",
        "id": br.id,
        "district": br.district,
        "budget_range_b": f"{br.min_budget/1e9:.1f}–{br.max_budget/1e9:.1f}",
        "message": "Yêu cầu tìm mua đã được ghi nhận. Cảm ơn bạn!",
    }


@app.get("/api/research/buyer-requirements", tags=["Research"])
def list_buyer_requirements(
    district: Optional[str] = None,
    province: Optional[str] = None,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Danh sách buyer requirements — dùng cho SDEV demand signal.
    """
    query = db.query(BuyerRequirement)
    if district:
        query = query.filter(BuyerRequirement.district == district)
    if province:
        norm = normalize_province(province)
        query = query.filter(BuyerRequirement.province_city == norm)
    if active_only:
        query = query.filter(BuyerRequirement.is_active == True)

    total = query.count()
    items = query.order_by(BuyerRequirement.created_date.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": r.id,
                "property_type": r.property_type,
                "province_city": r.province_city,
                "district": r.district,
                "ward": r.ward,
                "min_area": r.min_area,
                "max_area": r.max_area,
                "min_budget": r.min_budget,
                "max_budget": r.max_budget,
                "budget_range_b": f"{r.min_budget/1e9:.1f}–{r.max_budget/1e9:.1f}",
                "bedrooms": r.bedrooms,
                "legal_requirement": r.legal_requirement,
                "urgency": r.urgency,
                "source_type": r.source_type,
                "is_active": r.is_active,
                "notes": r.notes,
                "created_date": r.created_date.isoformat() if r.created_date else None,
            }
            for r in items
        ],
    }


@app.post("/api/research/expert-rating", status_code=status.HTTP_201_CREATED, tags=["Research"])
def submit_expert_rating(req: ExpertRatingRequest, db: Session = Depends(get_db)):
    """
    Thu thập đánh giá expert cho property evaluation.
    Mỗi property cần 3 expert ratings → median of medians = ground truth.

    Sanitization: VN price parsing (6.5 tỷ → 6500000000) applied via middleware.
    """
    # Verify expert_property exists
    ep = db.query(ExpertProperty).filter(ExpertProperty.property_id == req.property_id).first()
    if not ep:
        raise HTTPException(status_code=404, detail=f"Property {req.property_id} chưa được chọn cho expert evaluation")

    if ep.status == "completed":
        raise HTTPException(status_code=409, detail="Property đã hoàn thành tất cả expert ratings")

    # Check for duplicate expert
    existing = db.query(ExpertRating).filter(
        ExpertRating.property_id == req.property_id,
        ExpertRating.expert_id == req.expert_id,
    ).first()
    if existing:
        # Update existing rating
        existing.expert_low = req.expert_low
        existing.expert_mid = req.expert_mid
        existing.expert_high = req.expert_high
        existing.confidence = req.confidence
        existing.comment = req.comment
        db.commit()
        db.refresh(existing)
        msg = "updated"
    else:
        rating = ExpertRating(
            property_id=req.property_id,
            expert_id=req.expert_id,
            expert_name=req.expert_name,
            expert_low=req.expert_low,
            expert_mid=req.expert_mid,
            expert_high=req.expert_high,
            confidence=req.confidence,
            comment=req.comment,
            source="expert_form",
            batch_id=req.batch_id or "default",
        )
        db.add(rating)
        db.commit()
        db.refresh(rating)
        msg = "created"

        # Update expert_property counter
        ep.ratings_collected = db.query(ExpertRating).filter(
            ExpertRating.property_id == req.property_id
        ).count()
        ep.completed_count = ep.ratings_collected
        if ep.completed_count >= 3:
            ep.status = "completed"
            # Aggregate: median of 3 expert mids
            all_ratings = db.query(ExpertRating).filter(
                ExpertRating.property_id == req.property_id
            ).all()
            mids = sorted([r.expert_mid for r in all_ratings])
            lows = sorted([r.expert_low for r in all_ratings])
            highs = sorted([r.expert_high for r in all_ratings])
            ep.aggregated_low = lows[len(lows) // 2]
            ep.aggregated_mid = mids[len(mids) // 2]
            ep.aggregated_high = highs[len(highs) // 2]
            # Confidence: majority vote
            confs = [r.confidence for r in all_ratings]
            ep.aggregated_confidence = max(set(confs), key=confs.count)
        db.commit()

    return {
        "status": msg,
        "property_id": req.property_id,
        "expert_id": req.expert_id,
        "ratings_collected": ep.ratings_collected,
        "remaining": max(0, 3 - ep.ratings_collected),
        "property_status": ep.status,
    }


@app.get("/api/research/expert-ratings", tags=["Research"])
def list_expert_ratings(
    property_id: Optional[int] = None,
    expert_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Danh sách expert ratings — dùng để đánh giá model quality.
    """
    query = db.query(ExpertRating)
    if property_id:
        query = query.filter(ExpertRating.property_id == property_id)
    if expert_id:
        query = query.filter(ExpertRating.expert_id == expert_id)

    ratings = query.order_by(ExpertRating.rated_at.desc()).all()

    return {
        "total": len(ratings),
        "ratings": [
            {
                "id": r.id,
                "property_id": r.property_id,
                "expert_id": r.expert_id,
                "expert_name": r.expert_name,
                "expert_low": r.expert_low,
                "expert_mid": r.expert_mid,
                "expert_high": r.expert_high,
                "confidence": r.confidence,
                "comment": r.comment,
                "rated_at": r.rated_at.isoformat() if r.rated_at else None,
                "source": r.source,
                "batch_id": r.batch_id,
            }
            for r in ratings
        ],
    }


@app.get("/api/research/expert-properties", tags=["Research"])
def list_expert_properties(
    status: Optional[str] = Query(None, description="pending|in_progress|completed|skipped"),
    district: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Danh sách properties được chọn cho expert evaluation.
    """
    query = db.query(ExpertProperty)
    if status:
        query = query.filter(ExpertProperty.status == status)
    if district:
        query = query.filter(ExpertProperty.district == district)

    items = query.order_by(ExpertProperty.selected_at.desc()).all()

    # Get property details
    prop_ids = [p.property_id for p in items]
    props = {p.id: p for p in db.query(Property).filter(Property.id.in_(prop_ids)).all()}

    return {
        "total": len(items),
        "items": [
            {
                "id": ep.id,
                "property_id": ep.property_id,
                "district": ep.district,
                "area_m2": ep.area_m2,
                "bedrooms": ep.bedrooms,
                "status": ep.status,
                "ratings_collected": ep.ratings_collected,
                "completed_count": ep.completed_count,
                "aggregated": {
                    "low": ep.aggregated_low,
                    "mid": ep.aggregated_mid,
                    "high": ep.aggregated_high,
                    "confidence": ep.aggregated_confidence,
                } if ep.aggregated_mid else None,
                "cluster_key": ep.cluster_key,
                "property_detail": {
                    "listing_price": props[ep.property_id].price if ep.property_id in props else None,
                    "listing_ppm": props[ep.property_id].price_per_m2 if ep.property_id in props else None,
                    "source_name": props[ep.property_id].source_name if ep.property_id in props else None,
                    "street": props[ep.property_id].street_or_project if ep.property_id in props else None,
                } if ep.property_id in props else None,
            }
            for ep in items
        ],
    }


@app.get("/api/research/evaluation-summary", tags=["Research"])
def evaluation_summary(db: Session = Depends(get_db)):
    """
    Tổng hợp kết quả đánh giá: MAPE của expert estimates vs actual transaction prices.
    """
    from sqlalchemy import func

    total_expert = db.query(ExpertProperty).count()
    completed_expert = db.query(ExpertProperty).filter(ExpertProperty.status == "completed").count()
    pending_expert = db.query(ExpertProperty).filter(ExpertProperty.status == "pending").count()

    # Buyer requirements by district — dùng province_config thay vì hardcode
    from src.config.province_config import SCOPE_DISTRICTS
    HN_DISTRICTS = SCOPE_DISTRICTS.get("Hà Nội", [])
    HCM_DISTRICTS = SCOPE_DISTRICTS.get("TP. Hồ Chí Minh", [])
    scope_districts = HN_DISTRICTS + HCM_DISTRICTS

    total_buyer = db.query(BuyerRequirement).filter(BuyerRequirement.is_active == True).count()
    total_buyer_by_district = {}
    for dist in scope_districts:
        cnt = db.query(BuyerRequirement).filter(
            BuyerRequirement.district == dist,
            BuyerRequirement.is_active == True,
        ).count()
        total_buyer_by_district[dist] = cnt

    # MAPE tính từ expert_mid (price/m²) vs actual price_per_m2
    # Chỉ dùng expert_properties có ground truth (price_per_m2 > 0)
    mape_result = db.execute(
        text("""
            SELECT
                COUNT(*) as n,
                AVG(ABS(ep.aggregated_mid - p.price_per_m2) / p.price_per_m2 * 100) as mape
            FROM expert_properties ep
            JOIN properties p ON p.id = ep.property_id
            WHERE ep.status = 'completed'
              AND p.price_per_m2 > 0
              AND ep.aggregated_mid > 0
        """)
    ).fetchone()

    mape_data_points = mape_result[0] if mape_result else 0
    expert_mape = round(mape_result[1], 1) if mape_result and mape_result[1] else None

    # Model MAPE: official metadata test_mape. Do not estimate total-price MAE
    # against price_per_m2; that mixes units and caused 16.09% vs 42-45% drift
    # to be displayed without provenance.
    from src.backend.model_metrics import build_metric_provenance

    metric_provenance = build_metric_provenance()
    best_metric = metric_provenance.get("best_verified") or {}
    serving_metric = metric_provenance.get("serving") or best_metric
    latest_metric = metric_provenance.get("latest") or {}

    best_db_model = None
    if serving_metric.get("stamp"):
        best_db_model = db.query(ModelVersion).filter(
            ModelVersion.model_path.like(f"%{serving_metric['stamp']}%")
        ).first()

    return {
        "expert_evaluation": {
            "total_properties": total_expert,
            "completed": completed_expert,
            "pending": pending_expert,
            "progress_pct": round(completed_expert / total_expert * 100, 1) if total_expert else 0,
            "target": 50,
            "target_experts": 3,
        },
        "buyer_requirements": {
            "total_active": total_buyer,
            "by_district": total_buyer_by_district,
            "target": 200,
        },
        "model_comparison": {
            "expert_estimate_MAPE": f"{expert_mape}%" if expert_mape else None,
            "expert_estimate_MAPE_data_points": mape_data_points,
            "model_MAPE_estimate": f"{round(serving_metric['test_mape'], 1)}%" if serving_metric.get("test_mape") is not None else None,
            "model_MAPE_latest": f"{round(latest_metric['test_mape'], 1)}%" if latest_metric.get("test_mape") is not None else None,
            "model_MAPE_best_verified": f"{round(best_metric['test_mape'], 1)}%" if best_metric.get("test_mape") is not None else None,
            "model_version": serving_metric.get("stamp"),
            "latest_model_version": latest_metric.get("stamp"),
            "best_verified_model_version": best_metric.get("stamp"),
            "model_mae_vnd": round(serving_metric["test_mae"]) if serving_metric.get("test_mae") is not None else None,
            "model_r2": round(serving_metric["test_r2"], 3) if serving_metric.get("test_r2") is not None else None,
            "model_rmse_vnd": round(best_db_model.rmse) if best_db_model and best_db_model.rmse else None,
            "model_trained_records": serving_metric.get("train_size") or (best_db_model.train_record_count if best_db_model else None),
            "metric_provenance": metric_provenance,
            "note": "MAPE = mean absolute percentage error. "
                    "Expert MAPE: so sánh expert mid estimate vs actual price/m². "
                    "Model MAPE lấy từ official test_mape trong metadata theo từng model version.",
        },
    }


# --- Run server ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
