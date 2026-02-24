from datetime import UTC, datetime

from app.extensions import db
from app.models import RevokedToken


def cleanup_expired_revoked_tokens():
    """Delete revoked-token records that are already past their JWT expiry."""
    now = datetime.now(UTC)
    deleted_rows = (
        db.session.query(RevokedToken)
        .filter(RevokedToken.expires_at <= now)
        .delete(synchronize_session=False)
    )
    db.session.commit()
    return deleted_rows
