"""Configuration management for snapback."""

import os
import re
import shlex
from pathlib import Path
from typing import List, Optional


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


class Config:
    """
    Configuration for snapback backup system.

    Loads configuration from bash-style config files (e.g., ~/.snapshotrc)
    and provides validation and defaults.
    """

    def __init__(
        self,
        dirs: List[str],
        targetbase: str,
        rsync_params: str = "",
        hsnaps: int = 23,
        dsnaps: int = 7,
        wsnaps: int = 4,
        msnaps: int = 12,
    ):
        """
        Initialize configuration.

        Args:
            dirs: List of source directories to backup
            targetbase: Base directory for storing snapshots
            rsync_params: Additional rsync parameters
            hsnaps: Number of hourly snapshots (default: 23)
            dsnaps: Number of daily snapshots (default: 7)
            wsnaps: Number of weekly snapshots (default: 4)
            msnaps: Number of monthly snapshots (default: 12)
        """
        self.dirs = [os.path.expanduser(d) for d in dirs]
        self.target_base = os.path.expanduser(targetbase)  # Use target_base for consistency
        self.rsync_params = rsync_params
        self.hsnaps = hsnaps
        self.dsnaps = dsnaps
        self.wsnaps = wsnaps
        self.msnaps = msnaps

        self._validate()

    def _validate(self):
        """Validate configuration values."""
        if not self.dirs:
            raise ConfigError("DIRS is required and cannot be empty")
        if not self.target_base:
            raise ConfigError("TARGETBASE is required and cannot be empty")

        for d in self.dirs:
            if not os.path.isabs(d):
                raise ConfigError(f"Directory must be absolute path: {d}")

        if not os.path.isabs(self.target_base):
            raise ConfigError(f"TARGETBASE must be absolute path: {self.target_base}")

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """
        Load configuration from file.

        Args:
            config_path: Path to config file. If None, uses SNAPSHOTRC env var
                        or ~/.snapshotrc

        Returns:
            Config instance

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config is invalid
        """
        try:
            return cls.from_file(config_path)
        except ConfigError as e:
            # Convert ConfigError to appropriate exception type
            if "not found" in str(e):
                raise FileNotFoundError(str(e))
            else:
                raise ValueError(str(e))

    @classmethod
    def from_file(cls, config_path: Optional[str] = None) -> "Config":
        """
        Load configuration from file.

        Args:
            config_path: Path to config file. If None, uses SNAPSHOTRC env var
                        or ~/.snapshotrc

        Returns:
            Config instance

        Raises:
            ConfigError: If config file not found or invalid
        """
        if config_path is None:
            config_path = os.environ.get("SNAPSHOTRC", os.path.expanduser("~/.snapshotrc"))

        config_path = os.path.expanduser(config_path)
        if not os.path.exists(config_path):
            raise ConfigError(
                f"Configuration file not found: {config_path}\n"
                f"Run 'snapback sampleconfig > {config_path}' to create one."
            )

        config_data = cls._parse_bash_config(config_path)

        # Extract required fields
        dirs_str = config_data.get("DIRS", "")
        if not dirs_str:
            raise ConfigError(f"DIRS not found in {config_path}")

        # Parse space-separated directories, respecting quotes
        try:
            dirs = shlex.split(dirs_str)
        except ValueError as e:
            raise ConfigError(f"Failed to parse DIRS: {e}")

        targetbase = config_data.get("TARGETBASE", os.path.expanduser("~/.Snapshots"))
        rsync_params = config_data.get("RSYNC_PARAMS", "")

        # Optional: snapshot counts (use defaults if not specified)
        hsnaps = int(config_data.get("hsnaps", "23"))
        dsnaps = int(config_data.get("dsnaps", "7"))
        wsnaps = int(config_data.get("wsnaps", "4"))
        msnaps = int(config_data.get("msnaps", "12"))

        return cls(
            dirs=dirs,
            targetbase=targetbase,
            rsync_params=rsync_params,
            hsnaps=hsnaps,
            dsnaps=dsnaps,
            wsnaps=wsnaps,
            msnaps=msnaps,
        )

    @staticmethod
    def _parse_bash_config(config_path: str) -> dict:
        """
        Parse bash-style configuration file.

        Handles formats like:
            DIRS='/path/one /path/two'
            TARGETBASE="~/.Snapshots"
            RSYNC_PARAMS='--max-size=1.5m'

        Args:
            config_path: Path to config file

        Returns:
            Dictionary of configuration values
        """
        config = {}

        # Pattern to match: KEY='value' or KEY="value" or KEY=value
        pattern = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$')

        with open(config_path, "r") as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                match = pattern.match(line)
                if match:
                    key, value = match.groups()

                    # Strip whitespace and remove surrounding quotes
                    value = value.strip()
                    if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
                        value = value[1:-1]

                    config[key] = value

        return config

    @staticmethod
    def generate_sample_config() -> str:
        """
        Generate a sample configuration file content.

        Returns:
            Sample configuration as string
        """
        home = os.path.expanduser("~")
        return f"""# snapback configuration file
#
# Space-separated list of directories to backup
# For paths with spaces, use nested quotes:  DIRS='{home}/Documents "{home}/My Files"'
DIRS='{home}/Documents {home}/Projects'

# Base directory for snapshots
TARGETBASE='{home}/.Snapshots'

# Optional: Additional rsync parameters
# Examples:
#   --max-size=1.5m        # Skip files larger than 1.5MB
#   --exclude=node_modules # Exclude node_modules directories
#   --exclude=*.tmp        # Exclude .tmp files
RSYNC_PARAMS='--max-size=1.5m'
"""
