"""Test di contratto: valida le risposte contro l'OpenAPI del docente."""

from __future__ import annotations

import pytest
import responses

from contracts.validator import assert_matches_contract
from tests.conftest import EVENT_URL, USER_URL


def _as_contract_response(r):
    return {
        "status_code": r.status_code,
        "headers": dict(r.headers),
        "json": r.get_json(silent=True),
    }


def _mock_deps(rsps, user_id="u1", event_id="e1", status="published", capacity=10, price=50.0):
    rsps.add(responses.GET, f"{USER_URL}/api/v1/users/{user_id}",
             json={"id": user_id, "role": "attendee"}, status=200)
    rsps.add(responses.GET, f"{EVENT_URL}/api/v1/events/{event_id}",
             json={"id": event_id, "status": status, "capacity": capacity, "price": price},
             status=200)


def _create(client):
    return client.post("/api/v1/registrations", json={"user_id": "u1", "event_id": "e1"})


@responses.activate
@pytest.mark.req("REQ-REG-C01")
def test_contract_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert_matches_contract("registration", "GET", "/health", _as_contract_response(r))


@responses.activate
@pytest.mark.req("REQ-REG-C01")
def test_contract_create(client):
    _mock_deps(responses)
    r = _create(client)
    assert r.status_code == 201 and r.headers.get("Location")
    assert_matches_contract("registration", "POST", "/api/v1/registrations", _as_contract_response(r))


@responses.activate
@pytest.mark.req("REQ-REG-C01")
def test_contract_get_and_list(client):
    _mock_deps(responses)
    rid = _create(client).get_json()["id"]
    r = client.get(f"/api/v1/registrations/{rid}")
    assert r.status_code == 200
    assert_matches_contract("registration", "GET", f"/api/v1/registrations/{rid}", _as_contract_response(r))
    r = client.get("/api/v1/registrations?page=1&page_size=20")
    assert r.status_code == 200
    assert_matches_contract("registration", "GET", "/api/v1/registrations", _as_contract_response(r))


@responses.activate
@pytest.mark.req("REQ-REG-C01")
def test_contract_patch(client):
    _mock_deps(responses)
    rid = _create(client).get_json()["id"]
    r = client.patch(f"/api/v1/registrations/{rid}", json={"status": "cancelled"})
    assert r.status_code == 200
    assert_matches_contract("registration", "PATCH", f"/api/v1/registrations/{rid}", _as_contract_response(r))


@responses.activate
@pytest.mark.req("REQ-REG-C01")
def test_contract_delete(client):
    _mock_deps(responses)
    rid = _create(client).get_json()["id"]
    r = client.delete(f"/api/v1/registrations/{rid}")
    assert r.status_code == 204
    assert_matches_contract("registration", "DELETE", f"/api/v1/registrations/{rid}", _as_contract_response(r))


@responses.activate
@pytest.mark.req("REQ-REG-C01")
def test_contract_stats(client):
    _mock_deps(responses)
    _create(client)
    r = client.get("/api/v1/registrations/stats?event_id=e1")
    assert r.status_code == 200
    assert_matches_contract("registration", "GET", "/api/v1/registrations/stats", _as_contract_response(r))


@responses.activate
@pytest.mark.req("REQ-REG-F06")
def test_contract_put_405(client):
    r = client.put("/api/v1/registrations/x")
    assert r.status_code == 405
    assert_matches_contract("registration", "PUT", "/api/v1/registrations/x", _as_contract_response(r))


@responses.activate
@pytest.mark.req("REQ-REG-C01")
def test_contract_validation_error(client):
    r = client.post("/api/v1/registrations", json={"user_id": "u1"})
    assert r.status_code == 422
    assert_matches_contract("registration", "POST", "/api/v1/registrations", _as_contract_response(r))


@pytest.mark.req("REQ-REG-F03")
def test_invalid_status_filter_returns_422(client):
    """Regression #2: un filtro status fuori enum deve produrre 422."""
    r = client.get("/api/v1/registrations?status=invalid")
    assert r.status_code == 422
    assert r.get_json()["error"]["code"] == "VALIDATION_ERROR"
    assert_matches_contract(
        "registration",
        "GET",
        "/api/v1/registrations",
        _as_contract_response(r),
    )
