"""Recovery operations for snapback.

This module handles file recovery, snapshot tagging, and deletion operations.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .config import Config
from .snapshot import SnapshotManager


class RecoveryManager:
    """Manages recovery and snapshot manipulation operations."""

    def __init__(self, config: Config):
        """Initialize the recovery manager.

        Args:
            config: Configuration object with snapshot settings
        """
        self.config = config
        self.snapshot_manager = SnapshotManager(config)
        self.base_dir = Path(config.target_base)

    def recover(self, snapshot_name: str, dry_run: bool = False) -> None:
        """Perform a full recovery from a snapshot.

        This operation restores all backed-up directories from the specified
        snapshot, overwriting current files.

        Args:
            snapshot_name: Name of the snapshot to recover from (e.g., 'hour-1')
            dry_run: If True, only print what would be done

        Raises:
            FileNotFoundError: If the snapshot doesn't exist
        """
        snapshot_path = self.snapshot_manager.get_snapshot_path(snapshot_name)

        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot does not exist: {snapshot_name}")

        if dry_run:
            print(f"DRY RUN: Would recover from {snapshot_path}")

        # Recover each backed-up directory
        for source_dir in self.config.dirs:
            source_path = Path(source_dir).expanduser()
            snapshot_subdir = snapshot_path / source_path.name

            if not snapshot_subdir.exists():
                print(f"Warning: Snapshot subdirectory not found: {snapshot_subdir}")
                continue

            if dry_run:
                print(f"DRY RUN: Would rsync {snapshot_subdir} to {source_path}")
                continue

            # Ensure target directory exists
            source_path.parent.mkdir(parents=True, exist_ok=True)

            # Run rsync to restore files
            try:
                cmd = [
                    "rsync",
                    "-a",
                    "-v",
                    "--delete",  # Delete files not in snapshot
                    f"{snapshot_subdir}/",
                    str(source_path),
                ]
                print(f"Running: {' '.join(cmd)}")
                subprocess.run(cmd, check=True)
                print(f"Recovered {source_path} from {snapshot_name}")
            except subprocess.CalledProcessError as e:
                print(f"Error recovering {source_dir}: {e}")

    def undel(self, snapshot_name: str, dry_run: bool = False) -> None:
        """Recover only deleted files from a snapshot.

        This operation restores files that exist in the snapshot but not in
        the current directories. Existing files are not overwritten.

        Args:
            snapshot_name: Name of the snapshot to recover from (e.g., 'hour-1')
            dry_run: If True, only print what would be done

        Raises:
            FileNotFoundError: If the snapshot doesn't exist
        """
        snapshot_path = self.snapshot_manager.get_snapshot_path(snapshot_name)

        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot does not exist: {snapshot_name}")

        if dry_run:
            print(f"DRY RUN: Would undelete from {snapshot_path}")

        # Recover each backed-up directory
        for source_dir in self.config.dirs:
            source_path = Path(source_dir).expanduser()
            snapshot_subdir = snapshot_path / source_path.name

            if not snapshot_subdir.exists():
                print(f"Warning: Snapshot subdirectory not found: {snapshot_subdir}")
                continue

            if dry_run:
                print(
                    f"DRY RUN: Would rsync (ignore-existing) {snapshot_subdir} to {source_path}"
                )
                continue

            # Ensure target directory exists
            source_path.parent.mkdir(parents=True, exist_ok=True)

            # Run rsync with --ignore-existing to only restore deleted files
            try:
                cmd = [
                    "rsync",
                    "-a",
                    "-v",
                    "--ignore-existing",  # Skip files that already exist
                    f"{snapshot_subdir}/",
                    str(source_path),
                ]
                print(f"Running: {' '.join(cmd)}")
                subprocess.run(cmd, check=True)
                print(f"Undeleted files to {source_path} from {snapshot_name}")
            except subprocess.CalledProcessError as e:
                print(f"Error undeleting {source_dir}: {e}")

    def tag(self, snapshot_name: str, tag_name: str, dry_run: bool = False) -> None:
        """Create a named tag for a snapshot.

        This creates a copy of the snapshot with a custom name for preservation.

        Args:
            snapshot_name: Name of the snapshot to tag (e.g., 'hour-1')
            tag_name: Custom name for the tagged snapshot
            dry_run: If True, only print what would be done

        Raises:
            FileNotFoundError: If the snapshot doesn't exist
            FileExistsError: If the tag name already exists
        """
        snapshot_path = self.snapshot_manager.get_snapshot_path(snapshot_name)
        tag_path = self.base_dir / tag_name

        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot does not exist: {snapshot_name}")

        if tag_path.exists():
            raise FileExistsError(f"Tag already exists: {tag_name}")

        if dry_run:
            print(f"DRY RUN: Would create tag {tag_name} from {snapshot_name}")
            return

        # Create hard-link copy with the tag name
        self.snapshot_manager.create_hard_link_copy(snapshot_path, tag_path)
        print(f"Created tag '{tag_name}' from {snapshot_name}")

    def delete_path(self, path: str, dry_run: bool = False) -> None:
        """Delete a specific path from the hour-0 snapshot.

        This is useful for removing files from backups that shouldn't be backed up.

        Args:
            path: Path to delete from hour-0 (relative or absolute)
            dry_run: If True, only print what would be done

        Raises:
            FileNotFoundError: If hour-0 doesn't exist
        """
        hour_0 = self.base_dir / "hour-0"

        if not hour_0.exists():
            raise FileNotFoundError("hour-0 snapshot does not exist")

        # Convert path to Path object and resolve
        target_path = Path(path).expanduser()

        # Find the corresponding path in hour-0
        # The path in hour-0 is: hour-0/<source_dir_name>/<relative_path>
        deleted = False
        for source_dir in self.config.dirs:
            source_path = Path(source_dir).expanduser()

            # Check if the target path is under this source directory
            try:
                rel_path = target_path.relative_to(source_path)
            except ValueError:
                # Not under this source directory
                continue

            # Find the file in hour-0
            hour_0_path = hour_0 / source_path.name / rel_path

            if not hour_0_path.exists():
                print(f"Warning: Path not found in hour-0: {hour_0_path}")
                continue

            if dry_run:
                print(f"DRY RUN: Would delete {hour_0_path}")
                continue

            # Delete the path
            if hour_0_path.is_dir():
                shutil.rmtree(hour_0_path)
            else:
                hour_0_path.unlink()

            print(f"Deleted from hour-0: {hour_0_path}")
            deleted = True
            break

        if not deleted and not dry_run:
            print(f"Warning: Could not find {path} in any backed-up directory")

    def list_tagged_snapshots(self) -> list[str]:
        """List all tagged snapshots.

        Returns:
            List of tag names (snapshot names that don't match the standard patterns)
        """
        if not self.base_dir.exists():
            return []

        tags = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and not (
                item.name.startswith("hour-")
                or item.name.startswith("day-")
                or item.name.startswith("week-")
                or item.name.startswith("month-")
            ):
                tags.append(item.name)

        return sorted(tags)

    def delete_tag(self, tag_name: str, dry_run: bool = False) -> None:
        """Delete a tagged snapshot.

        Args:
            tag_name: Name of the tag to delete
            dry_run: If True, only print what would be done

        Raises:
            FileNotFoundError: If the tag doesn't exist
        """
        tag_path = self.base_dir / tag_name

        if not tag_path.exists():
            raise FileNotFoundError(f"Tag does not exist: {tag_name}")

        # Don't allow deleting standard snapshots
        if (
            tag_name.startswith("hour-")
            or tag_name.startswith("day-")
            or tag_name.startswith("week-")
            or tag_name.startswith("month-")
        ):
            raise ValueError(
                f"Cannot delete standard snapshot: {tag_name}. Use rotation commands instead."
            )

        if dry_run:
            print(f"DRY RUN: Would delete tag {tag_name}")
            return

        shutil.rmtree(tag_path)
        print(f"Deleted tag: {tag_name}")
