from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import DriverStatus


class Driver(Base):
    """
    Drivers don't have login accounts in this system (they never
    authenticate - there's no driver-facing UI), which is exactly why
    `email` matters here: it's the only way to reach a driver directly for
    trip-assignment notifications (see app/services/notification_service.py).
    Nullable at the DB level for backward compatibility with drivers
    created before this column existed.
    """

    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    status: Mapped[DriverStatus] = mapped_column(
        Enum(DriverStatus, name="driver_status", native_enum=False, length=20, create_constraint=True),
        nullable=False,
        default=DriverStatus.AVAILABLE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trips: Mapped[list["Trip"]] = relationship(back_populates="driver")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Driver id={self.id} license={self.license_number!r} status={self.status.value}>"
