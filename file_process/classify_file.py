from __future__ import annotations

"""CLI entry for upload-triggered ingest (no classifier).

Flow: NestJS emits `file.uploaded {fileName}` after MinIO put succeeds,
then spawns `python3 -m file_process.classify_file <fileName>`.
This module fetches via `GET /storage/:fileName`,
then runs `extract -> chunk -> PhoBERT embed -> persist vectors`
and prints a JSON summary. Vector persist/retrieve is fail-open
via `vector_store.py`.

Fail-open: unsupported types, storage errors, or vector-DB
errors all log a warning and exit 0 so uploads are never broken.
Usage errors (missing fileName) exit 2.
"""

import json
import logging
import sys
from collections.abc import Callable

logger = logging.getLogger("file_process.classify_file")


def ingest_file_name(
    file_name: str,
    base_url: str | None = None,
    encode_fn: Callable[[str], list[float]] | None = None,
    save_vectors: bool | None = None,
    db_url: str | None = None,
    retrieve: bool | None = None,
    top_k: int | None = None,
) -> dict:
    from . import settings
    from .pipeline import _resolve_encode_fn, ingest_document
    from .text_extractor import extract_file
    from .types import IngestedDocument

    doc = extract_file(file_name, base_url)
    resolved_encode = _resolve_encode_fn(encode_fn)
    result = IngestedDocument(chunks=ingest_document(doc, encode_fn=resolved_encode))
    db_info: dict = {"saved": False, "documentId": None}
    should_save = settings.vector_db_enabled() if save_vectors is None else save_vectors
    if should_save:
        try:
            from .vector_store import save_ingested_document

            saved = save_ingested_document(result, file_name, db_url=db_url)
            db_info = {"saved": True, "documentId": saved["documentId"]}
        except Exception as exc:
            logger.warning("vector db save skipped: file=%s error=%s", file_name, exc)
    vector_dbs: list[dict] = []
    should_retrieve = settings.vector_db_enabled() if retrieve is None else retrieve
    if should_retrieve:
        try:
            from .vector_store import retrieve_similar_documents

            vector_dbs = retrieve_similar_documents(
                result, file_name, top_k=top_k, db_url=db_url,
            )
        except Exception as exc:
            logger.warning("vector db retrieve skipped: file=%s error=%s", file_name, exc)
            vector_dbs = []
    return {
        "fileName": file_name,
        "chunkCount": len(result.chunks),
        "vectorDb": db_info,
        "vector_dbs": vector_dbs,
        "chunks": [
            {"chunk_index": c.chunk.chunk_index}
            for c in result.chunks
        ],
    }


# Alias giữ tương thích với caller cũ (NestJS spawn theo tên module).
classify_file_name = ingest_file_name


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or not args[0] or not args[0].strip():
        print(
            "usage: python -m file_process.classify_file <fileName> [--no-db] [--no-retrieve] [--db-url URL] [--top-k N]",
            file=sys.stderr,
        )
        return 2
    file_name = args[0].strip()
    save_vectors: bool | None = None
    db_url: str | None = None
    retrieve: bool | None = None
    top_k: int | None = None
    if "--no-db" in args[1:]:
        save_vectors = False
        retrieve = False
    if "--no-retrieve" in args[1:]:
        retrieve = False
    if "--db-url" in args:
        try:
            db_url = args[args.index("--db-url") + 1]
        except IndexError:
            print("missing value for --db-url", file=sys.stderr)
            return 2
    if "--top-k" in args:
        try:
            top_k = int(args[args.index("--top-k") + 1])
        except (IndexError, ValueError):
            print("invalid value for --top-k", file=sys.stderr)
            return 2

    try:
        summary = ingest_file_name(
            file_name, save_vectors=save_vectors, db_url=db_url,
            retrieve=retrieve, top_k=top_k,
        )
    except Exception as exc:  # fail-open: never break upload
        logger.warning("ingest skipped: file=%s error=%s", file_name, exc)
        print(
            json.dumps({"fileName": file_name, "chunkCount": 0})
        )
        return 0

    logger.info(
        "ingested document: file=%s chunks=%d",
        file_name,
        summary["chunkCount"],
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
