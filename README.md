# TidyDesk

AI-powered file organizer for macOS. Sorts by purpose, not file type.

## The Problem

Your Desktop and Downloads are dumping grounds. Existing tools sort by file type — screenshots here, PDFs there. But a screenshot of a Stripe dashboard belongs in `finances/`, not `screenshots/`. A PDF of a contract belongs in `client-project/`, not `documents/`.

**TidyDesk reads your files** (OCR on images, text from PDFs and code) and **sorts them by what they're actually about**.

## Install

```bash
pip install tidydesk
```

Requires macOS and Python 3.10+. Bring your own [Anthropic API key](https://console.anthropic.com/).

## Quick Start

```bash
# 1. Configure (API key, folders, model)
tidydesk setup

# 2. Organize your files
tidydesk run

# 3. Don't like the result? Undo it
tidydesk undo
```

## How It Works

1. **Scan** — Collects files from your Desktop and Downloads (skips recent files, in-progress downloads, and hidden files)
2. **Extract** — OCRs screenshots, reads PDF text, scans code/text files
3. **Classify** — Sends file metadata + content to Claude, which assigns each file to a project folder by purpose
4. **Move** — Creates folders and moves files. Every move is logged so you can undo.

## Commands

| Command | Description |
|---------|-------------|
| `tidydesk setup` | Configure API key, watch folders, and model |
| `tidydesk run` | Organize files now |
| `tidydesk run --dry-run` | Preview what would happen without moving anything |
| `tidydesk undo` | Reverse the last run |
| `tidydesk install` | Set up daily auto-run via launchd |
| `tidydesk uninstall` | Remove the daily schedule |
| `tidydesk status` | Show configuration and last run info |

## Configuration

Stored at `~/.tidydesk/config.json`:

| Field | Default | Description |
|-------|---------|-------------|
| `api_key` | — | Your Anthropic API key (required) |
| `watch_folders` | `~/Desktop, ~/Downloads` | Folders to scan for files |
| `organize_to` | `~/Desktop` | Where organized folders are created |
| `model` | `claude-haiku-4-5-20251001` | Claude model (Haiku or Sonnet) |
| `schedule_hour` | `9` | Hour for daily auto-run (0-23) |
| `schedule_minute` | `0` | Minute for daily auto-run (0-59) |
| `min_age_minutes` | `60` | Skip files newer than this |
| `batch_size` | `25` | Files per API call |
| `max_content_chars` | `2000` | Content extraction limit per file |
| `context_folders` | `[]` | Paths to scan for project context (e.g. Obsidian vaults) |

## Cost Estimate

TidyDesk uses your own API key. Estimated costs:

| Files/Day | Model | Daily Cost | Monthly Cost |
|-----------|-------|------------|-------------|
| 10 | Haiku | $0.002 | $0.06 |
| 25 | Haiku | $0.005 | $0.15 |
| 50 | Haiku | $0.010 | $0.30 |
| 25 | Sonnet | $0.05 | $1.50 |

## FAQ

**Is it safe?**
Every move is logged to `~/.tidydesk/manifest.jsonl`. Run `tidydesk undo` to reverse any run. Use `--dry-run` to preview first.

**Does it read my files?**
Yes — that's how it works. File content is sent to the Claude API for classification. No data is stored or logged beyond the move manifest. TidyDesk has no telemetry, no accounts, and no phone-home behavior.

**What model should I use?**
Haiku is the default — fast, cheap, and good enough for most files. Switch to Sonnet (`tidydesk setup` → option 2) for better accuracy on ambiguous files.

**Can I point it at project folders for context?**
Yes. Set `context_folders` in config to paths like your Obsidian vault or project directories. TidyDesk will scan folder names to improve classification.

**Does it work on Linux/Windows?**
No. macOS only — it uses the Vision framework for OCR and launchd for scheduling.

## License

MIT
