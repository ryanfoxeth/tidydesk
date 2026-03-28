"""Configuration management for TidyDesk.

All state lives in ~/.tidydesk/:
  config.json   — user settings
  manifest.jsonl — move history
  tidydesk.log  — run logs
  ocr           — compiled OCR binary
"""

import json
import sys
from pathlib import Path

STATE_DIR = Path.home() / ".tidydesk"
CONFIG_FILE = STATE_DIR / "config.json"
MANIFEST_FILE = STATE_DIR / "manifest.jsonl"
LOG_FILE = STATE_DIR / "tidydesk.log"
OCR_BINARY = STATE_DIR / "ocr"

DEFAULTS = {
    "api_key": "",
    "watch_folders": ["~/Desktop", "~/Downloads"],
    "organize_to": "~/Desktop",
    "model": "claude-haiku-4-5-20251001",
    "schedule_hour": 9,
    "schedule_minute": 0,
    "min_age_minutes": 60,
    "batch_size": 25,
    "max_content_chars": 2000,
    "context_folders": [],
}


def ensure_state_dir():
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    ensure_state_dir()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            saved = json.load(f)
        # Merge with defaults so new keys are always present
        config = {**DEFAULTS, **saved}
        return config
    return dict(DEFAULTS)


def save_config(config: dict):
    ensure_state_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def resolve_path(p: str) -> Path:
    return Path(p).expanduser().resolve()


def setup_wizard() -> dict:
    """Interactive setup wizard for first-time configuration."""
    print("TidyDesk Setup")
    print("=" * 40)

    config = load_config()

    # API key
    current_key = config["api_key"]
    if current_key:
        masked = current_key[:10] + "..." + current_key[-4:]
        print(f"\nCurrent API key: {masked}")
        key = input("Anthropic API key (Enter to keep current): ").strip()
        if key:
            config["api_key"] = key
    else:
        key = input("\nAnthropic API key: ").strip()
        if not key:
            print("Error: API key is required. Get one at console.anthropic.com")
            sys.exit(1)
        config["api_key"] = key

    # Watch folders
    default_watch = ", ".join(config["watch_folders"])
    watch = input(f"\nWatch folders [{default_watch}]: ").strip()
    if watch:
        config["watch_folders"] = [f.strip() for f in watch.split(",")]

    # Organize to
    default_org = config["organize_to"]
    org = input(f"Organize into [{default_org}]: ").strip()
    if org:
        config["organize_to"] = org

    # Model
    print(f"\nModels:")
    print(f"  1. Haiku  — fast, cheap (~$0.15/mo) [default]")
    print(f"  2. Sonnet — more accurate (~$1.50/mo)")
    model_choice = input("Model [1]: ").strip()
    if model_choice == "2":
        config["model"] = "claude-sonnet-4-6"
    elif not model_choice or model_choice == "1":
        config["model"] = "claude-haiku-4-5-20251001"

    # Context folders (optional)
    print(f"\nContext folders help TidyDesk understand your projects.")
    print(f"Point it at Obsidian vaults or project directories.")
    ctx = input("Context folders (comma-separated, Enter to skip): ").strip()
    if ctx:
        config["context_folders"] = [f.strip() for f in ctx.split(",")]

    save_config(config)
    print(f"\nSaved to {CONFIG_FILE}")
    return config


def get_config_or_exit() -> dict:
    """Load config, exit with helpful message if not set up."""
    config = load_config()
    if not config["api_key"]:
        print("TidyDesk is not configured. Run: tidydesk setup")
        sys.exit(1)
    return config
