"""
GPS ping ingestion (spec sections 15-17, 45).

The one rule that matters most here: a ping's `trip_id` is decided
ENTIRELY server-side, from whether the vehicle currently has an
`in_progress` Trip - never from anything the client (GPS device/simulator)
sends, because PingCreate has no trip_id field at all. This is what keeps
"general vehicle tracking" and "this specific trip's route" cleanly
separated: a vehicle pinging while idle, or while merely `approved` for a
future trip, gets trip_id=NULL; a vehicle pinging while `in_progress`
gets every ping tagged to that trip; once the trip is `completed`, new
pings fall back to NULL again automatically, because the query below
simply won't find an in_progress trip anymore.
"""

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.enums import TripStatus
from app.models.location_ping import LocationPing
from app.models.trip import Trip
from app.models.vehicle import Vehicle
from app.services import alert_service, geofence_service


class VehicleNotFound(LookupError):
    pass


def record_ping(
    db: Session, vehicle_id: int, lat: float, lng: float, speed: float
) -> tuple[LocationPing, list[Alert]]:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise VehicleNotFound(f"Vehicle {vehicle_id} does not exist.")

    active_trip = (
        db.query(Trip)
        .filter(Trip.vehicle_id == vehicle_id, Trip.status == TripStatus.IN_PROGRESS)
        .first()
    )

    ping = LocationPing(
        vehicle_id=vehicle_id,
        trip_id=active_trip.id if active_trip is not None else None,
        lat=lat,
        lng=lng,
        speed=speed,
    )
    db.add(ping)
    db.commit()
    db.refresh(ping)

    # Best-effort: geofence and speed alert detection run after the ping is
    # safely stored, so an alerting issue never blocks GPS ingestion itself.
    # Their results are returned (not broadcast here) so the router - which
    # is where the async WebSocket broadcast happens - can push them out.
    new_alerts: list[Alert] = []
    new_alerts.extend(geofence_service.process_ping(db, ping))
    speed_alert = alert_service.process_speed_alert(db, ping)
    if speed_alert is not None:
        new_alerts.append(speed_alert)

    return ping, new_alerts
