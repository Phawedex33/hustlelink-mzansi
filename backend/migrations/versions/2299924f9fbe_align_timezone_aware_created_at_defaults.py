"""align timezone-aware created_at defaults

Revision ID: 2299924f9fbe
Revises: 0d20cc9c9d80
Create Date: 2026-02-17 04:42:25.968724

"""

# revision identifiers, used by Alembic.
revision = '2299924f9fbe'
down_revision = '0d20cc9c9d80'
branch_labels = None
depends_on = None


def upgrade():
    # Application-level default switched to timezone-aware UTC in ORM model:
    # default=lambda: datetime.now(UTC). No DB schema change is required.
    pass


def downgrade():
    pass
