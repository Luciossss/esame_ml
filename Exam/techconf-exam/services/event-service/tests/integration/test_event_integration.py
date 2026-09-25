"""Integration test propri di event-service (§6.3).

Avvia i servizi reali (user + event) come sottoprocessi su porte libere e verifica:
* 1 caso positivo   -> creazione con organizzatore valido (201);
* 1 riferimento inesistente -> organizer inesistente (422 REFERENCE_NOT_FOUND);
* 1 dipendenza spenta -> user-service non raggiungibile (503 DEPENDENCY_UNAVAILABLE).

I servizi sono avviati con ``python -m app`` leggendo ``PORT`` e ``*_SERVICE_URL``, esattamente
come fa la suite di collaudo.
"""

from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import sys
import time

import pytest
import requests

# .../services/event-service/tests/integration/<file> -> services dir è 3 livelli su.
SERVICES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
USER_DIR = os.path.join(SERVICES_DIR, "user-service")
EVENT_DIR = os.path.join(SERVICES_DIR, "event-service")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_health(base_url: str, proc: subprocess.Popen, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"process exited early ({proc.returncode})")
        with contextlib.suppress(requests.RequestException):
            if requests.get(base_url + "/health", timeout=1).status_code == 200:
                return
        time.sleep(0.2)
    raise RuntimeError(f"timeout waiting for {base_url}/health")


def _launch(cwd: str, port: int, env_extra: dict[str, str]) -> subprocess.Popen:
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["STORAGE_BACKEND"] = "memory"
    env.update(env_extra)
    proc = subprocess.Popen(
        [sys.executable, "-m", "app"],
        cwd=cwd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


@pytest.fixture
def platform():
    """Avvia user + event su porte libere; event punta a user via USER_SERVICE_URL."""
    user_port = _free_port()
    event_port = _free_port()
    user_url = f"http://127.0.0.1:{user_port}"
    event_url = f"http://127.0.0.1:{event_port}"

    procs = []
    try:
        p_user = _launch(USER_DIR, user_port, {})
        procs.append(p_user)
        _wait_health(user_url, p_user)

        p_event = _launch(EVENT_DIR, event_port, {"USER_SERVICE_URL": user_url})
        procs.append(p_event)
        _wait_health(event_url, p_event)

        yield {"user_url": user_url, "event_url": event_url}
    finally:
        for p in reversed(procs):
            with contextlib.suppress(Exception):
                p.terminate()
                p.wait(timeout=5)


def _make_organizer(user_url: str) -> str:
    r = requests.post(
        f"{user_url}/api/v1/users",
        json={"first_name": "Org", "last_name": "One", "email": f"org{_free_port()}@x.io", "role": "organizer"},
        timeout=5,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _event_payload(organizer_id: str) -> dict:
    return {
        "title": "PyConf IT", "organizer_id": organizer_id, "venue": "Aud",
        "city": "Roma", "start_date": "2026-10-01", "end_date": "2026-10-02",
        "capacity": 100, "price": 149.0,
    }


@pytest.mark.req("REQ-EVT-B01")
def test_create_with_valid_organizer(platform):
    org_id = _make_organizer(platform["user_url"])
    r = requests.post(
        f"{platform['event_url']}/api/v1/events", json=_event_payload(org_id), timeout=5
    )
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "draft"


@pytest.mark.req("REQ-EVT-B01")
def test_reference_not_found(platform):
    r = requests.post(
        f"{platform['event_url']}/api/v1/events",
        json=_event_payload("00000000-0000-4000-8000-000000000000"),
        timeout=5,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "REFERENCE_NOT_FOUND"


@pytest.mark.req("REQ-EVT-B05")
def test_dependency_unavailable():
    """event-service con USER_SERVICE_URL verso una porta chiusa -> 503."""
    event_port = _free_port()
    event_url = f"http://127.0.0.1:{event_port}"
    dead = "http://127.0.0.1:1"  # porta chiusa
    proc = _launch(EVENT_DIR, event_port, {"USER_SERVICE_URL": dead})
    try:
        _wait_health(event_url, proc)
        r = requests.post(
            f"{event_url}/api/v1/events",
            json=_event_payload("11111111-1111-4111-8111-111111111111"),
            timeout=5,
        )
        assert r.status_code == 503
        assert r.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    finally:
        with contextlib.suppress(Exception):
            proc.terminate()
            proc.wait(timeout=5)
