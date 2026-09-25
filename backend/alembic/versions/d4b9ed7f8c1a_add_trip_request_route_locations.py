"""add trip request route locations

Revision ID: d4b9ed7f8c1a
Revises: 4fa843e7ab18
Create Date: 2026-09-24 13:34:04.934304

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4b9ed7f8c1a"
down_revision: Union[str, None] = "4fa843e7ab18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trip_requests",
        sa.Column("source", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "trip_requests",
        sa.Column("source_lat", sa.Float(), nullable=True),
    )
    op.add_column(
        "trip_requests",
        sa.Column("source_lng", sa.Float(), nullable=True),
    )
    op.add_column(
        "trip_requests",
        sa.Column("destination_lat", sa.Float(), nullable=True),
    )
    op.add_column(
        "trip_requests",
        sa.Column("destination_lng", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("trip_requests", "destination_lng")
    op.drop_column("trip_requests", "destination_lat")
    op.drop_column("trip_requests", "source_lng")
    op.drop_column("trip_requests", "source_lat")
    op.drop_column("trip_requests", "source")