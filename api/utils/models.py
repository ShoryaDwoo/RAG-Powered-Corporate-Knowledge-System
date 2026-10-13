"""
Shared Pydantic models and plain dataclasses used across ingestion,
retrieval, and the API layer.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Optional


# ── Chunk types ───────────────────────────────────────────────────

@dataclass
class ChunkMetadata:
    source: str                   # S3 key, e.g. "hr/leave_policy.pdf"
    doc_type: Literal["md", "pdf", "csv", "xlsx"]
    access_role: str              # "HR-Admin" | "Finance" | "General-Staff" | "Public"
    section: Optional[dict] = None      # Markdown header hierarchy
    page: Optional[int] = None          # PDF page number
    child_index: Optional[int] = None   # Position within parent page
    sheet: Optional[str] = None         # Excel sheet name
    row_index: Optional[int] = None     # Tabular row index
    ingestion_timestamp: Optional[str] = None
    doc_version: Optional[str] = None   # S3 VersionId or ETag


@dataclass
class Chunk:
    """A single unit ready for embedding and upsert into Qdrant."""
    text: str                     # Text to embed (child text for PDFs)
    metadata: ChunkMetadata
    parent_text: Optional[str] = None  # Full-page context for PDFs; None for others


# ── Query models ──────────────────────────────────────────────────

@dataclass
class QueryResult:
    text: str                     # Text shown / passed to LLM
    score: float                  # Cosine similarity
    source: str
    doc_type: str
    page: Optional[int] = None


@dataclass
class QueryRequest:
    question: str
    employee_role: str
    top_k: int = 5
