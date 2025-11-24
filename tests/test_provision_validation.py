"""Testes da validação do host (US-001).

Usa mocks para evitar alterações reais no host. Garante que:
- Apenas Debian/Ubuntu são aceitos.
- Pacotes ausentes são reportados corretamente.
- Configuração do SSH com senha é rejeitada.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from infra.provision import validate_host


def test_accepts_debian_os():
    os_data = {"ID": "debian", "PRETTY_NAME": "Debian GNU/Linux 12"}
    ok, msg = validate_host.check_os(os_data)
    assert ok
    assert "SO suportado" in msg


def test_rejects_non_supported_os():
    os_data = {"ID": "fedora", "PRETTY_NAME": "Fedora"}
    ok, msg = validate_host.check_os(os_data)
    assert not ok
    assert "não suportado" in msg


def test_missing_packages_are_reported(tmp_path: Path):
    installed = {"openssh-server", "sudo"}

    def fake_runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        pkg = cmd[-1]
        if pkg in installed:
            return subprocess.CompletedProcess(cmd, 0, stdout="install ok installed", stderr="")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="not installed")

    missing = validate_host.check_packages_installed(
        ["openssh-server", "sudo", "unattended-upgrades"], runner=fake_runner
    )
    assert missing == ["unattended-upgrades"]


def test_sshd_password_auth_is_detected(tmp_path: Path):
    sshd_config = tmp_path / "sshd_config"
    dropin_dir = tmp_path / "sshd_config.d"
    dropin_dir.mkdir()
    sshd_config.write_text("PasswordAuthentication yes\n")
    (dropin_dir / "010-hardening.conf").write_text("PermitRootLogin yes\n")

    directives = validate_host.collect_sshd_directives(sshd_config, dropin_dir)
    ssh_ok, issues = validate_host.check_ssh_hardening(directives)
    assert not ssh_ok
    assert any("PasswordAuthentication" in issue for issue in issues)
    assert any("PermitRootLogin" in issue for issue in issues)


def test_sshd_hardening_passes_when_secure(tmp_path: Path):
    sshd_config = tmp_path / "sshd_config"
    dropin_dir = tmp_path / "sshd_config.d"
    dropin_dir.mkdir()
    sshd_config.write_text("# base config\n")
    (dropin_dir / "010-hardening.conf").write_text(
        "PasswordAuthentication no\nPermitRootLogin prohibit-password\nPubkeyAuthentication yes\n"
    )

    directives = validate_host.collect_sshd_directives(sshd_config, dropin_dir)
    ssh_ok, issues = validate_host.check_ssh_hardening(directives)
    assert ssh_ok
    assert issues == []
