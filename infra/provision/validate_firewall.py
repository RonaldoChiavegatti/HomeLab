"""Validação de firewall e exposição mínima de portas (US-012).

Executa varredura TCP local para garantir que apenas as portas esperadas
(geralmente expostas no roteador) estejam escutando. Útil para CI ou para
rodar manualmente após ajustar regras do UFW/iptables no host.
"""
from __future__ import annotations

import argparse
import socket
import subprocess
from typing import Iterable, Set

DEFAULT_ALLOWED_TCP = {22, 80, 443, 8080}
DEFAULT_REQUIRED_TCP = {80, 443, 8080}


class PortScanResult:
    def __init__(self, open_ports: Set[int]):
        self.open_ports = open_ports

    def unexpected(self, allowed: Iterable[int]) -> Set[int]:
        return self.open_ports.difference(set(allowed))

    def missing_required(self, required: Iterable[int]) -> Set[int]:
        required_set = set(required)
        return required_set.difference(self.open_ports)


def scan_tcp_ports(host: str, port_range: range) -> PortScanResult:
    open_ports: set[int] = set()
    for port in port_range:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            result = sock.connect_ex((host, port))
            if result == 0:
                open_ports.add(port)
    return PortScanResult(open_ports)


def list_udp_ports() -> set[int]:
    """Lista portas UDP em estado de listen usando ss/iptables (aproximação)."""
    try:
        output = subprocess.check_output(["ss", "-lun"], text=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return set()
    ports: set[int] = set()
    for line in output.splitlines():
        if not line or line.startswith("State"):
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        local_addr = parts[4]
        if ":" in local_addr:
            *_, port = local_addr.rsplit(":", 1)
            if port.isdigit():
                ports.add(int(port))
    return ports


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida exposição de portas do homelab.")
    parser.add_argument("--host", default="127.0.0.1", help="Host/IP para varredura TCP")
    parser.add_argument(
        "--max-port",
        type=int,
        default=1024,
        help="Maior porta TCP a varrer (inclusive)",
    )
    parser.add_argument(
        "--allowed-tcp",
        type=int,
        nargs="*",
        default=sorted(DEFAULT_ALLOWED_TCP),
        help="Portas TCP permitidas (serão ignoradas caso estejam abertas)",
    )
    parser.add_argument(
        "--required-tcp",
        type=int,
        nargs="*",
        default=sorted(DEFAULT_REQUIRED_TCP),
        help="Portas TCP que devem obrigatoriamente estar abertas",
    )
    parser.add_argument(
        "--allowed-udp",
        type=int,
        nargs="*",
        default=[51820],
        help="Portas UDP liberadas (WireGuard por padrão)",
    )
    args = parser.parse_args()

    scan = scan_tcp_ports(args.host, range(1, args.max_port + 1))
    unexpected_tcp = scan.unexpected(args.allowed_tcp)
    missing_tcp = scan.missing_required(args.required_tcp)

    udp_ports = list_udp_ports()
    unexpected_udp = udp_ports.difference(set(args.allowed_udp))

    status = 0
    if unexpected_tcp:
        print(f"[ERRO] Portas TCP não esperadas abertas: {sorted(unexpected_tcp)}")
        status = 1
    else:
        print(f"[OK] Nenhuma porta TCP além das permitidas ({sorted(args.allowed_tcp)}) está aberta")

    if missing_tcp:
        print(f"[ERRO] Portas TCP obrigatórias ausentes: {sorted(missing_tcp)}")
        status = 1
    else:
        print(f"[OK] Portas obrigatórias respondendo: {sorted(args.required_tcp)}")

    if unexpected_udp:
        print(f"[ERRO] Portas UDP não esperadas abertas: {sorted(unexpected_udp)}")
        status = 1
    else:
        print(f"[OK] Portas UDP dentro do esperado ({sorted(args.allowed_udp)})")

    return status


if __name__ == "__main__":
    raise SystemExit(main())
