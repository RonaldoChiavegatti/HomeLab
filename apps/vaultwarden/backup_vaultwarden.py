"""Backup incremental do Vaultwarden usando rsync.

Mantém snapshots com hardlinks e registra status em JSON para conferência rápida.
Configuração via CLI ou variáveis de ambiente:
- VAULTWARDEN_BACKUP_SOURCE: diretório de dados (default: /srv/homelab/vaultwarden/data)
- VAULTWARDEN_BACKUP_TARGET: destino base dos snapshots (default: /srv/homelab/backups/vaultwarden)
- VAULTWARDEN_BACKUP_LOG: arquivo de log (default: <TARGET>/vaultwarden_backup.log)
- VAULTWARDEN_BACKUP_RETENTION: quantidade de snapshots a manter (default: 7)

Uso típico:
    python apps/vaultwarden/backup_vaultwarden.py --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Iterable, List, Optional

DEFAULT_SOURCE_PATH = Path("/srv/homelab/vaultwarden/data")
DEFAULT_TARGET_PATH = Path("/srv/homelab/backups/vaultwarden")
DEFAULT_RETENTION_VALUE = 7


def _env_path(var_name: str, fallback: Path) -> Path:
    return Path(os.getenv(var_name, str(fallback)))


def _timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def build_rsync_command(
    source: Path,
    snapshot_dir: Path,
    link_dest: Optional[Path],
    dry_run: bool = False,
) -> List[str]:
    """Monta comando rsync idempotente para snapshots com hardlinks."""

    cmd: List[str] = [
        "rsync",
        "-a",
        "--delete",
        "--numeric-ids",
        "--info=progress2",
    ]

    if link_dest:
        cmd.extend(["--link-dest", str(link_dest.resolve())])

    if dry_run:
        cmd.append("--dry-run")

    cmd.extend([f"{source.resolve()}/", f"{snapshot_dir.resolve()}/"])
    return cmd


def prune_snapshots(snapshots_dir: Path, keep: int) -> list[Path]:
    """Remove snapshots mais antigos que o limite desejado."""

    snapshots = sorted([p for p in snapshots_dir.iterdir() if p.is_dir()])
    if len(snapshots) <= keep:
        return []

    to_remove = snapshots[:-keep]
    for snap in to_remove:
        shutil.rmtree(snap, ignore_errors=True)
    return to_remove


def _write_status(target_dir: Path, success: bool, message: str, snapshot: Optional[Path]) -> None:
    status_file = target_dir / "last_run.json"
    payload = {
        "timestamp": dt.datetime.now().isoformat(),
        "success": success,
        "message": message,
        "snapshot": str(snapshot) if snapshot else None,
    }
    status_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _configure_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handlers = [logging.StreamHandler(sys.stdout), logging.FileHandler(log_file, encoding="utf-8")]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


def _ensure_dirs(target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    snapshots_dir = target / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    return snapshots_dir


def _latest_snapshot_link(target: Path) -> Optional[Path]:
    latest = target / "latest"
    if latest.is_symlink() and latest.exists():
        return latest.resolve()
    if latest.is_dir():
        return latest
    return None


def _update_latest_symlink(target: Path, snapshot_dir: Path) -> None:
    latest = target / "latest"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(snapshot_dir)


def run_backup(
    source: Path,
    target: Path,
    log_file: Path,
    retention: int,
    dry_run: bool = False,
) -> int:
    _configure_logging(log_file)
    snapshots_dir = _ensure_dirs(target)
    snapshot_dir = snapshots_dir / _timestamp()

    link_dest = _latest_snapshot_link(target)
    rsync_cmd = build_rsync_command(source, snapshot_dir, link_dest, dry_run=dry_run)

    logging.info("Iniciando backup do Vaultwarden")
    logging.info("Origem: %s", source)
    logging.info("Snapshot: %s", snapshot_dir)
    if link_dest:
        logging.info("Usando link-dest: %s", link_dest)

    snapshot_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(rsync_cmd, text=True, capture_output=True)
    if result.stdout:
        logging.info(result.stdout.strip())
    if result.stderr:
        logging.warning(result.stderr.strip())

    if result.returncode != 0:
        msg = f"Backup falhou com código {result.returncode}"
        logging.error(msg)
        _write_status(target, False, msg, snapshot_dir)
        return result.returncode

    _update_latest_symlink(target, snapshot_dir)
    removed = prune_snapshots(snapshots_dir, keep=retention)
    if removed:
        logging.info("Snapshots antigos removidos: %s", ", ".join(str(r.name) for r in removed))

    success_msg = "Backup concluído com sucesso"
    logging.info(success_msg)
    _write_status(target, True, success_msg, snapshot_dir)
    return 0


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    default_source = _env_path("VAULTWARDEN_BACKUP_SOURCE", DEFAULT_SOURCE_PATH)
    default_target = _env_path("VAULTWARDEN_BACKUP_TARGET", DEFAULT_TARGET_PATH)
    default_log = _env_path("VAULTWARDEN_BACKUP_LOG", default_target / "vaultwarden_backup.log")
    default_retention = int(os.getenv("VAULTWARDEN_BACKUP_RETENTION", str(DEFAULT_RETENTION_VALUE)))

    parser = argparse.ArgumentParser(description="Backup incremental do Vaultwarden com rsync")
    parser.add_argument("--source", default=default_source, type=Path, help="Diretório de dados do Vaultwarden")
    parser.add_argument("--target", default=default_target, type=Path, help="Destino base dos snapshots")
    parser.add_argument("--log-file", default=default_log, type=Path, help="Arquivo de log de execução")
    parser.add_argument(
        "--retention",
        default=default_retention,
        type=int,
        help="Quantidade de snapshots a manter (FIFO)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Apenas imprime comando rsync (não copia)")
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)

    if not args.source.exists():
        sys.stderr.write(f"Origem inexistente: {args.source}\n")
        return 2

    return run_backup(
        source=args.source,
        target=args.target,
        log_file=args.log_file,
        retention=args.retention,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
