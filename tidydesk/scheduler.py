"""launchd scheduler — install/uninstall daily auto-run."""

import logging
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("tidydesk")

PLIST_NAME = "com.tidydesk.organizer"
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = LAUNCH_AGENTS / f"{PLIST_NAME}.plist"


def _generate_plist(config: dict) -> str:
    python_path = sys.executable
    hour = config.get("schedule_hour", 9)
    minute = config.get("schedule_minute", 0)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>tidydesk</string>
        <string>run</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{Path.home() / ".tidydesk" / "tidydesk.log"}</string>
    <key>StandardErrorPath</key>
    <string>{Path.home() / ".tidydesk" / "tidydesk.log"}</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>"""


def install(config: dict):
    """Install the launchd schedule."""
    LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)

    plist_content = _generate_plist(config)
    PLIST_PATH.write_text(plist_content)

    # Unload first if already loaded (ignore errors)
    subprocess.run(
        ["launchctl", "bootout", f"gui/{_uid()}/{PLIST_NAME}"],
        capture_output=True,
    )
    result = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{_uid()}", str(PLIST_PATH)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        log.error("Failed to install schedule: %s", result.stderr)
        return False

    hour = config.get("schedule_hour", 9)
    minute = config.get("schedule_minute", 0)
    log.info("Schedule installed: daily at %d:%02d", hour, minute)
    return True


def uninstall():
    """Remove the launchd schedule."""
    subprocess.run(
        ["launchctl", "bootout", f"gui/{_uid()}/{PLIST_NAME}"],
        capture_output=True,
    )
    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
    log.info("Schedule removed.")
    return True


def is_installed() -> bool:
    return PLIST_PATH.exists()


def get_schedule_info(config: dict) -> str | None:
    if not is_installed():
        return None
    hour = config.get("schedule_hour", 9)
    minute = config.get("schedule_minute", 0)
    return f"Daily at {hour}:{minute:02d}"


def _uid() -> int:
    import os
    return os.getuid()
