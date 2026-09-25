"""Integration test propri di registration-service (§6.3).

Avvia user + event + registration reali su porte libere e verifica:
* 1 caso positivo   -> iscrizione a evento pubblicato (201, confirmed, amount=price);
* 1 riferimento inesistente -> user inesistente (422 REFERENCE_NOT_FOUND);
* 1 dipendenza spenta -> user/event non raggiungibili (503 DEPENDENCY_UNAVAILABLE).
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

SERVICES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
USER_DIR = os.path.join(SERVICES_DIR, "user-service")
EVENT_DIR = os.path.join(SERVICES_DIR, "event-service")
REG_DIR = os.path.join(SERVICES_DIR, "registration-service")


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
    return subprocess.Popen(
        [sys.executable, "-m", "app"], cwd=cwd, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


@pytest.fixture
def platform():
    up, ep, rp = _free_port(), _free_port(), _free_port()
    user_url = f"http://127.0.0.1:{up}"
    event_url = f"http://127.0.0.1:{ep}"
    reg_url = f"http://127.0.0.1:{rp}"
    procs = []
    try:
        p_user = _launch(USER_DIR, up, {}); procs.append(p_user); _wait_health(user_url, p_user)
        p_event = _launch(EVENT_DIR, ep, {"USER_SERVICE_URL": user_url}); procs.append(p_event); _wait_health(event_url, p_event)
        p_reg = _launch(REG_DIR, rp, {"USER_SERVICE_URL": user_url, "EVENT_SERVICE_URL": event_url})
        procs.append(p_reg); _wait_health(reg_url, p_reg)
        yield {"user_url": user_url, "event_url": event_url, "reg_url": reg_url}
    finally:
        for p in reversed(procs):
            with contextlib.suppress(Exception):
                p.terminate(); p.wait(timeout=5)


def _seed_published_event(user_url: str, event_url: str, capacity: int = 5, price: float = 149.0):
    """Crea organizzatore + partecipante + evento pubblicato; ritorna (user_id, event_id)."""
    org = requests.post(f"{user_url}/api/v1/users", json={
        "first_name": "Org", "last_name": "One", "email": f"org{_free_port()}@x.io", "role": "organizer"
    }, timeout=5).json()["id"]
    attendee = requests.post(f"{user_url}/api/v1/users", json={
        "first_name": "Att", "last_name": "Ee", "email": f"att{_free_port()}@x.io"
    }, timeout=5).json()["id"]
    ev = requests.post(f"{event_url}/api/v1/events", json={
        "title": "PyConf IT", "organizer_id": org, "venue": "Aud", "city": "Roma",
        "start_date": "2026-10-01", "end_date": "2026-10-02", "capacity": capacity, "price": price,
    }, timeout=5).json()["id"]
    # pubblica l'evento
    requests.patch(f"{event_url}/api/v1/events/{ev}", json={"status": "published"}, timeout=5)
    return attendee, ev


@pytest.mark.req("REQ-REG-F01")
def test_register_to_published_event(platform):
    user_id, event_id = _seed_published_event(platform["user_url"], platform["event_url"])
    r = requests.post(f"{platform['reg_url']}/api/v1/registrations",
                      json={"user_id": user_id, "event_id": event_id}, timeout=5)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "confirmed" and body["amount"] == 149.0


@pytest.mark.req("REQ-REG-B01")
def test_reference_not_found(platform):
    _, event_id = _seed_published_event(platform["user_url"], platform["event_url"])
    r = requests.post(f"{platform['reg_url']}/api/v1/registrations",
                      json={"user_id": "00000000-0000-4000-8000-000000000000", "event_id": event_id}, timeout=5)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "REFERENCE_NOT_FOUND"


@pytest.mark.req("REQ-REG-B09")
def test_dependency_unavailable():
    """registration con dipendenze verso porte chiuse -> 503."""
    rp = _free_port()
    reg_url = f"http://127.0.0.1:{rp}"
    dead = "http://127.0.0.1:1"
    proc = _launch(REG_DIR, rp, {"USER_SERVICE_URL": dead, "EVENT_SERVICE_URL": dead})
    try:
        _wait_health(reg_url, proc)
        r = requests.post(f"{reg_url}/api/v1/registrations",
                          json={"user_id": "11111111-1111-4111-8111-111111111111",
                                "event_id": "22222222-2222-4222-8222-222222222222"}, timeout=5)
        assert r.status_code == 503
        assert r.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    finally:
        with contextlib.suppress(Exception):
            proc.terminate(); proc.wait(timeout=5)
