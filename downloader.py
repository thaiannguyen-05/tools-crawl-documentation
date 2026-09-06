from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any
import httpx

try:
    from .config import DEFAULT_USER_AGENT, DEFAULT_TIMEOUT_SECONDS, MAX_DOWNLOAD_SIZE_BYTES
    from .doc_converter import convert_doc_if_needed
except (ImportError, ValueError):
    from config import DEFAULT_USER_AGENT, DEFAULT_TIMEOUT_SECONDS, MAX_DOWNLOAD_SIZE_BYTES
    from doc_converter import convert_doc_if_needed

logger = logging.getLogger(__name__)

MAGIC_HEADERS = {
    "pdf": b"%PDF-",
    "docx": b"PK\x03\x04",
    "doc": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
}


def sanitize_filename(name: str, max_length: int = 120) -> str:
    """Make filename safe for filesystem across OS platforms."""
    clean = re.sub(r'[\\/*?:"<>|]', "_", name)
    clean = re.sub(r"\s+", "_", clean).strip("._")
    if not clean:
        clean = "document"
    return clean[:max_length]


def verify_file_signature(data_prefix: bytes, expected_format: str) -> bool:
    """Check magic bytes for binary document types."""
    fmt = expected_format.lower()
    if fmt in MAGIC_HEADERS:
        magic = MAGIC_HEADERS[fmt]
        return data_prefix.startswith(magic)
    # For txt and md, any printable or utf-8 text is valid
    return True


def download_document(
    url: str,
    output_dir: Path,
    file_format: str,
    title: str = "",
    direct_content: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any] | None:
    """Download or save document and return file information."""
    output_dir.mkdir(parents=True, exist_ok=True)
    fmt = file_format.lower().lstrip(".")

    # Handle direct text content (e.g. from Wikipedia)
    if direct_content is not None:
        safe_title = sanitize_filename(title or "wiki_document")
        file_path = output_dir / f"{safe_title}.{fmt}"
        file_path.write_text(direct_content, encoding="utf-8")
        data_bytes = file_path.read_bytes()
        sha256 = hashlib.sha256(data_bytes).hexdigest()
        return {
            "file_name": file_path.name,
            "file_path": str(file_path),
            "url": url,
            "title": title,
            "format": fmt,
            "size": len(data_bytes),
            "sha256": sha256,
            "status": "downloaded",
            "converted_file": None,
        }

    # Otherwise stream download from URL
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "*/*",
    }

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, verify=False) as client:
            with client.stream("GET", url, headers=headers) as response:
                if response.status_code != 200:
                    logger.warning("Download failed (%d): %s", response.status_code, url)
                    return None

                content_len = response.headers.get("content-length")
                if content_len and int(content_len) > MAX_DOWNLOAD_SIZE_BYTES:
                    logger.warning("File too large (%s bytes): %s", content_len, url)
                    return None

                # Use a single stream iterator to avoid StreamConsumed error
                stream_iter = response.iter_bytes(chunk_size=32768)
                first_chunk = next(stream_iter, b"")
                if not first_chunk:
                    logger.warning("Empty response: %s", url)
                    return None

                # Verify file signature for binary formats
                if fmt in ("pdf", "docx", "doc") and not verify_file_signature(first_chunk, fmt):
                    # In some cases a .docx URL might point to a .doc or vice versa
                    if fmt == "docx" and verify_file_signature(first_chunk, "doc"):
                        fmt = "doc"
                    elif fmt == "doc" and verify_file_signature(first_chunk, "docx"):
                        fmt = "docx"
                    else:
                        logger.warning("Signature mismatch for %s (expected %s): %s", url, fmt, first_chunk[:8])
                        return None

                # Stream remaining content using the same iterator
                chunks = [first_chunk]
                total_size = len(first_chunk)
                for chunk in stream_iter:
                    total_size += len(chunk)
                    if total_size > MAX_DOWNLOAD_SIZE_BYTES:
                        logger.warning("Exceeded size limit during stream: %s", url)
                        return None
                    chunks.append(chunk)

                full_data = b"".join(chunks)

        # Derive filename from title or URL
        if title:
            base_name = sanitize_filename(title)
        else:
            url_name = Path(urllib.parse.urlparse(url).path).stem
            base_name = sanitize_filename(url_name) or "crawled_doc"

        file_name = f"{base_name}.{fmt}"
        file_path = output_dir / file_name

        # Avoid overwriting existing files with same name
        counter = 1
        while file_path.exists():
            file_name = f"{base_name}_{counter}.{fmt}"
            file_path = output_dir / file_name
            counter += 1

        file_path.write_bytes(full_data)
        sha256 = hashlib.sha256(full_data).hexdigest()

        converted_file = None
        if fmt == "doc":
            converted_path = convert_doc_if_needed(file_path)
            if converted_path:
                converted_file = str(converted_path)

        logger.info("Saved %s (%d bytes) from %s", file_path.name, len(full_data), url)
        return {
            "file_name": file_path.name,
            "file_path": str(file_path),
            "url": url,
            "title": title or file_name,
            "format": fmt,
            "size": len(full_data),
            "sha256": sha256,
            "status": "downloaded",
            "converted_file": converted_file,
        }

    except Exception as e:
        logger.error("Error downloading %s: %s", url, e)
        return None
