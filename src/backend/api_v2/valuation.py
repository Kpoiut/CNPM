"""
API v2 — Valuation endpoints.

POST /api/v2/valuation      — Chạy valuation engine mới (3 lớp output)
GET  /api/v2/valuation/{id} — Lấy valuation result đã lưu
GET  /api/v2/factors         — List all available adjustment factors
POST /api/v2/factors/evaluate — Đánh giá một property với danh sách factors
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4
import os
import time
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request, Body
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from src.backend.database import get_db
from src.backend.api_v2 import router as api_router
from src.domain.valuation.engine import (
    ValuationEngine,
    AssetInput,
    ComparableRecord,
    ValuationResult,
)
from src.domain.valuation.adjustment_registry import AdjustmentRegistry, FACTOR_REGISTRY
from src.domain.valuation.pipeline_orchestrator import PipelineOrchestrator
from src.domain.comparable.engine import ComparableCandidate, ComparableEngine, ComparableQuery
from src.config.province_config import SCOPE_DISTRICTS, normalize_province
from src.backend.models import ModelVersion, ValuationRun
from src.backend.config import limiter as _val_limiter


# =============================================================================
# ENGINE VERSION (configurable via env var)
# =============================================================================
ENGINE_VERSION: str = os.environ.get("VALUATION_ENGINE_VERSION", "v2.0.0")


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ComparableInput(BaseModel):
    """Comparable record input."""
    legacy_id: int
    asset_type: str
    province_city: str
    district: str
    ward: Optional[str] = None
    area_m2: float
    price: float
    price_per_m2: float
    evidence_tier: str = "E4"
    legal_status: str = "FULL_OWNERSHIP"
    floor: Optional[int] = None
    bedrooms: Optional[int] = None
    view_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    listing_date: Optional[str] = None
    verification_status: str = "unverified"


class ValuationRequest(BaseModel):
    """Request model cho valuation v2."""
    # Asset identity
    asset_type: str = Field(..., description="APARTMENT|TOWNHOUSE|LAND_URBAN|VILLA|SHOPHOUSE...")
    province_city: str
    district: str
    ward: Optional[str] = None
    street_or_project: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Area & geometry (cho LAND)
    area_m2: Optional[float] = Field(None, gt=0)
    polygon_json: Optional[str] = None
    frontage_m: Optional[float] = None
    frontage_road_class: Optional[str] = None
    depth_min_m: Optional[float] = None
    depth_max_m: Optional[float] = None
    taper_type: Optional[str] = None
    nö_hậu_score: Optional[float] = Field(None, ge=0, le=1)
    thóp_hậu_score: Optional[float] = Field(None, ge=0, le=1)
    irregularity_score: Optional[float] = Field(None, ge=0, le=1)
    corner_plot: bool = False
    alley_branch_count: int = 0

    # Building (nhà)
    built_area_m2: Optional[float] = None
    floor_count: int = 1
    bedrooms: int = 0
    bathrooms: int = 0
    facade_count: int = 1
    structure_grade: Optional[str] = None
    construction_year: Optional[int] = None
    main_facing: Optional[str] = None

    # Căn hộ
    block_name: Optional[str] = None
    apt_floor: Optional[int] = None
    view_type: Optional[str] = None
    door_orientation: Optional[str] = None
    balcony_orientation: Optional[str] = None
    elevator_distance: Optional[str] = None
    trash_room_distance: Optional[str] = None
    core_distance: Optional[str] = None
    sunlight_exposure: Optional[str] = None
    ventilation_score: Optional[float] = Field(None, ge=0, le=1)
    noise_inside_db: Optional[float] = None
    layout_score: Optional[float] = Field(None, ge=0, le=1)

    # Legal
    ownership_type: Optional[str] = None
    planning_zone: Optional[str] = None
    road_expansion_risk: Optional[str] = None
    mortgage_flag: bool = False
    dispute_flag: bool = False

    # Environment
    flood_risk: Optional[str] = None
    cemetery_distance_m: Optional[float] = None
    noise_day_db: Optional[float] = None
    noise_night_db: Optional[float] = None
    pollution_score: Optional[float] = None
    river_distance_m: Optional[float] = None
    park_distance_m: Optional[float] = None

    # Access
    road_width_m: Optional[float] = None
    road_class: Optional[str] = None
    car_access: bool = True
    dead_end: bool = False

    # Spiritual (fit layer)
    death_history_flag: bool = False
    worship_site_distance_m: Optional[float] = None
    stigma_known: bool = False

    # IoT
    noise_level: Optional[float] = None

    # Comparables override
    comparables: list[ComparableInput] = []

    # ---- Validators ----

    @field_validator('province_city', 'district', 'ward', 'street_or_project')
    @classmethod
    def strip_whitespace(cls, v):
        return v.strip() if v else v

    @field_validator('province_city')
    @classmethod
    def normalize_province_name(cls, v):
        return normalize_province(v.strip()) if v else v

    @field_validator('district')
    @classmethod
    def validate_scope_district(cls, v):
        # Build flat list of allowed districts from SCOPE_DISTRICTS
        allowed = []
        for districts in SCOPE_DISTRICTS.values():
            allowed.extend(districts)
        if v.strip() not in allowed:
            raise ValueError(
                f"Quận '{v}' không trong phạm vi 6 khu vực: "
                "Cầu Giấy, Thanh Xuân, Đống Đa (HN) | Q7, Bình Thạnh, Tân Bình (HCM)"
            )
        return v.strip()


class AdjustmentLedgerEntry(BaseModel):
    """Một entry trong adjustment ledger."""
    factor_code: str
    layer: str
    factor_group: str
    direction: str
    delta_pct: float
    delta_vnd: int
    confidence: float
    rationale: str
    evidence_id: Optional[str] = None
    applied_rule_id: Optional[str] = None


class ConfidenceEvidence(BaseModel):
    """Confidence và evidence breakdown."""
    overall_confidence: float
    confidence_grade: str
    evidence_tier: str
    effective_sample_size: float
    comparable_count: int
    comparable_breakdown: dict
    interval_ratio: float
    warnings: list[str]
    recommendations: list[str]


class MarketValuationOutput(BaseModel):
    """Output market valuation."""
    fair_market_value: int
    quick_sale_value: int
    recommended_listing: int
    optimistic_ask: int
    expected_range_low: int
    expected_range_high: int
    liquidity_score: str
    liquidity_band: float
    adjustment_ledger: list[AdjustmentLedgerEntry]
    base_price_from_comps: int


class FitSuitabilityOutput(BaseModel):
    """Output fit suitability."""
    persona_fit_score: Optional[float] = None
    feng_shui_fit: Optional[float] = None
    liquidity_fit: Optional[float] = None
    family_layout_fit: Optional[float] = None
    adjustment_ledger: list[AdjustmentLedgerEntry] = []


class SubEngineOutput(BaseModel):
    """Sub-engine assessment results."""
    geometry_metrics: Optional[dict] = None
    legal_assessment: Optional[dict] = None
    environment_assessment: Optional[dict] = None


class ValuationResponse(BaseModel):
    """Full valuation response."""
    run_id: str
    engine_version: str
    market_valuation: MarketValuationOutput
    fit_suitability: FitSuitabilityOutput
    confidence_evidence: ConfidenceEvidence
    sub_engines: Optional[SubEngineOutput] = None


# =============================================================================
# HELPERS
# =============================================================================

def _clean_response(data: dict, request_id: str = None) -> dict:
    """Wrap response in standard envelope."""
    return {
        "status": "success",
        "meta": {
            "request_id": request_id or str(uuid4()),
            "timestamp": datetime.now().isoformat(),
            "data_version": "1.0",
        },
        "data": data,
    }


def _timed_valuation(req: ValuationRequest, db: Session) -> dict:
    """Run valuation with timing metadata."""
    start = time.perf_counter()

    # Build AssetInput from request
    input_data = AssetInput(
        asset_type=req.asset_type,
        province_city=req.province_city,
        district=req.district,
        ward=req.ward,
        latitude=req.latitude,
        longitude=req.longitude,
        area_m2=req.area_m2 or 0.0,
        polygon_json=req.polygon_json,
        frontage_m=req.frontage_m,
        frontage_road_class=req.frontage_road_class,
        depth_min_m=req.depth_min_m,
        depth_max_m=req.depth_max_m,
        taper_type=req.taper_type,
        nö_hậu_score=req.nö_hậu_score,
        thóp_hậu_score=req.thóp_hậu_score,
        irregularity_score=req.irregularity_score,
        corner_plot=req.corner_plot,
        alley_branch_count=req.alley_branch_count,
        built_area_m2=req.built_area_m2,
        floor_count=req.floor_count,
        bedrooms=req.bedrooms,
        bathrooms=req.bathrooms,
        facade_count=req.facade_count,
        structure_grade=req.structure_grade,
        construction_year=req.construction_year,
        main_facing=req.main_facing,
        block_name=req.block_name,
        apt_floor=req.apt_floor,
        view_type=req.view_type,
        door_orientation=req.door_orientation,
        balcony_orientation=req.balcony_orientation,
        elevator_distance=req.elevator_distance,
        trash_room_distance=req.trash_room_distance,
        core_distance=req.core_distance,
        sunlight_exposure=req.sunlight_exposure,
        ventilation_score=req.ventilation_score,
        noise_inside_db=req.noise_inside_db,
        layout_score=req.layout_score,
        ownership_type=req.ownership_type,
        planning_zone=req.planning_zone,
        road_expansion_risk=req.road_expansion_risk,
        mortgage_flag=req.mortgage_flag,
        dispute_flag=req.dispute_flag,
        flood_risk=req.flood_risk,
        cemetery_distance_m=req.cemetery_distance_m,
        noise_day_db=req.noise_day_db,
        noise_night_db=req.noise_night_db,
        pollution_score=req.pollution_score,
        river_distance_m=req.river_distance_m,
        park_distance_m=req.park_distance_m,
        road_width_m=req.road_width_m,
        road_class=req.road_class,
        car_access=req.car_access,
        dead_end=req.dead_end,
        death_history_flag=req.death_history_flag,
        worship_site_distance_m=req.worship_site_distance_m,
        stigma_known=req.stigma_known,
        noise_level=req.noise_level,
    )

    # Comparable finder
    def finder(q):
        if req.comparables:
            return [
                ComparableRecord(
                    legacy_id=c.legacy_id,
                    asset_type=c.asset_type,
                    province_city=c.province_city,
                    district=c.district,
                    area_m2=c.area_m2,
                    price=c.price,
                    price_per_m2=c.price_per_m2,
                    evidence_tier=c.evidence_tier,
                    legal_status=c.legal_status,
                    floor=c.floor,
                    latitude=c.latitude,
                    longitude=c.longitude,
                    listing_date=c.listing_date,
                    verification_status=c.verification_status,
                )
                for c in req.comparables
            ]
        return _comparable_finder(q, db)

    engine.comparable_finder = finder
    result = engine.run(input_data)

    response_time_ms = round((time.perf_counter() - start) * 1000, 1)
    return {
        "run_id": result.run_id,
        "engine_version": ENGINE_VERSION,
        "market_valuation": {
            "fair_market_value": result.fair_market_value_vnd,
            "quick_sale_value": result.quick_sale_value_vnd,
            "recommended_listing": result.recommended_listing_vnd,
            "optimistic_ask": result.optimistic_ask_vnd,
            "expected_range_low": result.expected_range_low_vnd,
            "expected_range_high": result.expected_range_high_vnd,
            "liquidity_score": result.liquidity_score,
            "liquidity_band": result.liquidity_band,
            "adjustment_ledger": [a.to_dict() for a in result.market_adjustments],
            "base_price_from_comps": result.base_price_vnd,
        },
        "fit_suitability": {
            "persona_fit_score": result.persona_fit_score,
            "feng_shui_fit": result.feng_shui_fit,
            "liquidity_fit": result.liquidity_fit,
            "family_layout_fit": result.family_layout_fit,
            "adjustment_ledger": [a.to_dict() for a in result.fit_adjustments],
        },
        "confidence_evidence": {
            "overall_confidence": result.overall_confidence,
            "confidence_grade": result.confidence_grade,
            "evidence_tier": result.evidence_tier,
            "effective_sample_size": result.effective_sample_size,
            "comparable_count": result.comparable_count,
            "comparable_breakdown": result.comparable_breakdown,
            "interval_ratio": result.interval_ratio,
            "warnings": result.warnings,
            "recommendations": result.recommendations,
        },
        "_meta": {
            "response_time_ms": response_time_ms,
            "engine_version": ENGINE_VERSION,
            "timestamp": datetime.now().isoformat(),
        },
    }


# =============================================================================
# ROUTES
# =============================================================================

engine = ValuationEngine()
registry = AdjustmentRegistry()
pipeline = PipelineOrchestrator()


def _display_engine_version(raw: str | None) -> str:
    value = raw or ENGINE_VERSION
    # v3.0_locked_chain -> v3.0, v2.2.1 -> v2.2.1
    return value.split("_", 1)[0]


def _comparable_finder(asset_input: AssetInput, db: Session) -> list[ComparableRecord]:
    """
    Real comparable finder: query DB then score by Comparable Engine.

    Không lấy cố định 20 mẫu. Hàm này lấy toàn bộ ứng viên cùng loại, cùng
    tỉnh/thành và cùng quận/huyện, sau đó chỉ trả các mẫu đạt ngưỡng gần giống
    với mô tả form. Nếu không có mẫu đủ gần, trả [] để confidence phản ánh đúng.
    """
    from src.backend.models import Property
    from src.config.province_config import normalize_province

    # Map API asset_type → DB property_type
    type_map = {
        "APARTMENT": "apartment",
        "TOWNHOUSE": "townhouse",
        "LAND_URBAN": "land",
        "VILLA": "villa",
        "HOUSE": "house",
    }
    db_type = type_map.get(asset_input.asset_type, asset_input.asset_type.lower())

    norm_province = normalize_province(asset_input.province_city) or asset_input.province_city

    base_query = db.query(Property).filter(
        Property.record_status != "archived",
        Property.price > 0,
        Property.price.isnot(None),
        Property.area_m2 > 0,
        Property.province_city == norm_province,
        Property.property_type == db_type,
    )

    # Cùng quận/huyện là ranh giới tối thiểu cho "gần mô tả". Không fallback
    # sang toàn tỉnh vì điều đó làm comparable xa input và làm sai confidence.
    if asset_input.district:
        base_query = base_query.filter(Property.district == asset_input.district)

    props = base_query.all()

    def to_candidate(p: Property) -> ComparableCandidate | None:
        try:
            price = float(p.price or 0)
            area = float(p.area_m2 or 1)
            return ComparableCandidate(
                legacy_id=p.id,
                asset_type=p.property_type or db_type,
                province_city=p.province_city or norm_province,
                district=p.district or asset_input.district,
                ward=getattr(p, "ward", None),
                area_m2=area,
                price=price,
                price_per_m2=(float(p.price_per_m2) if getattr(p, "price_per_m2", None) else price / area),
                evidence_tier=p.evidence_tier or "E4",
                legal_status=p.legal_status or "unknown",
                floor=getattr(p, "floor_count", None),
                bedrooms=getattr(p, "bedrooms", None),
                latitude=getattr(p, "latitude", None),
                longitude=getattr(p, "longitude", None),
                listing_date=str(p.listing_date.date()) if getattr(p, "listing_date", None)
                    else str(p.updated_at.date()) if getattr(p, "updated_at", None) else None,
                verification_status=getattr(p, "verification_status", "unverified"),
            )
        except Exception:
            return None

    candidates = [candidate for candidate in (to_candidate(p) for p in props) if candidate]
    if not candidates:
        return []

    query = ComparableQuery(
        asset_type=db_type,
        province_city=norm_province,
        district=asset_input.district,
        ward=asset_input.ward,
        latitude=asset_input.latitude,
        longitude=asset_input.longitude,
        area_m2=asset_input.area_m2 or 0.0,
        floor=getattr(asset_input, "apt_floor", None) or getattr(asset_input, "floor_count", None),
        bedrooms=getattr(asset_input, "bedrooms", None),
        legal_status=getattr(asset_input, "ownership_type", None),
        max_count=200,
        min_similarity=0.55,
        weights={
            "geo": 0.25,
            "geometry": 0.30,
            "access": 0.10,
            "legal": 0.10,
            "evidence": 0.15,
            "recency": 0.10,
        },
    )

    scored = ComparableEngine(db_loader=lambda _query: candidates).find_comparables(query)

    records: list[ComparableRecord] = []
    for c in scored:
        reasons = []
        if asset_input.district and c.district == asset_input.district:
            reasons.append("Cùng quận/huyện")
        if asset_input.ward and c.ward == asset_input.ward:
            reasons.append("Cùng phường/xã")
        if asset_input.area_m2 and c.area_m2:
            gap = abs(c.area_m2 - asset_input.area_m2) / asset_input.area_m2
            if gap <= 0.10:
                reasons.append("Diện tích lệch dưới 10%")
            elif gap <= 0.25:
                reasons.append("Diện tích cùng biên độ")
        if c.evidence_tier in ("E1", "E2"):
            reasons.append(f"Nguồn mạnh {c.evidence_tier}")

        records.append(
            ComparableRecord(
                legacy_id=c.legacy_id,
                asset_type=c.asset_type,
                province_city=c.province_city,
                district=c.district,
                ward=c.ward,
                area_m2=c.area_m2,
                price=c.price,
                price_per_m2=c.price_per_m2,
                evidence_tier=c.evidence_tier,
                legal_status=c.legal_status or "unknown",
                floor=c.floor,
                bedrooms=c.bedrooms,
                latitude=c.latitude,
                longitude=c.longitude,
                listing_date=c.listing_date,
                verification_status=c.verification_status,
                similarity_score=round(c.overall_similarity, 3),
                match_reasons=reasons,
                adjustment_rationale=c.adjustment_rationale,
                price_adjustment_vnd=c.price_adjustment_vnd,
            )
        )

    return records


@_val_limiter.limit("30/minute")
@api_router.post("/valuation", response_model=ValuationResponse)
async def run_valuation(
    request: Request,
    req: ValuationRequest,
    db: Session = Depends(get_db),
):
    """
    Chạy valuation engine với đầy đủ 3 lớp output.

    Returns:
        - market_valuation: fair_market_value, quick_sale, recommended_listing, adjustments
        - fit_suitability: persona fit scores
        - confidence_evidence: confidence grade, evidence tier, warnings
    """
    # Build AssetInput
    input_data = AssetInput(
        asset_type=req.asset_type,
        province_city=req.province_city,
        district=req.district,
        ward=req.ward,
        latitude=req.latitude,
        longitude=req.longitude,
        area_m2=req.area_m2 or 0.0,
        polygon_json=req.polygon_json,
        frontage_m=req.frontage_m,
        frontage_road_class=req.frontage_road_class,
        depth_min_m=req.depth_min_m,
        depth_max_m=req.depth_max_m,
        taper_type=req.taper_type,
        nö_hậu_score=req.nö_hậu_score,
        thóp_hậu_score=req.thóp_hậu_score,
        irregularity_score=req.irregularity_score,
        corner_plot=req.corner_plot,
        alley_branch_count=req.alley_branch_count,
        built_area_m2=req.built_area_m2,
        floor_count=req.floor_count,
        bedrooms=req.bedrooms,
        bathrooms=req.bathrooms,
        facade_count=req.facade_count,
        structure_grade=req.structure_grade,
        construction_year=req.construction_year,
        main_facing=req.main_facing,
        block_name=req.block_name,
        apt_floor=req.apt_floor,
        view_type=req.view_type,
        door_orientation=req.door_orientation,
        balcony_orientation=req.balcony_orientation,
        elevator_distance=req.elevator_distance,
        trash_room_distance=req.trash_room_distance,
        core_distance=req.core_distance,
        sunlight_exposure=req.sunlight_exposure,
        ventilation_score=req.ventilation_score,
        noise_inside_db=req.noise_inside_db,
        layout_score=req.layout_score,
        ownership_type=req.ownership_type,
        planning_zone=req.planning_zone,
        road_expansion_risk=req.road_expansion_risk,
        mortgage_flag=req.mortgage_flag,
        dispute_flag=req.dispute_flag,
        flood_risk=req.flood_risk,
        cemetery_distance_m=req.cemetery_distance_m,
        noise_day_db=req.noise_day_db,
        noise_night_db=req.noise_night_db,
        pollution_score=req.pollution_score,
        river_distance_m=req.river_distance_m,
        park_distance_m=req.park_distance_m,
        road_width_m=req.road_width_m,
        road_class=req.road_class,
        car_access=req.car_access,
        dead_end=req.dead_end,
        death_history_flag=req.death_history_flag,
        worship_site_distance_m=req.worship_site_distance_m,
        stigma_known=req.stigma_known,
        noise_level=req.noise_level,
    )

    # Set comparable finder — dùng real DB query thay vì empty list
    def finder(q):
        if req.comparables:
            return [
                ComparableRecord(
                    legacy_id=c.legacy_id,
                    asset_type=c.asset_type,
                    province_city=c.province_city,
                    district=c.district,
                    area_m2=c.area_m2,
                    price=c.price,
                    price_per_m2=c.price_per_m2,
                    evidence_tier=c.evidence_tier,
                    legal_status=c.legal_status,
                    floor=c.floor,
                    latitude=c.latitude,
                    longitude=c.longitude,
                    listing_date=c.listing_date,
                    verification_status=c.verification_status,
                )
                for c in req.comparables
            ]
        # Real DB lookup
        return _comparable_finder(q, db)

    engine.comparable_finder = finder

    # Run engine
    result = engine.run(input_data)

    # Persist to valuation_runs
    import hashlib
    input_hash = hashlib.sha224(
        f"{req.asset_type}:{req.province_city}:{req.district}:{req.area_m2}".encode()
    ).hexdigest()
    run_record = ValuationRun(
        engine_version=ENGINE_VERSION,
        base_price_vnd=result.base_price_vnd,
        base_price_source=result.base_price_source if hasattr(result, 'base_price_source') else None,
        fair_market_value_vnd=result.fair_market_value_vnd,
        quick_sale_value_vnd=result.quick_sale_value_vnd,
        recommended_listing_vnd=result.recommended_listing_vnd,
        optimistic_ask_vnd=result.optimistic_ask_vnd,
        expected_range_low_vnd=result.expected_range_low_vnd,
        expected_range_high_vnd=result.expected_range_high_vnd,
        liquidity_score=result.liquidity_score,
        liquidity_band=result.liquidity_band,
        overall_confidence=result.overall_confidence,
        confidence_grade=result.confidence_grade,
        evidence_tier=result.evidence_tier,
        comparable_count=result.comparable_count,
        effective_sample_size=result.effective_sample_size,
        anchor_share=result.anchor_share if hasattr(result, 'anchor_share') else None,
        independent_source_count=result.independent_source_count if hasattr(result, 'independent_source_count') else None,
        input_hash=input_hash,
    )
    db.add(run_record)
    db.commit()

    # Build response
    return ValuationResponse(
        run_id=result.run_id,
        engine_version=ENGINE_VERSION,
        market_valuation=MarketValuationOutput(
            fair_market_value=result.fair_market_value_vnd,
            quick_sale_value=result.quick_sale_value_vnd,
            recommended_listing=result.recommended_listing_vnd,
            optimistic_ask=result.optimistic_ask_vnd,
            expected_range_low=result.expected_range_low_vnd,
            expected_range_high=result.expected_range_high_vnd,
            liquidity_score=result.liquidity_score,
            liquidity_band=result.liquidity_band,
            adjustment_ledger=[
                AdjustmentLedgerEntry(**a.to_dict())
                for a in result.market_adjustments
            ],
            base_price_from_comps=result.base_price_vnd,
        ),
        fit_suitability=FitSuitabilityOutput(
            persona_fit_score=result.persona_fit_score,
            feng_shui_fit=result.feng_shui_fit,
            liquidity_fit=result.liquidity_fit,
            family_layout_fit=result.family_layout_fit,
            adjustment_ledger=[
                AdjustmentLedgerEntry(**a.to_dict())
                for a in result.fit_adjustments
            ],
        ),
        confidence_evidence=ConfidenceEvidence(
            overall_confidence=result.overall_confidence,
            confidence_grade=result.confidence_grade,
            evidence_tier=result.evidence_tier,
            effective_sample_size=result.effective_sample_size,
            comparable_count=result.comparable_count,
            comparable_breakdown=result.comparable_breakdown,
            interval_ratio=result.interval_ratio,
            warnings=result.warnings,
            recommendations=result.recommendations,
        ),
        sub_engines=SubEngineOutput(
            geometry_metrics=result.geometry_metrics,
            legal_assessment=result.legal_assessment,
            environment_assessment=result.environment_assessment,
        ),
    )


@api_router.post("/pipeline")
def run_pipeline(
    req: ValuationRequest,
    db: Session = Depends(get_db),
):
    """
    Production pipeline — 9-gate locked chain.

    Mọi BĐS đưa vào đều đi qua 9 gate tuần tự:
    INTAKE → NORMALIZE → CLASSIFY → LEGAL → GEOMETRY → ENVIRONMENT →
    COMPARABLE → VALUATION → FIT

    Returns:
        - pipeline_id, final_status (PASS|WARN|BLOCK)
        - gates: audit trail của 9 gate
        - valuation: kết quả định giá (nếu không bị block)
        - completeness: báo cáo mức độ đầy đủ dữ liệu
    """
    input_data = AssetInput(
        asset_type=req.asset_type,
        province_city=req.province_city,
        district=req.district,
        ward=req.ward,
        latitude=req.latitude,
        longitude=req.longitude,
        area_m2=req.area_m2 or 0.0,
        frontage_m=req.frontage_m,
        depth_min_m=req.depth_min_m,
        depth_max_m=req.depth_max_m,
        taper_type=req.taper_type,
        nö_hậu_score=req.nö_hậu_score,
        thóp_hậu_score=req.thóp_hậu_score,
        irregularity_score=req.irregularity_score,
        corner_plot=req.corner_plot,
        alley_branch_count=req.alley_branch_count,
        built_area_m2=req.built_area_m2,
        floor_count=req.floor_count,
        bedrooms=req.bedrooms,
        bathrooms=req.bathrooms,
        facade_count=req.facade_count,
        structure_grade=req.structure_grade,
        construction_year=req.construction_year,
        main_facing=req.main_facing,
        block_name=req.block_name,
        apt_floor=req.apt_floor,
        view_type=req.view_type,
        door_orientation=req.door_orientation,
        balcony_orientation=req.balcony_orientation,
        elevator_distance=req.elevator_distance,
        trash_room_distance=req.trash_room_distance,
        core_distance=req.core_distance,
        sunlight_exposure=req.sunlight_exposure,
        ventilation_score=req.ventilation_score,
        noise_inside_db=req.noise_inside_db,
        layout_score=req.layout_score,
        ownership_type=req.ownership_type,
        planning_zone=req.planning_zone,
        road_expansion_risk=req.road_expansion_risk,
        mortgage_flag=req.mortgage_flag,
        dispute_flag=req.dispute_flag,
        flood_risk=req.flood_risk,
        cemetery_distance_m=req.cemetery_distance_m,
        noise_day_db=req.noise_day_db,
        noise_night_db=req.noise_night_db,
        pollution_score=req.pollution_score,
        river_distance_m=req.river_distance_m,
        park_distance_m=req.park_distance_m,
        road_width_m=req.road_width_m,
        road_class=req.road_class,
        car_access=req.car_access,
        dead_end=req.dead_end,
        death_history_flag=req.death_history_flag,
        worship_site_distance_m=req.worship_site_distance_m,
        stigma_known=req.stigma_known,
        noise_level=req.noise_level,
    )

    # Set comparable finder with DB session
    def finder(q):
        if req.comparables:
            return [
                ComparableRecord(
                    legacy_id=c.legacy_id, asset_type=c.asset_type,
                    province_city=c.province_city, district=c.district,
                    area_m2=c.area_m2, price=c.price, price_per_m2=c.price_per_m2,
                    evidence_tier=c.evidence_tier, legal_status=c.legal_status,
                    floor=c.floor, latitude=c.latitude, longitude=c.longitude,
                    listing_date=c.listing_date,
                    verification_status=c.verification_status,
                ) for c in req.comparables
            ]
        return _comparable_finder(q, db)

    pipeline.valuation_engine.comparable_finder = finder
    result = pipeline.run(input_data)
    return result.to_dict()


@api_router.get("/engine/version")
def engine_version(db: Session = Depends(get_db)):
    """
    Current valuation engine label for UI controls.

    Admin UI should keep the technical engine label and follow future ML/pipeline
    upgrades without hardcoding a button caption in the frontend.
    """
    latest_model = db.query(ModelVersion).order_by(ModelVersion.trained_at.desc()).first()
    pipeline_version = getattr(pipeline, "pipeline_version", None)
    display_version = _display_engine_version(pipeline_version or ENGINE_VERSION)
    return {
        "engine_version": display_version,
        "pipeline_version": pipeline_version or ENGINE_VERSION,
        "core_engine_version": ENGINE_VERSION,
        "button_label": f"Chạy Valuation Engine {display_version}",
        "latest_model": {
            "version": latest_model.model_version if latest_model else None,
            "model_name": latest_model.model_name if latest_model else None,
            "trained_at": latest_model.trained_at.isoformat() if latest_model and latest_model.trained_at else None,
        } if latest_model else None,
    }


@api_router.get("/valuation/runs")
def list_valuation_runs(limit: int = 20, db: Session = Depends(get_db)):
    """
    List recent valuation runs persisted to DB.
    """
    runs = db.query(ValuationRun).order_by(ValuationRun.created_at.desc()).limit(limit).all()
    return {
        "runs": [
            {
                "id": r.id,
                "engine_version": r.engine_version,
                "fair_market_value_vnd": r.fair_market_value_vnd,
                "confidence_grade": r.confidence_grade,
                "evidence_tier": r.evidence_tier,
                "overall_confidence": r.overall_confidence,
                "comparable_count": r.comparable_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ],
        "total": db.query(ValuationRun).count(),
    }


@api_router.get("/valuation/stats")
def valuation_stats(db: Session = Depends(get_db)):
    """
    Aggregate statistics from valuation runs.
    """
    total = db.query(ValuationRun).count()
    if total == 0:
        return {"total_runs": 0}

    from sqlalchemy import func
    avg_confidence = db.query(func.avg(ValuationRun.overall_confidence)).scalar() or 0
    avg_fmv = db.query(func.avg(ValuationRun.fair_market_value_vnd)).scalar() or 0
    grade_counts = db.query(
        ValuationRun.confidence_grade,
        func.count(ValuationRun.id)
    ).group_by(ValuationRun.confidence_grade).all()

    return {
        "total_runs": total,
        "avg_confidence": round(avg_confidence, 3),
        "avg_fair_market_value": round(avg_fmv),
        "by_grade": {g: c for g, c in grade_counts},
    }


@api_router.get("/factors")
def list_factors(layer: Optional[str] = None, asset_type: Optional[str] = None):
    """
    List all available adjustment factors.

    Args:
        layer: Filter by MARKET or FIT
        asset_type: Filter by asset type (APARTMENT, LAND_URBAN, etc.)
    """
    from src.domain.valuation.adjustment_registry import AdjustmentLayer

    factors = list(FACTOR_REGISTRY.values())

    if layer:
        factors = [f for f in factors if f.layer.value == layer.upper()]

    if asset_type:
        factors = [
            f for f in factors
            if not f.asset_types or asset_type.upper() in f.asset_types
        ]

    return {
        "total": len(factors),
        "factors": [
            {
                "factor_code": f.factor_code,
                "layer": f.layer.value,
                "group": f.group.value,
                "asset_types": list(f.asset_types) if f.asset_types else "ALL",
                "delta_pct_base": f.delta_pct_base,
                "confidence_base": f.confidence_base,
                "rationale_template": f.rationale_template,
                "evidence_requirement": f.evidence_requirement,
            }
            for f in factors
        ],
    }


# ─── Reference Photos (Phase 3: Visualization Pipeline) ───────────────────────

# Curated Unsplash reference photos per property type.
# These serve as fallback when Street View is unavailable.
# Attribution: All photos from Unsplash (free to use under Unsplash License).
DEFAULT_REFERENCE_PHOTOS = {
    "land": [
        {
            "url": "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=600&h=400&fit=crop",
            "caption_vi": "Khu đất trống quy hoạch đô thị",
            "photographer": "Unsplash",
            "tags": ["land", "urban", "empty"],
        },
        {
            "url": "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=600&h=400&fit=crop",
            "caption_vi": "Đất nền khu dân cư mới",
            "photographer": "Unsplash",
            "tags": ["land", "residential", "planning"],
        },
        {
            "url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=600&h=400&fit=crop",
            "caption_vi": "Quy hoạch khu đô thị ven đô",
            "photographer": "Unsplash",
            "tags": ["land", "planning", "suburban"],
        },
        {
            "url": "https://images.unsplash.com/photo-1592595896616-c37162298647?w=600&h=400&fit=crop",
            "caption_vi": "Đất ở ngoại thành Hà Nội",
            "photographer": "Unsplash",
            "tags": ["land", "suburban", "hanoi"],
        },
        {
            "url": "https://images.unsplash.com/photo-1515263487990-61b07816b324?w=600&h=400&fit=crop",
            "caption_vi": "Khu đất chưa khai thác",
            "photographer": "Unsplash",
            "tags": ["land", "unused", "empty"],
        },
        {
            "url": "https://images.unsplash.com/photo-1628624747186-a941c476b7ef?w=600&h=400&fit=crop",
            "caption_vi": "Đất nền dự án khu đô thị",
            "photographer": "Unsplash",
            "tags": ["land", "project", "urban"],
        },
    ],
    "apartment": [
        {
            "url": "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600&h=400&fit=crop",
            "caption_vi": "Chung cư cao cấp view thành phố",
            "photographer": "Unsplash",
            "tags": ["apartment", "city_view", "modern"],
        },
        {
            "url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=600&h=400&fit=crop",
            "caption_vi": "Nội thất căn hộ hiện đại",
            "photographer": "Unsplash",
            "tags": ["apartment", "interior", "modern"],
        },
        {
            "url": "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=600&h=400&fit=crop",
            "caption_vi": "Căn hộ chung cư Hà Nội",
            "photographer": "Unsplash",
            "tags": ["apartment", "hanoi", "residential"],
        },
        {
            "url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&h=400&fit=crop",
            "caption_vi": "Căn hộ view hồ nước",
            "photographer": "Unsplash",
            "tags": ["apartment", "lake_view", "premium"],
        },
        {
            "url": "https://images.unsplash.com/photo-1493809842364-78817add7ffb?w=600&h=400&fit=crop",
            "caption_vi": "Khu chung cư đông đúc",
            "photographer": "Unsplash",
            "tags": ["apartment", "dense", "urban"],
        },
        {
            "url": "https://images.unsplash.com/photo-1536376072261-38c75010e6c9?w=600&h=400&fit=crop",
            "caption_vi": "Chung cư cao tầng ban đêm",
            "photographer": "Unsplash",
            "tags": ["apartment", "highrise", "night"],
        },
    ],
    "townhouse": [
        {
            "url": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=600&h=400&fit=crop",
            "caption_vi": "Nhà phố hiện đại mặt tiền đường lớn",
            "photographer": "Unsplash",
            "tags": ["townhouse", "modern", "facade"],
        },
        {
            "url": "https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=600&h=400&fit=crop",
            "caption_vi": "Dãy nhà phố khu dân cư",
            "photographer": "Unsplash",
            "tags": ["townhouse", "row", "residential"],
        },
        {
            "url": "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=600&h=400&fit=crop",
            "caption_vi": "Nhà liền kề Hà Nội",
            "photographer": "Unsplash",
            "tags": ["townhouse", "hanoi", "urban"],
        },
        {
            "url": "https://images.unsplash.com/photo-1598228723793-52759bba239c?w=600&h=400&fit=crop",
            "caption_vi": "Nhà phố kinh doanh mặt phố",
            "photographer": "Unsplash",
            "tags": ["townhouse", "shophouse", "commercial"],
        },
        {
            "url": "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=600&h=400&fit=crop",
            "caption_vi": "Khu nhà phố vườn cây xanh",
            "photographer": "Unsplash",
            "tags": ["townhouse", "garden", "green"],
        },
        {
            "url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&h=400&fit=crop",
            "caption_vi": "Nhà phố cổ Hà Nội",
            "photographer": "Unsplash",
            "tags": ["townhouse", "old", "heritage"],
        },
    ],
    "villa": [
        {
            "url": "https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=600&h=400&fit=crop",
            "caption_vi": "Biệt thự hiện đại cao cấp",
            "photographer": "Unsplash",
            "tags": ["villa", "modern", "premium"],
        },
        {
            "url": "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=600&h=400&fit=crop",
            "caption_vi": "Biệt thự vườn rộng",
            "photographer": "Unsplash",
            "tags": ["villa", "garden", "spacious"],
        },
        {
            "url": "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=600&h=400&fit=crop",
            "caption_vi": "Biệt thự Vinhomes Riverside",
            "photographer": "Unsplash",
            "tags": ["villa", "vinhomes", "premium"],
        },
        {
            "url": "https://images.unsplash.com/photo-1512915922686-57c11dde9b6b?w=600&h=400&fit=crop",
            "caption_vi": "Biệt thự view hồ bơi",
            "photographer": "Unsplash",
            "tags": ["villa", "pool", "luxury"],
        },
        {
            "url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=600&h=400&fit=crop",
            "caption_vi": "Biệt thự phong cách Châu Âu",
            "photographer": "Unsplash",
            "tags": ["villa", "european", "classic"],
        },
        {
            "url": "https://images.unsplash.com/photo-1576941089067-2de3c901e126?w=600&h=400&fit=crop",
            "caption_vi": "Biệt thự khucompound cao cấp",
            "photographer": "Unsplash",
            "tags": ["villa", "compound", "gated"],
        },
    ],
    "house": [
        {
            "url": "https://images.unsplash.com/photo-1449844908441-8829872d2607?w=600&h=400&fit=crop",
            "caption_vi": "Nhà riêng một tầng ngoại thành",
            "photographer": "Unsplash",
            "tags": ["house", "single", "suburban"],
        },
        {
            "url": "https://images.unsplash.com/photo-1464146072230-91cabc968266?w=600&h=400&fit=crop",
            "caption_vi": "Nhà riêng truyền thống Việt Nam",
            "photographer": "Unsplash",
            "tags": ["house", "traditional", "vietnamese"],
        },
        {
            "url": "https://images.unsplash.com/photo-1518780664697-55e3ad937233?w=600&h=400&fit=crop",
            "caption_vi": "Nhà riêng có sân vườn",
            "photographer": "Unsplash",
            "tags": ["house", "garden", "private"],
        },
        {
            "url": "https://images.unsplash.com/photo-1523217582562-09d0def993a6?w=600&h=400&fit=crop",
            "caption_vi": "Nhà riêng khu phố cổ",
            "photographer": "Unsplash",
            "tags": ["house", "old_town", "heritage"],
        },
        {
            "url": "https://images.unsplash.com/photo-1505843513577-22bb7d21e455?w=600&h=400&fit=crop",
            "caption_vi": "Nhà riêng tầng trệt",
            "photographer": "Unsplash",
            "tags": ["house", "ground", "simple"],
        },
        {
            "url": "https://images.unsplash.com/photo-1416331108676-a22ccb276e35?w=600&h=400&fit=crop",
            "caption_vi": "Nhà riêng khu đô thị mới",
            "photographer": "Unsplash",
            "tags": ["house", "new", "urban"],
        },
    ],
}

# Map API asset_type → photo key
_PHOTO_TYPE_MAP = {
    "LAND_URBAN": "land", "LAND_SUBURBAN": "land", "LAND_PROJECT": "land",
    "APARTMENT": "apartment", "STUDIO": "apartment", "PENTHOUSE": "apartment",
    "DUPLEX": "apartment",
    "TOWNHOUSE": "townhouse", "SHOPHOUSE": "townhouse",
    "VILLA": "villa",
    "HOUSE": "house",
}


# ─────────────────────────────────────────────────────────────────────────────
# SDEV — Supply-Demand Equilibrium Valuation (Pilot M4)
# IMPORTANT: These estimates are PROXIES for market-acceptable price,
# NOT predictions of actual transaction prices.
# ─────────────────────────────────────────────────────────────────────────────

from src.domain.valuation.sdev_engine import SDEVEngine

SDEV_TYPE_MAP = {
    "APARTMENT": "apartment",
    "TOWNHOUSE": "townhouse",
    "LAND_URBAN": "land",
    "VILLA": "villa",
    "HOUSE": "house",
}


class SDEVRequest(BaseModel):
    """Request model for SDEV endpoint."""
    asset_type: str = Field(..., description="APARTMENT|TOWNHOUSE|LAND_URBAN|VILLA|HOUSE")
    province_city: str
    district: str
    area_m2: float = Field(..., gt=0)
    bedrooms: int = Field(default=2, ge=0)


@dataclass
class SDEVResponse:
    status: str
    reason: Optional[str]
    estimated_mid_price: int
    acceptable_low: int
    acceptable_high: int
    price_per_m2: int
    acceptance_score: float
    confidence_level: str
    ask_bid_overlap_score: float
    cluster_district: str
    cluster_area_band: str
    cluster_bedrooms: int
    n_ask_listings: int
    n_bid_requirements: int
    demand_coverage_ratio: float
    main_drivers: list
    ask_stats: Optional[dict]
    bid_stats: Optional[dict]


@api_router.post("/sdev", response_model=dict)
def run_sdev(
    req: SDEVRequest,
    db: Session = Depends(get_db),
):
    """
    SDEV — Supply-Demand Equilibrium Valuation.

    Estimates market-acceptable price range using bid-ask matching.
    Requires buyer requirement data for demand side. Falls back to
    ask-only if no demand data available.

    IMPORTANT: All outputs are PROXIES, not transaction price predictions.
    """
    asset_type = SDEV_TYPE_MAP.get(req.asset_type, req.asset_type.lower())

    engine = SDEVEngine(db)
    result = engine.run(
        district=req.district,
        area_m2=req.area_m2,
        bedrooms=req.bedrooms,
        asset_type=asset_type,
    )

    return {
        "status": result.status,
        "model": "SDEV-M4",
        "disclaimer": (
            "Estimates are PROXIES for market-acceptable price. "
            "NOT predictions of actual transaction prices."
        ),
        "estimated_mid_price": result.estimated_mid_price,
        "acceptable_low": result.acceptable_low,
        "acceptable_high": result.acceptable_high,
        "price_per_m2": result.price_per_m2,
        "acceptance_score": result.acceptance_score,
        "confidence_level": result.confidence_level,
        "ask_bid_overlap_score": result.ask_bid_overlap_score,
        "cluster": {
            "district": result.cluster_district,
            "area_band": result.cluster_area_band,
            "bedrooms": result.cluster_bedrooms,
            "n_ask_listings": result.n_ask_listings,
            "n_bid_requirements": result.n_bid_requirements,
        },
        "demand_coverage_ratio": result.demand_coverage_ratio,
        "main_drivers": result.main_drivers,
        "_ask_stats": result.ask_stats,
        "_bid_stats": result.bid_stats,
    }


@api_router.get("/reference-photos")
def get_reference_photos(
    property_type: Optional[str] = None,
    limit: int = 6,
):
    """
    Return curated reference photos for a property type.

    Used for visualization in the Prediction page when Street View is unavailable.
    Photos are from Unsplash (free to use under Unsplash License).
    Attribution is included per photo.
    """
    from src.domain.property_types import to_canonical

    # Determine photo category
    if property_type:
        photo_key = _PHOTO_TYPE_MAP.get(property_type.upper(), "land")
    else:
        photo_key = "land"

    photos = DEFAULT_REFERENCE_PHOTOS.get(photo_key, DEFAULT_REFERENCE_PHOTOS["land"])
    return {
        "property_type": photo_key,
        "photos": photos[:limit],
        "total": len(photos),
        "attribution": "Photos from Unsplash (Unsplash License)",
        "note": "Ảnh tham chiếu — dùng để trực quan hóa. "
                "Không phải ảnh thực của bất động sản cần định giá.",
    }
from src.backend.api_v2 import router
