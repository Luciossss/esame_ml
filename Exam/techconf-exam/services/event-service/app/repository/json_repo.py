"""Backend di persistenza su file JSON."""

from __future__ import annotations

import json
import os

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


class JsonEventRepository(EventRepository):
    def __init__(self, data_dir: str, filename: str = "events.json") -> None:
        self._data_dir = data_dir
        self._path = os.path.join(data_dir, filename)
        self._events: dict[str, Event] = {}
        self._load()

    def _load(self) -> None:
        if os.path.isfile(self._path):
            with open(self._path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            self._events = {d["id"]: Event.from_dict(d) for d in raw}
        else:
            self._events = {}

    def _flush(self) -> None:
        os.makedirs(self._data_dir, exist_ok=True)
        payload = [e.to_dict() for e in self._events.values()]
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path)

    def add(self, event: Event) -> None:
        self._events[event.id] = event
        self._flush()

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
        self._flush()

    def update(self, event: Event) -> None:
        self._events[event.id] = event
        self._flush()

    def delete(self, event_id: str) -> bool:
        existed = self._events.pop(event_id, None) is not None
        if existed:
            self._flush()
        return existed
