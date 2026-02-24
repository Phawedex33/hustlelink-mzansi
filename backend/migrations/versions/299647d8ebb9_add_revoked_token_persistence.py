"""add revoked token persistence

Revision ID: 299647d8ebb9
Revises: 2299924f9fbe
Create Date: 2026-02-17 13:09:33.012860

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '299647d8ebb9'
down_revision = '2299924f9fbe'
branch_labels = None
depends_on = None


def upgrade():
    # Persist revoked JWT IDs (jti) so logout revocation works across instances.
    op.create_table('revoked_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('jti', sa.String(length=36), nullable=False),
    sa.Column('revoked_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('revoked_tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_revoked_tokens_jti'), ['jti'], unique=True)



def downgrade():
    # Reverse revoked-token persistence table.
    with op.batch_alter_table('revoked_tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_revoked_tokens_jti'))

    op.drop_table('revoked_tokens')
