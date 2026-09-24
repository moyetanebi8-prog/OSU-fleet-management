from datetime import datetime, timedelta, timezone

import pytest

from app.models.driver import Driver
from app.models.enums import DriverStatus, TripStatus, VehicleStatus
from app.models.location_ping import LocationPing
from app.models.vehicle import Vehicle
from app.services.distance_service import calculate_route_distance_km


def _window(hours_ahead: int = 1, duration_hours: int = 2):
    start = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
    end = start + timedelta(hours=duration_hours)
    return start, end


def _create_approved_trip(client, dispatcher_headers, requester_headers, plate: str, license_no: str) -> dict:
    """Full path: request -> vehicle -> driver -> approve. Returns the
    created Trip's JSON body."""
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

    vehicle_resp = client.post(
        "/api/v1/vehicles/",
        json={"name": f"Vehicle {plate}", "plate_number": plate, "capacity": 4},
        headers=dispatcher_headers,
    )
    vehicle_id = vehicle_resp.json()["id"]

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


def _add_ping(db_session, vehicle_id: int, lat: float, lng: float, trip_id: int | None = None, speed: float = 40.0):
    ping = LocationPing(vehicle_id=vehicle_id, trip_id=trip_id, lat=lat, lng=lng, speed=speed)
    db_session.add(ping)
    db_session.commit()
    db_session.refresh(ping)
    return ping


# --- start ---


def test_start_requires_dispatcher(client, dispatcher_headers, requester_headers):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "LC-001", "DL-001")
    response = client.post(f"/api/v1/trips/{trip['id']}/start", headers=requester_headers)
    assert response.status_code == 403


def test_start_fails_without_any_gps_location(client, dispatcher_headers, requester_headers):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "LC-002", "DL-002")
    response = client.post(f"/api/v1/trips/{trip['id']}/start", headers=dispatcher_headers)
    assert response.status_code == 409


def test_start_success_captures_gps_and_updates_statuses(
    client, dispatcher_headers, requester_headers, db_session
):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "LC-003", "DL-003")
    ping = _add_ping(db_session, trip["vehicle_id"], lat=12.34, lng=56.78)

    response = client.post(f"/api/v1/trips/{trip['id']}/start", headers=dispatcher_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["actual_start_time"] is not None
    assert body["start_lat"] == pytest.approx(12.34)
    assert body["start_lng"] == pytest.approx(56.78)

    vehicle = db_session.get(Vehicle, trip["vehicle_id"])
    driver = db_session.get(Driver, trip["driver_id"])
    assert vehicle.status == VehicleStatus.IN_PROGRESS
    assert driver.status == DriverStatus.DRIVING

    db_session.refresh(ping)
    assert ping.trip_id == trip["id"]


def test_start_uses_most_recent_ping_not_oldest(
    client, dispatcher_headers, requester_headers, db_session
):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "LC-004", "DL-004")
    _add_ping(db_session, trip["vehicle_id"], lat=1.0, lng=1.0)  # older
    newest = _add_ping(db_session, trip["vehicle_id"], lat=2.0, lng=2.0)  # newer

    response = client.post(f"/api/v1/trips/{trip['id']}/start", headers=dispatcher_headers)
    body = response.json()
    assert body["start_lat"] == pytest.approx(newest.lat)
    assert body["start_lng"] == pytest.approx(newest.lng)


def test_start_rejects_non_approved_trip(client, dispatcher_headers, requester_headers, db_session):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "LC-005", "DL-005")
    _add_ping(db_session, trip["vehicle_id"], lat=1.0, lng=1.0)

    first = client.post(f"/api/v1/trips/{trip['id']}/start", headers=dispatcher_headers)
    assert first.status_code == 200

    second = client.post(f"/api/v1/trips/{trip['id']}/start", headers=dispatcher_headers)
    assert second.status_code == 400


def test_start_nonexistent_trip_404(client, dispatcher_headers):
    response = client.post("/api/v1/trips/999999/start", headers=dispatcher_headers)
    assert response.status_code == 404


# --- complete ---


def test_complete_requires_dispatcher(client, dispatcher_headers, requester_headers, db_session):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "LC-006", "DL-006")
    _add_ping(db_session, trip["vehicle_id"], lat=1.0, lng=1.0)
    client.post(f"/api/v1/trips/{trip['id']}/start", headers=dispatcher_headers)

    response = client.post(f"/api/v1/trips/{trip['id']}/complete", headers=requester_headers)
    assert response.status_code == 403


def test_complete_rejects_trip_not_in_progress(client, dispatcher_headers, requester_headers):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "LC-007", "DL-007")
    # Never started - still 'approved'.
    response = client.post(f"/api/v1/trips/{trip['id']}/complete", headers=dispatcher_headers)
    assert response.status_code == 400


def test_complete_calculates_distance_from_trip_points_and_frees_resources(
    client, dispatcher_headers, requester_headers, db_session
):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "LC-008", "DL-008")
    vehicle_id = trip["vehicle_id"]

    _add_ping(db_session, vehicle_id, lat=10.0, lng=10.0)
    start_resp = client.post(f"/api/v1/trips/{trip['id']}/start", headers=dispatcher_headers)
    assert start_resp.status_code == 200

    # Additional points recorded "during" the trip.
    _add_ping(db_session, vehicle_id, lat=10.01, lng=10.0, trip_id=trip["id"])
    _add_ping(db_session, vehicle_id, lat=10.02, lng=10.01, trip_id=trip["id"])

    response = client.post(f"/api/v1/trips/{trip['id']}/complete", headers=dispatcher_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["actual_end_time"] is not None
    assert body["end_lat"] == pytest.approx(10.02)
    assert body["end_lng"] == pytest.approx(10.01)

    expected_distance = calculate_route_distance_km(
        [(10.0, 10.0), (10.01, 10.0), (10.02, 10.01)]
    )
    assert body["distance_km"] == pytest.approx(expected_distance, rel=1e-4)
    assert body["distance_km"] > 0

    vehicle = db_session.get(Vehicle, vehicle_id)
    driver = db_session.get(Driver, trip["driver_id"])
    assert vehicle.status == VehicleStatus.AVAILABLE
    assert driver.status == DriverStatus.AVAILABLE


def test_complete_excludes_pings_not_belonging_to_this_trip(
    client, dispatcher_headers, requester_headers, db_session
):
    """The critical GPS rule (spec section 45): general vehicle tracking
    pings (trip_id=None) and pings from other trips must never leak into
    this trip's distance calculation."""
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "LC-009", "DL-009")
    vehicle_id = trip["vehicle_id"]

    _add_ping(db_session, vehicle_id, lat=20.0, lng=20.0)
    client.post(f"/api/v1/trips/{trip['id']}/start", headers=dispatcher_headers)

    # A ping with no trip (general tracking) recorded while this trip is
    # in progress - must NOT be included.
    _add_ping(db_session, vehicle_id, lat=99.0, lng=99.0, trip_id=None)
    # The one legitimate additional trip point.
    _add_ping(db_session, vehicle_id, lat=20.01, lng=20.0, trip_id=trip["id"])

    response = client.post(f"/api/v1/trips/{trip['id']}/complete", headers=dispatcher_headers)
    body = response.json()

    # End position must be the last TRIP point (20.01, 20.0), not the
    # stray general-tracking ping (99.0, 99.0).
    assert body["end_lat"] == pytest.approx(20.01)
    assert body["end_lng"] == pytest.approx(20.0)


def test_complete_nonexistent_trip_404(client, dispatcher_headers):
    response = client.post("/api/v1/trips/999999/complete", headers=dispatcher_headers)
    assert response.status_code == 404


def test_complete_rejects_already_completed_trip(
    client, dispatcher_headers, requester_headers, db_session
):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "LC-013", "DL-013")
    _add_ping(db_session, trip["vehicle_id"], lat=1.0, lng=1.0)
    client.post(f"/api/v1/trips/{trip['id']}/start", headers=dispatcher_headers)

    first = client.post(f"/api/v1/trips/{trip['id']}/complete", headers=dispatcher_headers)
    assert first.status_code == 200

    second = client.post(f"/api/v1/trips/{trip['id']}/complete", headers=dispatcher_headers)
    assert second.status_code == 400


# --- viewing ---


def test_requester_can_view_own_trip(client, dispatcher_headers, requester_headers, db_session):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "LC-010", "DL-010")
    response = client.get(f"/api/v1/trips/{trip['id']}", headers=requester_headers)
    assert response.status_code == 200


def test_requester_cannot_view_others_trip(client, dispatcher_headers, requester_headers, admin_headers):
    trip = _create_approved_trip(client, dispatcher_headers, requester_headers, "LC-011", "DL-011")

    client.post(
        "/api/v1/admin/employees/",
        json={"username": "other_req", "full_name": "Other", "email": "other_req@example.com", "password": "requesterpass1"},
        headers=admin_headers,
    )
    login = client.post(
        "/api/v1/auth/login", data={"username": "other_req", "password": "requesterpass1"}
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get(f"/api/v1/trips/{trip['id']}", headers=other_headers)
    assert response.status_code == 403


def test_dispatcher_sees_all_trips_requester_sees_only_own(
    client, dispatcher_headers, requester_headers, admin_headers
):
    trip_a = _create_approved_trip(client, dispatcher_headers, requester_headers, "LC-012", "DL-012")

    client.post(
        "/api/v1/admin/employees/",
        json={"username": "other_req2", "full_name": "Other Two", "email": "other_req2@example.com", "password": "requesterpass1"},
        headers=admin_headers,
    )
    login = client.post(
        "/api/v1/auth/login", data={"username": "other_req2", "password": "requesterpass1"}
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    trip_b = _create_approved_trip(client, dispatcher_headers, other_headers, "LC-013", "DL-013")

    dispatcher_ids = {t["id"] for t in client.get("/api/v1/trips/", headers=dispatcher_headers).json()}
    requester_ids = {t["id"] for t in client.get("/api/v1/trips/", headers=requester_headers).json()}

    assert {trip_a["id"], trip_b["id"]}.issubset(dispatcher_ids)
    assert trip_a["id"] in requester_ids
    assert trip_b["id"] not in requester_ids
