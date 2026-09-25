"""Application factory per event-service."""

from __future__ import annotations

from flask import Flask

from .config import Config


def create_app(config: Config | None = None) -> Flask:
    config = config or Config.from_env()

    app = Flask(__name__)
    app.config["APP_CONFIG"] = config

    from .api.errors import register_error_handlers
    from .api.events import bp as events_bp
    from .api.health import bp as health_bp

    register_error_handlers(app)
    app.register_blueprint(events_bp)
    app.register_blueprint(health_bp)

    return app
