from app.config import settings
from app.models.alert import Alert
from app.models.enums import AlertType

DEVICE_HEADERS = {"X-Device-API-Key": settings.DEVICE_API_KEY}
LIMIT = settings.DEFAULT_SPEED_LIMIT_KMH


def _create_vehicle(client, dispatcher_headers, plate: str) -> int:
    response = client.post(
        "/api/v1/vehicles/",
        json={"name": f"Vehicle {plate}", "plate_number": plate, "capacity": 4},
        headers=dispatcher_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _ping(client, vehicle_id: int, speed: float, lat: float = 1.0, lng: float = 1.0):
    return client.post(
        "/api/v1/pings/",
        json={"vehicle_id": vehicle_id, "lat": lat, "lng": lng, "speed": speed},
        headers=DEVICE_HEADERS,
    )


def _speeding_alerts(db_session, vehicle_id: int) -> list[Alert]:
    return (
        db_session.query(Alert)
        .filter(Alert.vehicle_id == vehicle_id, Alert.type == AlertType.SPEEDING)
        .order_by(Alert.id.asc())
        .all()
    )


def test_ping_under_limit_creates_no_alert(client, dispatcher_headers, db_session):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "SPD-001")
    _ping(client, vehicle_id, speed=LIMIT - 10)
    assert _speeding_alerts(db_session, vehicle_id) == []


def test_ping_exactly_at_limit_creates_no_alert(client, dispatcher_headers, db_session):
    """Only strictly exceeding the limit counts - the boundary itself is fine."""
    vehicle_id = _create_vehicle(client, dispatcher_headers, "SPD-002")
    _ping(client, vehicle_id, speed=LIMIT)
    assert _speeding_alerts(db_session, vehicle_id) == []


def test_ping_over_limit_creates_one_alert(client, dispatcher_headers, db_session):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "SPD-003")
    _ping(client, vehicle_id, speed=LIMIT + 5)
    alerts = _speeding_alerts(db_session, vehicle_id)
    assert len(alerts) == 1
    assert alerts[0].type == AlertType.SPEEDING


def test_consecutive_speeding_pings_do_not_duplicate_alert(client, dispatcher_headers, db_session):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "SPD-004")
    _ping(client, vehicle_id, speed=LIMIT + 5)
    _ping(client, vehicle_id, speed=LIMIT + 8)
    _ping(client, vehicle_id, speed=LIMIT + 12)
    _ping(client, vehicle_id, speed=LIMIT + 3)

    alerts = _speeding_alerts(db_session, vehicle_id)
    assert len(alerts) == 1  # still just the one, for the whole continuous event


def test_slowing_down_then_speeding_again_creates_second_alert(
    client, dispatcher_headers, db_session
):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "SPD-005")
    _ping(client, vehicle_id, speed=LIMIT + 5)   # event 1 starts
    _ping(client, vehicle_id, speed=LIMIT + 10)  # event 1 continues
    _ping(client, vehicle_id, speed=LIMIT - 5)   # back under limit - event 1 ends
    _ping(client, vehicle_id, speed=LIMIT + 7)   # event 2 starts

    alerts = _speeding_alerts(db_session, vehicle_id)
    assert len(alerts) == 2


def test_speeding_alert_associated_with_active_trip(
    client, dispatcher_headers, requester_headers, db_session
):
    from datetime import datetime, timedelta, timezone

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
    vehicle_id = _create_vehicle(client, dispatcher_headers, "SPD-006")
    driver_resp = client.post(
        "/api/v1/drivers/",
        json={"name": "Driver SPD-006", "license_number": "DL-SPD-006"},
        headers=dispatcher_headers,
    )
    driver_id = driver_resp.json()["id"]
    approve = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )
    trip_id = approve.json()["id"]

    _ping(client, vehicle_id, speed=20.0)  # starting position, under limit
    start_resp = client.post(f"/api/v1/trips/{trip_id}/start", headers=dispatcher_headers)
    assert start_resp.status_code == 200

    _ping(client, vehicle_id, speed=LIMIT + 15)  # speeds while on the trip

    alerts = _speeding_alerts(db_session, vehicle_id)
    assert len(alerts) == 1
    assert alerts[0].trip_id == trip_id
