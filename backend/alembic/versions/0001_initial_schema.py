"""create initial schema (users, vehicles, drivers, trip_requests, trips,
location_pings, alerts, geofences)

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-01

NOTE: This migration was hand-written (not produced by `alembic
autogenerate`) because this development environment has no network access
to install SQLAlemy/psycopg/GeoAlchemy2 or connect to a live PostgreSQL
instance. It was written to match app/models/*.py exactly, field for field.

Before trusting it in a real environment, run:
    alembic upgrade head
against a fresh database and diff `alembic revision --autogenerate` output
(it should come back empty) to confirm it matches the ORM models exactly.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostGIS is required for the geofences.geometry column.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=128), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("requester", "dispatcher", name="user_role", native_enum=False, length=20),
            nullable=False,
            server_default="requester",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "vehicles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("plate_number", sa.String(length=32), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "available", "assigned", "in_progress", "maintenance", "inactive",
                name="vehicle_status", native_enum=False, length=20,
            ),
            nullable=False,
            server_default="available",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vehicles_plate_number", "vehicles", ["plate_number"], unique=True)

    op.create_table(
        "drivers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("license_number", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "available", "assigned", "driving", "inactive",
                name="driver_status", native_enum=False, length=20,
            ),
            nullable=False,
            server_default="available",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_drivers_license_number", "drivers", ["license_number"], unique=True)

    op.create_table(
        "trip_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("purpose", sa.String(length=255), nullable=False),
        sa.Column("destination", sa.String(length=255), nullable=False),
        sa.Column("requested_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("passenger_count", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "approved", "declined",
                name="trip_request_status", native_enum=False, length=20,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("decline_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_trip_requests_requester_id", "trip_requests", ["requester_id"])
    op.create_index("ix_trip_requests_status", "trip_requests", ["status"])

    op.create_table(
        "trips",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "request_id", sa.Integer(), sa.ForeignKey("trip_requests.id"), nullable=False, unique=True
        ),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "approved", "in_progress", "completed", "cancelled",
                name="trip_status", native_enum=False, length=20,
            ),
            nullable=False,
            server_default="approved",
        ),
        sa.Column("planned_start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("planned_end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_lat", sa.Float(), nullable=True),
        sa.Column("start_lng", sa.Float(), nullable=True),
        sa.Column("end_lat", sa.Float(), nullable=True),
        sa.Column("end_lng", sa.Float(), nullable=True),
        sa.Column("distance_km", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_trips_vehicle_id", "trips", ["vehicle_id"])
    op.create_index("ix_trips_driver_id", "trips", ["driver_id"])
    op.create_index("ix_trips_status", "trips", ["status"])

    op.create_table(
        "location_pings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("trip_id", sa.Integer(), sa.ForeignKey("trips.id"), nullable=True),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("speed", sa.Float(), nullable=False, server_default="0"),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_location_pings_vehicle_id", "location_pings", ["vehicle_id"])
    op.create_index("ix_location_pings_trip_id", "location_pings", ["trip_id"])
    op.create_index(
        "ix_location_pings_vehicle_timestamp", "location_pings", ["vehicle_id", "timestamp"]
    )
    op.create_index("ix_location_pings_trip_timestamp", "location_pings", ["trip_id", "timestamp"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("trip_id", sa.Integer(), sa.ForeignKey("trips.id"), nullable=True),
        sa.Column(
            "type",
            sa.Enum(
                "SPEEDING", "GEOFENCE_EXIT", "GEOFENCE_ENTRY", "SYSTEM",
                name="alert_type", native_enum=False, length=20,
            ),
            nullable=False,
        ),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_alerts_vehicle_id", "alerts", ["vehicle_id"])
    op.create_index("ix_alerts_trip_id", "alerts", ["trip_id"])
    op.create_index("ix_alerts_vehicle_timestamp", "alerts", ["vehicle_id", "timestamp"])

    op.create_table(
        "geofences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "geometry",
            Geometry(geometry_type="POLYGON", srid=4326),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("geofences")
    op.drop_table("alerts")
    op.drop_table("location_pings")
    op.drop_table("trips")
    op.drop_table("trip_requests")
    op.drop_table("drivers")
    op.drop_table("vehicles")
    op.drop_table("users")
