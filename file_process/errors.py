from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorBody:
    message: str
    status_code: int
    error_code: str | None = None
    details: str | None = None


class StorageError(Exception):
    def __init__(self, body: ErrorBody) -> None:
        super().__init__(body.message)
        self.body = body


class FileNotFoundError(StorageError):
    def __init__(self, file_name: str) -> None:
        body = ErrorBody(
            message=f"File not found: {file_name}",
            status_code=404,
            error_code="FILE_NOT_FOUND",
        )
        super().__init__(body)
        self.file_name = file_name


class FileValidationError(StorageError):
    def __init__(self, message: str) -> None:
        body = ErrorBody(
            message=message,
            status_code=400,
            error_code="FILE_VALIDATION_FAILED",
        )
        super().__init__(body)


class StorageUnavailableError(StorageError):
    def __init__(self, message: str, details: str | None = None) -> None:
        body = ErrorBody(
            message=message,
            status_code=502,
            error_code="STORAGE_UNAVAILABLE",
            details=details,
        )
        super().__init__(body)


class UnsupportedFileError(StorageError):
    def __init__(self, file_name: str, reason: str) -> None:
        body = ErrorBody(
            message=f"Cannot extract text from {file_name}: {reason}",
            status_code=400,
            error_code="UNSUPPORTED_FILE",
        )
        super().__init__(body)
        self.file_name = file_name


class ModelUnavailableError(StorageError):
    def __init__(self, message: str, details: str | None = None) -> None:
        body = ErrorBody(
            message=message,
            status_code=502,
            error_code="MODEL_UNAVAILABLE",
            details=details,
        )
        super().__init__(body)
