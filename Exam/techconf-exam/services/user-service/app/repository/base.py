"""Interfaccia astratta del repository utenti.

Il dominio dipende solo da questa interfaccia, mai da un backend concreto: cambiare
``STORAGE_BACKEND`` non richiede modifiche alla logica di business (REQ-USR-P01).

Convenzioni comuni a tutte le implementazioni:

* ``email`` è confrontata/cercata sempre in minuscolo (il dominio normalizza prima di
  chiamare il repository), per garantire l'unicità case-insensitive (REQ-USR-B01/B02);
* ``list`` applica paginazione (1-based) e filtri opzionali, e ritorna ``(items, total)``
  dove ``total`` è il numero di elementi che soddisfano i filtri (prima della paginazione).
"""

from __future__ import annotations

import abc

from ..domain.models import User


class UserRepository(abc.ABC):
    """Contratto di persistenza per gli utenti."""

    @abc.abstractmethod
    def add(self, user: User) -> None:
        """Persiste un nuovo utente."""

    @abc.abstractmethod
    def get(self, user_id: str) -> User | None:
        """Ritorna l'utente con l'id dato, o ``None`` se non esiste."""

    @abc.abstractmethod
    def list(
        self,
        page: int,
        page_size: int,
        role: str | None = None,
        email: str | None = None,
    ) -> tuple[list[User], int]:
        """Ritorna ``(items, total)`` applicando filtri e paginazione.

        ``email`` è confrontata in minuscolo; ``role`` per valore esatto.
        """

    @abc.abstractmethod
    def replace(self, user: User) -> None:
        """Sostituisce integralmente un utente esistente (PUT)."""

    @abc.abstractmethod
    def update(self, user: User) -> None:
        """Aggiorna un utente esistente (PATCH); persiste lo stato passato."""

    @abc.abstractmethod
    def delete(self, user_id: str) -> bool:
        """Elimina l'utente; ritorna ``True`` se esisteva, ``False`` altrimenti."""

    @abc.abstractmethod
    def find_by_email(self, email_lower: str) -> User | None:
        """Ritorna l'utente con l'email (minuscola) data, per il controllo di unicità."""
