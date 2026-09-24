"""create vehicle_geofence_states table

Revision ID: 0002_geofence_state
Revises: 0001_initial_schema
Create Date: 2026-09-02

Hand-written for the same reason as 0001 (see its docstring) - no network
in this dev environment to run `alembic autogenerate` against a live DB.
Written field-for-field against app/models/geofence_state.py.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_geofence_state"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vehicle_geofence_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("geofence_id", sa.Integer(), sa.ForeignKey("geofences.id"), nullable=False),
        sa.Column("is_inside", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.UniqueConstraint("vehicle_id", "geofence_id", name="uq_vehicle_geofence_state"),
    )
    op.create_index(
        "ix_vehicle_geofence_states_vehicle_id", "vehicle_geofence_states", ["vehicle_id"]
    )
    op.create_index(
        "ix_vehicle_geofence_states_geofence_id", "vehicle_geofence_states", ["geofence_id"]
    )


def downgrade() -> None:
    op.drop_table("vehicle_geofence_states")
