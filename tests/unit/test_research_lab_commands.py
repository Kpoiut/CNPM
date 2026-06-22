"""Contract tests cho các lệnh vận hành trong admin Research Lab."""


def test_frontend_build_operation_enforces_bundle_budget_gate(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-for-research-lab")

    from src.backend.main import _build_research_lab_command

    command, cwd, timeout = _build_research_lab_command("frontend_build", {})

    assert command == ["npm", "run", "build:check"]
    assert cwd.name == "frontend"
    assert timeout >= 300
