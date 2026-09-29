"""initial_schema

Full initial schema creation for wx.db / PostgreSQL.
Creates the 'reports' table with all columns from Section 2.3.2.

Revision ID: 2188fb9e761d
Revises:
Create Date: 2026-09-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '2188fb9e761d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the reports table and all required indexes."""
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),

        # ── Section 2.3.2 core schema ─────────────────────────────────────────
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('city', sa.String(128), nullable=False, index=True),
        sa.Column('state', sa.String(128), nullable=False, index=True),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lon', sa.Float(), nullable=True),
        sa.Column('photos', sa.Text(), nullable=False, server_default=''),
        sa.Column('videos', sa.Text(), nullable=False, server_default=''),
        sa.Column('event_category', sa.String(32), nullable=False, index=True),
        sa.Column('source_type', sa.String(32), nullable=False),
        sa.Column('verification_status', sa.String(32), nullable=False,
                  server_default='unverified', index=True),
        sa.Column('trust_score', sa.Float(), nullable=False, server_default='0.0'),

        # ── Extended fields ────────────────────────────────────────────────────
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('source_handle', sa.String(256), nullable=True),

        # ── ML pipeline outputs ───────────────────────────────────────────────
        sa.Column('classify_conf', sa.Float(), nullable=True),
        sa.Column('fake_score', sa.Float(), nullable=True),
        sa.Column('high_impact', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('duplicate_of', sa.Integer(), nullable=True),
        sa.Column('ml_verdict', sa.String(32), nullable=True),
        sa.Column('ml_latency_ms', sa.Float(), nullable=True),

        # ── Admin panel ────────────────────────────────────────────────────────
        sa.Column('reviewed_by', sa.String(128), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),

        # ── Audit timestamps ───────────────────────────────────────────────────
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )



def downgrade() -> None:
    """Drop the reports table."""
    op.drop_table('reports')
