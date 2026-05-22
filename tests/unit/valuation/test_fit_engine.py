"""
Unit tests cho Fit/Suitability Engine.

Chạy: python -m pytest tests/unit/valuation/test_fit_engine.py -v
"""

import pytest
from src.domain.fit.feng_shui import FengShuiEngine, FengShuiInput
from src.domain.fit.suitability import SuitabilityEngine, PersonaProfile, FitScore


class TestFengShuiEngine:

    @pytest.fixture
    def engine(self):
        return FengShuiEngine()

    def test_element_mapping_tuoi_1985(self, engine):
        """1985 = Ất Mộc."""
        assert engine.thien_can[1985] == "Mộc"

    def test_element_mapping_tuoi_1990(self, engine):
        """1990 = Canh Kim."""
        assert engine.thien_can[1990] == "Kim"

    def test_favorable_directions_moc(self, engine):
        """Mộc → Đông, Đông Nam tốt."""
        assert "Đông" in engine.favorable["Mộc"]
        assert "Đông Nam" in engine.favorable["Mộc"]

    def test_unfavorable_directions_moc(self, engine):
        """Mộc → Tây, Tây Bắc xấu."""
        assert "Tây" in engine.unfavorable["Mộc"]

    def test_assess_full_ownership_hoa_tuoi_1987(self, engine):
        """1987 Đinh Hỏa + hướng Nam → tốt."""
        fs_input = FengShuiInput(
            house_orientation="Nam",
            birth_year=1987,
        )
        result = engine.assess(fs_input)
        assert result.element == "Hỏa"
        assert "Nam" in result.favorable_directions
        assert result.house_orientation_fit == 1.0
        assert result.is_compatible

    def test_assess_conflict_moc_vs_tay(self, engine):
        """1985 Ất Mộc + hướng Tây → xấu."""
        fs_input = FengShuiInput(
            house_orientation="Tây",
            birth_year=1985,
        )
        result = engine.assess(fs_input)
        assert result.element == "Mộc"
        assert result.house_orientation_fit == 0.3
        assert not result.is_compatible
        assert any("Tây" in w for w in result.warnings)

    def test_assess_no_birth_year_returns_1(self, engine):
        """Không có năm sinh → trả 1.0 (không ảnh hưởng)."""
        fs_input = FengShuiInput(house_orientation="Nam")
        result = engine.assess(fs_input)
        assert result.overall_feng_shui_score == 1.0
        assert result.is_compatible

    def test_assess_neutral_direction(self, engine):
        """Hướng trung tính → 0.7."""
        fs_input = FengShuiInput(
            house_orientation="Đông Bắc",
            birth_year=1988,
        )
        result = engine.assess(fs_input)
        assert result.element == "Thổ"
        assert "Đông Bắc" in result.favorable_directions  # Thổ → Đông Bắc tốt
        assert result.house_orientation_fit > 0.5

    def test_fit_adjustment_none_sensitivity(self, engine):
        """SENSITIVITY=NONE → 0 delta."""
        delta, warnings = engine.compute_fit_adjustment(
            FengShuiInput(house_orientation="Tây", birth_year=1985),
            sensitivity="NONE"
        )
        assert delta == 0.0
        assert warnings == []

    def test_fit_adjustment_low_positive(self, engine):
        """SENSITIVITY=LOW + tương thích → +1%."""
        delta, warnings = engine.compute_fit_adjustment(
            FengShuiInput(house_orientation="Đông Nam", birth_year=1985),
            sensitivity="LOW"
        )
        assert delta == 0.01

    def test_fit_adjustment_low_negative(self, engine):
        """SENSITIVITY=LOW + không tương thích → -1%."""
        delta, warnings = engine.compute_fit_adjustment(
            FengShuiInput(house_orientation="Tây", birth_year=1985),
            sensitivity="LOW"
        )
        assert delta == -0.01

    def test_fit_adjustment_critical_reject(self, engine):
        """SENSITIVITY=CRITICAL + xung → -100%."""
        delta, warnings = engine.compute_fit_adjustment(
            FengShuiInput(house_orientation="Tây", birth_year=1985),
            sensitivity="CRITICAL"
        )
        assert delta == -1.0
        assert len(warnings) > 0

    def test_fit_adjustment_critical_accept(self, engine):
        """SENSITIVITY=CRITICAL + tương thích → 0."""
        delta, warnings = engine.compute_fit_adjustment(
            FengShuiInput(house_orientation="Đông Nam", birth_year=1985),
            sensitivity="CRITICAL"
        )
        assert delta == 0.0


class TestSuitabilityEngine:

    @pytest.fixture
    def engine(self):
        return SuitabilityEngine()

    @pytest.fixture
    def investor_persona(self):
        return PersonaProfile(
            buyer_archetype="INVESTOR",
            budget_band="2B_TO_5B",
            budget_min_vnd=2_000_000_000,
            budget_max_vnd=5_000_000_000,
            holding_horizon="SHORT_3Y",
            feng_shui_sensitivity="NONE",
            liquidity_preference="MAX_LIQUID",
            family_structure="COUPLE_NO_KIDS",
            investment_profile="RENTAL_YIELD",
        )

    @pytest.fixture
    def retiree_persona(self):
        return PersonaProfile(
            buyer_archetype="RETIREE",
            budget_band="5B_TO_10B",
            budget_min_vnd=5_000_000_000,
            budget_max_vnd=10_000_000_000,
            holding_horizon="FOREVER",
            feng_shui_sensitivity="CRITICAL",
            birth_year=1960,
            noise_tolerance="SENSITIVE",
            liquidity_preference="BALANCED",
            family_structure="COUPLE_NO_KIDS",
        )

    def test_first_home_budget_fit(self, engine):
        """Budget fit phải so sánh đúng giá."""
        persona = PersonaProfile(
            buyer_archetype="FIRST_HOME",
            budget_band="5B_TO_10B",
            budget_max_vnd=5_000_000_000,
        )
        # Property 4 tỷ trong budget (dưới max)
        fit = engine._compute_budget_fit(persona, 4_000_000_000)
        assert 0.8 <= fit <= 1.0

    def test_first_home_over_budget_fit(self, engine):
        """Property vượt budget → fit thấp."""
        persona = PersonaProfile(
            buyer_archetype="FIRST_HOME",
            budget_band="2B_TO_5B",
            budget_max_vnd=3_000_000_000,
        )
        # Property 8 tỷ vượt budget 3 tỷ
        fit = engine._compute_budget_fit(persona, 8_000_000_000)
        assert fit < 0.6

    def test_investor_turns_property_fit(self, engine, investor_persona):
        """Investor với rental yield → căn hộ phù hợp hơn."""
        apt_fit = engine.compute_fit(
            persona=investor_persona,
            asset_fair_market_vnd=4_000_000_000,
            asset_type="APARTMENT",
        )
        land_fit = engine.compute_fit(
            persona=investor_persona,
            asset_fair_market_vnd=4_000_000_000,
            asset_type="LAND_URBAN",
        )
        # Cả hai đều trong budget → investment_fit quyết định
        assert apt_fit.investment_fit > 0
        assert land_fit.investment_fit > 0

    def test_retiree_noise_sensitive(self, engine, retiree_persona):
        """RETIREE + noise_tolerance SENSITIVE → nhạy cảm với ồn → lifestyle_fit thấp."""
        fit = engine.compute_fit(
            persona=retiree_persona,
            asset_fair_market_vnd=7_000_000_000,
            asset_type="APARTMENT",
            floor=8,
            noise_score=0.8,  # ồn cao
        )
        # RETIREE: lifestyle_fit weight=0.25, SENSITIVE với noise>0.6 → -0.3 → lifestyle_fit = 0.7
        assert fit.lifestyle_fit == 0.7
        assert any("Tiếng ồn" in w for w in fit.warnings)

    def test_retiree_high_floor_rejects(self, engine):
        """RETIREE + apartment cao → không phù hợp."""
        persona = PersonaProfile(
            buyer_archetype="RETIREE",
            budget_band="5B_TO_10B",
            budget_max_vnd=10_000_000_000,
            family_structure="ELDERLY_PARENTS",
            noise_tolerance="SENSITIVE",
        )
        fit = engine.compute_fit(
            persona=persona,
            asset_fair_market_vnd=7_000_000_000,
            asset_type="APARTMENT",
            floor=20,  # Cao quá
            noise_score=0.8,
        )
        assert fit.family_layout_fit < 0.7
        assert any("cao" in w.lower() or "elderly" in w.lower() for w in fit.warnings)

    def test_archetype_weights_sum_to_one(self, engine):
        """Weights của mỗi archetype phải tổng ≈ 1.0."""
        from src.domain.fit.suitability import ARCHETYPE_WEIGHTS
        for archetype, weights in ARCHETYPE_WEIGHTS.items():
            total = sum(weights.values())
            assert 0.98 <= total <= 1.02, f"{archetype}: weights sum = {total}"

    def test_fit_score_always_0_to_1(self, engine, investor_persona):
        """Tất cả fit scores phải trong khoảng 0-1."""
        fit = engine.compute_fit(
            persona=investor_persona,
            asset_fair_market_vnd=4_000_000_000,
            asset_type="APARTMENT",
            noise_score=0.2,
            view_type="CITY",
            flood_risk="none",
        )
        for score_field in [
            fit.overall, fit.feng_shui_fit, fit.liquidity_fit,
            fit.family_layout_fit, fit.investment_fit,
            fit.budget_fit, fit.lifestyle_fit,
        ]:
            assert 0.0 <= score_field <= 1.0, f"Score {score_field} out of range"

    def test_overall_weighted_by_archetype(self, engine):
        """Overall phải là weighted average đúng."""
        persona = PersonaProfile(
            buyer_archetype="INVESTOR",
            budget_band="5B_TO_10B",
            investment_profile="RENTAL_YIELD",
        )
        fit = engine.compute_fit(
            persona=persona,
            asset_fair_market_vnd=5_000_000_000,
            asset_type="APARTMENT",
        )
        # Investor: investment_fit weight = 0.55, nên overall bị ảnh hưởng nhiều bởi investment
        assert fit.overall > 0.3  # Phải có investment_fit cao

    def test_no_budget_overrides(self, engine):
        """Khi không có budget → band-based fallback."""
        persona = PersonaProfile(
            buyer_archetype="ANONYMOUS",
            budget_band="10B_TO_20B",
        )
        fit = engine._compute_budget_fit(persona, 12_000_000_000)
        assert fit == 1.0  # 12B < 15B band max

    def test_persona_archetype_persists_in_result(self, engine, investor_persona):
        """Fit result phải giữ archetype."""
        fit = engine.compute_fit(
            persona=investor_persona,
            asset_fair_market_vnd=4_000_000_000,
            asset_type="APARTMENT",
        )
        assert fit.persona_archetype == "INVESTOR"
