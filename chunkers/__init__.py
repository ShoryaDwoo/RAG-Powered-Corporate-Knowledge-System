"""
Format router — dispatches raw document bytes to the correct chunker
based on the file extension extracted from the S3 key.
"""
import os
from utils import logger
from utils import Chunk
from .markdown_chunker import chunk_markdown
from .pdf_chunker import chunk_pdf
from .tabular_chunker import chunk_csv, chunk_excel
from .docx_chunker import chunk_docx
from .text_chunker import chunk_txt


def route_and_chunk(
    key: str,
    raw: bytes,
    access_role: str,
    etag: str = "",
) -> list[Chunk]:
    """
    Route a raw document to its format-specific chunker.

    Args:
        key:         S3 object key (determines format by extension).
        raw:         Raw file bytes.
        access_role: RBAC tag inherited from the S3 prefix.
        etag:        S3 ETag stored as doc_version for cache invalidation.

    Returns:
        List of Chunk objects ready for embedding.

    Raises:
        ValueError: If the file extension is not supported.
    """
    ext = os.path.splitext(key)[-1].lower()

    if ext == ".md":
        return chunk_markdown(raw, key, access_role, etag)
    elif ext == ".pdf":
        return chunk_pdf(raw, key, access_role, etag)
    elif ext == ".csv":
        return chunk_csv(raw, key, access_role, etag)
    elif ext == ".xlsx":
        return chunk_excel(raw, key, access_role, etag)
    elif ext in (".doc", ".docx"):
        return chunk_docx(raw, key, access_role, etag)
    elif ext == ".txt":
        return chunk_txt(raw, key, access_role, etag)
    else:
        logger.warning(f"Unsupported file type: {ext} for key {key}")
        raise ValueError(f"Unsupported file extension: {ext}")


__all__ = [
    "route_and_chunk",
    "chunk_markdown",
    "chunk_pdf",
    "chunk_csv",
    "chunk_excel",
    "chunk_docx",
    "chunk_txt",
]