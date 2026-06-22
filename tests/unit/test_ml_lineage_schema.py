from src.backend.database import Base
from src.backend.model_registry import load_all_models


def test_ml_lineage_tables_are_part_of_canonical_metadata():
    load_all_models()

    assert {"dataset_versions", "training_runs", "training_metrics"} <= set(Base.metadata.tables)


def test_model_version_records_training_origin_and_improvement():
    load_all_models()
    columns = Base.metadata.tables["model_versions"].columns

    assert {
        "training_run_id",
        "parent_model_version_id",
        "mape",
        "status",
        "is_active",
        "improvement_mape_pct_points",
        "metadata_path",
        "artifact_sha256",
    } <= set(columns.keys())


def test_valuation_run_is_the_single_prediction_history_and_feedback_source():
    load_all_models()
    columns = Base.metadata.tables["valuation_runs"].columns

    assert columns["request_id"].type.length >= 80
    assert {
        "request_id",
        "source_endpoint",
        "account_id",
        "model_version_id",
        "model_version_snapshot",
        "input_features_json",
        "result_json",
        "request_latency_ms",
        "actual_price_vnd",
        "actual_price_recorded_at",
        "feedback_by_account_id",
        "feedback_verification_status",
        "training_eligible",
        "training_exclusion_reason",
        "training_run_id",
        "training_used_at",
    } <= set(columns.keys())

    assert "predictions" not in Base.metadata.tables
    assert "prediction_history" not in Base.metadata.tables
