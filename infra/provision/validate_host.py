"""Validação do host Raspberry Pi para o homelab.

Executa verificações rápidas:
- SO deve ser Debian ou Ubuntu.
- Pacotes críticos presentes (openssh-server, sudo, unattended-upgrades, ca-certificates, curl).
- SSH não aceita senha e root não faz login por senha.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable

SUPPORTED_OS = {"debian", "ubuntu"}
DEFAULT_PACKAGES = [
    "openssh-server",
    "sudo",
    "unattended-upgrades",
    "ca-certificates",
    "curl",
]


def read_os_release(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value.strip().strip('"')
    return data


def check_os(data: dict[str, str]) -> tuple[bool, str]:
    os_id = data.get("ID", "").lower()
    pretty = data.get("PRETTY_NAME", os_id or "desconhecido")
    if os_id in SUPPORTED_OS:
        return True, f"SO suportado: {pretty}"
    return False, f"SO não suportado: {pretty} (esperado: Debian ou Ubuntu)"


def _run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def check_packages_installed(
    packages: Iterable[str], runner: Callable[[list[str]], subprocess.CompletedProcess[str]] = _run_cmd
) -> list[str]:
    missing = []
    for pkg in packages:
        result = runner(["dpkg-query", "-W", "-f", "${Status}", pkg])
        if result.returncode != 0 or "install ok installed" not in result.stdout:
            missing.append(pkg)
    return missing


def collect_sshd_directives(config_path: Path, dropin_dir: Path) -> dict[str, str]:
    lines: list[str] = []
    if config_path.exists():
        lines.extend(config_path.read_text().splitlines())
    if dropin_dir.exists():
        for dropin in sorted(dropin_dir.glob("*.conf")):
            lines.extend(dropin.read_text().splitlines())
    directives: dict[str, str] = {}
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(maxsplit=1)
        if len(parts) != 2:
            continue
        key, value = parts
        directives[key.lower()] = value.strip()
    return directives


def check_ssh_hardening(directives: dict[str, str]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    password_auth = directives.get("passwordauthentication", "yes").lower()
    if password_auth != "no":
        issues.append("PasswordAuthentication deve estar em 'no'")
    root_login = directives.get("permitrootlogin", "yes").lower()
    if root_login == "yes":
        issues.append("PermitRootLogin deve estar desabilitado (prohibit-password ou no)")
    pubkey = directives.get("pubkeyauthentication", "yes").lower()
    if pubkey != "yes":
        issues.append("PubkeyAuthentication deve estar habilitado")
    return len(issues) == 0, issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida host Debian/Ubuntu para o homelab.")
    parser.add_argument("--os-release", default="/etc/os-release", help="Caminho do arquivo os-release para validar")
    parser.add_argument(
        "--sshd-config", default="/etc/ssh/sshd_config", help="Caminho do sshd_config base para validar"
    )
    parser.add_argument(
        "--sshd-config-dir",
        default="/etc/ssh/sshd_config.d",
        help="Diretório de drop-ins do sshd_config",
    )
    parser.add_argument(
        "--packages", nargs="*", default=DEFAULT_PACKAGES, help="Lista de pacotes obrigatórios a validar"
    )
    args = parser.parse_args()

    os_data = read_os_release(Path(args.os_release))
    ok_os, os_msg = check_os(os_data)
    if ok_os:
        print(f"[OK] {os_msg}")
    else:
        print(f"[ERRO] {os_msg}")

    missing = check_packages_installed(args.packages)
    if missing:
        print(f"[ERRO] Pacotes ausentes: {', '.join(missing)}")
    else:
        print("[OK] Pacotes obrigatórios instalados")

    directives = collect_sshd_directives(Path(args.sshd_config), Path(args.sshd_config_dir))
    ssh_ok, ssh_issues = check_ssh_hardening(directives)
    if ssh_ok:
        print("[OK] SSH configurado para recusar senha e usar somente chave")
    else:
        print("[ERRO] Falhas no hardening do SSH: " + "; ".join(ssh_issues))

    return 0 if ok_os and not missing and ssh_ok else 1


if __name__ == "__main__":
    sys.exit(main())
