"""
Chunker for plain .txt files.
"""
from __future__ import annotations

from datetime import datetime, timezone

from utils import Chunk, ChunkMetadata, logger


def chunk_txt(
    raw: bytes,
    key: str,
    access_role: str,
    etag: str = "",
    chunk_size: int = 200,
    overlap: int = 30,
    encoding: str = "utf-8",
) -> list[Chunk]:
    """
    Decode and chunk a plain text file.

    Args:
        raw:         Raw text bytes.
        key:         S3 object key (used as source label).
        access_role: RBAC tag for filtering.
        etag:        S3 ETag for cache invalidation.
        chunk_size:  Target word count per chunk.
        overlap:     Word overlap between consecutive chunks.
        encoding:    Text encoding (default utf-8, fallback latin-1).

    Returns:
        List of Chunk objects.
    """
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError:
        logger.warning(f"chunk_txt: UTF-8 decode failed for {key}, falling back to latin-1")
        text = raw.decode("latin-1")

    words = text.split()
    chunks: list[Chunk] = []
    now = datetime.now(timezone.utc).isoformat()

    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_text = " ".join(words[start:end])
        chunks.append(
            Chunk(
                text=chunk_text,
                metadata=ChunkMetadata(
                    source=key,
                    doc_type="md",          # closest plain-text type available
                    access_role=access_role,
                    ingestion_timestamp=now,
                    doc_version=etag,
                ),
            )
        )
        start += chunk_size - overlap

    logger.info(f"chunk_txt: {key} → {len(chunks)} chunks")
    return chunks