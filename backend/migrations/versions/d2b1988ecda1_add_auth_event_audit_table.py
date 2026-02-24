"""add auth event audit table

Revision ID: d2b1988ecda1
Revises: 50684b463d4c
Create Date: 2026-02-17 23:00:22.211022

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2b1988ecda1'
down_revision = '50684b463d4c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'auth_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('subject_type', sa.String(length=32), nullable=False),
        sa.Column('subject_id', sa.String(length=64), nullable=True),
        sa.Column('ip', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('auth_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_auth_events_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_auth_events_event_type'), ['event_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_auth_events_subject_id'), ['subject_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_auth_events_subject_type'), ['subject_type'], unique=False)


def downgrade():
    with op.batch_alter_table('auth_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_auth_events_subject_type'))
        batch_op.drop_index(batch_op.f('ix_auth_events_subject_id'))
        batch_op.drop_index(batch_op.f('ix_auth_events_event_type'))
        batch_op.drop_index(batch_op.f('ix_auth_events_created_at'))

    op.drop_table('auth_events')
