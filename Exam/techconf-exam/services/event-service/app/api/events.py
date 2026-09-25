"""Rotte HTTP per la risorsa events (``/api/v1/events``)."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import BadRequest

from ..clients.user_client import UserClient
from ..domain.models import EventStatus
from ..domain.service import EventService
from ..domain.validation import ValidationError
from ..repository.factory import build_repository

bp = Blueprint("events", __name__)


def _service() -> EventService:
    if "event_service" not in current_app.extensions:
        config = current_app.config["APP_CONFIG"]
        repo = build_repository(config)
        client = UserClient(config.user_service_url)
        current_app.extensions["event_service"] = EventService(repo, client)
    return current_app.extensions["event_service"]


def _json_body() -> Any:
    data = request.get_json(silent=True)
    if data is None:
        raise BadRequest()
    return data


def _location(event_id: str) -> str:
    return f"/api/v1/events/{event_id}"


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


@bp.post("/api/v1/events")
def create_event():
    event = _service().create_event(_json_body())
    resp = jsonify(event.to_dict())
    resp.status_code = 201
    resp.headers["Location"] = _location(event.id)
    return resp


@bp.put("/api/v1/events/<event_id>")
def replace_event(event_id: str):
    event = _service().replace_event(event_id, _json_body())
    return jsonify(event.to_dict()), 200


@bp.patch("/api/v1/events/<event_id>")
def update_event(event_id: str):
    event = _service().update_event(event_id, _json_body())
    return jsonify(event.to_dict()), 200


@bp.delete("/api/v1/events/<event_id>")
def delete_event(event_id: str):
    _service().delete_event(event_id)
    return "", 204


@bp.get("/api/v1/events/<event_id>")
def get_event(event_id: str):
    event = _service().get_event(event_id)
    return jsonify(event.to_dict()), 200


@bp.get("/api/v1/events")
def list_events():
    page, page_size = _parse_pagination()
    status = request.args.get("status")
    if status is not None and status not in {item.value for item in EventStatus}:
        raise ValidationError(
            {"status": "must be one of: draft, published, cancelled"}
        )
    city = request.args.get("city")
    items, total = _service().list_events(page, page_size, status=status, city=city)
    return (
        jsonify(
            {
                "items": [e.to_dict() for e in items],
                "page": page,
                "page_size": page_size,
                "total": total,
            }
        ),
        200,
    )
