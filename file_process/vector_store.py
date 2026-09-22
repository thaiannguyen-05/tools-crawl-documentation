from __future__ import annotations

"""Persist ingested chunk vectors to Postgres/pgvector + KNN query helper.

Tables (xem schema.prisma + migration 20260918_add_doc_vectors):
- documents(fileName unique, chunkCount)
- document_chunks(documentId FK cascade, chunkIndex, text, heading*,
  embedding vector(1024))

Pipeline chạy thẳng extract -> chunk -> embed -> save, không qua lớp
phân loại. Các cột docType/confidence/predictedLabel/labelProbs (nếu còn
trong schema từ bản cũ) được giữ nguyên, không ghi đè.

Quy ước giống compute_centroids.py: vector lưu dạng literal "[...]",
index HNSW + toán tử `<=>` (cosine). Fail-open ở caller: hàm này ném
Exception để caller log warning và không chặn pipeline.
"""

import logging
import uuid

from . import settings
from .types import IngestedDocument

logger = logging.getLogger(__name__)

UPSERT_DOCUMENT_SQL = """
INSERT INTO documents ("id", "fileName", "chunkCount", "updatedAt")
VALUES (%s::uuid, %s, %s, NOW())
ON CONFLICT ("fileName") DO UPDATE SET
  "chunkCount" = EXCLUDED."chunkCount",
  "updatedAt" = NOW()
RETURNING "id";
"""

DELETE_CHUNKS_SQL = 'DELETE FROM document_chunks WHERE "documentId" = %s::uuid;'

INSERT_CHUNK_SQL = """
INSERT INTO document_chunks
  ("id", "documentId", "chunkIndex", "text", "heading", "headingLevel",
   "embedding", "predictedLabel", "labelProbs")
VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s, %s::vector, NULL, NULL);
"""

KNN_SQL = """
SELECT c."chunkIndex", c."text", c."predictedLabel",
       d."fileName", d."docType",
       c."embedding" <=> %s::vector AS distance
FROM document_chunks c
JOIN documents d ON d."id" = c."documentId"
ORDER BY c."embedding" <=> %s::vector
LIMIT %s;
"""


def _vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{float(v):.6f}" for v in vec) + "]"


def save_ingested_document(
    ingested: IngestedDocument,
    file_name: str,
    db_url: str | None = None,
) -> dict:
    """Upsert 1 document + toàn bộ chunk vectors. Trả về {documentId, chunks}."""
    import psycopg2

    if not file_name or not file_name.strip():
        raise ValueError("file_name is required")
    url = db_url or settings.vector_db_url()
    document_id = str(uuid.uuid4())
    chunks = ingested.chunks

    conn = psycopg2.connect(url)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    UPSERT_DOCUMENT_SQL,
                    (
                        document_id,
                        file_name,
                        len(chunks),
                    ),
                )
                row = cur.fetchone()
                if row and row[0]:
                    document_id = str(row[0])
                cur.execute(DELETE_CHUNKS_SQL, (document_id,))
                for c in chunks:
                    heading_text = c.chunk.heading.text if c.chunk.heading else None
                    heading_level = c.chunk.heading.level if c.chunk.heading else None
                    cur.execute(
                        INSERT_CHUNK_SQL,
                        (
                            str(uuid.uuid4()),
                            document_id,
                            c.chunk.chunk_index,
                            c.chunk.text,
                            heading_text,
                            heading_level,
                            _vector_literal(c.embedding),
                        ),
                    )
    finally:
        conn.close()

    logger.info(
        "saved vectors: file=%s chunks=%d documentId=%s",
        file_name, len(chunks), document_id,
    )
    return {"documentId": document_id, "chunks": len(chunks)}


def query_similar(
    embedding: list[float],
    top_k: int = 5,
    db_url: str | None = None,
) -> list[dict]:
    """KNN cosine trên toàn bộ chunks. Dùng cho nhánh phải diagram."""
    import psycopg2
    import psycopg2.extras

    url = db_url or settings.vector_db_url()
    lit = _vector_literal(embedding)
    conn = psycopg2.connect(url)
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(KNN_SQL, (lit, lit, top_k))
                return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def retrieve_similar_documents(
    ingested: IngestedDocument,
    file_name: str,
    top_k: int | None = None,
    per_chunk_k: int | None = None,
    db_url: str | None = None,
) -> list[dict]:
    """Nhánh phải pipeline: KNN chunk embeddings vs toàn bộ DB.

    - doc_vectors: chunk embeddings của file vừa ingest (in-memory).
    - candidates: `query_similar` từng chunk (không lọc label).
    - loại chính file vừa ingest (`fileName`), dedup theo
      (fileName, chunkIndex) giữ distance nhỏ nhất, sort asc, cắt top-K.
    Trả về vector_dbs[] top-K gần nhất.
    """
    if not ingested.chunks:
        return []
    limit = top_k or settings.retrieval_top_k()
    per = per_chunk_k or limit
    merged: dict[tuple, dict] = {}
    for c in ingested.chunks:
        for hit in query_similar(
            c.embedding, top_k=per, db_url=db_url,
        ):
            if hit.get("fileName") == file_name:
                continue
            key = (hit.get("fileName"), hit.get("chunkIndex"))
            if key not in merged or float(hit["distance"]) < float(merged[key]["distance"]):
                merged[key] = hit
    ranked = sorted(merged.values(), key=lambda h: float(h["distance"]))
    return ranked[:limit]
