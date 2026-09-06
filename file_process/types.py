from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Heading:
    level: int
    text: str


@dataclass(frozen=True)
class Section:
    heading: Heading | None
    text: str


@dataclass(frozen=True)
class FileMetadata:
    file_name: str
    content_type: str
    size: int
    extension: str
    page_count: int | None
    paragraph_count: int


@dataclass(frozen=True)
class ExtractedDocument:
    metadata: FileMetadata
    headings: list[Heading]
    sections: list[Section]


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    chunk_index: int
    heading: Heading | None
    metadata: FileMetadata
    text: str


@dataclass(frozen=True)
class ChunkWithEmbedding:
    chunk: Chunk
    embedding: list[float]
