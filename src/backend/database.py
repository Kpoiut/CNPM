"""PostgreSQL-only database configuration and session management."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_SEARCH_PATH = "public,auth,ml,community,operations,management"


def _load_local_environment() -> None:
    """Load local configuration without overriding container/CI variables."""
    if os.getenv("DATABASE_URL"):
        return
    for filename in (".env", ".env.postgres.local"):
        path = PROJECT_ROOT / filename
        if path.exists():
            load_dotenv(path, override=False)
            if os.getenv("DATABASE_URL"):
                return


def validate_database_url(database_url: str | None) -> str:
    """Reject every non-PostgreSQL runtime before an engine is created."""
    value = (database_url or "").strip()
    if not value.startswith("postgresql+psycopg://"):
        raise RuntimeError(
            "DATABASE_URL phải dùng PostgreSQL với psycopg "
            "(postgresql+psycopg://...)."
        )
    return value


_load_local_environment()
DATABASE_URL = validate_database_url(os.getenv("DATABASE_URL"))


def build_engine_kwargs(database_url: str) -> dict:
    """Return pooled PostgreSQL engine options."""
    validate_database_url(database_url)
    return {
        "echo": False,
        "pool_pre_ping": True,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800")),
        "connect_args": {"options": f"-csearch_path={DB_SEARCH_PATH}"},
    }

# Create engine
engine = create_engine(DATABASE_URL, **build_engine_kwargs(DATABASE_URL))

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Verify that Alembic prepared PostgreSQL; runtime never creates schema."""
    with engine.connect() as connection:
        migration_table = connection.execute(
            text("SELECT to_regclass('public.alembic_version')")
        ).scalar_one()
    if migration_table is None:
        raise RuntimeError("PostgreSQL chưa được migrate. Chạy: python -m alembic upgrade head")
