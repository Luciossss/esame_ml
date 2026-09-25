"""Unit test del dominio: validazione, transizioni, UserClient."""

from __future__ import annotations

import pytest
import responses

from app.clients.user_client import DependencyUnavailable, UserClient
from app.domain.models import Event, EventStatus
from app.domain.service import (
    EventService,
    InvalidOrganizer,
    InvalidStatusTransition,
    ReferenceNotFound,
)
from app.domain.validation import ValidationError, validate_create
from app.repository.memory import MemoryEventRepository

BASE = {
    "title": "PyConf", "organizer_id": "org-1", "venue": "Aud", "city": "Roma",
    "start_date": "2026-10-01", "end_date": "2026-10-02", "capacity": 100, "price": 149.0,
}
USER_URL = "http://user:5001"


# --- validazione -----------------------------------------------------------
@pytest.mark.req("REQ-EVT-F01")
def test_validate_create_defaults_status_draft():
    data = validate_create(BASE)
    assert data["status"] == "draft"


@pytest.mark.req("REQ-EVT-B03")
def test_validate_dates_incoherent():
    with pytest.raises(ValidationError) as exc:
        validate_create({**BASE, "end_date": "2026-09-30"})
    assert "end_date" in exc.value.details


@pytest.mark.req("REQ-EVT-F01")
@pytest.mark.parametrize(
    "payload,bad",
    [
        ({k: v for k, v in BASE.items() if k != "title"}, "title"),
        ({**BASE, "title": "ab"}, "title"),
        ({**BASE, "capacity": 0}, "capacity"),
        ({**BASE, "capacity": 10001}, "capacity"),
        ({**BASE, "price": -1}, "price"),
        ({**BASE, "status": "archived"}, "status"),
        ({**BASE, "extra": 1}, "extra"),
        ({**BASE, "id": "x"}, "id"),
        ({**BASE, "start_date": "bad"}, "start_date"),
    ],
)
def test_validate_create_rejects(payload, bad):
    with pytest.raises(ValidationError) as exc:
        validate_create(payload)
    assert bad in exc.value.details


# --- UserClient ------------------------------------------------------------
@responses.activate
@pytest.mark.req("REQ-EVT-B01")
def test_user_client_found():
    responses.add(responses.GET, f"{USER_URL}/api/v1/users/u1",
                  json={"id": "u1", "role": "organizer"}, status=200)
    assert UserClient(USER_URL).get_user("u1")["role"] == "organizer"


@responses.activate
@pytest.mark.req("REQ-EVT-B01")
def test_user_client_not_found_returns_none():
    responses.add(responses.GET, f"{USER_URL}/api/v1/users/u1", status=404)
    assert UserClient(USER_URL).get_user("u1") is None


@responses.activate
@pytest.mark.req("REQ-EVT-B05")
def test_user_client_5xx_raises_dependency():
    responses.add(responses.GET, f"{USER_URL}/api/v1/users/u1", status=500)
    with pytest.raises(DependencyUnavailable):
        UserClient(USER_URL).get_user("u1")


@responses.activate
@pytest.mark.req("REQ-EVT-B05")
def test_user_client_timeout_raises_dependency():
    import requests
    responses.add(responses.GET, f"{USER_URL}/api/v1/users/u1",
                  body=requests.exceptions.ConnectTimeout())
    with pytest.raises(DependencyUnavailable):
        UserClient(USER_URL).get_user("u1")


# --- EventService regole ---------------------------------------------------
class _FakeClient:
    def __init__(self, user):
        self._user = user

    def get_user(self, user_id):
        return self._user


@pytest.mark.req("REQ-EVT-B01")
def test_service_reference_not_found():
    svc = EventService(MemoryEventRepository(), _FakeClient(None))
    with pytest.raises(ReferenceNotFound):
        svc.create_event(BASE)


@pytest.mark.req("REQ-EVT-B02")
def test_service_invalid_organizer():
    svc = EventService(MemoryEventRepository(), _FakeClient({"id": "x", "role": "attendee"}))
    with pytest.raises(InvalidOrganizer):
        svc.create_event(BASE)


@pytest.mark.req("REQ-EVT-B04")
def test_service_status_transitions():
    svc = EventService(MemoryEventRepository(), _FakeClient({"id": "x", "role": "organizer"}))
    ev = svc.create_event(BASE)
    assert ev.status == EventStatus.DRAFT
    ev = svc.update_event(ev.id, {"status": "published"})
    assert ev.status == EventStatus.PUBLISHED
    with pytest.raises(InvalidStatusTransition):
        svc.update_event(ev.id, {"status": "draft"})


@pytest.mark.req("REQ-EVT-B04")
def test_service_same_status_is_noop():
    svc = EventService(MemoryEventRepository(), _FakeClient({"id": "x", "role": "organizer"}))
    ev = svc.create_event(BASE)
    ev = svc.update_event(ev.id, {"status": "draft"})
    assert ev.status == EventStatus.DRAFT
