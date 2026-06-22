"""Ba kịch bản demo production cho ML model release gate.

Happy path
    ML-PROD-H01: ACTIVE_MODEL trỏ đúng artifact/metadata có metric serving.

Failure path
    ML-PROD-F01: candidate mới hơn nhưng MAPE kém không được tự ghi đè active.
    ML-PROD-F02: metadata thiếu metric hoặc artifact thiếu phải làm test fail.

Hướng xử lý
    Giữ model active, xác minh dataset checksum + exact holdout, retrain và chỉ
    promote khi MAPE/MAE/R2 cùng policy đạt gate. Không so 16.09 với 31-44 như
    cùng một run nếu split/dataset khác nhau.

Evidence
    ``pytest tests/production/test_ml_release_gate.py -vv``; metadata và pointer
    được lưu cùng artifact CI.
"""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_ROOT / "models"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _primary_metrics(metadata: dict) -> dict:
    best_model = metadata["best_model"]
    return metadata["all_results"][best_model]


def test_ml_prod_h01_active_pointer_matches_verified_artifacts():
    pointer = _load_json(MODEL_DIR / "ACTIVE_MODEL.json")
    model_path = MODEL_DIR / pointer["model_file"]
    metadata_path = MODEL_DIR / pointer["metadata_file"]

    assert pointer["stamp"] in model_path.name
    assert pointer["stamp"] in metadata_path.name
    assert model_path.is_file() and model_path.stat().st_size > 0
    assert metadata_path.is_file()

    metrics = _primary_metrics(_load_json(metadata_path))
    assert 0 < metrics["test_mape"] < 100
    assert metrics["test_mae"] > 0
    assert -1 <= metrics["test_r2"] <= 1
    assert metrics["n_test"] >= 100


def test_ml_prod_f01_worse_latest_candidate_does_not_replace_active():
    pointer = _load_json(MODEL_DIR / "ACTIVE_MODEL.json")
    active_metrics = _primary_metrics(_load_json(MODEL_DIR / pointer["metadata_file"]))
    candidates = sorted(MODEL_DIR.glob("metadata_*.json"))
    latest_path = candidates[-1]
    latest_metrics = _primary_metrics(_load_json(latest_path))

    assert latest_path.stem.removeprefix("metadata_") != pointer["stamp"]
    assert latest_metrics["test_mape"] > active_metrics["test_mape"]
    assert pointer["model_file"] == f"model_{pointer['stamp']}.pkl"
