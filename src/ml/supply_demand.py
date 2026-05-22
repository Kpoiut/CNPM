"""
Supply-Demand Matching Engine cho Market Acceptable Price.

Ý tưởng lõi:
  - Bên bán (Supply): giá rao bán = ask price = giá kỳ vọng
  - Bên mua (Demand): ngân sách, yêu cầu tìm mua = bid signal
  - Market Acceptable Price: giá mà cả bên bán lẫn bên mua đều chấp nhận được

Phương pháp:
  1. Nhóm listings và buyer requests theo (district, property_type)
  2. Tính phân phối cung (listing_prices) và cầu (buyer_budgets) cho mỗi nhóm
  3. Tìm vùng giao nhau (overlap) của 2 phân phối
  4. Market Acceptable Price = median/mode của vùng overlap
  5. Áp dụng penalties: stale listings, price revisions, demand coverage

Công thức:
  market_acceptable_price = overlap_price × (1 + demand_weight) × (1 - stale_penalty)

Trong đó:
  - overlap_price = median(prices_in_overlap_zone)
  - demand_weight = log(demand_count / supply_count) × 0.1  (capped at ±0.15)
  - stale_penalty = min(0.15, days_on_market × 0.001)
"""

import math
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ListingRecord:
    """Một tin rao bán (bên cung)."""
    id: int
    property_type: str
    district: str
    ward: Optional[str]
    area_m2: float
    price: float  # VND
    bedrooms: int
    legal_status: Optional[str]
    days_on_market: int = 0
    price_revision_count: int = 0
    views_count: int = 0
    saves_count: int = 0
    contacts_count: int = 0


@dataclass
class BuyerRequest:
    """Một yêu cầu tìm mua (bên cầu)."""
    id: int
    property_type: Optional[str]
    district: str
    ward: Optional[str]
    min_area: Optional[float]
    max_area: Optional[float]
    min_budget: float  # VND
    max_budget: float  # VND
    bedrooms: Optional[int]
    legal_requirement: Optional[str]
    urgency: str = "normal"


@dataclass
class MatchResult:
    """Kết quả matching giữa 1 listing và 1 buyer request."""
    listing_id: int
    request_id: int
    location_match_score: float  # 0-1
    area_match_score: float  # 0-1
    budget_gap: float  # listing_price - max_budget
    feature_match_score: float  # 0-1
    overlap_score: float  # combined 0-1
    is_potential_match: bool


@dataclass
class MarketGroup:
    """Kết quả phân tích 1 nhóm thị trường (district × property_type)."""
    district: str
    property_type: str
    supply_count: int
    demand_count: int
    supply_prices: List[float]
    demand_budgets_low: List[float]
    demand_budgets_high: List[float]
    overlap_low: float
    overlap_high: float
    market_acceptable_price: float
    price_range_low: float
    price_range_high: float
    demand_supply_ratio: float
    overpricing_index: float


class SupplyDemandEngine:
    """
    Engine tính Market Acceptable Price từ dữ liệu cung-cầu.
    """

    def __init__(self):
        self.match_threshold = 0.5  # Minimum overlap_score để coi là potential match
        self.stale_penalty_rate = 0.001  # Per day penalty
        self.max_stale_penalty = 0.15
        self.demand_weight_scale = 0.1
        self.max_demand_weight = 0.15

    # ==========================================
    # MATCHING FUNCTIONS
    # ==========================================

    def compute_location_match(self, listing: ListingRecord, buyer: BuyerRequest) -> float:
        """Tính điểm khớp vị trí (0-1)."""
        if listing.district != buyer.district:
            return 0.0

        score = 0.6  # Same district

        # Ward match bonus
        if listing.ward and buyer.ward:
            if listing.ward == buyer.ward:
                score += 0.4
            else:
                score += 0.1  # Same district, different ward
        elif not buyer.ward:
            score += 0.2  # Buyer doesn't care about ward

        return min(1.0, score)

    def compute_area_match(self, listing: ListingRecord, buyer: BuyerRequest) -> float:
        """Tính điểm khớp diện tích (0-1)."""
        if buyer.min_area is None and buyer.max_area is None:
            return 0.8  # No area preference = moderate match

        area = listing.area_m2
        if area <= 0:
            return 0.3  # Unknown area

        min_a = buyer.min_area or 0
        max_a = buyer.max_area or float('inf')

        if min_a <= area <= max_a:
            return 1.0  # Perfect match

        # Partial match: within 20% tolerance
        tolerance = max(min_a, max_a if max_a < float('inf') else min_a) * 0.2
        if area < min_a:
            gap = min_a - area
            return max(0, 1.0 - gap / (tolerance + 1))
        else:
            gap = area - max_a
            return max(0, 1.0 - gap / (tolerance + 1))

    def compute_budget_match(self, listing: ListingRecord, buyer: BuyerRequest) -> Tuple[float, float]:
        """
        Tính budget gap và budget match score.
        Returns: (budget_gap, budget_match_score)
        """
        price = listing.price
        budget_gap = price - buyer.max_budget

        if price <= buyer.max_budget:
            # Affordable
            if price >= buyer.min_budget:
                return budget_gap, 1.0  # Within budget range
            else:
                # Below min budget (might be suspicious)
                return budget_gap, 0.7
        else:
            # Over budget
            overshoot = budget_gap / buyer.max_budget if buyer.max_budget > 0 else 1.0
            if overshoot <= 0.1:
                return budget_gap, 0.7  # 10% over budget
            elif overshoot <= 0.2:
                return budget_gap, 0.4  # 20% over
            else:
                return budget_gap, max(0, 0.3 - overshoot * 0.3)

    def compute_feature_match(self, listing: ListingRecord, buyer: BuyerRequest) -> float:
        """Tính điểm khớp tính năng (bedrooms, legal, etc.)."""
        scores = []

        # Property type
        if buyer.property_type:
            if listing.property_type == buyer.property_type:
                scores.append(1.0)
            elif listing.property_type in ("house", "townhouse") and buyer.property_type in ("house", "townhouse"):
                scores.append(0.7)  # Similar types
            else:
                scores.append(0.2)
        else:
            scores.append(0.8)

        # Bedrooms
        if buyer.bedrooms and buyer.bedrooms > 0:
            if listing.bedrooms == buyer.bedrooms:
                scores.append(1.0)
            elif abs(listing.bedrooms - buyer.bedrooms) == 1:
                scores.append(0.7)
            else:
                scores.append(0.3)
        else:
            scores.append(0.8)

        # Legal status
        if buyer.legal_requirement and buyer.legal_requirement != "any":
            if listing.legal_status == buyer.legal_requirement:
                scores.append(1.0)
            elif listing.legal_status and listing.legal_status != "pending":
                scores.append(0.5)
            else:
                scores.append(0.3)
        else:
            scores.append(0.8)

        return sum(scores) / len(scores) if scores else 0.5

    def match_pair(self, listing: ListingRecord, buyer: BuyerRequest) -> MatchResult:
        """Match 1 listing với 1 buyer request."""
        loc_score = self.compute_location_match(listing, buyer)
        area_score = self.compute_area_match(listing, buyer)
        budget_gap, budget_score = self.compute_budget_match(listing, buyer)
        feature_score = self.compute_feature_match(listing, buyer)

        # Weighted overlap score
        overlap = (
            loc_score * 0.30 +
            area_score * 0.15 +
            budget_score * 0.35 +
            feature_score * 0.20
        )

        return MatchResult(
            listing_id=listing.id,
            request_id=buyer.id,
            location_match_score=round(loc_score, 3),
            area_match_score=round(area_score, 3),
            budget_gap=round(budget_gap, 0),
            feature_match_score=round(feature_score, 3),
            overlap_score=round(overlap, 3),
            is_potential_match=overlap >= self.match_threshold,
        )

    def match_all(self, listings: List[ListingRecord], buyers: List[BuyerRequest]) -> List[MatchResult]:
        """Match tất cả listings với tất cả buyer requests."""
        results = []
        for listing in listings:
            for buyer in buyers:
                result = self.match_pair(listing, buyer)
                if result.is_potential_match:
                    results.append(result)
        return results

    # ==========================================
    # MARKET ANALYSIS
    # ==========================================

    def group_by_market(
        self,
        listings: List[ListingRecord],
        buyers: List[BuyerRequest]
    ) -> Dict[str, MarketGroup]:
        """Nhóm listings và buyers theo (district, property_type)."""
        groups = {}

        for listing in listings:
            key = f"{listing.district}|{listing.property_type}"
            if key not in groups:
                groups[key] = {
                    "district": listing.district,
                    "property_type": listing.property_type,
                    "listings": [],
                    "buyers": [],
                }
            groups[key]["listings"].append(listing)

        for buyer in buyers:
            # Try exact match first
            for ptype in ([buyer.property_type] if buyer.property_type else ["house", "apartment", "land", "townhouse", "villa"]):
                key = f"{buyer.district}|{ptype}"
                if key in groups:
                    groups[key]["buyers"].append(buyer)

        results = {}
        for key, grp in groups.items():
            supply_prices = sorted([l.price for l in grp["listings"] if l.price > 0])
            demand_low = sorted([b.min_budget for b in grp["buyers"] if b.min_budget > 0])
            demand_high = sorted([b.max_budget for b in grp["buyers"] if b.max_budget > 0])

            if not supply_prices:
                continue

            # Compute overlap zone
            if demand_high:
                overlap_low = max(
                    np.percentile(supply_prices, 10) if len(supply_prices) >= 5 else min(supply_prices),
                    np.percentile(demand_low, 10) if len(demand_low) >= 5 else (min(demand_low) if demand_low else 0)
                )
                overlap_high = min(
                    np.percentile(supply_prices, 90) if len(supply_prices) >= 5 else max(supply_prices),
                    np.percentile(demand_high, 90) if len(demand_high) >= 5 else (max(demand_high) if demand_high else float('inf'))
                )
            else:
                # No demand data → use supply distribution only
                overlap_low = np.percentile(supply_prices, 25) if len(supply_prices) >= 4 else min(supply_prices)
                overlap_high = np.percentile(supply_prices, 75) if len(supply_prices) >= 4 else max(supply_prices)

            # Market acceptable price = median of overlap zone
            overlap_prices = [p for p in supply_prices if overlap_low <= p <= overlap_high]
            if overlap_prices:
                market_price = float(np.median(overlap_prices))
            else:
                market_price = float(np.median(supply_prices))

            supply_count = len(grp["listings"])
            demand_count = len(grp["buyers"])
            ds_ratio = demand_count / supply_count if supply_count > 0 else 0

            # Overpricing index
            median_supply = float(np.median(supply_prices))
            median_demand = float(np.median(demand_high)) if demand_high else median_supply
            overpricing = (median_supply - median_demand) / median_demand if median_demand > 0 else 0

            results[key] = MarketGroup(
                district=grp["district"],
                property_type=grp["property_type"],
                supply_count=supply_count,
                demand_count=demand_count,
                supply_prices=supply_prices,
                demand_budgets_low=demand_low,
                demand_budgets_high=demand_high,
                overlap_low=round(overlap_low, 0),
                overlap_high=round(overlap_high, 0),
                market_acceptable_price=round(market_price, 0),
                price_range_low=round(overlap_low, 0),
                price_range_high=round(overlap_high, 0),
                demand_supply_ratio=round(ds_ratio, 3),
                overpricing_index=round(overpricing, 4),
            )

        return results

    # ==========================================
    # MARKET ACCEPTABLE PRICE COMPUTATION
    # ==========================================

    def compute_market_acceptable_price(
        self,
        listing: ListingRecord,
        market_groups: Dict[str, MarketGroup],
    ) -> Dict:
        """
        Tính Market Acceptable Price cho 1 listing cụ thể.

        Returns dict với:
          - market_acceptable_price: giá chấp nhận thị trường
          - price_range: (low, high)
          - demand_weight: hệ số cầu
          - stale_penalty: penalty do tồn lâu
          - over_asking: chênh lệch so với giá rao
          - confidence: độ tin cậy (0-1)
        """
        key = f"{listing.district}|{listing.property_type}"
        group = market_groups.get(key)

        if not group:
            return {
                "market_acceptable_price": listing.price,
                "price_range": (listing.price * 0.85, listing.price * 1.05),
                "demand_weight": 0.0,
                "stale_penalty": 0.0,
                "over_asking": 0.0,
                "confidence": 0.1,
                "reasoning": "Không đủ dữ liệu nhóm thị trường",
            }

        base_price = group.market_acceptable_price

        # Demand weight: cầu cao → giá tăng, cầu thấp → giá giảm
        if group.demand_count > 0 and group.supply_count > 0:
            raw_weight = math.log(group.demand_supply_ratio + 0.01) * self.demand_weight_scale
            demand_weight = max(-self.max_demand_weight, min(self.max_demand_weight, raw_weight))
        else:
            demand_weight = 0.0

        # Stale penalty: tồn lâu → giá giảm
        dom = listing.days_on_market or 0
        stale_penalty = min(self.max_stale_penalty, dom * self.stale_penalty_rate)

        # Price revision bonus: giảm giá nhiều lần → thị trường đang từ chối giá rao
        revision_penalty = min(0.05, (listing.price_revision_count or 0) * 0.015)

        # Demand signal bonus: nhiều lượt xem/lưu → nhu cầu thật
        views = listing.views_count or 0
        saves = listing.saves_count or 0
        contacts = listing.contacts_count or 0
        demand_signal = min(0.05, (views * 0.001 + saves * 0.01 + contacts * 0.02))

        # Adjusted market acceptable price
        adjusted_price = base_price * (1 + demand_weight + demand_signal) * (1 - stale_penalty - revision_penalty)

        # Price range
        range_width = 0.10 + (0.05 if group.supply_count < 10 else 0)
        price_low = adjusted_price * (1 - range_width)
        price_high = adjusted_price * (1 + range_width * 0.5)

        # Over-asking score
        over_asking = listing.price - adjusted_price

        # Confidence based on data availability
        confidence = min(1.0, (
            0.3 * min(1, group.supply_count / 20) +
            0.3 * min(1, group.demand_count / 10) +
            0.2 * (1 if listing.days_on_market is not None else 0) +
            0.2 * (1 if listing.views_count else 0)
        ))

        return {
            "market_acceptable_price": round(adjusted_price, 0),
            "price_range": (round(price_low, 0), round(price_high, 0)),
            "demand_weight": round(demand_weight, 4),
            "stale_penalty": round(stale_penalty + revision_penalty, 4),
            "demand_signal": round(demand_signal, 4),
            "over_asking": round(over_asking, 0),
            "confidence": round(confidence, 3),
            "reasoning": self._generate_reasoning(
                listing, group, demand_weight, stale_penalty,
                revision_penalty, demand_signal, over_asking
            ),
        }

    def _generate_reasoning(
        self, listing, group, demand_weight, stale_penalty,
        revision_penalty, demand_signal, over_asking
    ) -> str:
        """Tạo giải thích cho Market Acceptable Price."""
        parts = []

        parts.append(
            f"Nhóm thị trường: {group.district} / {group.property_type} "
            f"({group.supply_count} tin rao, {group.demand_count} yêu cầu mua)"
        )

        parts.append(
            f"Giá trung vị nhóm: {group.market_acceptable_price/1e9:.2f} tỷ"
        )

        if demand_weight > 0.01:
            parts.append(f"Cầu cao hơn cung → điều chỉnh +{demand_weight*100:.1f}%")
        elif demand_weight < -0.01:
            parts.append(f"Cung dư → điều chỉnh {demand_weight*100:.1f}%")

        if stale_penalty > 0.01:
            parts.append(
                f"Tồn {listing.days_on_market} ngày → penalty -{stale_penalty*100:.1f}%"
            )

        if revision_penalty > 0.005:
            parts.append(
                f"Giảm giá {listing.price_revision_count} lần → penalty -{revision_penalty*100:.1f}%"
            )

        if demand_signal > 0.005:
            parts.append(
                f"Tín hiệu cầu (xem/lưu/liên hệ) → bonus +{demand_signal*100:.1f}%"
            )

        if over_asking > 0:
            parts.append(
                f"⚠ Giá rao CAO hơn giá thị trường {over_asking/1e9:.2f} tỷ "
                f"({over_asking/listing.price*100:.1f}%)"
            )
        elif over_asking < 0:
            parts.append(
                f"✓ Giá rao THẤP hơn giá thị trường {abs(over_asking)/1e9:.2f} tỷ"
            )

        return " | ".join(parts)

    # ==========================================
    # BATCH PROCESSING
    # ==========================================

    def process_all_listings(
        self,
        listings: List[ListingRecord],
        buyers: List[BuyerRequest],
    ) -> List[Dict]:
        """
        Tính Market Acceptable Price cho tất cả listings.
        Returns list of dicts, mỗi dict chứa listing_id + kết quả.
        """
        market_groups = self.group_by_market(listings, buyers)

        results = []
        for listing in listings:
            result = self.compute_market_acceptable_price(listing, market_groups)
            result["listing_id"] = listing.id
            result["listing_price"] = listing.price
            results.append(result)

        return results
