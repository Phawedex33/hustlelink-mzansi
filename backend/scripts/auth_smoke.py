import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def _env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _request(method, base_url, path, token=None, payload=None):
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8") or "{}"
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") or "{}"
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"raw": body}
        return exc.code, parsed


def _expect(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    base_url = _env("BASE_URL")
    provider_email = _env("PROVIDER_EMAIL")
    provider_password = _env("PROVIDER_PASSWORD")
    admin_email = _env("ADMIN_EMAIL")
    admin_password = _env("ADMIN_PASSWORD")

    # Register provider (idempotent flow: allow already-registered status).
    status, _ = _request(
        "POST",
        base_url,
        "/api/auth/register",
        payload={"email": provider_email, "password": provider_password},
    )
    _expect(status in (201, 409), f"register expected 201/409, got {status}")

    # Provider login + base token checks.
    status, provider_login = _request(
        "POST",
        base_url,
        "/api/auth/login",
        payload={"email": provider_email, "password": provider_password},
    )
    _expect(status == 200, f"provider login expected 200, got {status}: {provider_login}")
    provider_access = provider_login.get("access_token")
    provider_refresh = provider_login.get("refresh_token")
    _expect(provider_access and provider_refresh, "provider login did not return token pair")

    status, me = _request("GET", base_url, "/api/auth/me", token=provider_access)
    _expect(status == 200, f"provider me expected 200, got {status}: {me}")
    _expect(me.get("role") == "provider", f"provider me role mismatch: {me}")

    status, _ = _request("GET", base_url, "/api/auth/provider/ping", token=provider_access)
    _expect(status == 200, f"provider ping expected 200, got {status}")

    status, _ = _request("GET", base_url, "/api/auth/admin/ping", token=provider_access)
    _expect(status == 403, f"admin ping with provider token expected 403, got {status}")

    # Refresh rotation: old refresh must become invalid after use.
    old_refresh = provider_refresh
    status, refreshed = _request("POST", base_url, "/api/auth/refresh", token=old_refresh)
    _expect(status == 200, f"refresh expected 200, got {status}: {refreshed}")
    new_access = refreshed.get("access_token")
    new_refresh = refreshed.get("refresh_token")
    _expect(new_access and new_refresh, "refresh did not return token pair")
    _expect(new_refresh != old_refresh, "refresh token did not rotate")

    status, _ = _request("POST", base_url, "/api/auth/refresh", token=old_refresh)
    _expect(status == 401, f"reused old refresh expected 401, got {status}")

    # Logout must revoke current access token.
    status, _ = _request("POST", base_url, "/api/auth/logout", token=new_access)
    _expect(status == 200, f"logout expected 200, got {status}")

    status, _ = _request("GET", base_url, "/api/auth/me", token=new_access)
    _expect(status == 401, f"me with revoked access expected 401, got {status}")

    # Admin login and role checks.
    status, admin_login = _request(
        "POST",
        base_url,
        "/api/auth/admin/login",
        payload={"email": admin_email, "password": admin_password},
    )
    _expect(
        status == 200,
        "admin login failed. Ensure admin exists via `flask --app run.py create-admin ...`.",
    )
    admin_access = admin_login.get("access_token")
    _expect(admin_access, "admin login missing access token")

    status, _ = _request("GET", base_url, "/api/auth/admin/ping", token=admin_access)
    _expect(status == 200, f"admin ping expected 200, got {status}")

    status, _ = _request("GET", base_url, "/api/auth/provider/ping", token=admin_access)
    _expect(status == 403, f"provider ping with admin token expected 403, got {status}")

    print("Smoke auth flow passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Smoke auth flow failed: {exc}")
        sys.exit(1)
