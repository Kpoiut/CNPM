"""
Comparable Engine — Tìm và xếp hạng comparable properties.

5 lớp xử lý:
1. Candidate Retrieval     → Tìm tất cả candidates trong cùng khu vực
2. Similarity Scoring     → Tính multi-dimensional similarity
3. Adjustment Normalization → Điều chỉnh comparable về property mục tiêu
4. Evidence Ranking     → Xếp hạng theo evidence tier
5. Explanation Rendering → Sinh human-readable explanation
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from src.domain.evidence_tier import anchor_share, evidence_score, evidence_sort_key


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ComparableCandidate:
    """Một candidate comparable sau khi được xử lý."""
    # Required fields first
    legacy_id: int
    asset_type: str
    province_city: str
    district: str
    area_m2: float
    price: float
    price_per_m2: float
    evidence_tier: str  # E1-E5

    # Optional fields with defaults
    ward: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    floor: Optional[int] = None
    bedrooms: Optional[int] = None
    view_type: Optional[str] = None
    legal_status: Optional[str] = None
    age_years: Optional[int] = None
    listing_date: Optional[str] = None
    verification_status: str = "unverified"
    geo_proximity_score: float = 0.0
    geometry_score: float = 0.0
    access_score: float = 0.0
    legal_score: float = 0.0
    evidence_score: float = 0.0
    recency_score: float = 0.0
    overall_similarity: float = 0.0
    price_adjustment_vnd: int = 0
    adjustment_rationale: str = ""
    source_domain: Optional[str] = None


@dataclass
class ComparableQuery:
    """Query parameters cho comparable search."""
    asset_type: str
    province_city: str
    district: str
    area_m2: float
    ward: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    target_price: Optional[float] = None

    # Asset-specific filters
    floor: Optional[int] = None
    view_type: Optional[str] = None
    bedrooms: Optional[int] = None
    legal_status: Optional[str] = None

    # Limits
    max_distance_km: float = 5.0  # Bán kính tìm kiếm
    max_count: int = 20
    min_similarity: float = 0.30  # Ngưỡng similarity tối thiểu

    # Weights (cho similarity scoring)
    weights: Dict[str, float] = field(default_factory=lambda: {
        "geo": 0.20,
        "geometry": 0.15,
        "access": 0.15,
        "legal": 0.15,
        "evidence": 0.20,
        "recency": 0.15,
    })


# =============================================================================
# COMPARABLE ENGINE
# =============================================================================

class ComparableEngine:
    """
    Comparable Engine — 5-layer processing pipeline.

    Important: Similarity score ≠ Price adjustment.
    These are two separate concepts:
    - Similarity: how similar is this comp to the target (0-1)
    - Price adjustment: how much should we adjust the comp price (VND)
    """

    def __init__(self, db_loader: Optional[Callable] = None):
        """
        Args:
            db_loader: Hàm load records từ DB.
                      Signature: (ComparableQuery) -> List[ComparableCandidate]
        """
        self.db_loader = db_loader

    def find_comparables(self, query: ComparableQuery) -> List[ComparableCandidate]:
        """
        Main pipeline: Tìm và rank comparables.

        Returns:
            List[ComparableCandidate] đã được xử lý qua 5 lớp
        """
        # Layer 1: Candidate Retrieval
        candidates = self._retrieve_candidates(query)

        if not candidates:
            return []

        # Layer 2: Similarity Scoring
        candidates = self._score_similarity(query, candidates)

        # Layer 3: Adjustment Normalization
        candidates = self._normalize_adjustments(query, candidates)

        # Layer 4: Evidence Ranking
        candidates = self._rank_by_evidence(candidates)

        # Layer 5: Filter và sort
        result = self._finalize(query, candidates)

        return result

    def _retrieve_candidates(self, query: ComparableQuery) -> List[ComparableCandidate]:
        """Layer 1: Candidate Retrieval."""
        if self.db_loader:
            return self.db_loader(query)

        # Default: return empty
        return []

    def _score_similarity(
        self,
        query: ComparableQuery,
        candidates: List[ComparableCandidate],
    ) -> List[ComparableCandidate]:
        """Layer 2: Multi-dimensional Similarity Scoring."""
        w = query.weights

        for comp in candidates:
            # 2a. Geo proximity (Haversine distance)
            comp.geo_proximity_score = self._geo_proximity(query, comp)

            # 2b. Geometry similarity (area gap)
            comp.geometry_score = self._geometry_similarity(query, comp)

            # 2c. Access similarity
            comp.access_score = 0.5  # Default

            # 2d. Legal comparability
            comp.legal_score = self._legal_comparability(query, comp)

            # 2e. Evidence quality (sẽ được dùng trong ranking)
            comp.evidence_score = self._evidence_score(comp.evidence_tier)

            # 2f. Recency
            comp.recency_score = self._recency_score(comp.listing_date)

            # 2g. Overall similarity
            comp.overall_similarity = (
                w["geo"] * comp.geo_proximity_score +
                w["geometry"] * comp.geometry_score +
                w["access"] * comp.access_score +
                w["legal"] * comp.legal_score +
                w["evidence"] * comp.evidence_score +
                w["recency"] * comp.recency_score
            )

        return candidates

    def _geo_proximity(
        self,
        query: ComparableQuery,
        comp: ComparableCandidate,
    ) -> float:
        """Tính geo proximity score (0-1)."""
        if not query.latitude or not query.longitude:
            return 0.5  # Unknown location

        if not comp.latitude or not comp.longitude:
            return 0.3  # Can't compute

        distance_km = self._haversine(
            query.latitude, query.longitude,
            comp.latitude, comp.longitude,
        )

        if distance_km <= 0.5:
            return 1.0
        elif distance_km <= 1.0:
            return 0.90
        elif distance_km <= 2.0:
            return 0.75
        elif distance_km <= 5.0:
            return 0.50
        else:
            return 0.20

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Tính khoảng cách Haversine (km)."""
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    def _geometry_similarity(
        self,
        query: ComparableQuery,
        comp: ComparableCandidate,
    ) -> float:
        """Tính geometry similarity (0-1) dựa trên area gap."""
        if comp.area_m2 <= 0 or query.area_m2 <= 0:
            return 0.35

        gap = abs(comp.area_m2 - query.area_m2) / query.area_m2

        if gap <= 0.10:
            return 1.0
        elif gap <= 0.20:
            return 0.85
        elif gap <= 0.30:
            return 0.70
        elif gap <= 0.50:
            return 0.50
        else:
            return 0.25

    def _legal_comparability(
        self,
        query: ComparableQuery,
        comp: ComparableCandidate,
    ) -> float:
        """Tính legal comparability (0-1)."""
        if not comp.legal_status:
            return 0.40

        legal_map = {
            "FULL_OWNERSHIP": 1.0,
            "LURC": 0.80,
            "PENDING": 0.30,
            "DISPUTE": 0.10,
        }
        return legal_map.get(comp.legal_status, 0.40)

    def _evidence_score(self, tier: str) -> float:
        """Map E1-E5 tier sang score (0-1), E5 mạnh nhất."""
        return evidence_score(tier)

    def _recency_score(self, listing_date_str: Optional[str]) -> float:
        """Tính recency score (0-1) dựa trên ngày listing."""
        if not listing_date_str:
            return 0.40  # Unknown

        try:
            if isinstance(listing_date_str, str):
                listing_date = datetime.fromisoformat(listing_date_str.replace("Z", ""))
            else:
                return 0.40
        except (ValueError, AttributeError):
            return 0.40

        days_old = (datetime.now() - listing_date).days

        if days_old <= 30:
            return 1.0
        elif days_old <= 90:
            return 0.90
        elif days_old <= 180:
            return 0.70
        elif days_old <= 365:
            return 0.50
        else:
            return 0.30

    def _normalize_adjustments(
        self,
        query: ComparableQuery,
        candidates: List[ComparableCandidate],
    ) -> List[ComparableCandidate]:
        """
        Layer 3: Adjustment Normalization.

        Quan trọng: Similarity score không phải là adjustment.
        Similarity = "tương tự như thế nào"
        Adjustment = "điều chỉnh giá bao nhiêu"
        Đây là hai lớp RIÊNG BIỆT.
        """
        for comp in candidates:
            adjustments: List[str] = []
            total_pct = 0.0

            # Area adjustment
            area_gap = (comp.area_m2 - query.area_m2) / query.area_m2 if query.area_m2 > 0 else 0
            if abs(area_gap) > 0.05:
                # Mỗi 10% area gap = 3% price adjustment
                area_adj_pct = area_gap * 0.30
                total_pct += area_adj_pct
                adjustments.append(f"Diện tích chênh {area_gap*100:.0f}%")

            # Legal adjustment
            if comp.legal_status != query.legal_status:
                if comp.legal_status == "DISPUTE":
                    total_pct -= 0.10
                    adjustments.append("Pháp lý tranh chấp")
                elif comp.legal_status == "PENDING" and query.legal_status == "FULL_OWNERSHIP":
                    total_pct -= 0.05
                    adjustments.append("Pháp lý thấp hơn")

            # Floor adjustment (apartment)
            if query.floor and comp.floor:
                floor_gap = comp.floor - query.floor
                if abs(floor_gap) >= 5:
                    floor_adj = floor_gap * 0.002  # Mỗi tầng = 0.2%
                    total_pct += floor_adj
                    adjustments.append(f"Tầng chênh {floor_gap:+d}")

            comp.price_adjustment_vnd = int(comp.price * total_pct)
            comp.adjustment_rationale = "; ".join(adjustments) if adjustments else "Tương đương"

        return candidates

    def _rank_by_evidence(
        self,
        candidates: List[ComparableCandidate],
    ) -> List[ComparableCandidate]:
        """
        Layer 4: Evidence Ranking.

        Candidates được re-rank theo evidence tier,
        nhưng similarity vẫn được giữ nguyên.
        """
        return sorted(
            candidates,
            key=lambda c: (
                evidence_sort_key(c.evidence_tier),
                -c.overall_similarity,             # Then by similarity
            )
        )

    def _finalize(
        self,
        query: ComparableQuery,
        candidates: List[ComparableCandidate],
    ) -> List[ComparableCandidate]:
        """Layer 5: Filter và return."""
        # Filter by minimum similarity
        filtered = [c for c in candidates if c.overall_similarity >= query.min_similarity]

        # Preserve Layer 4 ordering: evidence tier first, similarity second.
        return filtered[:query.max_count]

    def generate_explanation(
        self,
        target: ComparableQuery,
        comps: List[ComparableCandidate],
    ) -> Dict[str, Any]:
        """Sinh human-readable explanation cho comparables."""
        if not comps:
            return {
                "summary": "Không tìm thấy comparable phù hợp trong khu vực.",
                "candidates": [],
                "quality": "low",
            }

        tier_counts = {"E1": 0, "E2": 0, "E3": 0, "E4": 0, "E5": 0}
        for c in comps:
            tier_counts[c.evidence_tier] = tier_counts.get(c.evidence_tier, 0) + 1

        avg_similarity = sum(c.overall_similarity for c in comps) / len(comps)

        strong_anchor_share = anchor_share(tier_counts, len(comps))
        if strong_anchor_share >= 0.4:
            quality = "high"
        elif strong_anchor_share + (tier_counts["E3"] / len(comps)) >= 0.5:
            quality = "medium"
        else:
            quality = "low"

        return {
            "summary": (
                f"Tìm thấy {len(comps)} comparable, "
                f"similarity trung bình {avg_similarity:.0%}, "
                f"quality: {quality}."
            ),
            "candidate_count": len(comps),
            "avg_similarity": round(avg_similarity, 3),
            "quality": quality,
            "tier_distribution": tier_counts,
            "top_comparables": [
                {
                    "legacy_id": c.legacy_id,
                    "district": c.district,
                    "area_m2": c.area_m2,
                    "price_per_m2": c.price_per_m2,
                    "evidence_tier": c.evidence_tier,
                    "similarity": round(c.overall_similarity, 3),
                    "adjustment_vnd": c.price_adjustment_vnd,
                    "adjustment_rationale": c.adjustment_rationale,
                }
                for c in comps[:5]
            ],
        }
