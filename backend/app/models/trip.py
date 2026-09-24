from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TripStatus


class Trip(Base):
    """
    Created exactly once a TripRequest is approved (trip_service.approve_request,
    Phase 6), inside the same DB transaction that assigns the vehicle/driver
    and flips the request status. Lives through Approved -> In Progress ->
    Completed/Cancelled.

    start_lat/lng and end_lat/lng are captured from real GPS at start/complete
    time (Phase 7/8) - never fabricated. distance_km is computed from this
    trip's own LocationPing rows only (Phase 10), never from unrelated
    vehicle history.
    """

    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("trip_requests.id"), nullable=False, unique=True, index=True
    )
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)

    status: Mapped[TripStatus] = mapped_column(
        Enum(TripStatus, name="trip_status", native_enum=False, length=20, create_constraint=True),
        nullable=False,
        default=TripStatus.APPROVED,
        index=True,
    )

    planned_start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    planned_end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    actual_start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    start_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request: Mapped["TripRequest"] = relationship(back_populates="trip")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="trips")
    driver: Mapped["Driver"] = relationship(back_populates="trips")

    location_pings: Mapped[list["LocationPing"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(back_populates="trip", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Trip id={self.id} status={self.status.value}>"
