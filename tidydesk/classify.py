"""File classification via Claude API.

Sends file metadata + extracted content to Claude and gets back
folder assignments. The prompt is the product's core IP, refined
through autoresearch eval iterations.
"""

import json
import logging
import unicodedata
from pathlib import Path

import anthropic

log = logging.getLogger("tidydesk")


def normalize_filename(name: str) -> str:
    """Normalize Unicode whitespace in macOS filenames."""
    for char in "\u202f\u00a0\u2007\u2009\u200a":
        name = name.replace(char, " ")
    return unicodedata.normalize("NFC", name)


def _build_prompt(
    file_descriptions: list[dict],
    existing_folders: list[str],
    projects: list[dict],
) -> str:
    """Build the classification prompt with dynamic context."""
    projects_json = json.dumps(projects, indent=2) if projects else "[]"
    folders_json = json.dumps(existing_folders)
    files_json = json.dumps(file_descriptions, indent=2)

    return f"""You are a file organizer. Classify each file into the best project folder.

## Known Project Context
{projects_json}

## Existing Folders
{folders_json}

## Files to Classify
{files_json}

## Classification Rules (in priority order)

### Rule 1: Project name in content takes priority
If extracted_content shows a project name in a browser tab, window title, terminal prompt path, or heading — that project wins, even if other projects are also mentioned.

### Rule 2: Classify by PURPOSE, not file type
Never create folders based on file type alone (no "screenshots", "pdfs", "videos"). A screenshot of a Stripe dashboard belongs in finances/, not screenshots/.

### Rule 3: Use extracted_content AND filename together
Content is the stronger signal when available. Filenames carry important clues especially when content is absent.

### Rule 4: Prefer existing folders
Don't create a new folder when an existing one fits. Match by project name, topic, or purpose.

### Rule 5: Create new folders in kebab-case
When a new folder is needed, use kebab-case (e.g. "tax-documents", "design-assets").

### Rule 6: Related files go together
Files about the same topic should share a folder even if they come from different source directories.

### Rule 7: Filename-based classification (when no extracted_content)
When a file has no extracted content, classify based on filename patterns:
- PDF/document names often contain project or topic keywords — use them
- Bare folder names from Downloads that look like social media usernames → "twitter" or "social-media"
- Audio/video files — infer from the filename what project they relate to
- Installer files (.dmg, .pkg) for known tools → match to the relevant project, or "inbox" if generic
- Files with UUID-style random names and no content → "inbox"

### Rule 8: Inbox is a LAST RESORT
Only use "inbox" when a file truly cannot be associated with any project or topic. Before defaulting to inbox, try harder:
- Check if the filename contains ANY keyword matching an existing folder
- Check if the file type suggests a category (e.g., .3mf → 3d-printing)
- Check if the source directory gives context

Do NOT put a file in inbox just because content extraction failed — use filename rules above.

Respond ONLY with a JSON array. Each element must include the index from the input:
{{"index": 0, "folder": "target-folder", "reason": "<=10 words"}}"""


def build_file_descriptions(
    files: list[Path],
    contents: dict[Path, str],
    organize_to: Path,
) -> list[dict]:
    """Build the file descriptions array for the prompt."""
    descriptions = []
    for idx, f in enumerate(files):
        desc = {
            "index": idx,
            "filename": normalize_filename(f.name),
            "source": f.parent.name,
            "type": "directory" if f.is_dir() else f.suffix.lower(),
        }
        if f.is_file():
            try:
                desc["size_kb"] = round(f.stat().st_size / 1024, 1)
            except Exception:
                pass
            content = contents.get(f, "")
            if content:
                desc["extracted_content"] = content
        elif f.is_dir():
            try:
                items = [
                    i.name for i in sorted(f.iterdir())[:20]
                    if not i.name.startswith(".")
                ]
                desc["directory_contents"] = items
            except Exception:
                pass
        descriptions.append(desc)
    return descriptions


def discover_projects(context_folders: list[str]) -> list[dict]:
    """Scan context folders for project awareness."""
    projects = []
    for folder_str in context_folders:
        folder = Path(folder_str).expanduser().resolve()
        if not folder.exists() or not folder.is_dir():
            continue
        folder_name = folder.name
        for item in sorted(folder.iterdir()):
            if item.is_dir() and not item.name.startswith(".") and item.name != "Templates":
                projects.append({"name": item.name, "source": folder_name})
        # Check for overview files
        for overview_name in ("Home.md", "README.md", "index.md"):
            overview = folder / overview_name
            if overview.exists():
                try:
                    content = overview.read_text(errors="ignore")[:800]
                    projects.append({
                        "name": f"{folder_name} (overview)",
                        "source": folder_name,
                        "description": content,
                    })
                except Exception:
                    pass
                break
    return projects


def classify_files(
    files: list[Path],
    contents: dict[Path, str],
    existing_folders: list[str],
    projects: list[dict],
    config: dict,
) -> list[dict]:
    """Send files to Claude for classification. Returns list of {index, folder, reason}."""
    client = anthropic.Anthropic(api_key=config["api_key"])
    organize_to = Path(config["organize_to"]).expanduser().resolve()

    file_descriptions = build_file_descriptions(files, contents, organize_to)
    prompt = _build_prompt(file_descriptions, existing_folders, projects)

    response = client.messages.create(
        model=config["model"],
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0].strip()

    return json.loads(text)
