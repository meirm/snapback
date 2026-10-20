"""Integration tests for project-local storage, exclusions and safe recovery.

These run the real ``rsync`` binary. The defect they cover — a full recovery
deleting ``.git``, gitignored directories and the tool's own configuration, and a
configured snapshot directory being snapshotted into itself — is invisible to
mocked subprocess calls, which is why it shipped.
"""

import sys
from pathlib import Path

import pytest

from snapback.backup import BackupManager
from snapback.cli import main
from snapback.config import Config
from snapback.recovery import RecoveryManager


def _project(tmp_path: Path, snapshots_dir: str = ".snapshots") -> Path:
    """Create a throwaway project with a repository, ignored content and config."""
    proj = tmp_path / "proj"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "app.txt").write_text("v1")
    (proj / "src" / "notes.txt").write_text("notes")
    (proj / "ignored").mkdir()
    (proj / "ignored" / "secret.txt").write_text("secret")
    (proj / ".git").mkdir()
    (proj / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (proj / ".gitignore").write_text("ignored/\n")
    (proj / ".snapshotrc").write_text(
        "# project-local configuration\n"
        "DIRS='.'\n"
        f"TARGETBASE='./{snapshots_dir}'\n"
        "RSYNC_PARAMS=''\n"
    )
    return proj


def test_recover_protects_excluded_paths_and_restores_deleted_file(tmp_path, monkeypatch):
    """A full recovery restores missing files and leaves excluded paths alone."""
    proj = _project(tmp_path)
    monkeypatch.chdir(proj)
    config = Config.load()
    BackupManager(config).hourly_backup()

    assert (proj / ".snapshots" / "hour-0" / "src" / "app.txt").read_text() == "v1"

    (proj / "src" / "app.txt").unlink()
    RecoveryManager(config).recover("hour-0")

    assert (proj / "src" / "app.txt").read_text() == "v1", "deleted file was not restored"
    assert (proj / ".git" / "HEAD").exists(), "recovery deleted the repository"
    assert (proj / "ignored" / "secret.txt").exists(), "recovery deleted ignored content"
    assert (proj / ".snapshotrc").exists(), "recovery deleted its own configuration"


def test_recover_restores_modified_file(tmp_path, monkeypatch):
    """A full recovery rolls a modified file back to the snapshot content."""
    proj = _project(tmp_path)
    monkeypatch.chdir(proj)
    config = Config.load()
    BackupManager(config).hourly_backup()

    (proj / "src" / "app.txt").write_text("v2-broken")
    RecoveryManager(config).recover("hour-0")

    assert (proj / "src" / "app.txt").read_text() == "v1"
    assert (proj / ".git" / "HEAD").exists()


def test_recover_keep_existing_never_deletes_or_overwrites(tmp_path, monkeypatch):
    """--keep-existing restores only what is missing."""
    proj = _project(tmp_path)
    monkeypatch.chdir(proj)
    config = Config.load()
    BackupManager(config).hourly_backup()

    (proj / "src" / "app.txt").write_text("v2-keep-me")
    (proj / "src" / "notes.txt").unlink()
    RecoveryManager(config).recover("hour-0", keep_existing=True)

    assert (proj / "src" / "app.txt").read_text() == "v2-keep-me", "overwrote an existing file"
    assert (proj / "src" / "notes.txt").read_text() == "notes", "did not restore the missing file"


def test_snapshot_dir_exclusion_follows_configuration(tmp_path, monkeypatch):
    """Pointing the project at another directory must not snapshot the snapshots."""
    proj = _project(tmp_path, snapshots_dir=".snapback")
    monkeypatch.chdir(proj)
    config = Config.load()
    BackupManager(config).hourly_backup()

    snap = proj / ".snapback" / "hour-0"
    assert (snap / "src" / "app.txt").exists(), "snapshot not written to the configured directory"
    assert not (snap / ".snapback").exists(), "snapshot directory snapshotted into itself"
    assert not (snap / ".snapshots").exists()


def test_recover_protects_custom_snapshot_directory(tmp_path, monkeypatch):
    """Recovery with a custom directory keeps the snapshots and the project intact."""
    proj = _project(tmp_path, snapshots_dir=".snapback")
    monkeypatch.chdir(proj)
    config = Config.load()
    BackupManager(config).hourly_backup()

    (proj / "src" / "app.txt").unlink()
    RecoveryManager(config).recover("hour-0")

    assert (proj / ".snapback" / "hour-0").is_dir(), "recovery deleted the snapshot directory"
    assert (proj / "src" / "app.txt").read_text() == "v1"
    assert (proj / ".git" / "HEAD").exists()


def test_local_excludes_follow_target_base(tmp_path, monkeypatch):
    """The exclusion list names the directory actually in use."""
    proj = _project(tmp_path, snapshots_dir=".snapback")
    monkeypatch.chdir(proj)
    config = Config.load()

    excludes = config.local_excludes
    assert "--exclude=.snapback" in excludes
    assert "--exclude=.snapshotrc" in excludes
    assert "--exclude=.git" in excludes
    assert "--filter=:- .gitignore" in excludes


def test_init_creates_custom_snapshot_directory(tmp_path, monkeypatch):
    """init --snapshots-dir writes the setting and ignores the directory it uses."""
    proj = tmp_path / "fresh"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "app.txt").write_text("x")
    monkeypatch.chdir(proj)
    monkeypatch.setattr(sys, "argv", ["snapback", "init", "--local", "--snapshots-dir", ".snapback"])

    assert main() == 0

    config_text = (proj / ".snapshotrc").read_text()
    assert "TARGETBASE='./.snapback'" in config_text, "config does not use the requested directory"
    gitignore = (proj / ".gitignore").read_text()
    assert ".snapback/" in gitignore, "the directory in use is not ignored"
    assert ".snapshotrc" in gitignore
    assert (proj / ".snapback" / "hour-0").is_dir(), "snapshot tree not created in the requested directory"


def test_init_rejects_absolute_or_escaping_directory(tmp_path, monkeypatch):
    """The snapshot directory must stay inside the project."""
    proj = tmp_path / "fresh2"
    proj.mkdir()
    monkeypatch.chdir(proj)

    for bad in ("/tmp/elsewhere", "../outside"):
        monkeypatch.setattr(
            sys, "argv", ["snapback", "init", "--local", "--snapshots-dir", bad]
        )
        assert main() == 1, f"{bad} should be refused"
        assert not (proj / ".snapshotrc").exists()
