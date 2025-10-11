"""Command-line interface for snapback.

This module provides the main CLI entry points for snapback operations.
"""

import argparse
import sys
from pathlib import Path

from .backup import BackupManager
from .config import Config
from .diff import DiffManager
from .recovery import RecoveryManager
from .snapshot import SnapshotManager
from .utils import (
    find_file_in_snapshots,
    format_file_listing,
    get_snapshot_age_description,
    sort_snapshots_by_age,
)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for snapback.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="snapback",
        description="Snapshot-based backup system using rsync and hard links",
        epilog="Run 'snapback <command> --help' for command-specific help",
    )

    # Global options
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Path to configuration file (default: ~/.snapshotrc)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # init command
    subparsers.add_parser(
        "init",
        help="Initialize snapshot directory structure",
    )

    # sampleconfig command
    subparsers.add_parser(
        "sampleconfig",
        help="Generate a sample configuration file",
    )

    # hourly command
    subparsers.add_parser(
        "hourly",
        help="Create hourly snapshot",
    )

    # daily command
    subparsers.add_parser(
        "daily",
        help="Rotate to daily snapshot",
    )

    # weekly command
    subparsers.add_parser(
        "weekly",
        help="Rotate to weekly snapshot",
    )

    # monthly command
    subparsers.add_parser(
        "monthly",
        help="Rotate to monthly snapshot",
    )

    # recover command
    parser_recover = subparsers.add_parser(
        "recover",
        help="Recover all files from a snapshot",
    )
    parser_recover.add_argument(
        "snapshot",
        help="Snapshot name to recover from (e.g., hour-1)",
    )

    # undel command
    parser_undel = subparsers.add_parser(
        "undel",
        help="Recover only deleted files from a snapshot",
    )
    parser_undel.add_argument(
        "snapshot",
        help="Snapshot name to recover from (e.g., hour-1)",
    )

    # tag command
    parser_tag = subparsers.add_parser(
        "tag",
        help="Create a named tag for a snapshot",
    )
    parser_tag.add_argument(
        "snapshot",
        help="Snapshot name to tag (e.g., hour-1)",
    )
    parser_tag.add_argument(
        "tagname",
        help="Custom name for the tagged snapshot",
    )

    # delete command
    parser_delete = subparsers.add_parser(
        "delete",
        help="Delete a path from hour-0 snapshot",
    )
    parser_delete.add_argument(
        "path",
        help="Path to delete from hour-0",
    )

    # list command
    parser_list = subparsers.add_parser(
        "list",
        help="List snapshots or find files in snapshots",
    )
    parser_list.add_argument(
        "filename",
        nargs="?",
        help="Optional: filename to search for in snapshots",
    )
    parser_list.add_argument(
        "--tags",
        action="store_true",
        help="List only tagged snapshots",
    )

    # diff command
    parser_diff = subparsers.add_parser(
        "diff",
        help="Compare file with previous version",
    )
    parser_diff.add_argument(
        "filename",
        help="File to compare",
    )
    parser_diff.add_argument(
        "periods",
        type=int,
        nargs="?",
        default=1,
        help="Number of periods to go back (default: 1)",
    )
    parser_diff.add_argument(
        "--tool",
        default="vimdiff",
        help="Diff tool to use (default: vimdiff)",
    )
    parser_diff.add_argument(
        "--text",
        action="store_true",
        help="Show text diff instead of launching diff tool",
    )

    return parser


def load_config(config_path: str = None) -> Config:
    """Load configuration with error handling.

    Args:
        config_path: Optional path to config file

    Returns:
        Loaded Config object

    Raises:
        SystemExit: If configuration cannot be loaded
    """
    try:
        return Config.load(config_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("\nRun 'snapback sampleconfig' to create a sample configuration file")
        sys.exit(1)
    except ValueError as e:
        print(f"Error in configuration: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize snapshot directory structure.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    config = load_config(args.config)
    snapshot_manager = SnapshotManager(config)

    print(f"Initializing snapshot directory structure in {config.target_base}")
    snapshot_manager.init_snapshots()
    print("Initialization complete")

    return 0


def cmd_sampleconfig(args: argparse.Namespace) -> int:
    """Generate sample configuration file.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    # Default to ~/.snapshotrc
    config_path = Path.home() / ".snapshotrc"

    if config_path.exists():
        response = input(f"{config_path} already exists. Overwrite? [y/N] ")
        if response.lower() != "y":
            print("Cancelled")
            return 1

    sample_config = """# snapback configuration file
# This file should be saved as ~/.snapshotrc

# Directories to backup (space-separated)
DIRS="$HOME/Documents $HOME/Projects"

# Base directory for snapshots (default: ~/.Snapshots)
TARGETBASE="$HOME/.Snapshots"

# Optional rsync parameters (e.g., --max-size=1.5m to exclude large files)
RSYNC_PARAMS=""
"""

    config_path.write_text(sample_config)
    print(f"Sample configuration written to {config_path}")
    print("\nPlease edit this file to customize your backup settings:")
    print(f"  - Set DIRS to the directories you want to backup")
    print(f"  - Set TARGETBASE to where you want snapshots stored")
    print(f"  - Optionally set RSYNC_PARAMS for additional rsync options")

    return 0


def cmd_hourly(args: argparse.Namespace) -> int:
    """Create hourly snapshot.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    config = load_config(args.config)
    backup_manager = BackupManager(config)

    try:
        backup_manager.hourly_backup(dry_run=args.dry_run)
        return 0
    except Exception as e:
        print(f"Error during hourly backup: {e}", file=sys.stderr)
        return 1


def cmd_daily(args: argparse.Namespace) -> int:
    """Rotate to daily snapshot.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    config = load_config(args.config)
    backup_manager = BackupManager(config)

    try:
        backup_manager.daily_backup(dry_run=args.dry_run)
        return 0
    except Exception as e:
        print(f"Error during daily rotation: {e}", file=sys.stderr)
        return 1


def cmd_weekly(args: argparse.Namespace) -> int:
    """Rotate to weekly snapshot.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    config = load_config(args.config)
    backup_manager = BackupManager(config)

    try:
        backup_manager.weekly_backup(dry_run=args.dry_run)
        return 0
    except Exception as e:
        print(f"Error during weekly rotation: {e}", file=sys.stderr)
        return 1


def cmd_monthly(args: argparse.Namespace) -> int:
    """Rotate to monthly snapshot.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    config = load_config(args.config)
    backup_manager = BackupManager(config)

    try:
        backup_manager.monthly_backup(dry_run=args.dry_run)
        return 0
    except Exception as e:
        print(f"Error during monthly rotation: {e}", file=sys.stderr)
        return 1


def cmd_recover(args: argparse.Namespace) -> int:
    """Recover all files from a snapshot.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    config = load_config(args.config)
    recovery_manager = RecoveryManager(config)

    try:
        recovery_manager.recover(args.snapshot, dry_run=args.dry_run)
        return 0
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_undel(args: argparse.Namespace) -> int:
    """Recover only deleted files from a snapshot.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    config = load_config(args.config)
    recovery_manager = RecoveryManager(config)

    try:
        recovery_manager.undel(args.snapshot, dry_run=args.dry_run)
        return 0
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_tag(args: argparse.Namespace) -> int:
    """Create a named tag for a snapshot.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    config = load_config(args.config)
    recovery_manager = RecoveryManager(config)

    try:
        recovery_manager.tag(args.snapshot, args.tagname, dry_run=args.dry_run)
        return 0
    except (FileNotFoundError, FileExistsError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_delete(args: argparse.Namespace) -> int:
    """Delete a path from hour-0 snapshot.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    config = load_config(args.config)
    recovery_manager = RecoveryManager(config)

    try:
        recovery_manager.delete_path(args.path, dry_run=args.dry_run)
        return 0
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_list(args: argparse.Namespace) -> int:
    """List snapshots or find files in snapshots.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    config = load_config(args.config)

    if args.tags:
        # List tagged snapshots
        recovery_manager = RecoveryManager(config)
        tags = recovery_manager.list_tagged_snapshots()
        if tags:
            print("Tagged snapshots:")
            for tag in tags:
                print(f"  {tag}")
        else:
            print("No tagged snapshots found")
        return 0

    if args.filename:
        # Search for a file in snapshots (snapls functionality)
        results = find_file_in_snapshots(
            args.filename,
            Path(config.target_base),
            config.dirs,
        )

        if not results:
            print(f"File not found in any snapshot: {args.filename}")
            return 1

        print(f"Found {len(results)} version(s) of '{args.filename}':")
        print()

        formatted = format_file_listing(results, Path(config.target_base))
        for line in formatted:
            print(line)

        return 0

    # List all snapshots
    snapshot_manager = SnapshotManager(config)
    snapshots = snapshot_manager.list_snapshots()

    if not snapshots:
        print("No snapshots found")
        print(f"Run 'snapback init' to initialize the snapshot directory structure")
        return 0

    # Sort by age
    snapshots = sort_snapshots_by_age(snapshots)

    print(f"Snapshots in {config.target_base}:")
    print()

    for snapshot in snapshots:
        age_desc = get_snapshot_age_description(snapshot)
        print(f"  {snapshot:15s}  ({age_desc})")

    # Also show tagged snapshots
    recovery_manager = RecoveryManager(config)
    tags = recovery_manager.list_tagged_snapshots()
    if tags:
        print("\nTagged snapshots:")
        for tag in tags:
            print(f"  {tag}")

    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    """Compare file with previous version.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    config = load_config(args.config)
    diff_manager = DiffManager(config)

    try:
        if args.text:
            success = diff_manager.show_file_diff(args.filename, args.periods)
        else:
            success = diff_manager.compare_file_versions(
                args.filename, args.periods, diff_tool=args.tool
            )

        return 0 if success else 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for snapback CLI.

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = create_parser()
    args = parser.parse_args()

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        return 1

    # Dispatch to command handler
    command_map = {
        "init": cmd_init,
        "sampleconfig": cmd_sampleconfig,
        "hourly": cmd_hourly,
        "daily": cmd_daily,
        "weekly": cmd_weekly,
        "monthly": cmd_monthly,
        "recover": cmd_recover,
        "undel": cmd_undel,
        "tag": cmd_tag,
        "delete": cmd_delete,
        "list": cmd_list,
        "diff": cmd_diff,
    }

    handler = command_map.get(args.command)
    if not handler:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1

    return handler(args)


def snapls_main() -> int:
    """Entry point for snapls command (compatibility).

    This provides backward compatibility with the original snapls.sh script.

    Returns:
        Exit code (0 for success)
    """
    parser = argparse.ArgumentParser(
        prog="snapls",
        description="List all snapshots containing a file",
    )
    parser.add_argument("filename", help="File to search for")
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Path to configuration file (default: ~/.snapshotrc)",
    )

    args = parser.parse_args()

    # Use the list command with filename
    args.command = "list"
    args.tags = False

    return cmd_list(args)


def snapdiff_main() -> int:
    """Entry point for snapdiff command (compatibility).

    This provides backward compatibility with the original snapdiff.sh script.

    Returns:
        Exit code (0 for success)
    """
    parser = argparse.ArgumentParser(
        prog="snapdiff",
        description="Compare file with version N snapshots ago",
    )
    parser.add_argument(
        "periods",
        type=int,
        help="Number of periods to go back",
    )
    parser.add_argument("filename", help="File to compare")
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Path to configuration file (default: ~/.snapshotrc)",
    )
    parser.add_argument(
        "--tool",
        default="vimdiff",
        help="Diff tool to use (default: vimdiff)",
    )

    args = parser.parse_args()

    # Use the diff command
    args.command = "diff"
    args.text = False
    args.dry_run = False

    return cmd_diff(args)


if __name__ == "__main__":
    sys.exit(main())
