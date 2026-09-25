"""Gestione centralizzata degli errori HTTP per registration-service."""

from __future__ import annotations

from typing import Any

from flask import Flask, Response, jsonify
from werkzeug.exceptions import BadRequest, MethodNotAllowed, NotFound

from ..clients import DependencyUnavailable
from ..domain.service import (
    AlreadyRegistered,
    EventFull,
    EventNotFound,
    EventNotOpen,
    InvalidStatusTransition,
    ReferenceNotFound,
    RegistrationNotFound,
)
from ..domain.validation import ValidationError


def error_response(
    status: int, code: str, message: str, details: dict[str, Any] | None = None
) -> tuple[Response, int]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ValidationError)
    def _validation(err: ValidationError):
        return error_response(422, "VALIDATION_ERROR", err.message, err.details)

    @app.errorhandler(ReferenceNotFound)
    def _ref(err: ReferenceNotFound):
        return error_response(
            422, "REFERENCE_NOT_FOUND", "Referenced resource does not exist",
            {"field": err.field},
        )

    @app.errorhandler(EventNotOpen)
    def _not_open(_err: EventNotOpen):
        return error_response(422, "EVENT_NOT_OPEN", "Event is not open for registration")

    @app.errorhandler(InvalidStatusTransition)
    def _transition(_err: InvalidStatusTransition):
        return error_response(422, "INVALID_STATUS_TRANSITION", "Status transition not allowed")

    @app.errorhandler(AlreadyRegistered)
    def _already(_err: AlreadyRegistered):
        return error_response(409, "ALREADY_REGISTERED", "User already registered for this event")

    @app.errorhandler(EventFull)
    def _full(_err: EventFull):
        return error_response(409, "EVENT_FULL", "Event capacity reached")

    @app.errorhandler(RegistrationNotFound)
    def _reg_nf(_err: RegistrationNotFound):
        return error_response(404, "NOT_FOUND", "Resource not found")

    @app.errorhandler(EventNotFound)
    def _evt_nf(_err: EventNotFound):
        return error_response(404, "NOT_FOUND", "Event not found")

    @app.errorhandler(DependencyUnavailable)
    def _dep(_err: DependencyUnavailable):
        return error_response(503, "DEPENDENCY_UNAVAILABLE", "A dependency is unavailable")

    @app.errorhandler(BadRequest)
    def _bad(_err: BadRequest):
        return error_response(400, "MALFORMED_JSON", "Malformed JSON body")

    @app.errorhandler(NotFound)
    def _http_nf(_err: NotFound):
        return error_response(404, "NOT_FOUND", "Resource not found")

    @app.errorhandler(MethodNotAllowed)
    def _method(_err: MethodNotAllowed):
        return error_response(405, "METHOD_NOT_ALLOWED", "Method not allowed")
