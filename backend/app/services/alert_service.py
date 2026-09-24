"""
Speed alert detection (spec sections 22-23).

Mirrors geofence_service's transition-based approach, but instead of a
separate state table, uses the vehicle's own immediately-previous
LocationPing as the "was this already happening" signal: a SPEEDING alert
is only created when the current ping exceeds the limit AND the ping
immediately before it did not (or didn't exist). A whole continuous
speeding event - dozens of pings in a row, all over the limit - produces
exactly one alert, at its start; slowing back down and speeding up again
later produces a second, separate alert.
"""

from sqlalchemy.orm import Session

from app.config import settings
from app.models.alert import Alert
from app.models.enums import AlertType
from app.models.location_ping import LocationPing


def process_speed_alert(db: Session, ping: LocationPing) -> Alert | None:
    speed_limit = settings.DEFAULT_SPEED_LIMIT_KMH

    if ping.speed <= speed_limit:
        return None

    previous_ping = (
        db.query(LocationPing)
        .filter(LocationPing.vehicle_id == ping.vehicle_id, LocationPing.id != ping.id)
        .order_by(LocationPing.timestamp.desc(), LocationPing.id.desc())
        .first()
    )
    if previous_ping is not None and previous_ping.speed > speed_limit:
        return None  # continuation of an already-flagged speeding event

    alert = Alert(
        vehicle_id=ping.vehicle_id,
        trip_id=ping.trip_id,
        type=AlertType.SPEEDING,
        message=(
            f"Vehicle exceeded the speed limit: {ping.speed:.1f} km/h "
            f"(limit {speed_limit:.1f} km/h)."
        ),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
