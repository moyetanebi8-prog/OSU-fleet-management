from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TripRequestTraveler(Base):
    """
    Links a TripRequest to every employee actually traveling on it - the
    requester is always one of these rows too (auto-added server-side, see
    trip_service.create_trip_request_with_travelers), never implied only
    by passenger_count.

    "Employee" in this system means an active User account with role
    `requester` - there's no separate employee directory, so travelers are
    selected from the same accounts people log in with. See
    app/routers/users.py for the search endpoint the traveler picker uses.
    """

    __tablename__ = "trip_request_travelers"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_request_id: Mapped[int] = mapped_column(
        ForeignKey("trip_requests.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trip_request: Mapped["TripRequest"] = relationship(back_populates="traveler_links")
    user: Mapped["User"] = relationship()

    __table_args__ = (
        # The same employee can never appear twice on the same request -
        # enforced at the database level, not just checked in Python.
        UniqueConstraint("trip_request_id", "user_id", name="uq_trip_request_traveler"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TripRequestTraveler trip_request_id={self.trip_request_id} user_id={self.user_id}>"
