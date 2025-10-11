"""Snapshot management for snapback.

This module handles the creation, rotation, and initialization of snapshots
across four tiers: hourly, daily, weekly, and monthly.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .config import Config
from .utils import safe_rmtree


class SnapshotManager:
    """Manages snapshot operations including rotation and initialization."""

    def __init__(self, config: Config):
        """Initialize the snapshot manager.

        Args:
            config: Configuration object with snapshot settings
        """
        self.config = config
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

    def init_snapshots(self) -> None:
        """Initialize the complete snapshot directory structure.

        Creates the full hierarchy:
        - hour-0 through hour-23
        - day-0 through day-7
        - week-0 through week-4
        - month-0 through month-12
        """
        # Create base directory
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Create hourly snapshots
        for i in range(24):
            (self.base_dir / f"hour-{i}").mkdir(exist_ok=True)

        # Create daily snapshots
        for i in range(8):
            (self.base_dir / f"day-{i}").mkdir(exist_ok=True)

        # Create weekly snapshots
        for i in range(5):
            (self.base_dir / f"week-{i}").mkdir(exist_ok=True)

        # Create monthly snapshots
        for i in range(13):
            (self.base_dir / f"month-{i}").mkdir(exist_ok=True)

    def create_hard_link_copy(self, src: Path, dst: Path) -> None:
        """Create a hard-link copy of a directory tree.

        This is equivalent to `cp -al src dst` in the original Bash script.
        Only new files consume disk space; unchanged files are hard-linked.

        Args:
            src: Source directory path
            dst: Destination directory path
        """
        if not src.exists():
            raise FileNotFoundError(f"Source directory does not exist: {src}")

        # Create destination directory
        dst.mkdir(parents=True, exist_ok=True)

        # Walk through source directory without following symlinks
        for root, dirs, files in os.walk(src, followlinks=False):
            src_root = Path(root)
            rel_path = src_root.relative_to(src)
            dst_root = dst / rel_path

            # Create directories
            for dir_name in dirs:
                (dst_root / dir_name).mkdir(exist_ok=True)

            # Create hard links for files
            for file_name in files:
                src_file = src_root / file_name
                dst_file = dst_root / file_name

                # Remove destination if it exists
                if dst_file.exists():
                    dst_file.unlink()

                try:
                    # Create hard link
                    os.link(src_file, dst_file)
                except (OSError, PermissionError) as e:
                    # If hard link fails, copy the file
                    print(f"Warning: Could not hard link {src_file}, copying instead: {e}")
                    shutil.copy2(src_file, dst_file)

    def rotate_hourly(self, dry_run: bool = False) -> None:
        """Rotate hourly snapshots.

        hour-23 is deleted, hour-22 becomes hour-23, ..., hour-0 becomes hour-1.
        A new hour-0 will be created by the backup operation.

        Args:
            dry_run: If True, only print what would be done
        """
        if dry_run:
            print("DRY RUN: Would rotate hourly snapshots")
            for i in range(23, 0, -1):
                print(f"  {self.base_dir}/hour-{i-1} -> {self.base_dir}/hour-{i}")
            return

        # Delete oldest snapshot (hour-23)
        hour_23 = self.base_dir / "hour-23"
        if hour_23.exists():
            safe_rmtree(hour_23, self.workspace_root)

        # Rotate snapshots (in reverse order to avoid overwriting)
        for i in range(22, -1, -1):
            src = self.base_dir / f"hour-{i}"
            dst = self.base_dir / f"hour-{i+1}"
            if src.exists():
                src.rename(dst)

    def rotate_daily(self, dry_run: bool = False) -> None:
        """Rotate daily snapshots.

        hour-23 becomes day-0, day-7 is promoted to weekly rotation,
        and intermediate days shift up.

        Args:
            dry_run: If True, only print what would be done
        """
        if dry_run:
            print("DRY RUN: Would rotate daily snapshots")
            print(f"  {self.base_dir}/day-7 -> weekly rotation")
            for i in range(6, -1, -1):
                print(f"  {self.base_dir}/day-{i} -> {self.base_dir}/day-{i+1}")
            print(f"  {self.base_dir}/hour-23 -> {self.base_dir}/day-0")
            return

        # Promote day-7 to weekly (handled by weekly rotation)
        # Delete day-7 if weekly rotation hasn't consumed it
        day_7 = self.base_dir / "day-7"
        if day_7.exists() and not (self.base_dir / "week-0").exists():
            # Create week-0 from day-7
            day_7.rename(self.base_dir / "week-0")
        elif day_7.exists():
            safe_rmtree(day_7, self.workspace_root)

        # Rotate daily snapshots (in reverse order)
        for i in range(6, -1, -1):
            src = self.base_dir / f"day-{i}"
            dst = self.base_dir / f"day-{i+1}"
            if src.exists():
                src.rename(dst)

        # Promote hour-23 to day-0
        hour_23 = self.base_dir / "hour-23"
        if hour_23.exists():
            hour_23.rename(self.base_dir / "day-0")

    def rotate_weekly(self, dry_run: bool = False) -> None:
        """Rotate weekly snapshots.

        day-7 becomes week-0, week-4 is promoted to monthly rotation,
        and intermediate weeks shift up.

        Args:
            dry_run: If True, only print what would be done
        """
        if dry_run:
            print("DRY RUN: Would rotate weekly snapshots")
            print(f"  {self.base_dir}/week-4 -> monthly rotation")
            for i in range(3, -1, -1):
                print(f"  {self.base_dir}/week-{i} -> {self.base_dir}/week-{i+1}")
            print(f"  {self.base_dir}/day-7 -> {self.base_dir}/week-0")
            return

        # Promote week-4 to monthly (handled by monthly rotation)
        # Delete week-4 if monthly rotation hasn't consumed it
        week_4 = self.base_dir / "week-4"
        if week_4.exists() and not (self.base_dir / "month-0").exists():
            # Create month-0 from week-4
            week_4.rename(self.base_dir / "month-0")
        elif week_4.exists():
            safe_rmtree(week_4, self.workspace_root)

        # Rotate weekly snapshots (in reverse order)
        for i in range(3, -1, -1):
            src = self.base_dir / f"week-{i}"
            dst = self.base_dir / f"week-{i+1}"
            if src.exists():
                src.rename(dst)

        # Promote day-7 to week-0 using hard links
        day_7 = self.base_dir / "day-7"
        if day_7.exists():
            # Use cp -al equivalent (hard link copy) instead of mv
            # This preserves day-7 for the daily rotation
            week_0 = self.base_dir / "week-0"
            if week_0.exists():
                safe_rmtree(week_0, self.workspace_root)
            self.create_hard_link_copy(day_7, week_0)

    def rotate_monthly(self, dry_run: bool = False) -> None:
        """Rotate monthly snapshots.

        week-4 becomes month-0, month-12 is deleted,
        and intermediate months shift up.

        Args:
            dry_run: If True, only print what would be done
        """
        if dry_run:
            print("DRY RUN: Would rotate monthly snapshots")
            print(f"  Deleting {self.base_dir}/month-12")
            for i in range(11, -1, -1):
                print(f"  {self.base_dir}/month-{i} -> {self.base_dir}/month-{i+1}")
            print(f"  {self.base_dir}/week-4 -> {self.base_dir}/month-0")
            return

        # Delete oldest snapshot (month-12)
        month_12 = self.base_dir / "month-12"
        if month_12.exists():
            safe_rmtree(month_12, self.workspace_root)

        # Rotate monthly snapshots (in reverse order)
        for i in range(11, -1, -1):
            src = self.base_dir / f"month-{i}"
            dst = self.base_dir / f"month-{i+1}"
            if src.exists():
                src.rename(dst)

        # Promote week-4 to month-0
        week_4 = self.base_dir / "week-4"
        if week_4.exists():
            week_4.rename(self.base_dir / "month-0")

    def snapshot_exists(self, snapshot_name: str) -> bool:
        """Check if a snapshot exists.

        Args:
            snapshot_name: Name of the snapshot (e.g., 'hour-1', 'day-0')

        Returns:
            True if the snapshot directory exists
        """
        return (self.base_dir / snapshot_name).exists()

    def get_snapshot_path(self, snapshot_name: str) -> Path:
        """Get the full path to a snapshot.

        Args:
            snapshot_name: Name of the snapshot (e.g., 'hour-1', 'day-0')

        Returns:
            Path object for the snapshot directory
        """
        return self.base_dir / snapshot_name

    def list_snapshots(self) -> list[str]:
        """List all available snapshots.

        Returns:
            List of snapshot names (e.g., ['hour-0', 'hour-1', ...])
        """
        if not self.base_dir.exists():
            return []

        snapshots = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and (
                item.name.startswith("hour-")
                or item.name.startswith("day-")
                or item.name.startswith("week-")
                or item.name.startswith("month-")
            ):
                snapshots.append(item.name)

        return sorted(snapshots)
