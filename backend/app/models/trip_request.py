from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TripRequestStatus


class TripRequest(Base):
    """
    A requester's ask for a vehicle. Starts Pending. A dispatcher either
    approves it (which creates a Trip, see Trip model) or declines it with
    a mandatory reason. A requester can only ever see their own requests -
    enforced in the router/service layer, not just here.
    """

    __tablename__ = "trip_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    passenger_count: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[TripRequestStatus] = mapped_column(
        Enum(TripRequestStatus, name="trip_request_status", native_enum=False, length=20, create_constraint=True),
        nullable=False,
        default=TripRequestStatus.PENDING,
        index=True,
    )
    decline_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    requester: Mapped["User"] = relationship(back_populates="trip_requests")
    trip: Mapped["Trip | None"] = relationship(
        back_populates="request", uselist=False, cascade="all, delete-orphan"
    )
    traveler_links: Mapped[list["TripRequestTraveler"]] = relationship(
        back_populates="trip_request", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TripRequest id={self.id} status={self.status.value}>"
