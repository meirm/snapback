"""
snapback - Space-efficient snapshot-based backup system.

A Python implementation of snapback that uses rsync and hard links to create
space-efficient, incremental backups with multiple retention policies.
"""

# Read version from package metadata (pyproject.toml)
try:
    from importlib.metadata import version
    __version__ = version("snapback")
except Exception:
    # Fallback for development/editable installs where metadata might not be available
    __version__ = "2.0.0"

__all__ = ["Config", "SnapshotManager", "BackupManager", "RecoveryManager"]

from snapback.backup import BackupManager
from snapback.config import Config
from snapback.recovery import RecoveryManager
from snapback.snapshot import SnapshotManager
