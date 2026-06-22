"""
API v2 — Transaction Price Derivation Endpoints.

GET /api/v2/transaction-price/{property_id}
    Returns market-acceptable price derived from supply-demand asymmetry.
    Uses matched_pairs table + SDEV engine for ML noise correction.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from src.backend.database import get_db
from src.backend.api_v2 import router as api_router
from src.backend.model_metrics import serving_calibration_metric
from src.backend.models import MatchedPair, Property
from src.domain.valuation.sdev_engine import SDEVEngine


router = api_router


def _vnd(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


def _area_band(area_m2: float) -> str:
    if area_m2 < 50:
        return "30-50"
    if area_m2 < 70:
        return "50-70"
    if area_m2 < 90:
        return "70-90"
    if area_m2 < 120:
        return "90-120"
    if area_m2 < 200:
        return "120-200"
    return "200+"


@api_router.get("/transaction-price/{property_id}", response_model=dict)
def get_transaction_price(property_id: int, db: Session = Depends(get_db)):
    """
    Derive market-acceptable transaction equivalent for a property.

    Method: Supply-Demand Equilibrium with ML noise correction.
    - ask_bid_overlap_score from matched_pairs table
    - SDEV midpoint from ask/bid distributions
    - overasking_pct = (listing_price - sdev_mid) / listing_price
    - calibration_mape from the pinned serving model's official test metric
    """
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    listing_price = float(prop.price or 0)
    area_m2 = float(prop.area_m2 or 0)
    district = prop.district
    prop_type = prop.property_type or "apartment"

    if area_m2 <= 0 or listing_price <= 0:
        raise HTTPException(status_code=400, detail="Property must have valid price and area")

    # Run SDEV for this property's cluster
    engine = SDEVEngine(db)
    sdev = engine.run(
        district=district,
        area_m2=area_m2,
        bedrooms=int(prop.bedrooms or 2),
        asset_type=prop_type,
    )

    # Query matched_pairs for buyer match count
    buyer_matches = db.query(MatchedPair).filter(
        MatchedPair.listing_id == property_id,
        MatchedPair.is_potential_match == True,
    ).count()

    # Similar listings in same cluster
    area_b = _area_band(area_m2)
    similar_count = db.query(Property).filter(
        Property.district == district,
        Property.property_type == prop_type,
        Property.record_status != "archived",
        Property.price > 0,
    ).count()

    # Compute overasking_pct
    sdev_mid = float(sdev.estimated_mid_price) if sdev.status == "ESTIMATED" else listing_price
    overasking_pct = ((listing_price - sdev_mid) / listing_price * 100) if listing_price > 0 else 0

    # Transaction equivalent range: noise-corrected
    if sdev.status == "ESTIMATED":
        # ML noise correction: properties near overlap zone → price likely accurate
        # Properties far from overlap → listing likely overstated
        overlap_score = float(sdev.ask_bid_overlap_score)
        correction_factor = max(0, 1 - overasking_pct / 100 * (1 - overlap_score))
        correction_factor = min(1.0, correction_factor)

        low_price = int(sdev.acceptable_low)
        mid_price = int(sdev_mid * correction_factor + sdev_mid * (1 - correction_factor))
        high_price = int(sdev.acceptable_high)
    else:
        # Fallback: ML model noise correction only
        overlap_score = 0.5
        correction_factor = max(0, 1 - abs(overasking_pct) / 100 * (1 - overlap_score))
        correction_factor = min(1.0, correction_factor)
        mid_price = int(listing_price * correction_factor)
        low_price = int(mid_price * 0.92)
        high_price = int(mid_price * 1.08)

    calibration = serving_calibration_metric()

    return {
        "status": "success",
        "property_id": property_id,
        "listing_price": listing_price,
        "listing_price_vnd": _vnd(listing_price),
        "transaction_equivalent_low": low_price,
        "transaction_equivalent_mid": mid_price,
        "transaction_equivalent_high": high_price,
        "transaction_equivalent_low_vnd": _vnd(low_price),
        "transaction_equivalent_mid_vnd": _vnd(mid_price),
        "transaction_equivalent_high_vnd": _vnd(high_price),
        "confidence": round(float(sdev.acceptance_score) if sdev.status == "ESTIMATED" else 0.5, 3),
        "overasking_pct": round(overasking_pct, 2),
        "market_acceptable_price": mid_price,
        "market_acceptable_price_vnd": _vnd(mid_price),
        "derivation_method": "sdev_noise_correction",
        "ask_bid_overlap_score": float(sdev.ask_bid_overlap_score) if sdev.status == "ESTIMATED" else 0.5,
        "buyer_matches": buyer_matches,
        "similar_listings": similar_count,
        "calibration_mape_pct": calibration["mape_pct"],
        "calibration_model_version": calibration["model_version"],
        "calibration_metric_name": calibration["metric_name"],
        "calibration_metric_source": calibration["source"],
        "sdev_status": sdev.status,
        "sdev_reason": sdev.reason,
        "cluster": {
            "district": sdev.cluster_district if sdev.status == "ESTIMATED" else district,
            "area_band": sdev.cluster_area_band if sdev.status == "ESTIMATED" else area_b,
            "bedrooms": int(prop.bedrooms or 2),
        },
        "disclaimer": (
            "Derived from supply-demand asymmetry analysis. "
            "NOT a prediction of actual transaction price. "
            "Use for market analysis only."
        ),
    }
