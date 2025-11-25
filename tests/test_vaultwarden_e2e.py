"""Teste E2E do Vaultwarden (US-050).

Sobe Traefik + Vaultwarden e valida que a página de login responde em HTTPS
carregando um recurso estático com status 200.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

import requests
import urllib3

ROOT = Path(__file__).resolve().parents[1]
INFRA_COMPOSE = ROOT / "infra" / "docker-compose.yml"
VAULT_COMPOSE = ROOT / "apps" / "docker-compose.vaultwarden.yml"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _run(cmd: list[str]):
    subprocess.check_call(cmd, cwd=ROOT)


def setup_module(module):
    _run(["docker", "compose", "-f", str(INFRA_COMPOSE), "up", "-d"])
    _run(["docker", "compose", "-f", str(VAULT_COMPOSE), "up", "-d"])
    time.sleep(8)


def teardown_module(module):
    _run(["docker", "compose", "-f", str(VAULT_COMPOSE), "down"])
    _run(["docker", "compose", "-f", str(INFRA_COMPOSE), "down"])


def _wait_for_login(headers: dict[str, str], port: str, timeout: int = 60):
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        try:
            resp = requests.get(
                f"https://localhost:{port}", headers=headers, timeout=10, verify=False
            )
            if resp.status_code == 200 and "bitwarden" in resp.text.lower():
                return resp
            last_error = f"status {resp.status_code}"
        except Exception as exc:  # pragma: no cover - log de troubleshooting
            last_error = str(exc)
        time.sleep(3)
    raise AssertionError(f"Vaultwarden não respondeu com HTML: {last_error}")


def _extract_first_static_path(html: str) -> str:
    match = re.search(r'(?:src|href)="([^"]+\.(?:js|css))"', html)
    if not match:
        raise AssertionError("Não foi possível localizar recurso estático para validar")
    return match.group(1)


def test_vaultwarden_login_and_static_assets_available():
    domain = os.getenv("HOMELAB_DOMAIN", "example.local")
    https_port = os.getenv("TRAEFIK_HTTPS_PORT", "443")
    headers = {"Host": f"pw.{domain}"}

    resp = _wait_for_login(headers, https_port)
    asset_path = _extract_first_static_path(resp.text)

    asset_url = asset_path
    if asset_path.startswith("/"):
        asset_url = f"https://localhost:{https_port}{asset_path}"
    elif not asset_path.startswith("http"):
        asset_url = f"https://localhost:{https_port}/{asset_path}"

    asset_resp = requests.get(asset_url, headers=headers, timeout=10, verify=False)
    assert asset_resp.status_code == 200
    assert "text/html" not in asset_resp.headers.get("content-type", "").lower()
