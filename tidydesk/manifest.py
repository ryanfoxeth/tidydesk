"""Move manifest — JSONL log of all file moves with undo support."""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from tidydesk.config import MANIFEST_FILE

log = logging.getLogger("tidydesk")


def log_moves(entries: list[dict]):
    """Append move entries to the manifest."""
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_FILE, "a") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def move_file(source: Path, folder_name: str, reason: str,
              organize_to: Path) -> dict | None:
    """Move a file into the target folder. Returns manifest entry or None."""
    target_dir = organize_to / folder_name
    target_dir.mkdir(exist_ok=True)

    target = target_dir / source.name
    if target.exists():
        stem, suffix = source.stem, source.suffix
        counter = 1
        while target.exists():
            target = target_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    try:
        shutil.move(str(source), str(target))
        entry = {
            "timestamp": datetime.now().isoformat(),
            "source": str(source),
            "destination": str(target),
            "folder": folder_name,
            "reason": reason,
        }
        log.info("  %s -> %s/ (%s)", source.name, folder_name, reason)
        return entry
    except Exception as e:
        log.error("  Failed to move %s: %s", source.name, e)
        return None


def undo_last_run() -> int:
    """Reverse the most recent run. Returns number of files restored."""
    if not MANIFEST_FILE.exists():
        log.info("No manifest found, nothing to undo.")
        return 0

    lines = MANIFEST_FILE.read_text().strip().splitlines()
    if not lines:
        log.info("Manifest is empty.")
        return 0

    # Find the last run's timestamp block (same YYYY-MM-DDTHH)
    last_entry = json.loads(lines[-1])
    last_ts = last_entry["timestamp"][:13]

    undone = 0
    remaining = []
    for line in lines:
        entry = json.loads(line)
        if entry["timestamp"][:13] == last_ts:
            src = Path(entry["destination"])
            dst = Path(entry["source"])
            if src.exists() and not dst.exists():
                shutil.move(str(src), str(dst))
                log.info("  Restored: %s", dst.name)
                undone += 1
            else:
                remaining.append(line)
        else:
            remaining.append(line)

    MANIFEST_FILE.write_text("\n".join(remaining) + "\n" if remaining else "")
    return undone
