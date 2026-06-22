import json
import pickle

import pytest
from fastapi import HTTPException

from src.backend.deps import _load_active_model


def test_active_model_loader_uses_exact_pointer_artifact(tmp_path):
    artifact = tmp_path / "model_20260621_120000.pkl"
    with artifact.open("wb") as handle:
        pickle.dump({"model": "verified-model", "metadata": {}, "version": "20260621_120000"}, handle)
    (tmp_path / "ACTIVE_MODEL.json").write_text(
        json.dumps({"stamp": "20260621_120000", "model_file": artifact.name}),
        encoding="utf-8",
    )

    loaded = _load_active_model(tmp_path)

    assert loaded["model"] == "verified-model"
    assert loaded["model_version"] == "20260621_120000"


@pytest.mark.parametrize(
    "pointer",
    [
        None,
        {"stamp": "20260621_120000", "model_file": "model_missing.pkl"},
        {"stamp": "20260621_120000", "model_file": "../model_20260621_120000.pkl"},
        {"stamp": "20260621_120000", "model_file": "model_20260621_130000.pkl"},
    ],
)
def test_active_model_loader_fails_closed_instead_of_selecting_latest_candidate(tmp_path, pointer):
    with (tmp_path / "model_20260621_999999.pkl").open("wb") as handle:
        pickle.dump({"model": "worse-latest-candidate"}, handle)
    if pointer is not None:
        (tmp_path / "ACTIVE_MODEL.json").write_text(json.dumps(pointer), encoding="utf-8")

    with pytest.raises(HTTPException) as error:
        _load_active_model(tmp_path)

    assert error.value.status_code == 503
    assert "ACTIVE_MODEL" in error.value.detail
