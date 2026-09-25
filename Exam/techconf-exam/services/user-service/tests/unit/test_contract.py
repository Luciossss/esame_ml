"""Test di contratto: valida le risposte contro l'OpenAPI del docente.

Usa ``assert_matches_contract`` da ``contracts/validator.py`` (non modificabile) per
almeno un caso per endpoint (REQ-USR-C01).
"""

from __future__ import annotations

import pytest

from contracts.validator import assert_matches_contract


def _as_contract_response(flask_response):
    """Adatta la risposta del test client Flask al formato dict atteso dal validator.

    Il validator chiama ``response.json()`` come metodo (stile ``requests.Response``),
    mentre il test client Flask espone ``.json`` come proprietà. Il validator supporta
    anche un dict ``{"status_code", "headers", "json"}``: lo usiamo per compatibilità.
    """
    return {
        "status_code": flask_response.status_code,
        "headers": dict(flask_response.headers),
        "json": flask_response.get_json(silent=True),
    }


def _create(client, email="a@x.io", role=None):
    payload = {"first_name": "Ann", "last_name": "Lee", "email": email}
    if role:
        payload["role"] = role
    return client.post("/api/v1/users", json=payload)


@pytest.mark.req("REQ-USR-C01")
def test_contract_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert_matches_contract("user", "GET", "/health", _as_contract_response(r))


@pytest.mark.req("REQ-USR-C01")
def test_contract_create(client):
    r = _create(client)
    assert r.status_code == 201
    assert r.headers.get("Location")
    assert_matches_contract("user", "POST", "/api/v1/users", _as_contract_response(r))


@pytest.mark.req("REQ-USR-C01")
def test_contract_get_by_id(client):
    uid = _create(client, email="get@x.io").get_json()["id"]
    r = client.get(f"/api/v1/users/{uid}")
    assert r.status_code == 200
    assert_matches_contract("user", "GET", f"/api/v1/users/{uid}", _as_contract_response(r))


@pytest.mark.req("REQ-USR-C01")
def test_contract_list(client):
    _create(client, email="list@x.io")
    r = client.get("/api/v1/users?page=1&page_size=20")
    assert r.status_code == 200
    assert_matches_contract("user", "GET", "/api/v1/users", _as_contract_response(r))


@pytest.mark.req("REQ-USR-C01")
def test_contract_put(client):
    uid = _create(client, email="put@x.io").get_json()["id"]
    r = client.put(
        f"/api/v1/users/{uid}",
        json={"first_name": "Anna", "last_name": "Lee", "email": "put@x.io", "role": "speaker"},
    )
    assert r.status_code == 200
    assert_matches_contract("user", "PUT", f"/api/v1/users/{uid}", _as_contract_response(r))


@pytest.mark.req("REQ-USR-C01")
def test_contract_patch(client):
    uid = _create(client, email="patch@x.io").get_json()["id"]
    r = client.patch(f"/api/v1/users/{uid}", json={"company": "ACME"})
    assert r.status_code == 200
    assert_matches_contract("user", "PATCH", f"/api/v1/users/{uid}", _as_contract_response(r))


@pytest.mark.req("REQ-USR-C01")
def test_contract_delete(client):
    uid = _create(client, email="del@x.io").get_json()["id"]
    r = client.delete(f"/api/v1/users/{uid}")
    assert r.status_code == 204
    assert_matches_contract("user", "DELETE", f"/api/v1/users/{uid}", _as_contract_response(r))


@pytest.mark.req("REQ-USR-C01")
def test_contract_error_validation(client):
    r = client.post("/api/v1/users", json={"last_name": "Lee", "email": "x@y.io"})
    assert r.status_code == 422
    assert_matches_contract("user", "POST", "/api/v1/users", _as_contract_response(r))
