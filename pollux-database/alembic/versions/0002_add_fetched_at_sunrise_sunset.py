"""add fetched_at, sunrise, sunset

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'hourly_forecasts',
        sa.Column('fetched_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
    )

    op.add_column(
        'daily_forecasts',
        sa.Column('fetched_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
    )
    op.add_column(
        'daily_forecasts',
        sa.Column('sunrise', sa.String(), nullable=True),
    )
    op.add_column(
        'daily_forecasts',
        sa.Column('sunset', sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('daily_forecasts', 'sunset')
    op.drop_column('daily_forecasts', 'sunrise')
    op.drop_column('daily_forecasts', 'fetched_at')
    op.drop_column('hourly_forecasts', 'fetched_at')
