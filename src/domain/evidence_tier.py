"""Canonical evidence-tier policy used across training, valuation and UI.

Production standard:
- E5 is the strongest evidence tier.
- E1 is the weakest evidence tier.

Do not redefine E1..E5 weights in feature-specific engines. Import this module
instead so model training, comparable ranking and confidence scoring stay
consistent.
"""

from __future__ import annotations

from typing import Mapping


VALID_EVIDENCE_TIERS = ("E1", "E2", "E3", "E4", "E5")
LOWEST_EVIDENCE_TIER = "E1"
HIGHEST_EVIDENCE_TIER = "E5"

DEFAULT_EVIDENCE_SCORE = 0.30
DEFAULT_EVIDENCE_WEIGHT = 0.30
DEFAULT_CONFIDENCE_CAP = 6.0

EVIDENCE_SCORE: Mapping[str, float] = {
    "E1": 0.15,
    "E2": 0.35,
    "E3": 0.65,
    "E4": 0.85,
    "E5": 1.00,
}

EVIDENCE_WEIGHT: Mapping[str, float] = {
    "E1": 0.20,
    "E2": 0.45,
    "E3": 0.65,
    "E4": 0.85,
    "E5": 1.00,
}

CONFIDENCE_CAP: Mapping[str, float] = {
    "E1": 4.0,
    "E2": 6.5,
    "E3": 8.0,
    "E4": 9.0,
    "E5": 10.0,
}

ANCHOR_TIERS = frozenset({"E4", "E5"})
HIGH_CONFIDENCE_TIERS = ANCHOR_TIERS


def normalize_evidence_tier(tier: str | None) -> str | None:
    """Return a valid tier or None for unknown/missing input."""
    value = (tier or "").strip().upper()
    return value if value in VALID_EVIDENCE_TIERS else None


def evidence_score(tier: str | None, default: float = DEFAULT_EVIDENCE_SCORE) -> float:
    """Comparable and ranking score; E5 is strongest."""
    normalized = normalize_evidence_tier(tier)
    return EVIDENCE_SCORE.get(normalized, default)


def evidence_weight(tier: str | None, default: float = DEFAULT_EVIDENCE_WEIGHT) -> float:
    """Training and confidence weight; E5 carries the highest weight."""
    normalized = normalize_evidence_tier(tier)
    return EVIDENCE_WEIGHT.get(normalized, default)


def evidence_anchor_strength(tier: str | None, default: float = DEFAULT_EVIDENCE_SCORE) -> float:
    """Market-anchor strength. Kept separate for readability."""
    return evidence_score(tier, default=default)


def confidence_cap(tier: str | None, default: float = DEFAULT_CONFIDENCE_CAP) -> float:
    """Maximum confidence allowed by evidence tier."""
    normalized = normalize_evidence_tier(tier)
    return CONFIDENCE_CAP.get(normalized, default)


def is_anchor_tier(tier: str | None) -> bool:
    """Return True for tiers strong enough to anchor market valuation."""
    return normalize_evidence_tier(tier) in ANCHOR_TIERS


def evidence_sort_key(tier: str | None) -> float:
    """Ascending sort key that places the strongest evidence first."""
    return -evidence_score(tier)


def anchor_share(tier_counts: Mapping[str, int], total: int) -> float:
    """Share of E4/E5 records in a comparable/training pool."""
    if total <= 0:
        return 0.0
    return sum(int(tier_counts.get(tier, 0) or 0) for tier in ANCHOR_TIERS) / total
