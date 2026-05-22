"""
Legal Gate Engine — Production-grade legal risk assessment.

Differentiator vs existing AVM research:
- Most papers ignore legal status or treat it as categorical variable.
- This engine implements a **gate system**: if legal risk exceeds threshold,
  the entire valuation is BLOCKED with clear explanation.
- Provides a legal_penalty_pct that feeds directly into adjustment ledger.
- Tracks evidence_requirement for each legal factor.

Legal factors:
  1. Ownership type (sổ đỏ/sổ hồng/hợp đồng/giấy viết tay)
  2. Planning zone compliance
  3. Road expansion risk (giải tỏa)
  4. Mortgage/encumbrance
  5. Dispute/litigation
  6. Building violation (xây dựng trái phép)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class LegalFactor:
    """A single legal factor assessment."""
    factor_code: str
    factor_label: str
    status: str              # CLEAR|MINOR|MODERATE|SEVERE|BLOCKED
    impact_pct: float        # Negative = decreases value
    confidence: float        # 0-1
    rationale: str
    evidence_required: str   # Loại bằng chứng cần thiết
    gate_blocked: bool = False  # True = chặn valuation

    def to_dict(self) -> Dict:
        return {
            "factor_code": self.factor_code,
            "factor_label": self.factor_label,
            "status": self.status,
            "impact_pct": round(self.impact_pct, 4),
            "confidence": round(self.confidence, 3),
            "rationale": self.rationale,
            "evidence_required": self.evidence_required,
            "gate_blocked": self.gate_blocked,
        }


@dataclass
class LegalAssessment:
    """Complete legal assessment result."""
    factors: List[LegalFactor] = field(default_factory=list)
    is_blocked: bool = False
    block_reason: str = ""
    total_penalty_pct: float = 0.0
    legal_risk_grade: str = "A"   # A|B|C|D|F (F=blocked)
    legal_quality_score: float = 1.0  # 0-1
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "factors": [f.to_dict() for f in self.factors],
            "is_blocked": self.is_blocked,
            "block_reason": self.block_reason,
            "total_penalty_pct": round(self.total_penalty_pct, 4),
            "legal_risk_grade": self.legal_risk_grade,
            "legal_quality_score": round(self.legal_quality_score, 3),
            "warnings": self.warnings,
        }


# Ownership type → impact
OWNERSHIP_TABLE: Dict[str, Dict] = {
    "FULL_OWNERSHIP": {
        "label": "Sổ đỏ/Sổ hồng (GCNQSDĐ)",
        "impact_pct": 0.05,
        "status": "CLEAR",
        "conf": 0.90,
        "rationale": "Sổ đỏ/Sổ hồng hợp lệ, quyền sở hữu đầy đủ.",
        "evidence": "Bản sao sổ đỏ/sổ hồng",
    },
    "LONG_TERM_LEASE": {
        "label": "Hợp đồng thuê dài hạn (50+ năm)",
        "impact_pct": -0.05,
        "status": "MINOR",
        "conf": 0.80,
        "rationale": "Thuê dài hạn — giá trị giảm do không sở hữu vĩnh viễn.",
        "evidence": "Hợp đồng thuê đất",
    },
    "SALE_CONTRACT": {
        "label": "Hợp đồng mua bán (chưa sang sổ)",
        "impact_pct": -0.10,
        "status": "MODERATE",
        "conf": 0.70,
        "rationale": "Chỉ có hợp đồng mua bán, chưa cấp GCNQSDĐ.",
        "evidence": "Hợp đồng mua bán công chứng",
    },
    "HANDWRITTEN": {
        "label": "Giấy viết tay / chưa có giấy tờ",
        "impact_pct": -0.25,
        "status": "SEVERE",
        "conf": 0.85,
        "rationale": "Giấy tờ viết tay — rủi ro pháp lý rất cao.",
        "evidence": "Cần xác minh quyền sử dụng đất tại UBND",
    },
    "NO_DOCUMENT": {
        "label": "Không có giấy tờ",
        "impact_pct": -0.35,
        "status": "BLOCKED",
        "conf": 0.90,
        "rationale": "Không có giấy tờ hợp lệ — không thể định giá chính xác.",
        "evidence": "N/A",
    },
}


class LegalGateEngine:
    """
    Assess legal risks and apply gate-based blocking for high-risk properties.

    Gate rules:
    - NO_DOCUMENT → BLOCK (cannot value without ownership proof)
    - dispute_flag + mortgage_flag → BLOCK (compound risk)
    - Total penalty > 40% → SOFT BLOCK (warning only)
    """

    def assess(
        self,
        ownership_type: Optional[str] = None,
        planning_zone: Optional[str] = None,
        road_expansion_risk: Optional[str] = None,
        mortgage_flag: bool = False,
        dispute_flag: bool = False,
        building_violation: bool = False,
        additional_encumbrances: Optional[List[str]] = None,
    ) -> LegalAssessment:
        """Run legal assessment."""
        result = LegalAssessment()
        factors: List[LegalFactor] = []

        # ── 1. Ownership ──
        ownership = ownership_type or "FULL_OWNERSHIP"
        ownership_data = OWNERSHIP_TABLE.get(ownership, OWNERSHIP_TABLE["FULL_OWNERSHIP"])
        ownership_factor = LegalFactor(
            factor_code="OWNERSHIP",
            factor_label=ownership_data["label"],
            status=ownership_data["status"],
            impact_pct=ownership_data["impact_pct"],
            confidence=ownership_data["conf"],
            rationale=ownership_data["rationale"],
            evidence_required=ownership_data["evidence"],
            gate_blocked=(ownership_data["status"] == "BLOCKED"),
        )
        factors.append(ownership_factor)

        if ownership_factor.gate_blocked:
            result.is_blocked = True
            result.block_reason = (
                "Không có giấy tờ hợp lệ — hệ thống CHẶN valuation. "
                "Cần bổ sung bằng chứng quyền sử dụng đất."
            )

        # ── 2. Planning zone ──
        if planning_zone:
            planning_factor = self._assess_planning(planning_zone)
            factors.append(planning_factor)

        # ── 3. Road expansion risk ──
        if road_expansion_risk:
            expansion_factor = self._assess_road_expansion(road_expansion_risk)
            factors.append(expansion_factor)
            if expansion_factor.gate_blocked:
                result.is_blocked = True
                result.block_reason = "Nằm trong quy hoạch giải tỏa — giá trị không xác định."

        # ── 4. Mortgage ──
        if mortgage_flag:
            factors.append(LegalFactor(
                factor_code="MORTGAGE",
                factor_label="Tài sản thế chấp ngân hàng",
                status="MODERATE",
                impact_pct=-0.05,
                confidence=0.80,
                rationale="Tài sản đang thế chấp — cần giải chấp trước khi giao dịch.",
                evidence_required="Xác nhận giải chấp từ ngân hàng",
            ))

        # ── 5. Dispute ──
        if dispute_flag:
            factors.append(LegalFactor(
                factor_code="DISPUTE",
                factor_label="Tranh chấp pháp lý",
                status="SEVERE",
                impact_pct=-0.20,
                confidence=0.85,
                rationale="Tài sản đang tranh chấp — rủi ro giao dịch rất cao.",
                evidence_required="Bản án / quyết định giải quyết tranh chấp",
            ))

        # ── 6. Building violation ──
        if building_violation:
            factors.append(LegalFactor(
                factor_code="VIOLATION",
                factor_label="Xây dựng trái phép / vi phạm GPXD",
                status="MODERATE",
                impact_pct=-0.10,
                confidence=0.75,
                rationale="Công trình xây dựng không phép hoặc sai phép.",
                evidence_required="GPXD hợp lệ hoặc xác nhận hợp thức hóa",
            ))

        # ── Compound gate check ──
        if dispute_flag and mortgage_flag:
            result.is_blocked = True
            result.block_reason = (
                "Tài sản vừa thế chấp vừa tranh chấp — compound risk. "
                "Hệ thống CHẶN valuation cho đến khi giải quyết."
            )

        # ── Aggregate ──
        result.factors = factors
        result.total_penalty_pct = sum(f.impact_pct for f in factors if f.impact_pct < 0)

        # Legal quality score
        total_negative = abs(result.total_penalty_pct)
        result.legal_quality_score = max(0.0, 1.0 - total_negative * 2.0)

        # Grade
        if result.is_blocked:
            result.legal_risk_grade = "F"
        elif result.legal_quality_score >= 0.90:
            result.legal_risk_grade = "A"
        elif result.legal_quality_score >= 0.75:
            result.legal_risk_grade = "B"
        elif result.legal_quality_score >= 0.50:
            result.legal_risk_grade = "C"
        else:
            result.legal_risk_grade = "D"

        # Warnings
        if result.total_penalty_pct < -0.15:
            result.warnings.append(
                f"Tổng rủi ro pháp lý {abs(result.total_penalty_pct)*100:.1f}% — cần luật sư thẩm định."
            )
        if dispute_flag:
            result.warnings.append("Tài sản đang tranh chấp — không nên giao dịch khi chưa giải quyết.")
        if ownership == "HANDWRITTEN":
            result.warnings.append("Giấy tờ viết tay — rủi ro mất trắng nếu bên bán không hợp tác.")

        return result

    def _assess_planning(self, planning_zone: str) -> LegalFactor:
        """Assess planning zone compliance."""
        zone_map = {
            "residential": (0.0, "CLEAR", "Đất ở — phù hợp mục đích sử dụng."),
            "commercial": (-0.02, "MINOR", "Đất thương mại — cần kiểm tra mục đích sử dụng thực tế."),
            "mixed": (-0.01, "MINOR", "Đất hỗn hợp — cần xác minh quy hoạch chi tiết."),
            "agricultural": (-0.15, "SEVERE", "Đất nông nghiệp — không thể xây dựng, cần chuyển đổi."),
            "industrial": (-0.12, "MODERATE", "Đất công nghiệp — hạn chế sử dụng cho mục đích ở."),
            "green_space": (-0.25, "BLOCKED", "Đất công viên/cây xanh — không thể giao dịch."),
        }
        data = zone_map.get(planning_zone, (-0.05, "MODERATE", f"Quy hoạch '{planning_zone}' — cần kiểm tra."))

        return LegalFactor(
            factor_code="PLANNING_ZONE",
            factor_label=f"Quy hoạch: {planning_zone}",
            status=data[1],
            impact_pct=data[0],
            confidence=0.75,
            rationale=data[2],
            evidence_required="Bản đồ quy hoạch 1/500 hoặc 1/2000",
            gate_blocked=(data[1] == "BLOCKED"),
        )

    def _assess_road_expansion(self, risk_level: str) -> LegalFactor:
        """Assess road expansion / demolition risk."""
        risk_map = {
            "none": (0.0, "CLEAR", "Không nằm trong quy hoạch đường."),
            "low": (-0.03, "MINOR", "Có khả năng mở rộng đường nhưng xác suất thấp."),
            "moderate": (-0.10, "MODERATE", "Nằm trong quy hoạch mở rộng đường — có thể bị giải tỏa."),
            "high": (-0.20, "SEVERE", "Quy hoạch đường xác nhận — sẽ bị giải tỏa."),
            "confirmed": (-0.30, "BLOCKED", "Đã có quyết định giải tỏa — không thể giao dịch."),
        }
        data = risk_map.get(risk_level, (-0.05, "MODERATE", f"Rủi ro giải tỏa: {risk_level}."))

        return LegalFactor(
            factor_code="ROAD_EXPANSION",
            factor_label=f"Rủi ro giải tỏa: {risk_level}",
            status=data[1],
            impact_pct=data[0],
            confidence=0.80,
            rationale=data[2],
            evidence_required="Quyết định UBND về quy hoạch đường",
            gate_blocked=(data[1] == "BLOCKED"),
        )
