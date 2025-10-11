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


def test_cmd_sampleconfig(capsys):
    """Test sampleconfig command outputs to stdout."""
    args = MagicMock()
    args.local = False

    result = cli.cmd_sampleconfig(args)

    assert result == 0
    captured = capsys.readouterr()
    # Should output sample config to stdout
    assert "DIRS=" in captured.out
    assert "TARGETBASE=" in captured.out


def test_cmd_sampleconfig_local(capsys):
    """Test sampleconfig command with --local flag."""
    args = MagicMock()
    args.local = True

    result = cli.cmd_sampleconfig(args)

    assert result == 0
    captured = capsys.readouterr()
    # Should output local config template
    assert "DIRS='.'" in captured.out
    assert "TARGETBASE='./.snapshots'" in captured.out
    assert "project-local configuration" in captured.out


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


# Project-Local Mode Tests


def test_is_git_repository_true(tmp_path, monkeypatch):
    """Test detecting a git repository."""
    monkeypatch.chdir(tmp_path)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    assert cli.is_git_repository() is True


def test_is_git_repository_false(tmp_path, monkeypatch):
    """Test detecting non-git directory."""
    monkeypatch.chdir(tmp_path)

    assert cli.is_git_repository() is False


def test_cmd_init_local_explicit(tmp_path, monkeypatch, capsys):
    """Test init command with explicit --local flag."""
    monkeypatch.chdir(tmp_path)

    args = MagicMock()
    args.config = None
    args.local = True
    args.force_global = False

    with patch("snapback.snapshot.SnapshotManager.init_snapshots"):
        result = cli.cmd_init(args)

    assert result == 0

    # Should create local config
    config_path = tmp_path / ".snapshotrc"
    assert config_path.exists()

    # Should update .gitignore
    gitignore_path = tmp_path / ".gitignore"
    assert gitignore_path.exists()

    gitignore_content = gitignore_path.read_text()
    assert ".snapshots/" in gitignore_content
    assert ".snapshotrc" in gitignore_content

    captured = capsys.readouterr()
    assert "project-local" in captured.out.lower()


def test_cmd_init_local_auto_detect(tmp_path, monkeypatch, capsys):
    """Test init command auto-detects git repository."""
    monkeypatch.chdir(tmp_path)

    # Create .git directory to simulate git repo
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    args = MagicMock()
    args.config = None
    args.local = False
    args.force_global = False

    with patch("snapback.snapshot.SnapshotManager.init_snapshots"):
        result = cli.cmd_init(args)

    assert result == 0

    # Should auto-detect and create local config
    config_path = tmp_path / ".snapshotrc"
    assert config_path.exists()

    captured = capsys.readouterr()
    assert "Git repository detected" in captured.out
    assert "project-local" in captured.out.lower()


def test_cmd_init_global_force(tmp_path, monkeypatch, capsys):
    """Test init command with --global flag overrides auto-detection."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create .git directory (would normally trigger local mode)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    # Create global config
    global_config = tmp_path / ".snapshotrc"
    global_config.write_text("DIRS='/tmp'\nTARGETBASE='/tmp/.Snapshots'\n")

    args = MagicMock()
    args.config = str(global_config)
    args.local = False
    args.force_global = True

    with patch("snapback.snapshot.SnapshotManager.init_snapshots"):
        result = cli.cmd_init(args)

    assert result == 0

    # Should NOT create local config
    local_config = tmp_path / ".snapshotrc"
    # Should use the existing global config instead


def test_cmd_init_local_existing_config(tmp_path, monkeypatch, capsys):
    """Test init with existing local config doesn't overwrite."""
    monkeypatch.chdir(tmp_path)

    # Create existing local config
    config_path = tmp_path / ".snapshotrc"
    original_content = "# My custom config\nDIRS='.'\nTARGETBASE='./.snapshots'\n"
    config_path.write_text(original_content)

    args = MagicMock()
    args.config = None
    args.local = True
    args.force_global = False

    with patch("snapback.snapshot.SnapshotManager.init_snapshots"):
        result = cli.cmd_init(args)

    assert result == 0

    # Config should not be overwritten
    assert config_path.read_text() == original_content

    captured = capsys.readouterr()
    assert "already exists" in captured.out


def test_cmd_init_local_gitignore_already_has_entries(tmp_path, monkeypatch, capsys):
    """Test init with .gitignore already containing snapback entries."""
    monkeypatch.chdir(tmp_path)

    # Create .gitignore with snapback entries
    gitignore_path = tmp_path / ".gitignore"
    gitignore_path.write_text(
        """# Python
__pycache__/
*.pyc

# snapback
.snapshots/
.snapshotrc
"""
    )

    args = MagicMock()
    args.config = None
    args.local = True
    args.force_global = False

    # Mock the Config and SnapshotManager to avoid filesystem operations
    with patch("snapback.cli.Config") as mock_config_class:
        mock_config = MagicMock()
        mock_config.target_base = "./.snapshots"
        mock_config_class.generate_sample_config.return_value = (
            "DIRS='.'\nTARGETBASE='./.snapshots'\n"
        )
        mock_config_class.load.return_value = mock_config

        with patch("snapback.snapshot.SnapshotManager.init_snapshots"):
            result = cli.cmd_init(args)

    assert result == 0

    # .gitignore should not be duplicated
    gitignore_content = gitignore_path.read_text()
    assert gitignore_content.count(".snapshots/") == 1
    assert gitignore_content.count(".snapshotrc") == 1

    captured = capsys.readouterr()
    assert "already contains" in captured.out


def test_cmd_init_local_updates_gitignore_preserves_content(tmp_path, monkeypatch):
    """Test init updates .gitignore while preserving existing content."""
    monkeypatch.chdir(tmp_path)

    # Create existing .gitignore without snapback entries
    gitignore_path = tmp_path / ".gitignore"
    original_content = """# Python
__pycache__/
*.py[cod]

# Virtual environments
venv/
"""
    gitignore_path.write_text(original_content)

    args = MagicMock()
    args.config = None
    args.local = True
    args.force_global = False

    with patch("snapback.snapshot.SnapshotManager.init_snapshots"):
        result = cli.cmd_init(args)

    assert result == 0

    # Original content should be preserved
    gitignore_content = gitignore_path.read_text()
    assert "__pycache__/" in gitignore_content
    assert "*.py[cod]" in gitignore_content
    assert "venv/" in gitignore_content

    # New entries should be added
    assert ".snapshots/" in gitignore_content
    assert ".snapshotrc" in gitignore_content
    assert "# snapback" in gitignore_content
