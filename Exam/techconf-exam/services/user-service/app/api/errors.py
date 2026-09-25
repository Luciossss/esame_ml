"""Gestione centralizzata degli errori HTTP.

Tutte le risposte di errore hanno la forma prevista dallo standard di piattaforma e dal
contratto::

    {"error": {"code": "UPPER_SNAKE", "message": "...", "details": {...}}}

Gli handler traducono le eccezioni di dominio negli status/code appropriati e gestiscono
gli errori HTTP standard (400 JSON malformato, 404, 405).
"""

from __future__ import annotations

from typing import Any

from flask import Flask, Response, jsonify
from werkzeug.exceptions import BadRequest, MethodNotAllowed, NotFound

from ..domain.service import EmailAlreadyExists, UserNotFound
from ..domain.validation import ValidationError


def error_response(
    status: int, code: str, message: str, details: dict[str, Any] | None = None
) -> tuple[Response, int]:
    """Costruisce una risposta di errore conforme al contratto."""
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


def register_error_handlers(app: Flask) -> None:
    """Registra gli handler sull'app Flask."""

    @app.errorhandler(ValidationError)
    def _handle_validation(err: ValidationError):
        return error_response(422, "VALIDATION_ERROR", err.message, err.details)

    @app.errorhandler(EmailAlreadyExists)
    def _handle_email_exists(err: EmailAlreadyExists):
        return error_response(
            409, "EMAIL_ALREADY_EXISTS", "Email already exists", {"email": err.email}
        )

    @app.errorhandler(UserNotFound)
    def _handle_not_found(_err: UserNotFound):
        return error_response(404, "NOT_FOUND", "Resource not found")

    @app.errorhandler(BadRequest)
    def _handle_bad_request(_err: BadRequest):
        # Include il caso di body JSON non parsabile.
        return error_response(400, "MALFORMED_JSON", "Malformed JSON body")

    @app.errorhandler(NotFound)
    def _handle_http_not_found(_err: NotFound):
        return error_response(404, "NOT_FOUND", "Resource not found")

    @app.errorhandler(MethodNotAllowed)
    def _handle_method_not_allowed(_err: MethodNotAllowed):
        return error_response(405, "METHOD_NOT_ALLOWED", "Method not allowed")
