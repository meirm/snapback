"""Tests for recovery operations."""

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from snapback.recovery import RecoveryManager


def test_recover(config, initialized_snapshots, sample_snapshot, source_dirs):
    """Test full recovery from snapshot."""
    manager = RecoveryManager(config)

    # Modify source files
    for source_dir in source_dirs:
        (source_dir / "file1.txt").write_text("modified")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        manager.recover("hour-0")

        # rsync should be called for each source directory
        assert mock_run.call_count == len(source_dirs)

        # Check that --delete flag is used
        args = mock_run.call_args[0][0]
        assert "--delete" in args


def test_recover_missing_snapshot(config, initialized_snapshots):
    """Test recovery from non-existent snapshot."""
    manager = RecoveryManager(config)

    with pytest.raises(FileNotFoundError):
        manager.recover("nonexistent-snapshot")


def test_recover_dry_run(config, initialized_snapshots, sample_snapshot, capsys):
    """Test recovery in dry-run mode."""
    manager = RecoveryManager(config)

    manager.recover("hour-0", dry_run=True)

    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out


def test_undel(config, initialized_snapshots, sample_snapshot, source_dirs):
    """Test undelete operation."""
    manager = RecoveryManager(config)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        manager.undel("hour-0")

        # rsync should be called with --ignore-existing
        args = mock_run.call_args[0][0]
        assert "--ignore-existing" in args


def test_undel_missing_snapshot(config, initialized_snapshots):
    """Test undel from non-existent snapshot."""
    manager = RecoveryManager(config)

    with pytest.raises(FileNotFoundError):
        manager.undel("nonexistent-snapshot")


def test_undel_dry_run(config, initialized_snapshots, sample_snapshot, capsys):
    """Test undel in dry-run mode."""
    manager = RecoveryManager(config)

    manager.undel("hour-0", dry_run=True)

    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out


def test_tag(config, initialized_snapshots, sample_snapshot, source_dirs):
    """Test creating a snapshot tag."""
    manager = RecoveryManager(config)
    base = Path(config.target_base)

    manager.tag("hour-0", "before-upgrade")

    # Tag should exist
    assert (base / "before-upgrade").exists()

    # Should contain same files
    assert (base / "before-upgrade" / source_dirs[0].name / "file1.txt").exists()


def test_tag_missing_snapshot(config, initialized_snapshots):
    """Test tagging non-existent snapshot."""
    manager = RecoveryManager(config)

    with pytest.raises(FileNotFoundError):
        manager.tag("nonexistent", "mytag")


def test_tag_existing_tag(config, initialized_snapshots, sample_snapshot):
    """Test creating tag with existing name."""
    manager = RecoveryManager(config)
    base = Path(config.target_base)

    # Create initial tag
    manager.tag("hour-0", "mytag")

    # Try to create again
    with pytest.raises(FileExistsError):
        manager.tag("hour-0", "mytag")


def test_tag_dry_run(config, initialized_snapshots, sample_snapshot, capsys):
    """Test tagging in dry-run mode."""
    manager = RecoveryManager(config)

    manager.tag("hour-0", "mytag", dry_run=True)

    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out


def test_delete_path(config, initialized_snapshots, sample_snapshot, source_dirs):
    """Test deleting path from hour-0."""
    manager = RecoveryManager(config)
    base = Path(config.target_base)

    # Get a file path from source
    file_path = source_dirs[0] / "file1.txt"

    manager.delete_path(str(file_path))

    # File should be deleted from hour-0
    hour_0_file = base / "hour-0" / source_dirs[0].name / "file1.txt"
    assert not hour_0_file.exists()


def test_delete_path_directory(
    config, initialized_snapshots, sample_snapshot, source_dirs
):
    """Test deleting directory from hour-0."""
    manager = RecoveryManager(config)
    base = Path(config.target_base)

    # Get a directory path from source
    dir_path = source_dirs[0] / "subdir"

    manager.delete_path(str(dir_path))

    # Directory should be deleted from hour-0
    hour_0_dir = base / "hour-0" / source_dirs[0].name / "subdir"
    assert not hour_0_dir.exists()


def test_delete_path_missing_hour0(config, initialized_snapshots):
    """Test deleting path when hour-0 doesn't exist."""
    manager = RecoveryManager(config)
    base = Path(config.target_base)

    # Remove hour-0
    shutil.rmtree(base / "hour-0")

    with pytest.raises(FileNotFoundError):
        manager.delete_path("/some/path")


def test_delete_path_dry_run(
    config, initialized_snapshots, sample_snapshot, source_dirs, capsys
):
    """Test deleting path in dry-run mode."""
    manager = RecoveryManager(config)

    file_path = source_dirs[0] / "file1.txt"
    manager.delete_path(str(file_path), dry_run=True)

    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out


def test_list_tagged_snapshots(config, initialized_snapshots, sample_snapshot):
    """Test listing tagged snapshots."""
    manager = RecoveryManager(config)

    # Create some tags
    manager.tag("hour-0", "before-upgrade")
    manager.tag("hour-0", "stable-version")

    tags = manager.list_tagged_snapshots()

    assert "before-upgrade" in tags
    assert "stable-version" in tags
    assert "hour-0" not in tags  # Standard snapshots should not be listed


def test_list_tagged_snapshots_empty(config, initialized_snapshots):
    """Test listing tagged snapshots when none exist."""
    manager = RecoveryManager(config)

    tags = manager.list_tagged_snapshots()

    assert tags == []


def test_delete_tag(config, initialized_snapshots, sample_snapshot):
    """Test deleting a tagged snapshot."""
    manager = RecoveryManager(config)
    base = Path(config.target_base)

    # Create a tag
    manager.tag("hour-0", "mytag")

    # Delete it
    manager.delete_tag("mytag")

    assert not (base / "mytag").exists()


def test_delete_tag_missing(config, initialized_snapshots):
    """Test deleting non-existent tag."""
    manager = RecoveryManager(config)

    with pytest.raises(FileNotFoundError):
        manager.delete_tag("nonexistent")


def test_delete_tag_standard_snapshot(config, initialized_snapshots):
    """Test that standard snapshots cannot be deleted as tags."""
    manager = RecoveryManager(config)

    with pytest.raises(ValueError):
        manager.delete_tag("hour-0")


def test_delete_tag_dry_run(
    config, initialized_snapshots, sample_snapshot, capsys
):
    """Test deleting tag in dry-run mode."""
    manager = RecoveryManager(config)

    # Create a tag
    manager.tag("hour-0", "mytag")

    # Delete in dry-run
    manager.delete_tag("mytag", dry_run=True)

    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out

    # Tag should still exist
    base = Path(config.target_base)
    assert (base / "mytag").exists()


def test_recover_missing_subdirectory(
    config, initialized_snapshots, sample_snapshot, source_dirs, capsys
):
    """Test recovery when snapshot subdirectory is missing."""
    manager = RecoveryManager(config)
    base = Path(config.target_base)

    # Remove a subdirectory from hour-0
    shutil.rmtree(base / "hour-0" / source_dirs[0].name)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        manager.recover("hour-0")

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "not found" in captured.out
