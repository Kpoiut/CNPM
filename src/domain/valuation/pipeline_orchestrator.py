"""
Pipeline Orchestrator — Chuỗi 9 Gate khóa chặt cho MỌI loại BĐS.

Bất kỳ dữ liệu BĐS nào đưa vào đều PHẢI đi qua tuần tự 9 gate:

  Gate 1: INTAKE     — Phân loại asset type, validate required fields
  Gate 2: NORMALIZE  — Chuẩn hóa tên tỉnh/quận, tọa độ, đơn vị
  Gate 3: CLASSIFY   — Xác định workflow (LAND/TOWNHOUSE/APARTMENT), required fields
  Gate 4: LEGAL      — Đánh giá pháp lý, BLOCK nếu rủi ro vượt ngưỡng
  Gate 5: GEOMETRY   — Phân tích hình học (LAND), enrichment scores
  Gate 6: ENVIRONMENT — Đánh giá môi trường, 23 loại rủi ro
  Gate 7: COMPARABLE — Tìm + scoring comparables, tính base price
  Gate 8: VALUATION  — Adjustment ledger + 4 mức giá + confidence
  Gate 9: FIT        — Persona/belief layer (tách biệt market value)

Mỗi gate có status: PASS | WARN | BLOCK | SKIP
Mỗi gate ghi log vào audit_trail
Nếu bất kỳ gate nào BLOCK → pipeline dừng, trả kết quả partial với lý do
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.domain.valuation.engine import (
    ValuationEngine, AssetInput, ValuationResult, AdjustmentResult,
)
from src.domain.valuation.geometry_calculator import GeometryCalculator
from src.domain.valuation.environment_risk import EnvironmentRiskEngine
from src.domain.valuation.legal_gate import LegalGateEngine
from src.config.province_config import normalize_province, SCOPE_DISTRICTS


# ─── Gate Status ─────────────────────────────────────────────────────

class GateStatus:
    PASS = "PASS"
    WARN = "WARN"
    BLOCK = "BLOCK"
    SKIP = "SKIP"


# ─── Asset Type Registry ────────────────────────────────────────────

ASSET_TYPES = {
    # LAND variants
    "LAND_URBAN", "LAND_SUBURBAN", "LAND_PROJECT",
    # Building variants
    "TOWNHOUSE", "VILLA", "SHOPHOUSE", "HOUSE",
    # Apartment variants
    "APARTMENT", "STUDIO", "PENTHOUSE", "DUPLEX",
}

# Required fields PER asset type — pipeline sẽ check completeness
REQUIRED_FIELDS: Dict[str, Dict[str, List[str]]] = {
    "LAND": {
        "critical": ["asset_type", "province_city", "district", "area_m2"],
        "important": ["frontage_m", "road_class", "ownership_type"],
        "optional": ["depth_min_m", "depth_max_m", "taper_type", "flood_risk",
                      "latitude", "longitude", "cemetery_distance_m"],
    },
    "TOWNHOUSE": {
        "critical": ["asset_type", "province_city", "district", "area_m2"],
        "important": ["floor_count", "bedrooms", "road_class", "ownership_type",
                       "construction_year"],
        "optional": ["frontage_m", "bathrooms", "structure_grade", "main_facing",
                      "flood_risk", "latitude", "longitude"],
    },
    "APARTMENT": {
        "critical": ["asset_type", "province_city", "district", "area_m2"],
        "important": ["apt_floor", "bedrooms", "ownership_type"],
        "optional": ["view_type", "block_name", "door_orientation",
                      "elevator_distance", "ventilation_score", "layout_score",
                      "latitude", "longitude"],
    },
}

# Map specific types → workflow category
def _workflow_category(asset_type: str) -> str:
    """Map any asset_type to canonical workflow category.

    Used for: completeness field requirements, comparable filtering.
    Note: VILLA and HOUSE share TOWNHOUSE workflow for completeness requirements
    (both have building structure), but have distinct value drivers in the engine.
    """
    from src.domain.property_types import to_canonical, PropertyType
    canonical = to_canonical(asset_type)
    if canonical == PropertyType.LAND:
        return "LAND"
    if canonical == PropertyType.APARTMENT:
        return "APARTMENT"
    return "TOWNHOUSE"  # TOWNHOUSE, VILLA, HOUSE


@dataclass
class GateResult:
    """Kết quả của một gate."""
    gate_id: int
    gate_name: str
    status: str          # PASS|WARN|BLOCK|SKIP
    duration_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    block_reason: str = ""

    def to_dict(self) -> Dict:
        public_details = {
            key: value
            for key, value in self.details.items()
            if not key.startswith("_")
        }
        return {
            "gate_id": self.gate_id,
            "gate_name": self.gate_name,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 1),
            "details": public_details,
            "warnings": self.warnings,
            "block_reason": self.block_reason,
        }


@dataclass
class CompletenessReport:
    """Báo cáo mức độ đầy đủ dữ liệu đầu vào."""
    critical_filled: int = 0
    critical_total: int = 0
    important_filled: int = 0
    important_total: int = 0
    optional_filled: int = 0
    optional_total: int = 0
    missing_critical: List[str] = field(default_factory=list)
    missing_important: List[str] = field(default_factory=list)
    missing_optional: List[str] = field(default_factory=list)
    completeness_pct: float = 0.0
    completeness_grade: str = "D"

    def to_dict(self) -> Dict:
        return {
            "critical": f"{self.critical_filled}/{self.critical_total}",
            "important": f"{self.important_filled}/{self.important_total}",
            "optional": f"{self.optional_filled}/{self.optional_total}",
            "missing_critical": self.missing_critical,
            "missing_important": self.missing_important,
            "missing_optional": self.missing_optional,
            "completeness_pct": round(self.completeness_pct, 1),
            "completeness_grade": self.completeness_grade,
        }


@dataclass
class PipelineResult:
    """Kết quả cuối cùng của toàn bộ pipeline."""
    pipeline_id: str
    pipeline_version: str = "v3.0_locked_chain"
    started_at: str = ""
    completed_at: str = ""
    total_duration_ms: float = 0.0

    # Gate audit trail
    gates: List[GateResult] = field(default_factory=list)
    final_status: str = "UNKNOWN"    # PASS|WARN|BLOCK
    blocked_at_gate: Optional[str] = None

    # Classified info
    workflow_category: str = ""      # LAND|TOWNHOUSE|APARTMENT
    asset_type_normalized: str = ""
    completeness: Optional[CompletenessReport] = None

    # Sub-engine results (always present, even if partial)
    legal_result: Optional[Dict] = None
    geometry_result: Optional[Dict] = None
    environment_result: Optional[Dict] = None

    # Valuation result (None if blocked before gate 8)
    valuation: Optional[ValuationResult] = None

    # Comparable records from Gate 7 (top-level convenience access for frontend)
    comparable_records: List[Dict] = field(default_factory=list)

    # Aggregated warnings
    all_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "pipeline_id": self.pipeline_id,
            "pipeline_version": self.pipeline_version,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration_ms": round(self.total_duration_ms, 1),
            "final_status": self.final_status,
            "blocked_at_gate": self.blocked_at_gate,
            "workflow_category": self.workflow_category,
            "asset_type_normalized": self.asset_type_normalized,
            "completeness": self.completeness.to_dict() if self.completeness else None,
            "gates": [g.to_dict() for g in self.gates],
            "legal_result": self.legal_result,
            "geometry_result": self.geometry_result,
            "environment_result": self.environment_result,
            "valuation": self.valuation.to_dict() if self.valuation else None,
            "comparable_records": self.comparable_records,
            "all_warnings": self.all_warnings,
        }


# ═════════════════════════════════════════════════════════════════════
# PIPELINE ORCHESTRATOR
# ═════════════════════════════════════════════════════════════════════

class PipelineOrchestrator:
    """
    Chuỗi 9 gate khóa chặt — MỌI BĐS phải đi qua tuần tự.

    Usage:
        orchestrator = PipelineOrchestrator()
        result = orchestrator.run(asset_input)
        # result.final_status = PASS|WARN|BLOCK
        # result.gates = [GateResult x 9]
        # result.valuation = ValuationResult (nếu không bị block)
    """

    def __init__(self, comparable_finder=None):
        self.geometry_engine = GeometryCalculator()
        self.legal_engine = LegalGateEngine()
        self.env_engine = EnvironmentRiskEngine()
        self.valuation_engine = ValuationEngine(comparable_finder=comparable_finder)

    def run(self, asset_input: AssetInput) -> PipelineResult:
        """Entry point duy nhất — chạy 9 gate tuần tự."""
        result = PipelineResult(
            pipeline_id=str(uuid4()),
            started_at=datetime.now().isoformat(),
        )
        start = time.perf_counter()
        blocked = False

        # Internal state for passing sub-engine results between gates
        self._legal_assessment = None
        self._env_assessment = None
        self._geometry_metrics = None

        # ── Gate 1: INTAKE ───────────────────────────────────────────
        g1 = self._gate_intake(asset_input)
        result.gates.append(g1)
        if g1.status == GateStatus.BLOCK:
            blocked = True
            result.blocked_at_gate = g1.gate_name

        # ── Gate 2: NORMALIZE ────────────────────────────────────────
        if not blocked:
            g2 = self._gate_normalize(asset_input)
            result.gates.append(g2)

        # ── Gate 3: CLASSIFY ─────────────────────────────────────────
        if not blocked:
            g3 = self._gate_classify(asset_input)
            result.gates.append(g3)
            result.workflow_category = g3.details.get("workflow", "")
            result.asset_type_normalized = g3.details.get("asset_type", "")
            result.completeness = g3.details.get("_completeness_obj")
            if g3.status == GateStatus.BLOCK:
                blocked = True
                result.blocked_at_gate = g3.gate_name

        # ── Gate 4: LEGAL ────────────────────────────────────────────
        if not blocked:
            g4 = self._gate_legal(asset_input)
            result.gates.append(g4)
            result.legal_result = g4.details.get("assessment")
            if g4.status == GateStatus.BLOCK:
                blocked = True
                result.blocked_at_gate = g4.gate_name

        # ── Gate 5: GEOMETRY ─────────────────────────────────────────
        if not blocked:
            g5 = self._gate_geometry(asset_input, result.workflow_category)
            result.gates.append(g5)
            result.geometry_result = g5.details.get("metrics")

        # ── Gate 6: ENVIRONMENT ──────────────────────────────────────
        if not blocked:
            g6 = self._gate_environment(asset_input)
            result.gates.append(g6)
            result.environment_result = g6.details.get("assessment")

        # ── Gate 7: COMPARABLE ───────────────────────────────────────
        if not blocked:
            g7 = self._gate_comparable(asset_input)
            result.gates.append(g7)
            result.comparable_records = g7.details.get("comparables", [])

        # ── Gate 8: VALUATION ────────────────────────────────────────
        if not blocked:
            g8 = self._gate_valuation(asset_input)
            result.gates.append(g8)
            result.valuation = g8.details.get("_valuation_obj")

        # ── Gate 9: FIT ──────────────────────────────────────────────
        if not blocked:
            g9 = self._gate_fit(asset_input, result.valuation)
            result.gates.append(g9)

        # ── Finalize ─────────────────────────────────────────────────
        result.completed_at = datetime.now().isoformat()
        result.total_duration_ms = (time.perf_counter() - start) * 1000

        # Aggregate warnings
        for g in result.gates:
            result.all_warnings.extend(g.warnings)

        # Final status
        if blocked:
            result.final_status = GateStatus.BLOCK
        elif any(g.status == GateStatus.WARN for g in result.gates):
            result.final_status = GateStatus.WARN
        else:
            result.final_status = GateStatus.PASS

        return result

    # ═════════════════════════════════════════════════════════════════
    # GATE IMPLEMENTATIONS
    # ═════════════════════════════════════════════════════════════════

    def _gate_intake(self, inp: AssetInput) -> GateResult:
        """Gate 1: Validate required identity fields + asset type."""
        t = time.perf_counter()
        warnings = []

        # Must have asset_type
        if not inp.asset_type:
            return GateResult(1, "INTAKE", GateStatus.BLOCK, _ms(t),
                              block_reason="Thieu asset_type — khong the phan loai.")

        # Normalize asset_type
        at = inp.asset_type.upper().replace(" ", "_")
        if at not in ASSET_TYPES:
            return GateResult(1, "INTAKE", GateStatus.BLOCK, _ms(t),
                              block_reason=f"asset_type '{at}' khong hop le. "
                              f"Phai la: {', '.join(sorted(ASSET_TYPES))}")
        inp.asset_type = at

        # Must have location
        if not inp.province_city or not inp.district:
            return GateResult(1, "INTAKE", GateStatus.BLOCK, _ms(t),
                              block_reason="Thieu province_city hoac district.")

        # Must have area
        if (inp.area_m2 or 0) <= 0 and (inp.built_area_m2 or 0) <= 0:
            return GateResult(1, "INTAKE", GateStatus.BLOCK, _ms(t),
                              block_reason="Thieu area_m2 — khong the dinh gia.")

        if not inp.latitude or not inp.longitude:
            warnings.append("Thieu toa do GPS — confidence se bi giam.")

        return GateResult(1, "INTAKE", GateStatus.WARN if warnings else GateStatus.PASS,
                          _ms(t), {"asset_type": at}, warnings)

    def _gate_normalize(self, inp: AssetInput) -> GateResult:
        """Gate 2: Chuẩn hóa province, district, units."""
        t = time.perf_counter()
        warnings = []

        # Province normalization
        norm = normalize_province(inp.province_city)
        if norm and norm != inp.province_city:
            warnings.append(f"Province chuan hoa: '{inp.province_city}' -> '{norm}'")
            inp.province_city = norm

        # Check scope
        allowed = []
        for districts in SCOPE_DISTRICTS.values():
            allowed.extend(districts)

        in_scope = inp.district in allowed
        if not in_scope:
            warnings.append(f"Quan '{inp.district}' ngoai scope 6 khu vuc — comparable co the it.")

        return GateResult(2, "NORMALIZE",
                          GateStatus.WARN if warnings else GateStatus.PASS,
                          _ms(t),
                          {"province": inp.province_city, "district": inp.district,
                           "in_scope": in_scope},
                          warnings)

    def _gate_classify(self, inp: AssetInput) -> GateResult:
        """Gate 3: Xác định workflow + check completeness."""
        t = time.perf_counter()
        warnings = []

        workflow = _workflow_category(inp.asset_type)
        req = REQUIRED_FIELDS.get(workflow, REQUIRED_FIELDS["TOWNHOUSE"])

        # Check completeness
        report = CompletenessReport()
        for level, fields in [("critical", req["critical"]),
                              ("important", req["important"]),
                              ("optional", req["optional"])]:
            total = len(fields)
            filled = 0
            missing = []
            for f in fields:
                val = getattr(inp, f, None)
                if val is not None and val != 0 and val != "" and val is not False:
                    filled += 1
                else:
                    missing.append(f)
            if level == "critical":
                report.critical_filled = filled
                report.critical_total = total
                report.missing_critical = missing
            elif level == "important":
                report.important_filled = filled
                report.important_total = total
                report.missing_important = missing
            else:
                report.optional_filled = filled
                report.optional_total = total
                report.missing_optional = missing

        all_total = report.critical_total + report.important_total + report.optional_total
        all_filled = report.critical_filled + report.important_filled + report.optional_filled
        report.completeness_pct = (all_filled / all_total * 100) if all_total > 0 else 0

        if report.completeness_pct >= 80:
            report.completeness_grade = "A"
        elif report.completeness_pct >= 60:
            report.completeness_grade = "B"
        elif report.completeness_pct >= 40:
            report.completeness_grade = "C"
        else:
            report.completeness_grade = "D"

        # Block if missing critical fields
        if report.missing_critical:
            return GateResult(3, "CLASSIFY", GateStatus.BLOCK, _ms(t),
                              block_reason=f"Thieu truong bat buoc: {', '.join(report.missing_critical)}")

        if report.missing_important:
            warnings.append(f"Thieu {len(report.missing_important)} truong quan trong: "
                            f"{', '.join(report.missing_important)}")

        return GateResult(3, "CLASSIFY",
                          GateStatus.WARN if warnings else GateStatus.PASS,
                          _ms(t),
                          {"workflow": workflow, "asset_type": inp.asset_type,
                           "completeness": report.to_dict(),
                           "_completeness_obj": report},
                          warnings)

    def _gate_legal(self, inp: AssetInput) -> GateResult:
        """Gate 4: Legal assessment with blocking."""
        t = time.perf_counter()

        assessment = self.legal_engine.assess(
            ownership_type=inp.ownership_type,
            planning_zone=inp.planning_zone,
            road_expansion_risk=inp.road_expansion_risk,
            mortgage_flag=inp.mortgage_flag,
            dispute_flag=inp.dispute_flag,
        )

        if assessment.is_blocked:
            return GateResult(4, "LEGAL", GateStatus.BLOCK, _ms(t),
                              {"assessment": assessment.to_dict()},
                              assessment.warnings,
                              block_reason=assessment.block_reason)

        self._legal_assessment = assessment  # Store for gate 8

        status = GateStatus.WARN if assessment.legal_risk_grade in ("C", "D") else GateStatus.PASS
        return GateResult(4, "LEGAL", status, _ms(t),
                          {"assessment": assessment.to_dict(),
                           "grade": assessment.legal_risk_grade},
                          assessment.warnings)

    def _gate_geometry(self, inp: AssetInput, workflow: str) -> GateResult:
        """Gate 5: Geometry analysis (LAND only, SKIP for others)."""
        t = time.perf_counter()

        if workflow != "LAND":
            return GateResult(5, "GEOMETRY", GateStatus.SKIP, _ms(t),
                              {"reason": f"Workflow {workflow} khong can geometry analysis."})

        metrics = self.geometry_engine.compute_from_simple(
            area_m2=inp.area_m2 or 100.0,
            frontage_m=inp.frontage_m or 5.0,
            depth_min_m=inp.depth_min_m,
            depth_max_m=inp.depth_max_m,
            corner_plot=inp.corner_plot,
            taper_type=inp.taper_type,
        )

        # Enrich input with computed scores
        if not inp.nö_hậu_score:
            inp.nö_hậu_score = metrics.nö_hậu_score
        if not inp.thóp_hậu_score:
            inp.thóp_hậu_score = metrics.thóp_hậu_score
        if not inp.irregularity_score:
            inp.irregularity_score = metrics.irregularity_score

        self._geometry_metrics = metrics  # Store for gate 8

        warnings = []
        if metrics.has_neck:
            warnings.append(f"Phat hien co chai (neck): {metrics.neck_width_m:.1f}m")
        if metrics.thóp_hậu_score > 0.5:
            warnings.append(f"Thop hau nang: score={metrics.thóp_hậu_score:.2f}")
        if metrics.squareness_score < 0.5:
            warnings.append(f"Hinh dang bat thuong: squareness={metrics.squareness_score:.2f}")

        return GateResult(5, "GEOMETRY",
                          GateStatus.WARN if warnings else GateStatus.PASS,
                          _ms(t),
                          {"metrics": metrics.to_dict(), "taper_type": metrics.taper_type},
                          warnings)

    def _gate_environment(self, inp: AssetInput) -> GateResult:
        """Gate 6: Environment risk assessment."""
        t = time.perf_counter()

        assessment = self.env_engine.assess(
            flood_risk=inp.flood_risk,
            noise_day_db=inp.noise_day_db,
            noise_night_db=inp.noise_night_db,
            pollution_score=inp.pollution_score,
            cemetery_distance_m=inp.cemetery_distance_m,
            river_distance_m=inp.river_distance_m,
            park_distance_m=inp.park_distance_m,
        )

        status = GateStatus.PASS
        if assessment.risk_grade in ("D", "F"):
            status = GateStatus.WARN

        self._env_assessment = assessment  # Store for gate 8

        return GateResult(6, "ENVIRONMENT", status, _ms(t),
                          {"assessment": assessment.to_dict(),
                           "grade": assessment.risk_grade,
                           "net_impact_pct": assessment.net_impact_pct},
                          assessment.warnings)

    def _gate_comparable(self, inp: AssetInput) -> GateResult:
        """Gate 7: Find and validate comparables."""
        t = time.perf_counter()
        warnings = []

        comps = self.valuation_engine.comparable_finder(inp)
        count = len(comps)

        if count == 0:
            warnings.append("Khong tim thay comparable — se dung location estimate.")
        elif count < 5:
            warnings.append(f"Chi co {count} comparable — do tin cay bi giam.")

        # Tier breakdown
        tiers = {}
        for c in comps:
            tiers[c.evidence_tier] = tiers.get(c.evidence_tier, 0) + 1

        anchor_count = tiers.get("E4", 0) + tiers.get("E5", 0)
        if count > 0 and anchor_count == 0:
            warnings.append("Khong co comparable E4/E5 — can bo sung du lieu chat luong cao.")

        return GateResult(7, "COMPARABLE",
                          GateStatus.WARN if warnings else GateStatus.PASS,
                          _ms(t),
                          {
                              "count": count,
                              "tier_breakdown": tiers,
                              "anchor_count": anchor_count,
                              # Actual records — returned so frontend can display them
                              "comparables": [
                                  {
                                      "legacy_id": c.legacy_id,
                                      "district": c.district,
                                      "ward": getattr(c, 'ward', None),
                                      "area_m2": c.area_m2,
                                      "price_per_m2": c.price_per_m2,
                                      "price": c.price,
                                      "evidence_tier": c.evidence_tier,
                                      "legal_status": getattr(c, 'legal_status', None),
                                      "latitude": getattr(c, 'latitude', None),
                                      "longitude": getattr(c, 'longitude', None),
                                      "listing_date": getattr(c, 'listing_date', None),
                                      "verification_status": getattr(c, 'verification_status', None),
                                      "similarity_score": getattr(c, 'similarity_score', None),
                                      "match_reasons": getattr(c, 'match_reasons', []),
                                      "adjustment_rationale": getattr(c, 'adjustment_rationale', None),
                                      "price_adjustment_vnd": getattr(c, 'price_adjustment_vnd', 0),
                                  }
                                  for c in comps
                              ],
                          },
                          warnings)

    def _gate_valuation(self, inp: AssetInput) -> GateResult:
        """Gate 8: Run valuation engine + inject legal/env adjustments."""
        t = time.perf_counter()

        val_result = self.valuation_engine.run(inp)

        # Inject legal adjustments from gate 4
        if self._legal_assessment:
            base = val_result.base_price_vnd
            for lf in self._legal_assessment.factors:
                if lf.impact_pct != 0:
                    val_result.market_adjustments.append(AdjustmentResult(
                        factor_code=f"LEGAL_{lf.factor_code}",
                        layer="MARKET", factor_group="LEGAL",
                        direction="POSITIVE" if lf.impact_pct > 0 else "NEGATIVE",
                        delta_pct=lf.impact_pct,
                        delta_vnd=int(base * lf.impact_pct),
                        confidence=lf.confidence,
                        rationale=lf.rationale,
                        source_type="legal_gate",
                    ))

        # Inject environment adjustments from gate 6
        if self._env_assessment:
            base = val_result.base_price_vnd
            for hazard in self._env_assessment.hazards + self._env_assessment.positive_factors:
                if hazard.impact_pct != 0:
                    val_result.market_adjustments.append(AdjustmentResult(
                        factor_code=f"ENV_{hazard.hazard_code}",
                        layer="MARKET", factor_group="ENVIRONMENT",
                        direction="POSITIVE" if hazard.impact_pct > 0 else "NEGATIVE",
                        delta_pct=hazard.impact_pct,
                        delta_vnd=int(base * hazard.impact_pct),
                        confidence=hazard.confidence,
                        rationale=hazard.explanation,
                        source_type="environment_risk",
                    ))

        # Recalculate FMV with ALL adjustments
        total_adj = sum(a.delta_vnd for a in val_result.market_adjustments)
        val_result.fair_market_value_vnd = max(
            50_000_000,
            min(val_result.base_price_vnd + total_adj, 100_000_000_000)
        )

        # Legal penalty to confidence
        if self._legal_assessment and self._legal_assessment.is_blocked:
            val_result.overall_confidence = max(0.10, val_result.overall_confidence * 0.3)
            val_result.confidence_grade = "D"
        elif self._legal_assessment and self._legal_assessment.legal_risk_grade in ("C", "D"):
            val_result.overall_confidence = max(0.20, val_result.overall_confidence * 0.7)

        # Store sub-engine results in valuation
        val_result.legal_assessment = (
            self._legal_assessment.to_dict() if self._legal_assessment else None
        )
        val_result.environment_assessment = (
            self._env_assessment.to_dict() if self._env_assessment else None
        )
        val_result.geometry_metrics = (
            self._geometry_metrics.to_dict() if self._geometry_metrics else None
        )

        # Merge sub-engine warnings
        if self._legal_assessment:
            val_result.warnings.extend(self._legal_assessment.warnings)
        if self._env_assessment:
            val_result.warnings.extend(self._env_assessment.warnings)

        warnings = list(val_result.warnings)
        status = GateStatus.PASS
        if val_result.confidence_grade == "D":
            status = GateStatus.WARN

        return GateResult(8, "VALUATION", status, _ms(t),
                          {"fair_market_value": val_result.fair_market_value_vnd,
                           "confidence_grade": val_result.confidence_grade,
                           "adjustment_count": len(val_result.market_adjustments),
                           "engine_version": val_result.engine_version,
                           "_valuation_obj": val_result},
                          warnings)

    def _gate_fit(self, inp: AssetInput, valuation: Optional[ValuationResult]) -> GateResult:
        """Gate 9: Fit/belief layer assessment."""
        t = time.perf_counter()
        warnings = []

        fit_factors = []
        if inp.death_history_flag:
            fit_factors.append("death_history")
            warnings.append("Nha co lich su chet bat thuong.")
        if inp.stigma_known:
            fit_factors.append("stigma")
            warnings.append("Tai san co stigma (tam linh/xa hoi).")
        if inp.worship_site_distance_m and inp.worship_site_distance_m < 50:
            fit_factors.append("worship_near")
        if inp.main_facing:
            fit_factors.append(f"facing_{inp.main_facing}")

        fit_count = len(valuation.fit_adjustments) if valuation else 0

        return GateResult(9, "FIT",
                          GateStatus.WARN if warnings else GateStatus.PASS,
                          _ms(t),
                          {"fit_factors_detected": fit_factors,
                           "fit_adjustment_count": fit_count,
                           "has_persona": False},
                          warnings)


def _ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000
