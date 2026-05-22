"""
Suitability Engine — Tổng hợp fit scores từ tất cả fit factors.

Fit scores hoàn toàn tách biệt với market valuation.
Đây là overlay layer dựa trên persona profile.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class PersonaProfile:
    """Persona profile của người mua tiềm năng."""
    buyer_archetype: str  # FIRST_HOME|UPGRADER|INVESTOR|SPECULATOR|RETIREE|ANONYMOUS
    budget_band: str  # BELOW_2B|2B_TO_5B|5B_TO_10B|10B_TO_20B|ABOVE_20B
    budget_min_vnd: Optional[int] = None
    budget_max_vnd: Optional[int] = None
    holding_horizon: str = "MEDIUM_5Y"  # FLIP_12M|SHORT_3Y|MEDIUM_5Y|LONG_10Y|FOREVER
    feng_shui_sensitivity: str = "NONE"  # NONE|LOW|MEDIUM|HIGH|CRITICAL
    birth_year: Optional[int] = None
    liquidity_preference: str = "BALANCED"  # MAX_LIQUID|PREFER_LIQUID|BALANCED|PREFER_APPRECIATION
    family_structure: str = "COUPLE_NO_KIDS"  # SINGLE|COUPLE_NO_KIDS|COUPLE_WITH_KIDS|LARGE_FAMILY|ELDERLY_PARENTS
    noise_tolerance: str = "NEUTRAL"  # VERY_SENSITIVE|SENSITIVE|NEUTRAL|TOLERANT|VERY_TOLERANT
    view_preference: str = "ANY_VIEW"  # PARK_REQUIRED|CITY_OK|NO_VIEW_OK|ANY_VIEW
    investment_profile: str = "BALANCED"  # RENTAL_YIELD|CAPITAL_APPRECIATION|BALANCED
    location_flexibility: str = "DISTRICT_FLEXIBLE"  # CBD_ONLY|DISTRICT_FLEXIBLE|CITY_WIDE|SUBURBS_OK


@dataclass
class FitScore:
    """Kết quả fit scoring."""
    overall: float = 0.0  # 0-1
    feng_shui_fit: float = 1.0
    liquidity_fit: float = 1.0
    family_layout_fit: float = 1.0
    investment_fit: float = 1.0
    budget_fit: float = 1.0
    lifestyle_fit: float = 1.0
    warnings: List[str] = field(default_factory=list)
    fit_reason: str = ""
    persona_archetype: str = ""


# Archetype → fit component weights
ARCHETYPE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "FIRST_HOME": {
        "budget": 0.40, "feng_shui": 0.10, "family": 0.25,
        "lifestyle": 0.15, "investment": 0.00, "liquidity": 0.10,
    },
    "UPGRADER": {
        "budget": 0.25, "feng_shui": 0.20, "family": 0.30,
        "lifestyle": 0.20, "investment": 0.00, "liquidity": 0.05,
    },
    "INVESTOR": {
        "budget": 0.20, "feng_shui": 0.00, "family": 0.00,
        "lifestyle": 0.05, "investment": 0.55, "liquidity": 0.20,
    },
    "SPECULATOR": {
        "budget": 0.30, "feng_shui": 0.00, "family": 0.00,
        "lifestyle": 0.00, "investment": 0.55, "liquidity": 0.15,
    },
    "RETIREE": {
        "budget": 0.25, "feng_shui": 0.25, "family": 0.20,
        "lifestyle": 0.25, "investment": 0.00, "liquidity": 0.05,
    },
    "ANONYMOUS": {
        "budget": 0.30, "feng_shui": 0.10, "family": 0.20,
        "lifestyle": 0.20, "investment": 0.10, "liquidity": 0.10,
    },
}


class SuitabilityEngine:
    """
    Tổng hợp fit scores từ persona + asset.

    Lưu ý: Đây là FIT LAYER, không ảnh hưởng market value.
    """

    def compute_fit(
        self,
        persona: PersonaProfile,
        asset_fair_market_vnd: int,
        asset_type: str,
        floor: Optional[int] = None,
        noise_score: Optional[float] = None,  # 0-1, cao = ồn
        view_type: Optional[str] = None,
        flood_risk: Optional[str] = None,
        feng_shui_result: Optional[Any] = None,
        building_age_years: Optional[int] = None,
    ) -> FitScore:
        """Tính overall fit score."""
        w = ARCHETYPE_WEIGHTS.get(persona.buyer_archetype, ARCHETYPE_WEIGHTS["ANONYMOUS"])

        # ── Budget fit ────────────────────────────────────────────────────
        budget_fit = self._compute_budget_fit(persona, asset_fair_market_vnd)

        # ── Feng Shui fit ─────────────────────────────────────────────────
        if feng_shui_result:
            feng_shui_fit = feng_shui_result.overall_feng_shui_score
        elif persona.feng_shui_sensitivity == "NONE":
            feng_shui_fit = 1.0
        else:
            feng_shui_fit = 0.7  # Unknown → default reasonable

        # ── Family layout fit ─────────────────────────────────────────────
        family_fit = self._compute_family_fit(persona, asset_type, floor, noise_score)

        # ── Lifestyle fit ─────────────────────────────────────────────────
        lifestyle_fit = self._compute_lifestyle_fit(persona, noise_score, view_type, flood_risk)

        # ── Investment fit ─────────────────────────────────────────────────
        investment_fit = self._compute_investment_fit(persona, asset_type, building_age_years)

        # ── Liquidity fit ─────────────────────────────────────────────────
        liquidity_fit = self._compute_liquidity_fit(persona, asset_type)

        # ── Overall weighted average ────────────────────────────────────────
        overall = (
            w["budget"] * budget_fit +
            w["feng_shui"] * feng_shui_fit +
            w["family"] * family_fit +
            w["lifestyle"] * lifestyle_fit +
            w["investment"] * investment_fit +
            w["liquidity"] * liquidity_fit
        )

        # ── Warnings & reason ─────────────────────────────────────────────
        warnings = []
        reasons = []

        if budget_fit < 0.5:
            warnings.append("Giá vượt ngân sách.")
            reasons.append(f"Property {asset_fair_market_vnd/1e9:.1f}t vượt budget.")
        elif budget_fit < 0.8:
            reasons.append("Giá nằm ở ngưỡng cao của budget.")

        if family_fit < 0.5:
            warnings.append("Property không phù hợp với cấu trúc gia đình.")

        if noise_score and noise_score > 0.6 and persona.noise_tolerance in ("VERY_SENSITIVE", "SENSITIVE"):
            warnings.append("Tiếng ồn cao, không phù hợp với mức nhạy cảm.")
            reasons.append("Tiếng ồn cao.")

        if investment_fit > 0.8:
            reasons.append("Phù hợp với chiến lược đầu tư.")

        if feng_shui_fit < 0.5:
            warnings.append("Phong thủy xấu theo tuổi người mua.")

        return FitScore(
            overall=round(overall, 2),
            feng_shui_fit=round(feng_shui_fit, 2),
            liquidity_fit=round(liquidity_fit, 2),
            family_layout_fit=round(family_fit, 2),
            investment_fit=round(investment_fit, 2),
            budget_fit=round(budget_fit, 2),
            lifestyle_fit=round(lifestyle_fit, 2),
            warnings=warnings,
            fit_reason="; ".join(reasons) if reasons else "Phù hợp theo profile người mua.",
            persona_archetype=persona.buyer_archetype,
        )

    def _compute_budget_fit(self, persona: PersonaProfile, asset_fair_market_vnd: int) -> float:
        """Tính budget fit (0-1)."""
        if persona.budget_max_vnd:
            if asset_fair_market_vnd > persona.budget_max_vnd * 1.1:
                return 0.3  # Over budget
            elif asset_fair_market_vnd > persona.budget_max_vnd:
                return 0.6  # At upper limit
            else:
                # Comfortable: 0.8-1.0
                margin = (persona.budget_max_vnd - asset_fair_market_vnd) / persona.budget_max_vnd
                return min(1.0, 0.8 + margin * 0.4)

        # Band-based fallback
        band_map = {
            "BELOW_2B": 1_000_000_000,
            "2B_TO_5B": 3_500_000_000,
            "5B_TO_10B": 7_500_000_000,
            "10B_TO_20B": 15_000_000_000,
            "ABOVE_20B": 25_000_000_000,
        }
        band_max = band_map.get(persona.budget_band, 5_000_000_000)
        if asset_fair_market_vnd > band_max:
            return max(0.2, 1.0 - (asset_fair_market_vnd - band_max) / band_max)
        return 1.0

    def _compute_family_fit(
        self, persona: PersonaProfile, asset_type: str, floor: Optional[int], noise_score: Optional[float]
    ) -> float:
        """Tính family layout fit (0-1)."""
        base = 1.0

        if persona.family_structure == "ELDERLY_PARENTS":
            if asset_type == "APARTMENT" and floor and floor > 5:
                base -= 0.3  # Too high for elderly
            base += 0.1 if noise_score and noise_score < 0.4 else -0.1

        elif persona.family_structure == "COUPLE_WITH_KIDS":
            if asset_type in ("APARTMENT", "TOWNHOUSE"):
                base += 0.05  # Good for families

        elif persona.family_structure == "SINGLE":
            if asset_type in ("STUDIO", "APARTMENT"):
                base += 0.05

        return max(0.0, min(1.0, base))

    def _compute_lifestyle_fit(
        self, persona: PersonaProfile, noise_score: Optional[float], view_type: Optional[str], flood_risk: Optional[str]
    ) -> float:
        """Tính lifestyle fit (0-1)."""
        score = 1.0

        # Noise sensitivity
        if noise_score and persona.noise_tolerance in ("VERY_SENSITIVE", "SENSITIVE"):
            if noise_score > 0.6:
                score -= 0.3
            elif noise_score > 0.4:
                score -= 0.1

        # View preference
        if persona.view_preference == "PARK_REQUIRED" and view_type not in ("PARK", "CITY_PARK"):
            score -= 0.15
        elif persona.view_preference == "NO_VIEW_OK":
            if view_type == "NOTHING":
                score += 0.05  # No view = no problem

        # Flood risk for all
        if flood_risk in ("moderate", "severe"):
            score -= 0.3
        elif flood_risk == "minor":
            score -= 0.1

        return max(0.0, min(1.0, score))

    def _compute_investment_fit(
        self, persona: PersonaProfile, asset_type: str, building_age_years: Optional[int]
    ) -> float:
        """Tính investment fit (0-1)."""
        if persona.buyer_archetype in ("FIRST_HOME", "UPGRADER", "RETIREE"):
            return 0.5  # Not investor

        score = 0.8

        if persona.investment_profile == "RENTAL_YIELD":
            if asset_type in ("APARTMENT", "SHOPHOUSE"):
                score += 0.1
            if building_age_years and building_age_years > 15:
                score -= 0.1  # Old = lower yield

        elif persona.investment_profile == "CAPITAL_APPRECIATION":
            if asset_type in ("LAND_URBAN", "LAND_PROJECT"):
                score += 0.1
            if building_age_years and building_age_years > 20:
                score -= 0.1

        return max(0.0, min(1.0, score))

    def _compute_liquidity_fit(self, persona: PersonaProfile, asset_type: str) -> float:
        """Tính liquidity fit (0-1)."""
        if persona.liquidity_preference == "MAX_LIQUIDITY":
            if asset_type in ("APARTMENT", "LAND_PROJECT"):
                return 0.9
            elif asset_type in ("TOWNHOUSE", "VILLA"):
                return 0.7
            else:
                return 0.5

        elif persona.liquidity_preference == "PREFER_APPRECIATION":
            if asset_type in ("LAND_URBAN", "LAND_PROJECT"):
                return 0.9
            return 0.6

        return 0.8  # Default balanced