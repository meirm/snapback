"""Gitignore file utilities for snapback.

This module provides functions to read, parse, and update .gitignore files.
"""

from pathlib import Path
from typing import List, Set


def read_gitignore(path: Path) -> List[str]:
    """Read and parse .gitignore file.

    Args:
        path: Path to .gitignore file

    Returns:
        List of patterns from .gitignore (preserves comments and formatting)

    Raises:
        FileNotFoundError: If .gitignore doesn't exist
    """
    if not path.exists():
        raise FileNotFoundError(f".gitignore not found: {path}")

    return path.read_text().splitlines()


def get_gitignore_patterns(path: Path) -> Set[str]:
    """Get set of non-comment patterns from .gitignore.

    Args:
        path: Path to .gitignore file

    Returns:
        Set of patterns (excluding comments and empty lines)
    """
    if not path.exists():
        return set()

    patterns = set()
    for line in path.read_text().splitlines():
        stripped = line.strip()
        # Skip empty lines and comments
        if stripped and not stripped.startswith('#'):
            patterns.add(stripped)

    return patterns


def update_gitignore(path: Path, entries: List[str]) -> None:
    """Add entries to .gitignore file.

    Creates the file if it doesn't exist. Adds entries at the end.
    Does not check for duplicates - use ensure_gitignore_entries() for that.

    Args:
        path: Path to .gitignore file
        entries: List of patterns to add
    """
    # Read existing content or start with empty
    if path.exists():
        content = path.read_text()
        # Ensure file ends with newline
        if content and not content.endswith('\n'):
            content += '\n'
    else:
        content = ''

    # Add header comment if file is new or empty
    if not content.strip():
        content = "# .gitignore\n\n"

    # Add entries
    for entry in entries:
        content += f"{entry}\n"

    # Write back
    path.write_text(content)


def ensure_gitignore_entries(path: Path, entries: List[str]) -> bool:
    """Ensure entries exist in .gitignore, adding them if missing.

    Args:
        path: Path to .gitignore file
        entries: List of patterns to ensure exist

    Returns:
        True if any entries were added, False if all existed
    """
    existing_patterns = get_gitignore_patterns(path)

    # Find entries that need to be added
    to_add = [entry for entry in entries if entry not in existing_patterns]

    if not to_add:
        return False  # Nothing to add

    # Add missing entries
    if path.exists():
        content = path.read_text()
        # Ensure file ends with newline
        if content and not content.endswith('\n'):
            content += '\n'
    else:
        content = "# .gitignore\n\n"

    # Add snapback section header if adding entries
    if to_add:
        content += "\n# snapback - local snapshot backups\n"
        for entry in to_add:
            content += f"{entry}\n"

    path.write_text(content)
    return True


def create_gitignore(path: Path, entries: List[str]) -> None:
    """Create a new .gitignore file with the given entries.

    Args:
        path: Path where .gitignore should be created
        entries: List of patterns to include

    Raises:
        FileExistsError: If .gitignore already exists
    """
    if path.exists():
        raise FileExistsError(f".gitignore already exists: {path}")

    content = "# .gitignore\n\n"

    if entries:
        content += "# snapback - local snapshot backups\n"
        for entry in entries:
            content += f"{entry}\n"

    path.write_text(content)
