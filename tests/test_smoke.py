"""
Testes de fumaça básicos para validar o esqueleto de rede e roteamento.
Executa docker compose da stack infra, checa Traefik e serviço whoami exposto via Host header.
"""
import os
import subprocess
import time

import requests

ROOT = os.path.dirname(os.path.dirname(__file__))
COMPOSE_FILE = os.path.join(ROOT, "infra", "docker-compose.yml")


def _run(cmd: list[str]):
    """Executa comando simples e levanta exceção se falhar."""
    subprocess.check_call(cmd, cwd=ROOT)


def setup_module(module):
    # Sobe a stack infra em background antes dos testes.
    _run(["docker", "compose", "-f", COMPOSE_FILE, "up", "-d"])
    # Pequena espera para containers inicializarem em hardware modesto.
    time.sleep(5)


def teardown_module(module):
    # Encerra stack infra após testes.
    _run(["docker", "compose", "-f", COMPOSE_FILE, "down"])


def test_traefik_dashboard_health():
    http_port = os.getenv("TRAEFIK_HTTP_PORT", "80")
    resp = requests.get(f"http://localhost:{http_port}/", timeout=5)
    assert resp.status_code == 404 or resp.status_code == 200


def test_whoami_route():
    domain = os.getenv("HOMELAB_DOMAIN", "example.local")
    http_port = os.getenv("TRAEFIK_HTTP_PORT", "80")
    headers = {"Host": f"whoami.{domain}"}
    resp = requests.get(f"http://localhost:{http_port}", headers=headers, timeout=5)
    assert resp.status_code == 200
    assert "Hostname" in resp.text or "whoami" in resp.text
