"""Thiết lập PostgreSQL local/CI trước khi pytest import application modules."""

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for filename in (".env", ".env.postgres.local"):
    path = PROJECT_ROOT / filename
    if path.exists():
        load_dotenv(path, override=False)
        if os.getenv("DATABASE_URL"):
            break

os.environ.setdefault("RESEARCH_LAB_ACCESS_CODE", "avm-research-2026")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-ci-only")
