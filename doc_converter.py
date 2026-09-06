from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text_from_doc(doc_bytes: bytes) -> str:
    """Extract legible text from legacy Word 97-2003 (.doc) binary format.
    
    Uses heuristics to extract UTF-16LE and ASCII / UTF-8 text runs from OLE streams
    without requiring LibreOffice or Windows COM dependencies.
    """
    extracted_chunks: list[str] = []

    # Heuristic 1: Extract UTF-16LE strings (common in Office 97-2003)
    try:
        # Match sequences of printable characters in UTF-16LE (2-byte runs)
        utf16_runs = re.findall(rb"(?:[\x20-\x7e\xa0-\xff][\x00-\x04]){4,}", doc_bytes)
        for run in utf16_runs:
            try:
                decoded = run.decode("utf-16le", errors="ignore").strip()
                if len(decoded) > 10 and not _is_binary_garbage(decoded):
                    extracted_chunks.append(decoded)
            except Exception:
                pass
    except Exception as e:
        logger.debug("UTF-16LE extraction failed: %s", e)

    # Heuristic 2: Extract ASCII / UTF-8 text runs
    try:
        ascii_runs = re.findall(rb"[\x20-\x7e\xc2-\xf4][\x80-\xbf\x20-\x7e]{8,}", doc_bytes)
        for run in ascii_runs:
            try:
                decoded = run.decode("utf-8", errors="ignore").strip()
                if len(decoded) > 15 and not _is_binary_garbage(decoded):
                    extracted_chunks.append(decoded)
            except Exception:
                pass
    except Exception as e:
        logger.debug("UTF-8 extraction failed: %s", e)

    text = "\n\n".join(extracted_chunks).strip()
    return text


def _is_binary_garbage(text: str) -> bool:
    """Check if the text segment looks like binary garbage or font tables."""
    if not text:
        return True
    # Ignore font names, XML schema URLs, internal OLE strings
    ignored_keywords = [
        "Normal.dot",
        "Microsoft Word",
        "Times New Roman",
        "Calibri",
        "schemas.microsoft.com",
        "xmlns:",
        "WordDocument",
        "CompObj",
        "SummaryInformation",
    ]
    if any(kw in text for kw in ignored_keywords):
        return True

    # Count whitespace ratio
    whitespace_count = sum(1 for c in text if c.isspace())
    if len(text) > 30 and whitespace_count == 0:
        return True

    return False


def convert_doc_if_needed(file_path: Path) -> Path | None:
    """If file is .doc, extract text and write a companion .txt file.
    
    Returns the path to the converted .txt file, or None if failed.
    """
    if file_path.suffix.lower() != ".doc":
        return None

    try:
        content = file_path.read_bytes()
        text = extract_text_from_doc(content)
        if text and len(text.strip()) > 50:
            converted_path = file_path.with_suffix(".extracted.txt")
            converted_path.write_text(text, encoding="utf-8")
            logger.info("Successfully extracted text from legacy .doc -> %s", converted_path.name)
            return converted_path
    except Exception as e:
        logger.warning("Failed to convert legacy doc %s: %s", file_path.name, e)

    return None
