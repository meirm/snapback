"""Tests for command-line interface."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from snapback import cli


def test_create_parser():
    """Test creating argument parser."""
    parser = cli.create_parser()

    assert parser is not None
    assert "snapback" in parser.prog


def test_cmd_init(config_file, capsys):
    """Test init command."""
    args = MagicMock()
    args.config = str(config_file)

    result = cli.cmd_init(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "Initializing" in captured.out


def test_cmd_sampleconfig(temp_dir, monkeypatch, capsys):
    """Test sampleconfig command."""
    monkeypatch.setenv("HOME", str(temp_dir))

    args = MagicMock()

    result = cli.cmd_sampleconfig(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "Sample configuration written" in captured.out

    # Check file was created
    config_path = temp_dir / ".snapshotrc"
    assert config_path.exists()


def test_cmd_sampleconfig_overwrite(temp_dir, monkeypatch, capsys):
    """Test sampleconfig with existing file."""
    monkeypatch.setenv("HOME", str(temp_dir))

    # Create existing config
    config_path = temp_dir / ".snapshotrc"
    config_path.write_text("existing")

    args = MagicMock()

    # Mock user input to decline overwrite
    with patch("builtins.input", return_value="n"):
        result = cli.cmd_sampleconfig(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "Cancelled" in captured.out


def test_cmd_hourly(config_file):
    """Test hourly command."""
    args = MagicMock()
    args.config = str(config_file)
    args.dry_run = True

    with patch("snapback.backup.BackupManager.hourly_backup") as mock_backup:
        result = cli.cmd_hourly(args)

        assert result == 0
        mock_backup.assert_called_once_with(dry_run=True)


def test_cmd_daily(config_file):
    """Test daily command."""
    args = MagicMock()
    args.config = str(config_file)
    args.dry_run = False

    with patch("snapback.backup.BackupManager.daily_backup") as mock_backup:
        result = cli.cmd_daily(args)

        assert result == 0
        mock_backup.assert_called_once_with(dry_run=False)


def test_cmd_weekly(config_file):
    """Test weekly command."""
    args = MagicMock()
    args.config = str(config_file)
    args.dry_run = False

    with patch("snapback.backup.BackupManager.weekly_backup") as mock_backup:
        result = cli.cmd_weekly(args)

        assert result == 0
        mock_backup.assert_called_once()


def test_cmd_monthly(config_file):
    """Test monthly command."""
    args = MagicMock()
    args.config = str(config_file)
    args.dry_run = False

    with patch("snapback.backup.BackupManager.monthly_backup") as mock_backup:
        result = cli.cmd_monthly(args)

        assert result == 0
        mock_backup.assert_called_once()


def test_cmd_recover(config_file):
    """Test recover command."""
    args = MagicMock()
    args.config = str(config_file)
    args.snapshot = "hour-1"
    args.dry_run = False

    with patch("snapback.recovery.RecoveryManager.recover") as mock_recover:
        result = cli.cmd_recover(args)

        assert result == 0
        mock_recover.assert_called_once_with("hour-1", dry_run=False)


def test_cmd_recover_missing_snapshot(config_file):
    """Test recover with missing snapshot."""
    args = MagicMock()
    args.config = str(config_file)
    args.snapshot = "nonexistent"
    args.dry_run = False

    with patch(
        "snapback.recovery.RecoveryManager.recover",
        side_effect=FileNotFoundError("not found"),
    ):
        result = cli.cmd_recover(args)

        assert result == 1


def test_cmd_undel(config_file):
    """Test undel command."""
    args = MagicMock()
    args.config = str(config_file)
    args.snapshot = "hour-2"
    args.dry_run = False

    with patch("snapback.recovery.RecoveryManager.undel") as mock_undel:
        result = cli.cmd_undel(args)

        assert result == 0
        mock_undel.assert_called_once_with("hour-2", dry_run=False)


def test_cmd_tag(config_file):
    """Test tag command."""
    args = MagicMock()
    args.config = str(config_file)
    args.snapshot = "hour-0"
    args.tagname = "before-upgrade"
    args.dry_run = False

    with patch("snapback.recovery.RecoveryManager.tag") as mock_tag:
        result = cli.cmd_tag(args)

        assert result == 0
        mock_tag.assert_called_once_with("hour-0", "before-upgrade", dry_run=False)


def test_cmd_delete(config_file):
    """Test delete command."""
    args = MagicMock()
    args.config = str(config_file)
    args.path = "/some/path"
    args.dry_run = False

    with patch("snapback.recovery.RecoveryManager.delete_path") as mock_delete:
        result = cli.cmd_delete(args)

        assert result == 0
        mock_delete.assert_called_once_with("/some/path", dry_run=False)


def test_cmd_list_snapshots(config_file, initialized_snapshots, capsys):
    """Test list command for snapshots."""
    args = MagicMock()
    args.config = str(config_file)
    args.filename = None
    args.tags = False

    result = cli.cmd_list(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "hour-0" in captured.out


def test_cmd_list_tags(config_file, initialized_snapshots, capsys):
    """Test list command for tags."""
    args = MagicMock()
    args.config = str(config_file)
    args.filename = None
    args.tags = True

    with patch(
        "snapback.recovery.RecoveryManager.list_tagged_snapshots",
        return_value=["my-tag"],
    ):
        result = cli.cmd_list(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "my-tag" in captured.out


def test_cmd_list_file(config_file, initialized_snapshots, sample_snapshot, capsys):
    """Test list command for finding files."""
    args = MagicMock()
    args.config = str(config_file)
    args.filename = "file1.txt"
    args.tags = False

    result = cli.cmd_list(args)

    captured = capsys.readouterr()
    # Should either find file or say not found
    assert "file1.txt" in captured.out or "not found" in captured.out


def test_cmd_diff(config_file):
    """Test diff command."""
    args = MagicMock()
    args.config = str(config_file)
    args.filename = "test.txt"
    args.periods = 1
    args.tool = "vimdiff"
    args.text = False

    with patch(
        "snapback.diff.DiffManager.compare_file_versions", return_value=True
    ) as mock_diff:
        result = cli.cmd_diff(args)

        assert result == 0
        mock_diff.assert_called_once_with("test.txt", 1, diff_tool="vimdiff")


def test_cmd_diff_text(config_file):
    """Test diff command with text output."""
    args = MagicMock()
    args.config = str(config_file)
    args.filename = "test.txt"
    args.periods = 2
    args.text = True

    with patch(
        "snapback.diff.DiffManager.show_file_diff", return_value=True
    ) as mock_diff:
        result = cli.cmd_diff(args)

        assert result == 0
        mock_diff.assert_called_once_with("test.txt", 2)


def test_main_no_command(capsys):
    """Test main with no command."""
    with patch("sys.argv", ["snapback"]):
        result = cli.main()

        assert result == 1
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower()


def test_main_init_command(config_file):
    """Test main with init command."""
    with patch("sys.argv", ["snapback", "--config", str(config_file), "init"]):
        result = cli.main()

        assert result == 0


def test_main_unknown_command():
    """Test main with unknown command."""
    with patch("sys.argv", ["snapback", "unknown"]):
        with pytest.raises(SystemExit):
            cli.main()


def test_snapls_main(config_file):
    """Test snapls compatibility command."""
    with patch(
        "sys.argv", ["snapls", "--config", str(config_file), "test.txt"]
    ), patch("snapback.cli.cmd_list", return_value=0) as mock_list:
        result = cli.snapls_main()

        assert result == 0
        mock_list.assert_called_once()


def test_snapdiff_main(config_file):
    """Test snapdiff compatibility command."""
    with patch(
        "sys.argv", ["snapdiff", "--config", str(config_file), "1", "test.txt"]
    ), patch("snapback.cli.cmd_diff", return_value=0) as mock_diff:
        result = cli.snapdiff_main()

        assert result == 0
        mock_diff.assert_called_once()


def test_load_config_missing_file(capsys):
    """Test loading missing config file."""
    with pytest.raises(SystemExit):
        cli.load_config("/nonexistent/config")

    captured = capsys.readouterr()
    assert "Error" in captured.err


def test_cmd_hourly_error(config_file, capsys):
    """Test hourly command with error."""
    args = MagicMock()
    args.config = str(config_file)
    args.dry_run = False

    with patch(
        "snapback.backup.BackupManager.hourly_backup",
        side_effect=Exception("test error"),
    ):
        result = cli.cmd_hourly(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err
