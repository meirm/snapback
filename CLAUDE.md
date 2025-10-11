# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**snapback** is a snapshot-based backup system written in Bash that uses rsync and hard links to create space-efficient, incremental backups with multiple retention policies (hourly, daily, weekly, monthly).

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
./snapback --init

# Generate sample configuration
./snapback --sampleconfig
```

### Backup Operations

```bash
# Create hourly snapshot (run via cron hourly)
./snapback --hourly

# Rotate to daily snapshot (run via cron at 23:58)
./snapback --daily

# Rotate to weekly snapshot (run via cron Monday 22:56)
./snapback --weekly

# Rotate to monthly snapshot (run via cron 1st of month 01:00)
./snapback --monthly

# Dry-run mode (doesn't actually modify files)
./snapback --dry-run --hourly
```

### Recovery Operations

```bash
# Recover deleted files from a snapshot (only copies missing files)
./snapback --undel hour-1

# Full recovery from snapshot (overwrites current files)
./snapback --recover hour-3

# Tag a snapshot for preservation
./snapback --tag hour-1 before-upgrade

# Delete a specific path from hour-0 snapshot
./snapback --delete /path/to/directory
```

### Utility Scripts

```bash
# List all snapshots containing a file
./snapls.sh myfile.txt

# Compare file with version N snapshots ago
./snapdiff.sh N myfile.txt
```

## Recommended Crontab Configuration

```cron
# Hourly backup
0 * * * * /path/to/snapback --hourly >/dev/null 2>&1

# Daily rotation (23:58)
58 23 * * * /path/to/snapback --daily >/dev/null 2>&1

# Weekly rotation (Monday 22:56)
56 22 * * 1 /path/to/snapback --weekly >/dev/null 2>&1

# Monthly rotation (1st of month 01:00)
0 1 1 * * /path/to/snapback --monthly >/dev/null 2>&1
```

## Development Notes

### Critical Implementation Details

1. **Hard Link Creation**: `cp -al` creates hard links instead of copies. This is central to space efficiency.

2. **Rotation Order**: The rotation sequences use `tac` (reverse) to avoid overwriting snapshots during the shift operation.

3. **rsync Parameters**: The `--delete` flag in hourly backups ensures hour-0 mirrors the source exactly (removes files deleted from source).

4. **Two-Phase Variables**: Note both `$RSYNC_PARAMS` and `$RSYNCPARAMS` are used (line 56). This appears intentional for configuration flexibility.

5. **Weekly Rotation Bug Fix**: Line 78 uses `cp -al` instead of `mv` (commented line 77), ensuring day-7 is preserved after promotion to week-0.

### Helper Scripts

- **snapls.sh**: Perl-based script that sorts snapshots by age (converts period names to hours for sorting)
- **snapdiff.sh**: Wrapper around `vimdiff` that compares current file with Nth previous snapshot

### Testing Approach

Always use `--dry-run` flag when testing backup/recovery operations to avoid unintended data modifications.

## License

GPLv2