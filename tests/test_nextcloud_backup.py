import json
from pathlib import Path

from core.nextcloud.backup_nextcloud import (
    build_rsync_command,
    parse_args,
    prune_snapshots,
    _write_status,
)


def test_build_rsync_command_includes_link_dest(tmp_path):
    source = tmp_path / "source"
    snapshot = tmp_path / "snapshot"
    link_dest = tmp_path / "previous"
    source.mkdir()
    snapshot.mkdir()
    link_dest.mkdir()

    cmd = build_rsync_command(source, snapshot, link_dest, dry_run=True)

    assert "--link-dest" in cmd
    assert "--dry-run" in cmd
    assert str(link_dest.resolve()) in cmd
    assert str(snapshot.resolve()) in cmd[-1]


def test_prune_snapshots_removes_old(tmp_path):
    snapshots_dir = tmp_path / "snapshots"
    snapshots_dir.mkdir()

    keep = 3
    names = ["20240101_000000", "20240102_000000", "20240103_000000", "20240104_000000", "20240105_000000"]
    for name in names:
        (snapshots_dir / name).mkdir()

    removed = prune_snapshots(snapshots_dir, keep=keep)

    assert len(removed) == len(names) - keep
    assert all(not path.exists() for path in removed)
    remaining = sorted([p.name for p in snapshots_dir.iterdir()])
    assert remaining == names[-keep:]


def test_write_status_creates_json(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    snapshot = target / "snapshots" / "20240101_010101"

    _write_status(target, True, "ok", snapshot)

    status_file = target / "last_run.json"
    data = json.loads(status_file.read_text())

    assert data["success"] is True
    assert data["message"] == "ok"
    assert data["snapshot"] == str(snapshot)


def test_parse_args_overrides_defaults(tmp_path, monkeypatch):
    env_log = tmp_path / "custom.log"
    monkeypatch.setenv("NEXTCLOUD_BACKUP_LOG", str(env_log))

    args = parse_args(["--source", "/tmp/source", "--target", "/tmp/target", "--retention", "10"])

    assert Path(args.source) == Path("/tmp/source")
    assert Path(args.target) == Path("/tmp/target")
    assert args.retention == 10
    assert args.log_file == env_log
