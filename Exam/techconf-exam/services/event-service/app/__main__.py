"""Entrypoint: `python -m app`. Legge PORT e avvia il server."""

from __future__ import annotations

from . import create_app
from .config import Config


def main() -> None:
    config = Config.from_env()
    app = create_app(config)
    app.run(host="0.0.0.0", port=config.port)


if __name__ == "__main__":
    main()
