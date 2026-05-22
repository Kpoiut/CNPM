"""
Canonical Property Type Taxonomy — Single Source of Truth.

Replaces ad-hoc string constants scattered across engine.py, orchestrator.py,
and valuation.py. ALL type comparisons and mappings go through this module.

Design basis: RICS AVM Standard hedonic model requirement that each canonical
type has distinct value drivers and comparable pools.

5 Canonical Types:
    LAND       — Đất nền: value = land use rights only, geometry-driven
    TOWNHOUSE  — Nhà phố: value = land + structure, access-driven
    APARTMENT  — Chung cư: value = floor area + view + orientation
    VILLA      — Biệt thự: value = land + premium structure + privacy
    HOUSE      — Nhà riêng: value = land + structure (aged/traditional)
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Set


class PropertyType(str, Enum):
    LAND       = "LAND"       # Đất nền
    TOWNHOUSE  = "TOWNHOUSE"  # Nhà phố / liền kề / shophouse
    APARTMENT  = "APARTMENT"  # Chung cư / condotel / studio / penthouse
    VILLA      = "VILLA"      # Biệt thự
    HOUSE      = "HOUSE"      # Nhà riêng


# ─── Frontend / API type → Canonical ────────────────────────────────────────
_FRONTEND_TO_CANONICAL: Dict[str, PropertyType] = {
    # LAND variants
    "LAND_URBAN":    PropertyType.LAND,
    "LAND_SUBURBAN": PropertyType.LAND,
    "LAND_PROJECT":  PropertyType.LAND,
    # TOWNHOUSE variants
    "TOWNHOUSE":     PropertyType.TOWNHOUSE,
    "SHOPHOUSE":     PropertyType.TOWNHOUSE,
    # APARTMENT variants
    "APARTMENT":     PropertyType.APARTMENT,
    "STUDIO":        PropertyType.APARTMENT,
    "PENTHOUSE":     PropertyType.APARTMENT,
    "DUPLEX":        PropertyType.APARTMENT,
    # Single types
    "VILLA":         PropertyType.VILLA,
    "HOUSE":         PropertyType.HOUSE,
}


# ─── Canonical → DB lowercase string ─────────────────────────────────────────
_CANONICAL_TO_DB: Dict[PropertyType, str] = {
    PropertyType.LAND:      "land",
    PropertyType.TOWNHOUSE: "townhouse",
    PropertyType.APARTMENT: "apartment",
    PropertyType.VILLA:     "villa",
    PropertyType.HOUSE:     "house",
}
_DB_TO_CANONICAL: Dict[str, PropertyType] = {v: k for k, v in _CANONICAL_TO_DB.items()}


# ─── Canonical → Config price category ───────────────────────────────────────
_CANONICAL_TO_PRICE_CAT: Dict[PropertyType, str] = {
    PropertyType.LAND:      "LAND",
    PropertyType.TOWNHOUSE: "TOWNHOUSE",
    PropertyType.APARTMENT: "APARTMENT",
    PropertyType.VILLA:     "VILLA",
    PropertyType.HOUSE:     "HOUSE",
}
_PRICE_CAT_TO_CANONICAL: Dict[str, PropertyType] = {v: k for k, v in _CANONICAL_TO_PRICE_CAT.items()}


# ─── Per-type feature zero-mask ─────────────────────────────────────────────
# Features that are ZEROED OUT for each property type.
# Based on RICS AVM hedonic model research: noisy features reduce accuracy.
TYPE_ZERO_MASK: Dict[str, Set[str]] = {
    "LAND": {
        # No building structure
        "bedrooms", "bathrooms", "floor_count", "construction_year",
        "structure_grade", "facade_count",
        # No apartment infrastructure
        "apt_floor", "view_type", "elevator_count", "elevator_distance",
        "trash_room_distance", "core_distance", "block_name",
        "sunlight_exposure", "ventilation_score", "layout_score",
        "noise_inside_db", "management_fee",
        # frontage_m and depth ARE relevant for land geometry
    },
    "TOWNHOUSE": {
        # No apartment infrastructure
        "apt_floor", "elevator_count", "elevator_distance",
        "trash_room_distance", "core_distance", "block_name",
        "view_type", "management_fee",
        # No raw land geometry concepts
        "depth_min_m", "depth_max_m", "taper_type",
        "nö_hậu_score", "thóp_hậu_score", "irregularity_score",
    },
    "APARTMENT": {
        # No land parcel features
        "frontage_m", "depth_min_m", "depth_max_m", "taper_type",
        "nö_hậu_score", "thóp_hậu_score", "irregularity_score",
        "corner_plot", "far_max",
        # No building structure (strata unit)
        "construction_year", "facade_count", "structure_grade",
        # No direct access — determined by building
        "road_class", "alley_width_m",
    },
    "VILLA": {
        # No apartment infrastructure
        "apt_floor", "elevator_count", "elevator_distance",
        "trash_room_distance", "core_distance", "block_name", "management_fee",
        # No raw land geometry (but frontage IS relevant)
        "taper_type", "irregularity_score",
        # bedrooms/bathrooms/floor_count ARE villa-relevant
    },
    "HOUSE": {
        # Same exclusions as TOWNHOUSE (structurally similar)
        "apt_floor", "elevator_count", "elevator_distance",
        "trash_room_distance", "core_distance", "block_name",
        "view_type", "management_fee",
        "depth_min_m", "depth_max_m", "taper_type",
        "nö_hậu_score", "thóp_hậu_score", "irregularity_score",
    },
}


# ─── Per-type adjustment applies-to ─────────────────────────────────────────
# Which adjustment factors apply to each type.
# Format: {"ADJ_CODE": {PropertyType, ...}}
ADJUSTMENT_TYPE_MAP: Dict[str, Set[str]] = {
    # Access — not for apartments (strata units don't have alley access)
    "ACCESS_MAIN_STREET":   {"TOWNHOUSE", "HOUSE", "VILLA"},
    "ACCESS_ALLEY_5M":      {"TOWNHOUSE", "HOUSE", "LAND"},
    "ACCESS_ALLEY_3M":      {"TOWNHOUSE", "HOUSE", "LAND"},
    "ACCESS_ALLEY_2M":      {"TOWNHOUSE", "HOUSE", "LAND"},
    "ACCESS_ALLEY_1M":      {"TOWNHOUSE", "HOUSE", "LAND"},
    "ACCESS_DEAD_END":      {"TOWNHOUSE", "HOUSE", "LAND"},
    # Geometry — only for land
    "GEOM_NÖHẬU":          {"LAND"},
    "GEOM_THOP_HAU":        {"LAND"},
    "GEOM_THOP_HAU_SEVERE": {"LAND"},
    "GEOM_IRREGULAR":       {"LAND"},
    "GEOM_CORNER_PLOT":     {"LAND"},
    # Apartment-specific
    "FLOOR_PREMIUM":        {"APARTMENT"},
    "VIEW_PREMIUM":         {"APARTMENT"},
    "VIEW_CITY":            {"APARTMENT"},
    "VIEW_RIVER":           {"APARTMENT"},
    "VIEW_PARK":            {"APARTMENT"},
    "DIST_METRO_500M":      {"APARTMENT"},   # Metro primarily drives apartment premium
    "AMENITY_POOL":         {"APARTMENT", "VILLA"},
    "AMENITY_GYM":          {"APARTMENT"},
    "ELEVATOR_COUNT":       {"APARTMENT"},
    # Building — for houses with structure
    "BLDG_NEW_5Y":          {"TOWNHOUSE", "VILLA", "HOUSE"},
    "BLDG_OLD_20Y":         {"TOWNHOUSE", "VILLA", "HOUSE"},
    "BLDG_FLOORS_EXCEED":   {"TOWNHOUSE", "VILLA", "HOUSE"},
    "BLDG_RENOVATED":       {"TOWNHOUSE", "VILLA", "HOUSE"},
    "BLDG_FURNISHED":       {"TOWNHOUSE", "VILLA", "HOUSE"},
}


# ─── Convenience helpers ──────────────────────────────────────────────────────

def to_canonical(raw: str) -> PropertyType:
    """Normalize any legacy/API/DB type string to canonical PropertyType."""
    if isinstance(raw, PropertyType):
        return raw
    if not raw:
        return PropertyType.TOWNHOUSE  # safe default
    upper = str(raw).strip().upper().replace(" ", "_").replace("-", "_")
    result = _FRONTEND_TO_CANONICAL.get(upper)
    if result:
        return result
    # Try partial match
    for key, val in _FRONTEND_TO_CANONICAL.items():
        if upper in key or key in upper:
            return val
    return PropertyType.TOWNHOUSE  # safe fallback


def to_db(raw: str) -> str:
    """Convert any type string to the lowercase DB column value."""
    return _CANONICAL_TO_DB[to_canonical(raw)]


def to_price_category(raw: str) -> str:
    """Convert any type string to the config price category key."""
    return _CANONICAL_TO_PRICE_CAT[to_canonical(raw)]


def is_applicable_factor(factor_code: str, property_type: str) -> bool:
    """Check if an adjustment factor applies to a given property type."""
    if factor_code not in ADJUSTMENT_TYPE_MAP:
        return True  # Unknown factors apply to all (conservative)
    canonical = to_canonical(property_type).value
    return canonical in ADJUSTMENT_TYPE_MAP[factor_code]


def get_zero_mask(property_type: str) -> Set[str]:
    """Get the set of features to zero out for a given property type."""
    return TYPE_ZERO_MASK.get(to_canonical(property_type).value, set())
