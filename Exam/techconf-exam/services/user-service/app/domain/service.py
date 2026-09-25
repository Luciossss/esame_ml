"""Servizio di dominio del user-service.

Orchestra validazione e persistenza e applica le regole di business:

* **REQ-USR-B01** email univoca case-insensitive -> ``EmailAlreadyExists`` (409),
  con eccezione per lo stesso utente in aggiornamento;
* **REQ-USR-B02** email memorizzata sempre in minuscolo;
* **REQ-USR-B03** filtri lista per ``role`` ed ``email`` (delegati al repository).

Il livello HTTP traduce le eccezioni di dominio negli opportuni status/code.
Questo modulo non conosce Flask: dipende solo dai modelli e dall'interfaccia repository.
"""

from __future__ import annotations

from typing import Any

from .models import User, now_iso
from .validation import validate_create, validate_update
from ..repository.base import UserRepository


class UserNotFound(Exception):
    """L'utente richiesto non esiste (-> 404)."""


class EmailAlreadyExists(Exception):
    """Esiste già un utente con quell'email (-> 409)."""

    def __init__(self, email: str) -> None:
        super().__init__("Email already exists")
        self.email = email


class UserService:
    """Logica applicativa per gli utenti."""

    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository

    # --- helper interni ----------------------------------------------------
    def _ensure_email_unique(self, email_lower: str, exclude_id: str | None = None) -> None:
        """Applica REQ-USR-B01: nessun altro utente con la stessa email (lowercase)."""
        existing = self._repo.find_by_email(email_lower)
        if existing is not None and existing.id != exclude_id:
            raise EmailAlreadyExists(email_lower)

    # --- comandi -----------------------------------------------------------
    def create_user(self, payload: Any) -> User:
        """Crea un utente. Solleva ValidationError o EmailAlreadyExists."""
        data = validate_create(payload)
        email_lower = data["email"].lower()  # REQ-USR-B02
        self._ensure_email_unique(email_lower)

        user = User(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=email_lower,
            company=data["company"],
            role=data["role"],
        )
        self._repo.add(user)
        return user

    def get_user(self, user_id: str) -> User:
        user = self._repo.get(user_id)
        if user is None:
            raise UserNotFound(user_id)
        return user

    def list_users(
        self,
        page: int,
        page_size: int,
        role: str | None = None,
        email: str | None = None,
    ) -> tuple[list[User], int]:
        """REQ-USR-B03: filtri per role ed email (case-insensitive nel repo)."""
        return self._repo.list(page, page_size, role=role, email=email)

    def replace_user(self, user_id: str, payload: Any) -> User:
        """PUT: sostituisce integralmente i campi modificabili."""
        current = self._repo.get(user_id)
        if current is None:
            raise UserNotFound(user_id)

        data = validate_create(payload)
        email_lower = data["email"].lower()  # REQ-USR-B02
        self._ensure_email_unique(email_lower, exclude_id=user_id)

        updated = User(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=email_lower,
            company=data["company"],
            role=data["role"],
            id=current.id,
            created_at=current.created_at,
            updated_at=now_iso(),
        )
        self._repo.replace(updated)
        return updated

    def update_user(self, user_id: str, payload: Any) -> User:
        """PATCH: aggiorna solo i campi forniti."""
        current = self._repo.get(user_id)
        if current is None:
            raise UserNotFound(user_id)

        changes = validate_update(payload)

        if "email" in changes:
            email_lower = changes["email"].lower()  # REQ-USR-B02
            self._ensure_email_unique(email_lower, exclude_id=user_id)
        else:
            email_lower = current.email

        updated = User(
            first_name=changes.get("first_name", current.first_name),
            last_name=changes.get("last_name", current.last_name),
            email=email_lower,
            company=changes["company"] if "company" in changes else current.company,
            role=changes.get("role", current.role),
            id=current.id,
            created_at=current.created_at,
            updated_at=now_iso(),
        )
        self._repo.update(updated)
        return updated

    def delete_user(self, user_id: str) -> None:
        if not self._repo.delete(user_id):
            raise UserNotFound(user_id)
