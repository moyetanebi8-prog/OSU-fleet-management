from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import VehicleStatus


class Vehicle(Base):
    """
    A fleet vehicle. Status is managed exclusively by backend business logic
    (trip_service, not arbitrary client input) - see spec section 7.
    """

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    plate_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[VehicleStatus] = mapped_column(
        Enum(VehicleStatus, name="vehicle_status", native_enum=False, length=20, create_constraint=True),
        nullable=False,
        default=VehicleStatus.AVAILABLE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trips: Mapped[list["Trip"]] = relationship(back_populates="vehicle")
    location_pings: Mapped[list["LocationPing"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Vehicle id={self.id} plate={self.plate_number!r} status={self.status.value}>"
