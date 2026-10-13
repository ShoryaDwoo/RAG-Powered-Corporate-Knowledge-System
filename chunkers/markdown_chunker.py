"""
Markdown chunker — Document-Aware + Recursive strategy.

Step 1: MarkdownHeaderTextSplitter splits on native headers (#, ##, ###),
        preserving the section hierarchy in metadata.
Step 2: RecursiveCharacterTextSplitter ensures no section exceeds
        cfg.md_chunk_size tokens, with cfg.md_chunk_overlap overlap.

Result: Induction steps, navigation paths, and policy lists remain intact
        under their respective headers rather than being split mid-procedure.
"""
from __future__ import annotations

from datetime import datetime, timezone

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from config import cfg
from utils import logger
from utils import Chunk, ChunkMetadata

HEADERS_TO_SPLIT = [
    ("#",   "h1"),
    ("##",  "h2"),
    ("###", "h3"),
    ("####","h4"),
]


def chunk_markdown(raw: bytes, source: str, access_role: str, etag: str = "") -> list[Chunk]:
    """
    Parse a Markdown document into semantically coherent chunks.

    Args:
        raw:         Raw bytes of the .md file.
        source:      S3 key used as the source identifier.
        access_role: RBAC role tag (e.g. "General-Staff").
        etag:        S3 ETag used as the doc_version.

    Returns:
        List of Chunk objects ready for embedding.
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
        logger.warning(f"{source}: fell back to latin-1 decoding")

    # ── Step 1: split on Markdown headers ─────────────────────────
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT,
        strip_headers=False,   # keep headers in the chunk text
    )
    sections = header_splitter.split_text(text)

    # ── Step 2: recursive fallback within each section ────────────
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=cfg.md_chunk_size,
        chunk_overlap=cfg.md_chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[Chunk] = []
    now = datetime.now(timezone.utc).isoformat()

    for section in sections:
        sub_texts = recursive_splitter.split_text(section.page_content)
        for sub_text in sub_texts:
            if not sub_text.strip():
                continue
            metadata = ChunkMetadata(
                source=source,
                doc_type="md",
                access_role=access_role,
                section=section.metadata,   # {"h1": "Leave Policy", "h2": "Sick Leave", …}
                ingestion_timestamp=now,
                doc_version=etag,
            )
            chunks.append(Chunk(text=sub_text.strip(), metadata=metadata))

    logger.info(f"{source}: {len(chunks)} markdown chunks produced")
    return chunks
