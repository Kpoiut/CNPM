from fastapi.testclient import TestClient


def test_health_endpoint_reports_database_status(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-for-health-endpoint")

    from src.backend.main import app

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"]["ok"] is True
    assert body["database"]["dialect"] == "postgresql"


def test_health_endpoint_cache_hit_has_sub_200ms_response_header(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-for-health-cache")

    from src.backend import main as backend_main

    backend_main._HEALTH_DB_CACHE["database"] = None
    backend_main._HEALTH_DB_CACHE["expires_at"] = 0.0

    client = TestClient(backend_main.app)
    client.get("/api/health")
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["database"]["cache"] == "hit"
    assert float(response.headers["X-Response-Time-Ms"]) < 200


def test_google_oauth_start_fails_safe_when_secret_missing(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-for-oauth")
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)

    from src.backend.main import app

    response = TestClient(app).get("/api/auth/google/start")

    assert response.status_code == 503
    assert "GOOGLE_OAUTH_CLIENT_SECRET" in response.text
    assert "GOCSPX" not in response.text
