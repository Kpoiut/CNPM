"""Shared fixtures cho integration tests."""
import pytest, sys, os
from pathlib import Path

# Load .env before importing app (main.py crashes if RESEARCH_LAB_ACCESS_CODE missing)
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

# Ensure required env vars for test environment
os.environ.setdefault("RESEARCH_LAB_ACCESS_CODE", "avm-research-2026")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-ci-only")

# Add src to path for api imports
sys.path.insert(0, str(project_root / "src"))
