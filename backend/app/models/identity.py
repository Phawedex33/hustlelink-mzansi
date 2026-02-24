from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from .base import TimestampMixin

class UserMixin:
    """Shared mixin for user-like entities with passwords."""
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Provider(db.Model, UserMixin, TimestampMixin):
    __tablename__ = "providers"

    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20))
    profile_pic = db.Column(db.String(200))
    certified = db.Column(db.Boolean, default=False)

class Admin(db.Model, UserMixin, TimestampMixin):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
