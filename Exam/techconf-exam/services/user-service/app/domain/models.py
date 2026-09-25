"""Modelli di dominio del user-service.

Definisce l'enum ``Role``, la dataclass ``User`` e gli helper per generare
identificatori (UUID v4) e timestamp (ISO 8601 UTC), coerenti con gli standard di
piattaforma e con il contratto ``contracts/openapi/user-service.yaml``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Role(str, Enum):
    """Ruolo di un utente sulla piattaforma."""

    ATTENDEE = "attendee"
    SPEAKER = "speaker"
    ORGANIZER = "organizer"

    def __str__(self) -> str:  # pragma: no cover - conveniente per la serializzazione
        return self.value


def new_id() -> str:
    """Genera un identificatore UUID v4 come stringa."""
    return str(uuid.uuid4())


def now_iso() -> str:
    """Timestamp corrente in ISO 8601 UTC con suffisso 'Z' (es. 2026-10-15T09:30:00Z)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class User:
    """Utente della piattaforma TechConf.

    ``id``, ``created_at`` e ``updated_at`` sono valorizzati dal server (read-only lato
    client). ``email`` è sempre memorizzata in minuscolo (REQ-USR-B02).
    """

    first_name: str
    last_name: str
    email: str
    company: str | None = None
    role: Role = Role.ATTENDEE
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        # Normalizza sempre role a Role, indipendentemente da come arriva (str o enum).
        if not isinstance(self.role, Role):
            self.role = Role(self.role)

    def to_dict(self) -> dict[str, Any]:
        """Serializza l'utente secondo lo schema ``User`` del contratto."""
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "company": self.company,
            "role": self.role.value if isinstance(self.role, Role) else self.role,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "User":
        """Ricostruisce un ``User`` da un dict (usato dai backend json/sqlite)."""
        role = data.get("role", Role.ATTENDEE.value)
        return cls(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            company=data.get("company"),
            role=Role(role) if not isinstance(role, Role) else role,
            id=data["id"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
