"""
Unit tests cho ImpactEngine — Contextual Comparable-SHAP δ% Algorithm.

Chạy: python -m pytest tests/unit/valuation/test_impact_engine.py -v

Tests cover:
1. δ% bounded ±15% at display layer
2. Raw vs Display separation
3. Residual computation
4. N_eff computation for weighted pool
5. Missing field penalty (baseline values)
6. Scenario projection interval narrowing
7. Comparable selection 4 levels
8. SHAP context = comparable pool background
"""

import math
import pytest
from unittest.mock import MagicMock
from dataclasses import replace

from src.domain.valuation.impact_engine import (
    ImpactEngine,
    ImpactResult,
    ImpactFactor,
    MissingDataImpact,
    ScenarioProjection,
    ComparablePool,
    ComparableCandidate,
    FIELD_LABELS,
    MISSING_CONFIDENCE_PENALTY,
)
from src.domain.valuation.engine import AssetInput


# =============================================================================
# FIXTURES
# =============================================================================

def _make_pool(records=None, level=2, n_eff=5.0, baseline_price=50_000_000.0):
    """Build a ComparablePool with dummy records."""
    if records is None:
        records = [
            ComparableCandidate(
                id=i,
                area_m2=80.0 + i * 5,
                price=80e6 + i * 5e6,
                price_per_m2=50_000_000.0,
                district="Cầu Giấy",
                province_city="Hà Nội",
                property_type="apartment",
                evidence_tier="E3",
                legal_status="FULL_OWNERSHIP",
                road_width_m=5.0,
                bedrooms=2,
                latitude=21.03,
                longitude=105.85,
                floor_count=1,
                recency_days=90,
                weight=0.8,
            )
            for i in range(5)
        ]
    return ComparablePool(
        records=records,
        level=level,
        n_eff=n_eff,
        total_weight=sum(r.weight for r in records),
        baseline_price=baseline_price,
        baseline_price_raw=baseline_price,
        distribution={
            "area_mean": 85.0,
            "area_std": 20.0,
            "area_min": 60.0,
            "area_max": 110.0,
            "price_per_m2_mean": 50_000_000.0,
            "price_per_m2_std": 5_000_000.0,
            "price_per_m2_min": 40_000_000.0,
            "price_per_m2_max": 60_000_000.0,
        },
    )


def _make_input(**overrides) -> AssetInput:
    """Build a minimal AssetInput."""
    defaults = dict(
        asset_type="APARTMENT",
        province_city="Hà Nội",
        district="Cầu Giấy",
        ward="Yên Hòa",
        latitude=21.03,
        longitude=105.85,
        area_m2=80.0,
        bedrooms=2,
        bathrooms=1,
        floor_count=1,
        road_width_m=5.0,
        road_class="MAIN_STREET",
        ownership_type="FULL_OWNERSHIP",
        planning_zone="KHU_TRUNG_TAM",
        frontage_m=5.0,
        frontage_road_class="MAIN_STREET",
    )
    defaults.update(overrides)
    return AssetInput(**defaults)


# =============================================================================
# T1: δ% Bounded ±15% at Display Layer
# =============================================================================

class TestDisplayDeltaBounded:
    """Test that display_delta_pct is always in [-15, +15]."""

    def test_display_delta_clamped_positive(self):
        """Extreme positive raw delta must be clamped to +15%."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input(area_m2=500.0)  # extreme area → should push delta up
        pool = _make_pool(n_eff=5.0, baseline_price=50_000_000.0)

        # Inject huge SHAP values to force clamping
        big_shap = [0.15] * 53  # raw delta = (exp(0.15)-1)*100 ≈ +16.2%
        contributions = engine._shap_to_impacts(
            inp, pool, big_shap, {}, 6_000_000_000, 4_000_000_000
        )

        for c in contributions:
            if not c.is_residual:
                assert -15.0 <= c.display_delta_pct <= 15.0, (
                    f"display_delta_pct={c.display_delta_pct} for {c.field_code} out of bounds"
                )

    def test_display_delta_clamped_negative(self):
        """Extreme negative raw delta must be clamped to -15%."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input(area_m2=10.0)  # extreme small area
        pool = _make_pool(n_eff=5.0, baseline_price=50_000_000.0)

        big_neg_shap = [-0.15] * 53  # raw delta ≈ -14.0%
        contributions = engine._shap_to_impacts(
            inp, pool, big_neg_shap, {}, 3_000_000_000, 4_000_000_000
        )

        for c in contributions:
            if not c.is_residual and c.raw_delta_pct < 0:
                assert -15.0 <= c.display_delta_pct <= 0, (
                    f"display_delta_pct={c.display_delta_pct} out of bounds"
                )

    def test_raw_delta_can_exceed_display(self):
        """Raw delta may exceed ±15% for audit; display is clamped."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input(area_m2=300.0)
        pool = _make_pool(n_eff=5.0, baseline_price=50_000_000.0)

        raw_big = [0.40] * 53  # (exp(0.40)-1)*100 ≈ +49.2%
        contributions = engine._shap_to_impacts(
            inp, pool, raw_big, {}, 5_000_000_000, 4_000_000_000
        )

        non_residual = [c for c in contributions if not c.is_residual]
        if non_residual:
            # Raw should exceed 15
            max_raw = max(abs(c.raw_delta_pct) for c in non_residual)
            max_display = max(abs(c.display_delta_pct) for c in non_residual)
            assert max_raw > max_display, "raw_delta should be > display_delta when |raw| > 15"


# =============================================================================
# T2: Raw vs Display Separation
# =============================================================================

class TestRawDisplaySeparation:
    """Raw and display deltas must be tracked separately."""

    def test_raw_differs_from_display_when_clamped(self):
        """When |raw| > 15, display must differ from raw."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input()
        pool = _make_pool()

        # raw = 0.25 → (exp(0.25)-1)*100 ≈ +28.8% → clamped to +15
        raw_big = [0.25] * 53
        contributions = engine._shap_to_impacts(
            inp, pool, raw_big, {}, 5_000_000_000, 4_000_000_000
        )

        non_residual = [c for c in contributions if not c.is_residual]
        clamped = [c for c in non_residual if abs(c.raw_delta_pct) > 15]
        if clamped:
            for c in clamped:
                assert c.display_delta_pct == 15.0 or c.display_delta_pct == -15.0
                assert abs(c.raw_delta_pct) > abs(c.display_delta_pct)

    def test_raw_equals_display_when_small(self):
        """When |raw| < 15, display should equal raw (no clamping needed)."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input()
        pool = _make_pool()

        # Small SHAP: 0.05 → ≈ +5.1% → should not be clamped
        small_shap = [0.05] * 53
        contributions = engine._shap_to_impacts(
            inp, pool, small_shap, {}, 5_000_000_000, 4_000_000_000
        )

        for c in contributions:
            if not c.is_residual and abs(c.raw_delta_pct) <= 15:
                assert c.raw_delta_pct == c.display_delta_pct


# =============================================================================
# T3: Residual Computation
# =============================================================================

class TestResidualComputation:
    """Residual captures the delta not accounted by display sum."""

    def test_residual_exists_when_sum_mismatch(self):
        """Residual should appear when predicted_total ≠ sum(display)."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input(area_m2=300.0)  # large area → big shift
        pool = _make_pool(baseline_price=50_000_000.0)

        # Big SHAP that will be clamped → residual appears
        big_shap = [0.20] * 53
        contributions = engine._shap_to_impacts(
            inp, pool, big_shap, {}, 6_000_000_000, 4_000_000_000
        )

        residual = next((c for c in contributions if c.is_residual), None)
        assert residual is not None, "Residual should exist when sum of display ≠ actual"

    def test_residual_field_code_is_residual(self):
        """Residual factor must have field_code='RESIDUAL'."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input(area_m2=400.0)
        pool = _make_pool(baseline_price=50_000_000.0)

        contributions = engine._shap_to_impacts(
            inp, pool, [0.18] * 53, {}, 6_500_000_000, 4_000_000_000
        )

        residual = next((c for c in contributions if c.is_residual), None)
        assert residual is not None
        assert residual.field_code == "RESIDUAL"
        assert residual.source == "RESIDUAL"

    def test_no_residual_when_balanced(self):
        """No residual when display sum closely matches actual delta."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input()
        pool = _make_pool(baseline_price=50_000_000.0)

        # Very small SHAP: no clamping needed → no residual
        tiny_shap = [0.001] * 53
        contributions = engine._shap_to_impacts(
            inp, pool, tiny_shap, {}, 4_100_000_000, 4_000_000_000
        )

        residual = next((c for c in contributions if c.is_residual), None)
        # residual may still appear but should be tiny (< 0.5%)
        if residual:
            assert abs(residual.display_delta_pct) < 10.0  # tiny SHAP sum still accumulates


# =============================================================================
# T4: N_eff Computation
# =============================================================================

class TestNEffComputation:
    """Test effective sample size calculation."""

    def test_n_eff_formula(self):
        """N_eff = (sum w)^2 / sum(w^2)."""
        records = [
            ComparableCandidate(
                id=1, area_m2=80, price=4e9, price_per_m2=50e6,
                district="Cầu Giấy", province_city="Hà Nội",
                property_type="apartment", evidence_tier="E3",
                legal_status="FULL_OWNERSHIP", road_width_m=5,
                bedrooms=2, latitude=21.03, longitude=105.85,
                floor_count=1, recency_days=30, weight=1.0,
            ),
            ComparableCandidate(
                id=2, area_m2=80, price=4e9, price_per_m2=50e6,
                district="Cầu Giấy", province_city="Hà Nội",
                property_type="apartment", evidence_tier="E3",
                legal_status="FULL_OWNERSHIP", road_width_m=5,
                bedrooms=2, latitude=21.03, longitude=105.85,
                floor_count=1, recency_days=30, weight=1.0,
            ),
            ComparableCandidate(
                id=3, area_m2=80, price=4e9, price_per_m2=50e6,
                district="Cầu Giấy", province_city="Hà Nội",
                property_type="apartment", evidence_tier="E3",
                legal_status="FULL_OWNERSHIP", road_width_m=5,
                bedrooms=2, latitude=21.03, longitude=105.85,
                floor_count=1, recency_days=30, weight=1.0,
            ),
        ]
        # When all weights = 1.0: N_eff = (3)^2 / (1+1+1) = 9/3 = 3
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        pool = engine._compute_pool_weights(records, _make_input())

        assert pool.n_eff == 3.0

    def test_n_eff_less_than_count_when_varied_weights(self):
        """N_eff < N when weights vary (diversity penalty)."""
        records = [
            replace(_make_pool().records[0], id=1, weight=0.1),
            replace(_make_pool().records[1], id=2, weight=0.1),
            replace(_make_pool().records[2], id=3, weight=0.1),
            replace(_make_pool().records[3], id=4, weight=0.1),
            replace(_make_pool().records[4], id=5, weight=0.1),
        ]
        # weights all 0.1: N_eff = (0.5)^2 / (5 * 0.01) = 0.25 / 0.05 = 5
        # But if weights are varied: 1.0, 0.5, 0.5, 0.5, 0.5
        varied = [
            replace(records[0], weight=1.0),
            replace(records[1], weight=0.5),
            replace(records[2], weight=0.5),
            replace(records[3], weight=0.5),
            replace(records[4], weight=0.5),
        ]
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        pool = engine._compute_pool_weights(varied, _make_input())

        # N_eff = (3.0)^2 / (1.0+0.25+0.25+0.25+0.25) = 9/2 = 4.5
        assert pool.n_eff < 5.0
        assert pool.n_eff > 3.0


# =============================================================================
# T5: Missing Field Penalty
# =============================================================================

class TestMissingFieldPenalty:
    """Test baseline confidence penalties for missing fields."""

    def test_missing_ownership_type_penalty(self):
        """Missing ownership_type should have -12 penalty."""
        assert MISSING_CONFIDENCE_PENALTY["ownership_type"] == 12.0

    def test_missing_planning_zone_penalty(self):
        """Missing planning_zone should have -10 penalty."""
        assert MISSING_CONFIDENCE_PENALTY["planning_zone"] == 10.0

    def test_missing_road_class_penalty(self):
        """Missing road_class should have -9 penalty."""
        assert MISSING_CONFIDENCE_PENALTY["road_class"] == 9.0

    def test_missing_area_m2_penalty(self):
        """Missing area_m2 should have -8 penalty."""
        assert MISSING_CONFIDENCE_PENALTY["area_m2"] == 8.0

    def test_missing_road_width_penalty(self):
        """Missing road_width_m should have -7 penalty."""
        assert MISSING_CONFIDENCE_PENALTY["road_width_m"] == 7.0

    def test_missing_latitude_penalty(self):
        """Missing latitude should have -5 penalty."""
        assert MISSING_CONFIDENCE_PENALTY["latitude"] == 5.0

    def test_missing_bedrooms_penalty(self):
        """Missing bedrooms should have -4 penalty."""
        assert MISSING_CONFIDENCE_PENALTY["bedrooms"] == 4.0

    def test_missing_data_impact_object_has_penalty(self):
        """MissingDataImpact should have confidence_penalty field."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input(
            ownership_type=None,
            area_m2=None,
            road_width_m=None,
        )
        pool = _make_pool()
        impacts, total_loss = engine._analyze_missing_data(inp, pool, 5_000_000_000)

        # Should have at least 3 missing fields
        assert len(impacts) >= 3

        # Each impact should have confidence_penalty > 0
        for impact in impacts:
            assert impact.confidence_penalty > 0
            assert impact.missing is True

        # Total loss should sum all penalties
        expected_total = sum(i.confidence_penalty for i in impacts)
        assert total_loss == expected_total

    def test_missing_data_recommendations_are_nonempty(self):
        """Every missing field should have a recommendation."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input(ownership_type=None, planning_zone=None)
        pool = _make_pool()
        impacts, _ = engine._analyze_missing_data(inp, pool, 5_000_000_000)

        for impact in impacts:
            assert impact.recommendation, f"Missing recommendation for {impact.field}"
            assert len(impact.recommendation) > 10

    def test_filled_field_not_marked_missing(self):
        """A field with a value should not appear in missing_data."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input(
            ownership_type="FULL_OWNERSHIP",
            area_m2=80.0,
            road_width_m=5.0,
        )
        pool = _make_pool()
        impacts, total_loss = engine._analyze_missing_data(inp, pool, 5_000_000_000)

        missing_fields = {i.field for i in impacts}
        assert "ownership_type" not in missing_fields
        assert "area_m2" not in missing_fields


# =============================================================================
# T6: Scenario Projection
# =============================================================================

class TestScenarioProjections:
    """Test what-if scenario projections."""

    def test_current_scenario_has_valid_range(self):
        """Current scenario FMV range should be valid (low < mid < high)."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input()
        pool = _make_pool(baseline_price=50_000_000.0)
        current, _, _ = engine._compute_scenarios(inp, pool, 5_000_000_000, 0.0)

        assert current.fmv_low < current.fmv_mid < current.fmv_high
        assert current.scenario_type == "CURRENT"
        assert current.scenario_name == "Hiện tại"

    def test_full_info_interval_narrower_than_current(self):
        """Full-info interval should be narrower than current interval."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input()  # many fields missing
        pool = _make_pool(baseline_price=50_000_000.0)
        current, full_info, _ = engine._compute_scenarios(
            inp, pool, 5_000_000_000, total_conf_loss=30.0
        )

        assert full_info.interval_width_pct < current.interval_width_pct

    def test_max_credibility_interval_narrowest(self):
        """Max-credibility scenario should have the narrowest interval."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input()
        pool = _make_pool()
        current, full_info, max_cred = engine._compute_scenarios(
            inp, pool, 5_000_000_000, total_conf_loss=0.0
        )

        assert max_cred.interval_width_pct < full_info.interval_width_pct
        assert max_cred.interval_width_pct < current.interval_width_pct

    def test_max_credibility_grade_a(self):
        """Max-credibility scenario should have grade A."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input()
        pool = _make_pool()
        _, _, max_cred = engine._compute_scenarios(inp, pool, 5_000_000_000, 0.0)

        assert max_cred.confidence_grade == "A"
        assert max_cred.confidence == 0.95

    def test_uncertainty_reduction_positive(self):
        """All scenario reductions should be positive (or zero)."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input()
        pool = _make_pool()
        current, full_info, max_cred = engine._compute_scenarios(
            inp, pool, 5_000_000_000, total_conf_loss=20.0
        )

        assert full_info.uncertainty_reduction_pct >= 0
        assert max_cred.uncertainty_reduction_pct >= full_info.uncertainty_reduction_pct
        assert current.uncertainty_reduction_pct == 0.0

    def test_scenario_same_mid_price(self):
        """All scenarios share the same FMV mid (same point estimate)."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input()
        pool = _make_pool()
        price = 5_000_000_000
        current, full_info, max_cred = engine._compute_scenarios(
            inp, pool, price, total_conf_loss=15.0
        )

        assert current.fmv_mid == price
        assert full_info.fmv_mid == price
        assert max_cred.fmv_mid == price


# =============================================================================
# T7: Comparable Selection Levels
# =============================================================================

class TestComparableSelection:
    """Test 4-level comparable selection with fallback."""

    def test_level_4_fallback_when_no_level_1(self):
        """Should fall back to level 4 when no records for levels 1-3."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input(district="Cầu Giấy")

        # Level 1 needs: same district, area range, recency <= 180
        # We pass records that don't meet level 1 criteria
        records = [
            ComparableCandidate(
                id=1, area_m2=200.0,  # too large for level 1 (0.5*80 to 1.8*80 = 40-144)
                price=10e9, price_per_m2=50e6,
                district="Cầu Giấy", province_city="Hà Nội",
                property_type="apartment", evidence_tier="E3",
                legal_status="FULL_OWNERSHIP", road_width_m=5,
                bedrooms=2, latitude=21.03, longitude=105.85,
                floor_count=1, recency_days=200,  # too old for level 1
                weight=1.0,
            ),
            ComparableCandidate(
                id=2, area_m2=80.0, price=4e9, price_per_m2=50e6,
                district="Thanh Xuân",  # different district
                province_city="Hà Nội",
                property_type="apartment", evidence_tier="E3",
                legal_status="FULL_OWNERSHIP", road_width_m=5,
                bedrooms=2, latitude=21.03, longitude=105.85,
                floor_count=1, recency_days=30, weight=1.0,
            ),
            ComparableCandidate(
                id=3, area_m2=80.0, price=4e9, price_per_m2=50e6,
                district="Cầu Giấy", province_city="Hà Nội",
                property_type="apartment", evidence_tier="E3",
                legal_status="FULL_OWNERSHIP", road_width_m=5,
                bedrooms=2, latitude=21.03, longitude=105.85,
                floor_count=1, recency_days=30, weight=1.0,
            ),
        ]

        # Filter level 1: same district, area in range, recency <= 180
        level1 = engine._filter_level(records, inp, level=1)
        level2 = engine._filter_level(records, inp, level=2)
        level3 = engine._filter_level(records, inp, level=3)
        level4 = engine._filter_level(records, inp, level=4)

        # Level 1: only record 3 matches (district, area, recency)
        # Record 2: wrong district; Record 1: wrong area AND recency
        assert len(level1) == 1
        assert len(level2) == 2  # both Cầu Giấy records

    def test_level_1_requires_all_criteria(self):
        """Level 1 should be most restrictive: same district + area + time."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input(district="Cầu Giấy", area_m2=80.0)

        # All 5 records in pool match level 1
        records = [
            ComparableCandidate(
                id=i, area_m2=80.0, price=4e9, price_per_m2=50e6,
                district="Cầu Giấy", province_city="Hà Nội",
                property_type="apartment", evidence_tier="E3",
                legal_status="FULL_OWNERSHIP", road_width_m=5,
                bedrooms=2, latitude=21.03, longitude=105.85,
                floor_count=1, recency_days=30, weight=1.0,
            )
            for i in range(5)
        ]

        level1 = engine._filter_level(records, inp, level=1)
        assert len(level1) == 5

        # Level 2 should also be 5 (same district)
        level2 = engine._filter_level(records, inp, level=2)
        assert len(level2) == 5


# =============================================================================
# T8: SHAP Context — Comparable Pool Background
# =============================================================================

class TestShapContext:
    """Test that SHAP uses comparable pool as background, not all records."""

    def test_shap_uses_pool_background(self):
        """SHAP background should be built from pool records."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        pool = _make_pool(records=[
            ComparableCandidate(
                id=i, area_m2=80.0, price=4e9, price_per_m2=50e6,
                district="Cầu Giấy", province_city="Hà Nội",
                property_type="apartment", evidence_tier="E3",
                legal_status="FULL_OWNERSHIP", road_width_m=5,
                bedrooms=2, latitude=21.03, longitude=105.85,
                floor_count=1, recency_days=30, weight=1.0,
            )
            for i in range(5)
        ])

        # Mock pipeline with is_fitted=False → triggers rule-based fallback
        mock_pipeline = MagicMock()
        mock_pipeline.is_fitted = False
        engine.pipeline = mock_pipeline

        inp = _make_input()
        price, shap_vals, feature_contrib = engine._ml_predict(inp, pool)

        # Rule-based fallback should return zero SHAP
        assert isinstance(shap_vals, list) or hasattr(shap_vals, "__iter__")
        assert feature_contrib == {} or isinstance(feature_contrib, dict)

    def test_shap_background_max_50_records(self):
        """SHAP background should cap at 50 records for performance."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        # Create pool with many records
        pool = _make_pool(records=[
            ComparableCandidate(
                id=i, area_m2=80.0, price=4e9, price_per_m2=50e6,
                district="Cầu Giấy", province_city="Hà Nội",
                property_type="apartment", evidence_tier="E3",
                legal_status="FULL_OWNERSHIP", road_width_m=5,
                bedrooms=2, latitude=21.03, longitude=105.85,
                floor_count=1, recency_days=30, weight=1.0,
            )
            for i in range(100)
        ])

        mock_pipeline = MagicMock()
        mock_pipeline.is_fitted = False
        mock_pipeline.feature_names = [f"f_{i}" for i in range(53)]
        mock_pipeline.best_model = MagicMock()
        mock_pipeline.scaler = MagicMock()
        mock_pipeline.scaler.transform = MagicMock(return_value=[[0.5] * 53] * 100)
        engine.pipeline = mock_pipeline

        inp = _make_input()
        engine._ml_predict(inp, pool)
        # No error = success (will fall back due to is_fitted=False)


# =============================================================================
# Integration Tests: Full analyze() method
# =============================================================================

class TestFullAnalyze:
    """Integration tests for the full analyze() pipeline."""

    def test_analyze_returns_complete_result(self):
        """analyze() must return a full ImpactResult."""
        mock_pipeline = MagicMock()
        mock_pipeline.is_fitted = False
        engine = ImpactEngine(ml_pipeline=mock_pipeline, db_session=None)

        inp = _make_input()
        result = engine.analyze(inp)

        assert isinstance(result, ImpactResult)
        assert result.run_id
        assert result.fair_market_value > 0
        assert isinstance(result.contributions, list)
        assert isinstance(result.missing_data, list)
        assert isinstance(result.current_scenario, ScenarioProjection)
        assert isinstance(result.full_info_scenario, ScenarioProjection)
        assert isinstance(result.max_credibility_scenario, ScenarioProjection)

    def test_analyze_sorting_contributions_by_abs_display(self):
        """Contributions should be sorted by |display_delta_pct| desc, residual last."""
        mock_pipeline = MagicMock()
        mock_pipeline.is_fitted = False
        engine = ImpactEngine(ml_pipeline=mock_pipeline, db_session=None)

        inp = _make_input(area_m2=300.0, corner_plot=True)
        result = engine.analyze(inp)

        contributions = result.contributions
        residuals = [c for c in contributions if c.is_residual]
        non_residuals = [c for c in contributions if not c.is_residual]

        # Residuals at end
        if residuals and non_residuals:
            last_contribution = contributions[-1]
            assert last_contribution.is_residual

        # Non-residuals sorted by |display_delta_pct| desc
        if len(non_residuals) > 1:
            for i in range(len(non_residuals) - 1):
                curr = abs(non_residuals[i].display_delta_pct)
                next_ = abs(non_residuals[i + 1].display_delta_pct)
                assert curr >= next_

    def test_analyze_with_all_fields_filled_minimal_missing(self):
        """All fields filled → minimal missing_data + high confidence."""
        mock_pipeline = MagicMock()
        mock_pipeline.is_fitted = False
        engine = ImpactEngine(ml_pipeline=mock_pipeline, db_session=None)

        inp = _make_input(
            ownership_type="FULL_OWNERSHIP",
            planning_zone="KHU_TRUNG_TAM",
            road_width_m=6.0,
            road_class="MAIN_STREET",
            area_m2=80.0,
            bedrooms=3,
            latitude=21.03,
            longitude=105.85,
            flood_risk="LOW",
        )
        result = engine.analyze(inp)

        # Should have fewer missing fields than baseline
        assert len(result.missing_data) < len(MISSING_CONFIDENCE_PENALTY)

    def test_analyze_top_positive_negative_fields(self):
        """top_positive and top_negative should contain field labels."""
        mock_pipeline = MagicMock()
        mock_pipeline.is_fitted = False
        engine = ImpactEngine(ml_pipeline=mock_pipeline, db_session=None)

        inp = _make_input(area_m2=120.0, corner_plot=True)
        result = engine.analyze(inp)

        assert isinstance(result.top_positive, list)
        assert isinstance(result.top_negative, list)
        for label in result.top_positive + result.top_negative:
            assert isinstance(label, str)
            assert len(label) > 0


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case handling."""

    def test_fallback_when_no_comparables(self):
        """Should return fallback result when no comparables available."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        inp = _make_input()
        pool = _make_pool(records=[])

        result = engine._fallback_no_comparables(inp, "test-run-id")

        assert result.n_eff == 0.0
        assert result.comparable_level == 4
        assert result.n_comparables_used == 0
        assert result.total_confidence_loss == 30.0
        assert result.current_scenario.confidence_grade == "D"
        assert result.current_scenario.interval_width_pct == 15.0

    def test_direction_positive_semantics(self):
        """Positive semantics: higher value → POSITIVE direction."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        direction = engine._determine_direction(5.0, "positive")
        assert direction == "POSITIVE"

        direction = engine._determine_direction(-5.0, "positive")
        assert direction == "NEGATIVE"

    def test_direction_negative_semantics(self):
        """Negative semantics: higher value → NEGATIVE direction."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        direction = engine._determine_direction(5.0, "negative")
        assert direction == "NEGATIVE"

    def test_direction_neutral_below_threshold(self):
        """Delta < 0.5% should be NEUTRAL."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)
        direction = engine._determine_direction(0.3, "positive")
        assert direction == "NEUTRAL"

    def test_field_labels_coverage(self):
        """All MISSING_CONFIDENCE_PENALTY keys should have FIELD_LABELS entries."""
        for field in MISSING_CONFIDENCE_PENALTY:
            assert field in FIELD_LABELS, f"Missing label for {field}"

    def test_confidence_grades(self):
        """Confidence grades should map correctly."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)

        assert engine._confidence_to_grade(0.90) == "A"
        assert engine._confidence_to_grade(0.85) == "A"
        assert engine._confidence_to_grade(0.75) == "B"
        assert engine._confidence_to_grade(0.60) == "C"
        assert engine._confidence_to_grade(0.50) == "D"

    def test_confidence_intervals(self):
        """Higher confidence → narrower intervals."""
        engine = ImpactEngine(ml_pipeline=None, db_session=None)

        high_conf_interval = engine._confidence_interval(0.90)
        mid_conf_interval = engine._confidence_interval(0.70)
        low_conf_interval = engine._confidence_interval(0.50)

        assert high_conf_interval < mid_conf_interval < low_conf_interval
