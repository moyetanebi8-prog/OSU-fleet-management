from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LocationPing(Base):
    """
    A single GPS report from a vehicle.

    trip_id is nullable BY DESIGN (spec section 17/45): a vehicle can report
    GPS positions whether or not it's currently on a trip. gps_service
    (Phase 8/9) sets trip_id to the vehicle's current IN_PROGRESS trip if one
    exists at ping time, otherwise leaves it NULL. This is decided entirely
    server-side from DB state - the simulator/client never sends trip_id.
    """

    __tablename__ = "location_pings"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    trip_id: Mapped[int | None] = mapped_column(ForeignKey("trips.id"), nullable=True, index=True)

    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    speed: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Server-side timestamp only - never trust a client-supplied time.
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vehicle: Mapped["Vehicle"] = relationship(back_populates="location_pings")
    trip: Mapped["Trip | None"] = relationship(back_populates="location_pings")

    __table_args__ = (
        Index("ix_location_pings_vehicle_timestamp", "vehicle_id", "timestamp"),
        Index("ix_location_pings_trip_timestamp", "trip_id", "timestamp"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<LocationPing id={self.id} vehicle_id={self.vehicle_id} trip_id={self.trip_id}>"
