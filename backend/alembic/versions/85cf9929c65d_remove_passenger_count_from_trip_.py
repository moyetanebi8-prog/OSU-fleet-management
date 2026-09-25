"""remove passenger count from trip requests

Revision ID: 85cf9929c65d
Revises: d4b9ed7f8c1a
Create Date: 2026-09-25 15:50:02.816716

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85cf9929c65d'
down_revision: Union[str, None] = 'd4b9ed7f8c1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("trip_requests", "passenger_count")


def downgrade() -> None:
    op.add_column(
        "trip_requests",
        sa.Column(
            "passenger_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
