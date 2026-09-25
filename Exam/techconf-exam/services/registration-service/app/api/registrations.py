"""Rotte HTTP per la risorsa registrations (``/api/v1/registrations``).

Nota di routing: la rotta ``/stats`` è dichiarata prima di ``/<registration_id>`` così che
"stats" non venga interpretato come un id. Il ``PUT /<id>`` è esplicitamente 405.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import BadRequest

from ..clients.event_client import EventClient
from ..clients.user_client import UserClient
from ..domain.models import RegistrationStatus
from ..domain.service import RegistrationService
from ..domain.validation import ValidationError
from ..repository.factory import build_repository

bp = Blueprint("registrations", __name__)


def _service() -> RegistrationService:
    if "registration_service" not in current_app.extensions:
        config = current_app.config["APP_CONFIG"]
        repo = build_repository(config)
        users = UserClient(config.user_service_url)
        events = EventClient(config.event_service_url)
        current_app.extensions["registration_service"] = RegistrationService(repo, users, events)
    return current_app.extensions["registration_service"]


def _json_body() -> Any:
    data = request.get_json(silent=True)
    if data is None:
        raise BadRequest()
    return data


def _parse_pagination() -> tuple[int, int]:
    details: dict[str, str] = {}

    def _as_int(name: str, default: int) -> int:
        raw = request.args.get(name)
        if raw is None:
            return default
        try:
            return int(raw)
        except (TypeError, ValueError):
            details[name] = "must be an integer"
            return default

    page = _as_int("page", 1)
    page_size = _as_int("page_size", 20)
    if "page" not in details and page < 1:
        details["page"] = "must be >= 1"
    if "page_size" not in details and not (1 <= page_size <= 100):
        details["page_size"] = "must be between 1 and 100"
    if details:
        raise ValidationError(details)
    return page, page_size


@bp.post("/api/v1/registrations")
def create_registration():
    reg = _service().create_registration(_json_body())
    resp = jsonify(reg.to_dict())
    resp.status_code = 201
    resp.headers["Location"] = f"/api/v1/registrations/{reg.id}"
    return resp


@bp.get("/api/v1/registrations")
def list_registrations():
    page, page_size = _parse_pagination()
    status = request.args.get("status")
    if status is not None and status not in {
        item.value for item in RegistrationStatus
    }:
        raise ValidationError(
            {"status": "must be one of: confirmed, cancelled"}
        )
    items, total = _service().list_registrations(
        page,
        page_size,
        user_id=request.args.get("user_id"),
        event_id=request.args.get("event_id"),
        status=status,
    )
    return (
        jsonify(
            {
                "items": [r.to_dict() for r in items],
                "page": page,
                "page_size": page_size,
                "total": total,
            }
        ),
        200,
    )


# Deve precedere la rotta con <registration_id>.
@bp.get("/api/v1/registrations/stats")
def registration_stats():
    stats = _service().stats(request.args.get("event_id"))
    return jsonify(stats), 200


@bp.get("/api/v1/registrations/<registration_id>")
def get_registration(registration_id: str):
    reg = _service().get_registration(registration_id)
    return jsonify(reg.to_dict()), 200


@bp.patch("/api/v1/registrations/<registration_id>")
def update_registration(registration_id: str):
    reg = _service().update_registration(registration_id, _json_body())
    return jsonify(reg.to_dict()), 200


@bp.put("/api/v1/registrations/<registration_id>")
def put_not_allowed(registration_id: str):
    from werkzeug.exceptions import MethodNotAllowed

    raise MethodNotAllowed()


@bp.delete("/api/v1/registrations/<registration_id>")
def delete_registration(registration_id: str):
    _service().delete_registration(registration_id)
    return "", 204
