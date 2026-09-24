"""add trip_request_travelers and notifications tables

Revision ID: 0003_travelers_and_notifications
Revises: 0002_geofence_state
Create Date: 2026-09-08

Adds explicit traveler tracking to trip requests (who is actually going,
not just a trusted passenger_count) and a Notification table for tracking
trip-approval notifications sent to requesters/travelers/drivers.

BACKWARD COMPATIBILITY (spec section 13 - do not destroy existing data):
existing trip_requests rows are untouched. For each one, this migration
inserts exactly one trip_request_travelers row: the request's own
requester as its sole traveler. This does NOT invent additional
travelers - it just makes "the requester is a traveler" true for old data
the same way it's now enforced for new data going forward. passenger_count
on those old rows is left as-is (whatever was originally submitted) since
we have no way to know who else, if anyone, actually traveled on a
historical trip - only new requests compute passenger_count from the
traveler list.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_travelers_and_notifications"
down_revision: Union[str, None] = "0002_geofence_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trip_request_travelers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "trip_request_id", sa.Integer(), sa.ForeignKey("trip_requests.id"), nullable=False
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("trip_request_id", "user_id", name="uq_trip_request_traveler"),
    )
    op.create_index(
        "ix_trip_request_travelers_trip_request_id", "trip_request_travelers", ["trip_request_id"]
    )
    op.create_index("ix_trip_request_travelers_user_id", "trip_request_travelers", ["user_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipient_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "trip_request_id", sa.Integer(), sa.ForeignKey("trip_requests.id"), nullable=True
        ),
        sa.Column("trip_id", sa.Integer(), sa.ForeignKey("trips.id"), nullable=True),
        sa.Column(
            "type",
            sa.Enum(
                "TRIP_APPROVED_REQUESTER",
                "TRIP_APPROVED_TRAVELER",
                "TRIP_APPROVED_DRIVER",
                name="notification_type",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "sent", "failed",
                name="notification_status", native_enum=False, length=20,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notifications_recipient_user_id", "notifications", ["recipient_user_id"])
    op.create_index("ix_notifications_trip_request_id", "notifications", ["trip_request_id"])
    op.create_index("ix_notifications_trip_id", "notifications", ["trip_id"])

    # --- backfill: every existing trip_request gets its requester as a traveler ---
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO trip_request_travelers (trip_request_id, user_id)
            SELECT id, requester_id FROM trip_requests
            """
        )
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("trip_request_travelers")
