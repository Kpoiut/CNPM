"""Load the canonical local environment and run Alembic migrations."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv


PROJECT_ROOT = Path.cwd()
for env_name in (".env", ".env.postgres.local"):
    env_path = PROJECT_ROOT / env_name
    if env_path.exists():
        load_dotenv(env_path)
        break


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.startswith("postgresql"):
        raise SystemExit("Refusing migration: DATABASE_URL is not PostgreSQL")
    command.upgrade(Config(str(PROJECT_ROOT / "alembic.ini")), "head")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
