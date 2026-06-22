from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_backend_image_includes_ci_reference_seed_script():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()

    assert "COPY scripts ./scripts" in dockerfile
    assert "scripts/quality/*" in dockerignore
    assert "!scripts/quality/seed_ci_reference_data.py" in dockerignore
    assert "scripts/quality" not in dockerignore
