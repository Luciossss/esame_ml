"""Gestione centralizzata degli errori HTTP per event-service."""

from __future__ import annotations

from typing import Any

from flask import Flask, Response, jsonify
from werkzeug.exceptions import BadRequest, MethodNotAllowed, NotFound

from ..clients.user_client import DependencyUnavailable
from ..domain.service import (
    EventNotFound,
    InvalidOrganizer,
    InvalidStatusTransition,
    ReferenceNotFound,
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
    def _ref_not_found(err: ReferenceNotFound):
        return error_response(
            422, "REFERENCE_NOT_FOUND", "Referenced resource does not exist",
            {"field": str(err) or "organizer_id"},
        )

    @app.errorhandler(InvalidOrganizer)
    def _invalid_organizer(_err: InvalidOrganizer):
        return error_response(422, "INVALID_ORGANIZER", "User is not an organizer")

    @app.errorhandler(InvalidStatusTransition)
    def _invalid_transition(_err: InvalidStatusTransition):
        return error_response(
            422, "INVALID_STATUS_TRANSITION", "Status transition not allowed"
        )

    @app.errorhandler(EventNotFound)
    def _not_found(_err: EventNotFound):
        return error_response(404, "NOT_FOUND", "Resource not found")

    @app.errorhandler(DependencyUnavailable)
    def _dependency(_err: DependencyUnavailable):
        return error_response(503, "DEPENDENCY_UNAVAILABLE", "A dependency is unavailable")

    @app.errorhandler(BadRequest)
    def _bad_request(_err: BadRequest):
        return error_response(400, "MALFORMED_JSON", "Malformed JSON body")

    @app.errorhandler(NotFound)
    def _http_not_found(_err: NotFound):
        return error_response(404, "NOT_FOUND", "Resource not found")

    @app.errorhandler(MethodNotAllowed)
    def _method(_err: MethodNotAllowed):
        return error_response(405, "METHOD_NOT_ALLOWED", "Method not allowed")
