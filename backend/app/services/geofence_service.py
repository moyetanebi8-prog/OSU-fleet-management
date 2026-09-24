"""
Geofence enter/exit detection (spec section 21).

Containment is computed by PostgreSQL/PostGIS itself (ST_Contains), not by
hand-rolled point-in-polygon math in Python. To avoid creating a new Alert
on every single ping while a vehicle happens to be sitting inside (or
outside) a geofence, each vehicle's last-known containment state per
geofence is cached in `vehicle_geofence_states` - an alert (and a state
update) is only produced when the computed state actually differs from
that cache.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.enums import AlertType
from app.models.geofence import Geofence
from app.models.geofence_state import VehicleGeofenceState
from app.models.location_ping import LocationPing


def process_ping(db: Session, ping: LocationPing) -> list[Alert]:
    geofences = db.query(Geofence).filter(Geofence.is_active.is_(True)).all()
    if not geofences:
        return []

    point = func.ST_SetSRID(func.ST_MakePoint(ping.lng, ping.lat), 4326)
    new_alerts: list[Alert] = []

    for geofence in geofences:
        # Filtering by Geofence.id + ST_Contains(Geofence.geometry, point) as
        # a single column-expression query (rather than passing the
        # already-loaded `geofence.geometry` Python value back into a new
        # expression) is the more standard GeoAlchemy2 usage pattern and
        # keeps the whole containment check as one clean SQL predicate.
        is_inside = (
            db.query(Geofence.id)
            .filter(Geofence.id == geofence.id, func.ST_Contains(Geofence.geometry, point))
            .first()
            is not None
        )

        state = (
            db.query(VehicleGeofenceState)
            .filter(
                VehicleGeofenceState.vehicle_id == ping.vehicle_id,
                VehicleGeofenceState.geofence_id == geofence.id,
            )
            .first()
        )
        was_inside = state.is_inside if state is not None else False

        if is_inside == was_inside:
            continue  # no change in containment -> no alert, no duplicate spam

        alert = Alert(
            vehicle_id=ping.vehicle_id,
            trip_id=ping.trip_id,
            type=AlertType.GEOFENCE_ENTRY if is_inside else AlertType.GEOFENCE_EXIT,
            message=(
                f"Vehicle entered geofence '{geofence.name}'."
                if is_inside
                else f"Vehicle exited geofence '{geofence.name}'."
            ),
        )
        db.add(alert)
        new_alerts.append(alert)

        if state is None:
            db.add(
                VehicleGeofenceState(
                    vehicle_id=ping.vehicle_id, geofence_id=geofence.id, is_inside=is_inside
                )
            )
        else:
            state.is_inside = is_inside

    if new_alerts:
        db.commit()
        for alert in new_alerts:
            db.refresh(alert)

    return new_alerts
