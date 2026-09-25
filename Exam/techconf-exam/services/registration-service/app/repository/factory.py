"""Factory che seleziona il backend di persistenza dalla configurazione."""

from __future__ import annotations

from ..config import Config
from .base import RegistrationRepository
from .memory import MemoryRegistrationRepository


def build_repository(config: Config) -> RegistrationRepository:
    backend = config.storage_backend
    if backend == "json":
        from .json_repo import JsonRegistrationRepository

        return JsonRegistrationRepository(config.data_dir)
    if backend == "sqlite":
        from .sqlite_repo import SqliteRegistrationRepository

        return SqliteRegistrationRepository(config.data_dir)
    return MemoryRegistrationRepository()
