"""
SDEV Engine — Supply-Demand Equilibrium Valuation
Implements BAE-AVM 2.0 pilot for the 6-district study.

Core formula:
  P*(c) = argmax_p [S_accept(p | r̄_s, σ_s) × D_accept(p | w̄_b, σ_b)]

Where:
  S_accept(p) = Φ((p - r̄_s) / σ_s)   ← seller reservation proxy
  D_accept(p) = 1 - Φ((p - w̄_b) / σ_b) ← buyer WTP proxy

NOTE: r̄_s and w̄_b are PROXIES, not ground truth.
      This is estimating market-acceptable price, NOT transaction price.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, asdict
from typing import List, Optional

import numpy as np
from sqlalchemy.orm import Session

from src.backend.models import Property, BuyerRequirement


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SDEVClusterStats:
    """Ask-side cluster statistics (supply signal)."""
    district: str
    area_band: str          # "50-70", "70-90", "90-120", "120+"
    bedrooms: int
    n_listings: int
    q25_ask: float
    q50_ask: float
    q75_ask: float
    std_ask: float
    median_ppm: float
    reliability_score: float   # sigmoid(score), 0-1


@dataclass
class SDEVBidStats:
    """Demand-side bid distribution statistics."""
    district: str
    area_band: str
    bedrooms: int
    n_requirements: int
    q25_bid: float
    q50_bid: float
    q75_bid: float
    std_bid: float
    demand_pressure: float    # buyer_inflow / (buyer_inflow + seller_inflow) proxy
    reliability_score: float


@dataclass
class SDEVOutput:
    """Full SDEV output."""
    status: str              # "ESTIMATED" | "NO_ESTIMATE"
    reason: Optional[str]     # Why NO_ESTIMATE

    # Price estimates
    estimated_mid_price: int       # VND
    acceptable_low: int            # VND
    acceptable_high: int            # VND
    price_per_m2: int             # VND/m²

    # Scores
    acceptance_score: float       # 0-1
    confidence_level: str         # "low" | "medium" | "high"
    ask_bid_overlap_score: float  # 0-1

    # Cluster info
    cluster_district: str
    cluster_area_band: str
    cluster_bedrooms: int
    n_ask_listings: int
    n_bid_requirements: int

    # Demand coverage
    demand_coverage_ratio: float  # qualified_buyers / similar_listings

    # Main drivers
    main_drivers: List[str]

    # For downstream use
    ask_stats: Optional[dict]
    bid_stats: Optional[dict]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _area_band(area_m2: float) -> str:
    if area_m2 < 50:
        return "<50"
    elif area_m2 < 70:
        return "50-70"
    elif area_m2 < 90:
        return "70-90"
    elif area_m2 < 120:
        return "90-120"
    elif area_m2 < 150:
        return "120-150"
    else:
        return "150+"


def _normal_cdf(x: float) -> float:
    """Approximation of Φ(x) — standard normal CDF."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def _compute_ask_stats(
    listings: List[Property],
    district: str,
    area_band: str,
    bedrooms: int,
) -> Optional[SDEVClusterStats]:
    """Compute ask-side distribution from listing prices in a cluster."""
    prices = [float(p.price) for p in listings if p.price and p.price > 0]
    if len(prices) < 3:
        return None

    prices.sort()
    n = len(prices)
    q25 = prices[int(n * 0.25)]
    q50 = prices[int(n * 0.50)]
    q75 = prices[int(n * 0.75)]
    std = statistics.stdev(prices) if n > 1 else (q75 - q25) / 1.35

    # Reliability: more listings = more reliable
    reliability = _sigmoid(math.log(len(prices) / 10))

    # ppm
    areas = [float(p.area_m2) for p in listings if p.area_m2 and p.area_m2 > 0]
    ppm_values = [p / a for p, a in zip(prices, areas) if a > 0]
    median_ppm = statistics.median(ppm_values) if ppm_values else q50 / 70

    return SDEVClusterStats(
        district=district,
        area_band=area_band,
        bedrooms=bedrooms,
        n_listings=len(listings),
        q25_ask=q25,
        q50_ask=q50,
        q75_ask=q75,
        std_ask=std,
        median_ppm=median_ppm,
        reliability_score=reliability,
    )


def _compute_bid_stats(
    requirements: List[BuyerRequirement],
    district: str,
    area_band: str,
    bedrooms: int,
) -> Optional[SDEVBidStats]:
    """Compute bid-side distribution from buyer requirements in a cluster."""
    budgets = [float(r.max_budget) for r in requirements
               if r.max_budget and r.max_budget > 0]
    if len(budgets) < 3:
        return None

    budgets.sort()
    n = len(budgets)
    q25 = budgets[int(n * 0.25)]
    q50 = budgets[int(n * 0.50)]
    q75 = budgets[int(n * 0.75)]
    std = statistics.stdev(budgets) if n > 1 else (q75 - q25) / 1.35

    # Reliability
    reliability = _sigmoid(math.log(len(budgets) / 5))

    return SDEVBidStats(
        district=district,
        area_band=area_band,
        bedrooms=bedrooms,
        n_requirements=len(requirements),
        q25_bid=q25,
        q50_bid=q50,
        q75_bid=q75,
        std_bid=std,
        demand_pressure=0.5,   # No seller_inflow data → neutral
        reliability_score=reliability,
    )


def _compute_overlap(
    q25_ask: float, q75_ask: float,
    q25_bid: float, q75_bid: float
) -> tuple[float, float, float]:
    """
    Compute ask-bid overlap score and acceptable range.
    Returns: (overlap_score, acceptable_low, acceptable_high)
    """
    # Intersection of [q25_ask, q75_ask] and [q25_bid, q75_bid]
    overlap_low = max(q25_ask, q25_bid)
    overlap_high = min(q75_ask, q75_bid)

    if overlap_high > overlap_low:
        # Vùng giao nhau
        overlap_width = overlap_high - overlap_low
        # Tính overlap score như tỷ lệ overlap / total spread
        total_spread = max(q75_ask, q75_bid) - min(q25_ask, q25_bid)
        if total_spread > 0:
            overlap_score = overlap_width / total_spread
        else:
            overlap_score = 1.0
        return overlap_score, overlap_low, overlap_high
    else:
        # Không có giao nhau → dùng weighted compromise
        # midpoint giữa hai vùng
        mid_ask = (q25_ask + q75_ask) / 2
        mid_bid = (q25_bid + q75_bid) / 2
        # Trọng số ngược với khoảng cách đến đầu gần nhất
        # Nếu ask cao hơn bid nhiều → dịch về phía bid
        gap = mid_ask - mid_bid
        # Compromise: weighted average với bias về phía bid
        compromise_low = mid_bid - gap * 0.2
        compromise_high = mid_ask + gap * 0.2
        # Overlap score = 0 (không giao nhau)
        return 0.0, compromise_low, compromise_high


def _compute_acceptance_score(
    overlap_score: float,
    ask_reliability: float,
    bid_reliability: float,
    n_ask: int,
    n_bid: int,
    ask_bid_overlap_score: float,
) -> float:
    """
    Composite acceptance score (heuristic, pilot-stage).
    Weights: overlap=0.35, ask_reliability=0.20,
             bid_reliability=0.20, data_sufficiency=0.25
    """
    data_sufficiency = min(1.0, (n_ask / 20) * 0.5 + (n_bid / 10) * 0.5)

    score = (
        overlap_score * 0.35 +
        ask_bid_overlap_score * 0.20 +
        ask_reliability * 0.20 +
        bid_reliability * 0.20 +
        data_sufficiency * 0.25
    )
    return round(min(1.0, max(0.0, score)), 2)


def _confidence_level(
    n_ask: int, n_bid: int,
    overlap_score: float,
    ask_reliability: float,
    bid_reliability: float
) -> str:
    """Determine confidence level."""
    if n_ask < 5 or ask_reliability < 0.3:
        return "low"
    if n_bid == 0 or bid_reliability < 0.3:
        # Ask-only → medium confidence
        if n_ask >= 20 and ask_reliability >= 0.7:
            return "medium"
        return "low"
    if n_bid >= 5 and n_ask >= 10 and overlap_score > 0.3:
        return "high"
    if n_bid >= 3 and n_ask >= 10:
        return "medium"
    return "low"


def _no_estimate_reason(
    n_ask: int, n_bid: int,
    ask_reliability: float
) -> str:
    if n_ask < 3:
        return "Insufficient comparable listings (n<3)"
    if ask_reliability < 0.3:
        return "Low listing quality in cluster"
    if n_bid == 0:
        return "No buyer requirement data for demand-side estimation"
    return "Unknown"


# ─────────────────────────────────────────────────────────────────────────────
# SDEV ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class SDEVEngine:
    """
    SDEV — Supply-Demand Equilibrium Valuation Engine.

    For the 6-district pilot, cluster is defined as:
      cluster = district × area_band × bedrooms

    Ask distribution: listing prices from comparable properties
    Bid distribution: buyer requirements (if available)

    IMPORTANT: All price estimates are PROXIES for market-acceptable price,
    NOT predictions of actual transaction prices.
    """

    def __init__(self, db: Session):
        self.db = db

    def run(
        self,
        district: str,
        area_m2: float,
        bedrooms: int,
        asset_type: str = "apartment",
    ) -> SDEVOutput:
        """
        Run SDEV valuation for a property.

        Args:
            district: e.g. "Quận Cầu Giấy"
            area_m2: Property area
            bedrooms: Number of bedrooms
            asset_type: "apartment" | "townhouse" | etc.

        Returns:
            SDEVOutput with estimated price range and acceptance score.
        """
        area_band = _area_band(area_m2)

        # ─── Step 1: Ask distribution (supply signal) ─────────────────
        ask_listings = self._find_comparable_ask(district, asset_type, area_band, bedrooms)
        ask_stats = _compute_ask_stats(ask_listings, district, area_band, bedrooms)

        if ask_stats is None:
            return SDEVOutput(
                status="NO_ESTIMATE",
                reason=_no_estimate_reason(len(ask_listings), 0, 0.0),
                estimated_mid_price=0,
                acceptable_low=0,
                acceptable_high=0,
                price_per_m2=0,
                acceptance_score=0.0,
                confidence_level="low",
                ask_bid_overlap_score=0.0,
                cluster_district=district,
                cluster_area_band=area_band,
                cluster_bedrooms=bedrooms,
                n_ask_listings=len(ask_listings),
                n_bid_requirements=0,
                demand_coverage_ratio=0.0,
                main_drivers=[],
                ask_stats=None,
                bid_stats=None,
            )

        # ─── Step 2: Bid distribution (demand signal) ──────────────
        bid_reqs = self._find_comparable_bid(district, area_band, bedrooms)
        bid_stats = _compute_bid_stats(bid_reqs, district, area_band, bedrooms)

        # ─── Step 3: Compute overlap ─────────────────────────────────
        if bid_stats is not None:
            overlap_score, accept_low, accept_high = _compute_overlap(
                ask_stats.q25_ask, ask_stats.q75_ask,
                bid_stats.q25_bid, bid_stats.q75_bid,
            )
            # Use bid stats for bid-side reliability
            bid_reliability = bid_stats.reliability_score
            n_bid = bid_stats.n_requirements
            # Market acceptable price: midpoint of overlap range
            mid_price = int((accept_low + accept_high) / 2)
        else:
            # No demand data → fallback to ask-only (seller perspective)
            overlap_score = 0.0
            accept_low = ask_stats.q25_ask
            accept_high = ask_stats.q75_ask
            mid_price = int(ask_stats.q50_ask)
            bid_reliability = 0.0
            n_bid = 0

        # ─── Step 4: Compute acceptance score ────────────────────────
        ask_reliability = ask_stats.reliability_score
        acceptance_score = _compute_acceptance_score(
            overlap_score=overlap_score,
            ask_reliability=ask_reliability,
            bid_reliability=bid_reliability,
            n_ask=ask_stats.n_listings,
            n_bid=n_bid,
            ask_bid_overlap_score=overlap_score,
        )

        # ─── Step 5: Demand coverage ratio ──────────────────────────
        if n_bid > 0 and ask_stats.n_listings > 0:
            coverage = n_bid / ask_stats.n_listings
            demand_coverage_ratio = min(1.0, coverage)
        elif n_bid == 0:
            demand_coverage_ratio = 0.0
        else:
            demand_coverage_ratio = 1.0

        # ─── Step 6: Confidence level ───────────────────────────────
        confidence = _confidence_level(
            ask_stats.n_listings, n_bid,
            overlap_score, ask_reliability, bid_reliability
        )

        # ─── Step 7: Main drivers ───────────────────────────────────
        drivers = self._explain_drivers(
            ask_stats, bid_stats, overlap_score, n_bid
        )

        # ─── Step 8: Price per m² ─────────────────────────────────
        price_per_m2 = int(mid_price / area_m2) if area_m2 > 0 else 0

        return SDEVOutput(
            status="ESTIMATED",
            reason=None,
            estimated_mid_price=mid_price,
            acceptable_low=int(accept_low),
            acceptable_high=int(accept_high),
            price_per_m2=price_per_m2,
            acceptance_score=acceptance_score,
            confidence_level=confidence,
            ask_bid_overlap_score=round(overlap_score, 2),
            cluster_district=district,
            cluster_area_band=area_band,
            cluster_bedrooms=bedrooms,
            n_ask_listings=ask_stats.n_listings,
            n_bid_requirements=n_bid,
            demand_coverage_ratio=round(demand_coverage_ratio, 2),
            main_drivers=drivers,
            ask_stats=asdict(ask_stats),
            bid_stats=asdict(bid_stats) if bid_stats else None,
        )

    def _find_comparable_ask(
        self,
        district: str,
        asset_type: str,
        area_band: str,
        bedrooms: int,
    ) -> List[Property]:
        type_map = {
            "apartment": "apartment",
            "townhouse": "townhouse",
            "villa": "villa",
            "house": "house",
            "land": "land",
        }
        db_type = type_map.get(asset_type.lower(), asset_type.lower())

        band_ranges = {
            "<50":      (0, 50),
            "50-70":   (50, 70),
            "70-90":   (70, 90),
            "90-120":  (90, 120),
            "120-150": (120, 150),
            "150+":     (150, 1000),
        }
        lo, hi = band_ranges.get(area_band, (0, 200))

        br_opts = []
        if bedrooms and bedrooms > 0:
            br_opts = [bedrooms-1, bedrooms, bedrooms+1]
        else:
            br_opts = [0, 1, 2, 3, 4, 5]

        listings = (
            self.db.query(Property)
            .filter(
                Property.record_status != "archived",
                Property.price > 0,
                Property.area_m2 != None,
                Property.area_m2 > lo,
                Property.area_m2 <= hi,
                Property.district == district,
                Property.property_type == db_type,
                Property.bedrooms.in_(br_opts),
            )
            .order_by(Property.evidence_tier)
            .limit(100)
            .all()
        )
        return listings

    def _find_comparable_bid(
        self,
        district: str,
        area_band: str,
        bedrooms: int,
    ) -> List[BuyerRequirement]:
        band_ranges = {
            "<50":      (0, 50),
            "50-70":   (50, 70),
            "70-90":   (70, 90),
            "90-120":  (90, 120),
            "120-150": (120, 150),
            "150+":     (150, 10000),
        }
        area_lo, area_hi = band_ranges.get(area_band, (0, 10000))

        reqs = (
            self.db.query(BuyerRequirement)
            .filter(
                BuyerRequirement.is_active == True,
                BuyerRequirement.district == district,
                BuyerRequirement.min_area <= area_hi,
                BuyerRequirement.max_area >= area_lo,
                BuyerRequirement.bedrooms == bedrooms,
            )
            .limit(50)
            .all()
        )
        return reqs

    def _explain_drivers(
        self,
        ask_stats: SDEVClusterStats,
        bid_stats: Optional[SDEVBidStats],
        overlap_score: float,
        n_bid: int,
    ) -> List[str]:
        drivers = []
        drivers.append(f"{ask_stats.n_listings} comparable listings in {ask_stats.district}")
        if ask_stats.n_listings >= 20:
            drivers.append("High listing density")
        elif ask_stats.n_listings >= 10:
            drivers.append("Medium listing density")
        else:
            drivers.append("Low listing density — estimate may be unreliable")

        if bid_stats and bid_stats.n_requirements > 0:
            drivers.append(f"{bid_stats.n_requirements} buyer requirements in cluster")
            drivers.append(f"Median buyer budget: {bid_stats.q50_bid/1e9:.2f}B VND")
        else:
            drivers.append("No buyer requirement data — ask-only estimation")

        if overlap_score > 0.3:
            drivers.append("Ask-bid overlap present")
        elif overlap_score > 0:
            drivers.append("Partial ask-bid overlap")
        else:
            drivers.append("No ask-bid overlap — demand data may be needed")

        return drivers
