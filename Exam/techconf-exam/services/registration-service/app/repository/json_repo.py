"""Backend di persistenza su file JSON."""

from __future__ import annotations

import json
import os

from ..domain.models import Registration, RegistrationStatus
from .base import RegistrationRepository


def _status_value(r: Registration) -> str:
    return r.status.value if hasattr(r.status, "value") else r.status


def _matches(r: Registration, user_id, event_id, status) -> bool:
    if user_id is not None and r.user_id != user_id:
        return False
    if event_id is not None and r.event_id != event_id:
        return False
    if status is not None and _status_value(r) != status:
        return False
    return True


class JsonRegistrationRepository(RegistrationRepository):
    def __init__(self, data_dir: str, filename: str = "registrations.json") -> None:
        self._data_dir = data_dir
        self._path = os.path.join(data_dir, filename)
        self._items: dict[str, Registration] = {}
        self._load()

    def _load(self) -> None:
        if os.path.isfile(self._path):
            with open(self._path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            self._items = {d["id"]: Registration.from_dict(d) for d in raw}
        else:
            self._items = {}

    def _flush(self) -> None:
        os.makedirs(self._data_dir, exist_ok=True)
        payload = [r.to_dict() for r in self._items.values()]
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path)

    def add(self, registration: Registration) -> None:
        self._items[registration.id] = registration
        self._flush()

    def get(self, registration_id: str) -> Registration | None:
        return self._items.get(registration_id)

    def list(self, page, page_size, user_id=None, event_id=None, status=None):
        filtered = [r for r in self._items.values() if _matches(r, user_id, event_id, status)]
        filtered.sort(key=lambda r: (r.created_at, r.id))
        total = len(filtered)
        start = (page - 1) * page_size
        return filtered[start : start + page_size], total

    def update(self, registration: Registration) -> None:
        self._items[registration.id] = registration
        self._flush()

    def delete(self, registration_id: str) -> bool:
        existed = self._items.pop(registration_id, None) is not None
        if existed:
            self._flush()
        return existed

    def count_confirmed(self, event_id: str) -> int:
        return sum(
            1
            for r in self._items.values()
            if r.event_id == event_id and _status_value(r) == RegistrationStatus.CONFIRMED.value
        )

    def find_confirmed(self, user_id: str, event_id: str) -> Registration | None:
        for r in self._items.values():
            if (
                r.user_id == user_id
                and r.event_id == event_id
                and _status_value(r) == RegistrationStatus.CONFIRMED.value
            ):
                return r
        return None
