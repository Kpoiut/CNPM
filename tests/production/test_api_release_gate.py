"""Ba kịch bản demo production cho API và SLO.

Happy path
    API-PROD-H01: health cache-hit trả PostgreSQL status và p95 dưới 200 ms.

Failure path
    API-PROD-F01: endpoint lịch sử không có account phải fail closed.
    API-PROD-F02: Google OAuth thiếu secret phải trả 503, không lộ secret mẫu.
    API-PROD-F03: JSON body hỏng phải trả 400, không được văng 500 từ middleware.

Hướng xử lý
    Nếu latency vượt SLO: kiểm tra DB pool/cache/middleware rồi chạy lại cùng
    workload. Nếu auth/OAuth fail sai contract: khóa release, kiểm tra RBAC,
    redirect allowlist và GitHub Secrets; không bật bypass.

Evidence
    ``pytest tests/production/test_api_release_gate.py -vv`` và JUnit XML từ CI.
"""

from pathlib import Path
from statistics import quantiles
from time import perf_counter

from fastapi.testclient import TestClient


def test_api_prod_h01_cached_health_p95_is_below_200ms(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-for-production-gate")
    from src.backend import main as backend_main

    backend_main._HEALTH_DB_CACHE["database"] = None
    backend_main._HEALTH_DB_CACHE["expires_at"] = 0.0
    client = TestClient(backend_main.app)
    client.get("/api/health")

    samples = []
    for _ in range(12):
        started = perf_counter()
        response = client.get("/api/health")
        samples.append((perf_counter() - started) * 1000)
        assert response.status_code == 200
        assert response.json()["database"]["dialect"] == "postgresql"
        assert response.json()["database"]["cache"] == "hit"

    p95_ms = quantiles(samples, n=20, method="inclusive")[18]
    assert p95_ms < 200, f"health p95={p95_ms:.2f}ms vượt SLO 200ms"


def test_api_prod_f01_history_fails_closed_without_account(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-for-production-gate")
    from src.backend.main import app

    response = TestClient(app).get("/api/v2/valuation/runs")
    assert response.status_code in {401, 403}


def test_api_prod_f02_oauth_missing_secret_is_safe(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-for-production-gate")
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)
    from src.backend.main import app

    response = TestClient(app).get("/api/auth/google/start")
    assert response.status_code == 503
    assert "GOCSPX" not in response.text


def test_api_prod_f03_invalid_json_body_fails_as_client_error(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-for-production-gate")
    from src.backend.main import app

    response = TestClient(app).post(
        "/api/auth/login",
        content="{bad json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert "Invalid JSON body" in response.text


def test_api_prod_h04_pipeline_endpoint_does_not_mutate_global_orchestrator():
    source = Path("src/backend/api_v2/valuation.py").read_text(encoding="utf-8")
    pipeline_region = source.split('@api_router.post("/pipeline")', 1)[1].split('@api_router.get("/engine/version")', 1)[0]

    assert "pipeline.valuation_engine.comparable_finder = finder" not in pipeline_region
    assert "request_pipeline = PipelineOrchestrator(comparable_finder=finder)" in pipeline_region
