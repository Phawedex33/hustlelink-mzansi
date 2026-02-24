from datetime import UTC, datetime, timedelta

from app.extensions import db
from app.models.user import RevokedToken
from app.tasks.token_cleanup import cleanup_expired_revoked_tokens


def test_cleanup_expired_revoked_tokens_removes_only_expired(app):
    with app.app_context():
        now = datetime.now(UTC)
        expired = RevokedToken(
            jti="expired-jti",
            expires_at=now - timedelta(minutes=5),
            revoked_at=now - timedelta(minutes=10),
        )
        active = RevokedToken(
            jti="active-jti",
            expires_at=now + timedelta(minutes=30),
            revoked_at=now - timedelta(minutes=1),
        )
        db.session.add_all([expired, active])
        db.session.commit()

        deleted_rows = cleanup_expired_revoked_tokens()

        assert deleted_rows == 1
        assert RevokedToken.query.filter_by(jti="expired-jti").first() is None
        assert RevokedToken.query.filter_by(jti="active-jti").first() is not None
