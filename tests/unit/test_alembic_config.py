from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_alembic_runtime_files_exist():
    assert (PROJECT_ROOT / "alembic.ini").exists()
    assert (PROJECT_ROOT / "alembic" / "env.py").exists()
    assert (PROJECT_ROOT / "alembic" / "script.py.mako").exists()


def test_initial_revision_declares_postgis_and_model_registry():
    versions = sorted((PROJECT_ROOT / "alembic" / "versions").glob("*.py"))
    assert versions, "expected at least one Alembic revision"

    initial = versions[0].read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS postgis" in initial
    assert "load_all_models()" in initial
    assert "Base.metadata.create_all" in initial
    assert "properties_backup" not in initial
    assert "valuation_runs_new" not in initial


def test_alembic_env_uses_database_url_from_environment():
    env_py = (PROJECT_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")

    assert 'os.getenv("DATABASE_URL")' in env_py
    assert "target_metadata = Base.metadata" in env_py
    assert "load_all_models()" in env_py


def test_canonical_revision_consolidates_prediction_history_and_removes_archives():
    versions = sorted((PROJECT_ROOT / "alembic" / "versions").glob("*0006*.py"))
    assert len(versions) == 1
    canonical = versions[0].read_text(encoding="utf-8")

    assert '"account_id"' in canonical
    assert '"request_id"' in canonical
    assert '"source_endpoint"' in canonical
    assert "training_feedback_candidates" in canonical
    assert "DROP SCHEMA IF EXISTS compatibility CASCADE" in canonical
    assert "DROP SCHEMA IF EXISTS archive_empty CASCADE" in canonical


def test_request_id_revision_keeps_request_id_wide_enough_for_prefixed_lineage_ids():
    versions = sorted((PROJECT_ROOT / "alembic" / "versions").glob("*0007*.py"))
    assert len(versions) == 1
    latest = versions[0].read_text(encoding="utf-8")

    assert "request_id" in latest
    assert "String(80)" in latest or "VARCHAR(80)" in latest


def test_domain_schema_revision_organizes_pgadmin_objects():
    versions = sorted((PROJECT_ROOT / "alembic" / "versions").glob("*0009*.py"))
    assert len(versions) == 1
    latest = versions[0].read_text(encoding="utf-8")

    assert "database_catalog" in latest
    assert "DOMAIN_TABLES" in latest
    assert "public.valuation_runs" in latest
    assert '"ml": ("dataset_versions", "training_runs", "training_metrics", "model_versions")' in latest
    assert '"auth": ("auth_accounts", "auth_account_sessions", "auth_refresh_tokens")' in latest
    assert "operations" in latest


def test_latest_revision_hardens_catalog_and_prediction_history():
    versions = sorted((PROJECT_ROOT / "alembic" / "versions").glob("*0010*.py"))
    assert len(versions) == 1
    latest = versions[0].read_text(encoding="utf-8")

    assert "n_live_tup" in latest
    assert "primary_key_columns" in latest
    assert "foreign_key_count" in latest
    assert "index_count" in latest
    assert "data_state" in latest
    assert "ix_valuation_runs_training_feedback_queue" in latest
    assert "ck_valuation_runs_non_negative_latency" in latest
    assert "ck_valuation_runs_confidence_range" in latest


def test_account_registry_revision_exposes_account_prediction_value():
    versions = sorted((PROJECT_ROOT / "alembic" / "versions").glob("*0011*.py"))
    assert len(versions) == 1
    latest = versions[0].read_text(encoding="utf-8")

    assert "account_registry" in latest
    assert "auth.auth_accounts" in latest
    assert "auth.auth_account_sessions" in latest
    assert "public.valuation_runs" in latest
    assert "prediction_count" in latest
    assert "verified_feedback_count" in latest
    assert "training_eligible_feedback_count" in latest


def test_pgadmin_visibility_revision_exposes_public_readable_views():
    versions = sorted((PROJECT_ROOT / "alembic" / "versions").glob("*0012*.py"))
    assert len(versions) == 1
    latest = versions[0].read_text(encoding="utf-8")

    assert "public.account_registry" in latest
    assert "public.accounts" in latest
    assert "public.valuation_runs_readable" in latest
    assert "management.account_registry" in latest
    assert "run_at = COALESCE" in latest


def test_public_read_model_revision_exposes_accounts_table_and_match_seed():
    versions = sorted((PROJECT_ROOT / "alembic" / "versions").glob("*0013*.py"))
    assert len(versions) == 1
    latest = versions[0].read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS public.accounts" in latest
    assert "management.refresh_public_accounts_snapshot" in latest
    assert "production_reference_profile" in latest
    assert "public.matched_pairs" in latest
    assert "public.buyer_requirements" in latest
