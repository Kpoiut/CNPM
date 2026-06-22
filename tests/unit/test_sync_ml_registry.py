import json

from scripts.sync_ml_registry import metadata_to_lineage


def test_metadata_is_normalized_into_dataset_run_model_and_metrics(tmp_path):
    metadata = {
        "best_model": "ReliabilityAwareGradientBoosting",
        "trained_at": "2026-05-04T14:47:53",
        "train_size": 2261,
        "validation_size": 485,
        "test_size": 485,
        "split_manifest": {
            "record_order": "Property.id ASC",
            "random_state": 42,
            "dataset_sha256": "a" * 64,
            "train_sha256": "b" * 64,
            "validation_sha256": "c" * 64,
            "test_sha256": "d" * 64,
        },
        "all_results": {
            "ReliabilityAwareGradientBoosting": {
                "test_mae": 776_510_800.7,
                "test_mape": 16.0864,
                "test_rmse": 1_391_186_310.3,
                "test_r2": 0.8448,
            }
        },
    }
    path = tmp_path / "metadata_20260504_144753.json"
    path.write_text(json.dumps(metadata), encoding="utf-8")

    lineage = metadata_to_lineage(path, active_stamp="20260504_144753")

    assert lineage["dataset"]["record_count"] == 3231
    assert lineage["dataset"]["checksum_sha256"] == "a" * 64
    assert lineage["training_run"]["run_version"] == "20260504_144753"
    run_notes = json.loads(lineage["training_run"]["notes"])
    assert run_notes["test_sha256"] == "d" * 64
    assert lineage["model"]["mape"] == 16.0864
    assert lineage["model"]["is_active"] is True
    assert {metric["name"] for metric in lineage["metrics"]} == {"mae", "mape", "rmse", "r2"}
