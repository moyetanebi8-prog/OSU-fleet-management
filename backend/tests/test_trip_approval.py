import itertools
from datetime import datetime, timedelta, timezone

from app.models.driver import Driver
from app.models.enums import DriverStatus, TripRequestStatus, TripStatus, VehicleStatus
from app.models.trip import Trip
from app.models.trip_request import TripRequest
from app.models.vehicle import Vehicle

_dummy_traveler_counter = itertools.count(1)


def _window(hours_ahead: int = 24, duration_hours: int = 2):
    start = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
    end = start + timedelta(hours=duration_hours)
    return start, end


def _make_traveler_ids(client, admin_headers, count: int) -> list[int]:
    """Creates `count` throwaway employee accounts and returns their ids -
    lets capacity-related tests precisely control passenger_count (now
    derived from the traveler list, not a directly-settable field) without
    caring who the travelers actually are. Uses a module-level counter so
    concurrent calls within the same test never collide on username."""
    ids = []
    for _ in range(count):
        n = next(_dummy_traveler_counter)
        username = f"dummy_traveler_{n}"
        response = client.post(
            "/api/v1/admin/employees/",
            json={
                "username": username,
                "full_name": f"Dummy Traveler {n}",
                "email": f"{username}@example.com",
                "password": "dummytravelerpass1",
            },
            headers=admin_headers,
        )
        ids.append(response.json()["id"])
    return ids


def _request_payload(traveler_ids: list[int] | None, hours_ahead: int, duration_hours: int) -> dict:
    start, end = _window(hours_ahead, duration_hours)
    return {
        "purpose": "Client visit",
        "destination": "Downtown",
        "traveler_ids": traveler_ids or [],
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
    }


def _create_request(
    client,
    requester_headers,
    admin_headers,
    passenger_count: int = 1,
    hours_ahead: int = 24,
    duration_hours: int = 2,
) -> int:
    """passenger_count is achieved by actually creating (passenger_count - 1)
    real traveler accounts - it is NOT a settable field on the request
    payload anymore (see the traveler-selection feature)."""
    traveler_ids = _make_traveler_ids(client, admin_headers, max(passenger_count - 1, 0))
    response = client.post(
        "/api/v1/trip-requests/",
        json=_request_payload(traveler_ids, hours_ahead, duration_hours),
        headers=requester_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_vehicle(client, dispatcher_headers, plate: str, capacity: int = 4) -> int:
    response = client.post(
        "/api/v1/vehicles/",
        json={"name": f"Vehicle {plate}", "plate_number": plate, "capacity": capacity},
        headers=dispatcher_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_driver(client, dispatcher_headers, license_no: str) -> int:
    response = client.post(
        "/api/v1/drivers/",
        json={"name": f"Driver {license_no}", "license_number": license_no},
        headers=dispatcher_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


# --- available-resources ---


def test_available_resources_requires_dispatcher(client, requester_headers, admin_headers):
    request_id = _create_request(client, requester_headers, admin_headers)
    response = client.get(
        f"/api/v1/trip-requests/{request_id}/available-resources", headers=requester_headers
    )
    assert response.status_code == 403


def test_available_resources_excludes_insufficient_capacity(
    client, dispatcher_headers, requester_headers, admin_headers
):
    request_id = _create_request(client, requester_headers, admin_headers, passenger_count=6)
    _create_vehicle(client, dispatcher_headers, "CAP-001", capacity=4)  # too small

    response = client.get(
        f"/api/v1/trip-requests/{request_id}/available-resources", headers=dispatcher_headers
    )
    assert response.status_code == 200
    assert response.json()["vehicles"] == []


def test_available_resources_excludes_non_available_status(
    client, dispatcher_headers, requester_headers, admin_headers, db_session
):
    request_id = _create_request(client, requester_headers, admin_headers, passenger_count=2)
    vehicle_id = _create_vehicle(client, dispatcher_headers, "CAP-002", capacity=4)

    vehicle = db_session.get(Vehicle, vehicle_id)
    vehicle.status = VehicleStatus.MAINTENANCE
    db_session.commit()

    response = client.get(
        f"/api/v1/trip-requests/{request_id}/available-resources", headers=dispatcher_headers
    )
    assert response.json()["vehicles"] == []


def test_available_resources_includes_valid_candidates(
    client, dispatcher_headers, requester_headers, admin_headers
):
    request_id = _create_request(client, requester_headers, admin_headers, passenger_count=2)
    vehicle_id = _create_vehicle(client, dispatcher_headers, "CAP-003", capacity=4)
    driver_id = _create_driver(client, dispatcher_headers, "LIC-CAP-003")

    response = client.get(
        f"/api/v1/trip-requests/{request_id}/available-resources", headers=dispatcher_headers
    )
    body = response.json()
    assert any(v["id"] == vehicle_id for v in body["vehicles"])
    assert any(d["id"] == driver_id for d in body["drivers"])


# --- approve ---


def test_approve_requires_dispatcher(client, requester_headers, admin_headers):
    request_id = _create_request(client, requester_headers, admin_headers)
    response = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": 1, "driver_id": 1},
        headers=requester_headers,
    )
    assert response.status_code == 403


def test_approve_success_creates_trip_and_assigns_resources(
    client, dispatcher_headers, requester_headers, admin_headers, db_session
):
    request_id = _create_request(client, requester_headers, admin_headers, passenger_count=2)
    vehicle_id = _create_vehicle(client, dispatcher_headers, "APR-001", capacity=4)
    driver_id = _create_driver(client, dispatcher_headers, "LIC-APR-001")

    response = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["vehicle_id"] == vehicle_id
    assert body["driver_id"] == driver_id
    assert body["request_id"] == request_id

    req = client.get(f"/api/v1/trip-requests/{request_id}", headers=dispatcher_headers).json()
    assert req["status"] == "approved"
    assert req["trip_id"] == body["id"]

    vehicle = db_session.get(Vehicle, vehicle_id)
    driver = db_session.get(Driver, driver_id)
    assert vehicle.status == VehicleStatus.ASSIGNED
    assert driver.status == DriverStatus.ASSIGNED


def test_approve_rejects_already_approved_request(
    client, dispatcher_headers, requester_headers, admin_headers
):
    request_id = _create_request(client, requester_headers, admin_headers, passenger_count=2)
    vehicle_id = _create_vehicle(client, dispatcher_headers, "APR-002", capacity=4)
    driver_id = _create_driver(client, dispatcher_headers, "LIC-APR-002")

    first = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )
    assert second.status_code == 400


def test_approve_rejects_missing_vehicle(client, dispatcher_headers, requester_headers, admin_headers):
    request_id = _create_request(client, requester_headers, admin_headers, passenger_count=2)
    driver_id = _create_driver(client, dispatcher_headers, "LIC-APR-003")

    response = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": 999999, "driver_id": driver_id},
        headers=dispatcher_headers,
    )
    assert response.status_code == 404


def test_approve_rejects_missing_driver(client, dispatcher_headers, requester_headers, admin_headers):
    request_id = _create_request(client, requester_headers, admin_headers, passenger_count=2)
    vehicle_id = _create_vehicle(client, dispatcher_headers, "APR-004", capacity=4)

    response = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": 999999},
        headers=dispatcher_headers,
    )
    assert response.status_code == 404


def test_approve_rejects_insufficient_capacity(
    client, dispatcher_headers, requester_headers, admin_headers
):
    request_id = _create_request(client, requester_headers, admin_headers, passenger_count=6)
    vehicle_id = _create_vehicle(client, dispatcher_headers, "APR-005", capacity=4)
    driver_id = _create_driver(client, dispatcher_headers, "LIC-APR-005")

    response = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )
    assert response.status_code == 409


def test_approve_rejects_vehicle_not_available(
    client, dispatcher_headers, requester_headers, admin_headers, db_session
):
    request_id = _create_request(client, requester_headers, admin_headers, passenger_count=2)
    vehicle_id = _create_vehicle(client, dispatcher_headers, "APR-006", capacity=4)
    driver_id = _create_driver(client, dispatcher_headers, "LIC-APR-006")

    vehicle = db_session.get(Vehicle, vehicle_id)
    vehicle.status = VehicleStatus.MAINTENANCE
    db_session.commit()

    response = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )
    assert response.status_code == 409


def test_approve_rejects_schedule_conflict(
    client, dispatcher_headers, requester_headers, admin_headers, db_session
):
    """Simulates the race-condition guard this check exists for: a vehicle
    whose status is still `available` but which already has an APPROVED
    trip overlapping the requested window must still be rejected."""
    request_id = _create_request(
        client, requester_headers, admin_headers, passenger_count=2, hours_ahead=48
    )
    vehicle_id = _create_vehicle(client, dispatcher_headers, "APR-007", capacity=4)
    driver_id = _create_driver(client, dispatcher_headers, "LIC-APR-007")

    start, end = _window(hours_ahead=48, duration_hours=2)

    # A second, throwaway request to satisfy the Trip.request_id FK/unique
    # constraint for the pre-existing conflicting trip we're injecting.
    other_request_id = _create_request(
        client, requester_headers, admin_headers, passenger_count=2, hours_ahead=48
    )
    other_request = db_session.get(TripRequest, other_request_id)
    other_request.status = TripRequestStatus.APPROVED

    conflicting_trip = Trip(
        request_id=other_request.id,
        vehicle_id=vehicle_id,
        driver_id=driver_id,
        status=TripStatus.APPROVED,
        planned_start_time=start - timedelta(minutes=30),
        planned_end_time=end - timedelta(minutes=30),
    )
    db_session.add(conflicting_trip)
    db_session.commit()

    # vehicle/driver status intentionally left as AVAILABLE to simulate the
    # edge case this defensive check exists for.
    response = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )
    assert response.status_code == 409


# --- decline ---


def test_decline_requires_dispatcher(client, requester_headers, admin_headers):
    request_id = _create_request(client, requester_headers, admin_headers)
    response = client.post(
        f"/api/v1/trip-requests/{request_id}/decline",
        json={"reason": "No vehicles available."},
        headers=requester_headers,
    )
    assert response.status_code == 403


def test_decline_success(client, dispatcher_headers, requester_headers, admin_headers):
    request_id = _create_request(client, requester_headers, admin_headers)
    response = client.post(
        f"/api/v1/trip-requests/{request_id}/decline",
        json={"reason": "No vehicle available for the requested time."},
        headers=dispatcher_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "declined"
    assert body["decline_reason"] == "No vehicle available for the requested time."


def test_decline_rejects_empty_reason(client, dispatcher_headers, requester_headers, admin_headers):
    request_id = _create_request(client, requester_headers, admin_headers)
    response = client.post(
        f"/api/v1/trip-requests/{request_id}/decline", json={"reason": ""}, headers=dispatcher_headers
    )
    assert response.status_code == 422


def test_decline_rejects_whitespace_only_reason(
    client, dispatcher_headers, requester_headers, admin_headers
):
    request_id = _create_request(client, requester_headers, admin_headers)
    response = client.post(
        f"/api/v1/trip-requests/{request_id}/decline",
        json={"reason": "   "},
        headers=dispatcher_headers,
    )
    assert response.status_code == 400


def test_decline_rejects_already_declined_request(
    client, dispatcher_headers, requester_headers, admin_headers
):
    request_id = _create_request(client, requester_headers, admin_headers)
    first = client.post(
        f"/api/v1/trip-requests/{request_id}/decline",
        json={"reason": "No vehicle available."},
        headers=dispatcher_headers,
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/trip-requests/{request_id}/decline",
        json={"reason": "Still no vehicle."},
        headers=dispatcher_headers,
    )
    assert second.status_code == 400


def test_decline_rejects_already_approved_request(
    client, dispatcher_headers, requester_headers, admin_headers
):
    """The symmetric case to the test above: an already-approved request
    can't be declined either. Both directions of the pending -> {approved,
    declined} state machine reject a second transition."""
    request_id = _create_request(client, requester_headers, admin_headers, passenger_count=2)
    vehicle_id = _create_vehicle(client, dispatcher_headers, "SYM-001", capacity=4)
    driver_id = _create_driver(client, dispatcher_headers, "LIC-SYM-001")

    approve = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )
    assert approve.status_code == 200

    decline = client.post(
        f"/api/v1/trip-requests/{request_id}/decline",
        json={"reason": "Changed my mind."},
        headers=dispatcher_headers,
    )
    assert decline.status_code == 400


def test_approve_rejects_already_declined_request(
    client, dispatcher_headers, requester_headers, admin_headers
):
    request_id = _create_request(client, requester_headers, admin_headers, passenger_count=2)
    vehicle_id = _create_vehicle(client, dispatcher_headers, "SYM-002", capacity=4)
    driver_id = _create_driver(client, dispatcher_headers, "LIC-SYM-002")

    decline = client.post(
        f"/api/v1/trip-requests/{request_id}/decline",
        json={"reason": "No vehicle available."},
        headers=dispatcher_headers,
    )
    assert decline.status_code == 200

    approve = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )
    assert approve.status_code == 400
