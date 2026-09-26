"""login_attempts: limit password, reset-code and sign-up guessing

Revision ID: b4c1f7a8e3cc
Revises: a3b0e6f7d2bb
Create Date: 2026-09-27 12:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = 'b4c1f7a8e3cc'
down_revision = 'a3b0e6f7d2bb'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'login_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=10), nullable=False, server_default='login'),
        sa.Column('subject', sa.String(length=140), nullable=False),
        sa.Column('identifier', sa.String(length=120), nullable=False),
        sa.Column('ip', sa.String(length=64), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_login_attempts_kind', 'login_attempts', ['kind'])
    op.create_index('ix_login_attempts_subject', 'login_attempts', ['subject'])
    op.create_index('ix_login_attempts_ip', 'login_attempts', ['ip'])
    op.create_index('ix_login_attempts_created_at', 'login_attempts', ['created_at'])


def downgrade():
    op.drop_index('ix_login_attempts_created_at', table_name='login_attempts')
    op.drop_index('ix_login_attempts_ip', table_name='login_attempts')
    op.drop_index('ix_login_attempts_subject', table_name='login_attempts')
    op.drop_index('ix_login_attempts_kind', table_name='login_attempts')
    op.drop_table('login_attempts')
