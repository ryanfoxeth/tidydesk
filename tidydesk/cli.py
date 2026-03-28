"""TidyDesk CLI — argparse-based command interface."""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from tidydesk import __version__
from tidydesk.config import (
    CONFIG_FILE, LOG_FILE, MANIFEST_FILE, STATE_DIR,
    get_config_or_exit, load_config, setup_wizard,
)

log = logging.getLogger("tidydesk")


def _setup_logging():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(),
        ],
    )


def cmd_setup(args):
    setup_wizard()


def cmd_run(args):
    from tidydesk.organize import run

    config = get_config_or_exit()
    dry_run = args.dry_run

    if dry_run:
        log.info("TidyDesk — dry run")
    else:
        log.info("TidyDesk — organizing...")

    count = run(config, dry_run=dry_run)

    if count == 0:
        return
    if dry_run:
        log.info("Would organize %d files.", count)
    else:
        log.info("Organized %d files.", count)


def cmd_undo(args):
    from tidydesk.manifest import undo_last_run

    log.info("TidyDesk — undoing last run...")
    count = undo_last_run()
    if count > 0:
        log.info("Restored %d files.", count)
    else:
        log.info("Nothing to undo.")


def cmd_install(args):
    from tidydesk.scheduler import install

    config = get_config_or_exit()
    log.info("TidyDesk — installing schedule...")
    install(config)


def cmd_uninstall(args):
    from tidydesk.scheduler import uninstall

    log.info("TidyDesk — removing schedule...")
    uninstall()


def cmd_status(args):
    from tidydesk.scheduler import get_schedule_info

    config = load_config()
    has_key = bool(config.get("api_key"))

    print(f"TidyDesk v{__version__}")
    print(f"  Config:    {CONFIG_FILE}" + (" (exists)" if CONFIG_FILE.exists() else " (not found)"))
    print(f"  API key:   {'configured' if has_key else 'not set — run: tidydesk setup'}")
    print(f"  Model:     {config.get('model', 'not set')}")
    print(f"  Watch:     {', '.join(config.get('watch_folders', []))}")
    print(f"  Organize:  {config.get('organize_to', 'not set')}")

    # Schedule
    schedule = get_schedule_info(config)
    print(f"  Schedule:  {schedule or 'not installed'}")

    # Last run
    if MANIFEST_FILE.exists():
        lines = MANIFEST_FILE.read_text().strip().splitlines()
        if lines:
            last = json.loads(lines[-1])
            ts = last["timestamp"][:19]
            # Count files in last run
            last_ts_prefix = last["timestamp"][:13]
            last_run_count = sum(
                1 for line in lines
                if json.loads(line)["timestamp"][:13] == last_ts_prefix
            )
            print(f"  Last run:  {ts} ({last_run_count} files)")
        else:
            print(f"  Last run:  never")
    else:
        print(f"  Last run:  never")

    # Context
    ctx = config.get("context_folders", [])
    if ctx:
        print(f"  Context:   {', '.join(ctx)}")


def main():
    parser = argparse.ArgumentParser(
        prog="tidydesk",
        description="AI-powered file organizer for macOS. Sorts by purpose, not file type.",
    )
    parser.add_argument("--version", action="version", version=f"tidydesk {__version__}")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # setup
    sp_setup = subparsers.add_parser("setup", help="Configure TidyDesk (API key, folders, model)")
    sp_setup.set_defaults(func=cmd_setup)

    # run
    sp_run = subparsers.add_parser("run", help="Organize files now")
    sp_run.add_argument("--dry-run", action="store_true", help="Show what would happen without moving files")
    sp_run.set_defaults(func=cmd_run)

    # undo
    sp_undo = subparsers.add_parser("undo", help="Reverse the last run")
    sp_undo.set_defaults(func=cmd_undo)

    # install
    sp_install = subparsers.add_parser("install", help="Install daily schedule (launchd)")
    sp_install.set_defaults(func=cmd_install)

    # uninstall
    sp_uninstall = subparsers.add_parser("uninstall", help="Remove daily schedule")
    sp_uninstall.set_defaults(func=cmd_uninstall)

    # status
    sp_status = subparsers.add_parser("status", help="Show current configuration and status")
    sp_status.set_defaults(func=cmd_status)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    _setup_logging()
    args.func(args)
