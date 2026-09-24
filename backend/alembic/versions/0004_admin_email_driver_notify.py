"""add admin role, user/driver email columns, notification driver recipient

Revision ID: 0004_admin_email_driver_notify
Revises: 0003_travelers_and_notifications
Create Date: 2026-09-10

Three independent changes, bundled in one migration since they're all
part of the same feature (admin-managed employees + real driver email
notifications):

1. `users.role` CHECK constraint extended to allow 'admin' (third role,
   alongside 'requester'/'dispatcher').
2. `email` column added to `users` and `drivers` (nullable, for backward
   compatibility with existing rows - going forward the application layer
   requires it for every newly-created account).
3. `notifications.recipient_user_id` becomes nullable, `recipient_driver_id`
   and `recipient_email` are added, so a driver (who has no User login) can
   be a tracked notification recipient too - closing the exact gap flagged
   in 0003's original design.

KNOWN UNCERTAINTY, stated plainly: step 1 assumes the CHECK constraint
SQLAlchemy generated for the non-native `role` enum back in 0001 is named
literally `user_role` (matching the `name="user_role"` passed to
`sa.Enum(...)` in that migration) - this is standard SQLAlchemy behavior
for non-native enums, but has not been verified against a live database in
this build environment. If `DROP CONSTRAINT user_role` fails with "does
not exist," find the real name first:

    SELECT conname FROM pg_constraint
    WHERE conrelid = 'users'::regclass AND contype = 'c';

then edit this migration's constraint name to match before re-running.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_admin_email_driver_notify"
down_revision: Union[str, None] = "0003_travelers_and_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. extend users.role to allow 'admin' ---

    op.create_check_constraint(
        "user_role",
        "users",
        "role IN ('requester', 'dispatcher', 'admin')"
    )

    # --- 2. email columns ---
    op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    op.add_column("drivers", sa.Column("email", sa.String(length=255), nullable=True))

    # --- 3. notifications: support a driver as recipient ---
    op.alter_column("notifications", "recipient_user_id", nullable=True)
    op.add_column(
        "notifications", sa.Column("recipient_driver_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_notifications_recipient_driver_id",
        "notifications",
        "drivers",
        ["recipient_driver_id"],
        ["id"],
    )
    op.create_index(
        "ix_notifications_recipient_driver_id", "notifications", ["recipient_driver_id"]
    )

    # recipient_email: add nullable, backfill from the existing user
    # relationship for any rows that already exist, THEN make it required.
    op.add_column("notifications", sa.Column("recipient_email", sa.String(length=255), nullable=True))
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE notifications
            SET recipient_email = users.email
            FROM users
            WHERE notifications.recipient_user_id = users.id
              AND notifications.recipient_email IS NULL
              AND users.email IS NOT NULL
            """
        )
    )
    # Any remaining NULLs (recipient's email was itself null, or somehow
    # orphaned) get a placeholder rather than leaving nulls before the
    # NOT NULL constraint is applied - this should be rare-to-never on a
    # fresh install but keeps the migration safe on existing data.
    connection.execute(
        sa.text(
            "UPDATE notifications SET recipient_email = 'unknown@unknown.invalid' "
            "WHERE recipient_email IS NULL"
        )
    )
    op.alter_column("notifications", "recipient_email", nullable=False)

    op.create_check_constraint(
        "ck_notification_exactly_one_recipient",
        "notifications",
        "(recipient_user_id IS NOT NULL) != (recipient_driver_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_notification_exactly_one_recipient", "notifications", type_="check")
    op.drop_column("notifications", "recipient_email")
    op.drop_index("ix_notifications_recipient_driver_id", table_name="notifications")
    op.drop_constraint("fk_notifications_recipient_driver_id", "notifications", type_="foreignkey")
    op.drop_column("notifications", "recipient_driver_id")
    op.alter_column("notifications", "recipient_user_id", nullable=False)

    op.drop_column("drivers", "email")

    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_column("users", "email")

    op.drop_constraint("user_role", "users", type_="check")
    op.create_check_constraint("user_role", "users", "role IN ('requester', 'dispatcher')")
