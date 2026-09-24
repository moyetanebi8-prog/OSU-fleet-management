from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Geofence(Base):
    """
    A named polygon area (e.g. "Main Depot") stored as real PostGIS geometry
    (SRID 4326 / WGS84, same as GPS lat/lng) so containment checks
    (ST_Contains) run in the database, not by hand-rolled point-in-polygon
    code in Python. geofence_service (Phase 11) diffs each vehicle's
    "currently inside" state ping-to-ping to avoid duplicate alerts.
    """

    __tablename__ = "geofences"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    geometry: Mapped[str] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326), nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Geofence id={self.id} name={self.name!r}>"
