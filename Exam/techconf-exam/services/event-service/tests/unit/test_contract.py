"""Test di contratto: valida le risposte contro l'OpenAPI del docente."""

from __future__ import annotations

import pytest
import responses

from contracts.validator import assert_matches_contract
from tests.conftest import USER_URL

BASE = {
    "title": "PyConf", "organizer_id": "org-1", "venue": "Aud", "city": "Roma",
    "start_date": "2026-10-01", "end_date": "2026-10-02", "capacity": 100, "price": 149.0,
}


def _as_contract_response(r):
    return {
        "status_code": r.status_code,
        "headers": dict(r.headers),
        "json": r.get_json(silent=True),
    }


def _mock_org(rsps, organizer_id="org-1", role="organizer"):
    rsps.add(
        responses.GET, f"{USER_URL}/api/v1/users/{organizer_id}",
        json={"id": organizer_id, "role": role}, status=200,
    )


@responses.activate
@pytest.mark.req("REQ-EVT-C01")
def test_contract_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert_matches_contract("event", "GET", "/health", _as_contract_response(r))


@responses.activate
@pytest.mark.req("REQ-EVT-C01")
def test_contract_create(client):
    _mock_org(responses)
    r = client.post("/api/v1/events", json=BASE)
    assert r.status_code == 201 and r.headers.get("Location")
    assert_matches_contract("event", "POST", "/api/v1/events", _as_contract_response(r))


@responses.activate
@pytest.mark.req("REQ-EVT-C01")
def test_contract_get_and_list(client):
    _mock_org(responses)
    eid = client.post("/api/v1/events", json=BASE).get_json()["id"]
    r = client.get(f"/api/v1/events/{eid}")
    assert r.status_code == 200
    assert_matches_contract("event", "GET", f"/api/v1/events/{eid}", _as_contract_response(r))
    r = client.get("/api/v1/events?page=1&page_size=20")
    assert r.status_code == 200
    assert_matches_contract("event", "GET", "/api/v1/events", _as_contract_response(r))


@responses.activate
@pytest.mark.req("REQ-EVT-C01")
def test_contract_put_patch(client):
    _mock_org(responses)
    eid = client.post("/api/v1/events", json=BASE).get_json()["id"]
    r = client.put(f"/api/v1/events/{eid}", json=BASE)
    assert r.status_code == 200
    assert_matches_contract("event", "PUT", f"/api/v1/events/{eid}", _as_contract_response(r))
    r = client.patch(f"/api/v1/events/{eid}", json={"status": "published"})
    assert r.status_code == 200
    assert_matches_contract("event", "PATCH", f"/api/v1/events/{eid}", _as_contract_response(r))


@responses.activate
@pytest.mark.req("REQ-EVT-C01")
def test_contract_delete(client):
    _mock_org(responses)
    eid = client.post("/api/v1/events", json=BASE).get_json()["id"]
    r = client.delete(f"/api/v1/events/{eid}")
    assert r.status_code == 204
    assert_matches_contract("event", "DELETE", f"/api/v1/events/{eid}", _as_contract_response(r))


@responses.activate
@pytest.mark.req("REQ-EVT-C01")
def test_contract_validation_error(client):
    r = client.post("/api/v1/events", json={"title": "ab"})
    assert r.status_code == 422
    assert_matches_contract("event", "POST", "/api/v1/events", _as_contract_response(r))
