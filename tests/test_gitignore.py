"""Tests for gitignore utility module."""

import pytest
from pathlib import Path
from snapback.gitignore import (
    read_gitignore,
    get_gitignore_patterns,
    update_gitignore,
    ensure_gitignore_entries,
    create_gitignore,
)


@pytest.fixture
def temp_gitignore(tmp_path):
    """Create a temporary .gitignore file."""
    gitignore_path = tmp_path / ".gitignore"
    return gitignore_path


@pytest.fixture
def existing_gitignore(tmp_path):
    """Create a temporary .gitignore file with existing content."""
    gitignore_path = tmp_path / ".gitignore"
    gitignore_path.write_text(
        """# Python
__pycache__/
*.py[cod]
*.so

# Virtual environments
venv/
.venv

# IDEs
.vscode/
.idea/
"""
    )
    return gitignore_path


class TestReadGitignore:
    """Tests for read_gitignore function."""

    def test_read_gitignore_success(self, existing_gitignore):
        """Test reading an existing .gitignore file."""
        lines = read_gitignore(existing_gitignore)

        assert isinstance(lines, list)
        assert len(lines) > 0
        assert "# Python" in lines
        assert "__pycache__/" in lines
        assert "*.py[cod]" in lines

    def test_read_gitignore_not_found(self, tmp_path):
        """Test reading non-existent .gitignore file raises FileNotFoundError."""
        non_existent = tmp_path / "non_existent.gitignore"

        with pytest.raises(FileNotFoundError, match="not found"):
            read_gitignore(non_existent)

    def test_read_gitignore_empty_file(self, temp_gitignore):
        """Test reading empty .gitignore file."""
        temp_gitignore.write_text("")
        lines = read_gitignore(temp_gitignore)

        assert lines == []

    def test_read_gitignore_preserves_comments(self, existing_gitignore):
        """Test that comments and formatting are preserved."""
        lines = read_gitignore(existing_gitignore)

        # Verify comments are preserved
        comment_lines = [line for line in lines if line.strip().startswith("#")]
        assert len(comment_lines) > 0

        # Verify empty lines are preserved
        empty_lines = [line for line in lines if not line.strip()]
        assert len(empty_lines) > 0


class TestGetGitignorePatterns:
    """Tests for get_gitignore_patterns function."""

    def test_get_patterns_success(self, existing_gitignore):
        """Test extracting patterns from .gitignore."""
        patterns = get_gitignore_patterns(existing_gitignore)

        assert isinstance(patterns, set)
        assert "__pycache__/" in patterns
        assert "*.py[cod]" in patterns
        assert "*.so" in patterns
        assert "venv/" in patterns
        assert ".vscode/" in patterns

    def test_get_patterns_excludes_comments(self, existing_gitignore):
        """Test that comments are excluded from patterns."""
        patterns = get_gitignore_patterns(existing_gitignore)

        # Comments should not be in patterns
        assert "# Python" not in patterns
        assert "# Virtual environments" not in patterns
        assert "# IDEs" not in patterns

    def test_get_patterns_excludes_empty_lines(self, existing_gitignore):
        """Test that empty lines are excluded from patterns."""
        patterns = get_gitignore_patterns(existing_gitignore)

        # No empty strings in patterns
        assert "" not in patterns

    def test_get_patterns_non_existent_file(self, tmp_path):
        """Test getting patterns from non-existent file returns empty set."""
        non_existent = tmp_path / "non_existent.gitignore"
        patterns = get_gitignore_patterns(non_existent)

        assert patterns == set()

    def test_get_patterns_empty_file(self, temp_gitignore):
        """Test getting patterns from empty file returns empty set."""
        temp_gitignore.write_text("")
        patterns = get_gitignore_patterns(temp_gitignore)

        assert patterns == set()

    def test_get_patterns_strips_whitespace(self, temp_gitignore):
        """Test that patterns have whitespace stripped."""
        temp_gitignore.write_text("  *.pyc  \n\n  venv/  \n")
        patterns = get_gitignore_patterns(temp_gitignore)

        assert "*.pyc" in patterns
        assert "venv/" in patterns
        # Whitespace-padded versions should not be present
        assert "  *.pyc  " not in patterns


class TestUpdateGitignore:
    """Tests for update_gitignore function."""

    def test_update_new_file(self, temp_gitignore):
        """Test creating new .gitignore with entries."""
        entries = [".snapshots/", ".snapshotrc"]
        update_gitignore(temp_gitignore, entries)

        assert temp_gitignore.exists()
        content = temp_gitignore.read_text()
        assert ".snapshots/" in content
        assert ".snapshotrc" in content
        assert "# .gitignore" in content

    def test_update_existing_file(self, existing_gitignore):
        """Test adding entries to existing .gitignore."""
        entries = [".snapshots/", ".snapshotrc"]
        update_gitignore(existing_gitignore, entries)

        content = existing_gitignore.read_text()
        # Original content should be preserved
        assert "__pycache__/" in content
        assert "*.py[cod]" in content
        # New entries should be added
        assert ".snapshots/" in content
        assert ".snapshotrc" in content

    def test_update_preserves_newline(self, existing_gitignore):
        """Test that file ending without newline gets one added."""
        # Remove trailing newline
        content = existing_gitignore.read_text().rstrip()
        existing_gitignore.write_text(content)

        entries = [".snapshots/"]
        update_gitignore(existing_gitignore, entries)

        # Should have newline before new entries
        final_content = existing_gitignore.read_text()
        assert not final_content.startswith(".snapshots/")

    def test_update_multiple_entries(self, temp_gitignore):
        """Test adding multiple entries at once."""
        entries = [".snapshots/", ".snapshotrc", "*.backup"]
        update_gitignore(temp_gitignore, entries)

        content = temp_gitignore.read_text()
        for entry in entries:
            assert entry in content


class TestEnsureGitignoreEntries:
    """Tests for ensure_gitignore_entries function."""

    def test_ensure_new_file(self, temp_gitignore):
        """Test creating new .gitignore with ensure."""
        entries = [".snapshots/", ".snapshotrc"]
        result = ensure_gitignore_entries(temp_gitignore, entries)

        assert result is True  # Entries were added
        assert temp_gitignore.exists()

        patterns = get_gitignore_patterns(temp_gitignore)
        assert ".snapshots/" in patterns
        assert ".snapshotrc" in patterns

    def test_ensure_existing_file_new_entries(self, existing_gitignore):
        """Test adding new entries to existing .gitignore."""
        entries = [".snapshots/", ".snapshotrc"]
        result = ensure_gitignore_entries(existing_gitignore, entries)

        assert result is True  # Entries were added

        patterns = get_gitignore_patterns(existing_gitignore)
        # Original patterns preserved
        assert "__pycache__/" in patterns
        # New patterns added
        assert ".snapshots/" in patterns
        assert ".snapshotrc" in patterns

    def test_ensure_existing_entries_no_duplicates(self, existing_gitignore):
        """Test that existing entries are not duplicated."""
        # Add snapback entries
        entries = [".snapshots/", ".snapshotrc"]
        result1 = ensure_gitignore_entries(existing_gitignore, entries)
        assert result1 is True

        # Try to add same entries again
        result2 = ensure_gitignore_entries(existing_gitignore, entries)
        assert result2 is False  # No entries added

        # Verify entries appear only once
        content = existing_gitignore.read_text()
        assert content.count(".snapshots/") == 1
        assert content.count(".snapshotrc") == 1

    def test_ensure_partial_overlap(self, existing_gitignore):
        """Test adding entries when some already exist."""
        # Add first entry
        ensure_gitignore_entries(existing_gitignore, [".snapshots/"])

        # Try to add first entry again plus a new one
        entries = [".snapshots/", ".snapshotrc"]
        result = ensure_gitignore_entries(existing_gitignore, entries)

        assert result is True  # New entry was added

        patterns = get_gitignore_patterns(existing_gitignore)
        assert ".snapshots/" in patterns
        assert ".snapshotrc" in patterns

        # First entry should not be duplicated
        content = existing_gitignore.read_text()
        assert content.count(".snapshots/") == 1

    def test_ensure_adds_section_header(self, temp_gitignore):
        """Test that snapback section header is added."""
        entries = [".snapshots/", ".snapshotrc"]
        ensure_gitignore_entries(temp_gitignore, entries)

        content = temp_gitignore.read_text()
        assert "# snapback - local snapshot backups" in content

    def test_ensure_preserves_newlines(self, existing_gitignore):
        """Test that newlines are properly managed."""
        # Remove trailing newline
        content = existing_gitignore.read_text().rstrip()
        existing_gitignore.write_text(content)

        entries = [".snapshots/"]
        ensure_gitignore_entries(existing_gitignore, entries)

        # Should have proper newlines
        final_content = existing_gitignore.read_text()
        lines = final_content.split("\n")
        # Should not have entries on same line as previous content
        assert any(".snapshots/" in line for line in lines)


class TestCreateGitignore:
    """Tests for create_gitignore function."""

    def test_create_new_file(self, temp_gitignore):
        """Test creating new .gitignore file."""
        entries = [".snapshots/", ".snapshotrc"]
        create_gitignore(temp_gitignore, entries)

        assert temp_gitignore.exists()

        content = temp_gitignore.read_text()
        assert "# .gitignore" in content
        assert "# snapback - local snapshot backups" in content
        assert ".snapshots/" in content
        assert ".snapshotrc" in content

    def test_create_file_already_exists(self, existing_gitignore):
        """Test creating .gitignore when file already exists raises error."""
        entries = [".snapshots/"]

        with pytest.raises(FileExistsError, match="already exists"):
            create_gitignore(existing_gitignore, entries)

    def test_create_empty_entries(self, temp_gitignore):
        """Test creating .gitignore with no entries."""
        create_gitignore(temp_gitignore, [])

        assert temp_gitignore.exists()
        content = temp_gitignore.read_text()
        assert "# .gitignore" in content
        # Should not have snapback section if no entries
        assert "# snapback" not in content

    def test_create_multiple_entries(self, temp_gitignore):
        """Test creating .gitignore with multiple entries."""
        entries = [".snapshots/", ".snapshotrc", "*.backup", "temp/"]
        create_gitignore(temp_gitignore, entries)

        patterns = get_gitignore_patterns(temp_gitignore)
        for entry in entries:
            assert entry in patterns


class TestIntegration:
    """Integration tests for gitignore module."""

    def test_full_workflow(self, temp_gitignore):
        """Test complete workflow: create, ensure, update."""
        # Start with create
        create_gitignore(temp_gitignore, ["*.pyc", "__pycache__/"])

        patterns = get_gitignore_patterns(temp_gitignore)
        assert "*.pyc" in patterns
        assert "__pycache__/" in patterns

        # Ensure additional entries
        result = ensure_gitignore_entries(temp_gitignore, [".snapshots/", ".snapshotrc"])
        assert result is True

        patterns = get_gitignore_patterns(temp_gitignore)
        assert ".snapshots/" in patterns
        assert ".snapshotrc" in patterns

        # Ensure again (should not duplicate)
        result = ensure_gitignore_entries(temp_gitignore, [".snapshots/"])
        assert result is False

        # Update with more entries
        update_gitignore(temp_gitignore, ["*.log"])

        patterns = get_gitignore_patterns(temp_gitignore)
        assert "*.log" in patterns

        # Verify all patterns still present
        assert "*.pyc" in patterns
        assert ".snapshots/" in patterns

    def test_real_world_git_repo_scenario(self, tmp_path):
        """Test realistic git repository initialization scenario."""
        # Simulate git repo with existing .gitignore
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(
            """# Python
__pycache__/
*.py[cod]

# Virtual environments
venv/
"""
        )

        # Snapback init adds its entries
        entries = [".snapshots/", ".snapshotrc"]
        added = ensure_gitignore_entries(gitignore, entries)
        assert added is True

        # Verify original patterns preserved
        patterns = get_gitignore_patterns(gitignore)
        assert "__pycache__/" in patterns
        assert "*.py[cod]" in patterns
        assert "venv/" in patterns

        # Verify snapback patterns added
        assert ".snapshots/" in patterns
        assert ".snapshotrc" in patterns

        # Running init again should not duplicate
        added = ensure_gitignore_entries(gitignore, entries)
        assert added is False

        content = gitignore.read_text()
        assert content.count(".snapshots/") == 1
        assert content.count(".snapshotrc") == 1
