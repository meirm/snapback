"""Utility functions for snapback.

This module provides utility functions for finding files, sorting snapshots,
and other helper operations.
"""

import os
import re
from pathlib import Path
from typing import Optional


def snapshot_to_hours(snapshot_name: str) -> int:
    """Convert a snapshot name to hours for sorting.

    This matches the logic from the original snapls.sh Perl script.

    The conversion considers that:
    - hour-N represents N hours ago
    - day-0 is yesterday's end-of-day (24 hours ago)
    - week-0 is last week's end-of-week (7 days ago)
    - month-0 is last month's end-of-month (30 days ago)

    Args:
        snapshot_name: Name of the snapshot (e.g., 'hour-1', 'day-3', 'week-2')

    Returns:
        Number of hours represented by the snapshot
    """
    # Extract period type and number
    match = re.match(r"(hour|day|week|month)-(\d+)", snapshot_name)
    if not match:
        # Not a standard snapshot name, return high value to sort last
        return 999999

    period_type, number_str = match.groups()
    number = int(number_str)

    # Convert to hours
    # Note: For day/week/month snapshots, index 0 represents the most recent
    # full period (yesterday, last week, last month), so we add 1 to the count
    if period_type == "hour":
        return number
    elif period_type == "day":
        return (number + 1) * 24  # day-0 is 24 hours ago (yesterday)
    elif period_type == "week":
        return (number + 1) * 24 * 7  # week-0 is 7 days ago
    elif period_type == "month":
        return (number + 1) * 24 * 30  # month-0 is 30 days ago

    return 999999


def sort_snapshots_by_age(snapshots: list[str]) -> list[str]:
    """Sort snapshots by age (newest first).

    Args:
        snapshots: List of snapshot names

    Returns:
        Sorted list of snapshot names (newest to oldest)
    """
    return sorted(snapshots, key=snapshot_to_hours)


def find_file_in_snapshots(
    filename: str, base_dir: Path, source_dirs: list[str]
) -> list[tuple[str, Path]]:
    """Find all occurrences of a file in snapshots.

    This implements the functionality of snapls.sh.

    Args:
        filename: Name of the file to search for
        base_dir: Base directory containing snapshots
        source_dirs: List of source directories that are backed up

    Returns:
        List of tuples (snapshot_name, file_path) sorted by age
    """
    if not base_dir.exists():
        return []

    results = []

    # Get all snapshots (including tagged ones)
    for snapshot_dir in base_dir.iterdir():
        if not snapshot_dir.is_dir():
            continue

        # Search in each source directory within the snapshot
        for source_dir in source_dirs:
            source_path = Path(source_dir).expanduser()
            snapshot_subdir = snapshot_dir / source_path.name

            if not snapshot_subdir.exists():
                continue

            # Walk through the snapshot subdirectory
            for root, dirs, files in os.walk(snapshot_subdir):
                if filename in files:
                    file_path = Path(root) / filename
                    results.append((snapshot_dir.name, file_path))

    # Sort by age (newest first)
    results.sort(key=lambda x: snapshot_to_hours(x[0]))

    return results


def format_file_listing(
    results: list[tuple[str, Path]], base_dir: Path
) -> list[str]:
    """Format file listing for display.

    Args:
        results: List of tuples (snapshot_name, file_path)
        base_dir: Base directory containing snapshots

    Returns:
        List of formatted strings for display
    """
    formatted = []

    for snapshot_name, file_path in results:
        # Get file stats
        try:
            stat = file_path.stat()
            size = stat.st_size
            # Format size in human-readable format
            if size < 1024:
                size_str = f"{size}B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f}K"
            elif size < 1024 * 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f}M"
            else:
                size_str = f"{size / (1024 * 1024 * 1024):.1f}G"

            # Format: snapshot_name | size | path
            formatted.append(f"{snapshot_name:15s} | {size_str:>10s} | {file_path}")
        except (OSError, FileNotFoundError):
            formatted.append(f"{snapshot_name:15s} | {'?':>10s} | {file_path}")

    return formatted


def get_file_from_snapshot(
    filename: str, periods_ago: int, base_dir: Path, source_dirs: list[str]
) -> Optional[Path]:
    """Get a file from N periods ago.

    This implements the functionality needed for snapdiff.sh.

    Args:
        filename: Name of the file to find
        periods_ago: Number of snapshots to go back (0 = current hour-0)
        base_dir: Base directory containing snapshots
        source_dirs: List of source directories that are backed up

    Returns:
        Path to the file in the snapshot, or None if not found
    """
    # Find all occurrences of the file
    results = find_file_in_snapshots(filename, base_dir, source_dirs)

    if not results:
        return None

    # Check if we have enough snapshots
    if periods_ago >= len(results):
        return None

    # Return the Nth result (sorted by age, newest first)
    return results[periods_ago][1]


def expand_path(path: str) -> Path:
    """Expand a path with user home directory and environment variables.

    Args:
        path: Path string that may contain ~ or environment variables

    Returns:
        Expanded Path object
    """
    return Path(os.path.expandvars(os.path.expanduser(path)))


def is_standard_snapshot(snapshot_name: str) -> bool:
    """Check if a snapshot name is a standard snapshot (not a tag).

    Args:
        snapshot_name: Name of the snapshot

    Returns:
        True if the snapshot is a standard hourly/daily/weekly/monthly snapshot
    """
    return bool(
        re.match(r"^(hour|day|week|month)-\d+$", snapshot_name)
    )


def parse_snapshot_name(snapshot_name: str) -> Optional[tuple[str, int]]:
    """Parse a snapshot name into period type and number.

    Args:
        snapshot_name: Name of the snapshot (e.g., 'hour-1', 'day-3')

    Returns:
        Tuple of (period_type, number) or None if invalid
    """
    match = re.match(r"^(hour|day|week|month)-(\d+)$", snapshot_name)
    if not match:
        return None

    period_type, number_str = match.groups()
    return (period_type, int(number_str))


def get_snapshot_age_description(snapshot_name: str) -> str:
    """Get a human-readable description of a snapshot's age.

    Args:
        snapshot_name: Name of the snapshot

    Returns:
        Human-readable age description
    """
    parsed = parse_snapshot_name(snapshot_name)
    if not parsed:
        return snapshot_name  # Tagged snapshot, return as-is

    period_type, number = parsed

    if period_type == "hour":
        if number == 0:
            return "current"
        elif number == 1:
            return "1 hour ago"
        else:
            return f"{number} hours ago"
    elif period_type == "day":
        if number == 0:
            return "yesterday (end of day)"
        elif number == 1:
            return "2 days ago"
        else:
            return f"{number + 1} days ago"
    elif period_type == "week":
        if number == 0:
            return "last week"
        elif number == 1:
            return "2 weeks ago"
        else:
            return f"{number + 1} weeks ago"
    elif period_type == "month":
        if number == 0:
            return "last month"
        elif number == 1:
            return "2 months ago"
        else:
            return f"{number + 1} months ago"

    return snapshot_name
