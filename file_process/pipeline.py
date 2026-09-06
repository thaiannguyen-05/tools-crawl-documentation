from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from . import settings
from .chunker import chunk_document
from .errors import FileValidationError
from .tokenizer import (
    META_SEP,
    build_phobert_input,
    estimate_tokens,
    segment_vietnamese,
)
from .types import Chunk, ChunkWithEmbedding, ExtractedDocument, FileMetadata

def aggregate_mean(chunks: list[list[float]]) -> list[float]:
    n = len(chunks)
    dim = len(chunks[0])
    return [sum(chunks[i][d] for i in range(n)) / n for d in range(dim)]


def aggregate_max(chunks: list[list[float]]) -> list[float]:
    dim = len(chunks[0])
    return [max(chunks[i][d] for i in range(len(chunks))) for d in range(dim)]


def aggregate_weighted(
    chunks: list[list[float]], weights: list[float]
) -> list[float]:
    total = sum(weights)
    if total == 0:
        raise ValueError("weights sum to zero")
    dim = len(chunks[0])
    return [
        sum(chunks[i][d] * weights[i] for i in range(len(chunks))) / total
        for d in range(dim)
    ]


def aggregate_chunk_vectors(
    embeddings: list[list[float]],
    method: str = "mean",
    weights: list[float] | None = None,
) -> list[float]:
    if not embeddings:
        raise ValueError("no embeddings to aggregate")
    if method == "mean":
        return aggregate_mean(embeddings)
    if method == "max":
        return aggregate_max(embeddings)
    if method == "weighted":
        if weights is None:
            raise ValueError("weights required for weighted aggregation")
        return aggregate_weighted(embeddings, weights)
    raise ValueError(f"unknown aggregation method: {method}")


def aggregate_embeddings(
    embeddings: list[list[float]], method: str = "mean"
) -> list[float]:
    return aggregate_chunk_vectors(embeddings, method)

logger = logging.getLogger(__name__)

MIN_MAX_TOKENS = 8


def describe_metadata(meta: FileMetadata) -> str:
    parts = [meta.file_name, meta.extension]
    if meta.page_count is not None:
        parts.append(f"{meta.page_count} pages")
    return META_SEP.join(p for p in parts if p)


def chunk_to_input(
    chunk: Chunk,
    token_len_fn: Callable[[str], int] | None = None,
    max_tokens: int | None = None,
) -> str:
    headings = [chunk.heading.text] if chunk.heading and chunk.heading.text else []
    return build_phobert_input(
        metadata_str=describe_metadata(chunk.metadata),
        headings=headings,
        content=chunk.text,
        token_len_fn=token_len_fn,
        max_tokens=max_tokens,
    )


def ingest_document(
    doc: ExtractedDocument,
    encode_fn: Callable[[str], list[float]],
    token_len_fn: Callable[[str], int] | None = None,
    max_tokens: int | None = None,
) -> list[ChunkWithEmbedding]:
    budget = settings.max_tokens() if max_tokens is None else max_tokens
    if budget < MIN_MAX_TOKENS:
        raise FileValidationError(f"max_tokens must be >= {MIN_MAX_TOKENS}")
    counter = token_len_fn or estimate_tokens
    out: list[ChunkWithEmbedding] = []

    chunks = chunk_document(doc)
    logger.info(
        "ingesting document: file=%s chunks=%d", doc.metadata.file_name, len(chunks)
    )

    for chunk in chunks:
        segmented = segment_vietnamese(chunk_to_input(chunk, token_len_fn, budget))
        if counter(segmented) <= budget:
            out.append(ChunkWithEmbedding(chunk=chunk, embedding=encode_fn(segmented)))
            continue
        # Safety net: content alone overflowed the budget estimate.
        # Encode two halves and average (sliding window, mean of 2 passes).
        logger.warning(
            "chunk over token budget, sliding window: file=%s chunk_index=%d",
            chunk.doc_id,
            chunk.chunk_index,
        )
        halves = _split_half(chunk.text)
        embs = [
            encode_fn(segment_vietnamese(chunk_to_input(_with_text(chunk, h), token_len_fn, budget)))
            for h in halves
        ]
        out.append(ChunkWithEmbedding(chunk=chunk, embedding=_mean_embeddings(embs)))

    return out


def _with_text(chunk: Chunk, text: str) -> Chunk:
    return Chunk(
        doc_id=chunk.doc_id,
        chunk_index=chunk.chunk_index,
        heading=chunk.heading,
        metadata=chunk.metadata,
        text=text,
    )


def _split_half(text: str, overlap: int | None = None) -> list[str]:
    window = settings.chunk_overlap() if overlap is None else overlap
    mid = len(text) // 2
    # Prefer a nearby space so words are not cut.
    cut = text.rfind(" ", 0, mid + window)
    if cut <= 0:
        cut = mid
    return [text[:cut].strip(), text[cut:].strip()]


def _mean_embeddings(embs: list[list[float]]) -> list[float]:
    dim = len(embs[0])
    return [sum(e[i] for e in embs) / len(embs) for i in range(dim)]


def _resolve_encode_fn(
    encode_fn: Callable[[str], list[float]] | None,
) -> Callable[[str], list[float]]:
    if encode_fn is not None:
        return encode_fn
    from model.phoBert.phobert import encode

    return encode


def ingest_bytes(
    file_name: str,
    content: bytes,
    encode_fn: Callable[[str], list[float]] | None = None,
    token_len_fn: Callable[[str], int] | None = None,
    max_tokens: int | None = None,
) -> list[ChunkWithEmbedding]:
    """End-to-end: raw file bytes -> extract -> chunk -> per-chunk vectors."""
    if not file_name or not file_name.strip():
        raise FileValidationError("file_name is required")
    if not content:
        raise FileValidationError(f"empty content: {file_name}")
    from .text_extractor import extract_text

    return ingest_document(
        extract_text(file_name, content),
        _resolve_encode_fn(encode_fn),
        token_len_fn,
        max_tokens,
    )


def ingest_file(
    file_name: str,
    base_url: str | None = None,
    encode_fn: Callable[[str], list[float]] | None = None,
    token_len_fn: Callable[[str], int] | None = None,
    max_tokens: int | None = None,
) -> list[ChunkWithEmbedding]:
    """End-to-end: stored file -> fetch -> extract -> chunk -> per-chunk vectors."""
    if not file_name or not file_name.strip():
        raise FileValidationError("file_name is required")
    from .text_extractor import extract_file

    return ingest_document(
        extract_file(file_name, base_url),
        _resolve_encode_fn(encode_fn),
        token_len_fn,
        max_tokens,
    )
