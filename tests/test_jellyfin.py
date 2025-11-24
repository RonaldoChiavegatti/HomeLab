"""Testes de integração do Jellyfin (US-030).

Sobe a stack de infraestrutura + mídia e valida que a página inicial do Jellyfin
responde via Traefik com HTML válido (HTTPS/staging por padrão).
"""
from __future__ import annotations

import os
import subprocess
import time

import requests
import urllib3

ROOT = os.path.dirname(os.path.dirname(__file__))
INFRA_COMPOSE = os.path.join(ROOT, "infra", "docker-compose.yml")
MEDIA_COMPOSE = os.path.join(ROOT, "apps", "docker-compose.media.yml")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _run(cmd: list[str]):
    """Executa comandos docker compose na raiz do repo."""
    subprocess.check_call(cmd, cwd=ROOT)


def setup_module(module):
    # Sobe Traefik e redes antes do stack de mídia para evitar problemas de dependência.
    _run(["docker", "compose", "-f", INFRA_COMPOSE, "up", "-d"])
    _run(["docker", "compose", "-f", MEDIA_COMPOSE, "up", "-d"])
    time.sleep(8)


def teardown_module(module):
    _run(["docker", "compose", "-f", MEDIA_COMPOSE, "down"])
    _run(["docker", "compose", "-f", INFRA_COMPOSE, "down"])


def _wait_for_homepage(headers: dict[str, str], port: str, timeout: int = 60):
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        try:
            resp = requests.get(
                f"https://localhost:{port}", headers=headers, timeout=10, verify=False
            )
            if resp.status_code == 200 and "<html" in resp.text.lower():
                return resp
            last_error = f"status {resp.status_code}"
        except Exception as exc:  # pragma: no cover - ajuda a depurar em CI
            last_error = str(exc)
        time.sleep(3)
    raise AssertionError(f"Jellyfin não respondeu com HTML: {last_error}")


def test_jellyfin_homepage_served_over_https():
    domain = os.getenv("HOMELAB_DOMAIN", "example.local")
    https_port = os.getenv("TRAEFIK_HTTPS_PORT", "443")
    headers = {"Host": f"media.{domain}"}

    resp = _wait_for_homepage(headers, https_port)
    assert "text/html" in resp.headers.get("content-type", "").lower()
    assert "jellyfin" in resp.text.lower()
