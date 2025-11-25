"""Validação da estrutura de dados em /srv/homelab (US-003).

Garante que:
- O SSD está montado no ponto informado (default: /srv) com filesystem esperado.
- A árvore de diretórios de dados existe para cada serviço.
- Opcionalmente cria diretórios ausentes para acelerar o bootstrap.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable, Sequence

# Diretórios esperados relativos ao caminho base (/srv/homelab por padrão)
EXPECTED_DIRECTORIES = [
    "traefik",
    "wireguard",
    "nextcloud/db",
    "nextcloud/redis",
    "nextcloud/data",
    "git",
    "vaultwarden/data",
    "media/jellyfin",
    "media/library",
    "media/transcodes",
    "homeassistant",
    "mail",
]

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def _run_cmd(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def detect_fstype(path: Path, runner: Runner = _run_cmd) -> str | None:
    """Retorna o filesystem do caminho fornecido usando `findmnt`.

    Retorna None se o comando falhar (ex.: caminho inexistente ou utilitário ausente).
    """

    result = runner(["findmnt", "-n", "-o", "FSTYPE", "-T", str(path)])
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def check_mountpoint(path: Path, expected_fs: Iterable[str], runner: Runner = _run_cmd) -> tuple[bool, str]:
    expected = {fs.lower() for fs in expected_fs}
    if not path.exists():
        return False, f"Ponto de montagem {path} não encontrado"
    fs_type = detect_fstype(path, runner)
    if fs_type is None:
        return False, f"Não foi possível detectar filesystem de {path} (verifique se findmnt está disponível)"
    fs_type_lower = fs_type.lower()
    if fs_type_lower not in expected:
        return False, f"Filesystem inesperado em {path}: {fs_type} (esperado: {', '.join(sorted(expected))})"
    return True, f"Ponto de montagem {path} ok com filesystem {fs_type}"


def list_missing_directories(base_path: Path, directories: Iterable[str]) -> list[Path]:
    missing: list[Path] = []
    for rel in directories:
        target = base_path / rel
        if not target.is_dir():
            missing.append(target)
    return missing


def create_directories(base_path: Path, directories: Iterable[str]) -> list[Path]:
    created: list[Path] = []
    for rel in directories:
        target = base_path / rel
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            created.append(target)
    return created


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida estrutura de dados em /srv/homelab")
    parser.add_argument("--mount", default="/srv", help="Ponto de montagem do SSD (default: /srv)")
    parser.add_argument(
        "--base", default="/srv/homelab", help="Diretório base para dados persistentes (default: /srv/homelab)"
    )
    parser.add_argument(
        "--fs", nargs="*", default=["ext4"], help="Sistemas de arquivos aceitos para o SSD (default: ext4)"
    )
    parser.add_argument(
        "--create-missing", action="store_true", help="Cria diretórios faltantes automaticamente antes de validar"
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    mount_path = Path(args.mount)
    base_path = Path(args.base)

    ok_mount, mount_msg = check_mountpoint(mount_path, args.fs)
    print(prefix(ok_mount) + mount_msg)

    if args.create_missing:
        created = create_directories(base_path, EXPECTED_DIRECTORIES)
        if created:
            for path in created:
                print(f"[INFO] Criado: {path}")
        else:
            print("[INFO] Nenhum diretório novo criado (todos já existiam)")

    missing = list_missing_directories(base_path, EXPECTED_DIRECTORIES)
    if missing:
        for path in missing:
            print(f"[FALTA] {path}")
    ok_dirs = len(missing) == 0
    dirs_msg = "Todos os diretórios de dados existem" if ok_dirs else "Diretórios de dados ausentes"
    print(prefix(ok_dirs) + dirs_msg)

    return 0 if ok_mount and ok_dirs else 1


def prefix(ok: bool) -> str:
    return "[OK] " if ok else "[ERRO] "


if __name__ == "__main__":
    sys.exit(main())
