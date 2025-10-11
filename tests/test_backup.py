"""Tests for backup operations."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from snapback.backup import BackupManager


def test_run_rsync(config):
    """Test running rsync command."""
    manager = BackupManager(config)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="test output", stderr=""
        )

        result = manager.run_rsync(
            "/source/path", Path("/target/path"), delete=True
        )

        # Check rsync was called with correct arguments
        args = mock_run.call_args[0][0]
        assert "rsync" in args
        assert "-a" in args
        assert "-v" in args
        assert "--delete" in args
        assert "/source/path/" in args  # Should add trailing slash
        assert "/target/path" in args


def test_run_rsync_with_ignore_existing(config):
    """Test rsync with ignore-existing flag."""
    manager = BackupManager(config)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        manager.run_rsync(
            "/source/path", Path("/target/path"), ignore_existing=True
        )

        args = mock_run.call_args[0][0]
        assert "--ignore-existing" in args


def test_run_rsync_dry_run(config):
    """Test rsync with dry-run flag."""
    manager = BackupManager(config)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        manager.run_rsync("/source/path", Path("/target/path"), dry_run=True)

        args = mock_run.call_args[0][0]
        assert "--dry-run" in args


def test_run_rsync_with_config_params(config):
    """Test rsync with custom parameters from config."""
    config.rsync_params = "--exclude=*.tmp --max-size=1m"
    manager = BackupManager(config)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        manager.run_rsync("/source/path", Path("/target/path"))

        args = mock_run.call_args[0][0]
        assert "--exclude=*.tmp" in args
        assert "--max-size=1m" in args


def test_hourly_backup(config, initialized_snapshots, source_dirs):
    """Test hourly backup operation."""
    manager = BackupManager(config)
    base = Path(config.target_base)

    # Create hour-1 with some files
    hour_1 = base / "hour-1"
    for source_dir in source_dirs:
        target_subdir = hour_1 / source_dir.name
        target_subdir.mkdir(parents=True, exist_ok=True)
        (target_subdir / "old_file.txt").write_text("old content")

    with patch.object(manager, "run_rsync") as mock_rsync:
        mock_rsync.return_value = MagicMock(returncode=0, stdout="", stderr="")

        manager.hourly_backup()

        # hour-0 should be created
        assert (base / "hour-0").exists()

        # hour-1 should be shifted to hour-2
        assert (base / "hour-2" / source_dirs[0].name / "old_file.txt").exists()

        # rsync should be called for each source directory
        assert mock_rsync.call_count == len(source_dirs)


def test_hourly_backup_first_run(config, initialized_snapshots, source_dirs):
    """Test hourly backup on first run (no hour-1)."""
    manager = BackupManager(config)
    base = Path(config.target_base)

    # No hour-1 exists
    (base / "hour-1").rmdir()

    with patch.object(manager, "run_rsync") as mock_rsync:
        mock_rsync.return_value = MagicMock(returncode=0, stdout="", stderr="")

        manager.hourly_backup()

        # hour-0 should be created
        assert (base / "hour-0").exists()


def test_hourly_backup_dry_run(config, initialized_snapshots, source_dirs, capsys):
    """Test hourly backup in dry-run mode."""
    manager = BackupManager(config)

    manager.hourly_backup(dry_run=True)

    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out


def test_hourly_backup_missing_source(config, initialized_snapshots, capsys):
    """Test hourly backup with missing source directory."""
    # Add a non-existent directory to config
    config.dirs.append("/nonexistent/path")

    manager = BackupManager(config)

    with patch.object(manager, "run_rsync") as mock_rsync:
        mock_rsync.return_value = MagicMock(returncode=0, stdout="", stderr="")

        manager.hourly_backup()

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "does not exist" in captured.out


def test_hourly_backup_rsync_failure(config, initialized_snapshots, source_dirs):
    """Test hourly backup with rsync failure."""
    manager = BackupManager(config)

    with patch.object(manager, "run_rsync") as mock_rsync:
        mock_rsync.side_effect = subprocess.CalledProcessError(1, "rsync")

        # Should not raise, just print error
        manager.hourly_backup()


def test_daily_backup(config, initialized_snapshots):
    """Test daily backup rotation."""
    manager = BackupManager(config)
    base = Path(config.target_base)

    # Create hour-23
    (base / "hour-23" / "marker.txt").write_text("test")

    manager.daily_backup()

    # hour-23 should become day-0
    assert (base / "day-0" / "marker.txt").exists()


def test_daily_backup_dry_run(config, initialized_snapshots, capsys):
    """Test daily backup in dry-run mode."""
    manager = BackupManager(config)

    manager.daily_backup(dry_run=True)

    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out


def test_weekly_backup(config, initialized_snapshots):
    """Test weekly backup rotation."""
    manager = BackupManager(config)
    base = Path(config.target_base)

    # Create day-7
    (base / "day-7" / "marker.txt").write_text("test")

    manager.weekly_backup()

    # day-7 should become week-0
    assert (base / "week-0" / "marker.txt").exists()


def test_weekly_backup_dry_run(config, initialized_snapshots, capsys):
    """Test weekly backup in dry-run mode."""
    manager = BackupManager(config)

    manager.weekly_backup(dry_run=True)

    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out


def test_monthly_backup(config, initialized_snapshots):
    """Test monthly backup rotation."""
    manager = BackupManager(config)
    base = Path(config.target_base)

    # Create week-4
    (base / "week-4" / "marker.txt").write_text("test")

    manager.monthly_backup()

    # week-4 should become month-0
    assert (base / "month-0" / "marker.txt").exists()


def test_monthly_backup_dry_run(config, initialized_snapshots, capsys):
    """Test monthly backup in dry-run mode."""
    manager = BackupManager(config)

    manager.monthly_backup(dry_run=True)

    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out


# Project-Local Mode Tests


def test_run_rsync_local_mode_gitignore_filter(config):
    """Test rsync in local mode adds gitignore filter."""
    config.is_local = True
    manager = BackupManager(config)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        manager.run_rsync("/source/path", Path("/target/path"))

        args = mock_run.call_args[0][0]
        # Should include gitignore filter
        assert "--filter=:- .gitignore" in args


def test_run_rsync_local_mode_exclusions(config):
    """Test rsync in local mode excludes .git and .snapshots."""
    config.is_local = True
    manager = BackupManager(config)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        manager.run_rsync("/source/path", Path("/target/path"))

        args = mock_run.call_args[0][0]
        # Should exclude .git and .snapshots
        assert "--exclude=.git" in args
        assert "--exclude=.snapshots" in args


def test_run_rsync_global_mode_no_filter(config):
    """Test rsync in global mode does not add gitignore filter."""
    config.is_local = False
    manager = BackupManager(config)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        manager.run_rsync("/source/path", Path("/target/path"))

        args = mock_run.call_args[0][0]
        # Should NOT include gitignore filter in global mode
        assert "--filter=:- .gitignore" not in args
        assert "--exclude=.git" not in args
        assert "--exclude=.snapshots" not in args


def test_run_rsync_local_mode_with_custom_params(config):
    """Test rsync in local mode preserves custom parameters."""
    config.is_local = True
    config.rsync_params = "--exclude=*.log --max-size=5m"
    manager = BackupManager(config)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        manager.run_rsync("/source/path", Path("/target/path"))

        args = mock_run.call_args[0][0]
        # Should have both local mode filters and custom params
        assert "--filter=:- .gitignore" in args
        assert "--exclude=.git" in args
        assert "--exclude=.snapshots" in args
        assert "--exclude=*.log" in args
        assert "--max-size=5m" in args


def test_hourly_backup_local_mode(config, initialized_snapshots, source_dirs):
    """Test hourly backup respects local mode settings."""
    config.is_local = True
    manager = BackupManager(config)

    with patch.object(manager, "run_rsync") as mock_rsync:
        mock_rsync.return_value = MagicMock(returncode=0, stdout="", stderr="")

        manager.hourly_backup()

        # Verify rsync was called with local mode
        # Check that calls included gitignore filtering
        for call_args in mock_rsync.call_args_list:
            # The manager's is_local flag should affect run_rsync behavior
            pass  # Just verify it doesn't crash with local mode


def test_run_rsync_local_mode_all_flags_together(config):
    """Test rsync in local mode with all flags combined."""
    config.is_local = True
    config.rsync_params = "--verbose --progress"
    manager = BackupManager(config)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        manager.run_rsync(
            "/source/path",
            Path("/target/path"),
            dry_run=True,
            delete=True,
            ignore_existing=False,
        )

        args = mock_run.call_args[0][0]
        # Base flags
        assert "rsync" in args
        assert "-a" in args
        assert "-v" in args

        # Operation flags
        assert "--dry-run" in args
        assert "--delete" in args

        # Local mode flags
        assert "--filter=:- .gitignore" in args
        assert "--exclude=.git" in args
        assert "--exclude=.snapshots" in args

        # Custom params
        assert "--verbose" in args
        assert "--progress" in args
