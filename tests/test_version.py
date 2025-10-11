"""Tests for version functionality."""

import re
import subprocess
import sys
from pathlib import Path


def test_version_argument():
    """Test that --version argument prints version and exits successfully."""
    # Run snapback --version
    result = subprocess.run(
        [sys.executable, "-m", "snapback.cli", "--version"],
        capture_output=True,
        text=True,
    )

    # Should exit with code 0
    assert result.returncode == 0

    # Output should be on stdout (argparse version action uses stdout)
    output = result.stdout.strip()

    # Should contain "snapback" and a version number (X.Y.Z format)
    assert "snapback" in output.lower()
    assert re.search(r"\d+\.\d+\.\d+", output), f"Version format not found in: {output}"


def test_version_matches_pyproject():
    """Test that __version__ matches version in pyproject.toml."""
    # Import version from package
    from snapback import __version__

    # Read version from pyproject.toml
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    pyproject_content = pyproject_path.read_text()

    # Extract version from pyproject.toml
    # Look for: version = "X.Y.Z"
    match = re.search(r'version\s*=\s*"([^"]+)"', pyproject_content)
    assert match, "Could not find version in pyproject.toml"

    pyproject_version = match.group(1)

    # Versions should match exactly
    assert __version__ == pyproject_version, (
        f"Version mismatch: __version__={__version__} "
        f"vs pyproject.toml={pyproject_version}"
    )


def test_version_format():
    """Test that version follows semantic versioning format."""
    from snapback import __version__

    # Should match semantic versioning: X.Y.Z or X.Y.Z-suffix
    assert re.match(
        r"^\d+\.\d+\.\d+(-[\w.]+)?$", __version__
    ), f"Invalid version format: {__version__}"


def test_version_importable():
    """Test that version can be imported from snapback package."""
    # This should not raise any exceptions
    from snapback import __version__

    # Version should be a non-empty string
    assert isinstance(__version__, str)
    assert len(__version__) > 0
