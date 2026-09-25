"""Validazione degli input per registration-service.

``RegistrationCreate`` accetta solo ``user_id`` ed ``event_id`` (``amount`` e ``status``
sono read-only). ``RegistrationPatch`` accetta solo ``status``.
"""

from __future__ import annotations

from typing import Any

from .models import RegistrationStatus

_CREATE_ALLOWED = {"user_id", "event_id"}
_CREATE_REQUIRED = {"user_id", "event_id"}
_READONLY = {"id", "amount", "status", "created_at", "updated_at"}

_VALID_STATUS = {s.value for s in RegistrationStatus}


class ValidationError(Exception):
    def __init__(self, details: dict[str, str], message: str = "Validation failed") -> None:
        super().__init__(message)
        self.message = message
        self.details = details


def validate_create(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    details: dict[str, str] = {}
    for key in payload:
        if key in _READONLY and key not in _CREATE_ALLOWED:
            details[key] = "is read-only and cannot be set by the client"
        elif key not in _CREATE_ALLOWED:
            details[key] = "unknown field"

    for f in _CREATE_REQUIRED:
        if f not in payload:
            details[f] = "is required"
        elif not isinstance(payload[f], str):
            details[f] = "must be a string (uuid)"

    if details:
        raise ValidationError(details)

    return {"user_id": payload["user_id"], "event_id": payload["event_id"]}


def validate_patch(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    details: dict[str, str] = {}
    for key in payload:
        if key != "status":
            details[key] = "unknown or read-only field"

    if "status" not in payload:
        details["status"] = "is required"
    elif payload["status"] not in _VALID_STATUS:
        details["status"] = f"must be one of {sorted(_VALID_STATUS)}"

    if details:
        raise ValidationError(details)

    return {"status": payload["status"]}
