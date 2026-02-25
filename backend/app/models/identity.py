from app.extensions import db
from werkzeug.security import check_password_hash, generate_password_hash

from .base import TimestampMixin


class User(db.Model, TimestampMixin):
    """Core User model for phone-based authentication."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(128), nullable=True)

    # Status flags
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)

    # Verification details
    phone_verified_at = db.Column(db.DateTime, nullable=True)
    id_verified_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    profile = db.relationship(
        "Profile", backref="user", uselist=False, cascade="all, delete-orphan"
    )
    provider_profile = db.relationship(
        "ProviderProfile", backref="user", uselist=False, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.phone_number}>"


class Profile(db.Model, TimestampMixin):
    """Stores personal information for all users."""

    __tablename__ = "profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )

    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    profile_pic_url = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.Text, nullable=True)

    @property
    def is_complete(self):
        """Check if basic profile info is filled out."""
        return all([self.first_name, self.last_name])

    def __repr__(self):
        return f"<Profile {self.first_name} {self.last_name}>"


class ProviderProfile(db.Model, TimestampMixin):
    """Stores service-related information for providers."""

    __tablename__ = "provider_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )

    business_name = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    average_rating = db.Column(db.Float, default=0.0)

    # Status
    is_verified = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)

    @property
    def can_list_services(self):
        """Business rule: Provider cannot create services until profile is fully completed."""
        if not self.user or not self.user.profile:
            return False
        return self.user.profile.is_complete and self.is_approved

    def __repr__(self):
        return f"<ProviderProfile {self.business_name or self.user_id}>"
