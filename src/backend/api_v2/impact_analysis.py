"""
API v2 — Impact Analysis Endpoint.

POST /api/v2/impact-analysis — Phân tích tác động (Admin-only)
    Contextual Comparable-SHAP δ% Algorithm:
      - Comparable pool selection (4 levels, weighted)
      - ML prediction + SHAP với comparable-pool background
      - Raw δ% → Display δ% (clamp ±15%) + residual
      - Missing data: price effect vs. confidence loss
      - What-if scenario projections
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.backend.database import get_db
from src.backend.api_v2 import router as api_router
from src.backend.auth.models import User
from src.backend.auth.dependencies import get_optional_user
from src.domain.valuation.engine import AssetInput
from src.domain.valuation.impact_engine import ImpactEngine, ImpactResult


# =============================================================================
# REQUEST MODELS
# =============================================================================

class ImpactAnalysisRequest(BaseModel):
    """Request cho impact analysis — mirrors ValuationRequest fields."""
    asset_type: str
    province_city: str
    district: str
    ward: Optional[str] = None
    street_or_project: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    area_m2: Optional[float] = Field(None, gt=0)
    polygon_json: Optional[str] = None
    frontage_m: Optional[float] = None
    frontage_road_class: Optional[str] = None
    depth_min_m: Optional[float] = None
    depth_max_m: Optional[float] = None
    depth_max_m_alt: Optional[float] = None
    taper_type: Optional[str] = None
    nö_hậu_score: Optional[float] = Field(None, ge=0, le=1)
    thóp_hậu_score: Optional[float] = Field(None, ge=0, le=1)
    irregularity_score: Optional[float] = Field(None, ge=0, le=1)
    corner_plot: bool = False
    alley_branch_count: int = 0

    built_area_m2: Optional[float] = None
    floor_count: int = 1
    bedrooms: int = 0
    bathrooms: int = 0
    facade_count: int = 1
    structure_grade: Optional[str] = None
    construction_year: Optional[int] = None
    main_facing: Optional[str] = None

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

    ownership_type: Optional[str] = None
    planning_zone: Optional[str] = None
    road_expansion_risk: Optional[str] = None
    mortgage_flag: bool = False
    dispute_flag: bool = False

    flood_risk: Optional[str] = None
    cemetery_distance_m: Optional[float] = None
    noise_day_db: Optional[float] = None
    noise_night_db: Optional[float] = None
    pollution_score: Optional[float] = None
    river_distance_m: Optional[float] = None
    park_distance_m: Optional[float] = None

    road_width_m: Optional[float] = None
    road_class: Optional[str] = None
    car_access: bool = True
    dead_end: bool = False

    death_history_flag: bool = False
    worship_site_distance_m: Optional[float] = None
    stigma_known: bool = False

    noise_level: Optional[float] = None

    run_id: Optional[str] = Field(None, description="Optional existing run_id to reference")


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class ImpactFactorResponse(BaseModel):
    field_code: str
    field_label: str
    field_value: Any
    comparable_mean: Optional[float] = None
    comparable_range: Optional[tuple[float, float]] = None
    raw_delta_pct: float
    display_delta_pct: float
    contribution_vnd: int
    direction: str
    confidence: float
    is_missing: bool
    is_residual: bool
    detail: str
    source: str


class MissingDataImpactResponse(BaseModel):
    field: str
    field_label: str
    missing: bool
    price_effect_pct: float
    confidence_penalty: float
    confidence_penalty_vnd: int
    recommendation: str


class ScenarioProjectionResponse(BaseModel):
    scenario_name: str
    scenario_type: str
    fmv_low: int
    fmv_high: int
    fmv_mid: int
    confidence: float
    confidence_grade: str
    interval_width_pct: float
    filled_fields: list[str]
    uncertainty_reduction_pct: float


class ImpactAnalysisResponse(BaseModel):
    run_id: str
    fair_market_value: int
    baseline_value: int
    delta_vs_baseline_pct: float

    n_eff: float
    comparable_level: int
    n_comparables_used: int

    contributions: list[ImpactFactorResponse]
    missing_data: list[MissingDataImpactResponse]
    total_confidence_loss: float

    current_scenario: ScenarioProjectionResponse
    full_info_scenario: ScenarioProjectionResponse
    max_credibility_scenario: ScenarioProjectionResponse

    top_positive: list[str]
    top_negative: list[str]
    raw_total_pct: float
    display_total_pct: float


# =============================================================================
# HELPERS
# =============================================================================

def _load_pipeline():
    """Lazy-load MLPipeline; impact analysis can fall back to rule-based mode."""
    from src.ml.pipeline import MLPipeline
    pipeline = MLPipeline()
    try:
        pipeline.load()
    except Exception as e:
        print(f"[WARN] impact-analysis running without loaded ML model: {e}")
        return None
    return pipeline


def _request_to_asset_input(req: ImpactAnalysisRequest) -> AssetInput:
    """Convert request model to AssetInput."""
    return AssetInput(
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
        depth_max_m=req.depth_max_m or req.depth_max_m_alt,
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


def _map_impact_result(result: ImpactResult) -> ImpactAnalysisResponse:
    """Map internal ImpactResult dataclass to API response model."""
    contributions = []
    for c in result.contributions:
        comparable_range: Optional[tuple[float, float]] = None
        if c.comparable_min is not None and c.comparable_max is not None:
            comparable_range = (c.comparable_min, c.comparable_max)

        contributions.append(ImpactFactorResponse(
            field_code=c.field_code,
            field_label=c.field_label,
            field_value=c.field_value,
            comparable_mean=c.comparable_mean,
            comparable_range=comparable_range,
            raw_delta_pct=round(c.raw_delta_pct, 2),
            display_delta_pct=round(c.display_delta_pct, 2),
            contribution_vnd=int(round(c.contribution_vnd)),
            direction=c.direction,
            confidence=round(c.confidence, 3),
            is_missing=c.is_missing,
            is_residual=c.is_residual,
            detail=c.detail,
            source=c.source,
        ))

    missing_data = [
        MissingDataImpactResponse(
            field=m.field,
            field_label=m.field_label,
            missing=m.missing,
            price_effect_pct=round(m.price_effect_pct, 2),
            confidence_penalty=round(m.confidence_penalty, 1),
            confidence_penalty_vnd=int(round(m.confidence_penalty_vnd)),
            recommendation=m.recommendation,
        )
        for m in result.missing_data
    ]

    def map_scenario(s):
        return ScenarioProjectionResponse(
            scenario_name=s.scenario_name,
            scenario_type=s.scenario_type,
            fmv_low=int(round(s.fmv_low)),
            fmv_high=int(round(s.fmv_high)),
            fmv_mid=int(round(s.fmv_mid)),
            confidence=round(s.confidence, 1),
            confidence_grade=s.confidence_grade,
            interval_width_pct=round(s.interval_width_pct, 1),
            filled_fields=s.filled_fields,
            uncertainty_reduction_pct=round(s.uncertainty_reduction_pct, 1),
        )

    return ImpactAnalysisResponse(
        run_id=result.run_id,
        fair_market_value=int(round(result.fair_market_value)),
        baseline_value=int(round(result.baseline_value)),
        delta_vs_baseline_pct=round(result.delta_vs_baseline_pct, 2),
        n_eff=round(result.n_eff, 2),
        comparable_level=result.comparable_level,
        n_comparables_used=result.n_comparables_used,
        contributions=contributions,
        missing_data=missing_data,
        total_confidence_loss=round(result.total_confidence_loss, 1),
        current_scenario=map_scenario(result.current_scenario),
        full_info_scenario=map_scenario(result.full_info_scenario),
        max_credibility_scenario=map_scenario(result.max_credibility_scenario),
        top_positive=result.top_positive,
        top_negative=result.top_negative,
        raw_total_pct=round(result.raw_total_pct, 2),
        display_total_pct=round(result.display_total_pct, 2),
    )


# =============================================================================
# ENDPOINT
# =============================================================================

@api_router.post("/impact-analysis", response_model=ImpactAnalysisResponse)
def impact_analysis(
    body: ImpactAnalysisRequest,
    request: Request,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """
    Phân tích tác động cho property — Admin-only.

    Sử dụng Contextual Comparable-SHAP δ% Algorithm:
      1. Chọn comparable pool (4 levels, weighted)
      2. ML model predict (log price)
      3. SHAP với background = comparable pool
      4. Raw δ% → Display δ% (clamp ±15%) + residual
      5. Missing data: price effect + confidence loss
      6. What-if scenario projections

    Trả về:
      - Danh sách tác động theo field (đã sort |display_delta| desc)
      - Missing data impact (confidence loss)
      - 3 scenario projections: hiện tại, full-info, max-credibility
    """
    host = request.headers.get("host", "")
    origin = request.headers.get("origin", "")
    is_local_dashboard = (
        "localhost" in host
        or "127.0.0.1" in host
        or "localhost" in origin
        or "127.0.0.1" in origin
    )
    has_admin_dashboard_session = (
        request.headers.get("X-AVM-Admin-Session") == "active"
        and is_local_dashboard
    )
    if not ((user and user.role == "admin") or has_admin_dashboard_session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới được truy cập phân tích tác động.",
        )

    pipeline = _load_pipeline()
    engine = ImpactEngine(ml_pipeline=pipeline, db_session=db)
    asset_input = _request_to_asset_input(body)
    result = engine.analyze(asset_input)

    return _map_impact_result(result)
