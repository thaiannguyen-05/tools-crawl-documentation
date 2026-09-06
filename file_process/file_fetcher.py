from __future__ import annotations

import os
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv

from .errors import ErrorBody, StorageError, StorageUnavailableError

_ENV = Path(__file__).resolve().parent.parent / ".env"
if not _ENV.exists():
    _ENV = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_ENV)

DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class FileContent:
    content: bytes
    content_type: str
    size: int


def fetch_file(file_name: str, base_url: str | None = None) -> FileContent:
    base = (
        base_url or os.environ.get("RAG_API_BASE_URL", "http://localhost:3000")
    ).rstrip("/")

    presigned_url = _get_presigned_url(base, file_name)

    try:
        response = httpx.get(presigned_url, timeout=DEFAULT_TIMEOUT_SECONDS)
    except httpx.HTTPError as error:
        raise StorageUnavailableError(
            "Download from presigned URL failed", str(error)
        ) from error

    if response.status_code != 200:
        raise StorageUnavailableError(
            f"Download failed: HTTP {response.status_code}"
        )

    content_type = response.headers.get("content-type", "application/octet-stream")
    content = response.content
    has_length = "content-length" in response.headers
    size = int(response.headers["content-length"]) if has_length else len(content)

    return FileContent(content=content, content_type=content_type, size=size)


def _get_presigned_url(base: str, file_name: str) -> str:
    url = f"{base}/storage/{urllib.parse.quote(file_name, safe='')}"
    try:
        response = httpx.get(url, timeout=DEFAULT_TIMEOUT_SECONDS)
    except httpx.HTTPError as error:
        raise StorageUnavailableError(
            f"Request to {url} failed", str(error)
        ) from error

    if response.status_code != 200:
        raise _parse_error_response(response)

    return response.text


def _parse_error_response(response: httpx.Response) -> StorageError:
    try:
        body = response.json()
    except ValueError:
        return StorageUnavailableError(
            f"HTTP {response.status_code}: {response.text}"
        )

    error_body = ErrorBody(
        message=body.get("message", f"HTTP {response.status_code}"),
        status_code=response.status_code,
        error_code=body.get("errorCode"),
        details=body.get("details"),
    )

    from .errors import FileNotFoundError, FileValidationError

    if error_body.error_code == "FILE_NOT_FOUND":
        return FileNotFoundError(
            error_body.message.removeprefix("File not found: ")
        )

    if error_body.error_code == "FILE_VALIDATION_FAILED":
        return FileValidationError(error_body.message)

    return StorageError(error_body)
