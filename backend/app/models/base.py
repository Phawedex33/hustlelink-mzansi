from datetime import UTC, datetime
from app.extensions import db
import typing as t

if t.TYPE_CHECKING:
    from flask_sqlalchemy import SQLAlchemy
    db: SQLAlchemy

class TimestampMixin:
    """Mixin to add created_at timestamp to models."""
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
