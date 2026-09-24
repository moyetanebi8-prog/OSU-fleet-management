from app.config import settings
from app.models.alert import Alert
from app.models.enums import AlertType
from app.models.geofence import Geofence

DEVICE_HEADERS = {"X-Device-API-Key": settings.DEVICE_API_KEY}

# A 1x1 degree square roughly centered near the equator, purely for
# arithmetic convenience in tests (real geofences would be much smaller
# and drawn from an actual map).
SQUARE = [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]
INSIDE = {"lat": 0.5, "lng": 0.5}
OUTSIDE = {"lat": 5.0, "lng": 5.0}


def _create_vehicle(client, dispatcher_headers, plate: str) -> int:
    response = client.post(
        "/api/v1/vehicles/",
        json={"name": f"Vehicle {plate}", "plate_number": plate, "capacity": 4},
        headers=dispatcher_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_geofence(client, dispatcher_headers, name: str, coordinates=None) -> int:
    response = client.post(
        "/api/v1/geofences/",
        json={"name": name, "coordinates": coordinates or SQUARE},
        headers=dispatcher_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _ping(client, vehicle_id: int, lat: float, lng: float, speed: float = 20.0):
    return client.post(
        "/api/v1/pings/",
        json={"vehicle_id": vehicle_id, "lat": lat, "lng": lng, "speed": speed},
        headers=DEVICE_HEADERS,
    )


def _alerts_for_vehicle(db_session, vehicle_id: int) -> list[Alert]:
    return (
        db_session.query(Alert)
        .filter(Alert.vehicle_id == vehicle_id)
        .order_by(Alert.id.asc())
        .all()
    )


def test_ping_outside_geofence_creates_no_alert(client, dispatcher_headers, db_session):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "GEO-001")
    _create_geofence(client, dispatcher_headers, "Depot A")

    _ping(client, vehicle_id, **OUTSIDE)

    assert _alerts_for_vehicle(db_session, vehicle_id) == []


def test_first_ping_inside_creates_entry_alert(client, dispatcher_headers, db_session):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "GEO-002")
    _create_geofence(client, dispatcher_headers, "Depot B")

    _ping(client, vehicle_id, **INSIDE)

    alerts = _alerts_for_vehicle(db_session, vehicle_id)
    assert len(alerts) == 1
    assert alerts[0].type == AlertType.GEOFENCE_ENTRY


def test_consecutive_pings_inside_do_not_duplicate_alert(client, dispatcher_headers, db_session):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "GEO-003")
    _create_geofence(client, dispatcher_headers, "Depot C")

    _ping(client, vehicle_id, **INSIDE)
    _ping(client, vehicle_id, lat=INSIDE["lat"] + 0.01, lng=INSIDE["lng"])
    _ping(client, vehicle_id, lat=INSIDE["lat"] + 0.02, lng=INSIDE["lng"])

    alerts = _alerts_for_vehicle(db_session, vehicle_id)
    assert len(alerts) == 1  # still just the one entry alert


def test_exit_after_entry_creates_exit_alert(client, dispatcher_headers, db_session):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "GEO-004")
    _create_geofence(client, dispatcher_headers, "Depot D")

    _ping(client, vehicle_id, **INSIDE)
    _ping(client, vehicle_id, **OUTSIDE)

    alerts = _alerts_for_vehicle(db_session, vehicle_id)
    assert [a.type for a in alerts] == [AlertType.GEOFENCE_ENTRY, AlertType.GEOFENCE_EXIT]


def test_consecutive_pings_outside_after_exit_do_not_duplicate(client, dispatcher_headers, db_session):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "GEO-005")
    _create_geofence(client, dispatcher_headers, "Depot E")

    _ping(client, vehicle_id, **INSIDE)
    _ping(client, vehicle_id, **OUTSIDE)
    _ping(client, vehicle_id, lat=OUTSIDE["lat"] + 1, lng=OUTSIDE["lng"])
    _ping(client, vehicle_id, lat=OUTSIDE["lat"] + 2, lng=OUTSIDE["lng"])

    alerts = _alerts_for_vehicle(db_session, vehicle_id)
    assert len(alerts) == 2  # one entry, one exit - nothing more


def test_full_enter_exit_enter_cycle(client, dispatcher_headers, db_session):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "GEO-006")
    _create_geofence(client, dispatcher_headers, "Depot F")

    _ping(client, vehicle_id, **INSIDE)   # entry
    _ping(client, vehicle_id, **OUTSIDE)  # exit
    _ping(client, vehicle_id, **INSIDE)   # entry again

    alerts = _alerts_for_vehicle(db_session, vehicle_id)
    assert [a.type for a in alerts] == [
        AlertType.GEOFENCE_ENTRY,
        AlertType.GEOFENCE_EXIT,
        AlertType.GEOFENCE_ENTRY,
    ]


def test_ping_inside_two_overlapping_geofences_creates_two_entry_alerts(
    client, dispatcher_headers, db_session
):
    """Each geofence is tracked independently (per vehicle_id + geofence_id
    in vehicle_geofence_states), so a single point that happens to fall
    inside two overlapping zones must produce one entry alert per zone,
    not just one overall."""
    vehicle_id = _create_vehicle(client, dispatcher_headers, "GEO-009")
    # Two overlapping squares that both contain (0.5, 0.5).
    _create_geofence(client, dispatcher_headers, "Zone Alpha", coordinates=SQUARE)
    _create_geofence(
        client,
        dispatcher_headers,
        "Zone Beta",
        coordinates=[[0.2, 0.2], [0.2, 1.2], [1.2, 1.2], [1.2, 0.2], [0.2, 0.2]],
    )

    _ping(client, vehicle_id, **INSIDE)

    alerts = _alerts_for_vehicle(db_session, vehicle_id)
    entry_alerts = [a for a in alerts if a.type == AlertType.GEOFENCE_ENTRY]
    assert len(entry_alerts) == 2


def test_inactive_geofence_is_ignored(client, dispatcher_headers, db_session):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "GEO-007")
    geofence_id = _create_geofence(client, dispatcher_headers, "Depot G")

    geofence = db_session.get(Geofence, geofence_id)
    geofence.is_active = False
    db_session.commit()

    _ping(client, vehicle_id, **INSIDE)

    assert _alerts_for_vehicle(db_session, vehicle_id) == []


def test_alert_is_associated_with_active_trip_when_present(
    client, dispatcher_headers, requester_headers, db_session
):
    from datetime import datetime, timedelta, timezone

    _create_geofence(client, dispatcher_headers, "Depot H")

    start = datetime.now(timezone.utc) + timedelta(hours=1)
    end = start + timedelta(hours=2)
    request_resp = client.post(
        "/api/v1/trip-requests/",
        json={
            "purpose": "Run",
            "destination": "Site",
            "traveler_ids": [],
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
        },
        headers=requester_headers,
    )
    request_id = request_resp.json()["id"]
    vehicle_id = _create_vehicle(client, dispatcher_headers, "GEO-008")
    driver_resp = client.post(
        "/api/v1/drivers/",
        json={"name": "Driver GEO-008", "license_number": "DL-GEO-008"},
        headers=dispatcher_headers,
    )
    driver_id = driver_resp.json()["id"]
    approve = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )
    trip_id = approve.json()["id"]

    _ping(client, vehicle_id, **OUTSIDE)  # starting position, outside geofence
    start_resp = client.post(f"/api/v1/trips/{trip_id}/start", headers=dispatcher_headers)
    assert start_resp.status_code == 200

    _ping(client, vehicle_id, **INSIDE)  # now drives into the geofence mid-trip

    alerts = _alerts_for_vehicle(db_session, vehicle_id)
    assert len(alerts) == 1
    assert alerts[0].trip_id == trip_id
