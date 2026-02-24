import os
import tempfile

from app import create_app
from app.extensions import db
from app.models.user import Admin


def test_create_admin_cli_creates_account(app):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "create-admin",
            "--email",
            "admin_bootstrap@example.com",
            "--password",
            "AdminPass123!",
            "--full-name",
            "Bootstrap Admin",
        ]
    )

    assert result.exit_code == 0
    assert "Admin created: admin_bootstrap@example.com" in result.output
    with app.app_context():
        created_admin = Admin.query.filter_by(email="admin_bootstrap@example.com").first()
        assert created_admin is not None
        assert created_admin.full_name == "Bootstrap Admin"


def test_create_admin_cli_rejects_duplicate_email(app):
    runner = app.test_cli_runner()
    first = runner.invoke(
        args=[
            "create-admin",
            "--email",
            "duplicate_admin@example.com",
            "--password",
            "AdminPass123!",
            "--full-name",
            "First Admin",
        ]
    )
    second = runner.invoke(
        args=[
            "create-admin",
            "--email",
            "duplicate_admin@example.com",
            "--password",
            "AdminPass123!",
            "--full-name",
            "Second Admin",
        ]
    )

    assert first.exit_code == 0
    assert second.exit_code != 0
    assert "Admin email already exists." in second.output


def test_env_bootstrap_creates_admin_without_cli_shell():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(
        {
            "TESTING": True,
            "ENV": "testing",
            "JWT_SECRET_KEY": "a" * 64,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "RATELIMIT_ENABLED": False,
            "TOKEN_CLEANUP_ENABLED": False,
            "CORS_ENABLED": True,
            "CORS_ORIGINS": ["http://localhost:3000"],
            "BOOTSTRAP_ADMIN_EMAIL": "env_admin@example.com",
            "BOOTSTRAP_ADMIN_PASSWORD": "AdminPass123!",
            "BOOTSTRAP_ADMIN_FULL_NAME": "Env Admin",
        }
    )
    client = app.test_client()
    with app.app_context():
        db.drop_all()
        db.create_all()
        assert Admin.query.filter_by(email="env_admin@example.com").first() is None

    # First request triggers bootstrap hook when admin env vars are set.
    response = client.get("/health")
    assert response.status_code == 200

    with app.app_context():
        created_admin = Admin.query.filter_by(email="env_admin@example.com").first()
        assert created_admin is not None
        assert created_admin.full_name == "Env Admin"
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
    os.unlink(db_path)
