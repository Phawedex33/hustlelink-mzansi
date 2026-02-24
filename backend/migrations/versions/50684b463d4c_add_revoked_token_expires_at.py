"""add revoked token expires_at

Revision ID: 50684b463d4c
Revises: 299647d8ebb9
Create Date: 2026-02-17 14:48:15.683352

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '50684b463d4c'
down_revision = '299647d8ebb9'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    # Handle both paths:
    # 1) normal upgrade where revoked_tokens already exists
    # 2) stamped/misaligned DBs where revoked_tokens was never created
    if 'revoked_tokens' not in table_names:
        op.create_table(
            'revoked_tokens',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('jti', sa.String(length=36), nullable=False),
            sa.Column('revoked_at', sa.DateTime(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('revoked_tokens', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_revoked_tokens_jti'), ['jti'], unique=True)
            batch_op.create_index(batch_op.f('ix_revoked_tokens_expires_at'), ['expires_at'], unique=False)
    else:
        existing_columns = {column["name"] for column in inspector.get_columns("revoked_tokens")}
        existing_indexes = {index["name"] for index in inspector.get_indexes("revoked_tokens")}
        with op.batch_alter_table('revoked_tokens', schema=None) as batch_op:
            if 'expires_at' not in existing_columns:
                batch_op.add_column(sa.Column('expires_at', sa.DateTime(), nullable=True))
            if 'ix_revoked_tokens_expires_at' not in existing_indexes:
                batch_op.create_index(batch_op.f('ix_revoked_tokens_expires_at'), ['expires_at'], unique=False)
            if 'ix_revoked_tokens_jti' not in existing_indexes:
                batch_op.create_index(batch_op.f('ix_revoked_tokens_jti'), ['jti'], unique=True)

    # Backfill legacy rows to keep cleanup logic safe after deployment.
    op.execute("UPDATE revoked_tokens SET expires_at = revoked_at WHERE expires_at IS NULL")


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'revoked_tokens' not in set(inspector.get_table_names()):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("revoked_tokens")}
    existing_indexes = {index["name"] for index in inspector.get_indexes("revoked_tokens")}
    with op.batch_alter_table('revoked_tokens', schema=None) as batch_op:
        if 'ix_revoked_tokens_expires_at' in existing_indexes:
            batch_op.drop_index(batch_op.f('ix_revoked_tokens_expires_at'))
        if 'expires_at' in existing_columns:
            batch_op.drop_column('expires_at')
