"""Client verso event-service."""

from __future__ import annotations

from typing import Any

import requests

from . import DependencyUnavailable

TIMEOUT_SECONDS = 2


class EventClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        """Ritorna l'evento (con status/price/capacity) o ``None`` se 404.

        Solleva DependencyUnavailable su timeout, connessione rifiutata o 5xx.
        """
        url = f"{self._base_url}/api/v1/events/{event_id}"
        try:
            resp = requests.get(url, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            raise DependencyUnavailable("event-service") from exc

        if resp.status_code == 200:
            try:
                return resp.json()
            except ValueError as exc:
                raise DependencyUnavailable("event-service") from exc
        if resp.status_code == 404:
            return None
        raise DependencyUnavailable("event-service")
