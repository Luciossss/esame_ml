"""Client verso user-service.

Isola le chiamate HTTP a user-service e applica la mappatura degli errori di dipendenza
prevista dagli standard di piattaforma:

* ``404`` dal servizio chiamato  -> l'utente è considerato assente (``get_user`` -> None),
  che il dominio traduce in ``422 REFERENCE_NOT_FOUND``;
* timeout, connessione rifiutata o ``5xx`` -> ``DependencyUnavailable`` (``503``).

L'URL è letto dalla configurazione (``USER_SERVICE_URL``), mai hardcodato.
"""

from __future__ import annotations

from typing import Any

import requests

TIMEOUT_SECONDS = 2


class DependencyUnavailable(Exception):
    """user-service non raggiungibile o in errore (-> 503)."""

    def __init__(self, dependency: str = "user-service") -> None:
        super().__init__(f"Dependency unavailable: {dependency}")
        self.dependency = dependency


class UserClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        """Ritorna il dict dell'utente, o ``None`` se non esiste (404).

        Solleva ``DependencyUnavailable`` su timeout, connessione rifiutata o 5xx.
        """
        url = f"{self._base_url}/api/v1/users/{user_id}"
        try:
            resp = requests.get(url, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            raise DependencyUnavailable() from exc

        if resp.status_code == 200:
            try:
                return resp.json()
            except ValueError as exc:
                raise DependencyUnavailable() from exc
        if resp.status_code == 404:
            return None
        if resp.status_code >= 500:
            raise DependencyUnavailable()
        # Altri 4xx inattesi: trattali come dipendenza non affidabile.
        raise DependencyUnavailable()
