"""Ba kịch bản demo production cho PostgreSQL.

Happy path
    DB-PROD-H01: Alembic đã tạo đủ schema theo domain và giữ các bảng AVM lõi
    trong ``public``.

Failure path
    DB-PROD-F01: SQLite hoặc domain table quay lại ``public`` phải làm test fail.
    Hướng xử lý: dừng release, chạy đúng Alembic head, không tự tạo/fallback DB.

Evidence
    Chạy ``pytest tests/production/test_database_release_gate.py -vv``; CI lưu
    JUnit XML cùng commit SHA.
"""

from sqlalchemy import inspect, text


CORE_PUBLIC_TABLES = {
    "alembic_version",
    "buyer_requirements",
    "collection_sources",
    "expert_properties",
    "expert_ratings",
    "matched_pairs",
    "properties",
    "provenance_chains",
    "valuation_runs",
}
DOMAIN_SCHEMAS = {"auth", "community", "management", "ml", "operations", "public"}
TABLES_NOT_ALLOWED_IN_PUBLIC = {
    "auth_accounts",
    "auth_account_sessions",
    "auth_refresh_tokens",
    "dataset_versions",
    "training_runs",
    "training_metrics",
    "model_versions",
    "audit_logs",
    "migration_rejected_rows",
    "claims",
    "community_comments",
}
REQUIRED_MANAGEMENT_VIEWS = {
    "account_registry",
    "collection_source_health",
    "database_catalog",
    "model_registry",
    "prediction_history",
    "training_feedback_candidates",
    "training_history",
}
REQUIRED_PUBLIC_READABLE_VIEWS = {
    "account_registry",
    "accounts",
    "valuation_runs_readable",
}


def test_db_prod_h01_postgresql_catalog_is_partitioned_by_domain():
    from src.backend.database import engine

    assert engine.dialect.name == "postgresql"
    inspector = inspect(engine)
    schema_names = set(inspector.get_schema_names())
    assert DOMAIN_SCHEMAS <= schema_names

    public_tables = set(inspector.get_table_names(schema="public"))
    assert CORE_PUBLIC_TABLES <= public_tables
    assert TABLES_NOT_ALLOWED_IN_PUBLIC.isdisjoint(public_tables)

    management_views = set(inspector.get_view_names(schema="management"))
    assert REQUIRED_MANAGEMENT_VIEWS <= management_views

    public_views = set(inspector.get_view_names(schema="public"))
    assert REQUIRED_PUBLIC_READABLE_VIEWS <= public_views


def test_db_prod_h02_account_registry_exposes_prediction_feedback_value():
    from src.backend.database import engine

    inspector = inspect(engine)
    columns = {
        column["name"]
        for column in inspector.get_columns("account_registry", schema="management")
    }

    assert {
        "account_id",
        "username",
        "role",
        "is_active",
        "total_sessions",
        "active_sessions",
        "prediction_count",
        "verified_feedback_count",
        "training_eligible_feedback_count",
        "latest_prediction_at",
        "account_state",
    } <= columns


def test_db_prod_h03_pgadmin_public_views_are_readable_without_duplicate_tables():
    from src.backend.database import engine

    inspector = inspect(engine)
    public_tables = set(inspector.get_table_names(schema="public"))
    assert "accounts" not in public_tables
    assert "account_registry" not in public_tables

    account_columns = {
        column["name"]
        for column in inspector.get_columns("accounts", schema="public")
    }
    history_columns = {
        column["name"]
        for column in inspector.get_columns("valuation_runs_readable", schema="public")
    }

    assert {"account_id", "username", "prediction_count", "account_state"} <= account_columns
    assert {
        "request_id",
        "predicted_at",
        "account_username",
        "fair_market_value_vnd",
        "training_eligible",
    } <= history_columns


def test_db_prod_f01_runtime_has_no_sqlite_extension_or_database_object():
    from src.backend.database import engine

    with engine.connect() as connection:
        extensions = set(connection.execute(text("SELECT extname FROM pg_extension")).scalars())
        current_database = connection.execute(text("SELECT current_database()")) .scalar_one()

    assert "sqlite" not in extensions
    assert "sqlite" not in current_database.lower()
