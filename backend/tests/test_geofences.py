SQUARE = [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]


def test_create_geofence_requires_dispatcher(client, requester_headers):
    response = client.post(
        "/api/v1/geofences/",
        json={"name": "Depot", "coordinates": SQUARE},
        headers=requester_headers,
    )
    assert response.status_code == 403


def test_create_geofence_success(client, dispatcher_headers):
    response = client.post(
        "/api/v1/geofences/",
        json={"name": "Depot", "description": "Main depot yard", "coordinates": SQUARE},
        headers=dispatcher_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Depot"
    assert body["is_active"] is True
    assert len(body["coordinates"]) == 5
    assert body["coordinates"][0] == body["coordinates"][-1]


def test_create_geofence_rejects_unclosed_ring(client, dispatcher_headers):
    unclosed = [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]]
    response = client.post(
        "/api/v1/geofences/",
        json={"name": "Bad Shape", "coordinates": unclosed},
        headers=dispatcher_headers,
    )
    assert response.status_code == 422


def test_create_geofence_rejects_too_few_points(client, dispatcher_headers):
    response = client.post(
        "/api/v1/geofences/",
        json={"name": "Bad Shape", "coordinates": [[0.0, 0.0], [0.0, 1.0], [0.0, 0.0]]},
        headers=dispatcher_headers,
    )
    assert response.status_code == 422


def test_create_geofence_rejects_invalid_latitude(client, dispatcher_headers):
    bad = [[0.0, 0.0], [0.0, 91.0], [1.0, 91.0], [1.0, 0.0], [0.0, 0.0]]
    response = client.post(
        "/api/v1/geofences/", json={"name": "Bad", "coordinates": bad}, headers=dispatcher_headers
    )
    assert response.status_code == 422


def test_list_geofences_requires_dispatcher(client, requester_headers):
    response = client.get("/api/v1/geofences/", headers=requester_headers)
    assert response.status_code == 403


def test_list_geofences_returns_created(client, dispatcher_headers):
    client.post(
        "/api/v1/geofences/",
        json={"name": "Depot Zone", "coordinates": SQUARE},
        headers=dispatcher_headers,
    )
    response = client.get("/api/v1/geofences/", headers=dispatcher_headers)
    assert response.status_code == 200
    assert any(g["name"] == "Depot Zone" for g in response.json())
