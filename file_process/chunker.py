from __future__ import annotations

import re

from . import settings
from .types import Chunk, ExtractedDocument

_SENT_SPLIT = re.compile(r"(?<=[.!?\u2026\n])\s+|(?<=\n)\s*")


def chunk_document(doc: ExtractedDocument) -> list[Chunk]:
    sections = [s for s in doc.sections if s.text and s.text.strip()]
    if not sections:
        return []

    total = sum(len(s.text) for s in sections)
    chunks: list[Chunk] = []
    index = 0

    for section in sections:
        text = section.text.strip()
        if total <= settings.large_doc_chars():
            chunks.append(
                Chunk(
                    doc_id=doc.metadata.file_name,
                    chunk_index=index,
                    heading=section.heading,
                    metadata=doc.metadata,
                    text=text,
                )
            )
            index += 1
        else:
            for piece in _split_long_text(text):
                chunks.append(
                    Chunk(
                        doc_id=doc.metadata.file_name,
                        chunk_index=index,
                        heading=section.heading,
                        metadata=doc.metadata,
                        text=piece,
                    )
                )
                index += 1

    return chunks


def _split_long_text(
    text: str, size: int | None = None, overlap: int | None = None
) -> list[str]:
    size = settings.chunk_size() if size is None else size
    overlap = settings.chunk_overlap() if overlap is None else overlap
    overlap = min(max(overlap, 0), size // 2)

    sentences = [s.strip() for s in _SENT_SPLIT.split(text.strip()) if s.strip()]
    if not sentences:
        return []

    # Single massive sentence (or no sentence boundaries): hard char windows.
    if len(sentences) == 1 and len(sentences[0]) > size:
        return _hard_split(sentences[0], size, overlap)

    out: list[str] = []
    current = ""

    for sent in sentences:
        if len(sent) > size:
            if current.strip():
                out.append(current.strip())
                current = ""
            out.extend(_hard_split(sent, size, overlap))
            continue

        candidate = f"{current} {sent}".strip() if current else sent
        if len(candidate) <= size:
            current = candidate
        else:
            if current.strip():
                out.append(current.strip())
                tail = current[-overlap:] if overlap and len(current) > overlap else ""
                current = f"{tail} {sent}".strip() if tail else sent
                # Tail + sentence may still overflow when overlap is large;
                # hard-split as a safety net to keep the size bound.
                if len(current) > size + 128:
                    hard = _hard_split(current, size, overlap)
                    out.extend(hard[:-1])
                    current = hard[-1]
            else:
                current = sent

    if current.strip():
        out.append(current.strip())
    return out


def _hard_split(text: str, size: int, overlap: int) -> list[str]:
    step = max(size - overlap, 1)
    return [text[i : i + size].strip() for i in range(0, len(text), step) if text[i : i + size].strip()]
