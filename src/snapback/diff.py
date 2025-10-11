"""File comparison functionality for snapback.

This module provides file comparison capabilities to compare current files
with versions from previous snapshots.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

from .config import Config
from .utils import get_file_from_snapshot


class DiffManager:
    """Manages file comparison operations."""

    def __init__(self, config: Config):
        """Initialize the diff manager.

        Args:
            config: Configuration object with snapshot settings
        """
        self.config = config
        self.base_dir = Path(config.target_base)

    def compare_file_versions(
        self,
        filename: str,
        periods_ago: int = 1,
        diff_tool: str = "vimdiff",
    ) -> bool:
        """Compare a file with its version from N periods ago.

        This implements the functionality of snapdiff.sh.

        Args:
            filename: Path to the file to compare
            periods_ago: Number of snapshots to go back (default: 1)
            diff_tool: Diff tool to use (default: vimdiff)

        Returns:
            True if comparison was successful, False otherwise
        """
        # Expand the filename path
        current_file = Path(filename).expanduser().resolve()

        # Check if current file exists
        if not current_file.exists():
            print(f"Error: File does not exist: {current_file}")
            return False

        # Find the file in the snapshot
        snapshot_file = get_file_from_snapshot(
            current_file.name,
            periods_ago,
            self.base_dir,
            self.config.dirs,
        )

        if not snapshot_file:
            print(
                f"Error: Could not find {current_file.name} in snapshot {periods_ago} periods ago"
            )
            print(f"(Searched in: {self.base_dir})")
            return False

        # Check if snapshot file exists
        if not snapshot_file.exists():
            print(f"Error: Snapshot file no longer exists: {snapshot_file}")
            return False

        print(f"Comparing:")
        print(f"  Current:  {current_file}")
        print(f"  Snapshot: {snapshot_file}")

        # Run the diff tool
        try:
            subprocess.run([diff_tool, str(current_file), str(snapshot_file)])
            return True
        except FileNotFoundError:
            print(f"Error: Diff tool not found: {diff_tool}")
            print("Please install it or specify a different tool with --tool")
            return False
        except subprocess.CalledProcessError as e:
            print(f"Error running diff tool: {e}")
            return False

    def show_file_diff(
        self,
        filename: str,
        periods_ago: int = 1,
        context_lines: int = 3,
    ) -> bool:
        """Show a unified diff of a file compared to N periods ago.

        This provides a simple text-based diff using the diff command.

        Args:
            filename: Path to the file to compare
            periods_ago: Number of snapshots to go back (default: 1)
            context_lines: Number of context lines to show (default: 3)

        Returns:
            True if diff was successful, False otherwise
        """
        # Expand the filename path
        current_file = Path(filename).expanduser().resolve()

        # Check if current file exists
        if not current_file.exists():
            print(f"Error: File does not exist: {current_file}")
            return False

        # Find the file in the snapshot
        snapshot_file = get_file_from_snapshot(
            current_file.name,
            periods_ago,
            self.base_dir,
            self.config.dirs,
        )

        if not snapshot_file:
            print(
                f"Error: Could not find {current_file.name} in snapshot {periods_ago} periods ago"
            )
            return False

        # Check if snapshot file exists
        if not snapshot_file.exists():
            print(f"Error: Snapshot file no longer exists: {snapshot_file}")
            return False

        # Run diff command
        try:
            result = subprocess.run(
                [
                    "diff",
                    f"-U{context_lines}",
                    str(snapshot_file),
                    str(current_file),
                ],
                capture_output=True,
                text=True,
            )

            # diff returns 0 if files are identical, 1 if different, 2 if error
            if result.returncode == 0:
                print("Files are identical")
            elif result.returncode == 1:
                print(f"Diff between {snapshot_file} and {current_file}:")
                print(result.stdout)
            else:
                print(f"Error running diff: {result.stderr}")
                return False

            return True
        except FileNotFoundError:
            print("Error: 'diff' command not found")
            return False

    def list_file_history(self, filename: str) -> bool:
        """List all versions of a file in snapshots.

        Args:
            filename: Name of the file to search for

        Returns:
            True if file was found in any snapshot, False otherwise
        """
        from .utils import find_file_in_snapshots, format_file_listing

        # Search for the file
        results = find_file_in_snapshots(
            filename,
            self.base_dir,
            self.config.dirs,
        )

        if not results:
            print(f"File not found in any snapshot: {filename}")
            return False

        print(f"Found {len(results)} version(s) of '{filename}':")
        print()

        formatted = format_file_listing(results, self.base_dir)
        for line in formatted:
            print(line)

        return True

    def compare_snapshots(
        self,
        snapshot1: str,
        snapshot2: str,
        path: Optional[str] = None,
    ) -> bool:
        """Compare two snapshots or specific paths within them.

        Args:
            snapshot1: Name of the first snapshot
            snapshot2: Name of the second snapshot
            path: Optional path to compare within snapshots

        Returns:
            True if comparison was successful, False otherwise
        """
        snap1_path = self.base_dir / snapshot1
        snap2_path = self.base_dir / snapshot2

        if not snap1_path.exists():
            print(f"Error: Snapshot does not exist: {snapshot1}")
            return False

        if not snap2_path.exists():
            print(f"Error: Snapshot does not exist: {snapshot2}")
            return False

        # If a specific path is provided, compare just that path
        if path:
            snap1_target = snap1_path / path
            snap2_target = snap2_path / path

            if not snap1_target.exists():
                print(f"Error: Path not found in {snapshot1}: {path}")
                return False

            if not snap2_target.exists():
                print(f"Error: Path not found in {snapshot2}: {path}")
                return False
        else:
            snap1_target = snap1_path
            snap2_target = snap2_path

        # Run diff recursively
        try:
            print(f"Comparing {snapshot1} and {snapshot2}:")
            result = subprocess.run(
                [
                    "diff",
                    "-r",
                    "-u",
                    str(snap1_target),
                    str(snap2_target),
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print("Snapshots are identical")
            elif result.returncode == 1:
                print(result.stdout)
            else:
                print(f"Error running diff: {result.stderr}")
                return False

            return True
        except FileNotFoundError:
            print("Error: 'diff' command not found")
            return False
