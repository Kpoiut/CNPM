import json
from pathlib import Path

from src.backend.model_metrics import serving_calibration_metric


def _write_metadata(path: Path, *, test_mape: float, test_mae: float) -> None:
    path.write_text(
        json.dumps(
            {
                "best_model": "ReliabilityAwareGradientBoosting",
                "trained_at": "2026-05-04T14:47:53.841501",
                "test_size": 485,
                "train_size": 2261,
                "all_results": {
                    "ReliabilityAwareGradientBoosting": {
                        "test_mape": test_mape,
                        "test_mae": test_mae,
                        "test_r2": 0.8448682378464769,
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_serving_calibration_uses_active_official_mape(tmp_path):
    _write_metadata(
        tmp_path / "metadata_20260504_144753.json",
        test_mape=16.08643446790566,
        test_mae=776_510_800.7012783,
    )
    _write_metadata(
        tmp_path / "metadata_20260621_162930.json",
        test_mape=44.37773977125798,
        test_mae=3_463_138_218.6765594,
    )
    (tmp_path / "ACTIVE_MODEL.json").write_text(
        json.dumps({"stamp": "20260504_144753"}),
        encoding="utf-8",
    )

    metric = serving_calibration_metric([tmp_path])

    assert metric == {
        "model_version": "20260504_144753",
        "metric_name": "official_test_mape",
        "mape_pct": 16.086434,
        "source": "ACTIVE_MODEL.json",
    }


def test_transaction_price_does_not_derive_mape_from_mae():
    source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "backend"
        / "api_v2"
        / "transaction_price.py"
    ).read_text(encoding="utf-8")

    assert "serving_calibration_metric()" in source
    assert '"calibration_model_version"' in source
    assert '"calibration_metric_source"' in source
    assert "test_mae / median_price" not in source
    assert "metadata_*.json" not in source
