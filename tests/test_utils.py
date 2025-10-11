"""Tests for utility functions."""

from pathlib import Path

import pytest

from snapback.utils import (
    expand_path,
    find_file_in_snapshots,
    format_file_listing,
    get_file_from_snapshot,
    get_snapshot_age_description,
    is_standard_snapshot,
    parse_snapshot_name,
    snapshot_to_hours,
    sort_snapshots_by_age,
)


def test_snapshot_to_hours():
    """Test converting snapshot names to hours."""
    assert snapshot_to_hours("hour-0") == 0
    assert snapshot_to_hours("hour-5") == 5
    assert snapshot_to_hours("day-0") == 24  # yesterday (24 hours ago)
    assert snapshot_to_hours("day-3") == 96  # 4 days ago (4 * 24)
    assert snapshot_to_hours("week-0") == 168  # last week (7 * 24)
    assert snapshot_to_hours("week-2") == 504  # 3 weeks ago (3 * 7 * 24)
    assert snapshot_to_hours("month-0") == 720  # last month (30 * 24)
    assert snapshot_to_hours("month-1") == 1440  # 2 months ago (2 * 30 * 24)


def test_snapshot_to_hours_invalid():
    """Test converting invalid snapshot names."""
    # Invalid names should return high value
    assert snapshot_to_hours("invalid") > 100000
    assert snapshot_to_hours("tagged-snapshot") > 100000


def test_sort_snapshots_by_age():
    """Test sorting snapshots by age."""
    snapshots = [
        "month-1",
        "hour-5",
        "day-2",
        "week-1",
        "hour-0",
        "day-0",
    ]

    sorted_snapshots = sort_snapshots_by_age(snapshots)

    # Should be sorted newest to oldest
    assert sorted_snapshots[0] == "hour-0"
    assert sorted_snapshots[1] == "hour-5"
    assert sorted_snapshots[2] == "day-0"


def test_find_file_in_snapshots(config, initialized_snapshots, sample_snapshot):
    """Test finding files in snapshots."""
    results = find_file_in_snapshots(
        "file1.txt",
        Path(config.target_base),
        config.dirs,
    )

    assert len(results) > 0
    assert all(name.startswith("hour-") for name, _ in results[:1])


def test_find_file_in_snapshots_not_found(config, initialized_snapshots):
    """Test finding non-existent file."""
    results = find_file_in_snapshots(
        "nonexistent.txt",
        Path(config.target_base),
        config.dirs,
    )

    assert len(results) == 0


def test_format_file_listing(config, initialized_snapshots, sample_snapshot):
    """Test formatting file listing."""
    results = find_file_in_snapshots(
        "file1.txt",
        Path(config.target_base),
        config.dirs,
    )

    formatted = format_file_listing(results, Path(config.target_base))

    assert len(formatted) > 0
    # Should contain snapshot name, size, and path
    assert all("|" in line for line in formatted)


def test_get_file_from_snapshot(config, initialized_snapshots, sample_snapshot):
    """Test getting file from N periods ago."""
    file_path = get_file_from_snapshot(
        "file1.txt",
        0,  # Current (hour-0)
        Path(config.target_base),
        config.dirs,
    )

    assert file_path is not None
    assert file_path.exists()
    assert file_path.name == "file1.txt"


def test_get_file_from_snapshot_not_found(config, initialized_snapshots):
    """Test getting non-existent file."""
    file_path = get_file_from_snapshot(
        "nonexistent.txt",
        0,
        Path(config.target_base),
        config.dirs,
    )

    assert file_path is None


def test_get_file_from_snapshot_out_of_range(
    config, initialized_snapshots, sample_snapshot
):
    """Test getting file with periods_ago out of range."""
    file_path = get_file_from_snapshot(
        "file1.txt",
        100,  # Far more than available snapshots
        Path(config.target_base),
        config.dirs,
    )

    assert file_path is None


def test_expand_path(temp_dir, monkeypatch):
    """Test path expansion."""
    monkeypatch.setenv("HOME", str(temp_dir))
    monkeypatch.setenv("TESTVAR", "test_value")

    # Test ~ expansion
    path = expand_path("~/test")
    assert str(temp_dir) in str(path)

    # Test environment variable expansion
    path = expand_path("$TESTVAR/test")
    assert "test_value" in str(path)


def test_is_standard_snapshot():
    """Test checking if snapshot is standard."""
    assert is_standard_snapshot("hour-0")
    assert is_standard_snapshot("day-5")
    assert is_standard_snapshot("week-2")
    assert is_standard_snapshot("month-10")
    assert not is_standard_snapshot("my-tag")
    assert not is_standard_snapshot("before-upgrade")
    assert not is_standard_snapshot("invalid")


def test_parse_snapshot_name():
    """Test parsing snapshot names."""
    assert parse_snapshot_name("hour-5") == ("hour", 5)
    assert parse_snapshot_name("day-3") == ("day", 3)
    assert parse_snapshot_name("week-1") == ("week", 1)
    assert parse_snapshot_name("month-0") == ("month", 0)
    assert parse_snapshot_name("invalid") is None
    assert parse_snapshot_name("my-tag") is None


def test_get_snapshot_age_description():
    """Test getting human-readable age descriptions."""
    assert get_snapshot_age_description("hour-0") == "current"
    assert "hour" in get_snapshot_age_description("hour-1")
    assert "hours" in get_snapshot_age_description("hour-5")

    assert "yesterday" in get_snapshot_age_description("day-0")
    assert "days" in get_snapshot_age_description("day-3")

    assert "week" in get_snapshot_age_description("week-0")
    assert "weeks" in get_snapshot_age_description("week-2")

    assert "month" in get_snapshot_age_description("month-0")
    assert "months" in get_snapshot_age_description("month-5")

    # Tagged snapshots return as-is
    assert get_snapshot_age_description("my-tag") == "my-tag"


def test_find_file_in_snapshots_multiple_locations(
    config, initialized_snapshots, sample_snapshot
):
    """Test finding file that exists in multiple snapshots."""
    base = Path(config.target_base)

    # Create the same file in multiple snapshots
    for i in range(3):
        snapshot_dir = base / f"hour-{i}"
        for source_dir in config.dirs:
            source_path = Path(source_dir)
            target_file = snapshot_dir / source_path.name / "common.txt"
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(f"content {i}")

    results = find_file_in_snapshots(
        "common.txt",
        base,
        config.dirs,
    )

    # Should find file in multiple snapshots
    assert len(results) >= 3


def test_sort_snapshots_by_age_with_tags():
    """Test sorting snapshots with tagged snapshots."""
    snapshots = [
        "my-tag",
        "hour-0",
        "day-1",
        "before-upgrade",
        "week-0",
    ]

    sorted_snapshots = sort_snapshots_by_age(snapshots)

    # Standard snapshots should come first (sorted by age)
    # Tags should come last
    standard = [s for s in sorted_snapshots if is_standard_snapshot(s)]
    tags = [s for s in sorted_snapshots if not is_standard_snapshot(s)]

    assert len(standard) == 3
    assert len(tags) == 2
