"""Pytest configuration and fixtures for snapback tests."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from snapback.config import Config


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing.

    Yields:
        Path object for the temporary directory
    """
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def config_file(temp_dir):
    """Create a temporary config file.

    Args:
        temp_dir: Temporary directory fixture

    Yields:
        Path to the config file
    """
    config_path = temp_dir / "test_config.rc"
    source_dir1 = temp_dir / "source1"
    source_dir2 = temp_dir / "source2"
    target_base = temp_dir / "snapshots"

    # Create source directories
    source_dir1.mkdir()
    source_dir2.mkdir()

    # Write config
    config_content = f"""
DIRS="{source_dir1} {source_dir2}"
TARGETBASE="{target_base}"
RSYNC_PARAMS="--exclude=*.tmp"
"""
    config_path.write_text(config_content)

    yield config_path


@pytest.fixture
def config(config_file):
    """Load a test configuration.

    Args:
        config_file: Config file fixture

    Returns:
        Config object
    """
    return Config.load(str(config_file))


@pytest.fixture
def source_dirs(config):
    """Create and populate source directories.

    Args:
        config: Config fixture

    Returns:
        List of Path objects for source directories
    """
    dirs = []
    for dir_path in config.dirs:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)

        # Create some test files
        (path / "file1.txt").write_text("content 1")
        (path / "file2.txt").write_text("content 2")

        subdir = path / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content 3")

        dirs.append(path)

    return dirs


@pytest.fixture
def snapshot_base(config):
    """Create snapshot base directory.

    Args:
        config: Config fixture

    Returns:
        Path object for snapshot base directory
    """
    base = Path(config.target_base)
    base.mkdir(parents=True, exist_ok=True)
    return base


@pytest.fixture
def initialized_snapshots(snapshot_base, config):
    """Create initialized snapshot structure.

    Args:
        snapshot_base: Snapshot base fixture
        config: Config fixture

    Returns:
        SnapshotManager instance
    """
    from snapback.snapshot import SnapshotManager

    manager = SnapshotManager(config)
    manager.init_snapshots()
    return manager


@pytest.fixture
def mock_rsync(monkeypatch):
    """Mock rsync command for testing.

    This prevents actual rsync calls during testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        Mock function that records calls
    """
    calls = []

    def mock_run(*args, **kwargs):
        """Mock subprocess.run for rsync."""
        calls.append((args, kwargs))

        # Create a mock result
        class MockResult:
            returncode = 0
            stdout = ""
            stderr = ""

        return MockResult()

    import subprocess

    monkeypatch.setattr(subprocess, "run", mock_run)

    return calls


@pytest.fixture
def sample_snapshot(initialized_snapshots, source_dirs):
    """Create a sample snapshot with test data.

    Args:
        initialized_snapshots: Initialized snapshot structure
        source_dirs: Source directories with test files

    Returns:
        Path to hour-0 snapshot
    """
    from snapback.backup import BackupManager

    config = initialized_snapshots.config
    backup_manager = BackupManager(config)

    # Create hour-0 with test data
    hour_0 = Path(config.target_base) / "hour-0"

    for source_dir in source_dirs:
        target_subdir = hour_0 / source_dir.name
        target_subdir.mkdir(parents=True, exist_ok=True)

        # Copy files
        for item in source_dir.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(source_dir)
                target_file = target_subdir / rel_path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target_file)

    return hour_0


@pytest.fixture
def env_config_path(temp_dir, monkeypatch):
    """Set up environment variable for config path.

    Args:
        temp_dir: Temporary directory fixture
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        Path to config file
    """
    config_path = temp_dir / ".snapshotrc"
    monkeypatch.setenv("SNAPSHOTRC", str(config_path))
    return config_path
