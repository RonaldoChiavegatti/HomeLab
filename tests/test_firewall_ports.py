"""Validação de exposição de portas externas (US-012).

Sobe a stack de infraestrutura e confirma que somente as portas esperadas
estão abertas na interface local. Usa o validador de firewall para reduzir a
superfície de ataque exposta.
"""
from __future__ import annotations

import os
import subprocess
import time

from infra.provision.validate_firewall import DEFAULT_ALLOWED_TCP, DEFAULT_REQUIRED_TCP, scan_tcp_ports

ROOT = os.path.dirname(os.path.dirname(__file__))
COMPOSE_FILE = os.path.join(ROOT, "infra", "docker-compose.yml")


def _run(cmd: list[str]):
    subprocess.check_call(cmd, cwd=ROOT)


def setup_module(module):
    _run(["docker", "compose", "-f", COMPOSE_FILE, "up", "-d"])
    # Buffer curto para Traefik e whoami iniciarem
    time.sleep(5)


def teardown_module(module):
    _run(["docker", "compose", "-f", COMPOSE_FILE, "down"])


def test_only_expected_tcp_ports_are_open():
    allowed_tcp = set(DEFAULT_ALLOWED_TCP)
    required_tcp = set(DEFAULT_REQUIRED_TCP)

    scan = scan_tcp_ports("127.0.0.1", range(1, 1025))
    unexpected_tcp = scan.unexpected(allowed_tcp)
    missing_required = scan.missing_required(required_tcp)

    assert not unexpected_tcp, f"Portas TCP inesperadas abertas: {sorted(unexpected_tcp)}"
    assert not missing_required, f"Portas TCP obrigatórias ausentes: {sorted(missing_required)}"
