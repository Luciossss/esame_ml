"""Factory che seleziona il backend di persistenza dalla configurazione.

I backend ``json`` e ``sqlite`` sono aggiunti nel task T5; qui viene già gestita la loro
selezione tramite import lazy, così ``memory`` funziona senza dipendere dagli altri.
"""

from __future__ import annotations

from ..config import Config
from .base import UserRepository
from .memory import MemoryUserRepository


def build_repository(config: Config) -> UserRepository:
    """Costruisce il repository adatto a ``config.storage_backend``."""
    backend = config.storage_backend

    if backend == "memory":
        return MemoryUserRepository()

    if backend == "json":
        from .json_repo import JsonUserRepository

        return JsonUserRepository(config.data_dir)

    if backend == "sqlite":
        from .sqlite_repo import SqliteUserRepository

        return SqliteUserRepository(config.data_dir)

    # from_env normalizza già a 'memory' per valori sconosciuti; fallback difensivo.
    return MemoryUserRepository()
