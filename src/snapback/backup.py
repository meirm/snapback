"""Backup operations for snapback.

This module handles rsync-based backup operations to create snapshots.
"""

import subprocess
from pathlib import Path
from typing import Optional

from .config import Config
from .snapshot import SnapshotManager
from .utils import validate_workspace_path


class BackupManager:
    """Manages backup operations using rsync."""

    def __init__(self, config: Config):
        """Initialize the backup manager.

        Args:
            config: Configuration object with backup settings
        """
        self.config = config
        self.snapshot_manager = SnapshotManager(config)
        self.base_dir = Path(config.target_base)

    @property
    def workspace_root(self) -> Optional[Path]:
        """Get workspace root in local mode.

        Returns:
            Workspace root path if in local mode, None otherwise
        """
        if self.config.is_local and self.config.config_path:
            return Path(self.config.config_path).parent.resolve()
        return None

    def run_rsync(
        self,
        source: str,
        target: Path,
        dry_run: bool = False,
        delete: bool = False,
        ignore_existing: bool = False,
    ) -> subprocess.CompletedProcess:
        """Run rsync to backup a directory.

        Args:
            source: Source directory path
            target: Target directory path
            dry_run: If True, run rsync with --dry-run flag
            delete: If True, delete files in target that don't exist in source
            ignore_existing: If True, skip files that already exist in target

        Returns:
            CompletedProcess object from subprocess.run

        Raises:
            subprocess.CalledProcessError: If rsync fails
        """
        # Base rsync command with common options
        cmd = [
            "rsync",
            "-a",  # archive mode (preserves permissions, timestamps, etc.)
            "-v",  # verbose
        ]

        # Validate source and target are within workspace in local mode
        # Only validate if we have a valid workspace_root (config has config_path set)
        if self.workspace_root and self.config.config_path:
            validate_workspace_path(Path(source), self.workspace_root, "backup source")
            validate_workspace_path(target, self.workspace_root, "backup target")

        # Add optional flags
        if dry_run:
            cmd.append("--dry-run")

        if delete:
            cmd.append("--delete")

        if ignore_existing:
            cmd.append("--ignore-existing")

        # In project-local mode, add gitignore filtering and default exclusions
        if self.config.is_local:
            # Respect .gitignore patterns
            cmd.append("--filter=:- .gitignore")
            # Always exclude .git and .snapshots directories
            cmd.append("--exclude=.git")
            cmd.append("--exclude=.snapshots")

        # Add custom rsync parameters from config
        if self.config.rsync_params:
            cmd.extend(self.config.rsync_params.split())

        # Add source and target
        # Ensure source ends with / to sync contents, not the directory itself
        if not source.endswith("/"):
            source = f"{source}/"

        cmd.extend([source, str(target)])

        # Run rsync
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        return result

    def hourly_backup(self, dry_run: bool = False) -> None:
        """Perform an hourly backup.

        This is the main backup operation that:
        1. Rotates existing hourly snapshots
        2. Creates hour-0 by hard-linking from hour-1
        3. Runs rsync to update hour-0 with current data

        Args:
            dry_run: If True, only print what would be done
        """
        hour_0 = self.base_dir / "hour-0"
        hour_1 = self.base_dir / "hour-1"

        if dry_run:
            print("DRY RUN: Hourly backup")

        # Rotate hourly snapshots
        self.snapshot_manager.rotate_hourly(dry_run=dry_run)

        if dry_run:
            print(f"DRY RUN: Would create hard-link copy: {hour_1} -> {hour_0}")
            for source_dir in self.config.dirs:
                print(f"DRY RUN: Would rsync {source_dir} to {hour_0}")
            return

        # Create hour-0 by hard-linking from hour-1 (if it exists)
        if hour_1.exists():
            self.snapshot_manager.create_hard_link_copy(hour_1, hour_0)
        else:
            # First run - create hour-0
            hour_0.mkdir(parents=True, exist_ok=True)

        # Run rsync for each source directory
        for source_dir in self.config.dirs:
            source_path = Path(source_dir).expanduser()
            if not source_path.exists():
                print(f"Warning: Source directory does not exist: {source_dir}")
                continue

            # Validate source directory is within workspace in local mode
            # Only validate if we have a valid workspace_root (config has config_path set)
            if self.workspace_root and self.config.config_path:
                try:
                    validate_workspace_path(source_path, self.workspace_root, "backup source directory")
                except ValueError as e:
                    print(f"Error: {e}")
                    continue

            # Create target subdirectory in hour-0
            # Use the directory name as the target subdirectory
            target_subdir = hour_0 / source_path.name
            target_subdir.mkdir(parents=True, exist_ok=True)

            try:
                self.run_rsync(
                    source=str(source_path),
                    target=target_subdir,
                    dry_run=False,
                    delete=True,  # Delete files in target that don't exist in source
                )
            except subprocess.CalledProcessError as e:
                print(f"Error backing up {source_dir}: {e}")
                continue

        print(f"Hourly backup completed to {hour_0}")

    def daily_backup(self, dry_run: bool = False) -> None:
        """Rotate to daily snapshot.

        This should be run at the end of the day (23:58) to promote
        hour-23 to day-0.

        Args:
            dry_run: If True, only print what would be done
        """
        self.snapshot_manager.rotate_daily(dry_run=dry_run)
        if not dry_run:
            print("Daily rotation completed")

    def weekly_backup(self, dry_run: bool = False) -> None:
        """Rotate to weekly snapshot.

        This should be run weekly (e.g., Monday 22:56) to promote
        day-7 to week-0.

        Args:
            dry_run: If True, only print what would be done
        """
        self.snapshot_manager.rotate_weekly(dry_run=dry_run)
        if not dry_run:
            print("Weekly rotation completed")

    def monthly_backup(self, dry_run: bool = False) -> None:
        """Rotate to monthly snapshot.

        This should be run monthly (e.g., 1st of month 01:00) to promote
        week-4 to month-0.

        Args:
            dry_run: If True, only print what would be done
        """
        self.snapshot_manager.rotate_monthly(dry_run=dry_run)
        if not dry_run:
            print("Monthly rotation completed")
