"""
Impact Engine — Contextual Comparable-SHAP δ% Algorithm.

Luồng:
  Input form → Comparable selection (4 levels, weighted) →
  Baseline price → ML model predict (log price) →
  SHAP với background = comparable pool →
  Raw δ% → Display δ% (clamp ±15%) →
  Missing data impact → Scenario projections

Key principle:
  - SHAP phải chạy với background = comparable pool (không phải toàn dataset)
  - δ% clamp ở tầng HIỂN THỊ, không phải tầng model
  - Missing data: tách rõ price effect vs. confidence loss
  - What-if scenarios: simulation, KHÔNG phải prediction
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.domain.valuation.engine import AssetInput
from src.config.province_config import SCOPE_DISTRICTS, normalize_province


# =============================================================================
# FIELD LABELS & SEMANTICS
# =============================================================================

FIELD_LABELS: Dict[str, str] = {
    # Canonical field names
    "area_m2": "Diện tích",
    "bedrooms": "Số phòng ngủ",
    "bathrooms": "Số phòng vệ sinh",
    "floor_count": "Số tầng",
    "frontage_m": "Chiều rộng mặt tiền",
    "road_width_m": "Chiều rộng đường",
    "road_class": "Loại đường tiếp cận",
    "built_area_m2": "Diện tích sàn xây dựng",
    "apt_floor": "Tầng căn hộ",
    "view_type": "Loại view",
    "ownership_type": "Pháp lý",
    "planning_zone": "Quy hoạch",
    "flood_risk": "Ngập lụt",
    "latitude": "Tọa độ GPS",
    "longitude": "Tọa độ GPS",
    "construction_year": "Năm xây dựng",
    "corner_plot": "Đất góc",
    "nö_hậu_score": "Tỷ lệ nở hậu",
    "thóp_hậu_score": "Tỷ lệ thóp hậu",
    "main_facing": "Hướng nhà",
    "cemetery_distance_m": "Khoảng cách nghĩa trang",
    "park_distance_m": "Khoảng cách công viên",
    "river_distance_m": "Khoảng cách sông",
    "noise_day_db": "Tiếng ồn ban ngày",
    "noise_night_db": "Tiếng ồn ban đêm",
    "structure_grade": "Cấp công trình",
    "noise_level": "Mức ồn cảm biến",
    "ventilation_score": "Điểm thông gió",
    "layout_score": "Điểm bố trí",
    "block_name": "Tên block/tòa",
    "elevation": "Độ cao",
    "orientation": "Hướng",
    "certificated": "Có sổ đỏ",
    # MLPipeline SHAP feature name variants (normalized features)
    "area_m2_norm": "Diện tích",
    "bedrooms_norm": "Số phòng ngủ",
    "bathrooms_norm": "Số phòng vệ sinh",
    "latitude_norm": "Tọa độ GPS",
    "longitude_norm": "Tọa độ GPS",
    "noise_level_norm": "Mức ồn cảm biến",
    "nö_hậu_score_norm": "Tỷ lệ nở hậu",
    "thóp_hậu_score_norm": "Tỷ lệ thóp hậu",
    "irregularity_score_norm": "Tính quy luật",
    "ventilation_score_norm": "Điểm thông gió",
    "layout_score_norm": "Điểm bố trí",
    "frontage_m_norm": "Chiều rộng mặt tiền",
    "built_area_m2_norm": "Diện tích sàn xây dựng",
    "cemetery_distance_m_norm": "Khoảng cách nghĩa trang",
    "river_distance_m_norm": "Khoảng cách sông",
    "park_distance_m_norm": "Khoảng cách công viên",
    "worship_site_distance_m_norm": "Khoảng cách nơi thờ cúng",
    "road_width_norm": "Chiều rộng đường",
    "depth_min_m_norm": "Chiều sâu tối thiểu",
    "depth_max_m_norm": "Chiều sâu tối đa",
    # Catch-all fallback for any raw SHAP feature names
    "RESIDUAL": "Tương tác / Residual",
}

# Positive direction: giá trị CAO hơn → tác động TÍCH CỰC
# Negative direction: giá trị CAO hơn → tác động TIÊU CỰC
FIELD_SEMANTICS: Dict[str, str] = {
    "area_m2": "positive",
    "bedrooms": "positive",
    "bathrooms": "positive",
    "floor_count": "positive",
    "frontage_m": "positive",
    "road_width_m": "positive",
    "road_class": "positive",
    "built_area_m2": "positive",
    "apt_floor": "positive",
    "view_type": "positive",
    "ownership_type": "positive",
    "planning_zone": "positive",
    "flood_risk": "negative",
    "latitude": "neutral",
    "longitude": "neutral",
    "construction_year": "negative",
    "corner_plot": "positive",
    "nö_hậu_score": "positive",
    "thóp_hậu_score": "negative",
    "main_facing": "positive",
    "cemetery_distance_m": "positive",
    "park_distance_m": "positive",
    "river_distance_m": "positive",
    "noise_day_db": "negative",
    "noise_night_db": "negative",
    "structure_grade": "positive",
    "noise_level": "negative",
    "ventilation_score": "positive",
    "layout_score": "positive",
}

# Baseline confidence loss per missing field
MISSING_CONFIDENCE_PENALTY: Dict[str, float] = {
    "ownership_type": 12.0,
    "planning_zone": 10.0,
    "road_width_m": 7.0,
    "road_class": 9.0,
    "latitude": 5.0,
    "longitude": 5.0,
    "area_m2": 8.0,
    "bedrooms": 4.0,
    "bathrooms": 3.0,
    "floor_count": 4.0,
    "frontage_m": 6.0,
    "flood_risk": 6.0,
    "construction_year": 5.0,
    "apt_floor": 4.0,
    "view_type": 5.0,
    "built_area_m2": 7.0,
    "cemetery_distance_m": 3.0,
    "park_distance_m": 2.0,
    "noise_day_db": 4.0,
    "noise_night_db": 4.0,
    "noise_level": 4.0,
    "ventilation_score": 3.0,
    "layout_score": 3.0,
    "main_facing": 3.0,
    "corner_plot": 4.0,
}

# Fields that have a natural categorical ordering
ROAD_CLASS_ORDER = ["ALLEY_1M", "ALLEY_2M", "ALLEY_3M", "ALLEY_5M", "MAIN_STREET"]
VIEW_TYPE_ORDER = ["NOTHING", "CITY", "PARK", "RIVER"]
OWNERSHIP_ORDER = ["PENDING", "LURC", "DISPUTE", "MORTGAGE", "FULL_OWNERSHIP"]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ComparableCandidate:
    """Một comparable record với trọng số."""
    id: int
    area_m2: float
    price: float
    price_per_m2: float
    district: str
    province_city: str
    property_type: str
    evidence_tier: str
    legal_status: str
    road_width_m: Optional[float]
    bedrooms: Optional[int]
    latitude: Optional[float]
    longitude: Optional[float]
    floor_count: Optional[int]
    recency_days: int
    weight: float = 1.0


@dataclass
class ComparablePool:
    """Tập comparable đã chọn và tính trọng số."""
    records: List[ComparableCandidate]
    level: int  # 1-4
    n_eff: float
    total_weight: float
    baseline_price: float  # VND/m² weighted median
    baseline_price_raw: float
    distribution: Dict[str, Any]


@dataclass
class ImpactFactor:
    """Một factor ảnh hưởng đến giá."""
    field_code: str
    field_label: str
    field_value: Any
    comparable_mean: Optional[float]
    comparable_std: Optional[float]
    comparable_min: Optional[float]
    comparable_max: Optional[float]
    raw_delta_pct: float
    display_delta_pct: float
    contribution_vnd: int
    direction: str
    confidence: float
    is_missing: bool
    is_residual: bool
    source: str
    detail: str


@dataclass
class MissingDataImpact:
    """Impact của một field bị thiếu."""
    field: str
    field_label: str
    missing: bool
    price_effect_pct: float
    confidence_penalty: float
    confidence_penalty_vnd: int
    recommendation: str


@dataclass
class ScenarioProjection:
    """Một what-if scenario projection."""
    scenario_name: str
    scenario_type: str
    fmv_low: int
    fmv_high: int
    fmv_mid: int
    confidence: float
    confidence_grade: str
    interval_width_pct: float
    filled_fields: List[str]
    uncertainty_reduction_pct: float


@dataclass
class ImpactResult:
    """Kết quả phân tích tác động hoàn chỉnh."""
    run_id: str
    fair_market_value: int
    baseline_value: int
    delta_vs_baseline_pct: float
    n_eff: float
    comparable_level: int
    n_comparables_used: int
    contributions: List[ImpactFactor]
    missing_data: List[MissingDataImpact]
    total_confidence_loss: float
    current_scenario: ScenarioProjection
    full_info_scenario: ScenarioProjection
    max_credibility_scenario: ScenarioProjection
    top_positive: List[str]
    top_negative: List[str]
    raw_total_pct: float
    display_total_pct: float


# =============================================================================
# IMPACT ENGINE
# =============================================================================

class ImpactEngine:
    """
    Contextual Comparable-SHAP δ% Engine.

    1. Select comparable pool (4 levels, weighted)
    2. Compute baseline price
    3. Run ML model → log(price)
    4. SHAP with comparable-pool background
    5. Convert SHAP → raw δ% → display δ% (clamp ±15%)
    6. Missing data: price effect + confidence loss
    7. Scenario projections
    """

    def __init__(self, ml_pipeline=None, db_session=None):
        """
        Args:
            ml_pipeline: MLPipeline instance (loaded model)
            db_session: SQLAlchemy session for DB queries
        """
        self.pipeline = ml_pipeline
        self.db_session = db_session

    def analyze(self, asset_input: AssetInput) -> ImpactResult:
        """
        Entry point — phân tích tác động cho một property.
        """
        run_id = str(datetime.now().strftime("%Y%m%d%H%M%S"))

        # Step 1: Select comparable pool
        pool = self._select_comparable_pool(asset_input)
        if not pool.records:
            return self._fallback_no_comparables(asset_input, run_id)

        # Step 2: Compute baseline
        base_price_vnd = pool.baseline_price * (asset_input.area_m2 or 100)

        # Step 3: ML prediction
        predicted_price_vnd, shap_values, feature_contributions = self._ml_predict(
            asset_input, pool
        )

        # Step 4: Convert to impacts
        contributions = self._shap_to_impacts(
            asset_input, pool, shap_values, feature_contributions,
            predicted_price_vnd, base_price_vnd
        )

        # Step 5: Missing data analysis
        missing_data, total_conf_loss = self._analyze_missing_data(
            asset_input, pool, predicted_price_vnd
        )

        # Step 6: Scenarios
        current_scenario, full_info_scenario, max_cred_scenario = self._compute_scenarios(
            asset_input, pool, predicted_price_vnd, total_conf_loss
        )

        # Summary
        top_pos = [f.field_label for f in contributions if f.direction == "POSITIVE"][:5]
        top_neg = [f.field_label for f in contributions if f.direction == "NEGATIVE"][:5]
        raw_total = sum(f.raw_delta_pct for f in contributions if not f.is_residual)
        disp_total = sum(f.display_delta_pct for f in contributions if not f.is_residual)

        return ImpactResult(
            run_id=run_id,
            fair_market_value=predicted_price_vnd,
            baseline_value=base_price_vnd,
            delta_vs_baseline_pct=round(
                (predicted_price_vnd - base_price_vnd) / max(base_price_vnd, 1) * 100, 2
            ),
            n_eff=round(pool.n_eff, 1),
            comparable_level=pool.level,
            n_comparables_used=len(pool.records),
            contributions=contributions,
            missing_data=missing_data,
            total_confidence_loss=round(total_conf_loss, 1),
            current_scenario=current_scenario,
            full_info_scenario=full_info_scenario,
            max_credibility_scenario=max_cred_scenario,
            top_positive=top_pos,
            top_negative=top_neg,
            raw_total_pct=round(raw_total, 2),
            display_total_pct=round(disp_total, 2),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Comparable Selection
    # ─────────────────────────────────────────────────────────────────────────

    def _select_comparable_pool(self, inp: AssetInput) -> ComparablePool:
        """Select comparable pool với 4 levels, có trọng số."""
        records = self._query_comparables(inp)

        if not records:
            return ComparablePool([], 4, 0.0, 0.0, 0.0, 0.0, {})

        # Level 1: same district + type + area + time
        level1 = self._filter_level(records, inp, level=1)
        # Level 2: same district + type
        level2 = self._filter_level(records, inp, level=2)
        # Level 3: neighboring district + type
        level3 = self._filter_level(records, inp, level=3)
        # Level 4: all + type
        level4 = self._filter_level(records, inp, level=4)

        # Pick best level with sufficient data
        for level, candidates in [(1, level1), (2, level2), (3, level3), (4, level4)]:
            if len(candidates) >= 3:
                pool = self._compute_pool_weights(candidates, inp)
                pool.level = level
                return pool

        # Fallback: use all
        pool = self._compute_pool_weights(records, inp)
        pool.level = 4
        return pool

    def _query_comparables(self, inp: AssetInput) -> List[ComparableCandidate]:
        """Query DB for potential comparable records."""
        if not self.db_session:
            return []

        from src.backend.models import Property
        norm = normalize_province(inp.province_city) or inp.province_city
        asset_type = self._map_asset_type(inp.asset_type)

        props = self.db_session.query(Property).filter(
            Property.record_status != "archived",
            Property.price.isnot(None),
            Property.price > 0,
            Property.area_m2.isnot(None),
            Property.area_m2 > 0,
            Property.property_type == asset_type,
        ).all()

        candidates = []
        now = datetime.now()
        for p in props:
            record_time = p.updated_at or p.created_at or now
            if getattr(record_time, "tzinfo", None) is not None:
                record_time = record_time.replace(tzinfo=None)
            recency = (now - record_time).days
            candidates.append(ComparableCandidate(
                id=p.id,
                area_m2=float(p.area_m2 or 100),
                price=float(p.price or 0),
                price_per_m2=float(p.price_per_m2 or 0),
                district=p.district or "",
                province_city=p.province_city or "",
                property_type=p.property_type or asset_type,
                evidence_tier=p.evidence_tier or "E3",
                legal_status=p.legal_status or "unknown",
                road_width_m=float(getattr(p, "frontage_m", 5) or 5),
                bedrooms=getattr(p, "bedrooms", None),
                latitude=getattr(p, "latitude", None),
                longitude=getattr(p, "longitude", None),
                floor_count=getattr(p, "floor_count", None),
                recency_days=recency,
                weight=1.0,
            ))

        return candidates

    def _filter_level(
        self, records: List[ComparableCandidate], inp: AssetInput, level: int
    ) -> List[ComparableCandidate]:
        """Filter records theo level."""
        norm = normalize_province(inp.province_city) or inp.province_city
        target_area = inp.area_m2 or 100
        area_lo = target_area * 0.5
        area_hi = target_area * 1.8

        if level == 1:
            return [r for r in records
                    if r.district == inp.district
                    and r.province_city == norm
                    and area_lo <= r.area_m2 <= area_hi
                    and r.recency_days <= 180]
        elif level == 2:
            return [r for r in records
                    if r.district == inp.district
                    and r.province_city == norm]
        elif level == 3:
            neighbors = _neighboring_districts(norm, inp.district)
            return [r for r in records
                    if r.province_city == norm
                    and r.district in neighbors]
        else:
            return [r for r in records if r.province_city == norm]

    def _compute_pool_weights(
        self, records: List[ComparableCandidate], inp: AssetInput
    ) -> ComparablePool:
        """Compute weighted pool: weights = location * type * area * recency * legal * road."""
        target_area = inp.area_m2 or 100
        target_lat = inp.latitude or 21.0
        target_lng = inp.longitude or 105.8

        tier_weights = {"E1": 1.0, "E2": 0.85, "E3": 0.65, "E4": 0.35, "E5": 0.15}

        for r in records:
            # Location
            loc_w = 1.0 if r.district == inp.district else 0.7

            # Type
            type_w = 1.0

            # Area similarity
            area_diff = abs(r.area_m2 - target_area) / max(target_area, 1)
            area_w = max(0.3, 1.0 - area_diff)

            # Recency
            rec_w = max(0.5, 1.0 - r.recency_days / 365)

            # Legal
            legal_w = 0.8 if r.legal_status != "FULL_OWNERSHIP" else 1.0

            # Road width
            road_w = 1.0

            # Evidence tier
            tier_w = tier_weights.get(r.evidence_tier, 0.3)

            r.weight = loc_w * type_w * area_w * rec_w * legal_w * road_w * tier_w

        # N_eff = (sum w)^2 / sum(w^2)
        w_sum = sum(r.weight for r in records)
        w_sq_sum = sum(r.weight ** 2 for r in records)
        n_eff = (w_sum ** 2) / max(w_sq_sum, 1e-9)

        # Weighted baseline price
        weighted_sum = sum(r.price_per_m2 * r.weight for r in records)
        baseline_price = weighted_sum / max(w_sum, 1e-9)

        # Distribution
        areas = [r.area_m2 for r in records]
        prices = [r.price_per_m2 for r in records]
        distribution = {
            "area_mean": float(np.mean(areas)),
            "area_std": float(np.std(areas)),
            "area_min": float(np.min(areas)),
            "area_max": float(np.max(areas)),
            "price_per_m2_mean": float(np.mean(prices)),
            "price_per_m2_std": float(np.std(prices)),
            "price_per_m2_min": float(np.min(prices)),
            "price_per_m2_max": float(np.max(prices)),
        }

        return ComparablePool(
            records=records,
            level=4,
            n_eff=n_eff,
            total_weight=w_sum,
            baseline_price=baseline_price,
            baseline_price_raw=float(np.median(prices)),
            distribution=distribution,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2-3: ML Prediction + SHAP
    # ─────────────────────────────────────────────────────────────────────────

    def _ml_predict(
        self, inp: AssetInput, pool: ComparablePool
    ) -> Tuple[int, np.ndarray, Dict[str, float]]:
        """
        Run ML model + SHAP với comparable-pool background.
        Returns: (predicted_price_vnd, shap_values, feature_contributions)
        """
        if not self.pipeline or not self.pipeline.is_fitted:
            return self._rule_based_predict(inp, pool)

        try:
            # Build feature vector
            feat = self._build_feature_vector(inp)
            X = np.array([feat], dtype=np.float64)

            # Predict log(price_per_m2)
            log_pred = self.pipeline.predict(X)[0]
            predicted_price = math.exp(log_pred) * (inp.area_m2 or 100)

            # SHAP với background = comparable pool
            shap_values = self._compute_shap(X, pool)
            feature_names = self.pipeline.feature_names

            # Map to readable feature contributions
            feature_contributions = {}
            for i, name in enumerate(feature_names):
                if i < len(shap_values):
                    feature_contributions[name] = float(shap_values[i])

            return int(predicted_price), shap_values, feature_contributions

        except Exception:
            return self._rule_based_predict(inp, pool)

    def _compute_shap(self, X: np.ndarray, pool: ComparablePool) -> np.ndarray:
        """Compute SHAP values với background = comparable pool."""
        import shap

        try:
            model = self.pipeline.best_model
            scaler = self.pipeline.scaler

            # Build background = features của comparable pool
            bg_features = []
            for r in pool.records[:50]:  # Max 50 for performance
                feat_vec = self._comparable_to_feature_vector(r)
                bg_features.append(feat_vec)

            if len(bg_features) < 3:
                # Fallback: use mean of pool
                bg_mean = np.mean(bg_features, axis=0) if bg_features else np.zeros(X.shape[1])
                bg = np.array([bg_mean])
            else:
                bg = np.array(bg_features, dtype=np.float64)

            # Scale background
            bg_scaled = scaler.transform(bg)

            # TreeExplainer
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(bg_scaled, check_additivity=False)

            # For single prediction
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            if len(shap_values.shape) > 1:
                shap_values = shap_values[0]

            return shap_values

        except Exception:
            return np.zeros(X.shape[1])

    def _build_feature_vector(self, inp: AssetInput) -> np.ndarray:
        """Build feature vector từ AssetInput matching MLPipeline._build_features."""
        area = float(inp.area_m2 or 80)
        bedrooms = int(inp.bedrooms or 0)
        bathrooms = int(inp.bathrooms or 0)
        floor_count = int(inp.floor_count or 1)
        frontage = float(inp.frontage_m or 5)
        lat = float(inp.latitude or 21.0)
        lng = float(inp.longitude or 105.8)
        ptype = inp.asset_type or "apartment"

        def norm(val, mn, mx):
            return (val - mn) / (mx - mn + 1e-9) if mx != mn else 0.5

        feat = []
        feat.append(norm(area, 15, 500))
        feat.append(norm(bedrooms, 0, 6))
        feat.append(norm(bathrooms, 0, 4))
        feat.append(float(floor_count))
        feat.append(float(frontage))
        feat.append(norm(lat, 10.5, 21.5))
        feat.append(norm(lng, 104.5, 107.0))
        feat.append(1 if ptype in ("HOUSE", "VILLA") else 0)
        feat.append(1 if ptype == "APARTMENT" else 0)
        feat.append(1 if ptype == "LAND_URBAN" else 0)
        feat.append(1 if ptype == "TOWNHOUSE" else 0)
        feat.append(1 if ptype == "VILLA" else 0)

        province = inp.province_city or "Hà Nội"
        feat.append(1 if "Hà Nội" in province else 0)
        feat.append(1 if "Hồ Chí Minh" in province else 0)
        feat.append(1 if "Đà Nẵng" in province else 0)
        feat.append(1 if "Hải Phòng" in province else 0)
        feat.append(1 if "Cần Thơ" in province else 0)
        feat.append(1 if "Bình Dương" in province else 0)

        noise = float(inp.noise_level or 50)
        feat.append(norm(noise, 30, 80))
        feat.append(0.5)  # temperature
        feat.append(0.5)  # humidity
        feat.append(0.5)  # light

        if "Hồ Chí Minh" in province:
            center = (10.78, 106.68)
        elif "Hà Nội" in province:
            center = (21.03, 105.85)
        else:
            center = (lat, lng)
        dist = ((lat - center[0]) ** 2 + (lng - center[1]) ** 2) ** 0.5
        feat.append(norm(dist, 0, 2))

        type_map = {"apartment": 0, "townhouse": 1, "house": 2, "land": 3, "villa": 4}
        feat.append(float(type_map.get(ptype.lower(), 0)))
        feat.append(1.0 if inp.ownership_type == "FULL_OWNERSHIP" else 0.0)
        feat.append(0.5)
        feat.append(0.9)

        # Quality features (defaults)
        feat.extend([0.5] * 10)
        feat.append(6.1)
        feat.extend([0.0] * 4)
        feat.append(0.2)

        # Binary flags
        feat.append(0.0)
        feat.append(1.0 if inp.latitude else 0.0)

        # Interactions
        feat.append(float(bedrooms) * norm(area, 15, 500))
        feat.append(float(floor_count) * norm(bedrooms, 0, 6))

        # KNN density
        feat.append(max(0, 1 - dist / 2))
        feat.append(max(0, 1 - dist / 2) * 0.8)

        n_expected = len(self.pipeline.feature_names) if self.pipeline and self.pipeline.feature_names else 53
        while len(feat) < n_expected:
            feat.append(0.0)

        return np.array(feat[:n_expected], dtype=np.float64)

    def _comparable_to_feature_vector(self, r: ComparableCandidate) -> np.ndarray:
        """Build feature vector từ ComparableCandidate."""
        def norm(val, mn, mx):
            return (val - mn) / (mx - mn + 1e-9) if mx != mn else 0.5

        ptype = r.property_type or "apartment"
        province = r.province_city or "Hà Nội"
        lat = r.latitude or 21.0
        lng = r.longitude or 105.8
        area = r.area_m2 or 80
        bedrooms = r.bedrooms or 0
        floor_count = r.floor_count or 1
        frontage = r.road_width_m or 5

        feat = []
        feat.append(norm(area, 15, 500))
        feat.append(norm(bedrooms, 0, 6))
        feat.append(0.5)
        feat.append(float(floor_count))
        feat.append(float(frontage))
        feat.append(norm(lat, 10.5, 21.5))
        feat.append(norm(lng, 104.5, 107.0))
        feat.append(1 if ptype in ("house", "villa") else 0)
        feat.append(1 if ptype == "apartment" else 0)
        feat.append(1 if ptype == "land" else 0)
        feat.append(1 if ptype == "townhouse" else 0)
        feat.append(1 if ptype == "villa" else 0)
        feat.append(1 if "Hà Nội" in province else 0)
        feat.append(1 if "Hồ Chí Minh" in province else 0)
        feat.append(0)  # Đà Nẵng
        feat.append(0)  # Hải Phòng
        feat.append(0)  # Cần Thơ
        feat.append(0)  # Bình Dương)
        feat.extend([0.5] * 4)  # IoT
        if "Hồ Chí Minh" in province:
            center = (10.78, 106.68)
        elif "Hà Nội" in province:
            center = (21.03, 105.85)
        else:
            center = (lat, lng)
        dist = ((lat - center[0]) ** 2 + (lng - center[1]) ** 2) ** 0.5
        feat.append(norm(dist, 0, 2))
        type_map = {"apartment": 0, "townhouse": 1, "house": 2, "land": 3, "villa": 4}
        feat.append(float(type_map.get(ptype.lower(), 0)))
        feat.append(1.0 if r.legal_status == "FULL_OWNERSHIP" else 0.0)
        feat.append(0.5)
        feat.append(0.9)
        feat.extend([0.5] * 10)
        feat.append(6.1)
        feat.extend([0.0] * 4)
        feat.append(0.2)
        feat.append(0.0)
        feat.append(1.0 if r.latitude else 0.0)
        feat.append(float(bedrooms) * norm(area, 15, 500))
        feat.append(float(floor_count) * norm(bedrooms, 0, 6))
        feat.append(max(0, 1 - dist / 2))
        feat.append(max(0, 1 - dist / 2) * 0.8)

        n_exp = len(self.pipeline.feature_names) if self.pipeline and self.pipeline.feature_names else 53
        while len(feat) < n_exp:
            feat.append(0.0)

        return np.array(feat[:n_exp], dtype=np.float64)

    def _rule_based_predict(
        self, inp: AssetInput, pool: ComparablePool
    ) -> Tuple[int, np.ndarray, Dict[str, float]]:
        """Fallback khi ML model không available."""
        area = inp.area_m2 or 100
        baseline = pool.baseline_price * area

        # Estimate roughly based on adjustments
        adj = self._rule_based_adjustments(inp, pool, baseline)

        # Estimate SHAP-like contributions (rule-based)
        feature_contributions = {}
        adj_names = {
            "area_m2": "Diện tích",
            "bedrooms": "Số phòng ngủ",
            "road_width_m": "Chiều rộng đường",
            "road_class": "Loại đường",
            "floor_count": "Số tầng",
            "corner_plot": "Đất góc",
            "ownership_type": "Pháp lý",
        }
        for fname, pct in adj.items():
            feature_contributions[adj_names.get(fname, fname)] = pct / 100

        return int(baseline + adj.get("_total", 0)), np.zeros(53), feature_contributions

    def _rule_based_adjustments(
        self, inp: AssetInput, pool: ComparablePool, base: int
    ) -> Dict[str, float]:
        """Rule-based adjustments khi ML không có."""
        adj = {}
        total_adj = 0.0

        area = inp.area_m2 or 100
        area_mean = pool.distribution.get("area_mean", 100)
        if area > area_mean:
            pct = min((area - area_mean) / area_mean * 100, 15)
            adj["area_m2"] = pct
            total_adj += base * pct / 100
        elif area < area_mean:
            pct = max((area - area_mean) / area_mean * 100, -15)
            adj["area_m2"] = pct
            total_adj += base * pct / 100

        if inp.road_width_m:
            if inp.road_width_m >= 6:
                adj["road_width_m"] = 8.0
                total_adj += base * 0.08
            elif inp.road_width_m <= 2:
                adj["road_width_m"] = -10.0
                total_adj += base * -0.10

        if inp.corner_plot:
            adj["corner_plot"] = 6.0
            total_adj += base * 0.06

        adj["_total"] = total_adj
        return adj

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: SHAP → Impacts
    # ─────────────────────────────────────────────────────────────────────────

    def _shap_to_impacts(
        self,
        inp: AssetInput,
        pool: ComparablePool,
        shap_values: np.ndarray,
        feature_contributions: Dict[str, float],
        predicted_price: int,
        baseline_price: int,
    ) -> List[ImpactFactor]:
        """Convert SHAP values → ImpactFactor list."""
        impacts: List[ImpactFactor] = []

        # Map SHAP features to readable field impacts
        shap_feature_map = {
            "area_m2_norm": ("area_m2", inp.area_m2 or 0),
            "bedrooms_norm": ("bedrooms", inp.bedrooms or 0),
            "bathrooms_norm": ("bathrooms", inp.bathrooms or 0),
            "floor_count": ("floor_count", inp.floor_count or 1),
            "frontage_m": ("frontage_m", inp.frontage_m or 0),
            "road_width": ("road_width_m", inp.road_width_m or 0),
            "road_class": ("road_class", 1),
            "built_area_m2": ("built_area_m2", inp.built_area_m2 or 0),
            "apt_floor": ("apt_floor", inp.apt_floor or 0),
            "view_type": ("view_type", 1),
            "ownership_type": ("ownership_type", 1),
            "planning_zone": ("planning_zone", 1),
            "flood_risk": ("flood_risk", 1),
            "latitude_norm": ("latitude", inp.latitude or 0),
            "longitude_norm": ("longitude", inp.longitude or 0),
            "construction_year": ("construction_year", inp.construction_year or 2020),
            "corner_plot": ("corner_plot", inp.corner_plot or False),
            "noise_level_norm": ("noise_level", inp.noise_level or 0),
        }

        # Compute raw deltas from SHAP. Unit tests and no-model fallback paths can
        # pass SHAP-like vectors without a fitted pipeline, so synthesize stable
        # names instead of silently dropping those raw audit deltas.
        feature_names = list(self.pipeline.feature_names) if self.pipeline and self.pipeline.feature_names else []
        if not feature_names and shap_values is not None:
            feature_names = list(shap_feature_map.keys())
            if len(shap_values) > len(feature_names):
                feature_names.extend(
                    f"feature_{i}" for i in range(len(feature_names), len(shap_values))
                )
        feature_names = feature_names[:len(shap_values)]
        total_shap = sum(abs(float(v)) for v in shap_values[:len(feature_names)])

        for i, fname in enumerate(feature_names):
            if i >= len(shap_values):
                break

            phi = float(shap_values[i])
            if abs(phi) < 1e-6:
                continue

            # Convert SHAP (log space) to percentage
            raw_delta = (math.exp(phi) - 1) * 100
            raw_delta = max(-100, min(100, raw_delta))

            # Clamp for display
            display_delta = max(-15.0, min(15.0, raw_delta))

            # Map to field
            field_code, field_value = shap_feature_map.get(fname, (fname, None))
            if field_value is None:
                field_value = self._get_input_value(inp, field_code)

            field_label = FIELD_LABELS.get(field_code, field_code)
            semantics = FIELD_SEMANTICS.get(field_code, "neutral")
            direction = self._determine_direction(raw_delta, semantics)

            # Comparable stats
            comparable_mean = pool.distribution.get("price_per_m2_mean") if field_code == "area_m2" else None

            # Contribution in VND
            if total_shap > 0:
                contribution_vnd = int(predicted_price * (phi / total_shap))
            else:
                contribution_vnd = 0

            # Confidence (from pool quality)
            confidence = min(0.95, 0.5 + pool.n_eff / 20)

            detail = self._build_detail(field_code, field_value, pool, raw_delta)

            impacts.append(ImpactFactor(
                field_code=field_code,
                field_label=field_label,
                field_value=field_value,
                comparable_mean=comparable_mean,
                comparable_std=pool.distribution.get("area_std") if field_code == "area_m2" else None,
                comparable_min=pool.distribution.get("area_min") if field_code == "area_m2" else None,
                comparable_max=pool.distribution.get("area_max") if field_code == "area_m2" else None,
                raw_delta_pct=round(raw_delta, 2),
                display_delta_pct=round(display_delta, 2),
                contribution_vnd=contribution_vnd,
                direction=direction,
                confidence=round(confidence, 3),
                is_missing=False,
                is_residual=False,
                source="SHAP",
                detail=detail,
            ))

        # Add rule-based adjustments (when ML not available)
        rule_adj = self._rule_based_adjustments(inp, pool, baseline_price)
        for fname, delta in rule_adj.items():
            if fname == "_total" or delta == 0:
                continue
            if any(i.field_code == fname for i in impacts):
                continue

            field_label = FIELD_LABELS.get(fname, fname)
            field_value = self._get_input_value(inp, fname)
            semantics = FIELD_SEMANTICS.get(fname, "neutral")
            direction = self._determine_direction(delta, semantics)
            contribution_vnd = int(baseline_price * delta / 100)

            impacts.append(ImpactFactor(
                field_code=fname,
                field_label=field_label,
                field_value=field_value,
                comparable_mean=None,
                comparable_std=None,
                comparable_min=None,
                comparable_max=None,
                raw_delta_pct=round(delta, 2),
                display_delta_pct=round(max(-15.0, min(15.0, delta)), 2),
                contribution_vnd=contribution_vnd,
                direction=direction,
                confidence=0.5,
                is_missing=False,
                is_residual=False,
                source="COMPARABLE",
                detail=f"So sánh với mặt bằng thị trường quận: {delta:+.1f}%",
            ))

        # Residual (what's left after factoring)
        non_residual_sum = sum(abs(f.display_delta_pct) for f in impacts if not f.is_residual)
        predicted_total = sum(f.display_delta_pct for f in impacts if not f.is_residual)
        actual_total = (predicted_price - baseline_price) / max(baseline_price, 1) * 100
        residual = round(actual_total - predicted_total, 2)

        if abs(residual) > 0.5:
            impacts.append(ImpactFactor(
                field_code="RESIDUAL",
                field_label="Tương tác / Residual",
                field_value=None,
                comparable_mean=None,
                comparable_std=None,
                comparable_min=None,
                comparable_max=None,
                raw_delta_pct=residual,
                display_delta_pct=residual,
                contribution_vnd=int(baseline_price * residual / 100),
                direction="NEUTRAL",
                confidence=0.3,
                is_missing=False,
                is_residual=True,
                source="RESIDUAL",
                detail=f"Tương tác giữa các yếu tố và phần bị clamp: {residual:+.1f}%",
            ))

        # Sort by |display_delta_pct| desc, residual last
        impacts.sort(key=lambda x: (0 if not x.is_residual else 1, -abs(x.display_delta_pct)))
        return impacts

    def _get_input_value(self, inp: AssetInput, field_code: str) -> Any:
        """Get field value from AssetInput."""
        return getattr(inp, field_code, None)

    def _determine_direction(self, delta_pct: float, semantics: str) -> str:
        """Determine direction based on delta and semantics."""
        if abs(delta_pct) < 0.5:
            return "NEUTRAL"
        if semantics == "positive":
            return "POSITIVE" if delta_pct > 0 else "NEGATIVE"
        elif semantics == "negative":
            return "POSITIVE" if delta_pct < 0 else "NEGATIVE"
        return "POSITIVE" if delta_pct > 0 else "NEGATIVE"

    def _build_detail(self, field_code: str, value: Any, pool: ComparablePool, raw_delta: float) -> str:
        """Build human-readable detail string."""
        dist = pool.distribution
        if field_code == "area_m2" and value:
            area_mean = dist.get("area_mean", 0)
            if area_mean > 0:
                return (f"Input {value:.0f}m² vs trung bình quận {area_mean:.0f}m² "
                        f"({(value - area_mean) / area_mean * 100:+.1f}%).")
        if raw_delta > 0:
            return f"Tác động tích cực: {raw_delta:+.1f}% so với baseline."
        elif raw_delta < 0:
            return f"Tác động tiêu cực: {raw_delta:+.1f}% so với baseline."
        return "Không có tác động đáng kể."

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: Missing Data Analysis
    # ─────────────────────────────────────────────────────────────────────────

    def _analyze_missing_data(
        self, inp: AssetInput, pool: ComparablePool, predicted_price: int
    ) -> Tuple[List[MissingDataImpact], float]:
        """Analyze missing fields: price effect + confidence loss."""
        all_fields = list(MISSING_CONFIDENCE_PENALTY.keys())
        missing_impacts: List[MissingDataImpact] = []
        total_conf_loss = 0.0

        for fname in all_fields:
            value = self._get_input_value(inp, fname)
            is_missing = (
                value is None
                or value == 0
                or value == ""
                or value is False
            )

            if not is_missing:
                continue

            penalty = MISSING_CONFIDENCE_PENALTY.get(fname, 5.0)
            total_conf_loss += penalty

            # Price effect: comparable distribution when field is missing
            price_effect_pct = self._missing_price_effect(fname, pool)

            recommendation = self._missing_recommendation(fname)

            missing_impacts.append(MissingDataImpact(
                field=fname,
                field_label=FIELD_LABELS.get(fname, fname),
                missing=True,
                price_effect_pct=round(price_effect_pct, 2),
                confidence_penalty=penalty,
                confidence_penalty_vnd=int(predicted_price * penalty / 100),
                recommendation=recommendation,
            ))

        return missing_impacts, total_conf_loss

    def _missing_price_effect(self, field_code: str, pool: ComparablePool) -> float:
        """Estimate price effect when field is missing (from comparable data)."""
        dist = pool.distribution

        # Simplified: if field is missing, we estimate a range
        if field_code == "ownership_type":
            return -4.0  # Missing legal → discount typical
        elif field_code == "road_width_m":
            return -3.0
        elif field_code == "area_m2":
            return -2.0
        elif field_code == "bedrooms":
            return -1.0
        elif field_code == "latitude":
            return -1.5
        return -1.0

    def _missing_recommendation(self, field_code: str) -> str:
        """Recommendation when field is missing."""
        recs = {
            "ownership_type": "Bổ sung giấy tờ pháp lý (sổ đỏ, hợp đồng mua bán) để tăng độ tin cậy.",
            "planning_zone": "Kiểm tra quy hoạch 1/500 hoặc quy hoạch đô thị để xác định vị trí quy hoạch.",
            "road_width_m": "Đo chiều rộng đường tiếp cận tại thực địa để định giá chính xác hơn.",
            "road_class": "Xác định loại đường: mặt tiền, hẻm 3m, hẻm 2m hay hẻm 1m.",
            "latitude": "Bổ sung tọa độ GPS để xác minh vị trí chính xác.",
            "longitude": "Bổ sung tọa độ GPS để xác minh vị trí chính xác.",
            "area_m2": "Đo đạc diện tích thực tế tại thực địa (có thể thuê đơn vị đo đạc).",
            "bedrooms": "Xác định số phòng ngủ thực tế từ thực địa hoặc chủ nhà.",
            "flood_risk": "Tra cứu bản đồ ngập lụt hoặc hỏi người dân địa phương.",
            "construction_year": "Xác định năm xây dựng từ giấy tờ hoặc ước lượng từ kiến trúc.",
            "apt_floor": "Xác định tầng căn hộ từ chủ nhà hoặc quản lý tòa nhà.",
            "view_type": "Kiểm tra view từ căn hộ bằng ảnh hoặc thực địa.",
            "built_area_m2": "Đo diện tích sàn xây dựng (không phải đất).",
            "frontage_m": "Đo chiều rộng mặt tiền đất.",
        }
        return recs.get(field_code, f"Bổ sung thông tin '{FIELD_LABELS.get(field_code, field_code)}' để cải thiện độ chính xác.")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: Scenario Projections
    # ─────────────────────────────────────────────────────────────────────────

    def _compute_scenarios(
        self,
        inp: AssetInput,
        pool: ComparablePool,
        current_price: int,
        total_conf_loss: float,
    ) -> Tuple[ScenarioProjection, ScenarioProjection, ScenarioProjection]:
        """Compute 3 scenarios: current, full-info, max-credibility."""

        sample_count = len(pool.records)
        sample_score = min(sample_count / 800.0, 1.0)
        neff_score = min(pool.n_eff / 800.0, 1.0)
        data_quality_score = max(0.0, min(1.0, 1.0 - total_conf_loss / 100.0))

        if sample_count >= 800:
            sample_cap = 0.95
        elif sample_count >= 300:
            sample_cap = 0.69
        else:
            sample_cap = 0.40

        # Current scenario: số lượng mẫu gần là chốt chặn chính. Bổ sung form
        # giúp giảm rủi ro, nhưng không thể biến vài chục comparable thành hạng A.
        current_confidence = min(
            sample_cap,
            max(
                0.10,
                0.08
                + sample_score * 0.58
                + neff_score * 0.12
                + data_quality_score * 0.14
            ),
        )
        current_grade = self._confidence_to_grade(current_confidence)
        current_interval = self._confidence_interval(current_confidence)
        current_low = int(current_price * (1 - current_interval))
        current_high = int(current_price * (1 + current_interval))

        current = ScenarioProjection(
            scenario_name="Hiện tại",
            scenario_type="CURRENT",
            fmv_low=current_low,
            fmv_high=current_high,
            fmv_mid=current_price,
            confidence=round(current_confidence, 3),
            confidence_grade=current_grade,
            interval_width_pct=round(current_interval * 100, 1),
            filled_fields=self._get_filled_fields(inp),
            uncertainty_reduction_pct=0.0,
        )

        # Full-info scenario: fill missing fields with median from pool
        full_info_confidence = min(
            sample_cap,
            current_confidence + min(total_conf_loss, 20) / 100
        )
        full_info_interval = self._confidence_interval(full_info_confidence)
        full_info_price = current_price  # Same point estimate
        full_info_low = int(full_info_price * (1 - full_info_interval))
        full_info_high = int(full_info_price * (1 + full_info_interval))
        full_info_uncertainty_reduction = round(
            (current_interval - full_info_interval) / max(current_interval, 0.001) * 100, 1
        )

        full_info = ScenarioProjection(
            scenario_name="Nếu có đủ thông tin",
            scenario_type="FULL_INFO",
            fmv_low=full_info_low,
            fmv_high=full_info_high,
            fmv_mid=full_info_price,
            confidence=round(full_info_confidence, 3),
            confidence_grade=self._confidence_to_grade(full_info_confidence),
            interval_width_pct=round(full_info_interval * 100, 1),
            filled_fields=["Tất cả các trường"],
            uncertainty_reduction_pct=full_info_uncertainty_reduction,
        )

        # Max credibility scenario: chỉ đạt A nếu pool thực sự đủ 800 mẫu gần.
        max_confidence = 0.95 if sample_count >= 800 else min(sample_cap, current_confidence + 0.08)
        max_interval = self._confidence_interval(max_confidence)
        max_low = int(current_price * (1 - max_interval))
        max_high = int(current_price * (1 + max_interval))
        max_uncertainty_reduction = round(
            (current_interval - max_interval) / max(current_interval, 0.001) * 100, 1
        )

        max_cred = ScenarioProjection(
            scenario_name="Nếu max uy tín + đủ thông tin",
            scenario_type="MAX_CREDIBILITY",
            fmv_low=max_low,
            fmv_high=max_high,
            fmv_mid=current_price,
            confidence=round(max_confidence, 3),
            confidence_grade=self._confidence_to_grade(max_confidence),
            interval_width_pct=round(max_interval * 100, 1),
            filled_fields=[
                "Tất cả + GPS + Pháp lý verified + Tier E1/E2",
                "Cần >=800 mẫu gần để đạt A"
            ],
            uncertainty_reduction_pct=max_uncertainty_reduction,
        )

        return current, full_info, max_cred

    def _confidence_to_grade(self, conf: float) -> str:
        if conf >= 0.85:
            return "A"
        elif conf >= 0.70:
            return "B"
        elif conf >= 0.55:
            return "C"
        return "D"

    def _confidence_interval(self, confidence: float) -> float:
        """Return interval ratio based on confidence."""
        if confidence >= 0.85:
            return 0.05
        elif confidence >= 0.70:
            return 0.08
        elif confidence >= 0.55:
            return 0.12
        return 0.18

    def _get_filled_fields(self, inp: AssetInput) -> List[str]:
        """Get list of filled fields."""
        filled = []
        for fname in FIELD_LABELS:
            val = self._get_input_value(inp, fname)
            if val is not None and val != 0 and val != "" and val is not False:
                filled.append(FIELD_LABELS.get(fname, fname))
        return filled

    # ─────────────────────────────────────────────────────────────────────────
    # Fallback
    # ─────────────────────────────────────────────────────────────────────────

    def _fallback_no_comparables(self, inp: AssetInput, run_id: str) -> ImpactResult:
        """Fallback khi không có comparable nào."""
        area = inp.area_m2 or 100
        norm = normalize_province(inp.province_city) or inp.province_city
        from src.config.province_config import get_base_price_per_m2
        base_ppm = get_base_price_per_m2(norm, inp.asset_type)
        baseline = int(base_ppm * area)
        predicted = baseline

        return ImpactResult(
            run_id=run_id,
            fair_market_value=predicted,
            baseline_value=baseline,
            delta_vs_baseline_pct=0.0,
            n_eff=0.0,
            comparable_level=4,
            n_comparables_used=0,
            contributions=[],
            missing_data=[],
            total_confidence_loss=30.0,
            current_scenario=ScenarioProjection(
                scenario_name="Hiện tại",
                scenario_type="CURRENT",
                fmv_low=int(predicted * 0.85),
                fmv_high=int(predicted * 1.15),
                fmv_mid=predicted,
                confidence=0.40,
                confidence_grade="D",
                interval_width_pct=15.0,
                filled_fields=self._get_filled_fields(inp),
                uncertainty_reduction_pct=0.0,
            ),
            full_info_scenario=ScenarioProjection(
                scenario_name="Nếu có đủ thông tin",
                scenario_type="FULL_INFO",
                fmv_low=int(predicted * 0.90),
                fmv_high=int(predicted * 1.10),
                fmv_mid=predicted,
                confidence=0.65,
                confidence_grade="B",
                interval_width_pct=10.0,
                filled_fields=[],
                uncertainty_reduction_pct=33.0,
            ),
            max_credibility_scenario=ScenarioProjection(
                scenario_name="Nếu max uy tín + đủ thông tin",
                scenario_type="MAX_CREDIBILITY",
                fmv_low=int(predicted * 0.95),
                fmv_high=int(predicted * 1.05),
                fmv_mid=predicted,
                confidence=0.95,
                confidence_grade="A",
                interval_width_pct=5.0,
                filled_fields=[],
                uncertainty_reduction_pct=67.0,
            ),
            top_positive=[],
            top_negative=[],
            raw_total_pct=0.0,
            display_total_pct=0.0,
        )

    def _map_asset_type(self, asset_type: str) -> str:
        """Map API asset_type → DB property_type."""
        mapping = {
            "APARTMENT": "apartment",
            "TOWNHOUSE": "townhouse",
            "LAND_URBAN": "land",
            "VILLA": "villa",
            "HOUSE": "house",
            "STUDIO": "apartment",
            "PENTHOUSE": "apartment",
            "DUPLEX": "apartment",
            "SHOPHOUSE": "townhouse",
        }
        return mapping.get(asset_type, asset_type.lower() if asset_type else "apartment")


def _neighboring_districts(province: str, current: str) -> List[str]:
    """Get neighboring districts for level 3 fallback."""
    neighbors = {
        "Quận Cầu Giấy": ["Quận Thanh Xuân", "Quận Đống Đa", "Quận Nam Từ Liêm"],
        "Quận Thanh Xuân": ["Quận Cầu Giấy", "Quận Đống Đa", "Quận Hà Đông"],
        "Quận Đống Đa": ["Quận Cầu Giấy", "Quận Thanh Xuân", "Quận Ba Đình"],
        "Quận 7": ["Quận Bình Thạnh", "Quận Tân Bình", "Quận 4"],
        "Quận Bình Thạnh": ["Quận 7", "Quận Tân Bình", "Quận Phú Nhuận"],
        "Quận Tân Bình": ["Quận Bình Thạnh", "Quận 7", "Quận Phú Nhuận"],
    }
    return neighbors.get(current, [])
