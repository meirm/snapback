"""Tests for configuration management."""

import os
from pathlib import Path

import pytest

from snapback.config import Config


def test_load_config(config_file):
    """Test loading configuration from file."""
    config = Config.load(str(config_file))

    assert len(config.dirs) == 2
    assert config.rsync_params == "--exclude=*.tmp"
    assert "snapshots" in str(config.target_base)


def test_load_config_missing_file():
    """Test loading configuration from non-existent file."""
    with pytest.raises(FileNotFoundError):
        Config.load("/nonexistent/path/config.rc")


def test_load_config_from_env(env_config_path, temp_dir):
    """Test loading configuration from environment variable."""
    # Create config in env path
    source_dir = temp_dir / "source"
    source_dir.mkdir()

    config_content = f"""
DIRS="{source_dir}"
TARGETBASE="{temp_dir / 'snapshots'}"
"""
    env_config_path.write_text(config_content)

    # Load config (should use SNAPSHOTRC env var)
    config = Config.load()

    assert len(config.dirs) == 1
    assert str(source_dir) in config.dirs


def test_load_config_default_path(temp_dir, monkeypatch):
    """Test loading configuration from default ~/.snapshotrc."""
    # Mock home directory
    monkeypatch.setenv("HOME", str(temp_dir))

    # Create config in home
    config_path = temp_dir / ".snapshotrc"
    source_dir = temp_dir / "source"
    source_dir.mkdir()

    config_content = f"""
DIRS="{source_dir}"
TARGETBASE="{temp_dir / 'snapshots'}"
"""
    config_path.write_text(config_content)

    # Unset SNAPSHOTRC to use default
    monkeypatch.delenv("SNAPSHOTRC", raising=False)

    # Load config
    config = Config.load()

    assert len(config.dirs) == 1


def test_config_missing_dirs(temp_dir):
    """Test configuration validation with missing DIRS."""
    config_path = temp_dir / "config.rc"
    config_content = """
TARGETBASE="/tmp/snapshots"
"""
    config_path.write_text(config_content)

    with pytest.raises((ValueError, FileNotFoundError), match="DIRS"):
        Config.load(str(config_path))


def test_config_default_targetbase(temp_dir):
    """Test configuration with default TARGETBASE."""
    config_path = temp_dir / "config.rc"
    source_dir = temp_dir / "source"
    source_dir.mkdir()

    config_content = f"""
DIRS="{source_dir}"
"""
    config_path.write_text(config_content)

    config = Config.load(str(config_path))

    # Should default to ~/.Snapshots
    assert ".Snapshots" in str(config.target_base)


def test_config_multiple_dirs(temp_dir):
    """Test configuration with multiple directories."""
    config_path = temp_dir / "config.rc"
    source_dir1 = temp_dir / "source1"
    source_dir2 = temp_dir / "source2"
    source_dir3 = temp_dir / "source3"

    for d in [source_dir1, source_dir2, source_dir3]:
        d.mkdir()

    config_content = f"""
DIRS="{source_dir1} {source_dir2} {source_dir3}"
TARGETBASE="{temp_dir / 'snapshots'}"
"""
    config_path.write_text(config_content)

    config = Config.load(str(config_path))

    assert len(config.dirs) == 3
    assert str(source_dir1) in config.dirs
    assert str(source_dir2) in config.dirs
    assert str(source_dir3) in config.dirs


def test_config_with_quotes(temp_dir):
    """Test configuration with quoted paths."""
    config_path = temp_dir / "config.rc"
    source_dir = temp_dir / "my dir with spaces"
    source_dir.mkdir()

    # Use nested quotes for paths with spaces
    config_content = f"""
DIRS='"{source_dir}"'
TARGETBASE="{temp_dir / 'snapshots'}"
"""
    config_path.write_text(config_content)

    config = Config.load(str(config_path))

    assert len(config.dirs) == 1
    assert "my dir with spaces" in config.dirs[0]


def test_config_expand_home(temp_dir, monkeypatch):
    """Test configuration with ~ expansion."""
    monkeypatch.setenv("HOME", str(temp_dir))

    config_path = temp_dir / "config.rc"
    config_content = """
DIRS="~/Documents ~/Projects"
TARGETBASE="~/Snapshots"
"""
    config_path.write_text(config_content)

    config = Config.load(str(config_path))

    # Paths should be expanded
    assert len(config.dirs) == 2
    assert str(temp_dir) in config.dirs[0]
    assert str(temp_dir) in config.target_base


def test_config_empty_rsync_params(temp_dir):
    """Test configuration with empty RSYNC_PARAMS."""
    config_path = temp_dir / "config.rc"
    source_dir = temp_dir / "source"
    source_dir.mkdir()

    config_content = f"""
DIRS="{source_dir}"
TARGETBASE="{temp_dir / 'snapshots'}"
RSYNC_PARAMS=""
"""
    config_path.write_text(config_content)

    config = Config.load(str(config_path))

    assert config.rsync_params == ""


def test_config_rsync_params_with_options(temp_dir):
    """Test configuration with multiple rsync options."""
    config_path = temp_dir / "config.rc"
    source_dir = temp_dir / "source"
    source_dir.mkdir()

    config_content = f"""
DIRS="{source_dir}"
TARGETBASE="{temp_dir / 'snapshots'}"
RSYNC_PARAMS="--exclude=*.tmp --max-size=1.5m --verbose"
"""
    config_path.write_text(config_content)

    config = Config.load(str(config_path))

    assert "--exclude=*.tmp" in config.rsync_params
    assert "--max-size=1.5m" in config.rsync_params
    assert "--verbose" in config.rsync_params
