from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VehicleGeofenceState(Base):
    """
    Tracks whether a vehicle is CURRENTLY considered inside a given
    geofence. geofence_service (see app/services/geofence_service.py) only
    emits an Alert when this actually flips between pings - never one
    alert per ping for every moment a vehicle happens to be parked inside
    a depot geofence (spec section 21: "Track the vehicle's previous
    geofence state... do not continuously create duplicate alerts").
    """

    __tablename__ = "vehicle_geofence_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    geofence_id: Mapped[int] = mapped_column(ForeignKey("geofences.id"), nullable=False, index=True)
    is_inside: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("vehicle_id", "geofence_id", name="uq_vehicle_geofence_state"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<VehicleGeofenceState vehicle_id={self.vehicle_id} "
            f"geofence_id={self.geofence_id} is_inside={self.is_inside}>"
        )
