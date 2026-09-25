"""Backend di persistenza su file JSON.

Gli utenti sono serializzati in un unico file ``users.json`` in ``DATA_DIR``. Il file
viene caricato all'avvio e riscritto interamente a ogni operazione di scrittura. Usa solo
la libreria standard (``json``), nessun DBMS.
"""

from __future__ import annotations

import json
import os

from ..domain.models import User
from .base import UserRepository


def _role_value(user: User) -> str:
    return user.role.value if hasattr(user.role, "value") else user.role


def _matches(user: User, role: str | None, email: str | None) -> bool:
    if role is not None and _role_value(user) != role:
        return False
    if email is not None and user.email.lower() != email.lower():
        return False
    return True


class JsonUserRepository(UserRepository):
    """Repository utenti persistito su un file JSON."""

    def __init__(self, data_dir: str, filename: str = "users.json") -> None:
        self._data_dir = data_dir
        self._path = os.path.join(data_dir, filename)
        self._users: dict[str, User] = {}
        self._load()

    # --- I/O ---------------------------------------------------------------
    def _load(self) -> None:
        if os.path.isfile(self._path):
            with open(self._path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            self._users = {d["id"]: User.from_dict(d) for d in raw}
        else:
            self._users = {}

    def _flush(self) -> None:
        os.makedirs(self._data_dir, exist_ok=True)
        payload = [u.to_dict() for u in self._users.values()]
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path)

    # --- API ---------------------------------------------------------------
    def add(self, user: User) -> None:
        self._users[user.id] = user
        self._flush()

    def get(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def list(
        self,
        page: int,
        page_size: int,
        role: str | None = None,
        email: str | None = None,
    ) -> tuple[list[User], int]:
        filtered = [u for u in self._users.values() if _matches(u, role, email)]
        filtered.sort(key=lambda u: (u.created_at, u.id))
        total = len(filtered)
        start = (page - 1) * page_size
        return filtered[start : start + page_size], total

    def replace(self, user: User) -> None:
        self._users[user.id] = user
        self._flush()

    def update(self, user: User) -> None:
        self._users[user.id] = user
        self._flush()

    def delete(self, user_id: str) -> bool:
        existed = self._users.pop(user_id, None) is not None
        if existed:
            self._flush()
        return existed

    def find_by_email(self, email_lower: str) -> User | None:
        for user in self._users.values():
            if user.email.lower() == email_lower:
                return user
        return None
