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


def test_db_prod_h01_postgresql_catalog_is_partitioned_by_domain():
    from src.backend.database import engine

    assert engine.dialect.name == "postgresql"
    inspector = inspect(engine)
    schema_names = set(inspector.get_schema_names())
    assert DOMAIN_SCHEMAS <= schema_names

    public_tables = set(inspector.get_table_names(schema="public"))
    assert CORE_PUBLIC_TABLES <= public_tables
    assert TABLES_NOT_ALLOWED_IN_PUBLIC.isdisjoint(public_tables)


def test_db_prod_f01_runtime_has_no_sqlite_extension_or_database_object():
    from src.backend.database import engine

    with engine.connect() as connection:
        extensions = set(connection.execute(text("SELECT extname FROM pg_extension")).scalars())
        current_database = connection.execute(text("SELECT current_database()")) .scalar_one()

    assert "sqlite" not in extensions
    assert "sqlite" not in current_database.lower()
