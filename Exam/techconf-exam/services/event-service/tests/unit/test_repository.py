"""Unit test del repository parametrizzati sui tre backend (memory/json/sqlite)."""

from __future__ import annotations

import pytest

from app.domain.models import Event, EventStatus
from app.repository.json_repo import JsonEventRepository
from app.repository.memory import MemoryEventRepository
from app.repository.sqlite_repo import SqliteEventRepository


def _mk(title, city="Roma", status=EventStatus.DRAFT, created_at="2026-01-01T00:00:00Z"):
    return Event(
        title=title, organizer_id="org", venue="V", city=city,
        start_date="2026-10-01", end_date="2026-10-02", capacity=10, price=99.0,
        status=status, created_at=created_at,
    )


@pytest.fixture(params=["memory", "json", "sqlite"])
def repo(request, tmp_path):
    if request.param == "memory":
        return MemoryEventRepository()
    if request.param == "json":
        return JsonEventRepository(str(tmp_path))
    return SqliteEventRepository(str(tmp_path))


@pytest.mark.req("REQ-EVT-P01")
def test_add_get(repo):
    e = _mk("A")
    repo.add(e)
    assert repo.get(e.id).title == "A"
    assert repo.get("missing") is None


@pytest.mark.req("REQ-EVT-F03")
def test_pagination(repo):
    repo.add(_mk("A", created_at="2026-01-01T00:00:00Z"))
    repo.add(_mk("B", created_at="2026-01-02T00:00:00Z"))
    repo.add(_mk("C", created_at="2026-01-03T00:00:00Z"))
    items, total = repo.list(1, 2)
    assert total == 3 and len(items) == 2 and items[0].title == "A"
    items, total = repo.list(2, 2)
    assert len(items) == 1 and items[0].title == "C"


@pytest.mark.req("REQ-EVT-B06")
def test_filters(repo):
    repo.add(_mk("A", city="Roma", status=EventStatus.PUBLISHED))
    repo.add(_mk("B", city="Milano", status=EventStatus.DRAFT))
    items, total = repo.list(1, 20, status="published")
    assert total == 1 and items[0].title == "A"
    items, total = repo.list(1, 20, city="ROMA")
    assert total == 1 and items[0].title == "A"


@pytest.mark.req("REQ-EVT-F04")
def test_replace_delete(repo):
    e = _mk("A")
    repo.add(e)
    e2 = _mk("AA", created_at=e.created_at)
    e2.id = e.id
    repo.replace(e2)
    assert repo.get(e.id).title == "AA"
    assert repo.delete(e.id) is True
    assert repo.get(e.id) is None
    assert repo.delete(e.id) is False


@pytest.mark.req("REQ-EVT-P01")
def test_json_persistence(tmp_path):
    r1 = JsonEventRepository(str(tmp_path))
    r1.add(_mk("persist"))
    r2 = JsonEventRepository(str(tmp_path))
    assert r2.list(1, 20)[1] == 1


@pytest.mark.req("REQ-EVT-P01")
def test_sqlite_persistence(tmp_path):
    r1 = SqliteEventRepository(str(tmp_path))
    r1.add(_mk("persist"))
    r2 = SqliteEventRepository(str(tmp_path))
    assert r2.list(1, 20)[1] == 1
