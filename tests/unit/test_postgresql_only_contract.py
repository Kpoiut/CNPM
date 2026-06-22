"""Contract guards chống tái đưa SQLite vào application và integration tests."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_and_integration_fixture_have_no_sqlite_dependency():
    runtime_files = [
        PROJECT_ROOT / "src" / "backend" / "database.py",
        PROJECT_ROOT / "src" / "backend" / "api_v2" / "nova.py",
        PROJECT_ROOT / "src" / "backend" / "auth" / "router.py",
        PROJECT_ROOT / "tests" / "integration" / "conftest.py",
    ]

    for path in runtime_files:
        source = path.read_text(encoding="utf-8")
        assert "sqlite" not in source.lower(), f"SQLite reference found in {path}"
        assert "StaticPool" not in source, f"StaticPool reference found in {path}"


def test_environment_example_defaults_to_postgresql():
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "DATABASE_URL=postgresql+psycopg://" in env_example
    assert "real_estate_avm_app" in env_example
    assert "127.0.0.1:5433/real_estate_avm" in env_example
    assert "DATABASE_URL=sqlite" not in env_example


def test_local_postgres18_realtime_checker_is_committed():
    checker = PROJECT_ROOT / "scripts" / "local" / "VERIFY_POSTGRES18_REALTIME.ps1"
    source = checker.read_text(encoding="utf-8")

    assert "PostgreSQL 18" in source
    assert "ExpectedPort = 5433" in source
    assert "20260622_0014" in source
    assert "/api/health" in source
    assert "DATABASE_URL" in source
