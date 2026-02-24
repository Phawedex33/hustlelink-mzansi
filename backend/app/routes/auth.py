"""
Authentication routes and utilities for providers and admins.

Covers: registration, login, token refresh, logout, role-gated
endpoints, and runtime contract inspection.
"""

import re
from datetime import UTC, datetime
from functools import wraps

from app.extensions import db, limiter
from app.models import AuthEvent, Profile, ProviderProfile, RevokedToken, User
from app.utils.responses import error_response
from flask import Blueprint, current_app, g, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)

auth_bp = Blueprint("auth", __name__)

# Compiled regex for email validation — avoids recompiling on every request.
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Runtime contract constants surfaced via /version endpoint.
AUTH_API_VERSION = "1.0.0"
SUPPORTED_AUTH_ROLES = ["provider", "admin"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_request_data():
    """Parse JSON body; return (data, None) or (None, error_response)."""
    data = request.get_json(silent=True)
    if not data:
        return None, error_response(
            "Request body must be valid JSON", 400, "bad_request"
        )
    return data, None


def _validate_required_fields(data, required_fields):
    """Return an error response if any required field is missing/blank."""
    missing = []
    for field in required_fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    if missing:
        return error_response(
            f"Missing required fields: {', '.join(missing)}",
            400,
            "bad_request",
        )
    return None


def _validate_email(email):
    """Return an error response if email does not match expected format."""
    if not EMAIL_PATTERN.match(email):
        return error_response("Invalid email format", 400, "bad_request")
    return None


def _validate_password_strength(password):
    """Enforce minimum password policy: 8+ chars, at least 1 letter + 1 digit."""
    if len(password) < 8:
        return error_response(
            "Password must be at least 8 characters long",
            400,
            "bad_request",
        )
    has_letter = any(char.isalpha() for char in password)
    has_digit = any(char.isdigit() for char in password)
    if not has_letter or not has_digit:
        return error_response(
            "Password must include at least one letter and one number",
            400,
            "bad_request",
        )
    return None


def _log_auth_metric(event, role="unknown"):
    """Emit a structured log line for auth metric tracking."""
    current_app.logger.info(
        "auth_metric event=%s role=%s request_id=%s path=%s" " timestamp_utc=%s",
        event,
        role,
        getattr(g, "request_id", ""),
        request.path,
        datetime.now(UTC).isoformat(),
    )


def _log_auth_event(event_type, subject_type, subject_id=None):
    """Persist an audit event. Fails open to avoid blocking auth flows."""
    try:
        db.session.add(
            AuthEvent(
                event_type=event_type,
                subject_type=subject_type,
                subject_id=(str(subject_id) if subject_id is not None else None),
                ip=request.remote_addr,
                user_agent=(
                    request.user_agent.string[:255]
                    if request.user_agent and request.user_agent.string
                    else None
                ),
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("auth_event_log_failed event_type=%s", event_type)


def _forbidden_if_not_role(required_role):
    """Check JWT role claim; return 403 response if it doesn't match."""
    claims = get_jwt()
    role = claims.get("role")
    if role != required_role:
        _log_auth_metric(event="role_access_denied", role=role or "unknown")
        _log_auth_event(
            event_type="role_access_denied",
            subject_type=role or "unknown",
            subject_id=get_jwt_identity(),
        )
        return error_response("Forbidden", 403, "forbidden")
    return None


def _issue_auth_tokens(identity, role):
    """Create and return a fresh access + refresh token pair."""
    return {
        "access_token": create_access_token(
            identity=identity,
            additional_claims={"role": role},
        ),
        "refresh_token": create_refresh_token(
            identity=identity,
            additional_claims={"role": role},
        ),
    }


def _extract_expiry_from_payload(jwt_payload):
    """Convert JWT 'exp' Unix timestamp to a UTC datetime object."""
    exp_timestamp = jwt_payload.get("exp")
    # Fallback to now() keeps behaviour safe for tokens that lack exp.
    return (
        datetime.fromtimestamp(exp_timestamp, UTC)
        if exp_timestamp is not None
        else datetime.now(UTC)
    )


def _revoke_token(jwt_payload):
    """Persistently revoke a token by storing its jti in the database."""
    jti = jwt_payload["jti"]
    # Idempotent: skip if already revoked.
    if RevokedToken.query.filter_by(jti=jti).first():
        return
    db.session.add(
        RevokedToken(
            jti=jti,
            expires_at=_extract_expiry_from_payload(jwt_payload),
        )
    )
    db.session.commit()


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def role_required(required_role):
    """Decorator: enforce a specific JWT role on a route."""

    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            forbidden = _forbidden_if_not_role(required_role)
            if forbidden:
                return forbidden
            return fn(*args, **kwargs)

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Provider registration
# ---------------------------------------------------------------------------


@auth_bp.route("/register", methods=["POST"])
def register_provider():
    """Register a new provider account."""
    data, err = _get_request_data()
    if err:
        return err

    validation_error = _validate_required_fields(
        data, ["full_name", "email", "password"]
    )
    if validation_error:
        return validation_error

    full_name = data["full_name"].strip()
    email = data["email"].strip().lower()
    password = data["password"]

    invalid_email = _validate_email(email)
    if invalid_email:
        return invalid_email

    weak_password = _validate_password_strength(password)
    if weak_password:
        return weak_password

    if User.query.filter_by(email=email).first():
        return error_response("Email already exists", 409, "conflict")

    phone_number = data.get("phone_number")
    if not phone_number:
        return error_response("Phone number is required", 400, "bad_request")

    if User.query.filter_by(phone_number=phone_number).first():
        return error_response("Phone number already exists", 409, "conflict")

    user = User(phone_number=phone_number, email=email)
    user.set_password(password)

    # Split full name into first and last parts.
    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    profile = Profile(user=user, first_name=first_name, last_name=last_name)
    provider_profile = ProviderProfile(user=user)

    db.session.add(user)
    db.session.add(profile)
    db.session.add(provider_profile)
    db.session.commit()

    return jsonify({"msg": "Provider registered successfully"}), 201


# ---------------------------------------------------------------------------
# Provider login
# ---------------------------------------------------------------------------


@auth_bp.route("/login", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("AUTH_LOGIN_RATE_LIMIT", "10 per minute"))
def login_provider():
    """Authenticate a provider and return JWT tokens."""
    data, err = _get_request_data()
    if err:
        return err

    validation_error = _validate_required_fields(data, ["email", "password"])
    if validation_error:
        return validation_error

    email = data["email"].strip().lower()
    password = data["password"]

    invalid_email = _validate_email(email)
    if invalid_email:
        return invalid_email

    user = User.query.filter_by(email=email).first()
    # Must be a valid user with a provider profile to log in via this route.
    if not user or not user.check_password(password) or not user.provider_profile:
        _log_auth_metric(event="provider_login_failed", role="provider")
        _log_auth_event(event_type="provider_login_failed", subject_type="provider")
        return error_response("Invalid credentials", 401, "unauthorized")

    tokens = _issue_auth_tokens(identity=str(user.id), role="provider")
    _log_auth_metric(event="provider_login_succeeded", role="provider")
    _log_auth_event(
        event_type="provider_login_succeeded",
        subject_type="provider",
        subject_id=user.id,
    )
    return jsonify(tokens), 200


# ---------------------------------------------------------------------------
# Admin login
# ---------------------------------------------------------------------------


@auth_bp.route("/admin/login", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("AUTH_LOGIN_RATE_LIMIT", "10 per minute"))
def login_admin():
    """Authenticate an admin account and return JWT tokens."""
    data, err = _get_request_data()
    if err:
        return err

    validation_error = _validate_required_fields(data, ["email", "password"])
    if validation_error:
        return validation_error

    email = data["email"].strip().lower()
    password = data["password"]

    invalid_email = _validate_email(email)
    if invalid_email:
        return invalid_email

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password) or not user.is_admin:
        _log_auth_metric(event="admin_login_failed", role="admin")
        _log_auth_event(event_type="admin_login_failed", subject_type="admin")
        return error_response("Invalid credentials", 401, "unauthorized")

    tokens = _issue_auth_tokens(identity=str(user.id), role="admin")
    _log_auth_metric(event="admin_login_succeeded", role="admin")
    _log_auth_event(
        event_type="admin_login_succeeded",
        subject_type="admin",
        subject_id=user.id,
    )
    return jsonify(tokens), 200


# ---------------------------------------------------------------------------
# Utility / info endpoints
# ---------------------------------------------------------------------------


@auth_bp.route("/test", methods=["GET"])
def test_route():
    """Temporary health check — confirms auth blueprint is mounted."""
    return {"message": "Auth route working!"}, 200


@auth_bp.route("/version", methods=["GET"])
def auth_version():
    """Return runtime auth contract metadata for frontend capability checks."""
    refresh_rotation_enabled = current_app.config.get(
        "AUTH_REFRESH_ROTATION_ENABLED", True
    )
    return (
        jsonify(
            {
                "api_version": AUTH_API_VERSION,
                "refresh_rotation_enabled": bool(refresh_rotation_enabled),
                "rate_limit_policy": current_app.config.get(
                    "AUTH_LOGIN_RATE_LIMIT", "10 per minute"
                ),
                "supported_roles": SUPPORTED_AUTH_ROLES,
            }
        ),
        200,
    )


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Return the identity and role of the currently authenticated user."""
    claims = get_jwt()
    return (
        jsonify(
            {
                "provider_id": get_jwt_identity(),
                "role": claims.get("role"),
            }
        ),
        200,
    )


# ---------------------------------------------------------------------------
# Role-gated ping endpoints (frontend capability checks)
# ---------------------------------------------------------------------------


@auth_bp.route("/admin/ping", methods=["GET"])
@role_required("admin")
def admin_ping():
    """Protected endpoint — confirms admin JWT is valid."""
    return jsonify({"msg": "Admin access granted"}), 200


@auth_bp.route("/provider/ping", methods=["GET"])
@role_required("provider")
def provider_ping():
    """Protected endpoint — confirms provider JWT is valid."""
    return jsonify({"msg": "Provider access granted"}), 200


# ---------------------------------------------------------------------------
# Token refresh & logout
# ---------------------------------------------------------------------------


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh_access_token():
    """
    Rotate the refresh token and issue a new access token.

    When AUTH_REFRESH_ROTATION_ENABLED is True (default), the current
    refresh token is revoked and a fresh pair is issued. When False,
    only a new access token is returned (compatibility mode).
    """
    claims = get_jwt()
    identity = get_jwt_identity()
    role = claims.get("role", "provider")

    if current_app.config.get("AUTH_REFRESH_ROTATION_ENABLED", True):
        # Rotation: revoke old refresh token, issue a brand-new pair.
        _revoke_token(claims)
        tokens = _issue_auth_tokens(identity=identity, role=role)
    else:
        # Compatibility mode: only a new access token, no new refresh token.
        tokens = {
            "access_token": create_access_token(
                identity=identity, additional_claims={"role": role}
            ),
            "refresh_token": None,  # nosec
        }

    _log_auth_metric(event="token_refreshed", role=role)
    _log_auth_event(
        event_type="token_refreshed",
        subject_type=role,
        subject_id=identity,
    )
    return jsonify(tokens), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """Revoke the current access token, preventing further use."""
    jwt_payload = get_jwt()
    _revoke_token(jwt_payload)
    role = jwt_payload.get("role", "unknown")
    _log_auth_metric(event="logout_succeeded", role=role)
    _log_auth_event(
        event_type="logout_succeeded",
        subject_type=role,
        subject_id=get_jwt_identity(),
    )
    return jsonify({"msg": "Logged out successfully"}), 200
