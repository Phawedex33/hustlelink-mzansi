from datetime import UTC, datetime
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

class Provider(db.Model):
    __tablename__ = "providers"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone_number = db.Column(db.String(20))
    password_hash = db.Column(db.String(128), nullable=False)
    profile_pic = db.Column(db.String(200))
    certified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class RevokedToken(db.Model):
    __tablename__ = "revoked_tokens"

    id = db.Column(db.Integer, primary_key=True)
    # jti is the unique token ID from JWT payload; indexed for fast revocation checks.
    jti = db.Column(db.String(36), unique=True, nullable=False, index=True)
    # Store when revocation happened for auditing and optional cleanup jobs.
    revoked_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    # Track token expiry so cleanup can remove only records that are no longer needed.
    expires_at = db.Column(db.DateTime, nullable=False, index=True)


class AuthEvent(db.Model):
    __tablename__ = "auth_events"

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    subject_type = db.Column(db.String(32), nullable=False, index=True)
    subject_id = db.Column(db.String(64), nullable=True, index=True)
    ip = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)
