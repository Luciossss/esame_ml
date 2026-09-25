"""Backend di persistenza in memoria (RAM)."""

from __future__ import annotations

from ..domain.models import Event
from .base import EventRepository


def _status_value(e: Event) -> str:
    return e.status.value if hasattr(e.status, "value") else e.status


def _matches(e: Event, status: str | None, city: str | None) -> bool:
    if status is not None and _status_value(e) != status:
        return False
    if city is not None and e.city.lower() != city.lower():
        return False
    return True


class MemoryEventRepository(EventRepository):
    def __init__(self) -> None:
        self._events: dict[str, Event] = {}

    def add(self, event: Event) -> None:
        self._events[event.id] = event

    def get(self, event_id: str) -> Event | None:
        return self._events.get(event_id)

    def list(self, page, page_size, status=None, city=None):
        filtered = [e for e in self._events.values() if _matches(e, status, city)]
        filtered.sort(key=lambda e: (e.created_at, e.id))
        total = len(filtered)
        start = (page - 1) * page_size
        return filtered[start : start + page_size], total

    def replace(self, event: Event) -> None:
        self._events[event.id] = event

    def update(self, event: Event) -> None:
        self._events[event.id] = event

    def delete(self, event_id: str) -> bool:
        return self._events.pop(event_id, None) is not None
