"""Servizio di dominio del event-service.

Orchestra validazione, chiamata a user-service e persistenza, applicando le regole:

* B01 organizer esistente -> ReferenceNotFound (422 REFERENCE_NOT_FOUND)
* B02 organizer con role=organizer -> InvalidOrganizer (422 INVALID_ORGANIZER)
* B03 end_date >= start_date -> ValidationError (422)
* B04 transizioni di stato -> InvalidStatusTransition (422 INVALID_STATUS_TRANSITION)
* B05 dipendenza giù -> DependencyUnavailable (503)
* B06 filtri lista status/city
"""

from __future__ import annotations

from datetime import date
from typing import Any

from ..clients.user_client import DependencyUnavailable, UserClient
from ..repository.base import EventRepository
from .models import Event, EventStatus, now_iso
from .validation import ValidationError, validate_create, validate_update

# Transizioni di stato ammesse (REQ-EVT-B04).
_ALLOWED_TRANSITIONS = {
    EventStatus.DRAFT: {EventStatus.PUBLISHED, EventStatus.CANCELLED},
    EventStatus.PUBLISHED: {EventStatus.CANCELLED},
    EventStatus.CANCELLED: set(),
}


class EventNotFound(Exception):
    """Evento inesistente (-> 404)."""


class ReferenceNotFound(Exception):
    """organizer_id non esiste in user-service (-> 422 REFERENCE_NOT_FOUND)."""


class InvalidOrganizer(Exception):
    """L'utente non ha role=organizer (-> 422 INVALID_ORGANIZER)."""


class InvalidStatusTransition(Exception):
    """Transizione di stato non ammessa (-> 422 INVALID_STATUS_TRANSITION)."""


class EventService:
    def __init__(self, repository: EventRepository, user_client: UserClient) -> None:
        self._repo = repository
        self._users = user_client

    # --- helper regole -----------------------------------------------------
    def _validate_organizer(self, organizer_id: str) -> None:
        """B01/B02/B05: l'organizzatore deve esistere e avere role=organizer."""
        user = self._users.get_user(organizer_id)  # può sollevare DependencyUnavailable
        if user is None:
            raise ReferenceNotFound("organizer_id")
        if user.get("role") != "organizer":
            raise InvalidOrganizer()

    @staticmethod
    def _check_transition(current: EventStatus, new: EventStatus) -> None:
        """B04: valida la transizione (uguale = no-op ammesso)."""
        if new == current:
            return
        if new not in _ALLOWED_TRANSITIONS.get(current, set()):
            raise InvalidStatusTransition()

    # --- comandi -----------------------------------------------------------
    def create_event(self, payload: Any) -> Event:
        data = validate_create(payload)
        self._validate_organizer(data["organizer_id"])
        event = Event(
            title=data["title"],
            organizer_id=data["organizer_id"],
            venue=data["venue"],
            city=data["city"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            capacity=data["capacity"],
            price=data["price"],
            description=data["description"],
            status=EventStatus(data["status"]),
        )
        self._repo.add(event)
        return event

    def get_event(self, event_id: str) -> Event:
        event = self._repo.get(event_id)
        if event is None:
            raise EventNotFound(event_id)
        return event

    def list_events(self, page, page_size, status=None, city=None):
        return self._repo.list(page, page_size, status=status, city=city)

    def replace_event(self, event_id: str, payload: Any) -> Event:
        current = self._repo.get(event_id)
        if current is None:
            raise EventNotFound(event_id)
        data = validate_create(payload)
        self._validate_organizer(data["organizer_id"])
        new_status = EventStatus(data["status"])
        self._check_transition(current.status, new_status)
        updated = Event(
            title=data["title"],
            organizer_id=data["organizer_id"],
            venue=data["venue"],
            city=data["city"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            capacity=data["capacity"],
            price=data["price"],
            description=data["description"],
            status=new_status,
            id=current.id,
            created_at=current.created_at,
            updated_at=now_iso(),
        )
        self._repo.replace(updated)
        return updated

    def update_event(self, event_id: str, payload: Any) -> Event:
        current = self._repo.get(event_id)
        if current is None:
            raise EventNotFound(event_id)
        changes = validate_update(payload)

        # Coerenza date rispetto ai valori risultanti (PATCH parziale).
        start = changes.get("start_date", current.start_date)
        end = changes.get("end_date", current.end_date)
        if date.fromisoformat(end) < date.fromisoformat(start):
            raise ValidationError({"end_date": "must be >= start_date"})

        if "organizer_id" in changes:
            self._validate_organizer(changes["organizer_id"])

        new_status = (
            EventStatus(changes["status"]) if "status" in changes else current.status
        )
        if "status" in changes:
            self._check_transition(current.status, new_status)

        updated = Event(
            title=changes.get("title", current.title),
            organizer_id=changes.get("organizer_id", current.organizer_id),
            venue=changes.get("venue", current.venue),
            city=changes.get("city", current.city),
            start_date=start,
            end_date=end,
            capacity=changes.get("capacity", current.capacity),
            price=changes.get("price", current.price),
            description=changes["description"] if "description" in changes else current.description,
            status=new_status,
            id=current.id,
            created_at=current.created_at,
            updated_at=now_iso(),
        )
        self._repo.update(updated)
        return updated

    def delete_event(self, event_id: str) -> None:
        if not self._repo.delete(event_id):
            raise EventNotFound(event_id)
