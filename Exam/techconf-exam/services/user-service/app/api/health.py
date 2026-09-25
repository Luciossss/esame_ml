"""Endpoint di health check.

``GET /health`` -> ``200 {"status": "ok", "service": "user-service"}`` come richiesto
dallo standard di piattaforma. La suite di collaudo lo usa per attendere che il servizio
sia pronto prima di eseguire i test.
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    config = current_app.config["APP_CONFIG"]
    return jsonify({"status": "ok", "service": config.service_name}), 200
