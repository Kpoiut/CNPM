"""
Equilibrium Prediction Pipeline — Thuật toán 3 tầng ước lượng giá cân bằng.

Tầng 1 (Supply Model): P_ask = f(property_features, location, listing_signals)
Tầng 2 (Demand Model): P_bid = g(buyer_requirements, budgets, urgency)
Tầng 3 (Equilibrium):  P_market = α·P_ask + (1-α)·P_bid - penalty_overasking - penalty_stale

Biến mục tiêu KHÔNG phải giá rao. Mà là:
  market_acceptable_price = overlap(ask_distribution, bid_distribution)

Đây là giá có khả năng được cả bên bán và bên mua chấp nhận.

Reference:
  "Estimating Market-Acceptable Residential Real Estate Prices
   Using Supply-Demand Matching Between Listings and Buyer Requirements"
"""
import numpy as np
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class EquilibriumInput:
    """Input cho 1 property cần định giá."""
    # Property features
    property_type: str
    district: str
    province: str
    area_m2: float
    bedrooms: int = 0
    floor_count: int = 1
    legal_status: str = "pending"

    # Listing signals (supply side)
    listing_price: float = 0  # Giá rao
    days_on_market: int = 0
    price_revision_count: int = 0
    views_count: int = 0
    saves_count: int = 0
    contacts_count: int = 0

    # Market context (pre-computed)
    supply_count_in_group: int = 0
    demand_count_in_group: int = 0
    median_ask_price: float = 0
    median_bid_budget: float = 0
    ask_bid_overlap_low: float = 0
    ask_bid_overlap_high: float = 0


@dataclass
class EquilibriumOutput:
    """Output: giá cân bằng + giải thích."""
    market_acceptable_price: float
    price_range_low: float
    price_range_high: float
    confidence: float  # 0-1
    alpha: float  # Trọng số supply vs demand

    # Components
    supply_price: float  # P_ask (adjusted)
    demand_price: float  # P_bid (estimated)
    stale_penalty: float
    overasking_penalty: float
    demand_pressure: float

    # Scores
    acceptance_score: float  # 0-1
    overpricing_index: float
    demand_coverage_ratio: float

    # Explanation
    reasoning: str = ""


class EquilibriumPipeline:
    """
    3-Layer Equilibrium Price Estimation.

    Layer 1: Supply Model
      - Ước lượng P_ask từ features + listing signals
      - Áp dụng stale penalty + revision adjustment

    Layer 2: Demand Model
      - Ước lượng P_bid từ buyer budgets + urgency
      - Tính demand pressure

    Layer 3: Equilibrium
      - P_market = α·P_ask + (1-α)·P_bid - penalties
      - α = f(demand_pressure, supply_pressure)
    """

    def __init__(self):
        # Configurable parameters
        self.stale_rate = 0.001           # Per day penalty
        self.max_stale_penalty = 0.15     # Max 15%
        self.revision_rate = 0.015        # Per revision penalty
        self.max_revision_penalty = 0.05  # Max 5%
        self.demand_signal_cap = 0.05     # Max demand bonus 5%
        self.alpha_min = 0.3              # Min supply weight
        self.alpha_max = 0.8              # Max supply weight

    # ═══════════════════════════════════════════════════════
    # LAYER 1: SUPPLY MODEL
    # ═══════════════════════════════════════════════════════
    def compute_supply_price(self, inp: EquilibriumInput) -> Tuple[float, float, float]:
        """
        Tầng 1: Ước lượng giá phía cung (adjusted ask price).

        Returns: (adjusted_ask, stale_penalty, revision_penalty)
        """
        base = inp.listing_price
        if base <= 0:
            base = inp.median_ask_price

        # Stale penalty: tin tồn lâu → giá thực thấp hơn giá rao
        stale = min(self.max_stale_penalty, (inp.days_on_market or 0) * self.stale_rate)

        # Revision penalty: giảm giá nhiều lần → thị trường đã reject
        revision = min(self.max_revision_penalty,
                       (inp.price_revision_count or 0) * self.revision_rate)

        # Demand signal bonus (nếu nhiều người quan tâm → giá rao có cơ sở)
        views = inp.views_count or 0
        saves = inp.saves_count or 0
        contacts = inp.contacts_count or 0
        demand_bonus = min(self.demand_signal_cap,
                          views * 0.0005 + saves * 0.005 + contacts * 0.01)

        adjusted = base * (1 + demand_bonus) * (1 - stale - revision)
        return adjusted, stale, revision

    # ═══════════════════════════════════════════════════════
    # LAYER 2: DEMAND MODEL
    # ═══════════════════════════════════════════════════════
    def compute_demand_price(self, inp: EquilibriumInput) -> Tuple[float, float]:
        """
        Tầng 2: Ước lượng giá phía cầu (bid estimate).

        Returns: (estimated_bid, demand_pressure)
        """
        if inp.median_bid_budget > 0:
            # Có dữ liệu cầu thực → dùng median budget
            bid_price = inp.median_bid_budget
        elif inp.ask_bid_overlap_high > 0:
            # Có vùng overlap → dùng midpoint
            bid_price = (inp.ask_bid_overlap_low + inp.ask_bid_overlap_high) / 2
        else:
            # Không có dữ liệu cầu → ước lượng = 85% giá rao trung vị
            bid_price = inp.median_ask_price * 0.85

        # Demand pressure: cầu/cung ratio
        if inp.supply_count_in_group > 0 and inp.demand_count_in_group > 0:
            ratio = inp.demand_count_in_group / inp.supply_count_in_group
            # log scale: ratio > 1 → pressure tăng, < 1 → giảm
            demand_pressure = math.log(max(0.01, ratio)) * 0.1
            demand_pressure = max(-0.15, min(0.15, demand_pressure))
        else:
            demand_pressure = 0.0

        return bid_price, demand_pressure

    # ═══════════════════════════════════════════════════════
    # LAYER 3: EQUILIBRIUM
    # ═══════════════════════════════════════════════════════
    def compute_alpha(self, inp: EquilibriumInput, demand_pressure: float) -> float:
        """
        Tính trọng số α giữa supply và demand.

        α cao → tin vào giá rao (thị trường thanh khoản)
        α thấp → tin vào ngân sách mua (thị trường trầm lắng)

        α = demand_pressure / (demand_pressure + supply_pressure)
        """
        if inp.demand_count_in_group == 0:
            return self.alpha_max  # Không có dữ liệu cầu → thiên về supply

        if inp.supply_count_in_group == 0:
            return self.alpha_min

        # Thanh khoản = nhiều cầu / ít cung → α cao
        ds_ratio = inp.demand_count_in_group / inp.supply_count_in_group

        if ds_ratio >= 1.0:
            # Nhiều cầu → giá rao đáng tin hơn
            alpha = min(self.alpha_max, 0.5 + ds_ratio * 0.1)
        else:
            # Ít cầu → nghiêng về demand
            alpha = max(self.alpha_min, 0.5 - (1 - ds_ratio) * 0.2)

        # Adjust by demand signals
        if (inp.views_count or 0) > 50 or (inp.contacts_count or 0) > 5:
            alpha = min(self.alpha_max, alpha + 0.05)

        if (inp.days_on_market or 0) > 90:
            alpha = max(self.alpha_min, alpha - 0.1)

        return round(alpha, 3)

    def predict(self, inp: EquilibriumInput) -> EquilibriumOutput:
        """
        Tính giá cân bằng cho 1 property.

        P_market = α·P_ask + (1-α)·P_bid + demand_pressure_adj
        """
        # Layer 1: Supply
        supply_price, stale_pen, revision_pen = self.compute_supply_price(inp)

        # Layer 2: Demand
        demand_price, demand_pressure = self.compute_demand_price(inp)

        # Layer 3: Equilibrium
        alpha = self.compute_alpha(inp, demand_pressure)

        # Weighted combination
        equilibrium = alpha * supply_price + (1 - alpha) * demand_price

        # Apply demand pressure adjustment
        equilibrium *= (1 + demand_pressure)

        # Overasking penalty: nếu giá rao >> equilibrium → penalty thêm
        overasking = 0.0
        if inp.listing_price > 0:
            gap = (inp.listing_price - equilibrium) / inp.listing_price
            if gap > 0.1:  # Over-asking > 10%
                overasking = min(0.1, gap * 0.3)
                equilibrium *= (1 - overasking)

        # Price range
        uncertainty = 0.10 + (0.05 if inp.supply_count_in_group < 10 else 0)
        if inp.demand_count_in_group == 0:
            uncertainty += 0.05
        range_low = equilibrium * (1 - uncertainty)
        range_high = equilibrium * (1 + uncertainty * 0.6)

        # Use overlap bounds if available
        if inp.ask_bid_overlap_low > 0 and inp.ask_bid_overlap_high > 0:
            range_low = max(range_low, inp.ask_bid_overlap_low * 0.95)
            range_high = min(range_high, inp.ask_bid_overlap_high * 1.05)

        # Confidence
        confidence = self._compute_confidence(inp)

        # Scores
        overpricing_idx = 0.0
        if inp.median_bid_budget > 0:
            overpricing_idx = (inp.median_ask_price - inp.median_bid_budget) / inp.median_bid_budget

        dcr = 0.0
        if inp.supply_count_in_group > 0:
            dcr = inp.demand_count_in_group / inp.supply_count_in_group

        acceptance = min(1.0, max(0.0,
            0.5 + (1 - abs(overpricing_idx)) * 0.3 + confidence * 0.2
        ))

        # Reasoning
        reasoning = self._build_reasoning(
            inp, supply_price, demand_price, equilibrium,
            alpha, stale_pen, revision_pen, demand_pressure, overasking
        )

        return EquilibriumOutput(
            market_acceptable_price=round(equilibrium, 0),
            price_range_low=round(range_low, 0),
            price_range_high=round(range_high, 0),
            confidence=round(confidence, 3),
            alpha=alpha,
            supply_price=round(supply_price, 0),
            demand_price=round(demand_price, 0),
            stale_penalty=round(stale_pen + revision_pen, 4),
            overasking_penalty=round(overasking, 4),
            demand_pressure=round(demand_pressure, 4),
            acceptance_score=round(acceptance, 3),
            overpricing_index=round(overpricing_idx, 4),
            demand_coverage_ratio=round(dcr, 3),
            reasoning=reasoning,
        )

    def _compute_confidence(self, inp: EquilibriumInput) -> float:
        """Tính độ tin cậy (0-1)."""
        c = 0.0
        c += 0.25 * min(1, inp.supply_count_in_group / 20)
        c += 0.25 * min(1, inp.demand_count_in_group / 10)
        c += 0.15 * (1 if inp.days_on_market is not None and inp.days_on_market > 0 else 0)
        c += 0.15 * (1 if (inp.views_count or 0) > 0 else 0)
        c += 0.10 * (1 if inp.ask_bid_overlap_high > 0 else 0)
        c += 0.10 * (1 if inp.listing_price > 0 else 0)
        return min(1.0, c)

    def _build_reasoning(self, inp, supply_p, demand_p, equilibrium,
                         alpha, stale, revision, d_pressure, overasking) -> str:
        parts = []
        parts.append(f"Nhom: {inp.district}/{inp.property_type} "
                     f"(cung={inp.supply_count_in_group}, cau={inp.demand_count_in_group})")
        parts.append(f"P_ask={supply_p/1e9:.2f}ty (alpha={alpha:.2f})")
        parts.append(f"P_bid={demand_p/1e9:.2f}ty (1-alpha={1-alpha:.2f})")
        parts.append(f"P_eq={equilibrium/1e9:.2f}ty")

        if stale > 0.005:
            parts.append(f"stale:-{stale*100:.1f}%")
        if revision > 0.005:
            parts.append(f"revision:-{revision*100:.1f}%")
        if d_pressure > 0.01:
            parts.append(f"demand_pressure:+{d_pressure*100:.1f}%")
        elif d_pressure < -0.01:
            parts.append(f"supply_excess:{d_pressure*100:.1f}%")
        if overasking > 0.005:
            parts.append(f"overasking:-{overasking*100:.1f}%")

        return " | ".join(parts)

    # ═══════════════════════════════════════════════════════
    # BATCH PROCESSING WITH DB
    # ═══════════════════════════════════════════════════════
    def process_from_db(self, db) -> List[Dict]:
        """
        Chạy pipeline trên toàn bộ DB.
        1. Load listings từ properties
        2. Load buyers từ buyer_requirements
        3. Group by (district, property_type)
        4. Compute equilibrium cho từng listing
        5. Ghi market_acceptance_score vào DB
        """
        from src.backend.models import Property, BuyerRequirement
        from src.ml.supply_demand import SupplyDemandEngine

        # Load data
        listings = db.query(Property).filter(Property.price > 0).all()
        buyers = db.query(BuyerRequirement).filter(BuyerRequirement.is_active == True).all()

        print(f"  Listings: {len(listings)} | Buyers: {len(buyers)}")

        # Build market groups using SupplyDemandEngine
        engine = SupplyDemandEngine()
        from src.ml.supply_demand import ListingRecord, BuyerRequest

        listing_records = [
            ListingRecord(
                id=p.id, property_type=p.property_type, district=p.district,
                ward=p.ward, area_m2=p.area_m2 or 0, price=p.price,
                bedrooms=p.bedrooms or 0, legal_status=p.legal_status,
                days_on_market=p.days_on_market or 0,
                price_revision_count=p.price_revision_count or 0,
                views_count=p.views_count or 0, saves_count=p.saves_count or 0,
                contacts_count=p.contacts_count or 0,
            ) for p in listings
        ]

        buyer_records = [
            BuyerRequest(
                id=b.id, property_type=b.property_type, district=b.district,
                ward=b.ward, min_area=b.min_area, max_area=b.max_area,
                min_budget=b.min_budget, max_budget=b.max_budget,
                bedrooms=b.bedrooms, legal_requirement=b.legal_requirement,
                urgency=b.urgency or "normal",
            ) for b in buyers
        ]

        market_groups = engine.group_by_market(listing_records, buyer_records)

        # Process each listing through equilibrium pipeline
        results = []
        for prop in listings:
            key = f"{prop.district}|{prop.property_type}"
            group = market_groups.get(key)

            inp = EquilibriumInput(
                property_type=prop.property_type,
                district=prop.district,
                province=prop.province_city,
                area_m2=prop.area_m2 or 0,
                bedrooms=prop.bedrooms or 0,
                floor_count=prop.floor_count or 1,
                legal_status=prop.legal_status or "pending",
                listing_price=prop.price,
                days_on_market=prop.days_on_market or 0,
                price_revision_count=prop.price_revision_count or 0,
                views_count=prop.views_count or 0,
                saves_count=prop.saves_count or 0,
                contacts_count=prop.contacts_count or 0,
                supply_count_in_group=group.supply_count if group else 0,
                demand_count_in_group=group.demand_count if group else 0,
                median_ask_price=float(np.median(group.supply_prices)) if group else prop.price,
                median_bid_budget=float(np.median(group.demand_budgets_high)) if group and group.demand_budgets_high else 0,
                ask_bid_overlap_low=group.overlap_low if group else 0,
                ask_bid_overlap_high=group.overlap_high if group else 0,
            )

            output = self.predict(inp)

            # Update DB
            prop.market_acceptance_score = output.acceptance_score
            prop.over_asking_score = output.overpricing_index
            prop.demand_coverage_ratio = output.demand_coverage_ratio
            prop.stale_listing_score = output.stale_penalty

            results.append({
                "property_id": prop.id,
                "listing_price": prop.price,
                "market_acceptable_price": output.market_acceptable_price,
                "range": (output.price_range_low, output.price_range_high),
                "confidence": output.confidence,
                "alpha": output.alpha,
                "acceptance_score": output.acceptance_score,
                "reasoning": output.reasoning,
            })

        db.commit()
        return results
