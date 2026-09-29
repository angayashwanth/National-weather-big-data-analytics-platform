"""add_ml_latency_ms

Adds the ml_latency_ms column to the reports table.
This column records the milliseconds from report creation to ML pipeline
completion, enabling the avg_ml_latency_ms KPI.

Revision ID: 9bc596d72a44
Revises: 2188fb9e761d
Create Date: 2026-09-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '9bc596d72a44'
down_revision: Union[str, Sequence[str], None] = '2188fb9e761d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('reports', sa.Column('ml_latency_ms', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('reports', 'ml_latency_ms')
