"""Interfaccia astratta del repository eventi."""

from __future__ import annotations

import abc

from ..domain.models import Event


class EventRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, event: Event) -> None: ...

    @abc.abstractmethod
    def get(self, event_id: str) -> Event | None: ...

    @abc.abstractmethod
    def list(
        self,
        page: int,
        page_size: int,
        status: str | None = None,
        city: str | None = None,
    ) -> tuple[list[Event], int]: ...

    @abc.abstractmethod
    def replace(self, event: Event) -> None: ...

    @abc.abstractmethod
    def update(self, event: Event) -> None: ...

    @abc.abstractmethod
    def delete(self, event_id: str) -> bool: ...
