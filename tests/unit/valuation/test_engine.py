"""
Unit tests cho Valuation Engine và Adjustment Registry.

Chạy: python -m pytest tests/unit/valuation/test_engine.py -v
"""

import pytest
from src.domain.valuation.engine import (
    ValuationEngine,
    AssetInput,
    ValuationResult,
    ComparableRecord,
    AdjustmentResult,
)
from src.domain.valuation.adjustment_registry import (
    AdjustmentRegistry,
    AdjustmentLayer,
    FactorGroup,
    FACTOR_REGISTRY,
)


class TestAdjustmentRegistry:
    """Tests cho AdjustmentRegistry."""

    def test_registry_has_all_40_factors(self):
        """Registry phải có ít nhất 40 factors cho alpha."""
        assert len(FACTOR_REGISTRY) >= 40, f"Expected >=40 factors, got {len(FACTOR_REGISTRY)}"

    def test_all_factor_codes_unique(self):
        """Mỗi factor_code phải unique."""
        codes = list(FACTOR_REGISTRY.keys())
        assert len(codes) == len(set(codes)), "Duplicate factor codes found"

    def test_market_factors_have_market_layer(self):
        """Market factors phải có layer = MARKET."""
        for code, adj in FACTOR_REGISTRY.items():
            if adj.layer == AdjustmentLayer.MARKET:
                assert adj.layer == AdjustmentLayer.MARKET

    def test_legal_factors_in_market_layer(self):
        """Legal factors phải ở layer MARKET."""
        registry = AdjustmentRegistry()
        legal = registry.list_by_group(FactorGroup.L1_LEGAL)
        assert len(legal) >= 5, "Should have at least 5 legal factors"
        for f in legal:
            assert f.layer == AdjustmentLayer.MARKET

    def test_access_factors_exist(self):
        """Access factors phải tồn tại cho alley widths."""
        registry = AdjustmentRegistry()
        access = registry.list_by_group(FactorGroup.L3_ACCESS)
        codes = [f.factor_code for f in access]
        assert "ACCESS_ALLEY_1M" in codes
        assert "ACCESS_ALLEY_2M" in codes
        assert "ACCESS_ALLEY_3M" in codes
        assert "ACCESS_MAIN_STREET" in codes

    def test_apartment_factors_exist(self):
        """Apartment-specific factors phải tồn tại."""
        registry = AdjustmentRegistry()
        apt_factors = registry.list_by_asset_type("APARTMENT")
        apt_codes = [f.factor_code for f in apt_factors]
        assert "APT_NO_VIEW" in apt_codes
        assert "APT_FLOOR_HIGH_15P" in apt_codes
        assert "APT_FLOOR_LOW_3M" in apt_codes
        assert "APT_VIEW_RIVER" in apt_codes

    def test_geometry_factors_for_land(self):
        """Geometry factors phải áp dụng cho LAND types."""
        registry = AdjustmentRegistry()
        # Registry uses "LAND" (not "LAND_URBAN") as asset type identifier
        geom = registry.list_by_asset_type("LAND")
        geom_codes = [f.factor_code for f in geom]
        assert "GEOM_NÖHẬU" in geom_codes
        assert "GEOM_THOP_HAU" in geom_codes
        assert "GEOM_CORNER_PLOT" in geom_codes

    def test_delta_pct_signs_correct(self):
        """Delta % phải đúng direction."""
        positive_codes = ["LEGAL_FULL", "ACCESS_MAIN_STREET", "GEOM_NÖHẬU", "GEOM_CORNER_PLOT", "APT_VIEW_RIVER"]
        negative_codes = ["LEGAL_DISPUTE", "ACCESS_ALLEY_2M", "ACCESS_ALLEY_1M", "ENV_FLOOD_SEVERE", "APT_NO_VIEW"]

        for code in positive_codes:
            adj = FACTOR_REGISTRY.get(code)
            if adj:
                assert adj.delta_pct_base >= 0, f"{code} should have positive delta"

        for code in negative_codes:
            adj = FACTOR_REGISTRY.get(code)
            if adj:
                assert adj.delta_pct_base < 0, f"{code} should have negative delta"

    def test_confidence_range(self):
        """Confidence phải trong khoảng 0-1."""
        for code, adj in FACTOR_REGISTRY.items():
            assert 0 <= adj.confidence_base <= 1, f"{code} confidence out of range"

    def test_rationale_templates_not_empty(self):
        """Tất cả rationale templates phải có nội dung."""
        for code, adj in FACTOR_REGISTRY.items():
            assert adj.rationale_template, f"{code} missing rationale_template"

    def test_get_applicable_factors_filters_by_layer(self):
        """get_applicable_factors phải filter đúng theo layer."""
        registry = AdjustmentRegistry()
        market = registry.get_applicable_factors("APARTMENT", AdjustmentLayer.MARKET)
        fit = registry.get_applicable_factors("APARTMENT", AdjustmentLayer.FIT)
        assert all(f.layer == AdjustmentLayer.MARKET for f in market)
        assert all(f.layer == AdjustmentLayer.FIT for f in fit)


class TestValuationEngine:
    """Tests cho ValuationEngine."""

    @pytest.fixture
    def engine(self):
        return ValuationEngine()

    @pytest.fixture
    def basic_land_input(self):
        return AssetInput(
            asset_type="LAND_URBAN",
            province_city="Hà Nội",
            district="Quận Cầu Giấy",
            area_m2=120.0,
            ownership_type="FULL_OWNERSHIP",
            road_class="ALLEY_3M",
            frontage_m=5.0,
            flood_risk="none",
            latitude=21.0285,
            longitude=105.8542,
        )

    @pytest.fixture
    def basic_apartment_input(self):
        return AssetInput(
            asset_type="APARTMENT",
            province_city="TP. Hồ Chí Minh",
            district="Quận 7",
            area_m2=85.0,
            apt_floor=15,
            view_type="CITY",
            ownership_type="FULL_OWNERSHIP",
            flood_risk="none",
        )

    @pytest.fixture
    def basic_townhouse_input(self):
        return AssetInput(
            asset_type="TOWNHOUSE",
            province_city="Hà Nội",
            district="Quận Thanh Xuân",
            area_m2=100.0,
            built_area_m2=80.0,
            floor_count=4,
            bedrooms=4,
            bathrooms=3,
            construction_year=2020,
            ownership_type="FULL_OWNERSHIP",
            road_class="MAIN_STREET",
        )

    @pytest.fixture
    def sample_comparables_land(self):
        return [
            ComparableRecord(
                legacy_id=1, asset_type="LAND_URBAN", province_city="Hà Nội",
                district="Quận Cầu Giấy", area_m2=100.0, price=7_500_000_000,
                price_per_m2=75_000_000, evidence_tier="E1", legal_status="full"
            ),
            ComparableRecord(
                legacy_id=2, asset_type="LAND_URBAN", province_city="Hà Nội",
                district="Quận Cầu Giấy", area_m2=130.0, price=9_100_000_000,
                price_per_m2=70_000_000, evidence_tier="E2", legal_status="full"
            ),
            ComparableRecord(
                legacy_id=3, asset_type="LAND_URBAN", province_city="Hà Nội",
                district="Quận Cầu Giấy", area_m2=90.0, price=6_300_000_000,
                price_per_m2=70_000_000, evidence_tier="E3", legal_status="full"
            ),
        ]

    def test_engine_run_returns_result(self, engine, basic_land_input):
        """Engine run phải trả về ValuationResult."""
        result = engine.run(basic_land_input)
        assert isinstance(result, ValuationResult)
        assert result.run_id is not None
        assert "v" in result.engine_version



    def test_alley_2m_negative_adjustment(self, engine, sample_comparables_land):
        """Hẻm 2m phải có adjustment âm."""
        input_data = AssetInput(
            asset_type="TOWNHOUSE",
            province_city="Hà Nội",
            district="Quận Cầu Giấy",
            area_m2=80.0,
            road_class="ALLEY_2M",
            ownership_type="FULL_OWNERSHIP",
        )
        engine.comparable_finder = lambda _: sample_comparables_land
        result = engine.run(input_data)
        adj_codes = [a.factor_code for a in result.market_adjustments]
        assert "ACCESS_ALLEY_2M" in adj_codes
        alley_adj = next(a for a in result.market_adjustments if a.factor_code == "ACCESS_ALLEY_2M")
        assert alley_adj.direction == "NEGATIVE"
        assert alley_adj.delta_vnd < 0

    def test_apartment_high_floor_positive(self, engine, basic_apartment_input):
        """Căn hộ tầng cao phải có adjustment dương."""
        result = engine.run(basic_apartment_input)
        adj_codes = [a.factor_code for a in result.market_adjustments]
        if "APT_FLOOR_HIGH_15P" in adj_codes:
            floor_adj = next(a for a in result.market_adjustments if a.factor_code == "APT_FLOOR_HIGH_15P")
            assert floor_adj.direction == "POSITIVE"
            assert floor_adj.delta_vnd > 0

    def test_apartment_no_view_negative(self, engine):
        """Căn hộ không view phải có adjustment âm."""
        input_data = AssetInput(
            asset_type="APARTMENT",
            province_city="TP. Hồ Chí Minh",
            district="Quận 7",
            area_m2=80.0,
            apt_floor=5,
            view_type="NOTHING",
            ownership_type="FULL_OWNERSHIP",
        )
        result = engine.run(input_data)
        adj_codes = [a.factor_code for a in result.market_adjustments]
        if "APT_NO_VIEW" in adj_codes:
            no_view = next(a for a in result.market_adjustments if a.factor_code == "APT_NO_VIEW")
            assert no_view.direction == "NEGATIVE"
            assert no_view.delta_vnd < 0



    def test_multiple_adjustments_applied(self, engine, basic_land_input, sample_comparables_land):
        """Nhiều adjustments phải được áp dụng đồng thời."""
        input_data = AssetInput(
            asset_type="TOWNHOUSE",
            province_city="Hà Nội",
            district="Quận Cầu Giấy",
            area_m2=100.0,
            road_class="MAIN_STREET",
            ownership_type="FULL_OWNERSHIP",
            flood_risk="none",
            apt_floor=12,
            view_type="CITY",
        )
        engine.comparable_finder = lambda _: sample_comparables_land
        result = engine.run(input_data)
        assert len(result.market_adjustments) >= 1

    def test_scenario_outputs_ordered(self, engine, basic_land_input, sample_comparables_land):
        """Scenario outputs phải có thứ tự: quick_sale < fair < listing < optimistic."""
        engine.comparable_finder = lambda _: sample_comparables_land
        result = engine.run(basic_land_input)
        assert result.quick_sale_value_vnd <= result.fair_market_value_vnd
        assert result.fair_market_value_vnd <= result.recommended_listing_vnd
        assert result.recommended_listing_vnd <= result.optimistic_ask_vnd

    def test_expected_range_wider_than_interval(self, engine, basic_land_input, sample_comparables_land):
        """Expected range phải chứa fair market value."""
        engine.comparable_finder = lambda _: sample_comparables_land
        result = engine.run(basic_land_input)
        assert result.expected_range_low_vnd <= result.fair_market_value_vnd
        assert result.fair_market_value_vnd <= result.expected_range_high_vnd
        # Range should be symmetric-ish
        low_gap = result.fair_market_value_vnd - result.expected_range_low_vnd
        high_gap = result.expected_range_high_vnd - result.fair_market_value_vnd
        ratio = abs(low_gap - high_gap) / result.fair_market_value_vnd
        assert ratio < 0.15, "Range should be roughly symmetric"

    def test_confidence_grade_corresponds_to_score(self, engine):
        """Confidence grade phải tương ứng với score."""
        # High confidence → grade A
        input_data = AssetInput(
            asset_type="TOWNHOUSE",
            province_city="Hà Nội",
            district="Quận Cầu Giấy",
            area_m2=100.0,
            road_class="MAIN_STREET",
            ownership_type="FULL_OWNERSHIP",
            latitude=21.0285,
            longitude=105.8542,
        )
        coms = [
            ComparableRecord(
                legacy_id=i, asset_type="TOWNHOUSE", province_city="Hà Nội",
                district="Quận Cầu Giấy", area_m2=100.0, price=8_000_000_000,
                price_per_m2=80_000_000, evidence_tier="E1" if i % 2 == 0 else "E2",
                legal_status="full"
            ) for i in range(10)
        ]
        engine.comparable_finder = lambda _: coms
        result = engine.run(input_data)
        assert result.overall_confidence > 0.5

    def test_input_hash_deterministic(self, engine, basic_land_input):
        """Input hash phải deterministic (cùng input → cùng hash)."""
        result1 = engine.run(basic_land_input)
        result2 = engine.run(basic_land_input)
        assert result1.input_hash == result2.input_hash

    def test_fair_market_value_clamps_reasonable(self, engine):
        """Fair market value không được quá cao hoặc quá thấp."""
        input_data = AssetInput(
            asset_type="TOWNHOUSE",
            province_city="Hà Nội",
            district="Quận Cầu Giấy",
            area_m2=1000.0,  # huge area
            ownership_type="FULL_OWNERSHIP",
        )
        result = engine.run(input_data)
        # VND 50M min, 100B max clamp
        assert 50_000_000 <= result.fair_market_value_vnd <= 100_000_000_000

    def test_adj_result_has_all_required_fields(self, engine, basic_land_input):
        """AdjustmentResult phải có đầy đủ fields."""
        result = engine.run(basic_land_input)
        for adj in result.market_adjustments:
            assert adj.factor_code
            assert adj.layer in ("MARKET", "FIT")
            assert adj.direction in ("POSITIVE", "NEGATIVE", "NEUTRAL")
            assert -1.0 <= adj.delta_pct <= 1.0
            assert isinstance(adj.delta_vnd, int)
            assert 0 <= adj.confidence <= 1
            assert adj.rationale

    def test_comparable_breakdown_tiers(self, engine, sample_comparables_land):
        """Comparable breakdown phải count đúng theo tier."""
        engine.comparable_finder = lambda _: sample_comparables_land
        input_data = AssetInput(
            asset_type="LAND_URBAN",
            province_city="Hà Nội",
            district="Quận Cầu Giấy",
            area_m2=100.0,
            ownership_type="FULL_OWNERSHIP",
        )
        result = engine.run(input_data)
        assert result.comparable_breakdown.get("E1") == 1
        assert result.comparable_breakdown.get("E2") == 1
        assert result.comparable_breakdown.get("E3") == 1
        assert result.comparable_count == 3

    def test_different_asset_types_get_different_adjustments(self, engine, sample_comparables_land):
        """Asset types khác nhau phải nhận adjustments khác nhau."""
        engine.comparable_finder = lambda _: sample_comparables_land

        land_input = AssetInput(
            asset_type="LAND_URBAN",
            province_city="Hà Nội",
            district="Quận Cầu Giấy",
            area_m2=100.0,
            ownership_type="FULL_OWNERSHIP",
            road_class="MAIN_STREET",
            corner_plot=True,
        )
        apt_input = AssetInput(
            asset_type="APARTMENT",
            province_city="TP. Hồ Chí Minh",
            district="Quận 7",
            area_m2=80.0,
            apt_floor=20,
            view_type="RIVER",
            ownership_type="FULL_OWNERSHIP",
        )

        land_result = engine.run(land_input)
        apt_result = engine.run(apt_input)

        land_codes = set(a.factor_code for a in land_result.market_adjustments)
        apt_codes = set(a.factor_code for a in apt_result.market_adjustments)

        # Land có geometry adjustments
        assert "GEOM_CORNER_PLOT" in land_codes
        # Apartment có floor/view adjustments
        assert "APT_VIEW_RIVER" in apt_codes or "APT_FLOOR_HIGH_15P" in apt_codes

    def test_output_dict_format(self, engine, basic_land_input):
        """to_dict() output phải đúng format."""
        result = engine.run(basic_land_input)
        d = result.to_dict()

        assert "market_valuation" in d
        assert "fit_suitability" in d
        assert "confidence_evidence" in d

        mv = d["market_valuation"]
        assert "fair_market_value" in mv
        assert "quick_sale_value" in mv
        assert "recommended_listing" in mv
        assert "adjustment_ledger" in mv
        assert isinstance(mv["adjustment_ledger"], list)

        ce = d["confidence_evidence"]
        assert "overall_confidence" in ce
        assert "confidence_grade" in ce
        assert "evidence_tier" in ce


class TestEdgeCases:
    """Tests cho edge cases."""

    @pytest.fixture
    def engine(self):
        return ValuationEngine()

    def test_no_comparables_still_runs(self, engine):
        """Không có comparables vẫn phải trả về kết quả."""
        input_data = AssetInput(
            asset_type="TOWNHOUSE",
            province_city="Đà Nẵng",
            district="Quận Hải Châu",
            area_m2=80.0,
        )
        result = engine.run(input_data)
        assert result.fair_market_value_vnd > 0
        assert result.overall_confidence < 0.6  # Low confidence without comparables
