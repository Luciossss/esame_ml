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
