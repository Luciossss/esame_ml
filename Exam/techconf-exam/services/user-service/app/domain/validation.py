"""Validazione degli input per user-service.

Rispecchia gli schemi ``UserCreate`` / ``UserUpdate`` del contratto OpenAPI
(``contracts/openapi/user-service.yaml``):

* campi ammessi ed obbligatori;
* vincoli di lunghezza (``first_name``/``last_name`` 1-50, ``company`` max 100);
* ``email`` in formato valido;
* ``role`` fra i valori dell'enum;
* ``additionalProperties: false`` -> i campi extra sono rifiutati;
* i campi read-only (``id``, ``created_at``, ``updated_at``) non sono accettati dal client.

Gli errori sono raccolti in una ``ValidationError`` con il dettaglio per campo, così che
il livello HTTP possa produrre ``422 VALIDATION_ERROR`` con ``details``.
"""

from __future__ import annotations

import re
from typing import Any

from .models import Role

# Campi accettati in input.
_ALLOWED_FIELDS = {"first_name", "last_name", "email", "company", "role"}
_REQUIRED_FIELDS = {"first_name", "last_name", "email"}
_READONLY_FIELDS = {"id", "created_at", "updated_at"}

# Validazione email volutamente semplice ma robusta (una @, un dominio con un punto).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_VALID_ROLES = {r.value for r in Role}


class ValidationError(Exception):
    """Errore di validazione con dettaglio per campo."""

    def __init__(self, details: dict[str, str], message: str = "Validation failed") -> None:
        super().__init__(message)
        self.message = message
        self.details = details


def _check_string(
    details: dict[str, str], data: dict[str, Any], field: str, min_len: int, max_len: int
) -> None:
    value = data[field]
    if not isinstance(value, str):
        details[field] = "must be a string"
        return
    if len(value) < min_len:
        details[field] = f"must be at least {min_len} character(s)"
    elif len(value) > max_len:
        details[field] = f"must be at most {max_len} character(s)"


def _check_common(details: dict[str, str], data: dict[str, Any]) -> None:
    """Valida i campi presenti (usata sia in create sia in update)."""
    if "first_name" in data:
        _check_string(details, data, "first_name", 1, 50)
    if "last_name" in data:
        _check_string(details, data, "last_name", 1, 50)
    if "email" in data:
        email = data["email"]
        if not isinstance(email, str) or not _EMAIL_RE.match(email):
            details["email"] = "must be a valid email address"
    if "company" in data:
        company = data["company"]
        if company is not None:
            if not isinstance(company, str):
                details["company"] = "must be a string or null"
            elif len(company) > 100:
                details["company"] = "must be at most 100 character(s)"
    if "role" in data:
        role = data["role"]
        if role not in _VALID_ROLES:
            details["role"] = f"must be one of {sorted(_VALID_ROLES)}"


def _reject_unknown_and_readonly(details: dict[str, str], data: dict[str, Any]) -> None:
    for key in data:
        if key in _READONLY_FIELDS:
            details[key] = "is read-only and cannot be set by the client"
        elif key not in _ALLOWED_FIELDS:
            details[key] = "unknown field"


def validate_create(payload: Any) -> dict[str, Any]:
    """Valida un payload di creazione/sostituzione (POST, PUT).

    Ritorna un dict normalizzato con i valori (``role`` impostato a default se assente).
    Solleva ``ValidationError`` in caso di problemi.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    details: dict[str, str] = {}
    _reject_unknown_and_readonly(details, payload)

    for field in _REQUIRED_FIELDS:
        if field not in payload:
            details[field] = "is required"

    _check_common(details, payload)

    if details:
        raise ValidationError(details)

    return {
        "first_name": payload["first_name"],
        "last_name": payload["last_name"],
        "email": payload["email"],
        "company": payload.get("company"),
        "role": payload.get("role", Role.ATTENDEE.value),
    }


def validate_update(payload: Any) -> dict[str, Any]:
    """Valida un payload di modifica parziale (PATCH).

    Tutti i campi sono opzionali, ma quelli presenti devono rispettare i vincoli.
    Ritorna solo i campi effettivamente forniti. Solleva ``ValidationError`` se invalido.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    details: dict[str, str] = {}
    _reject_unknown_and_readonly(details, payload)
    _check_common(details, payload)

    if details:
        raise ValidationError(details)

    return {k: payload[k] for k in _ALLOWED_FIELDS if k in payload}
