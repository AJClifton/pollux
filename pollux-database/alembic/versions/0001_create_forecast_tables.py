"""create forecast tables

Revision ID: 0001
Revises:
Create Date: 2026-03-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'hourly_forecasts',
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('datetime', sa.DateTime(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('dewpoint', sa.Float(), nullable=True),
        sa.Column('rain', sa.Float(), nullable=True),
        sa.Column('cloud_cover_total', sa.Float(), nullable=True),
        sa.Column('cloud_cover_low', sa.Float(), nullable=True),
        sa.Column('cloud_cover_mid', sa.Float(), nullable=True),
        sa.Column('cloud_cover_high', sa.Float(), nullable=True),
        sa.Column('visibility', sa.Float(), nullable=True),
        sa.Column('surface_pressure', sa.Float(), nullable=True),
        sa.Column('wind_speed', sa.Float(), nullable=True),
        sa.Column('wind_direction', sa.Float(), nullable=True),
        sa.Column('wind_gusts', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('latitude', 'longitude', 'datetime'),
    )

    op.create_table(
        'daily_forecasts',
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('weather_code', sa.Integer(), nullable=True),
        sa.Column('maximum_temperature', sa.Float(), nullable=True),
        sa.Column('minimum_temperature', sa.Float(), nullable=True),
        sa.Column('precipitation_sum', sa.Float(), nullable=True),
        sa.Column('precipitation_probability_max', sa.Float(), nullable=True),
        sa.Column('maximum_wind_speed', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('latitude', 'longitude', 'date'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('daily_forecasts')
    op.drop_table('hourly_forecasts')
