import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded for all execution paths (run.py, debugger, and inline scripts).
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _env_bool(name, default):
    return os.getenv(name, str(default)).lower() == "true"


class Config:
    ENV = os.getenv("FLASK_ENV", os.getenv("APP_ENV", "development"))
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///hlm.db"  # temporary for local dev
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    RATELIMIT_ENABLED = _env_bool("RATELIMIT_ENABLED", True)
    # Use a shared backend (e.g., redis://localhost:6379/0) in non-dev environments.
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    AUTH_LOGIN_RATE_LIMIT = os.getenv("AUTH_LOGIN_RATE_LIMIT", "10 per minute")
    AUTH_REFRESH_ROTATION_ENABLED = _env_bool("AUTH_REFRESH_ROTATION_ENABLED", True)
    BOOTSTRAP_ADMIN_EMAIL = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "")
    BOOTSTRAP_ADMIN_PASSWORD = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    BOOTSTRAP_ADMIN_FULL_NAME = os.getenv("BOOTSTRAP_ADMIN_FULL_NAME", "Platform Admin")
    TOKEN_CLEANUP_ENABLED = _env_bool("TOKEN_CLEANUP_ENABLED", True)
    TOKEN_CLEANUP_INTERVAL_MINUTES = int(os.getenv("TOKEN_CLEANUP_INTERVAL_MINUTES", "60"))
    CORS_ENABLED = _env_bool("CORS_ENABLED", True)
    CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
    CORS_SUPPORTS_CREDENTIALS = _env_bool("CORS_SUPPORTS_CREDENTIALS", False)
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    SESSION_COOKIE_HTTPONLY = _env_bool("SESSION_COOKIE_HTTPONLY", True)
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SECURITY_HEADERS_ENABLED = _env_bool("SECURITY_HEADERS_ENABLED", True)
