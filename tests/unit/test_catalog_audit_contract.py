from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_catalog_audit_exposes_database_value_and_count_mode():
    source = (PROJECT_ROOT / "scripts" / "audit_postgres_catalog.py").read_text(
        encoding="utf-8"
    )

    assert "--exact-counts" in source
    assert '"row_count_mode"' in source
    assert '"primary_key_columns"' in source
    assert '"index_count"' in source
    assert '"total_bytes"' in source
    assert '"purpose"' in source
    assert '"data_state"' in source
    assert '"accounts"' in source
    assert "management.account_registry" in source


def test_ci_requests_exact_catalog_evidence():
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "scripts/audit_postgres_catalog.py --exact-counts" in workflow
