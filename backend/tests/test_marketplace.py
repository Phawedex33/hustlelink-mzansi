from datetime import datetime, timedelta

from app.extensions import db
from app.models import User


def _create_user(client, email, phone, full_name="Test User", is_approved=False):
    payload = {
        "email": email,
        "password": "Pass1234!",
        "full_name": full_name,
        "phone_number": phone
    }
    client.post("/api/auth/register", json=payload)
    
    with client.application.app_context():
        user = User.query.filter_by(email=email).first()
        if is_approved:
            user.provider_profile.is_approved = True
        db.session.commit()
        return user.id

def _get_token(client, email):
    login_payload = {"email": email, "password": "Pass1234!"}
    response = client.post("/api/auth/login", json=login_payload)
    return response.get_json()["access_token"]

def test_create_service_fail_not_approved(client):
    _create_user(client, "provider1@example.com", "1111111111", is_approved=False)
    token = _get_token(client, "provider1@example.com")
    
    response = client.post(
        "/api/marketplace/services",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "House Cleaning",
            "description": "Professional cleaning",
            "category": "Cleaning",
            "price": 500.00
        }
    )
    
    assert response.status_code == 403
    assert "Provider profile must be complete and approved" in response.get_json()["msg"]

def test_create_service_success(client):
    _create_user(client, "provider2@example.com", "2222222222", is_approved=True)
    token = _get_token(client, "provider2@example.com")
    
    response = client.post(
        "/api/marketplace/services",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Plumbing",
            "description": "Fixing leaks",
            "category": "Maintenance",
            "price": 350.00
        }
    )
    
    assert response.status_code == 201
    assert response.get_json()["service"]["title"] == "Plumbing"

def test_create_booking_success(client):
    # Setup: Provider with a service
    _create_user(client, "p3@example.com", "3333333333", is_approved=True)
    p_token = _get_token(client, "p3@example.com")
    
    s_response = client.post(
        "/api/marketplace/services",
        headers={"Authorization": f"Bearer {p_token}"},
        json={
            "title": "Garden Service",
            "description": "Mowing lawn",
            "category": "Garden",
            "price": 200.00
        }
    )
    service_id = s_response.get_json()["service"]["id"]
    
    # Setup: Client
    _create_user(client, "c1@example.com", "4444444444")
    c_token = _get_token(client, "c1@example.com")
    
    # Action: Book the service
    scheduled_at = (datetime.now() + timedelta(days=1)).isoformat()
    response = client.post(
        "/api/marketplace/bookings",
        headers={"Authorization": f"Bearer {c_token}"},
        json={
            "service_id": service_id,
            "scheduled_at": scheduled_at
        }
    )
    
    assert response.status_code == 201
    assert response.get_json()["booking"]["status"] == "pending"

def test_list_user_bookings(client):
    # Setup: Provider, Client, Service, Booking
    _create_user(client, "p4@example.com", "5555555555", is_approved=True)
    p_token = _get_token(client, "p4@example.com")
    
    s_response = client.post(
        "/api/marketplace/services",
        headers={"Authorization": f"Bearer {p_token}"},
        json={"title": "S1", "description": "D1", "category": "C1", "price": 100}
    )
    s_id = s_response.get_json()["service"]["id"]
    
    c_token = _get_token(client, "p4@example.com") # User booking their own service (as client)
    
    client.post(
        "/api/marketplace/bookings",
        headers={"Authorization": f"Bearer {c_token}"},
        json={"service_id": s_id, "scheduled_at": datetime.now().isoformat()}
    )
    
    response = client.get(
        "/api/marketplace/bookings",
        headers={"Authorization": f"Bearer {p_token}"}
    )
    
    body = response.get_json()
    assert response.status_code == 200
    assert len(body["as_client"]) == 1
    assert len(body["as_provider"]) == 1
