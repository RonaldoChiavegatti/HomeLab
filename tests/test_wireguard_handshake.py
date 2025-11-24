"""Testes de integração do WireGuard (US-011).

Sobe a stack de infraestrutura com WireGuard e valida:
- Geração de peer default (peer1) e handshake ativo com cliente containerizado.
- Capacidade do cliente acessar um serviço interno (whoami) via túnel VPN.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(__file__))
COMPOSE_FILE = os.path.join(ROOT, "infra", "docker-compose.yml")
VPN_NETWORK = os.getenv("VPN_NETWORK", "vpn_net")
INTERNAL_NETWORK = os.getenv("INTERNAL_NETWORK", "internal_net")
WIREGUARD_CLIENT = "wireguard-ci-client"
PEER_CONFIG = Path("/srv/homelab/wireguard/peer1/peer1.conf")
PEER_DIR = PEER_CONFIG.parent


def _run(cmd: list[str]):
    subprocess.check_call(cmd, cwd=ROOT)


def setup_module(module):
    # Inicia stack completa para permitir roteamento até serviços internos.
    _run(["docker", "compose", "-f", COMPOSE_FILE, "up", "-d"])
    _wait_for_peer_config()
    _start_client()


def teardown_module(module):
    subprocess.run(["docker", "rm", "-f", WIREGUARD_CLIENT], cwd=ROOT, check=False)
    _run(["docker", "compose", "-f", COMPOSE_FILE, "down"])


def _wait_for_peer_config(timeout: int = 45):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if PEER_CONFIG.exists():
            return
        time.sleep(2)
    raise AssertionError("Configuração do peer1 não foi gerada pelo contêiner WireGuard")


def _start_client():
    subprocess.run(["docker", "rm", "-f", WIREGUARD_CLIENT], cwd=ROOT, check=False)
    # Usa a mesma imagem em modo cliente, apontando para o arquivo gerado pelo servidor.
    subprocess.check_call(
        [
            "docker",
            "run",
            "-d",
            "--name",
            WIREGUARD_CLIENT,
            "--cap-add",
            "NET_ADMIN",
            "--cap-add",
            "SYS_MODULE",
            "--device",
            "/dev/net/tun",
            "--network",
            VPN_NETWORK,
            "-e",
            "TZ=UTC",
            "-e",
            "WG_CONFIG_PATH=/config/peer1/peer1.conf",
            "-v",
            f"{PEER_DIR}:/config/peer1:ro",
            "lscr.io/linuxserver/wireguard:latest",
        ],
        cwd=ROOT,
    )
    time.sleep(3)


def _handshake_timestamp() -> int:
    try:
        output = subprocess.check_output(
            ["docker", "exec", "wireguard", "wg", "show", "wg0", "latest-handshakes"],
            cwd=ROOT,
            text=True,
        )
    except subprocess.CalledProcessError:
        return 0
    parts = [token.strip() for token in output.strip().split() if token.strip().isdigit()]
    return int(parts[-1]) if parts else 0


def test_wireguard_handshake_established():
    """Valida que o peer padrão realiza handshake com o servidor."""
    deadline = time.time() + 60
    timestamp = 0
    while time.time() < deadline:
        timestamp = _handshake_timestamp()
        if timestamp > 0:
            break
        time.sleep(3)
    assert timestamp > 0, "Peer não realizou handshake com o servidor WireGuard"


def _whoami_ip() -> str:
    inspect = subprocess.check_output(["docker", "inspect", "whoami"], cwd=ROOT, text=True)
    data = json.loads(inspect)[0]
    networks = data.get("NetworkSettings", {}).get("Networks", {})
    if INTERNAL_NETWORK in networks:
        return networks[INTERNAL_NETWORK]["IPAddress"]
    # fallback para qualquer IP disponível
    return next(iter(networks.values()))["IPAddress"]


def test_vpn_can_reach_internal_service():
    """Confere se o cliente VPN consegue chegar no serviço whoami via túnel."""
    whoami_ip = _whoami_ip()
    # Garante handshake ativo antes do teste de rota
    deadline = time.time() + 60
    while time.time() < deadline:
        if _handshake_timestamp() > 0:
            break
        time.sleep(2)
    else:
        raise AssertionError("Handshake não estabelecido antes do teste de rota")

    response = subprocess.check_output(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            f"container:{WIREGUARD_CLIENT}",
            "curlimages/curl:8.7.1",
            "-s",
            "-m",
            "5",
            f"http://{whoami_ip}",
        ],
        cwd=ROOT,
        text=True,
    )
    assert "Hostname" in response or "whoami" in response
