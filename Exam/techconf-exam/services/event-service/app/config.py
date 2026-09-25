"""Configurazione del servizio event-service.

Unico punto di lettura delle variabili d'ambiente.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

SERVICE_NAME = "event-service"
DEFAULT_PORT = 5002


@dataclass(frozen=True)
class Config:
    service_name: str = SERVICE_NAME
    port: int = DEFAULT_PORT
    storage_backend: str = "memory"
    data_dir: str = "./data"
    user_service_url: str = "http://localhost:5001"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Config":
        env = os.environ if env is None else env

        try:
            port = int(env.get("PORT", str(DEFAULT_PORT)))
        except (TypeError, ValueError):
            port = DEFAULT_PORT

        backend = (env.get("STORAGE_BACKEND") or "memory").strip().lower()
        if backend not in ("memory", "json", "sqlite"):
            backend = "memory"

        return cls(
            service_name=SERVICE_NAME,
            port=port,
            storage_backend=backend,
            data_dir=env.get("DATA_DIR") or "./data",
            user_service_url=(env.get("USER_SERVICE_URL") or "http://localhost:5001").rstrip("/"),
        )
