"""
snapback - Space-efficient snapshot-based backup system.

A Python implementation of snapback that uses rsync and hard links to create
space-efficient, incremental backups with multiple retention policies.
"""

__version__ = "2.0.0"
__all__ = ["Config", "SnapshotManager", "BackupManager", "RecoveryManager"]

from snapback.config import Config
from snapback.snapshot import SnapshotManager
from snapback.backup import BackupManager
from snapback.recovery import RecoveryManager
