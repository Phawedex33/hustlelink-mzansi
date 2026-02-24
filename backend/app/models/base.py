from datetime import UTC, datetime
from app.extensions import db

class TimestampMixin:
    """Mixin to add created_at timestamp to models."""
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
