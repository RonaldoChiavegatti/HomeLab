"""Testes da validação da estrutura de dados em /srv/homelab (US-003)."""
from __future__ import annotations

import subprocess
from pathlib import Path

from infra.provision import validate_data_dirs


def test_detect_fstype_success(monkeypatch):
    def fake_runner(cmd):
        return subprocess.CompletedProcess(cmd, 0, stdout="ext4\n", stderr="")

    fs = validate_data_dirs.detect_fstype(Path("/srv"), runner=fake_runner)
    assert fs == "ext4"


def test_check_mountpoint_rejects_wrong_fs(monkeypatch):
    def fake_runner(cmd):
        return subprocess.CompletedProcess(cmd, 0, stdout="xfs\n", stderr="")

    ok, msg = validate_data_dirs.check_mountpoint(Path("/srv"), ["ext4"], runner=fake_runner)
    assert not ok
    assert "xfs" in msg


def test_list_missing_directories(tmp_path: Path):
    base = tmp_path / "homelab"
    base.mkdir()
    (base / "traefik").mkdir()
    missing = validate_data_dirs.list_missing_directories(base, ["traefik", "git", "nextcloud/data"])
    assert base / "git" in missing
    assert base / "nextcloud/data" in missing
    assert len(missing) == 2


def test_create_directories(tmp_path: Path):
    base = tmp_path / "homelab"
    created = validate_data_dirs.create_directories(base, ["vaultwarden", "media/jellyfin"])
    assert (base / "vaultwarden").is_dir()
    assert (base / "media/jellyfin").is_dir()
    assert set(created) == {base / "vaultwarden", base / "media/jellyfin"}


def test_main_reports_missing_dirs(tmp_path: Path, capsys):
    mount = tmp_path / "srv"
    mount.mkdir()

    def fake_runner(cmd):
        return subprocess.CompletedProcess(cmd, 0, stdout="ext4\n", stderr="")

    exit_code = validate_data_dirs.main(
        ["--mount", str(mount), "--base", str(mount / "homelab"), "--fs", "ext4"],
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Diretórios de dados ausentes" in captured.out
    assert "findmnt" not in captured.err
