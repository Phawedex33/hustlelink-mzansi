import pytest

from app import create_app


def test_security_headers_present(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "no-referrer"
    assert response.headers.get("Content-Security-Policy") == "default-src 'none'; frame-ancestors 'none';"


def test_request_id_is_echoed_when_provided(client):
    response = client.get("/health", headers={"X-Request-ID": "req-123"})

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "req-123"


def test_request_id_is_generated_when_missing(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


def test_cors_allows_configured_origin(client):
    response = client.get(
        "/api/auth/test",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"


def test_cors_blocks_unconfigured_origin(client):
    response = client.get(
        "/api/auth/test",
        headers={"Origin": "http://evil.example"},
    )

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") is None


def test_production_cors_requires_explicit_origins():
    with pytest.raises(RuntimeError, match="CORS_ORIGINS must be explicitly set"):
        create_app(
            {
                "ENV": "production",
                "JWT_SECRET_KEY": "a" * 64,
                "RATELIMIT_STORAGE_URI": "redis://localhost:6379/0",
                "CORS_ENABLED": True,
                "CORS_ORIGINS": [],
                "TOKEN_CLEANUP_ENABLED": False,
            }
        )


def test_production_requires_secure_session_cookie():
    with pytest.raises(RuntimeError, match="SESSION_COOKIE_SECURE must be true"):
        create_app(
            {
                "ENV": "production",
                "JWT_SECRET_KEY": "a" * 64,
                "RATELIMIT_STORAGE_URI": "redis://localhost:6379/0",
                "CORS_ENABLED": True,
                "CORS_ORIGINS": ["https://app.example.com"],
                "SESSION_COOKIE_SECURE": False,
                "TOKEN_CLEANUP_ENABLED": False,
            }
        )


def test_unauthorized_error_payload_is_normalized(client):
    response = client.get("/api/auth/me")
    body = response.get_json()

    assert response.status_code == 401
    assert body["msg"]
    assert body["error"]["code"] == "unauthorized"
    assert body["error"]["request_id"]
