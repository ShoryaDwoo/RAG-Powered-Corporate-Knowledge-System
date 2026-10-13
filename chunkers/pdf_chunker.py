"""
PDF chunker — Parent-Child (Hierarchical) strategy.

Each PDF page is treated as a "parent" (full context for the LLM).
The page text is then split into small "child" chunks (128–256 tokens)
which are what gets embedded and searched against in Qdrant.

When a child chunk matches a query, the parent_text is promoted to the
LLM context window instead — giving full procedural context, not just
the matching sentence.

Both child text and parent_text are stored in the Qdrant payload so
no second lookup is required at query time.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import cfg
from utils import logger
from utils import Chunk, ChunkMetadata


def _extract_page_text(page: "pdfplumber.page.Page") -> str:
    """Extract text from a pdfplumber page, falling back gracefully."""
    text = page.extract_text()
    if text:
        return text.strip()
    # Try extracting words as a fallback for scanned/layout-heavy PDFs
    words = page.extract_words()
    if words:
        return " ".join(w["text"] for w in words)
    return ""


def chunk_pdf(raw: bytes, source: str, access_role: str, etag: str = "") -> list[Chunk]:
    """
    Parse a PDF into parent-child chunk pairs.

    Args:
        raw:         Raw bytes of the .pdf file.
        source:      S3 key used as the source identifier.
        access_role: RBAC role tag.
        etag:        S3 ETag used as the doc_version.

    Returns:
        List of Chunk objects. Each has:
          - chunk.text         → child text (embedded for search)
          - chunk.parent_text  → full page text (passed to LLM on hit)
    """
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=cfg.pdf_child_chunk_size,
        chunk_overlap=cfg.pdf_child_chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[Chunk] = []
    now = datetime.now(timezone.utc).isoformat()

    try:
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                parent_text = _extract_page_text(page)
                if not parent_text:
                    logger.warning(f"{source} page {page_num}: no text extracted, skipping")
                    continue

                children = child_splitter.split_text(parent_text)

                for child_index, child_text in enumerate(children):
                    if not child_text.strip():
                        continue
                    metadata = ChunkMetadata(
                        source=source,
                        doc_type="pdf",
                        access_role=access_role,
                        page=page_num,
                        child_index=child_index,
                        ingestion_timestamp=now,
                        doc_version=etag,
                    )
                    chunks.append(Chunk(
                        text=child_text.strip(),
                        parent_text=parent_text,    # ← stored in Qdrant payload
                        metadata=metadata,
                    ))

    except Exception as exc:
        logger.error(f"Failed to parse PDF {source}: {exc}")
        raise

    logger.info(f"{source}: {len(chunks)} PDF child chunks from {page_num + 1} pages")
    return chunks
