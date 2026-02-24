from datetime import UTC, datetime
from app.extensions import db
from .base import TimestampMixin

class RevokedToken(db.Model):
    __tablename__ = "revoked_tokens"

    id = db.Column(db.Integer, primary_key=True)
    # jti is the unique token ID from JWT payload
    jti = db.Column(db.String(36), unique=True, nullable=False, index=True)
    revoked_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)

class AuthEvent(db.Model, TimestampMixin):
    __tablename__ = "auth_events"

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    subject_type = db.Column(db.String(32), nullable=False, index=True)
    subject_id = db.Column(db.String(64), nullable=True, index=True)
    ip = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
