"""Unit test del repository parametrizzati sui tre backend (memory/json/sqlite).

Verifica che i backend abbiano comportamento identico (REQ-USR-P01), inclusa la
persistenza su disco per json/sqlite (riapertura dal file).
"""

from __future__ import annotations

import pytest

from app.domain.models import Role, User
from app.repository.json_repo import JsonUserRepository
from app.repository.memory import MemoryUserRepository
from app.repository.sqlite_repo import SqliteUserRepository


def _mk(first, email, role=Role.ATTENDEE, created_at="2026-01-01T00:00:00Z"):
    return User(first_name=first, last_name="X", email=email, role=role, created_at=created_at)


@pytest.fixture(params=["memory", "json", "sqlite"])
def repo(request, tmp_path):
    if request.param == "memory":
        return MemoryUserRepository()
    if request.param == "json":
        return JsonUserRepository(str(tmp_path))
    return SqliteUserRepository(str(tmp_path))


@pytest.mark.req("REQ-USR-P01")
def test_add_and_get(repo):
    u = _mk("A", "a@x.io")
    repo.add(u)
    got = repo.get(u.id)
    assert got is not None and got.email == "a@x.io"
    assert repo.get("missing") is None


@pytest.mark.req("REQ-USR-B01")
def test_find_by_email_case_insensitive(repo):
    u = _mk("A", "Mixed@Case.IO")
    repo.add(u)
    assert repo.find_by_email("mixed@case.io").id == u.id
    assert repo.find_by_email("no@one.io") is None


@pytest.mark.req("REQ-USR-F03")
def test_list_pagination_and_total(repo):
    repo.add(_mk("A", "a@x.io", created_at="2026-01-01T00:00:00Z"))
    repo.add(_mk("B", "b@x.io", created_at="2026-01-02T00:00:00Z"))
    repo.add(_mk("C", "c@x.io", created_at="2026-01-03T00:00:00Z"))
    items, total = repo.list(1, 2)
    assert total == 3 and len(items) == 2 and items[0].email == "a@x.io"
    items, total = repo.list(2, 2)
    assert total == 3 and len(items) == 1 and items[0].email == "c@x.io"


@pytest.mark.req("REQ-USR-B03")
def test_list_filters(repo):
    repo.add(_mk("A", "org@x.io", role=Role.ORGANIZER))
    repo.add(_mk("B", "att@x.io", role=Role.ATTENDEE))
    items, total = repo.list(1, 20, role="organizer")
    assert total == 1 and items[0].email == "org@x.io"
    items, total = repo.list(1, 20, email="ORG@x.io")
    assert total == 1 and items[0].email == "org@x.io"


@pytest.mark.req("REQ-USR-F04")
def test_replace_and_update(repo):
    u = _mk("A", "a@x.io")
    repo.add(u)
    u2 = User(
        first_name="AA", last_name="X", email="a@x.io", role=Role.SPEAKER,
        id=u.id, created_at=u.created_at, updated_at="2026-05-05T00:00:00Z",
    )
    repo.replace(u2)
    assert repo.get(u.id).first_name == "AA" and repo.get(u.id).role == Role.SPEAKER


@pytest.mark.req("REQ-USR-F06")
def test_delete(repo):
    u = _mk("A", "a@x.io")
    repo.add(u)
    assert repo.delete(u.id) is True
    assert repo.get(u.id) is None
    assert repo.delete(u.id) is False


@pytest.mark.req("REQ-USR-P01")
def test_json_persistence(tmp_path):
    r1 = JsonUserRepository(str(tmp_path))
    r1.add(_mk("A", "persist@x.io"))
    r2 = JsonUserRepository(str(tmp_path))
    assert r2.find_by_email("persist@x.io") is not None


@pytest.mark.req("REQ-USR-P01")
def test_sqlite_persistence(tmp_path):
    r1 = SqliteUserRepository(str(tmp_path))
    r1.add(_mk("A", "persist@x.io"))
    r2 = SqliteUserRepository(str(tmp_path))
    assert r2.find_by_email("persist@x.io") is not None
