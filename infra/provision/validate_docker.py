"""Validação do setup de Docker/Compose (US-002).

Verifica rapidamente se:
- docker CLI responde e o daemon está ativo.
- docker compose está disponível.
- Usuário informado pertence ao grupo docker (sem sudo para `docker ps`).
- hello-world roda e exibe a mensagem esperada.
"""
from __future__ import annotations

import argparse
import getpass
import grp
import pwd
import subprocess
import sys
from typing import Callable, Iterable, Sequence

CheckResult = tuple[bool, str]
Runner = Callable[[Sequence[str], str | None], subprocess.CompletedProcess[str]]


def _run_cmd(cmd: Sequence[str], user: str | None = None) -> subprocess.CompletedProcess[str]:
    final_cmd: list[str]
    if user:
        final_cmd = ["sudo", "-u", user, *cmd]
    else:
        final_cmd = list(cmd)
    return subprocess.run(final_cmd, check=False, capture_output=True, text=True)


def check_docker_cli(runner: Runner = _run_cmd) -> CheckResult:
    result = runner(["docker", "version", "--format", "{{.Client.Version}}"], None)
    if result.returncode == 0:
        return True, f"docker CLI OK (v{result.stdout.strip() or 'desconhecida'})"
    return False, f"docker CLI indisponível: {result.stderr.strip() or result.stdout.strip()}"


def check_compose(runner: Runner = _run_cmd) -> CheckResult:
    result = runner(["docker", "compose", "version"], None)
    if result.returncode == 0:
        return True, result.stdout.strip() or "docker compose version OK"
    return False, f"docker compose falhou: {result.stderr.strip() or result.stdout.strip()}"


def user_in_group(user: str, group: str = "docker") -> CheckResult:
    try:
        pwd.getpwnam(user)
    except KeyError:
        return False, f"Usuário {user} não encontrado"
    try:
        group_info = grp.getgrnam(group)
    except KeyError:
        return False, f"Grupo {group} não existe (instalação do Docker incompleta?)"
    members = set(group_info.gr_mem)
    if user in members:
        return True, f"Usuário {user} pertence ao grupo {group}"
    user_gid = pwd.getpwnam(user).pw_gid
    if group_info.gr_gid == user_gid:
        return True, f"Usuário {user} é owner do grupo {group}"
    return False, f"Usuário {user} não está no grupo {group}"


def check_docker_ps(user: str, runner: Runner = _run_cmd) -> CheckResult:
    result = runner(["docker", "ps"], user)
    if result.returncode == 0:
        return True, "docker ps executa sem sudo"
    return False, f"docker ps falhou para {user}: {result.stderr.strip() or result.stdout.strip()}"


def run_hello_world(user: str, runner: Runner = _run_cmd) -> CheckResult:
    result = runner(["docker", "run", "--rm", "hello-world"], user)
    if result.returncode == 0 and "Hello from Docker!" in result.stdout:
        return True, "hello-world retornou mensagem esperada"
    return False, f"hello-world falhou: {result.stderr.strip() or result.stdout.strip()}"


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida instalação do Docker/Compose para o homelab.")
    parser.add_argument(
        "--user",
        default=None,
        help="Usuário que deve executar docker sem sudo (default: HOMELAB_USER ou usuário atual)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    target_user = args.user or getenv_default_user()

    checks: list[CheckResult] = []
    ok, msg = check_docker_cli()
    print(prefix(ok) + msg)
    checks.append((ok, msg))

    ok, msg = check_compose()
    print(prefix(ok) + msg)
    checks.append((ok, msg))

    ok, msg = user_in_group(target_user)
    print(prefix(ok) + msg)
    checks.append((ok, msg))

    ok, msg = check_docker_ps(target_user)
    print(prefix(ok) + msg)
    checks.append((ok, msg))

    ok, msg = run_hello_world(target_user)
    print(prefix(ok) + msg)
    checks.append((ok, msg))

    return 0 if all(flag for flag, _ in checks) else 1


def prefix(ok: bool) -> str:
    return "[OK] " if ok else "[ERRO] "


def getenv_default_user() -> str:
    return getpass.getuser()


if __name__ == "__main__":
    sys.exit(main())
