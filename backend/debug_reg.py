"""
Debug script for testing provider registration.
"""

from app import create_app
from app.extensions import db

app = create_app(
    {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "RATELIMIT_ENABLED": False,  # nosec
        "TOKEN_CLEANUP_ENABLED": False,  # nosec
    }
)

with app.app_context():
    db.create_all()
    client = app.test_client()

    payload = {
        "email": "dupe@example.com",
        "password": "Pass1234!",  # nosec
        "full_name": "Test User",
        "phone_number": "0987654321",
    }

    print("Registering first time...")
    res1 = client.post("/api/auth/register", json=payload)
    print(f"Status: {res1.status_code}")
    print(f"Body: {res1.get_data(as_text=True)}")

    print("\nRegistering second time...")
    res2 = client.post("/api/auth/register", json=payload)
    print(f"Status: {res2.status_code}")
    print(f"Body: {res2.get_data(as_text=True)}")
