"""Modelli di dominio del registration-service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RegistrationStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

    def __str__(self) -> str:  # pragma: no cover
        return self.value


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Registration:
    user_id: str
    event_id: str
    amount: float
    status: RegistrationStatus = RegistrationStatus.CONFIRMED
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if not isinstance(self.status, RegistrationStatus):
            self.status = RegistrationStatus(self.status)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_id": self.event_id,
            "amount": round(float(self.amount), 2),
            "status": self.status.value if isinstance(self.status, RegistrationStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Registration":
        return cls(
            user_id=data["user_id"],
            event_id=data["event_id"],
            amount=float(data["amount"]),
            status=RegistrationStatus(data.get("status", RegistrationStatus.CONFIRMED.value)),
            id=data["id"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
