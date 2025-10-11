"""Utility functions for snapback.

This module provides utility functions for finding files, sorting snapshots,
and other helper operations.
"""

import os
import re
import shutil
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


def is_safe_workspace_path(path: Path, workspace_root: Path) -> bool:
    """Check if a path is within workspace boundaries.

    Args:
        path: Path to check
        workspace_root: Workspace root directory

    Returns:
        True if path is within workspace_root, False otherwise
    """
    try:
        # Resolve both paths to handle symlinks and normalize
        resolved_path = path.resolve()
        resolved_workspace = workspace_root.resolve()

        # Check if the path is within the workspace
        resolved_path.relative_to(resolved_workspace)
        return True
    except (ValueError, RuntimeError, OSError):
        # ValueError: path is not relative to workspace
        # RuntimeError: infinite loop in symlink resolution
        # OSError: permission issues or broken symlinks
        return False


def is_dangerous_targetbase(path: str, is_local: bool) -> tuple[bool, str]:
    """Check if a TARGETBASE path is dangerous.

    Args:
        path: TARGETBASE path to check
        is_local: True if in project-local mode

    Returns:
        Tuple of (is_dangerous, reason) where is_dangerous is True if path
        is unsafe, and reason explains why
    """
    # System directories that should never be used as TARGETBASE
    system_dirs = {
        "/",
        "/home",
        "/usr",
        "/etc",
        "/var",
        "/tmp",
        "/boot",
        "/sys",
        "/proc",
        "/dev",
        "/bin",
        "/sbin",
        "/lib",
        "/lib64",
        "/opt",
        "/root",
        "/run",
        "/srv",
        "/mnt",
        "/media",
    }

    # Expand path to handle ~ and environment variables
    expanded = expand_path(path)
    try:
        # Try to resolve, but allow non-existent paths (they might be created later)
        if expanded.exists():
            resolved = expanded.resolve()
        else:
            # For non-existent paths, use absolute path without resolving symlinks
            resolved = expanded.absolute()
    except (RuntimeError, OSError):
        # Can't resolve path (infinite symlink loop, permission issues, etc.)
        return (True, f"Path cannot be resolved: {path}")

    # Check if it's a system directory (use both resolved path and original expanded path)
    resolved_str = str(resolved)
    if resolved_str in system_dirs or str(expanded.absolute()) in system_dirs:
        return (True, f"Cannot use system directory: {path}")

    # Check if it's the user's home directory root
    home_dir = Path.home().resolve()
    if resolved == home_dir:
        return (True, f"Cannot use home directory root. Use a subdirectory like '{home_dir}/.Snapshots'")

    # In local mode, check for parent directory references
    if is_local:
        # Check if path contains .. components (before resolution)
        path_parts = Path(path).parts
        if ".." in path_parts:
            return (True, f"Parent directory references (..) not allowed in local mode. Use './.snapshots' instead")

        # Check if it's an absolute path pointing outside workspace
        # Note: This check is done in config validation with workspace context
        if os.path.isabs(path):
            return (True, f"Absolute paths not recommended in local mode. Use relative path like './.snapshots'")

    return (False, "")


def safe_rmtree(path: Path, workspace_root: Optional[Path] = None) -> None:
    """Safely remove a directory tree without following symlinks.

    Args:
        path: Directory path to remove
        workspace_root: Optional workspace root for boundary validation

    Raises:
        ValueError: If path is outside workspace (when workspace_root is provided)
        FileNotFoundError: If path doesn't exist
    """
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    # Validate workspace boundaries if provided
    if workspace_root is not None:
        if not is_safe_workspace_path(path, workspace_root):
            raise ValueError(
                f"Path is outside workspace boundaries: {path} "
                f"(workspace: {workspace_root})"
            )

    # Use shutil.rmtree with onerror callback to handle symlinks safely
    def handle_remove_readonly(func, path_str, exc):
        """Error handler for read-only files."""
        # If it's a permission error, try to make writable and retry
        if isinstance(exc[1], PermissionError):
            os.chmod(path_str, 0o700)
            func(path_str)
        else:
            raise

    # Remove the directory tree
    # Note: shutil.rmtree already doesn't follow symlinks by default
    # It removes symlinks themselves without following them
    shutil.rmtree(path, onerror=handle_remove_readonly)


def validate_workspace_path(path: Path, workspace_root: Path, operation: str) -> None:
    """Validate that a path is safe for operations in local mode.

    Args:
        path: Path to validate
        workspace_root: Workspace root directory
        operation: Description of operation (for error messages)

    Raises:
        ValueError: If path is unsafe or outside workspace boundaries
    """
    # Check for path traversal attempts using .. components
    try:
        path_str = str(path)
        if ".." in Path(path_str).parts:
            raise ValueError(
                f"Path traversal (..) not allowed in {operation}: {path}. "
                f"All paths must be within workspace: {workspace_root}"
            )
    except (ValueError, RuntimeError):
        raise ValueError(f"Invalid path for {operation}: {path}")

    # Check workspace boundaries
    if not is_safe_workspace_path(path, workspace_root):
        raise ValueError(
            f"Path is outside workspace for {operation}: {path}. "
            f"In local mode, all operations must stay within: {workspace_root}"
        )
