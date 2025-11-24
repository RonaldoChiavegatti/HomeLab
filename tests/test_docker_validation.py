"""Testes unitários do validador de Docker/Compose (US-002).

Usa runners fakes para evitar dependência de Docker real.
Garante que cada verificação responde corretamente a sucessos/falhas esperados.
"""
from __future__ import annotations

import subprocess
from types import SimpleNamespace

from infra.provision import validate_docker


def test_check_docker_cli_success():
    def runner(cmd, user):
        return subprocess.CompletedProcess(cmd, 0, stdout="24.0.6\n", stderr="")

    ok, msg = validate_docker.check_docker_cli(runner)
    assert ok
    assert "24.0.6" in msg


def test_check_compose_failure():
    def runner(cmd, user):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="missing plugin")

    ok, msg = validate_docker.check_compose(runner)
    assert not ok
    assert "missing plugin" in msg


def test_user_not_in_group(monkeypatch):
    monkeypatch.setattr(validate_docker.pwd, "getpwnam", lambda user: SimpleNamespace(pw_gid=1000))
    monkeypatch.setattr(validate_docker.grp, "getgrnam", lambda group: SimpleNamespace(gr_mem=[], gr_gid=2000))

    ok, msg = validate_docker.user_in_group("homelab")
    assert not ok
    assert "não está" in msg


def test_docker_ps_uses_target_user(monkeypatch):
    calls = []

    def runner(cmd, user):
        calls.append((cmd, user))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    ok, msg = validate_docker.check_docker_ps("homelab", runner)
    assert ok
    assert calls and calls[0][1] == "homelab"
    assert "ps executa" in msg


def test_hello_world_success():
    def runner(cmd, user):
        return subprocess.CompletedProcess(cmd, 0, stdout="Hello from Docker!\n", stderr="")

    ok, msg = validate_docker.run_hello_world("homelab", runner)
    assert ok
    assert "mensagem esperada" in msg
