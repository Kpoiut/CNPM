"""The canonical PostgreSQL schema must include every live domain table."""

from pathlib import Path

from src.backend.database import Base
from src.backend.model_registry import load_all_models


PROJECT_ROOT = Path(__file__).resolve().parents[2]


CANONICAL_TABLES = {
    "properties",
    "dataset_versions",
    "training_runs",
    "training_metrics",
    "model_versions",
    "audit_logs",
    "valuation_runs",
    "provenance_chains",
    "collection_sources",
    "buyer_requirements",
    "matched_pairs",
    "expert_ratings",
    "expert_properties",
    "auth_accounts",
    "auth_account_sessions",
    "auth_refresh_tokens",
    "reputation_ledger",
    "claims",
    "claim_evidence",
    "community_comments",
    "challenges",
    "claim_court_sessions",
    "prediction_bonds",
    "coalition_flags",
    "ai_training_candidates",
    "appeal_cases",
    "private_insights",
    "migration_rejected_rows",
}


def test_registry_contains_only_the_live_tables():
    load_all_models()

    assert set(Base.metadata.tables) == CANONICAL_TABLES
    assert "properties_backup" not in Base.metadata.tables
    assert "valuation_runs_new" not in Base.metadata.tables
    assert "predictions" not in Base.metadata.tables
    assert "prediction_history" not in Base.metadata.tables


def test_property_declares_verification_status_once():
    source = (PROJECT_ROOT / "src" / "backend" / "models.py").read_text(encoding="utf-8")
    property_source = source.split("class Property(Base):", 1)[1].split(
        "class DatasetVersion(Base):", 1
    )[0]

    assert property_source.count("verification_status = Column(") == 1
