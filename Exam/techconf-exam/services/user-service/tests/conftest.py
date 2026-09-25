"""Configurazione pytest condivisa.

Aggiunge la root del repository template al ``sys.path`` così i test possono importare
``contracts.validator`` (il validatore di contratto fornito dal docente), e fornisce una
fixture ``client`` con un'app in backend ``memory``.
"""

from __future__ import annotations

import os
import sys

import pytest

# services/user-service/tests -> risali fino alla root del template (contiene contracts/).
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402


@pytest.fixture
def client():
    app = create_app(Config.from_env({"STORAGE_BACKEND": "memory"}))
    return app.test_client()
