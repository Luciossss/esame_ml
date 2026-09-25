"""Application factory per registration-service."""

from __future__ import annotations

from flask import Flask

from .config import Config


def create_app(config: Config | None = None) -> Flask:
    config = config or Config.from_env()

    app = Flask(__name__)
    app.config["APP_CONFIG"] = config

    from .api.errors import register_error_handlers
    from .api.health import bp as health_bp
    from .api.registrations import bp as registrations_bp

    register_error_handlers(app)
    app.register_blueprint(registrations_bp)
    app.register_blueprint(health_bp)

    return app
