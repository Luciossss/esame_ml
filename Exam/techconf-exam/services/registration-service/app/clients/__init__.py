"""Client HTTP verso gli altri microservizi."""

from __future__ import annotations


class DependencyUnavailable(Exception):
    """Una dipendenza non è raggiungibile o è in errore (-> 503)."""

    def __init__(self, dependency: str) -> None:
        super().__init__(f"Dependency unavailable: {dependency}")
        self.dependency = dependency
