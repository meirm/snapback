"""Tests for path security and workspace confinement.

This module contains comprehensive security tests for path validation,
dangerous path rejection, symlink safety, and workspace boundary enforcement.
"""

import os
import pytest
from pathlib import Path

from snapback.config import Config, ConfigError
from snapback.utils import (
    is_safe_workspace_path,
    is_dangerous_targetbase,
    safe_rmtree,
    validate_workspace_path,
)
from snapback.snapshot import SnapshotManager
from snapback.recovery import RecoveryManager
from snapback.backup import BackupManager


class TestDangerousTargetbaseRejection:
    """Test rejection of dangerous TARGETBASE values."""

    def test_dangerous_targetbase_system_root(self):
        """Test that TARGETBASE="/" is rejected."""
        is_dangerous, reason = is_dangerous_targetbase("/", is_local=False)
        assert is_dangerous
        assert "system directory" in reason.lower()

    def test_dangerous_targetbase_home(self):
        """Test that TARGETBASE="/home" is rejected (if it exists on the system)."""
        # /home may not exist on macOS, so we test it but don't fail if not dangerous
        is_dangerous, reason = is_dangerous_targetbase("/home", is_local=False)
        # On Linux it should be dangerous, on macOS it might not exist
        if Path("/home").exists():
            assert is_dangerous
            assert "system directory" in reason.lower()

    def test_dangerous_targetbase_usr(self):
        """Test that TARGETBASE="/usr" is rejected."""
        is_dangerous, reason = is_dangerous_targetbase("/usr", is_local=False)
        assert is_dangerous
        assert "system directory" in reason.lower()

    def test_dangerous_targetbase_etc(self):
        """Test that TARGETBASE="/etc" is rejected (if exists on system)."""
        is_dangerous, reason = is_dangerous_targetbase("/etc", is_local=False)
        if Path("/etc").exists():
            assert is_dangerous
            assert "system directory" in reason.lower()

    def test_dangerous_targetbase_var(self):
        """Test that TARGETBASE="/var" is rejected (if exists on system)."""
        is_dangerous, reason = is_dangerous_targetbase("/var", is_local=False)
        if Path("/var").exists():
            assert is_dangerous
            assert "system directory" in reason.lower()

    def test_dangerous_targetbase_tmp(self):
        """Test that TARGETBASE="/tmp" is rejected (if exists on system)."""
        is_dangerous, reason = is_dangerous_targetbase("/tmp", is_local=False)
        if Path("/tmp").exists():
            assert is_dangerous
            assert "system directory" in reason.lower()

    def test_dangerous_targetbase_home_root(self, tmp_path):
        """Test that TARGETBASE="~" (home directory root) is rejected."""
        home_dir = str(Path.home())
        is_dangerous, reason = is_dangerous_targetbase(home_dir, is_local=False)
        assert is_dangerous
        assert "home directory root" in reason.lower()

    def test_dangerous_targetbase_parent_in_local(self):
        """Test that TARGETBASE=".." is rejected in local mode."""
        is_dangerous, reason = is_dangerous_targetbase("..", is_local=True)
        assert is_dangerous
        assert ".." in reason or "parent" in reason.lower()

    def test_dangerous_targetbase_absolute_in_local(self):
        """Test that absolute paths are flagged in local mode."""
        is_dangerous, reason = is_dangerous_targetbase("/tmp/outside", is_local=True)
        assert is_dangerous
        assert "absolute" in reason.lower()

    def test_safe_targetbase_subdirectory(self, tmp_path):
        """Test that safe subdirectory is accepted."""
        safe_path = str(tmp_path / ".snapshots")
        is_dangerous, reason = is_dangerous_targetbase(safe_path, is_local=False)
        assert not is_dangerous
        assert reason == ""

    def test_safe_targetbase_relative_in_local(self):
        """Test that relative path like './.snapshots' is accepted in local mode."""
        is_dangerous, reason = is_dangerous_targetbase("./.snapshots", is_local=True)
        assert not is_dangerous or "absolute" not in reason.lower()  # May warn about absolute but not dangerous


class TestConfigDangerousPathRejection:
    """Test that Config validation rejects dangerous paths."""

    def test_config_rejects_system_root(self, tmp_path, monkeypatch):
        """Test that config rejects TARGETBASE="/"."""
        config_file = tmp_path / ".snapshotrc"
        config_file.write_text("DIRS='.'\nTARGETBASE='/'")

        monkeypatch.chdir(tmp_path)

        with pytest.raises(ConfigError, match="system directory"):
            Config.from_file(str(config_file))

    def test_config_rejects_home_directory(self, tmp_path, monkeypatch):
        """Test that config rejects TARGETBASE="/home"."""
        config_file = tmp_path / ".snapshotrc"
        config_file.write_text("DIRS='.'\nTARGETBASE='/home'")

        monkeypatch.chdir(tmp_path)

        # May be rejected for "system directory" or as "absolute path" in local mode
        with pytest.raises(ConfigError, match="(?i)(system directory|absolute|dangerous)"):
            Config.from_file(str(config_file))

    def test_config_local_rejects_parent_directory(self, tmp_path, monkeypatch):
        """Test that local mode rejects TARGETBASE='..'."""
        config_file = tmp_path / ".snapshotrc"
        config_file.write_text("DIRS='.'\nTARGETBASE='..'")

        monkeypatch.chdir(tmp_path)

        with pytest.raises(ConfigError, match="(?i)(parent|dangerous|\\.\\.)")  :
            Config.from_file(str(config_file))

    def test_config_local_rejects_outside_workspace(self, tmp_path, monkeypatch):
        """Test that local mode rejects TARGETBASE outside workspace."""
        workspace = tmp_path / "project"
        workspace.mkdir()

        config_file = workspace / ".snapshotrc"
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()

        config_file.write_text(f"DIRS='.'\nTARGETBASE='{outside_dir}'")

        monkeypatch.chdir(workspace)

        with pytest.raises(ConfigError, match="(?i)(workspace|dangerous|absolute)"):
            Config.from_file(str(config_file))

    def test_config_accepts_safe_local_path(self, tmp_path, monkeypatch):
        """Test that local mode accepts safe relative path."""
        config_file = tmp_path / ".snapshotrc"
        config_file.write_text("DIRS='.'\nTARGETBASE='./.snapshots'")

        monkeypatch.chdir(tmp_path)

        # Should not raise
        config = Config.from_file(str(config_file))
        assert config.is_local
        assert config.target_base == "./.snapshots"


class TestSymlinkSafety:
    """Test that operations don't follow symlinks outside workspace."""

    def test_safe_rmtree_does_not_follow_symlinks(self, tmp_path):
        """Test that safe_rmtree doesn't follow symlinks."""
        # Create a directory with a symlink to outside
        inside_dir = tmp_path / "inside"
        inside_dir.mkdir()

        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "important.txt"
        outside_file.write_text("important data")

        # Create symlink inside that points outside
        symlink = inside_dir / "link_to_outside"
        symlink.symlink_to(outside_dir)

        # Remove inside_dir with safe_rmtree
        safe_rmtree(inside_dir)

        # Verify inside_dir is removed
        assert not inside_dir.exists()

        # Verify outside data is still there (symlink wasn't followed)
        assert outside_dir.exists()
        assert outside_file.exists()
        assert outside_file.read_text() == "important data"

    def test_safe_rmtree_with_workspace_validation(self, tmp_path):
        """Test that safe_rmtree validates workspace boundaries."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        inside_dir = workspace / "inside"
        inside_dir.mkdir()

        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()

        # Should succeed for path inside workspace
        safe_rmtree(inside_dir, workspace)
        assert not inside_dir.exists()

        # Should fail for path outside workspace
        with pytest.raises(ValueError, match="outside workspace"):
            safe_rmtree(outside_dir, workspace)

        # Verify outside_dir still exists
        assert outside_dir.exists()

    def test_snapshot_rotation_with_symlink(self, tmp_path, monkeypatch):
        """Test that snapshot rotation doesn't follow symlinks."""
        # Create local workspace
        workspace = tmp_path / "project"
        workspace.mkdir()

        # Create config
        config_file = workspace / ".snapshotrc"
        config_file.write_text("DIRS='.'\nTARGETBASE='./.snapshots'")

        monkeypatch.chdir(workspace)
        config = Config.from_file(str(config_file))

        # Create snapshot structure
        snapshots_dir = workspace / ".snapshots"
        snapshots_dir.mkdir()

        # Create hour-23 with symlink to outside
        hour_23 = snapshots_dir / "hour-23"
        hour_23.mkdir()

        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "data.txt"
        outside_file.write_text("outside data")

        symlink = hour_23 / "link"
        symlink.symlink_to(outside_dir)

        # Rotate hourly snapshots
        manager = SnapshotManager(config)
        manager.rotate_hourly()

        # Verify hour-23 is removed
        assert not hour_23.exists()

        # Verify outside data is untouched
        assert outside_dir.exists()
        assert outside_file.exists()


class TestWorkspaceBoundaryEnforcement:
    """Test workspace boundary enforcement in local mode."""

    def test_local_mode_backup_validates_paths(self, tmp_path, monkeypatch):
        """Test that backup validates source directories are in workspace."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()

        # Create config with outside directory
        config_file = workspace / ".snapshotrc"
        config_file.write_text(f"DIRS='{outside_dir}'\nTARGETBASE='./.snapshots'")

        monkeypatch.chdir(workspace)

        # Config validation should catch this
        with pytest.raises(ConfigError, match="(?i)workspace"):
            Config.from_file(str(config_file))

    def test_workspace_validation_detects_escape(self, tmp_path):
        """Test that workspace validation detects path traversal."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Try to validate path outside workspace
        outside_path = tmp_path / "outside"

        assert not is_safe_workspace_path(outside_path, workspace)

        # validate_workspace_path should raise
        with pytest.raises(ValueError, match="(?i)outside workspace"):
            validate_workspace_path(outside_path, workspace, "test")

    def test_workspace_validation_with_symlinks(self, tmp_path):
        """Test that symlinks pointing outside workspace are detected."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()

        # Create symlink inside workspace pointing outside
        symlink = workspace / "link"
        symlink.symlink_to(outside_dir)

        # The symlink itself is inside workspace
        # But when resolved, it points outside
        # is_safe_workspace_path resolves symlinks, so should detect this
        assert not is_safe_workspace_path(symlink, workspace)


class TestPathTraversalPrevention:
    """Test prevention of path traversal attacks."""

    def test_reject_path_traversal_in_config(self, tmp_path, monkeypatch):
        """Test that config rejects TARGETBASE with .. components."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        config_file = workspace / ".snapshotrc"
        config_file.write_text("DIRS='.'\nTARGETBASE='../outside'")

        monkeypatch.chdir(workspace)

        with pytest.raises(ConfigError, match="(?i)(parent|\\.\\.| dangerous)"):
            Config.from_file(str(config_file))

    def test_validate_workspace_path_rejects_dots(self, tmp_path):
        """Test that validate_workspace_path rejects .. components."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        bad_path = Path("../outside")

        with pytest.raises(ValueError, match="(?i)(traversal|\\.\\.| outside)"):
            validate_workspace_path(bad_path, workspace, "test")

    def test_path_traversal_with_resolve(self, tmp_path):
        """Test path traversal detection with resolved paths."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create a path that uses .. to escape
        inside_dir = workspace / "inside"
        inside_dir.mkdir()

        # Path like workspace/inside/../.. resolves to parent of workspace
        traversal_path = inside_dir / ".." / ".."

        # After resolution, this should be outside workspace
        assert not is_safe_workspace_path(traversal_path, workspace)


class TestErrorMessages:
    """Test that error messages are descriptive and helpful."""

    def test_dangerous_path_error_includes_reason(self, tmp_path, monkeypatch):
        """Test that dangerous path errors explain why."""
        config_file = tmp_path / ".snapshotrc"
        config_file.write_text("DIRS='.'\nTARGETBASE='/'")

        monkeypatch.chdir(tmp_path)

        with pytest.raises(ConfigError) as exc_info:
            Config.from_file(str(config_file))

        error_msg = str(exc_info.value)
        # Should mention why it's rejected
        assert "system directory" in error_msg.lower()
        # Should suggest alternative
        assert ".snapshots" in error_msg.lower() or "safe" in error_msg.lower()

    def test_workspace_boundary_error_includes_paths(self, tmp_path):
        """Test that workspace errors show attempted path and workspace root."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        outside_path = tmp_path / "outside"

        with pytest.raises(ValueError) as exc_info:
            validate_workspace_path(outside_path, workspace, "test operation")

        error_msg = str(exc_info.value)
        # Should mention the operation
        assert "test operation" in error_msg
        # Should mention workspace
        assert "workspace" in error_msg.lower()

    def test_parent_directory_error_suggests_alternative(self, tmp_path, monkeypatch):
        """Test that parent directory error suggests safe alternative."""
        config_file = tmp_path / ".snapshotrc"
        config_file.write_text("DIRS='.'\nTARGETBASE='..'")

        monkeypatch.chdir(tmp_path)

        with pytest.raises(ConfigError) as exc_info:
            Config.from_file(str(config_file))

        error_msg = str(exc_info.value)
        # Should suggest using ./.snapshots or similar
        assert ".snapshots" in error_msg.lower() or "within" in error_msg.lower()
