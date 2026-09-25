"""Entrypoint del servizio: `python -m app`.

Legge la porta da PORT (via Config) e avvia il server sulla porta richiesta.
"""

from __future__ import annotations

from . import create_app
from .config import Config


def main() -> None:
    config = Config.from_env()
    app = create_app(config)
    app.run(host="0.0.0.0", port=config.port)


if __name__ == "__main__":
    main()
