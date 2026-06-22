"""Initial PostgreSQL schema from canonical SQLAlchemy metadata.

Revision ID: 20260620_0001
Revises:
Create Date: 2026-06-20
"""

from __future__ import annotations

from alembic import op

from src.backend.database import Base
from src.backend.model_registry import load_all_models


revision = "20260620_0001"
down_revision = None
branch_labels = None
depends_on = None


def _metadata_tables():
    load_all_models()
    return list(Base.metadata.sorted_tables)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM pg_available_extensions
                    WHERE name = 'postgis'
                ) THEN
                    EXECUTE 'CREATE EXTENSION IF NOT EXISTS postgis';
                ELSE
                    RAISE NOTICE 'PostGIS is not installed on this PostgreSQL server; continuing with non-spatial schema.';
                END IF;
            END
            $$;
            """
        )
    Base.metadata.create_all(bind=bind, tables=_metadata_tables())


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, tables=list(reversed(_metadata_tables())))
