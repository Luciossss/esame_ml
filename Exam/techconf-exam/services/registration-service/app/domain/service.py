"""Servizio di dominio del registration-service.

Orchestra validazione, chiamate a user/event e persistenza, applicando le regole:

* B01 user esiste            -> ReferenceNotFound (422 REFERENCE_NOT_FOUND)
* B02 event esiste           -> ReferenceNotFound (422 REFERENCE_NOT_FOUND)
* B03 event published        -> EventNotOpen (422 EVENT_NOT_OPEN)
* B04 no doppia confirmed    -> AlreadyRegistered (409 ALREADY_REGISTERED)
* B05 capienza               -> EventFull (409 EVENT_FULL); cancellazione libera posto
* B06 amount = event.price
* B07 transizione confirmed->cancelled -> InvalidStatusTransition (422)
* B08 stats {event_id, capacity, confirmed, available}
* B09 dipendenza giù         -> DependencyUnavailable (503)
"""

from __future__ import annotations

from typing import Any

from ..clients import DependencyUnavailable  # noqa: F401 (ri-esportato per gli handler)
from ..clients.event_client import EventClient
from ..clients.user_client import UserClient
from ..repository.base import RegistrationRepository
from .models import Registration, RegistrationStatus, now_iso
from .validation import ValidationError, validate_create, validate_patch


class RegistrationNotFound(Exception):
    """Iscrizione inesistente (-> 404)."""


class EventNotFound(Exception):
    """Evento inesistente in stats (-> 404)."""


class ReferenceNotFound(Exception):
    """user_id o event_id inesistente (-> 422 REFERENCE_NOT_FOUND)."""

    def __init__(self, field: str) -> None:
        super().__init__(field)
        self.field = field


class EventNotOpen(Exception):
    """Evento non published (-> 422 EVENT_NOT_OPEN)."""


class AlreadyRegistered(Exception):
    """Doppia iscrizione confermata (-> 409 ALREADY_REGISTERED)."""


class EventFull(Exception):
    """Capienza raggiunta (-> 409 EVENT_FULL)."""


class InvalidStatusTransition(Exception):
    """Transizione di stato non ammessa (-> 422 INVALID_STATUS_TRANSITION)."""


class RegistrationService:
    def __init__(
        self,
        repository: RegistrationRepository,
        user_client: UserClient,
        event_client: EventClient,
    ) -> None:
        self._repo = repository
        self._users = user_client
        self._events = event_client

    # --- comandi -----------------------------------------------------------
    def create_registration(self, payload: Any) -> Registration:
        data = validate_create(payload)
        user_id, event_id = data["user_id"], data["event_id"]

        # B01: utente esiste
        if self._users.get_user(user_id) is None:
            raise ReferenceNotFound("user_id")

        # B02: evento esiste
        event = self._events.get_event(event_id)
        if event is None:
            raise ReferenceNotFound("event_id")

        # B03: evento published
        if event.get("status") != "published":
            raise EventNotOpen()

        # B04: nessuna doppia iscrizione confermata
        if self._repo.find_confirmed(user_id, event_id) is not None:
            raise AlreadyRegistered()

        # B05: capienza
        capacity = int(event.get("capacity", 0))
        if self._repo.count_confirmed(event_id) >= capacity:
            raise EventFull()

        # B06: amount da event.price
        amount = float(event.get("price", 0))

        reg = Registration(
            user_id=user_id,
            event_id=event_id,
            amount=amount,
            status=RegistrationStatus.CONFIRMED,
        )
        self._repo.add(reg)
        return reg

    def get_registration(self, registration_id: str) -> Registration:
        reg = self._repo.get(registration_id)
        if reg is None:
            raise RegistrationNotFound(registration_id)
        return reg

    def list_registrations(self, page, page_size, user_id=None, event_id=None, status=None):
        return self._repo.list(
            page, page_size, user_id=user_id, event_id=event_id, status=status
        )

    def update_registration(self, registration_id: str, payload: Any) -> Registration:
        current = self._repo.get(registration_id)
        if current is None:
            raise RegistrationNotFound(registration_id)

        data = validate_patch(payload)
        new_status = RegistrationStatus(data["status"])

        # B07: unica transizione confirmed->cancelled (uguale = no-op)
        if new_status != current.status:
            if not (
                current.status == RegistrationStatus.CONFIRMED
                and new_status == RegistrationStatus.CANCELLED
            ):
                raise InvalidStatusTransition()

        updated = Registration(
            user_id=current.user_id,
            event_id=current.event_id,
            amount=current.amount,
            status=new_status,
            id=current.id,
            created_at=current.created_at,
            updated_at=now_iso(),
        )
        self._repo.update(updated)
        return updated

    def delete_registration(self, registration_id: str) -> None:
        if not self._repo.delete(registration_id):
            raise RegistrationNotFound(registration_id)

    def stats(self, event_id: str | None) -> dict[str, Any]:
        # B08: event_id obbligatorio
        if not event_id:
            raise ValidationError({"event_id": "is required"})

        event = self._events.get_event(event_id)
        if event is None:
            raise EventNotFound(event_id)

        capacity = int(event.get("capacity", 0))
        confirmed = self._repo.count_confirmed(event_id)
        return {
            "event_id": event_id,
            "capacity": capacity,
            "confirmed": confirmed,
            "available": capacity - confirmed,
        }
