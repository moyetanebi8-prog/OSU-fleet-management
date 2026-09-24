from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import AlertType


class Alert(Base):
    """
    A fleet event worth a dispatcher's attention: speeding, geofence
    entry/exit, or system-level notices. alert_service (Phase 12) is
    responsible for de-duplicating - e.g. one SPEEDING alert per continuous
    speeding event, not one per GPS ping (spec section 22/23).
    """

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    trip_id: Mapped[int | None] = mapped_column(ForeignKey("trips.id"), nullable=True, index=True)

    type: Mapped[AlertType] = mapped_column(
        Enum(AlertType, name="alert_type", native_enum=False, length=20, create_constraint=True), nullable=False
    )
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="alerts")
    trip: Mapped["Trip | None"] = relationship(back_populates="alerts")

    __table_args__ = (Index("ix_alerts_vehicle_timestamp", "vehicle_id", "timestamp"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Alert id={self.id} type={self.type.value} vehicle_id={self.vehicle_id}>"
