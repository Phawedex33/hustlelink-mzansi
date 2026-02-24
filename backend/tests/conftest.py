import os
import tempfile

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app():
    # Use a dedicated sqlite file so tests never touch local/dev data.
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
        "SECURITY_HEADERS_ENABLED": True,
        }
    )

    with app.app_context():
        # Isolate database state (including revoked tokens) between tests.
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
        # Ensure SQLite file handles are released before unlink on Windows.
        db.engine.dispose()

    os.unlink(db_path)


@pytest.fixture()
def client(app):
    return app.test_client()
