import os
import tempfile

from app import create_app
from app.extensions import db
from app.models import AuthEvent, User


def _create_admin(app, email, password):
    with app.app_context():
        admin = User(
            phone_number=f"admin-{email}", email=email, is_admin=True, is_verified=True
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()


def _count_auth_events(app, event_type):
    with app.app_context():
        return AuthEvent.query.filter_by(event_type=event_type).count()


def test_register_success(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "user1@example.com",
            "password": "Pass1234!",
            "full_name": "Test User",
            "phone_number": "0123456789",
        },
    )

    assert response.status_code == 201
    assert response.get_json()["msg"] == "Provider registered successfully"


def test_register_duplicate_email(client):
    payload = {
        "email": "dupe@example.com",
        "password": "Pass1234!",
        "full_name": "Test User",
        "phone_number": "0987654321",
    }
    first = client.post("/api/auth/register", json=payload)
    second = client.post("/api/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.get_json()["msg"] == "Email already exists"


def test_register_invalid_email_returns_400(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "password": "Pass1234!",
            "full_name": "Test User",
            "phone_number": "0000000000",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["msg"] == "Invalid email format"


def test_register_weak_password_returns_400(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "weakpass@example.com",
            "password": "short",
            "full_name": "Test User",
            "phone_number": "1111111111",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["msg"] == "Password must be at least 8 characters long"


def test_login_success_returns_token(client):
    register_payload = {
        "email": "loginok@example.com",
        "password": "Pass1234!",
        "full_name": "Test User",
        "phone_number": "2222222222",
    }
    client.post("/api/auth/register", json=register_payload)

    response = client.post("/api/auth/login", json=register_payload)
    body = response.get_json()

    assert response.status_code == 200
    assert "access_token" in body
    assert "refresh_token" in body
    assert isinstance(body["access_token"], str)
    assert isinstance(body["refresh_token"], str)
    assert body["access_token"]
    assert body["refresh_token"]
    assert _count_auth_events(client.application, "provider_login_succeeded") == 1


def test_login_invalid_password_returns_401(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "badpw@example.com",
            "password": "Pass1234!",
            "full_name": "Test User",
            "phone_number": "3333333333",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "badpw@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.get_json()["msg"] == "Invalid credentials"
    assert _count_auth_events(client.application, "provider_login_failed") == 1


def test_login_invalid_email_format_returns_400(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "bad-email-format", "password": "Pass1234!"},
    )

    assert response.status_code == 400
    assert response.get_json()["msg"] == "Invalid email format"


def test_auth_version_endpoint_returns_runtime_contract(client):
    response = client.get("/api/auth/version")
    body = response.get_json()

    assert response.status_code == 200
    assert body["api_version"] == "1.0.0"
    assert body["refresh_rotation_enabled"] is True
    assert body["rate_limit_policy"] == "10 per minute"
    assert body["supported_roles"] == ["provider", "admin"]


def test_me_without_token_returns_401(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_with_token_returns_200(client):
    creds = {"email": "tokenuser@example.com", "password": "Pass1234!"}
    client.post(
        "/api/auth/register",
        json={
            "email": creds["email"],
            "password": creds["password"],
            "full_name": "Test User",
            "phone_number": "4444444444",
        },
    )
    login_response = client.post("/api/auth/login", json=creds)
    token = login_response.get_json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert "provider_id" in response.get_json()
    assert response.get_json()["role"] == "provider"


def test_admin_ping_with_provider_token_returns_403(client):
    creds = {"email": "provideronly@example.com", "password": "Pass1234!"}
    client.post(
        "/api/auth/register",
        json={
            "email": creds["email"],
            "password": creds["password"],
            "full_name": "Test User",
            "phone_number": "5555555555",
        },
    )
    login_response = client.post("/api/auth/login", json=creds)
    token = login_response.get_json()["access_token"]

    response = client.get(
        "/api/auth/admin/ping",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.get_json()["msg"] == "Forbidden"
    assert _count_auth_events(client.application, "role_access_denied") == 1


def test_admin_login_success_returns_token(client):
    _create_admin(client.application, "admin1@example.com", "AdminPass123!")

    response = client.post(
        "/api/auth/admin/login",
        json={"email": "admin1@example.com", "password": "AdminPass123!"},
    )

    body = response.get_json()
    assert response.status_code == 200
    assert "access_token" in body
    assert "refresh_token" in body
    assert isinstance(body["access_token"], str)
    assert isinstance(body["refresh_token"], str)
    assert body["access_token"]
    assert body["refresh_token"]


def test_admin_ping_with_admin_token_returns_200(client):
    _create_admin(client.application, "admin2@example.com", "AdminPass123!")
    login_response = client.post(
        "/api/auth/admin/login",
        json={"email": "admin2@example.com", "password": "AdminPass123!"},
    )
    token = login_response.get_json()["access_token"]

    response = client.get(
        "/api/auth/admin/ping",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.get_json()["msg"] == "Admin access granted"


def test_provider_ping_with_provider_token_returns_200(client):
    creds = {"email": "provider_ping@example.com", "password": "Pass1234!"}
    client.post(
        "/api/auth/register",
        json={
            "email": creds["email"],
            "password": creds["password"],
            "full_name": "Test User",
            "phone_number": "6666666666",
        },
    )
    login_response = client.post("/api/auth/login", json=creds)
    token = login_response.get_json()["access_token"]

    response = client.get(
        "/api/auth/provider/ping",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.get_json()["msg"] == "Provider access granted"


def test_provider_ping_with_admin_token_returns_403(client):
    _create_admin(client.application, "admin3@example.com", "AdminPass123!")
    login_response = client.post(
        "/api/auth/admin/login",
        json={"email": "admin3@example.com", "password": "AdminPass123!"},
    )
    token = login_response.get_json()["access_token"]

    response = client.get(
        "/api/auth/provider/ping",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.get_json()["msg"] == "Forbidden"


def test_login_rate_limit_returns_429(client):
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(
        {
            "TESTING": True,
            "ENV": "testing",
            "JWT_SECRET_KEY": "a" * 64,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "RATELIMIT_ENABLED": True,
            "AUTH_LOGIN_RATE_LIMIT": "2 per minute",
            "TOKEN_CLEANUP_ENABLED": False,
            "CORS_ENABLED": True,
            "CORS_ORIGINS": ["http://localhost:3000"],
            "SECURITY_HEADERS_ENABLED": True,
        }
    )
    local_client = app.test_client()
    with app.app_context():
        db.drop_all()
        db.create_all()
    payload = {"email": "nobody@example.com", "password": "Pass1234!"}
    first = local_client.post("/api/auth/login", json=payload)
    second = local_client.post("/api/auth/login", json=payload)
    third = local_client.post("/api/auth/login", json=payload)

    assert first.status_code == 401
    assert second.status_code == 401
    assert third.status_code == 429
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
    os.unlink(db_path)


def test_refresh_returns_new_access_token(client):
    creds = {"email": "refresh_user@example.com", "password": "Pass1234!"}
    client.post(
        "/api/auth/register",
        json={
            "email": creds["email"],
            "password": creds["password"],
            "full_name": "Test User",
            "phone_number": "7777777777",
        },
    )
    login_response = client.post("/api/auth/login", json=creds)
    refresh_token = login_response.get_json()["refresh_token"]

    response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    body = response.get_json()
    assert response.status_code == 200
    assert "access_token" in body
    assert "refresh_token" in body
    assert isinstance(body["access_token"], str)
    assert isinstance(body["refresh_token"], str)
    assert body["access_token"]
    assert body["refresh_token"]
    assert _count_auth_events(client.application, "token_refreshed") == 1


def test_refresh_rotation_revokes_old_refresh_token(client):
    creds = {"email": "refresh_rotate@example.com", "password": "Pass1234!"}
    client.post(
        "/api/auth/register",
        json={
            "email": creds["email"],
            "password": creds["password"],
            "full_name": "Test User",
            "phone_number": "8888888888",
        },
    )
    login_response = client.post("/api/auth/login", json=creds)
    old_refresh = login_response.get_json()["refresh_token"]

    rotate_response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {old_refresh}"},
    )
    assert rotate_response.status_code == 200
    new_refresh = rotate_response.get_json()["refresh_token"]
    assert new_refresh
    assert new_refresh != old_refresh

    reused_response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {old_refresh}"},
    )
    assert reused_response.status_code == 401
    assert reused_response.get_json()["msg"] == "Token has been revoked"


def test_logout_revokes_access_token(client):
    creds = {"email": "logout_user@example.com", "password": "Pass1234!"}
    client.post(
        "/api/auth/register",
        json={
            "email": creds["email"],
            "password": creds["password"],
            "full_name": "Test User",
            "phone_number": "9999999999",
        },
    )
    login_response = client.post("/api/auth/login", json=creds)
    access_token = login_response.get_json()["access_token"]

    logout_response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_response.status_code == 200
    assert _count_auth_events(client.application, "logout_succeeded") == 1

    # Same token should be rejected once revoked.
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 401
    assert me_response.get_json()["msg"] == "Token has been revoked"
