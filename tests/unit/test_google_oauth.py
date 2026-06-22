from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient


def _set_google_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-for-google-oauth")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-client.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "http://testserver/api/auth/google/callback")
    monkeypatch.setenv("GOOGLE_OAUTH_FRONTEND_REDIRECT", "/")


def test_google_oauth_start_uses_state_cookie_and_pkce(monkeypatch):
    _set_google_env(monkeypatch)

    from src.backend.main import app

    response = TestClient(app).get("/api/auth/google/start", follow_redirects=False)

    assert response.status_code in {302, 307}
    location = response.headers["location"]
    parsed = urlparse(location)
    query = parse_qs(parsed.query)
    assert parsed.netloc == "accounts.google.com"
    assert query["client_id"] == ["test-client.apps.googleusercontent.com"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"][0]
    assert query["code_challenge"][0]
    assert "test-client-secret" not in location

    cookies = SimpleCookie()
    for header in response.headers.get_list("set-cookie"):
        cookies.load(header)
    assert "avm_google_oauth_state" in cookies
    assert "avm_google_oauth_verifier" in cookies
    assert cookies["avm_google_oauth_state"].value == query["state"][0]
    assert "httponly" in response.headers.get("set-cookie", "").lower()


def test_google_oauth_start_uses_frontend_relay_for_local_preview(monkeypatch):
    _set_google_env(monkeypatch)
    monkeypatch.setenv(
        "GOOGLE_OAUTH_REDIRECT_URI",
        "http://127.0.0.1:8000/api/auth/google/callback",
    )

    from src.backend.main import app

    response = TestClient(app).get(
        "/api/auth/google/start",
        headers={"referer": "http://127.0.0.1:4173/login"},
        follow_redirects=False,
    )

    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["redirect_uri"] == ["http://127.0.0.1:4173/signin-google"]


def test_google_oauth_callback_rejects_invalid_state_before_google_exchange(monkeypatch):
    _set_google_env(monkeypatch)

    from src.backend.main import app

    client = TestClient(app)
    client.cookies.set("avm_google_oauth_state", "expected-state", path="/api/auth")
    client.cookies.set("avm_google_oauth_verifier", "expected-verifier", path="/api/auth")

    response = client.get("/api/auth/google/callback?code=fake-code&state=attacker-state")

    assert response.status_code == 401
    assert "state is invalid" in response.text
