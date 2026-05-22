#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supply-demand matched pairs — populate matched_pairs table.
Dùng để compute market acceptable price cho từng listing.
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.database import SessionLocal
from src.backend.models import Property, BuyerRequirement, MatchedPair


def run():
    db = SessionLocal()

    # Load listings
    listings = db.query(Property).filter(
        Property.record_status != "archived",
        Property.price > 0,
    ).all()

    # Load buyers
    buyers = db.query(BuyerRequirement).filter(
        BuyerRequirement.is_active == True,
    ).all()

    print(f"Matching {len(listings)} listings with {len(buyers)} buyer requirements...")

    # Clear existing pairs
    db.query(MatchedPair).delete()

    total_pairs = 0
    for listing in listings:
        for buyer in buyers:
            # Basic matching filters
            if listing.district != buyer.district:
                continue
            if listing.property_type != buyer.property_type:
                continue

            area = listing.area_m2 or 0
            if area < (buyer.min_area or 0) or area > (buyer.max_area or 999999):
                continue

            price = listing.price or 0
            if price < (buyer.min_budget or 0) or price > (buyer.max_budget or 999999999):
                continue

            # Budget gap: negative = buyer can afford
            budget_gap = price - (buyer.max_budget or 0)

            # Area match score
            if buyer.min_area and buyer.max_area:
                area_in_range = buyer.min_area <= area <= buyer.max_area
                area_match = 1.0 if area_in_range else max(0, 1 - abs(area - (buyer.min_area + buyer.max_area) / 2) / (buyer.max_area - buyer.min_area + 1))
            else:
                area_match = 0.5

            # Location match
            location_match = 1.0 if listing.district == buyer.district else 0.0

            # Feature match
            bedroom_match = 1.0
            lb = listing.bedrooms
            bb = buyer.bedrooms
            if lb and bb:
                try:
                    bedroom_match = 1.0 - abs(int(lb) - int(bb)) * 0.2
                except (ValueError, TypeError):
                    pass

            feature_match = max(0, min(1, (location_match + area_match + bedroom_match) / 3))

            # Overlap score
            overlap_score = max(0, min(1, (1 - abs(budget_gap) / price) * feature_match)) if price > 0 else 0

            # Is potential match?
            is_match = overlap_score > 0.3 and budget_gap < (buyer.max_budget or 0) * 0.15

            pair = MatchedPair(
                listing_id=listing.id,
                request_id=buyer.id,
                location_match_score=round(location_match, 3),
                area_match_score=round(area_match, 3),
                budget_gap=round(budget_gap, -6),
                feature_match_score=round(feature_match, 3),
                is_potential_match=is_match,
                overlap_score=round(overlap_score, 3),
                match_group=f"{listing.id}_{buyer.id}",
            )
            db.add(pair)
            total_pairs += 1

        if total_pairs % 10000 == 0 and total_pairs > 0:
            db.commit()
            print(f"  Committed {total_pairs} pairs...")

    db.commit()
    print(f"[OK] Generated {total_pairs} matched pairs")
    db.close()


if __name__ == "__main__":
    run()
