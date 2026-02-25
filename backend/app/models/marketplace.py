from typing import TYPE_CHECKING

from app.extensions import db

from .base import TimestampMixin

if TYPE_CHECKING:
    pass


class Service(db.Model, TimestampMixin):
    """Services offered by providers."""

    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(
        db.Integer, db.ForeignKey("provider_profiles.id"), nullable=False
    )

    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    provider = db.relationship("ProviderProfile", backref="services")

    def __repr__(self):
        return f"<Service {self.title}>"


class Booking(db.Model, TimestampMixin):
    """Bookings made by clients for services."""

    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    scheduled_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(
        db.String(20), default="pending", index=True
    )  # pending, confirmed, completed, cancelled

    # Optional feedback
    rating = db.Column(db.Integer, nullable=True)
    comment = db.Column(db.Text, nullable=True)

    # Relationships
    service = db.relationship("Service", backref="bookings")
    client = db.relationship("User", backref="bookings")

    def __repr__(self):
        return f"<Booking {self.id} - {self.status}>"
