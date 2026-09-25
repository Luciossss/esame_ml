"""Application factory per user-service."""

from __future__ import annotations

from flask import Flask

from .config import Config


def create_app(config: Config | None = None) -> Flask:
    """Crea e configura l'app Flask.

    I blueprint delle rotte e gli error handler vengono registrati nei task successivi.
    """
    config = config or Config.from_env()

    app = Flask(__name__)
    app.config["APP_CONFIG"] = config

    from .api.errors import register_error_handlers

    register_error_handlers(app)

    # I blueprint (users, health) sono registrati nei task T8-T10.

    return app
