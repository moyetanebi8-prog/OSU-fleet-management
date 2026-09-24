from app.models.enums import VehicleStatus
from app.models.vehicle import Vehicle


def test_create_vehicle_requires_authentication(client):
    response = client.post(
        "/api/v1/vehicles/", json={"name": "Van 1", "plate_number": "AA-111", "capacity": 8}
    )
    assert response.status_code == 401


def test_create_vehicle_rejects_requester(client, requester_headers):
    response = client.post(
        "/api/v1/vehicles/",
        json={"name": "Van 1", "plate_number": "AA-111", "capacity": 8},
        headers=requester_headers,
    )
    assert response.status_code == 403


def test_create_vehicle_success(client, dispatcher_headers):
    response = client.post(
        "/api/v1/vehicles/",
        json={"name": "Van 1", "plate_number": "AA-111", "capacity": 8},
        headers=dispatcher_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Van 1"
    assert body["plate_number"] == "AA-111"
    assert body["capacity"] == 8
    assert body["status"] == "available"  # backend-assigned default, not client input


def test_create_vehicle_duplicate_plate_conflict(client, dispatcher_headers):
    payload = {"name": "Van 1", "plate_number": "AA-222", "capacity": 8}
    first = client.post("/api/v1/vehicles/", json=payload, headers=dispatcher_headers)
    assert first.status_code == 201

    second = client.post("/api/v1/vehicles/", json=payload, headers=dispatcher_headers)
    assert second.status_code == 409


def test_create_vehicle_rejects_non_positive_capacity(client, dispatcher_headers):
    response = client.post(
        "/api/v1/vehicles/",
        json={"name": "Van 1", "plate_number": "AA-333", "capacity": 0},
        headers=dispatcher_headers,
    )
    assert response.status_code == 422


def test_create_vehicle_cannot_set_status_directly(client, dispatcher_headers):
    """Status isn't even a field on VehicleCreate - sending it is silently
    ignored and the vehicle still starts 'available'."""
    response = client.post(
        "/api/v1/vehicles/",
        json={
            "name": "Van 1",
            "plate_number": "AA-444",
            "capacity": 8,
            "status": "maintenance",
        },
        headers=dispatcher_headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "available"


def test_list_vehicles(client, dispatcher_headers):
    client.post(
        "/api/v1/vehicles/",
        json={"name": "Van 1", "plate_number": "AA-555", "capacity": 8},
        headers=dispatcher_headers,
    )
    response = client.get("/api/v1/vehicles/", headers=dispatcher_headers)
    assert response.status_code == 200
    assert any(v["plate_number"] == "AA-555" for v in response.json())


def test_get_vehicle_not_found(client, dispatcher_headers):
    response = client.get("/api/v1/vehicles/999999", headers=dispatcher_headers)
    assert response.status_code == 404


def test_update_vehicle_success(client, dispatcher_headers):
    create = client.post(
        "/api/v1/vehicles/",
        json={"name": "Van 1", "plate_number": "AA-666", "capacity": 8},
        headers=dispatcher_headers,
    )
    vehicle_id = create.json()["id"]

    response = client.put(
        f"/api/v1/vehicles/{vehicle_id}",
        json={"name": "Van 1 (renamed)", "plate_number": "AA-666", "capacity": 10},
        headers=dispatcher_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Van 1 (renamed)"
    assert response.json()["capacity"] == 10


def test_update_vehicle_duplicate_plate_conflict(client, dispatcher_headers):
    client.post(
        "/api/v1/vehicles/",
        json={"name": "Van A", "plate_number": "AA-777", "capacity": 8},
        headers=dispatcher_headers,
    )
    second = client.post(
        "/api/v1/vehicles/",
        json={"name": "Van B", "plate_number": "AA-888", "capacity": 8},
        headers=dispatcher_headers,
    )
    vehicle_b_id = second.json()["id"]

    response = client.put(
        f"/api/v1/vehicles/{vehicle_b_id}",
        json={"name": "Van B", "plate_number": "AA-777", "capacity": 8},
        headers=dispatcher_headers,
    )
    assert response.status_code == 409


def test_delete_vehicle_success(client, dispatcher_headers):
    create = client.post(
        "/api/v1/vehicles/",
        json={"name": "Van 1", "plate_number": "AA-999", "capacity": 8},
        headers=dispatcher_headers,
    )
    vehicle_id = create.json()["id"]

    response = client.delete(f"/api/v1/vehicles/{vehicle_id}", headers=dispatcher_headers)
    assert response.status_code == 204

    followup = client.get(f"/api/v1/vehicles/{vehicle_id}", headers=dispatcher_headers)
    assert followup.status_code == 404


def test_delete_vehicle_not_found(client, dispatcher_headers):
    response = client.delete("/api/v1/vehicles/999999", headers=dispatcher_headers)
    assert response.status_code == 404


def test_change_vehicle_status_success(client, dispatcher_headers):
    create = client.post(
        "/api/v1/vehicles/",
        json={"name": "Van 1", "plate_number": "BB-111", "capacity": 8},
        headers=dispatcher_headers,
    )
    vehicle_id = create.json()["id"]

    response = client.patch(
        f"/api/v1/vehicles/{vehicle_id}/status",
        json={"status": "maintenance"},
        headers=dispatcher_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "maintenance"


def test_change_vehicle_status_rejects_assigned_as_manual_target(client, dispatcher_headers):
    """'assigned' and 'in_progress' are set only by the trip workflow, never
    by direct manual edit, even by a dispatcher."""
    create = client.post(
        "/api/v1/vehicles/",
        json={"name": "Van 1", "plate_number": "BB-222", "capacity": 8},
        headers=dispatcher_headers,
    )
    vehicle_id = create.json()["id"]

    response = client.patch(
        f"/api/v1/vehicles/{vehicle_id}/status",
        json={"status": "assigned"},
        headers=dispatcher_headers,
    )
    assert response.status_code == 409


def test_change_vehicle_status_rejects_while_on_active_trip(client, dispatcher_headers, db_session):
    create = client.post(
        "/api/v1/vehicles/",
        json={"name": "Van 1", "plate_number": "BB-333", "capacity": 8},
        headers=dispatcher_headers,
    )
    vehicle_id = create.json()["id"]

    vehicle = db_session.get(Vehicle, vehicle_id)
    vehicle.status = VehicleStatus.IN_PROGRESS
    db_session.commit()

    response = client.patch(
        f"/api/v1/vehicles/{vehicle_id}/status",
        json={"status": "maintenance"},
        headers=dispatcher_headers,
    )
    assert response.status_code == 409


def test_delete_vehicle_with_trip_history_returns_409(client, dispatcher_headers, requester_headers):
    """This exercises the real foreign-key constraint (trips.vehicle_id),
    not just an app-level check - a vehicle that has ever been on a trip
    can never be hard-deleted, only marked inactive."""
    from datetime import datetime, timedelta, timezone

    create = client.post(
        "/api/v1/vehicles/",
        json={"name": "Van History", "plate_number": "HIST-001", "capacity": 4},
        headers=dispatcher_headers,
    )
    vehicle_id = create.json()["id"]

    driver_resp = client.post(
        "/api/v1/drivers/",
        json={"name": "Driver History", "license_number": "DL-HIST-001"},
        headers=dispatcher_headers,
    )
    driver_id = driver_resp.json()["id"]

    start = datetime.now(timezone.utc) + timedelta(hours=1)
    end = start + timedelta(hours=2)
    request_resp = client.post(
        "/api/v1/trip-requests/",
        json={
            "purpose": "History test",
            "destination": "Somewhere",
            "traveler_ids": [],
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
        },
        headers=requester_headers,
    )
    request_id = request_resp.json()["id"]

    approve_resp = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )
    assert approve_resp.status_code == 200

    response = client.delete(f"/api/v1/vehicles/{vehicle_id}", headers=dispatcher_headers)
    assert response.status_code == 409

    # And it's genuinely still there, unaffected by the failed delete.
    still_there = client.get(f"/api/v1/vehicles/{vehicle_id}", headers=dispatcher_headers)
    assert still_there.status_code == 200
