"""Backend di persistenza in memoria (RAM).

Nessuna persistenza su disco: i dati sono azzerati a ogni riavvio. È il backend di
default (``STORAGE_BACKEND=memory``).
"""

from __future__ import annotations

from ..domain.models import User
from .base import UserRepository


def _matches(user: User, role: str | None, email: str | None) -> bool:
    if role is not None and (user.role.value if hasattr(user.role, "value") else user.role) != role:
        return False
    if email is not None and user.email.lower() != email.lower():
        return False
    return True


class MemoryUserRepository(UserRepository):
    """Repository utenti basato su un dizionario in memoria."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    def add(self, user: User) -> None:
        self._users[user.id] = user

    def get(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def list(
        self,
        page: int,
        page_size: int,
        role: str | None = None,
        email: str | None = None,
    ) -> tuple[list[User], int]:
        # Ordinamento stabile per created_at, poi id, così la paginazione è deterministica.
        filtered = [u for u in self._users.values() if _matches(u, role, email)]
        filtered.sort(key=lambda u: (u.created_at, u.id))
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        return filtered[start:end], total

    def replace(self, user: User) -> None:
        self._users[user.id] = user

    def update(self, user: User) -> None:
        self._users[user.id] = user

    def delete(self, user_id: str) -> bool:
        return self._users.pop(user_id, None) is not None

    def find_by_email(self, email_lower: str) -> User | None:
        for user in self._users.values():
            if user.email.lower() == email_lower:
                return user
        return None
