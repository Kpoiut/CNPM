from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_retrain_uses_canonical_postgres_lineage_without_duplicate_registry_write():
    source = (PROJECT_ROOT / "scripts" / "retrain_v2.py").read_text(encoding="utf-8")

    assert ".env.postgres.local" in source
    assert "DATABASE_URL" in source
    assert "sync_registry" in source
    assert "registry.register_version" not in source
