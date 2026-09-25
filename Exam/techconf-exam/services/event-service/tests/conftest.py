"""Configurazione pytest condivisa per event-service."""

from __future__ import annotations

import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402

USER_URL = "http://user-svc:5001"


@pytest.fixture
def client():
    app = create_app(
        Config.from_env({"STORAGE_BACKEND": "memory", "USER_SERVICE_URL": USER_URL})
    )
    return app.test_client()
