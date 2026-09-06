from __future__ import annotations

import os

# Grilled defaults: change via environment, no code edit needed.
DEFAULT_LARGE_DOC_CHARS = 2000
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 64
DEFAULT_MAX_TOKENS = 256
DEFAULT_RESERVED_TOKENS = 32
DEFAULT_BATCH_SIZE = 32


def _int_env(name: str, default: int, minimum: int = 0) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= minimum else default


def large_doc_chars() -> int:
    return _int_env("RAG_LARGE_DOC_CHARS", DEFAULT_LARGE_DOC_CHARS, minimum=1)


def chunk_size() -> int:
    return _int_env("RAG_CHUNK_SIZE", DEFAULT_CHUNK_SIZE, minimum=1)


def chunk_overlap() -> int:
    return _int_env("RAG_CHUNK_OVERLAP", DEFAULT_CHUNK_OVERLAP)


def max_tokens() -> int:
    return _int_env("RAG_MAX_TOKENS", DEFAULT_MAX_TOKENS, minimum=1)


def reserved_tokens() -> int:
    return _int_env("RAG_RESERVED_TOKENS", DEFAULT_RESERVED_TOKENS)


def batch_size() -> int:
    return _int_env("RAG_BATCH_SIZE", DEFAULT_BATCH_SIZE, minimum=1)
