# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**snapback** is a snapshot-based backup system written in Python 3.10+ that uses rsync and hard links to create space-efficient, incremental backups with multiple retention policies (hourly, daily, weekly, monthly).

Version 2.0 is a complete rewrite in Python, replacing the original Bash implementation while maintaining 100% functional compatibility. The Python implementation features comprehensive testing (118 unit tests), proper error handling, and modern packaging via pip/uv.

## Core Architecture

### Snapshot Rotation System

The system maintains four tiers of snapshots with automatic rotation:

1. **Hourly**: 23 snapshots (hour-0 to hour-23)
2. **Daily**: 7 snapshots (day-0 to day-7)
3. **Weekly**: 4 snapshots (week-0 to week-4)
4. **Monthly**: 12 snapshots (month-0 to month-12)

**Key Technical Detail**: The system uses `cp -al` (hard links) to create space-efficient copies. Only changed files consume additional disk space; unchanged files are hard-linked to previous snapshots.

### Rotation Flow

```
hourly → hour-0 becomes hour-1, hour-1 becomes hour-2, etc.
         oldest (hour-23) is deleted

daily  → hour-23 becomes day-0
         day-0 becomes day-1, etc.
         oldest (day-7) feeds into weekly

weekly → day-7 becomes week-0
         week-0 becomes week-1, etc.
         oldest (week-4) feeds into monthly

monthly → week-4 becomes month-0
          month-0 becomes month-1, etc.
          oldest (month-12) is deleted
```

### Python Modules

The Python implementation consists of seven core modules in `src/snapback/`:

- **cli.py** (625 lines) - Command-line interface
  - Argparse-based CLI with subcommands (init, hourly, recover, etc.)
  - Entry points for `snapback`, `snapls`, `snapdiff` commands
  - Help text and error message handling

- **config.py** (219 lines) - Configuration management
  - Loads and validates `~/.snapshotrc` or custom config paths
  - Environment variable support (`$SNAPSHOTRC`)
  - Sample configuration generation

- **backup.py** (184 lines) - Backup operations
  - rsync orchestration for hourly, daily, weekly, monthly backups
  - Hard link management via `cp -al`
  - Dry-run mode support

- **snapshot.py** (282 lines) - Snapshot management
  - Directory initialization and rotation logic
  - Four-tier retention policy implementation
  - Snapshot listing and validation

- **recovery.py** (276 lines) - Recovery and tagging
  - Full recovery (`recover`) and selective recovery (`undel`)
  - Snapshot tagging for preservation
  - Path deletion from snapshots

- **diff.py** - File comparison
  - Integration with vimdiff, meld, or other diff tools
  - Text-based diff output
  - Multi-snapshot file history

- **utils.py** - Utility functions
  - Path handling and validation
  - Error handling and logging
  - Common helper functions

### Configuration System

The system requires `~/.snapshotrc` (or custom path via `$SNAPSHOTRC` environment variable) with:

- `DIRS`: Space-separated list of directories to back up
- `TARGETBASE`: Base directory for snapshots (default: `~/.Snapshots`)
- `RSYNC_PARAMS`: Optional rsync parameters (e.g., `--max-size=1.5m`)

The configuration is sourced at runtime; the script exits with usage message if not found.

## Commands

### Setup and Initialization

```bash
# Create initial snapshot directory structure
snapback init

# Generate sample configuration
snapback sampleconfig
```

### Backup Operations

```bash
# Create hourly snapshot (run via cron hourly)
snapback hourly

# Rotate to daily snapshot (run via cron at 23:58)
snapback daily

# Rotate to weekly snapshot (run via cron Monday 22:56)
snapback weekly

# Rotate to monthly snapshot (run via cron 1st of month 01:00)
snapback monthly

# Dry-run mode (doesn't actually modify files)
snapback --dry-run hourly
```

### Recovery Operations

```bash
# Recover deleted files from a snapshot (only copies missing files)
snapback undel hour-1

# Full recovery from snapshot (overwrites current files)
snapback recover hour-3

# Tag a snapshot for preservation
snapback tag hour-1 before-upgrade

# Delete a specific path from hour-0 snapshot
snapback delete /path/to/directory
```

### Utility Commands

```bash
# List all snapshots containing a file
snapls myfile.txt
# or: snapback list myfile.txt

# Compare file with version N snapshots ago
snapdiff N myfile.txt
# or: snapback diff myfile.txt N
```

## Recommended Crontab Configuration

```cron
# Hourly backup
0 * * * * /usr/local/bin/snapback hourly >/dev/null 2>&1

# Daily rotation (23:58)
58 23 * * * /usr/local/bin/snapback daily >/dev/null 2>&1

# Weekly rotation (Monday 22:56)
56 22 * * 1 /usr/local/bin/snapback weekly >/dev/null 2>&1

# Monthly rotation (1st of month 01:00)
0 1 1 * * /usr/local/bin/snapback monthly >/dev/null 2>&1
```

Find installation path with: `which snapback`

## Development Notes

### Critical Implementation Details

1. **Hard Link Creation**: The system uses `cp -al` via subprocess calls to create hard links instead of copies. This is central to space efficiency. See `backup.py` and `snapshot.py` for implementation.

2. **Rotation Order**: The rotation sequences process snapshots in reverse order to avoid overwriting during the shift operation. See `snapshot.py:_rotate_snapshots()` method.

3. **rsync Parameters**: The `--delete` flag in hourly backups ensures hour-0 mirrors the source exactly (removes files deleted from source). See `backup.py:run_rsync()` method.

4. **Configuration Variables**: Both `RSYNC_PARAMS` and `RSYNCPARAMS` environment variables are supported for backward compatibility. See `config.py:Config.from_file()`.

5. **Subprocess Handling**: All shell commands (rsync, cp, mv) are executed via `subprocess.run()` with proper error handling and output capture. See `utils.py` for helper functions.

6. **Path Validation**: All user-provided paths are validated and normalized using `pathlib.Path`. See `utils.py` and individual command handlers.

### Testing

The project has comprehensive test coverage:

```bash
# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/test_cli.py -v

# Run with coverage
pytest tests/ --cov=src/snapback --cov-report=html

# Run linting
ruff check src/ tests/
```

**Test Structure**:
- `tests/test_cli.py` (344 lines) - CLI interface tests
- `tests/test_config.py` (196 lines) - Configuration loading and validation
- `tests/test_backup.py` (229 lines) - Backup operations
- `tests/test_snapshot.py` - Snapshot rotation logic
- `tests/test_recovery.py` - Recovery and tagging operations

Always use `--dry-run` flag when testing backup/recovery operations to avoid unintended data modifications.

### Development Workflow

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Make code changes
# ... edit src/snapback/*.py ...

# Run tests
pytest tests/ -v

# Run linting
ruff check src/ tests/

# Build package
uv build
```

## License

GPLv2