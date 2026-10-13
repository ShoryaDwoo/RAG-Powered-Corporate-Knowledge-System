"""
Chunker for .doc / .docx files using python-docx.
Install: pip install python-docx
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from docx import Document

from utils import Chunk, ChunkMetadata, logger


def chunk_docx(
    raw: bytes,
    key: str,
    access_role: str,
    etag: str = "",
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[Chunk]:
    """
    Extract and chunk text from a .docx file.

    Args:
        raw:         Raw .docx bytes.
        key:         S3 object key (used as source label).
        access_role: RBAC tag for filtering.
        etag:        S3 ETag for cache invalidation.
        chunk_size:  Target word count per chunk.
        overlap:     Word overlap between consecutive chunks.

    Returns:
        List of Chunk objects.
    """
    doc = Document(io.BytesIO(raw))

    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    full_text = "\n\n".join(paragraphs)

    words = full_text.split()
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

    logger.info(f"chunk_docx: {key} → {len(chunks)} chunks")
    return chunks