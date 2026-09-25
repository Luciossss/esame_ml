"""Configurazione del servizio.

Unico punto in cui si leggono le variabili d'ambiente. Il resto del codice riceve un
oggetto ``Config`` e non accede mai direttamente a ``os.environ``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

SERVICE_NAME = "user-service"
DEFAULT_PORT = 5001


@dataclass(frozen=True)
class Config:
    """Configurazione runtime del servizio, derivata dall'ambiente."""

    service_name: str = SERVICE_NAME
    port: int = DEFAULT_PORT
    storage_backend: str = "memory"  # memory | json | sqlite
    data_dir: str = "./data"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Config":
        """Costruisce la configurazione leggendo l'ambiente (o un dict fornito)."""
        env = os.environ if env is None else env

        port_raw = env.get("PORT", str(DEFAULT_PORT))
        try:
            port = int(port_raw)
        except (TypeError, ValueError):
            port = DEFAULT_PORT

        backend = (env.get("STORAGE_BACKEND") or "memory").strip().lower()
        if backend not in ("memory", "json", "sqlite"):
            backend = "memory"

        data_dir = env.get("DATA_DIR") or "./data"

        return cls(
            service_name=SERVICE_NAME,
            port=port,
            storage_backend=backend,
            data_dir=data_dir,
        )
