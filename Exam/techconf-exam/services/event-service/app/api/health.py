"""Endpoint di health check."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    config = current_app.config["APP_CONFIG"]
    return jsonify({"status": "ok", "service": config.service_name}), 200
