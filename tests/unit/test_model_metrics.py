import json
from pathlib import Path

from src.backend.model_metrics import (
    build_metric_provenance,
    load_model_metrics,
    select_best_verified_metric,
    select_latest_metric,
    select_serving_metric,
)
from src.backend.deps import _build_model_cache


def _write_metadata(path, *, best_model, test_mae, test_mape, test_r2, trained_at):
    path.write_text(
        json.dumps(
            {
                "best_model": best_model,
                "trained_at": trained_at,
                "test_size": 485,
                "train_size": 2261,
                "all_results": {
                    best_model: {
                        "test_mae": test_mae,
                        "test_mape": test_mape,
                        "test_r2": test_r2,
                        "test_median_ae": test_mae / 2,
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_model_metrics_distinguish_latest_from_best_verified(tmp_path):
    _write_metadata(
        tmp_path / "metadata_20260504_144753.json",
        best_model="ReliabilityAwareGradientBoosting",
        test_mae=776_510_800.7012783,
        test_mape=16.08643446790566,
        test_r2=0.8448682378464769,
        trained_at="2026-05-04T14:47:53.841501",
    )
    _write_metadata(
        tmp_path / "metadata_20260523_003819.json",
        best_model="ReliabilityAwareGradientBoosting",
        test_mae=3_346_239_287.077247,
        test_mape=42.420794145088315,
        test_r2=0.6355,
        trained_at="2026-05-23T00:38:19",
    )

    metrics = load_model_metrics([tmp_path])

    assert select_latest_metric(metrics).stamp == "20260523_003819"
    assert select_best_verified_metric(metrics).stamp == "20260504_144753"


def test_metric_provenance_reports_gap_in_percentage_points(tmp_path):
    _write_metadata(
        tmp_path / "metadata_20260504_144753.json",
        best_model="ReliabilityAwareGradientBoosting",
        test_mae=776_510_800.7012783,
        test_mape=16.08643446790566,
        test_r2=0.8448682378464769,
        trained_at="2026-05-04T14:47:53.841501",
    )
    _write_metadata(
        tmp_path / "metadata_20260514_110830.json",
        best_model="ReliabilityAwareGradientBoosting",
        test_mae=3_821_908_079.1609454,
        test_mape=45.175909626649336,
        test_r2=0.57,
        trained_at="2026-05-14T11:08:30",
    )

    provenance = build_metric_provenance([tmp_path])

    assert provenance["best_verified"]["stamp"] == "20260504_144753"
    assert provenance["latest"]["stamp"] == "20260514_110830"
    assert provenance["latest_is_best_verified"] is False
    assert provenance["mape_gap_percentage_points"] == 29.09
    assert "latest retrain is not the best verified model" in provenance["warning"]


def test_metric_provenance_respects_active_model_pointer(tmp_path):
    _write_metadata(
        tmp_path / "metadata_20260503_185414.json",
        best_model="ReliabilityAwareGradientBoosting",
        test_mae=804_022_708.446306,
        test_mape=14.1962041178795,
        test_r2=0.7647801985228266,
        trained_at="2026-05-03T18:54:14",
    )
    _write_metadata(
        tmp_path / "metadata_20260504_144753.json",
        best_model="ReliabilityAwareGradientBoosting",
        test_mae=776_510_800.7012783,
        test_mape=16.08643446790566,
        test_r2=0.8448682378464769,
        trained_at="2026-05-04T14:47:53.841501",
    )
    _write_metadata(
        tmp_path / "metadata_20260523_003819.json",
        best_model="ReliabilityAwareGradientBoosting",
        test_mae=3_346_239_287.077247,
        test_mape=42.420794145088315,
        test_r2=0.6355,
        trained_at="2026-05-23T00:38:19",
    )
    (tmp_path / "ACTIVE_MODEL.json").write_text(
        json.dumps({"stamp": "20260504_144753", "model_file": "model_20260504_144753.pkl"}),
        encoding="utf-8",
    )

    metrics = load_model_metrics([tmp_path])
    provenance = build_metric_provenance([tmp_path])

    assert select_serving_metric(metrics, [tmp_path]).stamp == "20260504_144753"
    assert provenance["serving"]["stamp"] == "20260504_144753"
    assert provenance["serving"]["test_mape"] == 16.086434
    assert provenance["best_verified"]["stamp"] == "20260503_185414"
    assert provenance["best_verified"]["test_mape"] == 14.196204
    assert provenance["serving_source"] == "ACTIVE_MODEL.json"
    assert "not the lowest-MAPE historical snapshot" in provenance["serving_warning"]


def test_model_cache_exposes_artifact_version_for_prediction_provenance():
    cache = _build_model_cache({
        "version": "20260504_144753",
        "best_model_name": "ReliabilityAwareGradientBoosting",
        "metadata": {
            "all_results": {
                "ReliabilityAwareGradientBoosting": {
                    "test_mape": 16.08643446790566,
                }
            }
        },
    })

    assert cache["model_version"] == "20260504_144753"
    assert cache["metrics"]["test_mape"] == 16.08643446790566


def test_legacy_predict_persists_serving_provenance_instead_of_latest_db_model():
    source = (Path(__file__).resolve().parents[2] / "src" / "backend" / "main.py").read_text(encoding="utf-8")
    predict_region = source.split("def predict_price", 1)[1].split("# --- Property Management Endpoints", 1)[0]

    assert "_resolve_serving_model_version_info(db, model_data)" in predict_region
    assert "_get_prediction_pool_stats(db)" in predict_region
    assert "ValuationRun(" in predict_region
    assert 'source_endpoint="api_predict"' in predict_region
    assert "PredictionHistory(" not in predict_region
    assert "Prediction(" not in predict_region
    assert "db.query(ModelVersion).order_by(ModelVersion.trained_at.desc()).first()" not in predict_region


def test_backend_dashboard_uses_serving_model_not_latest_candidate():
    source = (Path(__file__).resolve().parents[2] / "src" / "backend" / "main.py").read_text(encoding="utf-8")
    dashboard_region = source.split("def get_dashboard_stats", 1)[1].split("@app.get(\"/api/dataset/stats\"", 1)[0]

    assert "serving_model" in dashboard_region
    assert "build_metric_provenance()" in dashboard_region
    assert "latest_model = db.query(ModelVersion).order_by(ModelVersion.trained_at.desc()).first()" not in dashboard_region


def test_v2_engine_version_reports_serving_model_not_latest_candidate():
    source = (
        Path(__file__).resolve().parents[2] / "src" / "backend" / "api_v2" / "valuation.py"
    ).read_text(encoding="utf-8")
    engine_region = source.split("def engine_version", 1)[1].split("@api_router.get(\"/valuation/runs\")", 1)[0]

    assert "serving_model" in engine_region
    assert "build_metric_provenance()" in engine_region
    assert "order_by(ModelVersion.trained_at.desc()).first()" not in engine_region


def test_explain_calibration_uses_serving_model_metadata():
    source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "backend"
        / "api_v2"
        / "explainability.py"
    ).read_text(encoding="utf-8")
    serving_helper = source.split("def _get_serving_model_metadata", 1)[1].split(
        "def _load_pipeline", 1
    )[0]
    calibration_region = source.split("def explain_calibration", 1)[1].split(
        '@api_router.get("/explain/model-compare"', 1
    )[0]

    assert "_get_latest_model_metadata()" in serving_helper
    assert "_get_serving_model_metadata()" not in serving_helper
    assert "_get_serving_model_metadata()" in calibration_region
    assert "_get_latest_model_metadata()" not in calibration_region
    assert '"model_version": metadata.get("model_version"' in calibration_region
    assert '"metric_source": metadata.get("serving_source"' in calibration_region
