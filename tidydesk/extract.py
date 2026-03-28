"""Content extraction — OCR, PDF text, and plain text files."""

import logging
import subprocess
from pathlib import Path

from tidydesk.config import OCR_BINARY, STATE_DIR

log = logging.getLogger("tidydesk")

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".tiff", ".bmp"}
PDF_SUFFIXES = {".pdf"}
TEXT_SUFFIXES = {
    ".txt", ".md", ".csv", ".json", ".xml", ".html", ".css", ".js", ".ts",
    ".py", ".swift", ".rb", ".sh", ".yaml", ".yml", ".toml", ".ini", ".log",
    ".jsx", ".tsx", ".vue", ".sql", ".graphql", ".conf", ".rtf",
}

MAX_FILE_SIZE_MB = 50


def _ocr_source() -> Path:
    """Find the bundled ocr.swift source."""
    return Path(__file__).parent / "ocr.swift"


def ensure_ocr_binary() -> bool:
    """Compile the Swift OCR helper if needed. Returns True if available."""
    if OCR_BINARY.exists():
        return True
    source = _ocr_source()
    if not source.exists():
        log.warning("OCR source not found at %s", source)
        return False
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Compiling OCR helper (first run only)...")
    result = subprocess.run(
        ["swiftc", "-O", "-o", str(OCR_BINARY), str(source),
         "-framework", "Vision", "-framework", "AppKit"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        log.error("OCR compile failed: %s", result.stderr)
        return False
    log.info("OCR helper ready")
    return True


def ocr_image(path: Path, max_chars: int = 2000) -> str:
    if not OCR_BINARY.exists():
        return ""
    try:
        result = subprocess.run(
            [str(OCR_BINARY), str(path)],
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout.strip()[:max_chars]
    except (subprocess.TimeoutExpired, Exception) as e:
        log.warning("OCR failed for %s: %s", path.name, e)
        return ""


def extract_pdf_text(path: Path, max_chars: int = 2000) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        text = ""
        for page in reader.pages[:5]:
            text += page.extract_text() or ""
            if len(text) > max_chars:
                break
        return text[:max_chars]
    except Exception as e:
        log.warning("PDF extraction failed for %s: %s", path.name, e)
        return ""


def extract_text_file(path: Path, max_chars: int = 2000) -> str:
    try:
        return path.read_text(errors="ignore")[:max_chars]
    except Exception as e:
        log.warning("Text read failed for %s: %s", path.name, e)
        return ""


def extract_content(path: Path, max_chars: int = 2000) -> str:
    """Extract text content from a file based on its type.

    Returns empty string for unsupported types or on failure.
    Silently skips files larger than MAX_FILE_SIZE_MB.
    """
    try:
        if path.stat().st_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            return ""
    except Exception:
        return ""

    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return ocr_image(path, max_chars)
    if suffix in PDF_SUFFIXES:
        return extract_pdf_text(path, max_chars)
    if suffix in TEXT_SUFFIXES:
        return extract_text_file(path, max_chars)
    return ""
