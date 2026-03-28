"""Core orchestration — scan, extract, classify, move."""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from tidydesk.classify import classify_files, discover_projects
from tidydesk.config import resolve_path
from tidydesk.extract import ensure_ocr_binary, extract_content
from tidydesk.manifest import log_moves, move_file

log = logging.getLogger("tidydesk")

SKIP_NAMES = {".DS_Store", ".localized", "Icon\r"}
SKIP_SUFFIXES = {".crdownload", ".part", ".tmp", ".download"}
SKIP_DIRS = {"node_modules", "__pycache__", ".git", "venv", ".venv"}


def get_existing_folders(organize_to: Path) -> list[str]:
    """Get current subfolder names in the organize-to directory."""
    if not organize_to.exists():
        return []
    return sorted([
        item.name for item in organize_to.iterdir()
        if item.is_dir() and not item.name.startswith(".")
    ])


def collect_files(watch_folders: list[str], organize_to: Path,
                  min_age_minutes: int) -> list[Path]:
    """Gather files from watch folders."""
    files = []
    cutoff = datetime.now() - timedelta(minutes=min_age_minutes)

    for folder_str in watch_folders:
        source_dir = resolve_path(folder_str)
        if not source_dir.exists():
            continue

        is_organize_target = source_dir == organize_to

        for item in source_dir.iterdir():
            if item.name.startswith(".") or item.name in SKIP_NAMES:
                continue
            if item.suffix.lower() in SKIP_SUFFIXES:
                continue
            # In the organize-to dir (e.g. Desktop), skip directories
            # (they're project folders we created)
            if is_organize_target and item.is_dir():
                continue
            # In other dirs (e.g. Downloads), skip dev artifact dirs
            if not is_organize_target and item.is_dir() and item.name in SKIP_DIRS:
                continue
            try:
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if mtime > cutoff:
                    continue
            except Exception:
                continue
            files.append(item)

    return files


def run(config: dict, dry_run: bool = False) -> int:
    """Run the organizer. Returns number of files organized."""
    organize_to = resolve_path(config["organize_to"])
    batch_size = config["batch_size"]
    max_chars = config["max_content_chars"]

    ensure_ocr_binary()

    # Collect files
    files = collect_files(
        config["watch_folders"], organize_to, config["min_age_minutes"],
    )
    if not files:
        log.info("Nothing to organize. Desktop is clean.")
        return 0

    log.info("Found %d files to organize", len(files))

    # Extract content
    log.info("Extracting content...")
    contents = {}
    for f in files:
        if f.is_file():
            content = extract_content(f, max_chars)
            if content:
                contents[f] = content

    log.info("Extracted content from %d files", len(contents))

    # Discover project context
    projects = discover_projects(config["context_folders"])
    existing_folders = get_existing_folders(organize_to)

    # Classify and move in batches
    all_entries = []
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(files) + batch_size - 1) // batch_size
        log.info("Classifying batch %d/%d (%d files)...",
                 batch_num, total_batches, len(batch))

        try:
            batch_contents = {f: contents[f] for f in batch if f in contents}
            classifications = classify_files(
                batch, batch_contents, existing_folders, projects, config,
            )
        except Exception as e:
            log.error("Classification failed: %s", e)
            continue

        class_map = {c["index"]: c for c in classifications}

        for batch_idx, f in enumerate(batch):
            cls = class_map.get(batch_idx)
            if not cls:
                log.warning("  No classification for %s, skipping", f.name)
                continue

            folder = cls["folder"].strip("/").split("/")[0].strip()
            if not folder or folder.startswith("."):
                folder = "inbox"

            if dry_run:
                log.info("  [DRY RUN] %s -> %s/ (%s)",
                         f.name, folder, cls.get("reason", ""))
                if folder not in existing_folders:
                    existing_folders.append(folder)
                continue

            entry = move_file(f, folder, cls.get("reason", ""), organize_to)
            if entry:
                all_entries.append(entry)
                if folder not in existing_folders:
                    existing_folders.append(folder)

    if all_entries:
        log_moves(all_entries)

    count = len(all_entries) if not dry_run else len(files)
    return count
