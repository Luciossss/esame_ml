"""Unit test del dominio: modelli, validazione e regole di business.

Ogni test è tracciato al requisito con il marker ``@pytest.mark.req``.
"""

from __future__ import annotations

import re
import uuid

import pytest

from app.domain.models import Role, User, new_id, now_iso
from app.domain.service import EmailAlreadyExists, UserNotFound, UserService
from app.domain.validation import ValidationError, validate_create, validate_update
from app.repository.memory import MemoryUserRepository


# --------------------------------------------------------------------------- #
# Modelli
# --------------------------------------------------------------------------- #
@pytest.mark.req("REQ-USR-F01")
def test_new_id_is_uuid_v4():
    value = new_id()
    parsed = uuid.UUID(value)
    assert parsed.version == 4


@pytest.mark.req("REQ-USR-F01")
def test_now_iso_format():
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", now_iso())


@pytest.mark.req("REQ-USR-C01")
def test_user_to_dict_shape_and_role_normalization():
    u = User(first_name="A", last_name="B", email="a@x.io", role="organizer")
    d = u.to_dict()
    assert set(d) == {
        "id", "first_name", "last_name", "email", "company", "role",
        "created_at", "updated_at",
    }
    assert d["role"] == "organizer"
    assert d["company"] is None
    assert isinstance(u.role, Role)


# --------------------------------------------------------------------------- #
# Validazione
# --------------------------------------------------------------------------- #
@pytest.mark.req("REQ-USR-F01")
def test_validate_create_defaults_role_attendee():
    data = validate_create({"first_name": "A", "last_name": "B", "email": "a@x.io"})
    assert data["role"] == "attendee"
    assert data["company"] is None


@pytest.mark.req("REQ-USR-F01")
@pytest.mark.parametrize(
    "payload,bad_field",
    [
        ({"last_name": "B", "email": "a@x.io"}, "first_name"),
        ({"first_name": "A", "last_name": "B", "email": "not-an-email"}, "email"),
        ({"first_name": "", "last_name": "B", "email": "a@x.io"}, "first_name"),
        ({"first_name": "A" * 51, "last_name": "B", "email": "a@x.io"}, "first_name"),
        ({"first_name": "A", "last_name": "B", "email": "a@x.io", "extra": 1}, "extra"),
        ({"first_name": "A", "last_name": "B", "email": "a@x.io", "id": "z"}, "id"),
        ({"first_name": "A", "last_name": "B", "email": "a@x.io", "role": "boss"}, "role"),
        ({"first_name": "A", "last_name": "B", "email": "a@x.io", "company": "C" * 101}, "company"),
    ],
)
def test_validate_create_rejects(payload, bad_field):
    with pytest.raises(ValidationError) as exc:
        validate_create(payload)
    assert bad_field in exc.value.details


@pytest.mark.req("REQ-USR-F05")
def test_validate_update_partial_and_rejects_readonly():
    assert validate_update({"company": "ACME"}) == {"company": "ACME"}
    with pytest.raises(ValidationError):
        validate_update({"email": "nope"})
    with pytest.raises(ValidationError):
        validate_update({"created_at": "2020-01-01T00:00:00Z"})


# --------------------------------------------------------------------------- #
# Regole di business (UserService)
# --------------------------------------------------------------------------- #
@pytest.fixture
def service() -> UserService:
    return UserService(MemoryUserRepository())


@pytest.mark.req("REQ-USR-B02")
def test_email_stored_lowercase(service):
    u = service.create_user({"first_name": "Ann", "last_name": "Lee", "email": "Ann.Lee@X.IO"})
    assert u.email == "ann.lee@x.io"


@pytest.mark.req("REQ-USR-B01")
def test_email_unique_case_insensitive(service):
    service.create_user({"first_name": "A", "last_name": "B", "email": "dup@x.io"})
    with pytest.raises(EmailAlreadyExists):
        service.create_user({"first_name": "C", "last_name": "D", "email": "DUP@x.io"})


@pytest.mark.req("REQ-USR-B01")
def test_patch_same_email_same_user_allowed(service):
    u = service.create_user({"first_name": "A", "last_name": "B", "email": "self@x.io"})
    updated = service.update_user(u.id, {"email": "SELF@x.io"})
    assert updated.email == "self@x.io"


@pytest.mark.req("REQ-USR-B01")
def test_patch_email_conflict_other_user(service):
    a = service.create_user({"first_name": "A", "last_name": "B", "email": "a@x.io"})
    b = service.create_user({"first_name": "C", "last_name": "D", "email": "b@x.io"})
    with pytest.raises(EmailAlreadyExists):
        service.update_user(b.id, {"email": "a@x.io"})
    assert a.email == "a@x.io"


@pytest.mark.req("REQ-USR-F02")
def test_get_missing_raises(service):
    with pytest.raises(UserNotFound):
        service.get_user("does-not-exist")


@pytest.mark.req("REQ-USR-F04")
def test_replace_updates_updated_at_keeps_created_at(service, monkeypatch):
    u = service.create_user({"first_name": "A", "last_name": "B", "email": "a@x.io"})
    # forza un timestamp successivo
    import app.domain.service as svc_mod
    monkeypatch.setattr(svc_mod, "now_iso", lambda: "2999-01-01T00:00:00Z")
    r = service.replace_user(
        u.id,
        {"first_name": "Anna", "last_name": "B", "email": "a@x.io", "role": "speaker"},
    )
    assert r.created_at == u.created_at
    assert r.updated_at == "2999-01-01T00:00:00Z"
    assert r.role == Role.SPEAKER


@pytest.mark.req("REQ-USR-F06")
def test_delete_then_missing(service):
    u = service.create_user({"first_name": "A", "last_name": "B", "email": "a@x.io"})
    service.delete_user(u.id)
    with pytest.raises(UserNotFound):
        service.get_user(u.id)
    with pytest.raises(UserNotFound):
        service.delete_user(u.id)


@pytest.mark.req("REQ-USR-B03")
def test_list_filters_role_and_email(service):
    service.create_user({"first_name": "A", "last_name": "B", "email": "org@x.io", "role": "organizer"})
    service.create_user({"first_name": "C", "last_name": "D", "email": "att@x.io"})
    items, total = service.list_users(1, 20, role="organizer")
    assert total == 1 and items[0].email == "org@x.io"
    items, total = service.list_users(1, 20, email="ATT@x.io")
    assert total == 1 and items[0].email == "att@x.io"
