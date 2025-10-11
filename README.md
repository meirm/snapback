# snapback

**Space-efficient snapshot-based backup system for Unix/Linux**

[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20BSD-lightgrey)]()

---

## Table of Contents

- [Overview](#overview)
- [Why snapback?](#why-snapback)
- [Key Features](#key-features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Setup Commands](#setup-commands)
  - [Backup Operations](#backup-operations)
  - [Recovery Operations](#recovery-operations)
- [Usage Examples](#usage-examples)
- [Automated Backups with Cron](#automated-backups-with-cron)
- [Utility Scripts](#utility-scripts)
- [How It Works](#how-it-works)
- [Python Implementation](#python-implementation)
- [Container Testing](#container-testing)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [Best Practices](#best-practices)
- [License](#license)
- [Contributing](#contributing)

---

## Overview

**snapback** is a snapshot-based backup system written in Python that uses rsync and hard links to create space-efficient, incremental backups with multiple retention policies. It automatically maintains four tiers of snapshots: hourly, daily, weekly, and monthly.

Unlike traditional backup systems that create full copies of your data, snapback leverages hard links to store only the changed files, dramatically reducing storage requirements while maintaining instant access to every snapshot. All backups are stored as regular directories with human-readable filenames—no proprietary formats, no databases, no compression archives.

The modern Python 3.10+ implementation features comprehensive testing (118 unit tests), proper error handling, and easy installation via pip/uv. Whether you're a developer protecting working directories, a sysadmin managing servers, or a power user running a home NAS, snapback provides a transparent, reliable, and efficient backup solution that Just Works™.

## Why snapback?

- **Space Efficient**: Only changed files consume additional disk space. Unchanged files are hard-linked, typically using just 1.5-3x source size instead of 20-40x for full copies.
- **Transparent**: All backups are regular directories. Browse them with standard tools, no special software needed.
- **Simple**: Clean Python implementation, minimal dependencies, easy to understand and customize.
- **Time-Based Retention**: Four-tier policy (hourly → daily → weekly → monthly) provides both granular recent history and long-term archives.
- **No Vendor Lock-in**: Plain directories and files. Your data is always accessible, even without snapback.
- **Fast Recovery**: No extraction, no decompression. Copy files directly from snapshots.

## Key Features

- **Four-Tier Retention Policy**
  - 23 hourly snapshots (hour-0 to hour-23)
  - 7 daily snapshots (day-0 to day-7)
  - 4 weekly snapshots (week-0 to week-4)
  - 12 monthly snapshots (month-0 to month-12)
  - Total: 46 snapshots covering ~1 year of history

- **Space-Efficient Storage**
  - Hard links via `cp -al` for unchanged files
  - Only modified files consume additional space
  - Typical storage: 1.5-3x source size (vs 20-40x for full copies)

- **Flexible Recovery Options**
  - Full recovery: restore entire snapshot
  - Selective recovery: restore only deleted/missing files
  - Tagged snapshots: preserve important states indefinitely
  - Point-in-time recovery from any snapshot

- **Safe Operations**
  - Dry-run mode for testing
  - Configurable rsync filters (file size, patterns, exclusions)
  - Non-destructive recovery options

- **Minimal Dependencies**
  - Python 3.10+
  - rsync 3.0+
  - Standard Unix utilities: cp, mv, find

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, BSD, or any Unix-like system
- **Python**: Version 3.10 or later
- **rsync**: Version 3.0 or later
- **Disk Space**: At least 1.5-3x your source data size
- **pip or uv**: For installing Python packages

### Verify Prerequisites

```bash
# Check Python version (3.10+ required)
python3 --version

# Check rsync version
rsync --version

# Check pip or uv is available
pip --version
# or
uv --version
```

## Installation

### Option 1: Install from PyPI (Recommended when published)

```bash
pip install snapback
```

### Option 2: Install with uv (Recommended for development)

```bash
uv pip install snapback
```

### Option 3: Install from Source

```bash
# Clone the repository
git clone https://github.com/meirm/snapback.git
cd snapback

# Install in development mode
uv pip install -e ".[dev]"
```

### Verify Installation

```bash
snapback --help
snapls --help
snapdiff --help
```

The commands `snapback`, `snapls`, and `snapdiff` will be available in your PATH after installation.

## Quick Start

Get up and running in 5 minutes:

```bash
# 1. Generate sample configuration
snapback sampleconfig

# 2. Edit configuration (set DIRS to directories you want to backup)
nano ~/.snapshotrc

# 3. Initialize snapshot directory structure
snapback init

# 4. Create your first backup
snapback hourly

# 5. Verify backup was created
ls -la ~/.Snapshots/hour-0/
```

Your first snapshot is ready! See [Automated Backups with Cron](#automated-backups-with-cron) to set up automatic backups.

## Configuration

snapback requires a configuration file at `~/.snapshotrc` (or custom path via `$SNAPSHOTRC` environment variable).

### Configuration Variables

```bash
# Required: Space-separated list of directories to backup
DIRS="/home/user/Documents /home/user/Projects"

# Required: Base directory for all snapshots
TARGETBASE="~/.Snapshots"

# Optional: Additional rsync parameters
RSYNC_PARAMS="--max-size=1.5m --exclude=node_modules --exclude=.git"
```

### Configuration Options

- **DIRS**: Absolute paths to directories you want to backup. Separate multiple directories with spaces.
- **TARGETBASE**: Where snapshots are stored. Default: `~/.Snapshots`. Ensure this location has sufficient disk space.
- **RSYNC_PARAMS**: Optional rsync flags for filtering/customization.

### Example Configuration

```bash
# ~/.snapshotrc
DIRS="/home/user/Documents /home/user/Code /home/user/.config"
TARGETBASE="/mnt/backups/Snapshots"
RSYNC_PARAMS="--max-size=100m --exclude=*.tmp --exclude=.cache"
```

### Generate Sample Configuration

```bash
snapback sampleconfig
```

### Custom Configuration Path

```bash
# Use a different config file with --config flag
snapback --config /path/to/custom/config hourly

# Or use environment variable
export SNAPSHOTRC=/path/to/custom/config
snapback hourly
```

## Usage

### Setup Commands

#### Initialize Snapshot Directory Structure

```bash
snapback init
```

Creates the directory structure for all 46 snapshots (hour-0 through month-12). Run this once before your first backup.

#### Generate Sample Configuration

```bash
snapback sampleconfig
```

Prints a sample configuration file to stdout. To create the configuration file:

```bash
snapback sampleconfig > ~/.snapshotrc
```

Or the command will prompt to create it interactively if run without redirection.

#### Display Help

```bash
snapback --help
snapback <command> --help  # Get help for specific command
```

Shows usage information, available commands, and options.

### Backup Operations

#### Create Hourly Snapshot

```bash
snapback hourly
```

Creates a new hourly snapshot by:
1. Rotating existing snapshots (hour-0 → hour-1, hour-1 → hour-2, etc.)
2. Hard-linking hour-0 to hour-1
3. Running rsync to update hour-0 with current data
4. Deleting the oldest snapshot (hour-23)

**Note**: This is the main backup command. Run it via cron every hour.

#### Rotate to Daily Snapshot

```bash
snapback daily
```

Promotes hour-23 to day-0, then rotates daily snapshots. Run once daily at 23:58.

#### Rotate to Weekly Snapshot

```bash
snapback weekly
```

Promotes day-7 to week-0, then rotates weekly snapshots. Run once weekly (e.g., Monday at 22:56).

#### Rotate to Monthly Snapshot

```bash
snapback monthly
```

Promotes week-4 to month-0, then rotates monthly snapshots. Run on the 1st of each month (e.g., 01:00).

#### Dry-Run Mode

```bash
snapback --dry-run hourly
```

Simulates the backup operation without modifying any files. Use this to test configuration changes safely.

### Recovery Operations

#### Full Recovery from Snapshot

```bash
snapback recover hour-3
```

**WARNING**: Overwrites current files with the snapshot version. Use with caution.

Restores all directories from the specified snapshot, replacing current files. Useful for complete system rollback.

#### Recover Deleted Files Only

```bash
snapback undel hour-1
```

Restores only files that are missing from the current directories. Existing files are NOT overwritten. Safe for recovering accidentally deleted files.

**Example**: You deleted a file 2 hours ago. Run `snapback undel hour-2` to restore it without affecting other files.

#### Tag a Snapshot for Preservation

```bash
snapback tag hour-1 before-upgrade
```

Creates a named copy of a snapshot that won't be automatically deleted by rotation. Useful before system upgrades, major changes, or experiments.

**Example**: Before upgrading software:

```bash
snapback hourly              # Create fresh snapshot
snapback tag hour-0 pre-v2-upgrade
# ... perform upgrade ...
# If something breaks:
snapback recover pre-v2-upgrade
```

#### Delete Specific Path from Latest Snapshot

```bash
snapback delete /home/user/large-file.iso
```

Removes a specific path from the hour-0 snapshot. Useful for removing accidentally backed-up large files or sensitive data.

**Note**: Only removes from hour-0. Other snapshots are not affected.

## Usage Examples

### Example 1: First-Time Setup

Complete walkthrough from installation to first backup:

```bash
# 1. Install snapback
pip install snapback
# or: uv pip install snapback

# 2. Create configuration
cat > ~/.snapshotrc << 'EOF'
DIRS="/home/user/Documents /home/user/Projects"
TARGETBASE="/home/user/.Snapshots"
RSYNC_PARAMS="--max-size=50m"
EOF

# 3. Initialize snapshot structure
snapback init

# 4. Verify structure was created
ls ~/.Snapshots/
# Output: hour-0  hour-1  ...  day-0  ...  week-0  ...  month-0  ...

# 5. Create first backup
snapback hourly

# 6. Verify backup contains your files
ls ~/.Snapshots/hour-0/Documents/
```

### Example 2: Recovering Accidentally Deleted Files

You deleted a file 3 hours ago and need it back:

```bash
# 1. Check which snapshots contain the file
snapls myfile.txt

# 2. Recover only deleted/missing files from 3 hours ago
snapback undel hour-3

# 3. Verify the file was restored
ls -l myfile.txt
```

### Example 3: Full System Rollback

You made changes that broke your system. Rollback to yesterday:

```bash
# 1. List available snapshots
snapback list

# 2. Perform full recovery from day-1 (yesterday)
snapback recover day-1

# All files are now restored to yesterday's state
```

### Example 4: Tagging Before Risky Operations

Before making major system changes:

```bash
# 1. Create a fresh backup
snapback hourly

# 2. Tag it for safekeeping
snapback tag hour-0 before-config-changes

# 3. Make your changes
nano /etc/important-config.conf

# 4. If something breaks, recover:
snapback recover before-config-changes

# The tagged snapshot won't be deleted by rotation
```

### Example 5: Testing Configuration Safely

Before enabling a new rsync filter:

```bash
# 1. Edit configuration
nano ~/.snapshotrc
# Add: RSYNC_PARAMS="--exclude=*.log"

# 2. Test with dry-run
snapback --dry-run hourly

# 3. Review output to verify behavior

# 4. If satisfied, run actual backup
snapback hourly
```

### Example 6: Removing Large Accidentally-Backed-Up Files

You accidentally backed up a 10GB ISO file:

```bash
# 1. Remove from latest snapshot
snapback delete /home/user/Downloads/ubuntu.iso

# 2. Verify removal
ls -lh ~/.Snapshots/hour-0/Downloads/
```

## Automated Backups with Cron

For automatic, hands-off backups, configure cron to run snapback on a schedule.

### Recommended Cron Schedule

```bash
# Edit your crontab
crontab -e
```

Add these entries (find your snapback installation path with `which snapback`):

```cron
# Hourly backup (every hour at :00)
0 * * * * /usr/local/bin/snapback hourly >/dev/null 2>&1

# Daily rotation (23:58 every day)
58 23 * * * /usr/local/bin/snapback daily >/dev/null 2>&1

# Weekly rotation (Monday at 22:56)
56 22 * * 1 /usr/local/bin/snapback weekly >/dev/null 2>&1

# Monthly rotation (1st of month at 01:00)
0 1 1 * * /usr/local/bin/snapback monthly >/dev/null 2>&1
```

**Important**: Replace `/usr/local/bin/snapback` with your actual installation path (use `which snapback` to find it).

### Timing Rationale

- **Hourly**: Top of every hour (clean, predictable)
- **Daily**: 23:58 (just before midnight, captures end-of-day state)
- **Weekly**: Monday 22:56 (before daily rotation, captures end-of-week)
- **Monthly**: 1st at 01:00 (after midnight, captures end-of-month)

The staggered timing ensures each rotation completes before the next begins.

### Enable Logging (Optional)

To log backup activity instead of discarding output:

```cron
# Log to file
0 * * * * /usr/local/bin/snapback hourly >> /var/log/snapback.log 2>&1

# Log with timestamps (requires 'ts' utility from moreutils package)
0 * * * * /usr/local/bin/snapback hourly 2>&1 | ts >> /var/log/snapback.log
```

### Verify Cron is Working

```bash
# Check cron service is running
systemctl status cron    # Linux (systemd)
service cron status      # Linux (sysvinit)
# macOS uses launchd, cron jobs work automatically

# Wait an hour, then check if backup was created
ls -lt ~/.Snapshots/
```

## Utility Scripts

### snapls - List File History Across Snapshots

Lists all snapshots containing a specific file, sorted chronologically from newest to oldest.

**Syntax**:
```bash
snapls <filename>
# or
snapback list <filename>
```

**Example**:
```bash
snapls config.yaml
```

**Output**:
```
Found 5 version(s) of 'config.yaml':

hour-0  (0 hours ago)    /home/user/.Snapshots/hour-0/config.yaml
hour-1  (1 hour ago)     /home/user/.Snapshots/hour-1/config.yaml
hour-2  (2 hours ago)    /home/user/.Snapshots/hour-2/config.yaml
day-0   (1 day ago)      /home/user/.Snapshots/day-0/config.yaml
week-0  (1 week ago)     /home/user/.Snapshots/week-0/config.yaml
```

The tool automatically sorts snapshots chronologically and displays age descriptions.

### snapdiff - Compare File Versions

Compares the current version of a file with a version N snapshots ago using vimdiff (or another diff tool).

**Syntax**:
```bash
snapdiff N <filename>
# or
snapback diff <filename> N
```

**Example**:
```bash
# Compare current file with version 3 snapshots ago
snapdiff 3 config.yaml

# Use different diff tool
snapback diff config.yaml 3 --tool meld

# Show text diff instead of opening editor
snapback diff config.yaml 3 --text
```

This opens your configured diff tool showing the differences between your current file and the version from N snapshots back.

**Requirements**: vimdiff (default) or another diff tool must be installed.

**Tip**: Use `snapls <filename>` first to see which snapshots contain the file, then use `snapdiff` to compare specific versions.

## How It Works

### Four-Tier Retention System

snapback maintains 46 snapshots across four tiers with automatic rotation:

```
┌─────────────────────────────────────────────────────────┐
│ HOURLY (23 snapshots)                                   │
│ hour-0 → hour-1 → hour-2 → ... → hour-23                │
│                                         ↓                │
│ DAILY (7 snapshots)                                      │
│ day-0 → day-1 → day-2 → ... → day-7                     │
│                                  ↓                       │
│ WEEKLY (4 snapshots)                                     │
│ week-0 → week-1 → week-2 → ... → week-4                 │
│                                    ↓                     │
│ MONTHLY (12 snapshots)                                   │
│ month-0 → month-1 → month-2 → ... → month-12            │
│                                          ↓               │
│                                     [deleted]            │
└─────────────────────────────────────────────────────────┘
```

### Rotation Flow

1. **Hourly** (`--hourly`):
   - hour-23 is deleted
   - All snapshots shift right (hour-0 → hour-1, hour-1 → hour-2, etc.)
   - hour-0 is hard-linked from the new hour-1
   - rsync updates hour-0 with current data

2. **Daily** (`--daily`):
   - hour-23 is promoted to day-0
   - day-7 is deleted
   - All daily snapshots shift right

3. **Weekly** (`--weekly`):
   - day-7 is promoted to week-0
   - week-4 is deleted
   - All weekly snapshots shift right

4. **Monthly** (`--monthly`):
   - week-4 is promoted to month-0
   - month-12 is deleted
   - All monthly snapshots shift right

### Hard Link Magic

The key to snapback's space efficiency is hard links created by `cp -al`:

- **Hard links** point to the same data on disk
- Multiple filenames can reference the same file content
- Disk space is only consumed once, regardless of how many hard links exist
- When you modify a file, only that file's new version consumes additional space
- Unchanged files remain as hard links, using zero additional space

**Example**:
```bash
# Initial backup: 10GB of files
snapback init
snapback hourly
# Disk usage: 10GB

# 23 hours pass, you modify 500MB of files
# 23 hourly snapshots exist
snapback hourly  # (run 23 times over 23 hours)
# Disk usage: 10GB (original) + 500MB (changes) = 10.5GB
# Not: 10GB × 23 = 230GB!
```

### Storage Efficiency

- **Typical usage**: 1.5-3x source data size for 46 snapshots
- **Full copies**: 46x source data size
- **Savings**: 93-95% reduction in storage requirements

### rsync Synchronization

Each hourly backup uses rsync with the `--delete` flag:

```bash
rsync -av --delete $RSYNC_PARAMS $RSYNCPARAMS SOURCE/. TARGET/.
```

- Efficiently copies only changed files
- Removes files from backup that were deleted from source
- Preserves permissions, timestamps, symlinks
- Supports custom filters via `RSYNC_PARAMS`

### Snapshot Limits

- **Maximum snapshots**: 46 total (23h + 7d + 4w + 12m)
- **Time coverage**: ~1 year of history
- **Tested scale**: ~100,000 files, ~100GB datasets
- **Directory structure**: All snapshots in `$TARGETBASE`

## Python Implementation

snapback 2.0 is a complete rewrite in Python 3.10+, replacing the original Bash implementation while maintaining 100% command compatibility and functional behavior.

### Architecture

The Python implementation consists of seven core modules in `src/snapback/`:

- **cli.py** (625 lines) - Command-line interface with argparse
  - Modern subcommand-based CLI (like git, docker)
  - Entry points for `snapback`, `snapls`, `snapdiff` commands
  - Comprehensive help text and error messages

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

- **diff.py** - File comparison utilities
  - Integration with vimdiff, meld, or other diff tools
  - Text-based diff output
  - Multi-snapshot file history

- **utils.py** - Utility functions
  - Path handling and validation
  - Error handling and logging
  - Common helper functions

### Benefits of Python Implementation

1. **Better Error Handling**: Clear, informative error messages with proper exception handling
2. **Comprehensive Testing**: 118 unit tests with pytest, >90% code coverage
3. **Modern Packaging**: Installable via pip/uv with proper dependency management
4. **Type Safety**: Python type hints throughout codebase for better IDE support
5. **Maintainability**: Modular code structure with clear separation of concerns
6. **Documentation**: Comprehensive docstrings and inline documentation
7. **Cross-Platform**: Better Windows support (via WSL) compared to Bash

### Testing

The test suite includes 118 comprehensive unit tests covering:

- Configuration loading and validation
- Backup operations and rsync integration
- Snapshot rotation logic
- Recovery operations (full and selective)
- Edge cases and error conditions
- Command-line interface

Run tests with:

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/snapback --cov-report=html
```

### Development Setup

To contribute or modify snapback:

```bash
# Clone repository
git clone https://github.com/meirm/snapback.git
cd snapback

# Install in development mode with all dependencies
uv pip install -e ".[dev]"

# Run tests
pytest tests/

# Run linting
ruff check src/ tests/

# Run type checking
mypy src/
```

### Version 2.0 Changes

Version 2.0.0 represents a major milestone with breaking changes in CLI syntax:

**Old Bash Syntax**:
```bash
./snapback --init
./snapback --hourly
./snapback --recover hour-1
```

**New Python Syntax**:
```bash
snapback init
snapback hourly
snapback recover hour-1
```

**Functional Compatibility**:
- Same configuration file format (`~/.snapshotrc`)
- Same snapshot directory structure
- Same rotation logic and retention policies
- Same rsync integration and hard link behavior
- Same recovery mechanisms

The only breaking change is command syntax (flags → subcommands), which provides better UX following modern CLI conventions.

## Container Testing

snapback includes comprehensive container-based testing infrastructure using **Podman** (recommended) or Docker. This allows you to test snapback in isolated environments with extreme scenarios including large files (>1GB), high file counts (>100k), and stress testing.

### Quick Start with Containers

**Using Podman (recommended):**
```bash
# Build the image
make podman-build

# Run tests
make podman-test

# Run extreme scenarios
make podman-test-extreme
```

**Using Docker:**
```bash
# Build the image
make docker-build

# Run tests
make docker-test

# Run extreme scenarios
make docker-test-extreme
```

**Auto-detect container runtime:**
```bash
# Automatically uses podman if available, falls back to docker
make container-build
make container-test
```

### Available Test Scenarios

The test suite includes 10 extreme scenarios:

1. **Large Single File Backup** (>1GB files)
2. **High File Count** (>100k small files)
3. **Deep Directory Nesting** (>50 levels)
4. **Rapid Backup Cycles** (24 hourly snapshots in minutes)
5. **Full Rotation Cycle** (hourly → daily → weekly → monthly)
6. **Disk Space Constraints**
7. **Permission Edge Cases**
8. **Corruption Recovery**
9. **Hard Link Verification**
10. **rsync Parameter Edge Cases**

### Container Testing Documentation

For comprehensive container testing documentation including:
- Detailed Podman and Docker instructions
- All test scenario descriptions
- Performance benchmarking guide
- CI/CD integration examples
- Troubleshooting guide

See **[DOCKER_TESTING.md](DOCKER_TESTING.md)** for complete documentation.

### Makefile Commands

```bash
# Container building
make container-build        # Auto-detect runtime
make docker-build          # Use Docker
make podman-build          # Use Podman

# Running tests
make container-test        # Quick test (auto-detect)
make docker-test           # Quick test (Docker)
make podman-test           # Quick test (Podman)
make docker-test-extreme   # Extreme scenarios (Docker)
make podman-test-extreme   # Extreme scenarios (Podman)

# Interactive shell
make docker-shell          # Enter Docker container
make podman-shell          # Enter Podman container

# Benchmarking
make docker-bench          # Performance benchmarks

# Cleanup
make docker-clean          # Clean Docker resources
make podman-clean          # Clean Podman resources
```

## Troubleshooting

### Config file not found

**Error**: `Configuration file not found: ~/.snapshotrc`

**Solution**: Create the configuration file:
```bash
snapback sampleconfig > ~/.snapshotrc
nano ~/.snapshotrc  # Edit DIRS and TARGETBASE
```

### Permission denied errors

**Error**: `Permission denied` when creating snapshots

**Solutions**:
- Ensure write access to `$TARGETBASE` directory:
  ```bash
  mkdir -p ~/.Snapshots
  chmod 755 ~/.Snapshots
  ```
- If backing up system directories, run with sudo:
  ```bash
  sudo snapback hourly
  ```
- Check source directory permissions

### Disk space issues

**Error**: `No space left on device`

**Solutions**:
- Check available disk space:
  ```bash
  df -h $TARGETBASE
  ```
- Review and tighten `RSYNC_PARAMS` filters:
  ```bash
  RSYNC_PARAMS="--max-size=10m --exclude=*.iso --exclude=node_modules"
  ```
- Delete old tagged snapshots you no longer need
- Move `TARGETBASE` to a larger disk

### Cron backups not running

**Problem**: Backups aren't happening automatically

**Solutions**:
- Verify cron service is running:
  ```bash
  systemctl status cron    # Linux
  ```
- Check crontab syntax:
  ```bash
  crontab -l
  ```
- Use absolute paths in crontab:
  ```bash
  0 * * * * /usr/local/bin/snapback hourly
  ```
- Check cron logs:
  ```bash
  grep CRON /var/log/syslog    # Linux
  grep cron /var/log/system.log # macOS
  ```
- Test manually to verify configuration:
  ```bash
  /usr/local/bin/snapback hourly
  ```

### Recovery not working

**Error**: Files not restored as expected

**Solutions**:
- Verify snapshot exists:
  ```bash
  ls -la ~/.Snapshots/hour-1/
  ```
- Check path syntax in recovery command:
  ```bash
  snapback recover hour-1  # Correct
  snapback recover ~/.Snapshots/hour-1  # Wrong
  ```
- For selective recovery, use `undel` instead of `recover`
- Verify source directories in `~/.snapshotrc` match recovery target

### rsync errors

**Error**: `rsync: command not found` or rsync version issues

**Solutions**:
- Install rsync:
  ```bash
  # Ubuntu/Debian
  sudo apt-get install rsync

  # macOS
  brew install rsync

  # RHEL/CentOS
  sudo yum install rsync
  ```
- Verify version is 3.0+:
  ```bash
  rsync --version
  ```

### Debugging tips

- Use `--dry-run` to test without modifying files:
  ```bash
  snapback --dry-run hourly
  ```
- Run commands manually to see full output:
  ```bash
  snapback hourly
  # (don't redirect to /dev/null)
  ```
- Check snapshot directory structure:
  ```bash
  tree -L 1 ~/.Snapshots/
  ```
- Verify hard links are working:
  ```bash
  # Same inode number means hard link
  ls -li ~/.Snapshots/hour-0/path/to/file
  ls -li ~/.Snapshots/hour-1/path/to/file
  ```

## Limitations

Be aware of these current limitations:

- **Manual crontab setup required**: No automated installation of cron jobs
- **No built-in snapshot verification**: No integrity checking or corruption detection
- **No GUI or interactive recovery browsing**: Command-line only
- **Single-host only**: No remote backup server support (local snapshots only)
- **No bandwidth throttling**: rsync runs at full speed
- **No email notifications**: No built-in alerts for failures or completion
- **Tested scale**: Validated with ~100,000 files and ~100GB datasets
- **No incremental file-level tracking**: Entire files are updated, not byte-level deltas
- **No encryption**: Snapshots stored in plain text (use encrypted filesystem if needed)
- **No compression**: Files stored as-is (use filesystem compression if needed)

## Best Practices

### Testing and Validation

- **Test recovery procedures regularly**: Verify you can actually restore files
- **Use `--dry-run` before production**: Test configuration changes safely
- **Verify first backup**: Check that hour-0 contains expected files
- **Test selective recovery**: Practice using `--undel` before you need it urgently

### Tagging and Safety

- **Tag before major changes**: Use `--tag` before system upgrades, migrations, or risky operations
- **Create pre-deployment snapshots**: Tag before deploying new code or configurations
- **Document tags**: Use descriptive tag names (`pre-upgrade-v2.0`, `before-refactor`, etc.)

### Monitoring and Maintenance

- **Monitor disk space regularly**: Set up alerts when disk usage exceeds 80%
- **Review backup logs**: Check for rsync errors or failures
- **Validate snapshot integrity**: Periodically verify files can be accessed
- **Clean up old tags**: Remove obsolete tagged snapshots to free space

### Configuration

- **Keep config backed up separately**: Store `~/.snapshotrc` outside the backup system
- **Document custom rsync filters**: Comment your `RSYNC_PARAMS` for future reference
- **Test rsync filters**: Use `--dry-run` to verify exclusions work as expected
- **Start with generous filters**: Begin with large `--max-size`, then tighten if needed

### Security

- **Protect snapshot directory**: Ensure proper permissions on `$TARGETBASE`
- **Use encrypted filesystems**: If backing up sensitive data, encrypt the target disk
- **Limit access**: Restrict who can run recovery commands
- **Audit regularly**: Review what's being backed up to avoid sensitive data leaks

### Performance

- **Schedule backups during low activity**: Run hourly backups during non-peak hours if possible
- **Use SSD for snapshots**: Faster disk I/O improves backup and recovery performance
- **Monitor rsync performance**: Adjust filters if backups take too long
- **Consider separate disks**: Store snapshots on a different physical disk than source data

## License

snapback is licensed under the **GNU General Public License v2.0 (GPLv2)**.

See the [LICENSE](LICENSE) file for full license text.

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

## Contributing

Contributions are welcome! Whether it's bug reports, feature requests, documentation improvements, or code contributions, your help is appreciated.

### How to Contribute

1. **Report bugs**: Open an issue describing the problem, steps to reproduce, and your environment
2. **Request features**: Open an issue explaining the feature and use case
3. **Submit pull requests**: Fork the repository, create a feature branch, and submit a PR
4. **Improve documentation**: Fix typos, clarify instructions, add examples

### Development

When contributing code:

```bash
# 1. Fork and clone the repository
git clone https://github.com/yourusername/snapback.git
cd snapback

# 2. Install development dependencies
uv pip install -e ".[dev]"

# 3. Run tests before making changes
pytest tests/ -v

# 4. Make your changes
# ... edit code ...

# 5. Run linting and tests
ruff check src/ tests/
pytest tests/ -v

# 6. Update documentation as needed
# ... edit README.md, docstrings, etc. ...

# 7. Commit and push
git add .
git commit -m "Your descriptive commit message"
git push origin your-feature-branch
```

**Code Style Guidelines**:
- Follow Python PEP 8 style guide
- Use type hints throughout code
- Write comprehensive docstrings for all functions and classes
- Maintain test coverage above 90%
- Test with `--dry-run` before committing backup operation changes
- Test on multiple platforms if possible (Linux, macOS, BSD)

### Support

- **Issues**: Open a GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions or general discussion
- **Security**: For security vulnerabilities, please email privately (do not open public issues)

---

**Made with ❤️ for reliable, transparent backups**
