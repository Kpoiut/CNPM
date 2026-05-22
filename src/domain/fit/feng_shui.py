"""
Feng Shui Engine — Tính phong thủy và độ phù hợp với tuổi người mua.

Đây là LỚP FIT, không ảnh hưởng market_value.
Chỉ dùng khi feng_shui_sensitivity != NONE.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# Ngũ hành của thiên can
THIEN_CAN_ELEMENT: Dict[int, str] = {
    1984: "Mộc", 1985: "Mộc",
    1986: "Hỏa", 1987: "Hỏa",
    1988: "Thổ", 1989: "Thổ",
    1990: "Kim", 1991: "Kim",
    1992: "Thủy", 1993: "Thủy",
    1994: "Mộc", 1995: "Mộc",
    1996: "Hỏa", 1997: "Hỏa",
    1998: "Thổ", 1999: "Thổ",
    2000: "Kim", 2001: "Kim",
    2002: "Thủy", 2003: "Thủy",
    2004: "Mộc", 2005: "Mộc",
    2006: "Hỏa", 2007: "Hỏa",
    2008: "Thổ", 2009: "Thổ",
    2010: "Kim", 2011: "Kim",
    2012: "Thủy", 2013: "Thủy",
    2014: "Mộc", 2015: "Mộc",
    2016: "Hỏa", 2017: "Hỏa",
    2018: "Thổ", 2019: "Thổ",
    2020: "Kim", 2021: "Kim",
    2022: "Thủy", 2023: "Thủy",
    2024: "Mộc", 2025: "Mộc",
    2026: "Hỏa",
}

# Hướng tốt theo ngũ hành (sinh khắc)
ELEMENT_FAVORABLE_DIRECTIONS: Dict[str, List[str]] = {
    "Mộc": ["Đông", "Đông Nam"],
    "Hỏa": ["Nam"],
    "Thổ": ["Tây Nam", "Đông Bắc"],
    "Kim": ["Tây", "Tây Bắc"],
    "Thủy": ["Bắc"],
}

# Hướng xấu theo ngũ hành
ELEMENT_UNFAVORABLE_DIRECTIONS: Dict[str, List[str]] = {
    "Mộc": ["Tây", "Tây Bắc"],
    "Hỏa": ["Bắc"],
    "Thổ": ["Đông"],
    "Kim": ["Đông Nam"],
    "Thủy": ["Nam"],
}

# Điểm phong thủy cơ bản cho mỗi hướng
DIRECTION_SCORE: Dict[str, float] = {
    "Đông": 0.85,
    "Đông Nam": 0.85,
    "Nam": 0.80,
    "Tây Nam": 0.80,
    "Đông Bắc": 0.75,
    "Tây": 0.70,
    "Tây Bắc": 0.70,
    "Bắc": 0.65,
    "Tây Bắc": 0.70,
}


@dataclass
class FengShuiInput:
    """Input cho Feng Shui engine."""
    house_orientation: str  # NORTH|SOUTH|EAST|WEST|...
    birth_year: Optional[int] = None
    main_door_direction: Optional[str] = None
    bedroom_orientation: Optional[str] = None


@dataclass
class FengShuiResult:
    """Kết quả Feng Shui assessment."""
    element: Optional[str] = None  # Ngũ hành của chủ nhà
    favorable_directions: List[str] = None
    unfavorable_directions: List[str] = None
    house_orientation_fit: float = 1.0  # 0-1
    overall_feng_shui_score: float = 1.0  # 0-1
    is_compatible: bool = True
    warnings: List[str] = None
    explanation: str = ""


class FengShuiEngine:
    """Tính Feng Shui fit score."""

    def __init__(self):
        self.thien_can = THIEN_CAN_ELEMENT
        self.favorable = ELEMENT_FAVORABLE_DIRECTIONS
        self.unfavorable = ELEMENT_UNFAVORABLE_DIRECTIONS
        self.direction_score = DIRECTION_SCORE

    def assess(self, fs_input: FengShuiInput) -> FengShuiResult:
        """
        Đánh giá Feng Shui của property với chủ nhà.

        Returns:
            FengShuiResult với overall score 0-1.
            Score = 1.0 means perfectly compatible.
        """
        warnings: List[str] = []
        explanations: List[str] = []

        # 1. Xác định ngũ hành của chủ nhà
        element = None
        if fs_input.birth_year:
            element = self.thien_can.get(fs_input.birth_year)

        if not element:
            # Không xác định được → trả 1.0 (không ảnh hưởng)
            return FengShuiResult(
                element=None,
                favorable_directions=[],
                unfavorable_directions=[],
                house_orientation_fit=1.0,
                overall_feng_shui_score=1.0,
                is_compatible=True,
                warnings=["Không xác định được ngũ hành từ năm sinh"],
                explanation="Không đủ thông tin để đánh giá phong thủy.",
            )

        favorable = self.favorable.get(element, [])
        unfavorable = self.unfavorable.get(element, [])

        # 2. Đánh giá hướng nhà
        orientation = fs_input.house_orientation or fs_input.main_door_direction
        house_fit = 1.0
        if orientation:
            if orientation in favorable:
                house_fit = 1.0
                explanations.append(f"Hướng {orientation} thuộc hành {element} — rất tốt.")
            elif orientation in unfavorable:
                house_fit = 0.3
                warnings.append(f"Hướng {orientation} xung khắc với tuổi {fs_input.birth_year} ({element}).")
                explanations.append(f"Hướng {orientation} xung khắc với ngũ hành {element}.")
            else:
                house_fit = 0.7
                explanations.append(f"Hướng {orientation} trung tính với ngũ hành {element}.")

        # 3. Overall Feng Shui score
        overall = house_fit

        return FengShuiResult(
            element=element,
            favorable_directions=favorable,
            unfavorable_directions=unfavorable,
            house_orientation_fit=house_fit,
            overall_feng_shui_score=overall,
            is_compatible=(overall >= 0.7),
            warnings=warnings,
            explanation="; ".join(explanations) if explanations else "Phong thủy phù hợp.",
        )

    def compute_fit_adjustment(
        self,
        fs_input: FengShuiInput,
        sensitivity: str,
    ) -> Tuple[float, List[str]]:
        """
        Tính fit adjustment từ Feng Shui.

        Args:
            fs_input: Dữ liệu phong thủy
            sensitivity: NONE | LOW | MEDIUM | HIGH | CRITICAL

        Returns:
            (delta_pct, warnings)
        """
        if sensitivity == "NONE":
            return 0.0, []

        if sensitivity == "LOW":
            # Low: ±1-2%
            fs_result = self.assess(fs_input)
            if fs_result.is_compatible:
                return 0.01, []
            else:
                return -0.01, fs_result.warnings

        if sensitivity == "MEDIUM":
            # Medium: ±3-5%
            fs_result = self.assess(fs_input)
            if fs_result.is_compatible:
                return 0.03, []
            else:
                return -0.03, fs_result.warnings

        if sensitivity == "HIGH":
            # High: ±5-10%
            fs_result = self.assess(fs_input)
            score = fs_result.overall_feng_shui_score
            delta = (score - 0.5) * 0.20  # -10% to +10%
            return delta, fs_result.warnings

        # CRITICAL: refuse if incompatible
        fs_result = self.assess(fs_input)
        if not fs_result.is_compatible:
            return -1.0, fs_result.warnings + ["CRITICAL: Người mua từ chối property do phong thủy xấu."]
        return 0.0, []
