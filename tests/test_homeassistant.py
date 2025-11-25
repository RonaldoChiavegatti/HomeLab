"""Testes de integração do Home Assistant (US-060).

Sobe infra + stack de automação e valida que o Home Assistant
responde tanto na porta 8123 (modo host) quanto via Traefik
usando o host `ha.<domínio>`.
"""
from __future__ import annotations

import os
import subprocess
import time
from typing import Any

import requests
import urllib3

ROOT = os.path.dirname(os.path.dirname(__file__))
INFRA_COMPOSE = os.path.join(ROOT, "infra", "docker-compose.yml")
HOMEASSISTANT_COMPOSE = os.path.join(ROOT, "apps", "docker-compose.homeassistant.yml")
HOMEASSISTANT_PORT = os.getenv("HOMEASSISTANT_PORT", "8123")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _run(cmd: list[str]):
    subprocess.check_call(cmd, cwd=ROOT)


def _wait_for_homeassistant(url: str, *, headers: dict[str, str] | None = None, verify: Any = True, timeout: int = 90):
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        try:
            resp = requests.get(url, headers=headers, timeout=10, verify=verify)
            if resp.status_code in (200, 401) and "home assistant" in resp.text.lower():
                return resp
            last_error = f"status {resp.status_code}"
        except Exception as exc:  # pragma: no cover - auxilia debug em CI
            last_error = str(exc)
        time.sleep(4)
    raise AssertionError(f"Home Assistant não respondeu de forma esperada: {last_error}")


def setup_module(module):
    _run(["docker", "compose", "-f", INFRA_COMPOSE, "up", "-d"])
    _run(["docker", "compose", "-f", HOMEASSISTANT_COMPOSE, "up", "-d"])


def teardown_module(module):
    _run(["docker", "compose", "-f", HOMEASSISTANT_COMPOSE, "down"])
    _run(["docker", "compose", "-f", INFRA_COMPOSE, "down"])


def test_homeassistant_listens_on_host_port():
    resp = _wait_for_homeassistant(f"http://localhost:{HOMEASSISTANT_PORT}")
    assert resp.status_code in (200, 401)
    assert "home assistant" in resp.text.lower()


def test_homeassistant_accessible_via_traefik():
    domain = os.getenv("HOMELAB_DOMAIN", "example.local")
    https_port = os.getenv("TRAEFIK_HTTPS_PORT", "443")
    headers = {"Host": f"ha.{domain}"}

    resp = _wait_for_homeassistant(
        f"https://localhost:{https_port}", headers=headers, verify=False
    )
    assert resp.status_code in (200, 401)
    assert "home assistant" in resp.text.lower()
