"""
Environment Risk Catalog — Production-grade environmental impact assessment.

Differentiator vs existing AVM research:
- Most papers treat environment as optional/notes. This engine provides:
  1. Structured catalog of 23 hazard types with severity scales
  2. Automatic adjustment computation from hazard proximity
  3. Buffer zone impact with distance-based decay
  4. Risk aggregation into composite environment score
  5. Each hazard generates an adjustment entry with confidence + source

Key principle: Every environmental factor must have:
  - geometry (point/polygon/buffer on map)
  - distance_m from property
  - impact_direction and impact_pct
  - confidence level and evidence source
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math


@dataclass
class HazardEntry:
    """A single environmental hazard near the property."""
    hazard_code: str
    hazard_label: str
    category: str           # FLOOD|NOISE|POLLUTION|NEGATIVE_PROXIMITY|POSITIVE_PROXIMITY|INFRASTRUCTURE
    distance_m: float
    severity: str            # none|minor|moderate|severe|critical
    impact_pct: float        # Negative = decreases value
    confidence: float        # 0-1
    source: str              # observed|modelled|reported|estimated
    explanation: str
    buffer_radius_m: float = 0.0    # Radius of impact zone
    geometry_type: str = "point"     # point|polygon|buffer

    def to_dict(self) -> Dict:
        return {
            "hazard_code": self.hazard_code,
            "hazard_label": self.hazard_label,
            "category": self.category,
            "distance_m": round(self.distance_m, 1),
            "severity": self.severity,
            "impact_pct": round(self.impact_pct, 4),
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "explanation": self.explanation,
        }


@dataclass
class EnvironmentAssessment:
    """Complete environmental assessment result."""
    hazards: List[HazardEntry] = field(default_factory=list)
    positive_factors: List[HazardEntry] = field(default_factory=list)
    total_negative_pct: float = 0.0
    total_positive_pct: float = 0.0
    net_impact_pct: float = 0.0
    env_quality_score: float = 0.5  # 0=terrible, 1=excellent
    risk_grade: str = "B"           # A|B|C|D|F
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "hazards": [h.to_dict() for h in self.hazards],
            "positive_factors": [p.to_dict() for p in self.positive_factors],
            "total_negative_pct": round(self.total_negative_pct, 4),
            "total_positive_pct": round(self.total_positive_pct, 4),
            "net_impact_pct": round(self.net_impact_pct, 4),
            "env_quality_score": round(self.env_quality_score, 3),
            "risk_grade": self.risk_grade,
            "warnings": self.warnings,
        }


# ─── HAZARD CATALOG ──────────────────────────────────────────────────

HAZARD_CATALOG: Dict[str, Dict] = {
    # FLOOD
    "FLOOD_NONE":       {"cat": "FLOOD", "base_pct": 0.03, "label": "Không ngập lụt", "conf": 0.80},
    "FLOOD_MINOR":      {"cat": "FLOOD", "base_pct": -0.06, "label": "Ngập nhẹ theo mùa", "conf": 0.75},
    "FLOOD_MODERATE":   {"cat": "FLOOD", "base_pct": -0.12, "label": "Ngập vừa", "conf": 0.80},
    "FLOOD_SEVERE":     {"cat": "FLOOD", "base_pct": -0.18, "label": "Ngập nặng thường xuyên", "conf": 0.85},
    "SUBSIDENCE":       {"cat": "FLOOD", "base_pct": -0.10, "label": "Sạt lở / lún đất", "conf": 0.70},

    # NOISE
    "NOISE_DAY_HIGH":   {"cat": "NOISE", "base_pct": -0.05, "label": "Tiếng ồn ban ngày >65dB", "conf": 0.75},
    "NOISE_NIGHT_HIGH": {"cat": "NOISE", "base_pct": -0.07, "label": "Tiếng ồn ban đêm >55dB", "conf": 0.75},
    "AIRPORT_NOISE":    {"cat": "NOISE", "base_pct": -0.08, "label": "Gần sân bay, ồn máy bay", "conf": 0.80},
    "HIGHWAY_NOISE":    {"cat": "NOISE", "base_pct": -0.04, "label": "Gần đường cao tốc", "conf": 0.70},

    # NEGATIVE PROXIMITY
    "CEMETERY":         {"cat": "NEGATIVE_PROXIMITY", "base_pct": -0.06, "label": "Gần nghĩa trang", "conf": 0.70, "buffer_m": 200},
    "LANDFILL":         {"cat": "NEGATIVE_PROXIMITY", "base_pct": -0.08, "label": "Gần bãi rác", "conf": 0.75, "buffer_m": 500},
    "POWER_LINE":       {"cat": "NEGATIVE_PROXIMITY", "base_pct": -0.04, "label": "Gần cột điện cao thế", "conf": 0.65, "buffer_m": 100},
    "INDUSTRIAL_ZONE":  {"cat": "NEGATIVE_PROXIMITY", "base_pct": -0.05, "label": "Gần khu công nghiệp", "conf": 0.70, "buffer_m": 500},
    "STAGNANT_WATER":   {"cat": "NEGATIVE_PROXIMITY", "base_pct": -0.04, "label": "Ao tù / nước đọng", "conf": 0.60, "buffer_m": 100},
    "ROAD_COLLISION":   {"cat": "NEGATIVE_PROXIMITY", "base_pct": -0.05, "label": "Đường đâm thẳng vào nhà", "conf": 0.70},
    "T_JUNCTION":       {"cat": "NEGATIVE_PROXIMITY", "base_pct": -0.03, "label": "Ngã ba T", "conf": 0.60},
    "TECH_STATION":     {"cat": "NEGATIVE_PROXIMITY", "base_pct": -0.02, "label": "Trạm kỹ thuật / biến áp", "conf": 0.55, "buffer_m": 50},
    "HEAVY_TRUCK_ROUTE":{"cat": "NEGATIVE_PROXIMITY", "base_pct": -0.03, "label": "Tuyến xe tải nặng", "conf": 0.65},

    # POLLUTION
    "AIR_POOR":         {"cat": "POLLUTION", "base_pct": -0.04, "label": "Chất lượng không khí kém", "conf": 0.65},
    "DUST_HIGH":        {"cat": "POLLUTION", "base_pct": -0.03, "label": "Bụi bẩn cao", "conf": 0.60},

    # POSITIVE PROXIMITY
    "PARK_NEAR":        {"cat": "POSITIVE_PROXIMITY", "base_pct": 0.04, "label": "Gần công viên", "conf": 0.75, "buffer_m": 500},
    "RIVER_VIEW":       {"cat": "POSITIVE_PROXIMITY", "base_pct": 0.06, "label": "View sông", "conf": 0.70, "buffer_m": 200},
    "LAKE_NEAR":        {"cat": "POSITIVE_PROXIMITY", "base_pct": 0.04, "label": "Gần hồ", "conf": 0.70, "buffer_m": 300},
    "SCHOOL_NEAR":      {"cat": "POSITIVE_PROXIMITY", "base_pct": 0.03, "label": "Gần trường học tốt", "conf": 0.65, "buffer_m": 1000},
    "HOSPITAL_NEAR":    {"cat": "POSITIVE_PROXIMITY", "base_pct": 0.02, "label": "Gần bệnh viện", "conf": 0.60, "buffer_m": 1500},
    "METRO_NEAR":       {"cat": "POSITIVE_PROXIMITY", "base_pct": 0.08, "label": "Gần ga metro", "conf": 0.85, "buffer_m": 500},
    "MARKET_NEAR":      {"cat": "POSITIVE_PROXIMITY", "base_pct": 0.02, "label": "Gần chợ / siêu thị", "conf": 0.55, "buffer_m": 800},
}


class EnvironmentRiskEngine:
    """
    Assess environmental risks and positive factors for a property.

    Key difference from existing research:
    - Structured catalog instead of free-text notes
    - Distance-based impact decay
    - Each factor produces an auditable adjustment entry
    """

    def __init__(self):
        self.catalog = HAZARD_CATALOG

    def assess(
        self,
        flood_risk: Optional[str] = None,
        noise_day_db: Optional[float] = None,
        noise_night_db: Optional[float] = None,
        pollution_score: Optional[float] = None,
        cemetery_distance_m: Optional[float] = None,
        landfill_distance_m: Optional[float] = None,
        power_line_distance_m: Optional[float] = None,
        industrial_zone_m: Optional[float] = None,
        river_distance_m: Optional[float] = None,
        park_distance_m: Optional[float] = None,
        lake_distance_m: Optional[float] = None,
        school_distance_m: Optional[float] = None,
        hospital_distance_m: Optional[float] = None,
        metro_distance_m: Optional[float] = None,
        market_distance_m: Optional[float] = None,
        road_collision: bool = False,
        t_junction: bool = False,
        stagnant_water_m: Optional[float] = None,
    ) -> EnvironmentAssessment:
        """Run environmental assessment."""
        result = EnvironmentAssessment()
        hazards: List[HazardEntry] = []
        positives: List[HazardEntry] = []

        # ── FLOOD ──
        if flood_risk:
            entry = self._assess_flood(flood_risk)
            if entry:
                if entry.impact_pct >= 0:
                    positives.append(entry)
                else:
                    hazards.append(entry)

        # ── NOISE ──
        if noise_day_db and noise_day_db >= 65:
            hazards.append(self._make_entry(
                "NOISE_DAY_HIGH", noise_day_db,
                f"Tiếng ồn ban ngày {noise_day_db:.0f}dB vượt ngưỡng 65dB.", "observed"
            ))
        if noise_night_db and noise_night_db >= 55:
            hazards.append(self._make_entry(
                "NOISE_NIGHT_HIGH", noise_night_db,
                f"Tiếng ồn ban đêm {noise_night_db:.0f}dB vượt ngưỡng ngủ 55dB.", "observed"
            ))

        # ── NEGATIVE PROXIMITY ──
        proximity_checks = [
            ("CEMETERY", cemetery_distance_m, 200),
            ("LANDFILL", landfill_distance_m, 500),
            ("POWER_LINE", power_line_distance_m, 100),
            ("INDUSTRIAL_ZONE", industrial_zone_m, 500),
            ("STAGNANT_WATER", stagnant_water_m, 100),
        ]
        for code, dist, threshold in proximity_checks:
            if dist is not None and dist < threshold:
                entry = self._proximity_entry(code, dist, threshold)
                hazards.append(entry)

        if road_collision:
            hazards.append(self._make_entry(
                "ROAD_COLLISION", 0, "Đường đâm thẳng vào nhà (lộ xung).", "observed"
            ))
        if t_junction:
            hazards.append(self._make_entry(
                "T_JUNCTION", 0, "Nhà nằm tại ngã ba T.", "observed"
            ))

        # ── POLLUTION ──
        if pollution_score and pollution_score > 0.5:
            impact = -0.04 * (pollution_score / 1.0)
            hazards.append(HazardEntry(
                hazard_code="AIR_POOR", hazard_label="Chất lượng không khí kém",
                category="POLLUTION", distance_m=0, severity="moderate",
                impact_pct=impact, confidence=0.65, source="estimated",
                explanation=f"Pollution score {pollution_score:.2f} > 0.5.",
            ))

        # ── POSITIVE PROXIMITY ──
        positive_checks = [
            ("PARK_NEAR", park_distance_m, 500),
            ("RIVER_VIEW", river_distance_m, 200),
            ("LAKE_NEAR", lake_distance_m, 300),
            ("SCHOOL_NEAR", school_distance_m, 1000),
            ("HOSPITAL_NEAR", hospital_distance_m, 1500),
            ("METRO_NEAR", metro_distance_m, 500),
            ("MARKET_NEAR", market_distance_m, 800),
        ]
        for code, dist, threshold in positive_checks:
            if dist is not None and dist < threshold:
                entry = self._proximity_entry(code, dist, threshold)
                positives.append(entry)

        # ── AGGREGATE ──
        result.hazards = hazards
        result.positive_factors = positives
        result.total_negative_pct = sum(h.impact_pct for h in hazards)
        result.total_positive_pct = sum(p.impact_pct for p in positives)
        result.net_impact_pct = result.total_negative_pct + result.total_positive_pct

        # Environment quality score (0-1)
        # Start at 0.7 (neutral), subtract for hazards, add for positives
        score = 0.70 + result.net_impact_pct * 2.0
        result.env_quality_score = max(0.0, min(1.0, score))

        # Risk grade
        if result.env_quality_score >= 0.85:
            result.risk_grade = "A"
        elif result.env_quality_score >= 0.70:
            result.risk_grade = "B"
        elif result.env_quality_score >= 0.50:
            result.risk_grade = "C"
        elif result.env_quality_score >= 0.30:
            result.risk_grade = "D"
        else:
            result.risk_grade = "F"

        # Warnings
        if len(hazards) >= 3:
            result.warnings.append(f"Phát hiện {len(hazards)} yếu tố rủi ro môi trường.")
        if result.net_impact_pct < -0.15:
            result.warnings.append("Tác động môi trường tiêu cực vượt 15% — cần khảo sát thực địa.")
        if any(h.hazard_code == "FLOOD_SEVERE" for h in hazards):
            result.warnings.append("Khu vực ngập nặng — ảnh hưởng nghiêm trọng đến thanh khoản.")

        return result

    def _assess_flood(self, flood_risk: str) -> Optional[HazardEntry]:
        """Assess flood risk."""
        flood_map = {
            "none": "FLOOD_NONE",
            "minor": "FLOOD_MINOR",
            "moderate": "FLOOD_MODERATE",
            "severe": "FLOOD_SEVERE",
        }
        code = flood_map.get(flood_risk)
        if not code:
            return None

        cat = self.catalog.get(code, {})
        severity = flood_risk
        return HazardEntry(
            hazard_code=code, hazard_label=cat.get("label", flood_risk),
            category="FLOOD", distance_m=0, severity=severity,
            impact_pct=cat.get("base_pct", 0), confidence=cat.get("conf", 0.70),
            source="reported",
            explanation=f"Mức ngập: {flood_risk}.",
        )

    def _proximity_entry(self, code: str, distance_m: float, threshold_m: float) -> HazardEntry:
        """Create proximity-based hazard entry with distance decay."""
        cat = self.catalog.get(code, {})
        base_pct = cat.get("base_pct", -0.03)

        # Distance decay: impact decreases linearly with distance
        if threshold_m > 0 and distance_m < threshold_m:
            decay = 1.0 - (distance_m / threshold_m)
            impact = base_pct * decay
        else:
            impact = base_pct * 0.5  # Minimal impact at threshold

        severity = "severe" if distance_m < threshold_m * 0.3 else (
            "moderate" if distance_m < threshold_m * 0.6 else "minor"
        )

        return HazardEntry(
            hazard_code=code, hazard_label=cat.get("label", code),
            category=cat.get("cat", "UNKNOWN"), distance_m=distance_m,
            severity=severity, impact_pct=impact,
            confidence=cat.get("conf", 0.60), source="estimated",
            explanation=f"{cat.get('label', code)} cách {distance_m:.0f}m (ngưỡng {threshold_m}m).",
            buffer_radius_m=cat.get("buffer_m", threshold_m),
        )

    def _make_entry(self, code: str, value: float, explanation: str, source: str) -> HazardEntry:
        """Create a hazard entry from catalog."""
        cat = self.catalog.get(code, {})
        return HazardEntry(
            hazard_code=code, hazard_label=cat.get("label", code),
            category=cat.get("cat", "UNKNOWN"), distance_m=value,
            severity="moderate", impact_pct=cat.get("base_pct", -0.03),
            confidence=cat.get("conf", 0.60), source=source,
            explanation=explanation,
        )
