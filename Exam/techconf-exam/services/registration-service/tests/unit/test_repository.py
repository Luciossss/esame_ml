"""Unit test del repository parametrizzati sui tre backend (memory/json/sqlite)."""

from __future__ import annotations

import pytest

from app.domain.models import Registration, RegistrationStatus
from app.repository.json_repo import JsonRegistrationRepository
from app.repository.memory import MemoryRegistrationRepository
from app.repository.sqlite_repo import SqliteRegistrationRepository


def _mk(user_id="u", event_id="e", status=RegistrationStatus.CONFIRMED,
        amount=10.0, created_at="2026-01-01T00:00:00Z"):
    return Registration(
        user_id=user_id, event_id=event_id, amount=amount, status=status, created_at=created_at
    )


@pytest.fixture(params=["memory", "json", "sqlite"])
def repo(request, tmp_path):
    if request.param == "memory":
        return MemoryRegistrationRepository()
    if request.param == "json":
        return JsonRegistrationRepository(str(tmp_path))
    return SqliteRegistrationRepository(str(tmp_path))


@pytest.mark.req("REQ-REG-P01")
def test_add_get(repo):
    r = _mk()
    repo.add(r)
    assert repo.get(r.id).user_id == "u"
    assert repo.get("missing") is None


@pytest.mark.req("REQ-REG-F03")
def test_list_filters(repo):
    repo.add(_mk(user_id="u1", event_id="e1", created_at="2026-01-01T00:00:00Z"))
    repo.add(_mk(user_id="u2", event_id="e1", status=RegistrationStatus.CANCELLED, created_at="2026-01-02T00:00:00Z"))
    items, total = repo.list(1, 20, event_id="e1")
    assert total == 2
    items, total = repo.list(1, 20, status="confirmed")
    assert total == 1 and items[0].user_id == "u1"
    items, total = repo.list(1, 20, user_id="u2")
    assert total == 1


@pytest.mark.req("REQ-REG-B05")
def test_count_confirmed(repo):
    repo.add(_mk(user_id="u1", event_id="e1"))
    repo.add(_mk(user_id="u2", event_id="e1"))
    repo.add(_mk(user_id="u3", event_id="e1", status=RegistrationStatus.CANCELLED))
    repo.add(_mk(user_id="u4", event_id="e2"))
    assert repo.count_confirmed("e1") == 2
    assert repo.count_confirmed("e2") == 1


@pytest.mark.req("REQ-REG-B04")
def test_find_confirmed(repo):
    r = _mk(user_id="u1", event_id="e1")
    repo.add(r)
    assert repo.find_confirmed("u1", "e1").id == r.id
    assert repo.find_confirmed("u1", "e2") is None


@pytest.mark.req("REQ-REG-F04")
def test_update_delete(repo):
    r = _mk()
    repo.add(r)
    r2 = _mk(created_at=r.created_at, status=RegistrationStatus.CANCELLED)
    r2.id = r.id
    repo.update(r2)
    assert repo.get(r.id).status == RegistrationStatus.CANCELLED
    assert repo.delete(r.id) is True
    assert repo.get(r.id) is None
    assert repo.delete(r.id) is False


@pytest.mark.req("REQ-REG-P01")
def test_json_persistence(tmp_path):
    r1 = JsonRegistrationRepository(str(tmp_path))
    r1.add(_mk())
    assert JsonRegistrationRepository(str(tmp_path)).list(1, 20)[1] == 1


@pytest.mark.req("REQ-REG-P01")
def test_sqlite_persistence(tmp_path):
    r1 = SqliteRegistrationRepository(str(tmp_path))
    r1.add(_mk())
    assert SqliteRegistrationRepository(str(tmp_path)).list(1, 20)[1] == 1
