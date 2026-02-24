import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import click
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, Response, g, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import inspect

from .config import Config
from .extensions import db, jwt, limiter, migrate
from .models import RevokedToken
from .tasks.admin_bootstrap import create_admin_account
from .tasks.token_cleanup import cleanup_expired_revoked_tokens
from .utils.responses import error_response

_cleanup_scheduler = None


def _is_dev_environment(env_name):
    return str(env_name).lower() in {"development", "dev", "local", "test", "testing"}


def _validate_jwt_secret(app):
    # Fail fast outside dev/test when JWT secret is weak or left as a placeholder.
    weak_defaults = {"", "dev-jwt-secret", "super-jwt-secret", "changeme"}
    env_name = app.config.get("ENV", "development")
    jwt_secret = app.config.get("JWT_SECRET_KEY", "") or ""
    if not _is_dev_environment(env_name) and (
        jwt_secret in weak_defaults or len(jwt_secret) < 32
    ):
        raise RuntimeError(
            "JWT_SECRET_KEY must be at least 32 characters and "
            "not a default value in non-dev environments."
        )


def _validate_rate_limit_storage(app):
    env_name = app.config.get("ENV", "development")
    if _is_dev_environment(env_name) or not app.config.get("RATELIMIT_ENABLED", True):
        return
    storage_uri = app.config.get("RATELIMIT_STORAGE_URI", "memory://")
    # Production multi-instance limits must use shared storage (e.g., Redis), not memory.
    if storage_uri.startswith("memory://"):
        raise RuntimeError(
            "RATELIMIT_STORAGE_URI must use shared storage "
            "(for example redis://) in non-dev environments."
        )


def _validate_cors_configuration(app):
    env_name = app.config.get("ENV", "development")
    if _is_dev_environment(env_name) or not app.config.get("CORS_ENABLED", True):
        return
    cors_origins = app.config.get("CORS_ORIGINS", [])
    # In non-dev mode, wildcard CORS is blocked to prevent overly broad cross-origin access.
    if not cors_origins or "*" in cors_origins:
        raise RuntimeError(
            "CORS_ORIGINS must be explicitly set (no wildcard) "
            "in non-dev environments."
        )


def _validate_cookie_security(app):
    env_name = app.config.get("ENV", "development")
    if _is_dev_environment(env_name):
        return
    # Prevent non-HTTPS cookie transport in production-like environments.
    if not app.config.get("SESSION_COOKIE_SECURE", False):
        raise RuntimeError(
            "SESSION_COOKIE_SECURE must be true in non-dev environments."
        )


def _start_token_cleanup_scheduler(app):
    global _cleanup_scheduler
    if _cleanup_scheduler is not None:
        return
    if not app.config.get("TOKEN_CLEANUP_ENABLED", True):
        return
    # Prevent duplicate schedulers when Flask reloader spawns a child process.
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    scheduler = BackgroundScheduler(timezone="UTC")

    def _scheduled_cleanup():
        with app.app_context():
            deleted_rows = cleanup_expired_revoked_tokens()
            # Emit cleanup metrics for production log monitoring.
            app.logger.info(
                "token_cleanup_run deleted_rows=%s timestamp_utc=%s",
                deleted_rows,
                datetime.now(UTC).isoformat(),
            )

    scheduler.add_job(
        _scheduled_cleanup,
        trigger="interval",
        minutes=app.config.get("TOKEN_CLEANUP_INTERVAL_MINUTES", 60),
        id="cleanup_expired_revoked_tokens",
        replace_existing=True,
    )
    scheduler.start()
    _cleanup_scheduler = scheduler


def _bootstrap_admin_from_env(app, bootstrap_state):
    if bootstrap_state.get("done"):
        return

    email = str(app.config.get("BOOTSTRAP_ADMIN_EMAIL", "")).strip().lower()
    password = str(app.config.get("BOOTSTRAP_ADMIN_PASSWORD", ""))
    full_name = str(
        app.config.get("BOOTSTRAP_ADMIN_FULL_NAME", "Platform Admin")
    ).strip()

    if not email or not password:
        bootstrap_state["done"] = True
        return

    # Avoid failing startup before migrations; retry on later requests until table exists.
    table_names = set(inspect(db.engine).get_table_names())
    if "users" not in table_names:
        app.logger.warning("admin_bootstrap_skipped reason=missing_users_table")
        return

    admin = create_admin_account(email=email, password=password, full_name=full_name)
    if admin is None:
        app.logger.info("admin_bootstrap_exists email=%s", email)
    else:
        app.logger.info("admin_bootstrap_created email=%s", admin.email)
    bootstrap_state["done"] = True


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)
    _validate_jwt_secret(app)
    _validate_rate_limit_storage(app)
    _validate_cors_configuration(app)
    _validate_cookie_security(app)

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    if app.config.get("CORS_ENABLED", True):
        CORS(
            app,
            resources={
                r"/api/*": {"origins": app.config.get("CORS_ORIGINS", []) or "*"}
            },
            supports_credentials=app.config.get("CORS_SUPPORTS_CREDENTIALS", False),
        )
    bootstrap_state = {"done": False}

    @app.before_request
    def assign_request_id():
        # Propagate incoming request id for traceability, or generate a new one.
        g.request_id = request.headers.get("X-Request-ID", str(uuid4()))

    @app.before_request
    def bootstrap_admin_if_configured():
        # Render free tier path: create first admin from env vars without shell access.
        _bootstrap_admin_from_env(app, bootstrap_state)
        return None

    @jwt.token_in_blocklist_loader
    def is_token_revoked(_jwt_header, jwt_payload):
        # Persistent lookup allows revocation checks to work across instances.
        jti = jwt_payload.get("jti")
        return db.session.query(RevokedToken.id).filter_by(jti=jti).scalar() is not None

    @jwt.unauthorized_loader
    def jwt_missing_token(reason):
        return error_response(reason, 401, "unauthorized")

    @jwt.invalid_token_loader
    def jwt_invalid_token(reason):
        return error_response(reason, 401, "unauthorized")

    @jwt.expired_token_loader
    def jwt_expired_token(_jwt_header, _jwt_payload):
        return error_response("Token has expired", 401, "unauthorized")

    @jwt.revoked_token_loader
    def jwt_revoked_token(_jwt_header, _jwt_payload):
        return error_response("Token has been revoked", 401, "unauthorized")

    @app.cli.command("cleanup-revoked-tokens")
    def cleanup_revoked_tokens_command():
        # Manual maintenance command: flask --app run.py cleanup-revoked-tokens
        deleted_rows = cleanup_expired_revoked_tokens()
        app.logger.info(
            "token_cleanup_manual deleted_rows=%s timestamp_utc=%s",
            deleted_rows,
            datetime.now(UTC).isoformat(),
        )
        click.echo(f"Removed {deleted_rows} expired revoked token rows.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True, help="Admin email address.")
    @click.option(
        "--password",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="Admin password.",
    )
    @click.option(
        "--full-name",
        default="Platform Admin",
        show_default=True,
        help="Admin display name.",
    )
    def create_admin_command(email, password, full_name):
        # Controlled bootstrap path for admin creation without exposing a public API endpoint.
        if "@" not in email or "." not in email:
            raise click.ClickException("Invalid email format.")
        if len(password) < 8:
            raise click.ClickException("Password must be at least 8 characters long.")
        if not any(char.isalpha() for char in password) or not any(
            char.isdigit() for char in password
        ):
            raise click.ClickException(
                "Password must include at least one letter and one number."
            )

        admin = create_admin_account(
            email=email, password=password, full_name=full_name
        )
        if admin is None:
            raise click.ClickException("Admin email already exists.")

        click.echo(f"Admin created: {admin.email}")

    _start_token_cleanup_scheduler(app)
    with app.app_context():
        _bootstrap_admin_from_env(app, bootstrap_state)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Request-ID", getattr(g, "request_id", ""))
        if app.config.get("SECURITY_HEADERS_ENABLED", True):
            # Baseline API-safe hardening headers.
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "no-referrer")
            response.headers.setdefault(
                "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none';"
            )
        return response

    @app.errorhandler(401)
    def handle_unauthorized(_error):
        return error_response("Unauthorized", 401, "unauthorized")

    @app.errorhandler(403)
    def handle_forbidden(_error):
        return error_response("Forbidden", 403, "forbidden")

    @app.errorhandler(429)
    def handle_rate_limit(_error):
        app.logger.info(
            "auth_metric event=rate_limit_hit request_id=%s path=%s timestamp_utc=%s",
            getattr(g, "request_id", ""),
            request.path,
            datetime.now(UTC).isoformat(),
        )
        return error_response("Too Many Requests", 429, "rate_limited")

    @app.errorhandler(500)
    def handle_internal_error(error):
        app.logger.exception(
            "internal_error request_id=%s path=%s timestamp_utc=%s error=%s",
            getattr(g, "request_id", ""),
            request.path,
            datetime.now(UTC).isoformat(),
            str(error),
        )
        return error_response("Internal Server Error", 500, "internal_error")

    @app.route("/health", methods=["GET"])
    def health_check():
        return {"status": "ok"}, 200

    @app.route("/", methods=["GET"])
    def index():
        # Convenient landing page choice for an API: redirect to interactive docs.
        return {
            "message": "Welcome to HustleLink API",
            "docs": "/docs",
            "health": "/health",
        }, 200

    docs_dir = Path(__file__).resolve().parents[1] / "docs"

    @app.route("/openapi.yaml", methods=["GET"])
    def openapi_spec():
        # Serve OpenAPI contract directly so docs tooling can consume it in-app.
        return send_from_directory(docs_dir, "openapi.yaml")

    @app.route("/docs", methods=["GET"])
    def swagger_ui():
        # Lightweight Swagger UI using CDN assets; no extra package required.
        html = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>HustleLink Auth API Docs</title>
    <link rel="stylesheet"
          href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js">
    </script>
    <script>
      window.ui = SwaggerUIBundle({
        url: "/openapi.yaml",
        dom_id: "#swagger-ui",
        deepLinking: true
      });
    </script>
  </body>
</html>"""
        return Response(html, mimetype="text/html")

    from app.routes.auth import auth_bp
    from app.routes.marketplace import marketplace_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(marketplace_bp, url_prefix="/api/marketplace")

    return app
