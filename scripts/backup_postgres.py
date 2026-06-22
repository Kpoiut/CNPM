"""Create a compressed PostgreSQL backup without printing credentials."""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url


PROJECT_ROOT = Path.cwd()
for env_name in (".env", ".env.postgres.local"):
    env_path = PROJECT_ROOT / env_name
    if env_path.exists():
        load_dotenv(env_path)
        break


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url or not database_url.startswith("postgresql"):
        raise SystemExit("DATABASE_URL PostgreSQL is required")

    url = make_url(database_url)
    pg_dump = shutil.which("pg_dump") or r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"
    backup_dir = PROJECT_ROOT / "backups" / "postgresql"
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"before_ml_lineage_{datetime.now():%Y%m%d_%H%M%S}.dump"
    env = os.environ.copy()
    env["PGPASSWORD"] = url.password or ""
    subprocess.run(
        [
            pg_dump,
            "--format=custom",
            "--no-owner",
            "--host",
            url.host or "127.0.0.1",
            "--port",
            str(url.port or 5432),
            "--username",
            url.username or "postgres",
            "--file",
            str(target),
            url.database or "postgres",
        ],
        check=True,
        env=env,
    )
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
