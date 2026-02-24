from datetime import datetime

from app.extensions import db
from app.models import Booking, Service, User
from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

marketplace_bp = Blueprint("marketplace", __name__)

def _error_response(message, status_code, code):
    return (
        jsonify(
            {
                "msg": message,
                "error": {
                    "code": code,
                    "message": message,
                    "request_id": getattr(g, "request_id", ""),
                },
            }
        ),
        status_code,
    )

# --- Service Routes ---

@marketplace_bp.route("/services", methods=["POST"])
@jwt_required()
def create_service():
    """Create a new service. Only for approved providers with complete profiles."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.provider_profile:
        return _error_response("User is not a provider", 403, "forbidden")
    
    if not user.is_active:
         return _error_response("User account is suspended", 403, "forbidden")

    if not user.provider_profile.can_list_services:
        return _error_response(
            "Provider profile must be complete and approved by admin before listing services",
            403,
            "forbidden"
        )

    data = request.get_json()
    required = ["title", "description", "category", "price"]
    for field in required:
        if not data.get(field):
            return _error_response(f"Field '{field}' is required", 400, "bad_request")

    service = Service(
        provider_id=user.provider_profile.id,
        title=data["title"],
        description=data["description"],
        category=data["category"],
        price=data["price"]
    )
    
    db.session.add(service)
    db.session.commit()

    return jsonify({
        "msg": "Service created successfully",
        "service": {
            "id": service.id,
            "title": service.title,
            "category": service.category,
            "price": float(service.price)
        }
    }), 201

@marketplace_bp.route("/services", methods=["GET"])
def list_services():
    """List all active services. Public access."""
    category = request.args.get("category")
    query = Service.query.filter_by(is_active=True)
    
    if category:
        query = query.filter_by(category=category)
        
    services = query.all()
    return jsonify([
        {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "category": s.category,
            "price": float(s.price),
            "provider": {
                "id": s.provider.id,
                "business_name": s.provider.business_name
            }
        } for s in services
    ]), 200

# --- Booking Routes ---

@marketplace_bp.route("/bookings", methods=["POST"])
@jwt_required()
def create_booking():
    """Book a service. Any active user can book."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.is_active:
        return _error_response("Unauthorized or account suspended", 403, "forbidden")

    data = request.get_json()
    service_id = data.get("service_id")
    scheduled_at_str = data.get("scheduled_at")

    if not service_id or not scheduled_at_str:
        return _error_response("Service ID and schedule time required", 400, "bad_request")

    service = Service.query.get(service_id)
    if not service or not service.is_active:
        return _error_response("Service not found or inactive", 404, "not_found")

    try:
        scheduled_at = datetime.fromisoformat(scheduled_at_str)
    except ValueError:
        return _error_response("Invalid date format. Use ISO format.", 400, "bad_request")

    booking = Booking(
        service_id=service.id,
        client_id=user.id,
        scheduled_at=scheduled_at,
        status="pending"
    )
    
    db.session.add(booking)
    db.session.commit()

    return jsonify({
        "msg": "Booking created successfully",
        "booking": {
            "id": booking.id,
            "status": booking.status,
            "scheduled_at": booking.scheduled_at.isoformat()
        }
    }), 201

@marketplace_bp.route("/bookings", methods=["GET"])
@jwt_required()
def list_user_bookings():
    """List bookings for the current user (as client or provider)."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # As client
    client_bookings = Booking.query.filter_by(client_id=user.id).all()
    
    # As provider
    provider_bookings = []
    if user.provider_profile:
        provider_bookings = Booking.query.join(Service).filter(
            Service.provider_id == user.provider_profile.id
        ).all()

    return jsonify({
        "as_client": [
            {
                "id": b.id,
                "service_title": b.service.title,
                "status": b.status,
                "scheduled_at": b.scheduled_at.isoformat()
            } for b in client_bookings
        ],
        "as_provider": [
            {
                "id": b.id,
                "service_title": b.service.title,
                "client_phone": b.client.phone_number,
                "status": b.status,
                "scheduled_at": b.scheduled_at.isoformat()
            } for b in provider_bookings
        ]
    }), 200
