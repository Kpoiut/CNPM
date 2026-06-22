"""Database configuration chỉ chấp nhận PostgreSQL cho mọi runtime."""

import pytest

from src.backend.database import build_engine_kwargs, validate_database_url


def test_postgresql_engine_uses_pool_and_no_sqlite_connect_args():
    options = build_engine_kwargs("postgresql+psycopg://avm:secret@db:5432/avm")

    assert options["connect_args"]["options"].startswith(
        "-csearch_path=public,auth,ml,community,operations,management"
    )
    assert options["pool_pre_ping"] is True
    assert options["pool_size"] == 10
    assert options["max_overflow"] == 20
    assert options["pool_recycle"] == 1800


@pytest.mark.parametrize("database_url", ["sqlite://", "sqlite:///./fixture.db", ""])
def test_non_postgresql_database_is_rejected(database_url):
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        validate_database_url(database_url)


def test_postgresql_database_url_is_accepted():
    assert validate_database_url(
        "postgresql+psycopg://avm:secret@db:5432/real_estate_avm"
    ).startswith("postgresql+psycopg://")
