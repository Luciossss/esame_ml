"""Unit test del dominio: validazione, regole di business, client."""

from __future__ import annotations

import pytest
import responses

from app.clients import DependencyUnavailable
from app.clients.event_client import EventClient
from app.clients.user_client import UserClient
from app.domain.models import RegistrationStatus
from app.domain.service import (
    AlreadyRegistered,
    EventFull,
    EventNotFound,
    EventNotOpen,
    InvalidStatusTransition,
    ReferenceNotFound,
    RegistrationService,
)
from app.domain.validation import ValidationError, validate_create, validate_patch
from app.repository.memory import MemoryRegistrationRepository

U = "http://user:5001"
E = "http://event:5002"


# --- validazione -----------------------------------------------------------
@pytest.mark.req("REQ-REG-F01")
def test_validate_create_ok():
    assert validate_create({"user_id": "u", "event_id": "e"}) == {"user_id": "u", "event_id": "e"}


@pytest.mark.req("REQ-REG-F01")
@pytest.mark.parametrize(
    "payload,bad",
    [
        ({"event_id": "e"}, "user_id"),
        ({"user_id": "u"}, "event_id"),
        ({"user_id": "u", "event_id": "e", "amount": 10}, "amount"),
        ({"user_id": "u", "event_id": "e", "status": "confirmed"}, "status"),
        ({"user_id": "u", "event_id": "e", "x": 1}, "x"),
    ],
)
def test_validate_create_rejects(payload, bad):
    with pytest.raises(ValidationError) as exc:
        validate_create(payload)
    assert bad in exc.value.details


@pytest.mark.req("REQ-REG-F04")
def test_validate_patch():
    assert validate_patch({"status": "cancelled"}) == {"status": "cancelled"}
    with pytest.raises(ValidationError):
        validate_patch({"status": "archived"})
    with pytest.raises(ValidationError):
        validate_patch({"amount": 5})


# --- client ----------------------------------------------------------------
@responses.activate
@pytest.mark.req("REQ-REG-B02")
def test_event_client_found_and_404():
    responses.add(responses.GET, f"{E}/api/v1/events/e1", json={"id": "e1"}, status=200)
    responses.add(responses.GET, f"{E}/api/v1/events/e2", status=404)
    ec = EventClient(E)
    assert ec.get_event("e1")["id"] == "e1"
    assert ec.get_event("e2") is None


@responses.activate
@pytest.mark.req("REQ-REG-B09")
def test_event_client_5xx_raises():
    responses.add(responses.GET, f"{E}/api/v1/events/e1", status=503)
    with pytest.raises(DependencyUnavailable):
        EventClient(E).get_event("e1")


@responses.activate
@pytest.mark.req("REQ-REG-B09")
def test_user_client_timeout_raises():
    import requests
    responses.add(responses.GET, f"{U}/api/v1/users/u1", body=requests.exceptions.ConnectTimeout())
    with pytest.raises(DependencyUnavailable):
        UserClient(U).get_user("u1")


# --- service regole --------------------------------------------------------
class _FakeUser:
    def __init__(self, exists=True):
        self._exists = exists

    def get_user(self, user_id):
        return {"id": user_id} if self._exists else None


class _FakeEvent:
    def __init__(self, event):
        self._event = event

    def get_event(self, event_id):
        return self._event


_DEFAULT_EVENT = {"id": "e1", "status": "published", "capacity": 2, "price": 149.0}
_NO_EVENT = object()  # sentinella per "evento inesistente" (get_event -> None)


def _svc(user_exists=True, event=_NO_EVENT):
    if event is _NO_EVENT:
        event = _DEFAULT_EVENT
    return RegistrationService(MemoryRegistrationRepository(), _FakeUser(user_exists), _FakeEvent(event))


@pytest.mark.req("REQ-REG-B01")
def test_user_missing():
    with pytest.raises(ReferenceNotFound):
        _svc(user_exists=False).create_registration({"user_id": "x", "event_id": "e1"})


@pytest.mark.req("REQ-REG-B02")
def test_event_missing():
    with pytest.raises(ReferenceNotFound):
        _svc(event=None).create_registration({"user_id": "u", "event_id": "e1"})


@pytest.mark.req("REQ-REG-B03")
def test_event_not_open():
    with pytest.raises(EventNotOpen):
        _svc(event={"id": "e1", "status": "draft", "capacity": 5, "price": 10}).create_registration(
            {"user_id": "u", "event_id": "e1"}
        )


@pytest.mark.req("REQ-REG-B06")
def test_amount_from_event():
    svc = _svc()
    reg = svc.create_registration({"user_id": "u", "event_id": "e1"})
    assert reg.amount == 149.0 and reg.status == RegistrationStatus.CONFIRMED


@pytest.mark.req("REQ-REG-B04")
def test_already_registered():
    svc = _svc()
    svc.create_registration({"user_id": "u", "event_id": "e1"})
    with pytest.raises(AlreadyRegistered):
        svc.create_registration({"user_id": "u", "event_id": "e1"})


@pytest.mark.req("REQ-REG-B05")
def test_event_full_and_free_seat():
    svc = _svc(event={"id": "e1", "status": "published", "capacity": 1, "price": 10})
    r1 = svc.create_registration({"user_id": "u1", "event_id": "e1"})
    with pytest.raises(EventFull):
        svc.create_registration({"user_id": "u2", "event_id": "e1"})
    svc.update_registration(r1.id, {"status": "cancelled"})
    r3 = svc.create_registration({"user_id": "u2", "event_id": "e1"})
    assert r3.status == RegistrationStatus.CONFIRMED


@pytest.mark.req("REQ-REG-B07")
def test_invalid_transition():
    svc = _svc()
    r = svc.create_registration({"user_id": "u", "event_id": "e1"})
    svc.update_registration(r.id, {"status": "cancelled"})
    with pytest.raises(InvalidStatusTransition):
        svc.update_registration(r.id, {"status": "confirmed"})


@pytest.mark.req("REQ-REG-B08")
def test_stats_and_missing_event():
    svc = _svc(event={"id": "e1", "status": "published", "capacity": 3, "price": 10})
    svc.create_registration({"user_id": "u1", "event_id": "e1"})
    stats = svc.stats("e1")
    assert stats == {"event_id": "e1", "capacity": 3, "confirmed": 1, "available": 2}
    with pytest.raises(ValidationError):
        svc.stats(None)
    svc2 = RegistrationService(MemoryRegistrationRepository(), _FakeUser(), _FakeEvent(None))
    with pytest.raises(EventNotFound):
        svc2.stats("ghost")
