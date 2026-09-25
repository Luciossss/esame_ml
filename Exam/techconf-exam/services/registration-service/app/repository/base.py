"""Interfaccia astratta del repository iscrizioni."""

from __future__ import annotations

import abc

from ..domain.models import Registration


class RegistrationRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, registration: Registration) -> None: ...

    @abc.abstractmethod
    def get(self, registration_id: str) -> Registration | None: ...

    @abc.abstractmethod
    def list(
        self,
        page: int,
        page_size: int,
        user_id: str | None = None,
        event_id: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Registration], int]: ...

    @abc.abstractmethod
    def update(self, registration: Registration) -> None: ...

    @abc.abstractmethod
    def delete(self, registration_id: str) -> bool: ...

    @abc.abstractmethod
    def count_confirmed(self, event_id: str) -> int:
        """Numero di iscrizioni ``confirmed`` per l'evento (capienza/stats)."""

    @abc.abstractmethod
    def find_confirmed(self, user_id: str, event_id: str) -> Registration | None:
        """Iscrizione ``confirmed`` per la coppia (user, event), se esiste (unicità)."""
