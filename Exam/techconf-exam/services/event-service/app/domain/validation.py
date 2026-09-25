"""Validazione degli input per event-service.

Rispecchia gli schemi ``EventCreate`` / ``EventUpdate`` del contratto OpenAPI, inclusa la
coerenza delle date (``end_date >= start_date``, REQ-EVT-B03).
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from .models import EventStatus

_ALLOWED_FIELDS = {
    "title", "description", "organizer_id", "venue", "city",
    "start_date", "end_date", "capacity", "price", "status",
}
_REQUIRED_FIELDS = {
    "title", "organizer_id", "venue", "city", "start_date", "end_date",
    "capacity", "price",
}
_READONLY_FIELDS = {"id", "created_at", "updated_at"}

_VALID_STATUS = {s.value for s in EventStatus}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ValidationError(Exception):
    def __init__(self, details: dict[str, str], message: str = "Validation failed") -> None:
        super().__init__(message)
        self.message = message
        self.details = details


def _parse_date(value: str) -> date | None:
    if not isinstance(value, str) or not _DATE_RE.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _check_common(details: dict[str, str], data: dict[str, Any]) -> None:
    if "title" in data:
        v = data["title"]
        if not isinstance(v, str) or not (3 <= len(v) <= 120):
            details["title"] = "must be a string of 3-120 characters"
    if "description" in data:
        v = data["description"]
        if v is not None and (not isinstance(v, str) or len(v) > 2000):
            details["description"] = "must be a string up to 2000 chars or null"
    if "organizer_id" in data and not isinstance(data["organizer_id"], str):
        details["organizer_id"] = "must be a string (uuid)"
    if "venue" in data:
        v = data["venue"]
        if not isinstance(v, str) or len(v) > 100:
            details["venue"] = "must be a string up to 100 chars"
    if "city" in data:
        v = data["city"]
        if not isinstance(v, str) or len(v) > 60:
            details["city"] = "must be a string up to 60 chars"
    if "capacity" in data:
        v = data["capacity"]
        if not isinstance(v, int) or isinstance(v, bool) or not (1 <= v <= 10000):
            details["capacity"] = "must be an integer between 1 and 10000"
    if "price" in data:
        v = data["price"]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
            details["price"] = "must be a number >= 0"
    if "status" in data and data["status"] not in _VALID_STATUS:
        details["status"] = f"must be one of {sorted(_VALID_STATUS)}"

    # date format
    for f in ("start_date", "end_date"):
        if f in data and _parse_date(data[f]) is None:
            details[f] = "must be a valid date YYYY-MM-DD"

    # coerenza date (solo se entrambe presenti e valide)
    if "start_date" in data and "end_date" in data:
        sd, ed = _parse_date(data["start_date"]), _parse_date(data["end_date"])
        if sd is not None and ed is not None and ed < sd:
            details["end_date"] = "must be >= start_date"


def _reject_unknown_and_readonly(details: dict[str, str], data: dict[str, Any]) -> None:
    for key in data:
        if key in _READONLY_FIELDS:
            details[key] = "is read-only and cannot be set by the client"
        elif key not in _ALLOWED_FIELDS:
            details[key] = "unknown field"


def validate_create(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    details: dict[str, str] = {}
    _reject_unknown_and_readonly(details, payload)
    for f in _REQUIRED_FIELDS:
        if f not in payload:
            details[f] = "is required"
    _check_common(details, payload)
    if details:
        raise ValidationError(details)

    return {
        "title": payload["title"],
        "description": payload.get("description"),
        "organizer_id": payload["organizer_id"],
        "venue": payload["venue"],
        "city": payload["city"],
        "start_date": payload["start_date"],
        "end_date": payload["end_date"],
        "capacity": payload["capacity"],
        "price": payload["price"],
        "status": payload.get("status", EventStatus.DRAFT.value),
    }


def validate_update(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    details: dict[str, str] = {}
    _reject_unknown_and_readonly(details, payload)
    _check_common(details, payload)
    if details:
        raise ValidationError(details)

    return {k: payload[k] for k in _ALLOWED_FIELDS if k in payload}
