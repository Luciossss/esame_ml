"""Modelli di dominio del event-service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"

    def __str__(self) -> str:  # pragma: no cover
        return self.value


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Event:
    title: str
    organizer_id: str
    venue: str
    city: str
    start_date: str
    end_date: str
    capacity: int
    price: float
    description: str | None = None
    status: EventStatus = EventStatus.DRAFT
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if not isinstance(self.status, EventStatus):
            self.status = EventStatus(self.status)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "organizer_id": self.organizer_id,
            "venue": self.venue,
            "city": self.city,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "capacity": self.capacity,
            "price": round(float(self.price), 2),
            "status": self.status.value if isinstance(self.status, EventStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        return cls(
            title=data["title"],
            organizer_id=data["organizer_id"],
            venue=data["venue"],
            city=data["city"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            capacity=int(data["capacity"]),
            price=float(data["price"]),
            description=data.get("description"),
            status=EventStatus(data.get("status", EventStatus.DRAFT.value)),
            id=data["id"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
