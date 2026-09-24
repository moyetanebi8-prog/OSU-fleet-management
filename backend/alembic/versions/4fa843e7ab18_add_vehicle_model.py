"""add vehicle model

Revision ID: 4fa843e7ab18
Revises: 0004_admin_email_driver_notify
Create Date: 2026-09-21 15:27:46.732732

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4fa843e7ab18"
down_revision: Union[str, None] = "0004_admin_email_driver_notify"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vehicles",
        sa.Column("model", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vehicles", "model")