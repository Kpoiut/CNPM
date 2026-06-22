from pathlib import Path

from src.domain.evidence_tier import (
    ANCHOR_TIERS,
    HIGHEST_EVIDENCE_TIER,
    LOWEST_EVIDENCE_TIER,
    anchor_share,
    confidence_cap,
    evidence_score,
    evidence_sort_key,
    evidence_weight,
    is_anchor_tier,
)


def test_evidence_tier_policy_is_e5_highest_e1_lowest():
    assert LOWEST_EVIDENCE_TIER == "E1"
    assert HIGHEST_EVIDENCE_TIER == "E5"
    assert ANCHOR_TIERS == {"E4", "E5"}

    assert evidence_score("E1") < evidence_score("E2") < evidence_score("E3")
    assert evidence_score("E3") < evidence_score("E4") < evidence_score("E5")

    assert evidence_weight("E1") < evidence_weight("E2") < evidence_weight("E3")
    assert evidence_weight("E3") < evidence_weight("E4") < evidence_weight("E5")

    assert confidence_cap("E1") < confidence_cap("E2") < confidence_cap("E3")
    assert confidence_cap("E3") < confidence_cap("E4") < confidence_cap("E5")


def test_evidence_sort_and_anchor_share_use_e4_e5_as_strong_tiers():
    tiers = ["E2", "E5", "E3", "E1", "E4"]

    assert sorted(tiers, key=evidence_sort_key) == ["E5", "E4", "E3", "E2", "E1"]
    assert is_anchor_tier("E5")
    assert is_anchor_tier("E4")
    assert not is_anchor_tier("E2")
    assert anchor_share({"E5": 2, "E4": 1, "E3": 7}, total=10) == 0.3


def test_production_code_does_not_reintroduce_inverse_e1_highest_maps():
    bad_patterns = [
        '"E1": 1.0',
        "'E1': 1.0",
        '"E5": 0.15',
        "'E5': 0.15",
        "E1/E2",
        "E1 first",
    ]
    allowed_files = {
        Path("src/domain/evidence_tier.py"),
    }

    offenders: list[str] = []
    for path in Path("src").rglob("*.py"):
        rel = path.as_posix()
        if Path(rel) in allowed_files:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in bad_patterns:
            if pattern in text:
                offenders.append(f"{rel}: {pattern}")

    assert offenders == []
