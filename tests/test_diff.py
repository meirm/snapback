"""Tests for diff operations."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from snapback.diff import DiffManager


def test_compare_file_versions(config, initialized_snapshots, sample_snapshot):
    """Test comparing file versions."""
    manager = DiffManager(config)

    # Create a test file in source and snapshot
    source_dir = Path(config.dirs[0])
    test_file = source_dir / "file1.txt"  # Use a file that exists in sample_snapshot

    # file1.txt already exists from sample_snapshot fixture

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        result = manager.compare_file_versions(str(test_file), periods_ago=0)

        # Should attempt to run diff tool
        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "vimdiff" in args


def test_compare_file_versions_missing_file(config, initialized_snapshots):
    """Test comparing non-existent file."""
    manager = DiffManager(config)

    result = manager.compare_file_versions("/nonexistent/file.txt")

    assert result is False


def test_compare_file_versions_not_in_snapshot(
    config, initialized_snapshots, sample_snapshot, capsys
):
    """Test comparing file not in snapshot."""
    manager = DiffManager(config)

    # Create a new file not in snapshots
    source_dir = Path(config.dirs[0])
    test_file = source_dir / "new_file.txt"
    test_file.write_text("new content")

    result = manager.compare_file_versions(str(test_file))

    assert result is False
    captured = capsys.readouterr()
    assert "Could not find" in captured.out


def test_compare_file_versions_custom_tool(
    config, initialized_snapshots, sample_snapshot
):
    """Test comparing with custom diff tool."""
    manager = DiffManager(config)

    source_dir = Path(config.dirs[0])
    test_file = source_dir / "file1.txt"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        manager.compare_file_versions(str(test_file), diff_tool="meld")

        args = mock_run.call_args[0][0]
        assert "meld" in args


def test_compare_file_versions_tool_not_found(
    config, initialized_snapshots, sample_snapshot, capsys
):
    """Test comparing with missing diff tool."""
    manager = DiffManager(config)

    source_dir = Path(config.dirs[0])
    test_file = source_dir / "file1.txt"

    with patch("subprocess.run", side_effect=FileNotFoundError()):
        result = manager.compare_file_versions(str(test_file))

        assert result is False
        captured = capsys.readouterr()
        assert "not found" in captured.out


def test_show_file_diff(config, initialized_snapshots, sample_snapshot):
    """Test showing text diff."""
    manager = DiffManager(config)

    source_dir = Path(config.dirs[0])
    test_file = source_dir / "file1.txt"

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 1  # Files differ
        mock_result.stdout = "diff output"
        mock_run.return_value = mock_result

        result = manager.show_file_diff(str(test_file))

        assert result is True
        args = mock_run.call_args[0][0]
        assert "diff" in args


def test_show_file_diff_identical(config, initialized_snapshots, sample_snapshot):
    """Test showing diff for identical files."""
    manager = DiffManager(config)

    source_dir = Path(config.dirs[0])
    test_file = source_dir / "file1.txt"

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0  # Files identical
        mock_run.return_value = mock_result

        result = manager.show_file_diff(str(test_file))

        assert result is True


def test_show_file_diff_error(
    config, initialized_snapshots, sample_snapshot, capsys
):
    """Test showing diff with error."""
    manager = DiffManager(config)

    source_dir = Path(config.dirs[0])
    test_file = source_dir / "file1.txt"

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 2  # Error
        mock_result.stderr = "error message"
        mock_run.return_value = mock_result

        result = manager.show_file_diff(str(test_file))

        assert result is False


def test_show_file_diff_missing_command(
    config, initialized_snapshots, sample_snapshot, capsys
):
    """Test showing diff when diff command not found."""
    manager = DiffManager(config)

    source_dir = Path(config.dirs[0])
    test_file = source_dir / "file1.txt"

    with patch("subprocess.run", side_effect=FileNotFoundError()):
        result = manager.show_file_diff(str(test_file))

        assert result is False
        captured = capsys.readouterr()
        assert "not found" in captured.out


def test_list_file_history(config, initialized_snapshots, sample_snapshot, capsys):
    """Test listing file history."""
    manager = DiffManager(config)

    result = manager.list_file_history("file1.txt")

    assert result is True
    captured = capsys.readouterr()
    assert "file1.txt" in captured.out


def test_list_file_history_not_found(config, initialized_snapshots, capsys):
    """Test listing history for non-existent file."""
    manager = DiffManager(config)

    result = manager.list_file_history("nonexistent.txt")

    assert result is False
    captured = capsys.readouterr()
    assert "not found" in captured.out


def test_compare_snapshots(config, initialized_snapshots, sample_snapshot):
    """Test comparing two snapshots."""
    manager = DiffManager(config)
    base = Path(config.target_base)

    # Create another snapshot
    hour_1 = base / "hour-1"
    hour_1.mkdir(parents=True, exist_ok=True)

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "diff output"
        mock_run.return_value = mock_result

        result = manager.compare_snapshots("hour-0", "hour-1")

        assert result is True
        args = mock_run.call_args[0][0]
        assert "diff" in args
        assert "-r" in args


def test_compare_snapshots_missing(config, initialized_snapshots):
    """Test comparing with missing snapshot."""
    manager = DiffManager(config)

    result = manager.compare_snapshots("hour-0", "nonexistent")

    assert result is False


def test_compare_snapshots_with_path(config, initialized_snapshots, sample_snapshot):
    """Test comparing specific path in snapshots."""
    manager = DiffManager(config)
    base = Path(config.target_base)

    # Create another snapshot
    hour_1 = base / "hour-1"
    hour_1.mkdir(parents=True, exist_ok=True)

    # Create a specific path in both
    source_dir = Path(config.dirs[0])
    for snapshot in ["hour-0", "hour-1"]:
        target_dir = base / snapshot / source_dir.name
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "test.txt").write_text(f"content {snapshot}")

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "diff output"
        mock_run.return_value = mock_result

        result = manager.compare_snapshots(
            "hour-0", "hour-1", path=str(source_dir.name)
        )

        assert result is True


def test_compare_snapshots_path_missing(
    config, initialized_snapshots, sample_snapshot, capsys
):
    """Test comparing path that doesn't exist in snapshot."""
    manager = DiffManager(config)
    base = Path(config.target_base)

    # Create another snapshot
    hour_1 = base / "hour-1"
    hour_1.mkdir(parents=True, exist_ok=True)

    result = manager.compare_snapshots("hour-0", "hour-1", path="nonexistent")

    assert result is False
    captured = capsys.readouterr()
    assert "not found" in captured.out


def test_compare_snapshots_identical(config, initialized_snapshots, sample_snapshot):
    """Test comparing identical snapshots."""
    manager = DiffManager(config)

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0  # Identical
        mock_run.return_value = mock_result

        result = manager.compare_snapshots("hour-0", "hour-0")

        assert result is True


def test_show_file_diff_custom_context(config, initialized_snapshots, sample_snapshot):
    """Test showing diff with custom context lines."""
    manager = DiffManager(config)

    source_dir = Path(config.dirs[0])
    test_file = source_dir / "file1.txt"

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "diff output"
        mock_run.return_value = mock_result

        manager.show_file_diff(str(test_file), context_lines=5)

        args = mock_run.call_args[0][0]
        assert "-U5" in args
