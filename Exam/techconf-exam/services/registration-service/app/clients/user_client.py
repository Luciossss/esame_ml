"""Client verso user-service."""

from __future__ import annotations

from typing import Any

import requests

from . import DependencyUnavailable

TIMEOUT_SECONDS = 2


class UserClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        """Ritorna l'utente o ``None`` se 404. Solleva DependencyUnavailable su errore."""
        url = f"{self._base_url}/api/v1/users/{user_id}"
        try:
            resp = requests.get(url, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            raise DependencyUnavailable("user-service") from exc

        if resp.status_code == 200:
            try:
                return resp.json()
            except ValueError as exc:
                raise DependencyUnavailable("user-service") from exc
        if resp.status_code == 404:
            return None
        raise DependencyUnavailable("user-service")
