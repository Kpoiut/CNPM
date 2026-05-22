"""
Valuation Engine — Core của Real Estate Decision Intelligence Platform.

Công thức:
  fair_market_value = base_market_price + Σ(market_adjustments)
  quick_sale_value = fair_market_value × (1 - liquidity_discount)
  recommended_listing = fair_market_value × (1 + listing_premium)
  optimistic_ask = fair_market_value × (1 + optimistic_premium)

  confidence = computed_from(evidence_quality, comparable_coverage, data_freshness)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from src.domain.valuation.adjustment_registry import (
    AdjustmentRegistry,
    Adjustment,
    AdjustmentLayer,
    FactorGroup,
)
from src.config.province_config import (
    BASE_PRICES_PER_M2,
    get_base_price_per_m2,
    SCOPE_DISTRICTS,
    normalize_province,
)


# =============================================================================
# DATA CLASSES — Input/Output contracts
# =============================================================================

@dataclass
class ComparableRecord:
    """Một bản ghi comparable."""
    legacy_id: int
    asset_type: str
    province_city: str
    district: str
    area_m2: float
    price: float
    price_per_m2: float
    evidence_tier: str  # E1-E5
    legal_status: str
    ward: Optional[str] = None
    age_years: Optional[int] = None
    floor: Optional[int] = None
    bedrooms: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    listing_date: Optional[str] = None
    verification_status: str = "unverified"
    similarity_score: Optional[float] = None
    match_reasons: List[str] = field(default_factory=list)
    adjustment_rationale: str = ""
    price_adjustment_vnd: int = 0


@dataclass
class AssetInput:
    """Input data cho một property (từ form hoặc API)."""
    asset_type: str  # APARTMENT|TOWNHOUSE|LAND_URBAN...
    province_city: str
    district: str
    ward: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Parcel geometry (cho LAND)
    area_m2: float = 0.0
    polygon_json: Optional[str] = None  # JSON array của [{lat, lng}, ...]
    frontage_m: Optional[float] = None
    frontage_road_class: Optional[str] = None  # MAIN_STREET|ALLEY_3M|ALLEY_2M|...
    depth_min_m: Optional[float] = None
    depth_max_m: Optional[float] = None
    taper_type: Optional[str] = None  # uniform|nö_hậu|thóp_hậu|irregular
    nö_hậu_score: Optional[float] = None
    thóp_hậu_score: Optional[float] = None
    irregularity_score: Optional[float] = None
    corner_plot: bool = False
    alley_branch_count: int = 0

    # Building (cho TOWNHOUSE, VILLA)
    built_area_m2: Optional[float] = None
    floor_count: int = 1
    bedrooms: int = 0
    bathrooms: int = 0
    facade_count: int = 1
    structure_grade: Optional[str] = None  # RC|BRICK|WOOD
    construction_year: Optional[int] = None
    main_facing: Optional[str] = None  # NORTH|SOUTH|EAST|WEST|...

    # Apartment (cho APARTMENT)
    block_name: Optional[str] = None
    apt_floor: Optional[int] = None
    view_type: Optional[str] = None  # CITY|PARK|RIVER|NOTHING|...
    door_orientation: Optional[str] = None
    balcony_orientation: Optional[str] = None
    elevator_distance: Optional[str] = None  # close|medium|far
    trash_room_distance: Optional[str] = None
    core_distance: Optional[str] = None
    sunlight_exposure: Optional[str] = None  # GOOD|FAIR|POOR
    ventilation_score: Optional[float] = None
    noise_inside_db: Optional[float] = None
    layout_score: Optional[float] = None

    # Legal
    ownership_type: Optional[str] = None  # FULL_OWNERSHIP|LURC|PENDING|DISPUTE
    planning_zone: Optional[str] = None
    road_expansion_risk: Optional[str] = None
    mortgage_flag: bool = False
    dispute_flag: bool = False

    # Environment
    flood_risk: Optional[str] = None  # none|minor|moderate|severe
    cemetery_distance_m: Optional[float] = None
    noise_day_db: Optional[float] = None
    noise_night_db: Optional[float] = None
    pollution_score: Optional[float] = None
    river_distance_m: Optional[float] = None
    park_distance_m: Optional[float] = None

    # Access
    road_width_m: Optional[float] = None
    road_class: Optional[str] = None  # MAIN_STREET|ALLEY_3M|ALLEY_2M|ALLEY_1M
    car_access: bool = True
    dead_end: bool = False

    # Spiritual (chỉ cho fit layer)
    death_history_flag: bool = False
    worship_site_distance_m: Optional[float] = None
    stigma_known: bool = False

    # IoT
    noise_level: Optional[float] = None  # từ cảm biến

    def to_hash(self) -> str:
        """Tạo SHA256 hash của input để truy ngược."""
        data = {k: v for k, v in asdict(self).items() if v is not None and v != 0}
        return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


@dataclass
class AdjustmentResult:
    """Kết quả của một adjustment factor."""
    factor_code: str
    layer: str  # MARKET|FIT
    factor_group: str
    direction: str  # POSITIVE|NEGATIVE|NEUTRAL
    delta_pct: float
    delta_vnd: int
    confidence: float
    rationale: str
    evidence_id: Optional[str] = None
    applied_rule_id: Optional[str] = None
    source_type: str = "rule"
    comparable_ids: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_code": self.factor_code,
            "layer": self.layer,
            "factor_group": self.factor_group,
            "direction": self.direction,
            "delta_pct": round(self.delta_pct, 4),
            "delta_vnd": self.delta_vnd,
            "confidence": round(self.confidence, 3),
            "rationale": self.rationale,
            "evidence_id": self.evidence_id,
            "applied_rule_id": self.applied_rule_id,
        }


@dataclass
class ValuationResult:
    """Kết quả định giá hoàn chỉnh — 3 lớp."""
    run_id: str
    property_asset_id: Optional[str]
    engine_version: str = "v2_alpha"

    # ── Market Valuation ──
    base_price_vnd: int = 0
    base_price_source: str = "comparable"
    fair_market_value_vnd: int = 0
    quick_sale_value_vnd: int = 0
    recommended_listing_vnd: int = 0
    optimistic_ask_vnd: int = 0
    expected_range_low_vnd: int = 0
    expected_range_high_vnd: int = 0
    liquidity_score: str = "medium"
    liquidity_band: float = 0.5

    # ── Adjustments ──
    market_adjustments: List[AdjustmentResult] = field(default_factory=list)
    fit_adjustments: List[AdjustmentResult] = field(default_factory=list)

    # ── Confidence & Evidence ──
    overall_confidence: float = 0.0
    confidence_grade: str = "C"
    evidence_tier: str = "E3"
    effective_sample_size: float = 0.0
    comparable_count: int = 0
    anchor_share: float = 0.0
    independent_source_count: int = 0
    data_freshness_days: int = 90
    comparable_breakdown: Dict[str, int] = field(default_factory=dict)
    interval_ratio: float = 0.10

    # ── Fit Suitability ──
    persona_fit_score: Optional[float] = None
    feng_shui_fit: Optional[float] = None
    liquidity_fit: Optional[float] = None
    family_layout_fit: Optional[float] = None

    # ── Sub-engine results ──
    geometry_metrics: Optional[Dict] = None
    legal_assessment: Optional[Dict] = None
    environment_assessment: Optional[Dict] = None

    # ── Metadata ──
    input_hash: str = ""
    run_at: str = ""
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert sang dict theo output contract."""
        return {
            "run_id": self.run_id,
            "property_asset_id": self.property_asset_id,
            "engine_version": self.engine_version,
            "market_valuation": {
                "fair_market_value": self.fair_market_value_vnd,
                "quick_sale_value": self.quick_sale_value_vnd,
                "recommended_listing": self.recommended_listing_vnd,
                "optimistic_ask": self.optimistic_ask_vnd,
                "expected_range_low": self.expected_range_low_vnd,
                "expected_range_high": self.expected_range_high_vnd,
                "liquidity_score": self.liquidity_score,
                "liquidity_band": self.liquidity_band,
                "adjustment_ledger": [a.to_dict() for a in self.market_adjustments],
                "base_price_from_comps": self.base_price_vnd,
            },
            "fit_suitability": {
                "persona_fit_score": self.persona_fit_score,
                "feng_shui_fit": self.feng_shui_fit,
                "liquidity_fit": self.liquidity_fit,
                "family_layout_fit": self.family_layout_fit,
                "adjustment_ledger": [a.to_dict() for a in self.fit_adjustments],
            },
            "confidence_evidence": {
                "overall_confidence": round(self.overall_confidence, 3),
                "confidence_grade": self.confidence_grade,
                "evidence_tier": self.evidence_tier,
                "effective_sample_size": round(self.effective_sample_size, 1),
                "comparable_count": self.comparable_count,
                "comparable_breakdown": self.comparable_breakdown,
                "interval_ratio": round(self.interval_ratio, 4),
                "warnings": self.warnings,
                "recommendations": self.recommendations,
            },
            "sub_engines": {
                "geometry_metrics": self.geometry_metrics,
                "legal_assessment": self.legal_assessment,
                "environment_assessment": self.environment_assessment,
            },
        }


# =============================================================================
# VALUATION ENGINE
# =============================================================================

class ValuationEngine:
    """
    Core valuation engine.
    Quy trình:
    1. Lấy comparable records
    2. Tính base price từ comparables
    3. Áp dụng adjustment factors (market + fit)
    4. Tính confidence từ evidence quality
    5. Sinh scenario outputs
    """

    def __init__(
        self,
        comparable_finder: Optional[callable] = None,
        evidence_loader: Optional[callable] = None,
    ):
        """
        Args:
            comparable_finder: Hàm tìm comparables.
                               Signature: (AssetInput) -> List[ComparableRecord]
            evidence_loader: Hàm load evidence cho property.
                           Signature: (property_asset_id) -> List[EvidenceRecord]
        """
        self.registry = AdjustmentRegistry()
        self.comparable_finder = comparable_finder or self._default_comparable_finder
        self.evidence_loader = evidence_loader

    def run(self, asset_input: AssetInput, persona_id: Optional[str] = None) -> ValuationResult:
        """
        Pure computation engine — KHÔNG tự chạy sub-engines.
        Sub-engines (legal, geometry, env) do PipelineOrchestrator quản lý.
        Engine chỉ nhận input đã enriched và tính: base_price → adjustments → scenarios.
        """
        run_id = str(uuid4())
        input_hash = asset_input.to_hash()

        # Step 1: Lấy comparables
        comparables = self.comparable_finder(asset_input)

        # Step 2: Tính base price từ comparables
        base_price, comp_stats = self._compute_base_price(asset_input, comparables)

        # Step 3: Tính market adjustments (geometry, access, building, apartment)
        market_adj = self._compute_market_adjustments(asset_input, base_price, comparables)

        # Step 4: Tính fit adjustments (spiritual/belief)
        fit_adj = self._compute_fit_adjustments(asset_input, base_price)

        # Step 5: Tính fair market value
        total_market_adj_vnd = sum(a.delta_vnd for a in market_adj)
        fair_market = base_price + total_market_adj_vnd
        fair_market = max(50_000_000, min(fair_market, 100_000_000_000))

        # Step 6: Tính confidence
        confidence, grade, tier, stats = self._compute_confidence(
            comparables, market_adj, asset_input
        )

        # Step 7: Scenario outputs
        scenarios = self._generate_scenarios(
            fair_market, confidence, market_adj, comparables
        )

        # Step 8: Liquidity
        liquidity_score, liquidity_band = self._compute_liquidity(
            asset_input, market_adj, comparables
        )

        # Step 9: Warnings & Recommendations
        warnings, recommendations = self._generate_warnings_and_recommendations(
            asset_input, comparables, market_adj, stats, confidence, grade
        )

        return ValuationResult(
            run_id=run_id,
            property_asset_id=None,
            engine_version="v3.1_pure_20260426",
            base_price_vnd=base_price,
            base_price_source="comparable",
            fair_market_value_vnd=fair_market,
            quick_sale_value_vnd=scenarios["quick_sale"],
            recommended_listing_vnd=scenarios["listing"],
            optimistic_ask_vnd=scenarios["optimistic"],
            expected_range_low_vnd=scenarios["range_low"],
            expected_range_high_vnd=scenarios["range_high"],
            liquidity_score=liquidity_score,
            liquidity_band=liquidity_band,
            market_adjustments=market_adj,
            fit_adjustments=fit_adj,
            overall_confidence=confidence,
            confidence_grade=grade,
            evidence_tier=tier,
            effective_sample_size=stats.get("effective_sample_size", 0.0),
            comparable_count=len(comparables),
            anchor_share=stats.get("anchor_share", 0.0),
            independent_source_count=stats.get("independent_source_count", 0),
            data_freshness_days=stats.get("data_freshness_days", 90),
            comparable_breakdown=stats.get("tier_breakdown", {}),
            interval_ratio=scenarios["interval_ratio"],
            input_hash=input_hash,
            run_at=datetime.now().isoformat(),
            warnings=warnings,
            recommendations=recommendations,
        )

    def _default_comparable_finder(self, asset_input: AssetInput) -> List[ComparableRecord]:
        """Fallback: trả về empty list."""
        return []

    def _compute_base_price(
        self,
        asset_input: AssetInput,
        comparables: List[ComparableRecord],
    ) -> tuple[int, Dict[str, Any]]:
        """
        Tính base price từ comparables.
        Dùng weighted median theo evidence tier.
        """
        if not comparables:
            # Fallback: dùng estimate dựa trên location
            estimate = self._location_estimate(asset_input)
            return estimate, {}

        # Lọc comparables cùng district → cùng province
        # CRITICAL: chỉ dùng comparable CÙNG LOẠI BĐS
        from src.domain.valuation.pipeline_orchestrator import _workflow_category
        target_category = _workflow_category(asset_input.asset_type)
        
        type_comps = [c for c in comparables 
                      if hasattr(c, 'property_type') and 
                      _workflow_category(c.property_type or '') == target_category]
        if not type_comps:
            type_comps = comparables  # fallback nếu không có type info
            
        district_comps = [c for c in type_comps if c.district == asset_input.district]
        province_comps = [
            c for c in type_comps
            if c.province_city == asset_input.province_city and c not in district_comps
        ]
        target_comps = district_comps or province_comps

        if not target_comps:
            target_comps = comparables

        # Weighted median theo evidence tier
        tier_weights = {"E1": 1.0, "E2": 0.85, "E3": 0.65, "E4": 0.35, "E5": 0.15}
        weights = [tier_weights.get(c.evidence_tier, 0.3) for c in target_comps]
        total_weight = sum(weights) or 1.0

        # Weighted mean price_per_m2
        weighted_sum = sum(c.price_per_m2 * w for c, w in zip(target_comps, weights))
        avg_price_per_m2 = weighted_sum / total_weight

        # Estimate từ area — chọn đúng loại diện tích theo type
        if asset_input.asset_type in ("APARTMENT", "STUDIO", "PENTHOUSE", "DUPLEX"):
            # Chung cư: diện tích thông thủy (usable/built area)
            target_area = asset_input.built_area_m2 or asset_input.area_m2 or 65.0
        elif asset_input.asset_type in ("TOWNHOUSE", "VILLA", "SHOPHOUSE", "HOUSE"):
            # Nhà phố/biệt thự: diện tích sàn xây dựng
            target_area = asset_input.built_area_m2 or asset_input.area_m2 or 100.0
        else:
            # Đất nền: diện tích đất
            target_area = asset_input.area_m2 or 100.0
        base_price = int(avg_price_per_m2 * target_area)

        # Stats
        tier_breakdown: Dict[str, int] = {}
        for c in target_comps:
            tier_breakdown[c.evidence_tier] = tier_breakdown.get(c.evidence_tier, 0) + 1
        anchor_share = (tier_breakdown.get("E1", 0) + tier_breakdown.get("E2", 0)) / max(len(target_comps), 1)

        return base_price, {
            "avg_price_per_m2": avg_price_per_m2,
            "tier_breakdown": tier_breakdown,
            "anchor_share": anchor_share,
            "effective_sample_size": total_weight,
            "independent_source_count": len({c.evidence_tier for c in target_comps}),
        }

    def _location_estimate(self, asset_input: AssetInput) -> int:
        """Estimate fallback dựa trên location + asset type.
        
        Mỗi loại BĐS có giá/m2 khác nhau tại cùng vị trí:
        - Đất nền: giá đất thuần (cao nhất)
        - Chung cư: giá sàn thông thủy  
        - Nhà phố: giá bao gồm đất + công trình
        - Biệt thự: giá đất + khuôn viên
        """
        norm = normalize_province(asset_input.province_city) or asset_input.province_city
        price_per_m2 = get_base_price_per_m2(norm, asset_input.asset_type)
        
        # Chọn diện tích phù hợp theo loại BĐS
        if asset_input.asset_type in ("APARTMENT", "STUDIO", "PENTHOUSE", "DUPLEX"):
            area = asset_input.built_area_m2 or asset_input.area_m2 or 65.0
        else:
            area = asset_input.area_m2 or 100.0
        return int(price_per_m2 * area)

    def _compute_market_adjustments(
        self,
        asset_input: AssetInput,
        base_price: int,
        comparables: List[ComparableRecord],
    ) -> List[AdjustmentResult]:
        """
        Tính tất cả market adjustments.
        Mỗi adjustment được sinh từ asset_input data + registry.
        """
        results: List[AdjustmentResult] = []
        area = asset_input.area_m2 or asset_input.built_area_m2 or 100.0

        # NOTE: Legal & Environment adjustments are injected by PipelineOrchestrator
        # (see pipeline_orchestrator.py gate 4 & 6). Engine chỉ xử lý:
        # L2 Geometry, L3 Access, L5 Building, L6 Apartment

        # ── L2: Geometry (chỉ LAND) ─────────────────────────────────────────
        from src.domain.property_types import to_canonical, PropertyType
        asset_canonical = to_canonical(asset_input.asset_type)

        if asset_canonical == PropertyType.LAND:
            if (asset_input.nö_hậu_score or 0) >= 0.8:
                results.append(self._make_adjustment("GEOM_NÖHẬU", base_price, area, asset_input=asset_input))
            elif (asset_input.thóp_hậu_score or 0) >= 0.6:
                results.append(self._make_adjustment("GEOM_THOP_HAU", base_price, area, asset_input=asset_input))
            elif (asset_input.thóp_hậu_score or 0) >= 0.8:
                results.append(self._make_adjustment("GEOM_THOP_HAU_SEVERE", base_price, area, asset_input=asset_input))

            if asset_input.taper_type == "irregular":
                # Irregular shape
                pass  # GEOM_IRREGULAR

            if asset_input.corner_plot:
                results.append(self._make_adjustment("GEOM_CORNER_PLOT", base_price, area, asset_input=asset_input))

            depth_avg = (asset_input.depth_min_m + asset_input.depth_max_m) / 2 if asset_input.depth_max_m else None
            if depth_avg and depth_avg >= 60:
                results.append(self._make_adjustment("DEPTH_60_PLUS", base_price, area, asset_input=asset_input))

        # ── L3: Access (chỉ BĐS có tiếp cận đường trực tiếp) ──────────────
        # Chung cư KHÔNG có road_class/alley — đường vào là property của chung cư
        if asset_canonical != PropertyType.APARTMENT:
            if asset_input.road_class == "MAIN_STREET":
                results.append(self._make_adjustment("ACCESS_MAIN_STREET", base_price, area, asset_input=asset_input))
            elif asset_input.road_class == "ALLEY_5M":
                results.append(self._make_adjustment("ACCESS_ALLEY_5M", base_price, area, asset_input=asset_input))
            elif asset_input.road_class == "ALLEY_3M":
                results.append(self._make_adjustment("ACCESS_ALLEY_3M", base_price, area, asset_input=asset_input))
            elif asset_input.road_class == "ALLEY_2M":
                results.append(self._make_adjustment("ACCESS_ALLEY_2M", base_price, area, asset_input=asset_input))
            elif asset_input.road_class == "ALLEY_1M":
                results.append(self._make_adjustment("ACCESS_ALLEY_1M", base_price, area, asset_input=asset_input))

            if asset_input.dead_end:
                results.append(self._make_adjustment("ACCESS_DEAD_END", base_price, area, asset_input=asset_input))

            if asset_input.alley_branch_count > 0:
                results.append(self._make_adjustment("ACCESS_ALLEY_BRANCH", base_price, area, asset_input=asset_input))

        # NOTE: Environment adjustments handled by EnvironmentRiskEngine
        # (see pipeline_orchestrator.py gate 6)

        # ── L5: Building (TOWNHOUSE, VILLA, HOUSE) ─────────────────────────────
        if asset_canonical in {PropertyType.TOWNHOUSE, PropertyType.VILLA, PropertyType.HOUSE}:
            age = None
            if asset_input.construction_year:
                age = datetime.now().year - asset_input.construction_year
            if age is not None and age <= 5:
                results.append(self._make_adjustment(
                    "BLDG_NEW_5Y", base_price, area,
                    applied_rule_id=f"bldg_age_{age}",
                    asset_input=asset_input,
                ))
            elif age is not None and age >= 20:
                results.append(self._make_adjustment(
                    "BLDG_OLD_20Y", base_price, area,
                    applied_rule_id=f"bldg_age_{age}",
                    asset_input=asset_input,
                ))

            if asset_input.floor_count > 4:
                results.append(self._make_adjustment("BLDG_FLOORS_EXCEED", base_price, area, asset_input=asset_input))

        # ── L6: Apartment ──────────────────────────────────────────────────
        if asset_canonical == PropertyType.APARTMENT:
            if asset_input.view_type == "RIVER":
                results.append(self._make_adjustment("APT_VIEW_RIVER", base_price, area, asset_input=asset_input))
            elif asset_input.view_type == "CITY":
                results.append(self._make_adjustment("APT_VIEW_CITY", base_price, area, asset_input=asset_input))
            elif asset_input.view_type == "NOTHING":
                results.append(self._make_adjustment("APT_NO_VIEW", base_price, area, asset_input=asset_input))

            floor = asset_input.apt_floor or 0
            if floor >= 15:
                results.append(self._make_adjustment("APT_FLOOR_HIGH_15P", base_price, area, asset_input=asset_input))
            elif 0 < floor <= 3:
                results.append(self._make_adjustment("APT_FLOOR_LOW_3M", base_price, area, asset_input=asset_input))

            if asset_input.trash_room_distance == "close":
                results.append(self._make_adjustment("APT_TRASH_NEAR", base_price, area, asset_input=asset_input))

            if asset_input.core_distance == "adjacent":
                results.append(self._make_adjustment("APT_CORE_ADJACENT", base_price, area, asset_input=asset_input))

            if asset_input.sunlight_exposure == "POOR":
                results.append(self._make_adjustment("APT_SUNLIGHT_WEST_STRONG", base_price, area, asset_input=asset_input))

            if (asset_input.ventilation_score or 1.0) < 0.4:
                results.append(self._make_adjustment("APT_VENTILATION_POOR", base_price, area, asset_input=asset_input))

        # IoT noise level override
        if asset_input.noise_level and asset_input.noise_level >= 65:
            # Check if not already added via noise_day_db
            if not any(a.factor_code == "NOISE_DAY_65DB" for a in results):
                results.append(self._make_adjustment("NOISE_DAY_65DB", base_price, area, asset_input=asset_input))

        # Sort: positive trước, negative sau
        results.sort(key=lambda x: (0 if x.direction == "POSITIVE" else 1, x.delta_vnd), reverse=True)

        return results

    def _compute_fit_adjustments(
        self,
        asset_input: AssetInput,
        base_price: int,
    ) -> List[AdjustmentResult]:
        """Fit adjustments — spiritual/belief factors + F1-F4 registry factors.

        Per SPEC: FIT layer tách biệt khỏi market value. Đây là các yếu tố
        phong thủy (F1), tâm linh (F2), gia đình (F3), đầu tư (F4).
        """
        from src.domain.valuation.adjustment_registry import FACTOR_REGISTRY
        from src.domain.valuation.adjustment_registry import AdjustmentLayer, FactorGroup
        from src.domain.property_types import to_canonical, is_applicable_factor, PropertyType

        results: List[AdjustmentResult] = []
        asset_canonical = to_canonical(asset_input.asset_type)

        # ── F1 FENG_SHUI adjustments (from registry) ──────────────────────────
        for code, adj in FACTOR_REGISTRY.items():
            if adj.layer != AdjustmentLayer.FIT or adj.group != FactorGroup.F1_FENG_SHUI:
                continue
            if not is_applicable_factor(code, asset_input.asset_type):
                continue

            # Only apply if we have orientation data
            if adj.factor_code == "FIT_ORIENTATION_NORTH" and asset_input.main_facing == "NORTH":
                results.append(self._make_fit_adjustment(adj, base_price,
                    f"Hướng Bắc — {adj.rationale_template}"))
            elif adj.factor_code == "FIT_ORIENTATION_SOUTH" and asset_input.main_facing == "SOUTH":
                results.append(self._make_fit_adjustment(adj, base_price,
                    f"Hướng Nam — {adj.rationale_template}"))
            elif adj.factor_code == "FIT_ORIENTATION_EAST" and asset_input.main_facing == "EAST":
                results.append(self._make_fit_adjustment(adj, base_price,
                    f"Hướng Đông — {adj.rationale_template}"))
            elif adj.factor_code == "FIT_ORIENTATION_BAD" and asset_input.main_facing in ("SOUTHWEST", "NORTHEAST"):
                results.append(self._make_fit_adjustment(adj, base_price,
                    f"Hướng {asset_input.main_facing} — {adj.rationale_template}"))
            elif adj.factor_code == "FIT_LAND_SHAPE_HARMONY":
                # Land: positive for regular shapes
                if asset_input.taper_type == "regular" or not asset_input.taper_type:
                    results.append(self._make_fit_adjustment(adj, base_price,
                        f"Đất hình vuông — {adj.rationale_template}"))

        # ── F2 SPIRITUAL adjustments (from registry) ──────────────────────────
        for code, adj in FACTOR_REGISTRY.items():
            if adj.layer != AdjustmentLayer.FIT or adj.group != FactorGroup.F2_SPIRITUAL:
                continue
            if not is_applicable_factor(code, asset_input.asset_type):
                continue

            if adj.factor_code == "FIT_FLOOR_NUMBER_LUCKY":
                # Apartment: lucky floors 6, 8, 9
                floor = asset_input.apt_floor or 0
                if floor in {6, 8, 9}:
                    results.append(self._make_fit_adjustment(adj, base_price,
                        f"Tầng {floor} — số may mắn"))

        # ── F3 FAMILY adjustments (from registry) ──────────────────────────────
        for code, adj in FACTOR_REGISTRY.items():
            if adj.layer != AdjustmentLayer.FIT or adj.group != FactorGroup.F3_FAMILY:
                continue
            if not is_applicable_factor(code, asset_input.asset_type):
                continue

            if adj.factor_code == "FIT_BEDROOM_BALANCE":
                beds = asset_input.bedrooms or 0
                if 2 <= beds <= 4:
                    results.append(self._make_fit_adjustment(adj, base_price,
                        f"{beds} phòng ngủ cân đối cho gia đình"))

        # ── F4 INVESTMENT adjustments (from registry) ──────────────────────────
        for code, adj in FACTOR_REGISTRY.items():
            if adj.layer != AdjustmentLayer.FIT or adj.group != FactorGroup.F4_INVESTMENT:
                continue
            if not is_applicable_factor(code, asset_input.asset_type):
                continue

            if adj.factor_code == "FIT_LIQUIDITY_HIGH":
                # Apartment + townhouse in urban districts = high liquidity
                if asset_canonical in {PropertyType.APARTMENT, PropertyType.TOWNHOUSE}:
                    results.append(self._make_fit_adjustment(adj, base_price,
                        f"BĐS thanh khoản cao tại {asset_input.district}"))
            elif adj.factor_code == "FIT_LIQUIDITY_LOW":
                if asset_canonical in {PropertyType.LAND, PropertyType.VILLA}:
                    results.append(self._make_fit_adjustment(adj, base_price,
                        f"BĐS {asset_canonical.value} có thanh khoản thấp"))
            elif adj.factor_code == "FIT_GROWTH_METRO":
                if asset_canonical in {PropertyType.APARTMENT, PropertyType.TOWNHOUSE}:
                    # Metro proximity from district (simplified proxy)
                    results.append(self._make_fit_adjustment(adj, base_price,
                        f"Tiềm năng tăng giá từ quy hoạch metro"))
            elif adj.factor_code == "FIT_GROWTH_NEWTOWN":
                # New town / urban expansion districts
                if asset_input.district and any(kw in asset_input.district for kw in ['Mỹ', 'Thủ', 'Đức', 'Phú', 'Vinhomes']):
                    results.append(self._make_fit_adjustment(adj, base_price,
                        f"Khu đô thị mới — hạ tầng đang phát triển"))
            elif adj.factor_code == "FIT_YIELD_RENTAL":
                if asset_canonical == PropertyType.APARTMENT:
                    results.append(self._make_fit_adjustment(adj, base_price,
                        f"Căn hộ cho thuê — tỷ lệ lấp đầy cao"))

        # ── Legacy spiritual factors (death/stigma/worship) ────────────────────
        if asset_input.death_history_flag:
            results.append(AdjustmentResult(
                factor_code="FIT_DEATH_HISTORY",
                layer="FIT",
                factor_group="SPIRITUAL",
                direction="NEGATIVE",
                delta_pct=-0.15,
                delta_vnd=int(base_price * -0.15),
                confidence=0.70,
                rationale="Nhà có lịch sử chết bất thường — ảnh hưởng tâm lý người mua.",
                source_type="belief",
            ))

        if asset_input.stigma_known:
            results.append(AdjustmentResult(
                factor_code="FIT_STIGMA",
                layer="FIT",
                factor_group="SPIRITUAL",
                direction="NEGATIVE",
                delta_pct=-0.10,
                delta_vnd=int(base_price * -0.10),
                confidence=0.65,
                rationale="Tài sản có stigma (vấn đề tâm linh/xã hội).",
                source_type="belief",
            ))

        if asset_input.worship_site_distance_m and asset_input.worship_site_distance_m < 50:
            results.append(AdjustmentResult(
                factor_code="FIT_WORSHIP_NEAR",
                layer="FIT",
                factor_group="SPIRITUAL",
                direction="NEGATIVE",
                delta_pct=-0.05,
                delta_vnd=int(base_price * -0.05),
                confidence=0.55,
                rationale=f"Gần cơ sở thờ tự ({asset_input.worship_site_distance_m:.0f}m).",
                source_type="belief",
            ))

        return results

    def _make_fit_adjustment(self, adjustment, base_price: int, rationale: str) -> AdjustmentResult:
        """Create a fit adjustment result from registry Adjustment."""
        delta_vnd = int(base_price * adjustment.delta_pct_base)
        direction = "POSITIVE" if adjustment.delta_pct_base > 0 else "NEGATIVE" if adjustment.delta_pct_base < 0 else "NEUTRAL"
        return AdjustmentResult(
            factor_code=adjustment.factor_code,
            layer="FIT",
            factor_group=adjustment.group.value,
            direction=direction,
            delta_pct=adjustment.delta_pct_base,
            delta_vnd=delta_vnd,
            confidence=adjustment.confidence_base,
            rationale=rationale,
            source_type="registry",
        )

    def _compute_confidence(
        self,
        comparables: List[ComparableRecord],
        adjustments: List[AdjustmentResult],
        asset_input: AssetInput,
    ) -> tuple[float, str, str, Dict[str, Any]]:
        """
        Tính mức độ tin cậy dự đoán.

        Quy tắc sản phẩm: số lượng comparable gần giống là điều kiện có trọng
        số cao nhất. Mốc A về số lượng là >= 800 mẫu đạt ngưỡng similarity.
        Vì vậy đa số dự đoán thực tế với vài chục mẫu không thể có confidence
        cao, dù evidence tier của các mẫu đó tốt.
        """
        if not comparables:
            return 0.10, "D", "E5", {
                "effective_sample_size": 0.0,
                "anchor_share": 0.0,
                "sample_count": 0,
                "sample_score": 0.0,
                "avg_similarity": 0.0,
                "independent_source_count": 0,
                "data_freshness_days": 90,
                "tier_breakdown": {},
            }

        tier_weights = {"E1": 1.0, "E2": 0.85, "E3": 0.65, "E4": 0.35, "E5": 0.15}
        tier_breakdown: Dict[str, int] = {}
        weighted_sum = 0.0
        total_weight = 0.0

        for c in comparables:
            w = tier_weights.get(c.evidence_tier, 0.3)
            weighted_sum += w * w  # square for emphasis on high-quality
            total_weight += w
            tier_breakdown[c.evidence_tier] = tier_breakdown.get(c.evidence_tier, 0) + 1

        anchor_share = (tier_breakdown.get("E1", 0) + tier_breakdown.get("E2", 0)) / max(len(comparables), 1)
        avg_evidence_weight = total_weight / max(len(comparables), 1)
        similarity_values = [
            c.similarity_score for c in comparables
            if c.similarity_score is not None
        ]
        avg_similarity = sum(similarity_values) / len(similarity_values) if similarity_values else 0.50

        # Effective sample size (Neff approximation)
        neff = sum(
            tier_weights.get(c.evidence_tier, 0.3) * 0.5
            for c in comparables
        )

        sample_count = len(comparables)
        sample_score = min(sample_count / 800.0, 1.0)

        # Số lượng là trụ chính: 55 điểm. Chất lượng/evidence/similarity chỉ
        # bổ trợ, không được phép kéo vài chục mẫu lên mức xanh cao.
        sample_component = sample_score * 0.55
        anchor_component = anchor_share * 0.15
        evidence_component = avg_evidence_weight * 0.10
        similarity_component = avg_similarity * 0.10

        adjustment_count = len([a for a in adjustments if a.layer == "MARKET"])
        coverage_component = min(0.05, adjustment_count * 0.01)
        geo_component = 0.05 if asset_input.latitude and asset_input.longitude else 0.0

        confidence = min(
            0.95,
            max(
                0.10,
                sample_component
                + anchor_component
                + evidence_component
                + similarity_component
                + coverage_component
                + geo_component,
            ),
        )

        # Grade
        if sample_count >= 800 and confidence >= 0.85:
            grade = "A"
        elif sample_count >= 300 and confidence >= 0.70:
            grade = "B"
        elif confidence >= 0.45:
            grade = "C"
        else:
            grade = "D"

        # Evidence tier (dominant tier in comparable set)
        dominant_tier = max(tier_breakdown.items(), key=lambda x: x[1])[0] if tier_breakdown else "E5"

        stats = {
            "effective_sample_size": round(neff, 1),
            "anchor_share": round(anchor_share, 3),
            "sample_count": sample_count,
            "sample_score": round(sample_score, 3),
            "avg_similarity": round(avg_similarity, 3),
            "independent_source_count": len(tier_breakdown),
            "data_freshness_days": 90,
            "tier_breakdown": tier_breakdown,
        }

        return confidence, grade, dominant_tier, stats

    def _generate_scenarios(
        self,
        fair_market: int,
        confidence: float,
        adjustments: List[AdjustmentResult],
        comparables: List[ComparableRecord],
    ) -> Dict[str, Any]:
        """
        Sinh scenario outputs từ fair market value.
        """
        # Liquidity discount
        if confidence >= 0.85:
            liquidity_discount = 0.05
        elif confidence >= 0.70:
            liquidity_discount = 0.07
        elif confidence >= 0.55:
            liquidity_discount = 0.10
        else:
            liquidity_discount = 0.15

        # Adjustments spread bonus
        adj_spread = sum(abs(a.delta_pct) for a in adjustments)
        if adj_spread > 0.20:
            liquidity_discount += 0.02

        quick_sale = int(fair_market * (1 - liquidity_discount))
        listing_premium = 0.04 + (confidence * 0.03)
        optimistic_premium = 0.08 + (confidence * 0.05)
        listing = int(fair_market * (1 + listing_premium))
        optimistic = int(fair_market * (1 + optimistic_premium))

        # Confidence interval
        if confidence >= 0.85:
            interval_ratio = 0.05
        elif confidence >= 0.70:
            interval_ratio = 0.08
        elif confidence >= 0.55:
            interval_ratio = 0.12
        else:
            interval_ratio = 0.18

        range_low = int(fair_market * (1 - interval_ratio))
        range_high = int(fair_market * (1 + interval_ratio))

        return {
            "quick_sale": quick_sale,
            "listing": listing,
            "optimistic": optimistic,
            "range_low": range_low,
            "range_high": range_high,
            "interval_ratio": interval_ratio,
        }

    def _compute_liquidity(
        self,
        asset_input: AssetInput,
        adjustments: List[AdjustmentResult],
        comparables: List[ComparableRecord],
    ) -> tuple[str, float]:
        """Tính liquidity score."""
        score = 0.5

        # Access bonus
        if asset_input.road_class == "MAIN_STREET":
            score += 0.2
        elif asset_input.road_class == "ALLEY_5M":
            score += 0.1
        elif asset_input.road_class in ("ALLEY_2M", "ALLEY_1M"):
            score -= 0.2

        if asset_input.dead_end:
            score -= 0.1

        # Market depth bonus
        if len(comparables) >= 10:
            score += 0.1
        elif len(comparables) >= 5:
            score += 0.05

        # Negative adjustments
        negative_adj_count = len([a for a in adjustments if a.direction == "NEGATIVE"])
        score -= negative_adj_count * 0.02

        score = max(0.0, min(1.0, score))

        if score >= 0.70:
            return "high", round(score, 2)
        elif score >= 0.40:
            return "medium", round(score, 2)
        else:
            return "low", round(score, 2)

    def _generate_warnings_and_recommendations(
        self,
        asset_input: AssetInput,
        comparables: List[ComparableRecord],
        adjustments: List[AdjustmentResult],
        stats: Dict[str, Any],
        confidence: float,
        grade: str,
    ) -> tuple[List[str], List[str]]:
        """Sinh warnings và recommendations."""
        warnings: List[str] = []
        recommendations: List[str] = []

        if not comparables:
            warnings.append("Không có comparable trong cùng quận — base price từ estimate location.")

        anchor_share = stats.get("anchor_share", 0.0)
        if anchor_share == 0:
            warnings.append("Không có comparable E1/E2 trong dataset — confidence bị cap.")

        if stats.get("effective_sample_size", 0) < 10:
            warnings.append("Effective sample size thấp — kết quả chỉ mang tính tham khảo.")

        sample_count = stats.get("sample_count", len(comparables))
        if sample_count < 800:
            warnings.append(
                f"Số mẫu gần giống đạt ngưỡng là {sample_count}/800 — chưa đủ điều kiện mức A về số lượng."
            )

        if len([a for a in adjustments if a.layer == "MARKET"]) < 5:
            recommendations.append("Bổ sung thêm thông tin để áp dụng nhiều adjustment factors hơn.")

        if not asset_input.latitude or not asset_input.longitude:
            warnings.append("Thiếu tọa độ GPS — geocode quality thấp, confidence bị giảm.")

        if confidence < 0.55:
            warnings.append(f"Confidence grade {grade} — cần bổ sung bằng chứng trước khi dùng cho quyết định.")

        return warnings, recommendations

    def _make_adjustment(
        self,
        factor_code: str,
        base_price: int,
        area: float,
        applied_rule_id: Optional[str] = None,
        asset_input: Optional[AssetInput] = None,
    ) -> AdjustmentResult:
        """Sinh AdjustmentResult từ factor_code."""
        factor = self.registry.get(factor_code)
        if not factor:
            return AdjustmentResult(
                factor_code=factor_code,
                layer="MARKET",
                factor_group="UNKNOWN",
                direction="NEUTRAL",
                delta_pct=0.0,
                delta_vnd=0,
                confidence=0.0,
                rationale=f"Không tìm thấy factor {factor_code} trong registry.",
            )

        delta_vnd = int(base_price * factor.delta_pct_base)

        return AdjustmentResult(
            factor_code=factor_code,
            layer=factor.layer.value,
            factor_group=factor.group.value,
            direction="POSITIVE" if factor.delta_pct_base > 0 else ("NEGATIVE" if factor.delta_pct_base < 0 else "NEUTRAL"),
            delta_pct=factor.delta_pct_base,
            delta_vnd=delta_vnd,
            confidence=factor.confidence_base,
            rationale=factor.rationale_template.format(**{
                "certificate_type": (asset_input.ownership_type if asset_input else "Sổ đỏ"),
                "width": (asset_input.road_width_m if asset_input else 8.0),
                "count": (asset_input.frontage_m if asset_input else 1),
                "bank": "ngân hàng",
                "min_width": (asset_input.depth_min_m if asset_input else 5.0),
                "avg_width": (asset_input.frontage_m if asset_input else 5.0),
                "depth": (asset_input.depth_max_m if asset_input else 30.0),
                "taper_pct": 15,
                "floor": (asset_input.apt_floor or 1) if asset_input else 1,
                "age": (datetime.now().year - (asset_input.construction_year or 2020)) if asset_input else 5,
                "year": (asset_input.construction_year or 2020) if asset_input else 2020,
                "allowed": 4,
                "frequency": "mỗi năm",
                "distance": (asset_input.cemetery_distance_m or 200) if asset_input else 200,
                "db": (asset_input.noise_day_db or 65) if asset_input else 65,
                "ratio": 1.5,
                "source": "bản đồ ngập",
                "dispute_type": "tranh chấp đất đai",
            }),
            applied_rule_id=applied_rule_id,
            source_type="rule",
        )
