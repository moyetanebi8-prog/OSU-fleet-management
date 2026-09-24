from app.models.driver import Driver
from app.models.enums import DriverStatus


def test_create_driver_requires_authentication(client):
    response = client.post(
        "/api/v1/drivers/", json={"name": "Sam Driver", "license_number": "LIC-001"}
    )
    assert response.status_code == 401


def test_create_driver_rejects_requester(client, requester_headers):
    response = client.post(
        "/api/v1/drivers/",
        json={"name": "Sam Driver", "license_number": "LIC-001"},
        headers=requester_headers,
    )
    assert response.status_code == 403


def test_create_driver_success(client, dispatcher_headers):
    response = client.post(
        "/api/v1/drivers/",
        json={"name": "Sam Driver", "license_number": "LIC-002"},
        headers=dispatcher_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Sam Driver"
    assert body["license_number"] == "LIC-002"
    assert body["status"] == "available"


def test_create_driver_duplicate_license_conflict(client, dispatcher_headers):
    payload = {"name": "Sam Driver", "license_number": "LIC-003"}
    first = client.post("/api/v1/drivers/", json=payload, headers=dispatcher_headers)
    assert first.status_code == 201

    second = client.post("/api/v1/drivers/", json=payload, headers=dispatcher_headers)
    assert second.status_code == 409


def test_list_drivers(client, dispatcher_headers):
    client.post(
        "/api/v1/drivers/",
        json={"name": "Sam Driver", "license_number": "LIC-004"},
        headers=dispatcher_headers,
    )
    response = client.get("/api/v1/drivers/", headers=dispatcher_headers)
    assert response.status_code == 200
    assert any(d["license_number"] == "LIC-004" for d in response.json())


def test_get_driver_not_found(client, dispatcher_headers):
    response = client.get("/api/v1/drivers/999999", headers=dispatcher_headers)
    assert response.status_code == 404


def test_update_driver_success(client, dispatcher_headers):
    create = client.post(
        "/api/v1/drivers/",
        json={"name": "Sam Driver", "license_number": "LIC-005"},
        headers=dispatcher_headers,
    )
    driver_id = create.json()["id"]

    response = client.put(
        f"/api/v1/drivers/{driver_id}",
        json={"name": "Samantha Driver", "license_number": "LIC-005"},
        headers=dispatcher_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Samantha Driver"


def test_update_driver_duplicate_license_conflict(client, dispatcher_headers):
    client.post(
        "/api/v1/drivers/",
        json={"name": "Driver A", "license_number": "LIC-006"},
        headers=dispatcher_headers,
    )
    second = client.post(
        "/api/v1/drivers/",
        json={"name": "Driver B", "license_number": "LIC-007"},
        headers=dispatcher_headers,
    )
    driver_b_id = second.json()["id"]

    response = client.put(
        f"/api/v1/drivers/{driver_b_id}",
        json={"name": "Driver B", "license_number": "LIC-006"},
        headers=dispatcher_headers,
    )
    assert response.status_code == 409


def test_change_driver_status_success(client, dispatcher_headers):
    create = client.post(
        "/api/v1/drivers/",
        json={"name": "Sam Driver", "license_number": "LIC-008"},
        headers=dispatcher_headers,
    )
    driver_id = create.json()["id"]

    response = client.patch(
        f"/api/v1/drivers/{driver_id}/status",
        json={"status": "inactive"},
        headers=dispatcher_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "inactive"


def test_change_driver_status_rejects_driving_as_manual_target(client, dispatcher_headers):
    create = client.post(
        "/api/v1/drivers/",
        json={"name": "Sam Driver", "license_number": "LIC-009"},
        headers=dispatcher_headers,
    )
    driver_id = create.json()["id"]

    response = client.patch(
        f"/api/v1/drivers/{driver_id}/status",
        json={"status": "driving"},
        headers=dispatcher_headers,
    )
    assert response.status_code == 409


def test_change_driver_status_rejects_while_driving(client, dispatcher_headers, db_session):
    create = client.post(
        "/api/v1/drivers/",
        json={"name": "Sam Driver", "license_number": "LIC-010"},
        headers=dispatcher_headers,
    )
    driver_id = create.json()["id"]

    driver = db_session.get(Driver, driver_id)
    driver.status = DriverStatus.DRIVING
    db_session.commit()

    response = client.patch(
        f"/api/v1/drivers/{driver_id}/status",
        json={"status": "available"},
        headers=dispatcher_headers,
    )
    assert response.status_code == 409
