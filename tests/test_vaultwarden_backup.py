import json
from pathlib import Path

from apps.vaultwarden.backup_vaultwarden import (
    build_rsync_command,
    parse_args,
    prune_snapshots,
    _write_status,
)


def test_build_rsync_command_accepts_link_dest_and_dry_run(tmp_path):
    source = tmp_path / "source"
    snapshot = tmp_path / "snapshot"
    link_dest = tmp_path / "prev"
    source.mkdir()
    snapshot.mkdir()
    link_dest.mkdir()

    cmd = build_rsync_command(source, snapshot, link_dest, dry_run=True)

    assert "--link-dest" in cmd
    assert "--dry-run" in cmd
    assert str(link_dest.resolve()) in cmd
    assert str(snapshot.resolve()) in cmd[-1]


def test_prune_snapshots_respects_retention(tmp_path):
    snapshots_dir = tmp_path / "snapshots"
    snapshots_dir.mkdir()

    names = [f"2024010{i}_000000" for i in range(1, 7)]
    for name in names:
        (snapshots_dir / name).mkdir()

    removed = prune_snapshots(snapshots_dir, keep=3)

    assert len(removed) == 3
    assert all(not path.exists() for path in removed)
    assert sorted(p.name for p in snapshots_dir.iterdir()) == names[-3:]


def test_write_status_persists_metadata(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    snapshot = target / "snapshots" / "20240101_010101"

    _write_status(target, True, "ok", snapshot)

    status_file = target / "last_run.json"
    data = json.loads(status_file.read_text())

    assert data["success"] is True
    assert data["message"] == "ok"
    assert data["snapshot"] == str(snapshot)


def test_parse_args_uses_env_defaults(monkeypatch, tmp_path):
    env_log = tmp_path / "vaultwarden.log"
    monkeypatch.setenv("VAULTWARDEN_BACKUP_LOG", str(env_log))

    args = parse_args(["--source", "/tmp/source", "--target", "/tmp/target", "--retention", "5"])

    assert Path(args.source) == Path("/tmp/source")
    assert Path(args.target) == Path("/tmp/target")
    assert args.retention == 5
    assert args.log_file == env_log
