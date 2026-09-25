"""Factory che seleziona il backend di persistenza dalla configurazione."""

from __future__ import annotations

from ..config import Config
from .base import EventRepository
from .memory import MemoryEventRepository


def build_repository(config: Config) -> EventRepository:
    backend = config.storage_backend
    if backend == "json":
        from .json_repo import JsonEventRepository

        return JsonEventRepository(config.data_dir)
    if backend == "sqlite":
        from .sqlite_repo import SqliteEventRepository

        return SqliteEventRepository(config.data_dir)
    return MemoryEventRepository()
