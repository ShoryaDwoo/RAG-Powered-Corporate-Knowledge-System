"""
Main ingestion pipeline.

Orchestrates the full flow:
  S3 (fetch) → Format Router (chunk) → Gemini (embed) → Qdrant (upsert)

Supports:
  - Full ingest: scan all prefixes in S3
  - Partial ingest: specific prefix or single key
  - Re-ingest: deletes stale vectors before re-processing
"""
from __future__ import annotations

from qdrant_client import QdrantClient

from chunkers import route_and_chunk
from ingestion.s3_loader import stream_documents, fetch_single
from ingestion.embedder import embed_texts
from ingestion.qdrant_store import ensure_collection, upsert_chunks, delete_by_source
from utils import logger

# Keys to skip during ingestion — meta/index files that pollute retrieval
EXCLUDED_KEYS: set[str] = {
    "00_README_Document_Index.md",
}


def _should_ingest(key: str) -> bool:
    """Return False for keys that should never be indexed."""
    filename = key.split("/")[-1]
    if filename in EXCLUDED_KEYS:
        logger.info(f"Skipping excluded file: {key}")
        return False
    return True


def run_full_ingest(prefix: str = "", reingest: bool = False) -> dict:
    """
    Run the full ingestion pipeline for all documents under `prefix`.

    Args:
        prefix:   S3 key prefix to scan. Empty string = entire bucket.
        reingest: If True, delete existing vectors for each document before
                  re-processing. Set True when re-running after document updates.

    Returns:
        Summary dict: {"processed": int, "chunks": int, "errors": list[str]}
    """
    client: QdrantClient = ensure_collection()
    stats = {"processed": 0, "chunks": 0, "errors": []}

    for key, raw, access_role, etag in stream_documents(prefix=prefix):
        if not _should_ingest(key):
            continue

        try:
            if reingest:
                delete_by_source(key, client=client)

            chunks = route_and_chunk(key, raw, access_role, etag)
            if not chunks:
                logger.warning(f"{key}: produced 0 chunks — skipping")
                continue

            texts = [c.text for c in chunks]
            vectors = embed_texts(texts)
            upserted = upsert_chunks(chunks, vectors, client=client)

            stats["processed"] += 1
            stats["chunks"] += upserted

        except Exception as exc:
            logger.error(f"Error processing {key}: {exc}")
            stats["errors"].append(f"{key}: {exc}")
            continue

    logger.info(
        f"Ingest complete — {stats['processed']} documents, "
        f"{stats['chunks']} chunks, {len(stats['errors'])} errors"
    )
    return stats


def ingest_single_document(key: str, reingest: bool = True) -> dict:
    """
    Ingest (or re-ingest) a single document by its S3 key.

    Args:
        key:      S3 object key, e.g. "hr/leave_policy_2026.pdf".
        reingest: Whether to delete existing vectors first (default True).

    Returns:
        Summary dict: {"key": str, "chunks": int, "error": str | None}
    """
    if not _should_ingest(key):
        return {"key": key, "chunks": 0, "error": "File is excluded from ingestion"}

    client: QdrantClient = ensure_collection()

    try:
        raw, access_role, etag = fetch_single(key)

        if reingest:
            delete_by_source(key, client=client)

        chunks = route_and_chunk(key, raw, access_role, etag)
        texts = [c.text for c in chunks]
        vectors = embed_texts(texts)
        upserted = upsert_chunks(chunks, vectors, client=client)

        logger.info(f"Single ingest done: {key} → {upserted} chunks")
        return {"key": key, "chunks": upserted, "error": None}

    except Exception as exc:
        logger.error(f"Single ingest failed for {key}: {exc}")
        return {"key": key, "chunks": 0, "error": str(exc)}