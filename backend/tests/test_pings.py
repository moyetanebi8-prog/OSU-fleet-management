from datetime import datetime, timedelta, timezone

from app.config import settings
from app.models.enums import TripStatus
from app.models.location_ping import LocationPing
from app.models.trip import Trip

DEVICE_HEADERS = {"X-Device-API-Key": settings.DEVICE_API_KEY}


def _window(hours_ahead: int = 1, duration_hours: int = 2):
    start = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
    end = start + timedelta(hours=duration_hours)
    return start, end


def _create_vehicle(client, dispatcher_headers, plate: str, capacity: int = 4) -> int:
    response = client.post(
        "/api/v1/vehicles/",
        json={"name": f"Vehicle {plate}", "plate_number": plate, "capacity": capacity},
        headers=dispatcher_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_approved_trip(client, dispatcher_headers, requester_headers, plate: str, license_no: str) -> dict:
    start, end = _window()
    request_resp = client.post(
        "/api/v1/trip-requests/",
        json={
            "purpose": "Depot run",
            "destination": "Warehouse B",
            "traveler_ids": [],
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
        },
        headers=requester_headers,
    )
    request_id = request_resp.json()["id"]

    vehicle_id = _create_vehicle(client, dispatcher_headers, plate)

    driver_resp = client.post(
        "/api/v1/drivers/",
        json={"name": f"Driver {license_no}", "license_number": license_no},
        headers=dispatcher_headers,
    )
    driver_id = driver_resp.json()["id"]

    approve_resp = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )
    assert approve_resp.status_code == 200
    return approve_resp.json()


# --- device auth ---


def test_create_ping_requires_device_key(client, dispatcher_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "PNG-001")
    response = client.post(
        "/api/v1/pings/", json={"vehicle_id": vehicle_id, "lat": 1.0, "lng": 1.0, "speed": 30.0}
    )
    assert response.status_code == 401


def test_create_ping_rejects_wrong_device_key(client, dispatcher_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "PNG-002")
    response = client.post(
        "/api/v1/pings/",
        json={"vehicle_id": vehicle_id, "lat": 1.0, "lng": 1.0, "speed": 30.0},
        headers={"X-Device-API-Key": "totally-wrong-key"},
    )
    assert response.status_code == 401


def test_create_ping_rejects_user_jwt_alone(client, dispatcher_headers):
    """A dispatcher's own login token is NOT a substitute for the device key
    - these are two separate authentication mechanisms."""
    vehicle_id = _create_vehicle(client, dispatcher_headers, "PNG-003")
    response = client.post(
        "/api/v1/pings/",
        json={"vehicle_id": vehicle_id, "lat": 1.0, "lng": 1.0, "speed": 30.0},
        headers=dispatcher_headers,
    )
    assert response.status_code == 401


# --- validation ---


def test_create_ping_success(client, dispatcher_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "PNG-004")
    response = client.post(
        "/api/v1/pings/",
        json={"vehicle_id": vehicle_id, "lat": 12.5, "lng": 45.6, "speed": 55.5},
        headers=DEVICE_HEADERS,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["vehicle_id"] == vehicle_id
    assert body["trip_id"] is None
    assert body["lat"] == 12.5
    assert body["lng"] == 45.6
    assert body["speed"] == 55.5
    assert body["timestamp"] is not None


def test_create_ping_ignores_client_supplied_timestamp_and_trip_id(client, dispatcher_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "PNG-005")
    response = client.post(
        "/api/v1/pings/",
        json={
            "vehicle_id": vehicle_id,
            "lat": 1.0,
            "lng": 1.0,
            "speed": 10.0,
            "trip_id": 999999,
            "timestamp": "1999-01-01T00:00:00Z",
        },
        headers=DEVICE_HEADERS,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["trip_id"] is None
    assert not body["timestamp"].startswith("1999")


def test_create_ping_rejects_invalid_latitude(client, dispatcher_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "PNG-006")
    response = client.post(
        "/api/v1/pings/",
        json={"vehicle_id": vehicle_id, "lat": 91.0, "lng": 1.0, "speed": 10.0},
        headers=DEVICE_HEADERS,
    )
    assert response.status_code == 422


def test_create_ping_rejects_invalid_longitude(client, dispatcher_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "PNG-007")
    response = client.post(
        "/api/v1/pings/",
        json={"vehicle_id": vehicle_id, "lat": 1.0, "lng": -181.0, "speed": 10.0},
        headers=DEVICE_HEADERS,
    )
    assert response.status_code == 422


def test_create_ping_rejects_negative_speed(client, dispatcher_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "PNG-008")
    response = client.post(
        "/api/v1/pings/",
        json={"vehicle_id": vehicle_id, "lat": 1.0, "lng": 1.0, "speed": -5.0},
        headers=DEVICE_HEADERS,
    )
    assert response.status_code == 422


def test_create_ping_accepts_boundary_lat_lng_values(client, dispatcher_headers):
    """The exact edges of valid ranges (±90 lat, ±180 lng) must be
    accepted, not just values strictly inside them - Field(ge=..., le=...)
    is inclusive, and this proves it stays that way."""
    vehicle_id = _create_vehicle(client, dispatcher_headers, "PNG-009B")
    for lat, lng in [(90.0, 180.0), (-90.0, -180.0), (0.0, 0.0)]:
        response = client.post(
            "/api/v1/pings/",
            json={"vehicle_id": vehicle_id, "lat": lat, "lng": lng, "speed": 10.0},
            headers=DEVICE_HEADERS,
        )
        assert response.status_code == 201, f"boundary point ({lat}, {lng}) was rejected"


def test_create_ping_accepts_boundary_speed_value(client, dispatcher_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "PNG-009C")
    response = client.post(
        "/api/v1/pings/",
        json={"vehicle_id": vehicle_id, "lat": 1.0, "lng": 1.0, "speed": 300.0},
        headers=DEVICE_HEADERS,
    )
    assert response.status_code == 201


def test_create_ping_rejects_nonexistent_vehicle(client):
    response = client.post(
        "/api/v1/pings/",
        json={"vehicle_id": 999999, "lat": 1.0, "lng": 1.0, "speed": 10.0},
        headers=DEVICE_HEADERS,
    )
    assert response.status_code == 404


# --- trip association (the core Phase 8/9 rule) ---


def test_ping_has_no_trip_id_when_vehicle_idle(client, dispatcher_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "PNG-009")
    response = client.post(
        "/api/v1/pings/",
        json={"vehicle_id": vehicle_id, "lat": 1.0, "lng": 1.0, "speed": 10.0},
        headers=DEVICE_HEADERS,
    )
    assert response.json()["trip_id"] is None


def test_ping_has_no_trip_id_when_trip_only_approved(client, dispatcher_headers, requester_headers):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "PNG-010", "DL-PNG-010")
    response = client.post(
        "/api/v1/pings/",
        json={"vehicle_id": trip["vehicle_id"], "lat": 1.0, "lng": 1.0, "speed": 10.0},
        headers=DEVICE_HEADERS,
    )
    assert response.json()["trip_id"] is None


def test_ping_auto_assigned_to_in_progress_trip(client, dispatcher_headers, requester_headers):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "PNG-011", "DL-PNG-011")

    # Need an initial ping to start the trip.
    client.post(
        "/api/v1/pings/",
        json={"vehicle_id": trip["vehicle_id"], "lat": 1.0, "lng": 1.0, "speed": 10.0},
        headers=DEVICE_HEADERS,
    )
    start_resp = client.post(f"/api/v1/trips/{trip['id']}/start", headers=dispatcher_headers)
    assert start_resp.status_code == 200

    response = client.post(
        "/api/v1/pings/",
        json={"vehicle_id": trip["vehicle_id"], "lat": 1.01, "lng": 1.0, "speed": 40.0},
        headers=DEVICE_HEADERS,
    )
    assert response.json()["trip_id"] == trip["id"]


def test_ping_falls_back_to_null_after_trip_completes(
    client, dispatcher_headers, requester_headers
):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "PNG-012", "DL-PNG-012")

    client.post(
        "/api/v1/pings/",
        json={"vehicle_id": trip["vehicle_id"], "lat": 1.0, "lng": 1.0, "speed": 10.0},
        headers=DEVICE_HEADERS,
    )
    client.post(f"/api/v1/trips/{trip['id']}/start", headers=dispatcher_headers)
    client.post(
        "/api/v1/pings/",
        json={"vehicle_id": trip["vehicle_id"], "lat": 1.01, "lng": 1.0, "speed": 40.0},
        headers=DEVICE_HEADERS,
    )
    complete_resp = client.post(f"/api/v1/trips/{trip['id']}/complete", headers=dispatcher_headers)
    assert complete_resp.status_code == 200

    response = client.post(
        "/api/v1/pings/",
        json={"vehicle_id": trip["vehicle_id"], "lat": 2.0, "lng": 2.0, "speed": 5.0},
        headers=DEVICE_HEADERS,
    )
    assert response.json()["trip_id"] is None


# --- vehicle history ---


def test_vehicle_history_requires_dispatcher(client, requester_headers, dispatcher_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "PNG-013")
    response = client.get(f"/api/v1/vehicles/{vehicle_id}/history", headers=requester_headers)
    assert response.status_code == 403


def test_vehicle_history_returns_pings_most_recent_first(client, dispatcher_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "PNG-014")
    for i in range(3):
        client.post(
            "/api/v1/pings/",
            json={"vehicle_id": vehicle_id, "lat": float(i), "lng": float(i), "speed": 10.0},
            headers=DEVICE_HEADERS,
        )

    response = client.get(f"/api/v1/vehicles/{vehicle_id}/history", headers=dispatcher_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert body[0]["lat"] == 2.0  # most recent (last inserted) first


def test_vehicle_history_404_for_missing_vehicle(client, dispatcher_headers):
    response = client.get("/api/v1/vehicles/999999/history", headers=dispatcher_headers)
    assert response.status_code == 404


# --- trip route ---


def test_trip_route_only_includes_this_trips_points(
    client, dispatcher_headers, requester_headers, db_session
):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "PNG-015", "DL-PNG-015")

    client.post(
        "/api/v1/pings/",
        json={"vehicle_id": trip["vehicle_id"], "lat": 5.0, "lng": 5.0, "speed": 10.0},
        headers=DEVICE_HEADERS,
    )
    client.post(f"/api/v1/trips/{trip['id']}/start", headers=dispatcher_headers)
    client.post(
        "/api/v1/pings/",
        json={"vehicle_id": trip["vehicle_id"], "lat": 5.01, "lng": 5.0, "speed": 20.0},
        headers=DEVICE_HEADERS,
    )

    # A stray general-tracking ping recorded after completion should never
    # show up in this trip's route.
    client.post(f"/api/v1/trips/{trip['id']}/complete", headers=dispatcher_headers)
    client.post(
        "/api/v1/pings/",
        json={"vehicle_id": trip["vehicle_id"], "lat": 99.0, "lng": 99.0, "speed": 0.0},
        headers=DEVICE_HEADERS,
    )

    response = client.get(f"/api/v1/trips/{trip['id']}/route", headers=dispatcher_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert all(p["trip_id"] == trip["id"] for p in body)
    assert body[0]["lat"] == 5.0
    assert body[1]["lat"] == 5.01


def test_trip_route_requester_ownership_enforced(
    client, dispatcher_headers, requester_headers, admin_headers
):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "PNG-016", "DL-PNG-016")

    client.post(
        "/api/v1/admin/employees/",
        json={"username": "other_png", "full_name": "Other", "email": "other_png@example.com", "password": "requesterpass1"},
        headers=admin_headers,
    )
    login = client.post(
        "/api/v1/auth/login", data={"username": "other_png", "password": "requesterpass1"}
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get(f"/api/v1/trips/{trip['id']}/route", headers=other_headers)
    assert response.status_code == 403

    own_response = client.get(f"/api/v1/trips/{trip['id']}/route", headers=requester_headers)
    assert own_response.status_code == 200
