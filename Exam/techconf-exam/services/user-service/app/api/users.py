"""Rotte HTTP per la risorsa users (``/api/v1/users``).

Il blueprint mappa le richieste al ``UserService`` di dominio; il parsing del JSON
gestisce il 400 su body malformato, mentre le eccezioni di dominio (validazione,
conflitto email, not found) sono tradotte dagli error handler centralizzati (T7).
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify, request

from ..domain.service import UserService
from ..domain.validation import ValidationError
from ..repository.factory import build_repository

bp = Blueprint("users", __name__)


def _service() -> UserService:
    """Costruisce il servizio con il repository selezionato dalla config.

    Il repository è mantenuto per l'intero processo (una sola istanza), così i dati
    persistono tra le richieste anche con il backend ``memory``.
    """
    if "user_service" not in current_app.extensions:
        config = current_app.config["APP_CONFIG"]
        repo = build_repository(config)
        current_app.extensions["user_service"] = UserService(repo)
    return current_app.extensions["user_service"]


def _json_body() -> Any:
    """Restituisce il body JSON; solleva 400 se assente o malformato."""
    # force=False + silent=True: non solleva l'eccezione HTML di Flask, la gestiamo noi.
    data = request.get_json(silent=True)
    if data is None:
        # Body vuoto o non-JSON -> 400 MALFORMED_JSON (via handler BadRequest).
        from werkzeug.exceptions import BadRequest

        raise BadRequest()
    return data


def _location(user_id: str) -> str:
    return f"/api/v1/users/{user_id}"


def _parse_pagination() -> tuple[int, int]:
    """Legge e valida ``page`` e ``page_size`` dalla query string.

    Default: ``page=1``, ``page_size=20``. ``page_size`` max 100. Valori non interi o
    fuori range -> ``ValidationError`` (422).
    """
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


@bp.post("/api/v1/users")
def create_user():
    payload = _json_body()
    user = _service().create_user(payload)
    resp = jsonify(user.to_dict())
    resp.status_code = 201
    resp.headers["Location"] = _location(user.id)
    return resp


@bp.put("/api/v1/users/<user_id>")
def replace_user(user_id: str):
    payload = _json_body()
    user = _service().replace_user(user_id, payload)
    return jsonify(user.to_dict()), 200


@bp.patch("/api/v1/users/<user_id>")
def update_user(user_id: str):
    payload = _json_body()
    user = _service().update_user(user_id, payload)
    return jsonify(user.to_dict()), 200


@bp.delete("/api/v1/users/<user_id>")
def delete_user(user_id: str):
    _service().delete_user(user_id)
    return "", 204


@bp.get("/api/v1/users/<user_id>")
def get_user(user_id: str):
    user = _service().get_user(user_id)
    return jsonify(user.to_dict()), 200


@bp.get("/api/v1/users")
def list_users():
    page, page_size = _parse_pagination()
    role = request.args.get("role")
    email = request.args.get("email")
    items, total = _service().list_users(page, page_size, role=role, email=email)
    return (
        jsonify(
            {
                "items": [u.to_dict() for u in items],
                "page": page,
                "page_size": page_size,
                "total": total,
            }
        ),
        200,
    )
