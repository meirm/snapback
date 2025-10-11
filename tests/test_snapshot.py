"""Tests for snapshot management."""

import shutil
from pathlib import Path

import pytest

from snapback.snapshot import SnapshotManager


def test_init_snapshots(config, snapshot_base):
    """Test initializing snapshot directory structure."""
    manager = SnapshotManager(config)
    manager.init_snapshots()

    # Check hourly snapshots
    for i in range(24):
        assert (snapshot_base / f"hour-{i}").exists()

    # Check daily snapshots
    for i in range(8):
        assert (snapshot_base / f"day-{i}").exists()

    # Check weekly snapshots
    for i in range(5):
        assert (snapshot_base / f"week-{i}").exists()

    # Check monthly snapshots
    for i in range(13):
        assert (snapshot_base / f"month-{i}").exists()


def test_create_hard_link_copy(config, snapshot_base, source_dirs):
    """Test creating hard-link copies."""
    manager = SnapshotManager(config)

    src = source_dirs[0]
    dst = snapshot_base / "test_copy"

    manager.create_hard_link_copy(src, dst)

    # Check that files exist
    assert (dst / "file1.txt").exists()
    assert (dst / "file2.txt").exists()
    assert (dst / "subdir" / "file3.txt").exists()

    # Check that files are hard-linked (same inode)
    src_file = src / "file1.txt"
    dst_file = dst / "file1.txt"
    assert src_file.stat().st_ino == dst_file.stat().st_ino


def test_rotate_hourly(initialized_snapshots, sample_snapshot):
    """Test hourly snapshot rotation."""
    manager = initialized_snapshots
    base = Path(manager.config.target_base)

    # Populate some snapshots
    for i in range(3):
        (base / f"hour-{i}" / "marker.txt").write_text(f"hour-{i}")

    manager.rotate_hourly()

    # hour-0 should be rotated to hour-1
    assert not (base / "hour-0").exists() or not (
        base / "hour-0" / "marker.txt"
    ).exists()
    assert (base / "hour-1" / "marker.txt").read_text() == "hour-0"
    assert (base / "hour-2" / "marker.txt").read_text() == "hour-1"


def test_rotate_hourly_dry_run(initialized_snapshots, sample_snapshot, capsys):
    """Test hourly snapshot rotation in dry-run mode."""
    manager = initialized_snapshots
    base = Path(manager.config.target_base)

    # Populate snapshots
    for i in range(3):
        (base / f"hour-{i}" / "marker.txt").write_text(f"hour-{i}")

    manager.rotate_hourly(dry_run=True)

    # Nothing should change
    assert (base / "hour-0" / "marker.txt").read_text() == "hour-0"
    assert (base / "hour-1" / "marker.txt").read_text() == "hour-1"

    # Check output
    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out


def test_rotate_daily(initialized_snapshots, sample_snapshot):
    """Test daily snapshot rotation."""
    manager = initialized_snapshots
    base = Path(manager.config.target_base)

    # Create hour-23 and some days
    (base / "hour-23" / "marker.txt").write_text("hour-23")
    for i in range(3):
        (base / f"day-{i}" / "marker.txt").write_text(f"day-{i}")

    manager.rotate_daily()

    # hour-23 should become day-0
    assert (base / "day-0" / "marker.txt").read_text() == "hour-23"
    assert (base / "day-1" / "marker.txt").read_text() == "day-0"


def test_rotate_weekly(initialized_snapshots, sample_snapshot):
    """Test weekly snapshot rotation."""
    manager = initialized_snapshots
    base = Path(manager.config.target_base)

    # Create day-7 and some weeks
    (base / "day-7" / "marker.txt").write_text("day-7")
    for i in range(2):
        (base / f"week-{i}" / "marker.txt").write_text(f"week-{i}")

    manager.rotate_weekly()

    # day-7 should become week-0 (using hard links)
    assert (base / "week-0" / "marker.txt").read_text() == "day-7"
    assert (base / "week-1" / "marker.txt").read_text() == "week-0"

    # day-7 should still exist (hard-linked, not moved)
    assert (base / "day-7" / "marker.txt").exists()


def test_rotate_monthly(initialized_snapshots, sample_snapshot):
    """Test monthly snapshot rotation."""
    manager = initialized_snapshots
    base = Path(manager.config.target_base)

    # Create week-4 and some months
    (base / "week-4" / "marker.txt").write_text("week-4")
    for i in range(3):
        (base / f"month-{i}" / "marker.txt").write_text(f"month-{i}")

    manager.rotate_monthly()

    # week-4 should become month-0
    assert (base / "month-0" / "marker.txt").read_text() == "week-4"
    assert (base / "month-1" / "marker.txt").read_text() == "month-0"


def test_rotate_hourly_deletes_oldest(initialized_snapshots, sample_snapshot):
    """Test that hourly rotation deletes hour-23."""
    manager = initialized_snapshots
    base = Path(manager.config.target_base)

    # Create all hourly snapshots
    for i in range(24):
        (base / f"hour-{i}" / "marker.txt").write_text(f"hour-{i}")

    manager.rotate_hourly()

    # hour-23 should be deleted
    # hour-22 should be in hour-23 position
    assert (base / "hour-23" / "marker.txt").read_text() == "hour-22"


def test_rotate_monthly_deletes_oldest(initialized_snapshots, sample_snapshot):
    """Test that monthly rotation deletes month-12."""
    manager = initialized_snapshots
    base = Path(manager.config.target_base)

    # Create all monthly snapshots
    for i in range(13):
        (base / f"month-{i}" / "marker.txt").write_text(f"month-{i}")

    # Also create week-4
    (base / "week-4" / "marker.txt").write_text("week-4")

    manager.rotate_monthly()

    # month-12 should now contain old month-11 data
    assert (base / "month-12" / "marker.txt").read_text() == "month-11"
    # month-0 should contain week-4
    assert (base / "month-0" / "marker.txt").read_text() == "week-4"


def test_snapshot_exists(initialized_snapshots):
    """Test checking if snapshot exists."""
    manager = initialized_snapshots

    assert manager.snapshot_exists("hour-0")
    assert manager.snapshot_exists("day-5")
    assert not manager.snapshot_exists("nonexistent")


def test_get_snapshot_path(initialized_snapshots):
    """Test getting snapshot path."""
    manager = initialized_snapshots
    base = Path(manager.config.target_base)

    path = manager.get_snapshot_path("hour-1")
    assert path == base / "hour-1"


def test_list_snapshots(initialized_snapshots):
    """Test listing all snapshots."""
    manager = initialized_snapshots

    snapshots = manager.list_snapshots()

    assert "hour-0" in snapshots
    assert "day-0" in snapshots
    assert "week-0" in snapshots
    assert "month-0" in snapshots

    # Should be sorted
    assert snapshots == sorted(snapshots)


def test_create_hard_link_copy_missing_source(config, snapshot_base):
    """Test creating hard-link copy with missing source."""
    manager = SnapshotManager(config)

    with pytest.raises(FileNotFoundError):
        manager.create_hard_link_copy(
            snapshot_base / "nonexistent", snapshot_base / "dest"
        )


def test_rotation_with_empty_snapshots(initialized_snapshots):
    """Test rotation with empty snapshot structure."""
    manager = initialized_snapshots

    # Should not raise errors
    manager.rotate_hourly()
    manager.rotate_daily()
    manager.rotate_weekly()
    manager.rotate_monthly()
