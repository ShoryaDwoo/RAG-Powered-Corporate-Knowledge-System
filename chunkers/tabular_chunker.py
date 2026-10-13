"""
Tabular chunker — Row-as-a-Chunk strategy for .csv and .xlsx files.

Never pass spreadsheet data into a text splitter — doing so decouples
cell values from their column headers, destroying meaning.

Instead, each row is serialized as a self-contained string:
  "EmployeeID: E001 | Department: HR | LeaveBalance: 18 | Manager: Jane Doe"

This ensures the embedding model sees a complete, labelled record and
semantic search can match "how much leave does E001 have?" precisely.

For multi-sheet Excel files, the sheet name is prepended to each row
so the origin context is never lost.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Literal

import pandas as pd

from utils import logger
from utils import Chunk, ChunkMetadata


def _serialize_row(row: pd.Series, sheet: str | None = None) -> str:
    """Convert a DataFrame row to a pipe-delimited labelled string."""
    parts = [f"{col}: {val}" for col, val in row.items() if pd.notna(val)]
    row_str = " | ".join(parts)
    if sheet:
        return f"Sheet: {sheet} | {row_str}"
    return row_str


def _chunk_dataframe(
    df: pd.DataFrame,
    source: str,
    access_role: str,
    etag: str,
    sheet: str | None,
    doc_type: Literal["csv", "xlsx"],
) -> list[Chunk]:
    """Shared logic for both CSV and Excel chunking."""
    # Drop entirely empty rows
    df = df.dropna(how="all")
    # Normalise column names: strip whitespace
    df.columns = [str(c).strip() for c in df.columns]

    now = datetime.now(timezone.utc).isoformat()
    chunks: list[Chunk] = []

    for row_index, row in df.iterrows():
        text = _serialize_row(row, sheet=sheet)
        if not text.strip():
            continue
        metadata = ChunkMetadata(
            source=source,
            doc_type=doc_type,
            access_role=access_role,
            sheet=sheet,
            row_index=int(row_index),  # type: ignore[arg-type]
            ingestion_timestamp=now,
            doc_version=etag,
        )
        chunks.append(Chunk(text=text, metadata=metadata))

    return chunks


def chunk_csv(raw: bytes, source: str, access_role: str, etag: str = "") -> list[Chunk]:
    """
    Parse a CSV file into one chunk per data row.

    Args:
        raw:         Raw bytes of the .csv file.
        source:      S3 key.
        access_role: RBAC role tag.
        etag:        S3 ETag.

    Returns:
        List of Chunk objects, one per non-empty row.
    """
    try:
        df = pd.read_csv(io.BytesIO(raw), dtype=str)
    except Exception as exc:
        logger.error(f"Failed to parse CSV {source}: {exc}")
        raise

    chunks = _chunk_dataframe(df, source, access_role, etag, sheet=None, doc_type="csv")
    logger.info(f"{source}: {len(chunks)} CSV row chunks")
    return chunks


def chunk_excel(raw: bytes, source: str, access_role: str, etag: str = "") -> list[Chunk]:
    """
    Parse an Excel file (.xlsx) into one chunk per data row across all sheets.

    Each chunk is prefixed with the sheet name so multi-sheet files retain
    their origin context after embedding.

    Args:
        raw:         Raw bytes of the .xlsx file.
        source:      S3 key.
        access_role: RBAC role tag.
        etag:        S3 ETag.

    Returns:
        List of Chunk objects, one per non-empty row across all sheets.
    """
    try:
        xl = pd.ExcelFile(io.BytesIO(raw), engine="openpyxl")
    except Exception as exc:
        logger.error(f"Failed to open Excel {source}: {exc}")
        raise

    chunks: list[Chunk] = []
    for sheet_name in xl.sheet_names:
        df = xl.parse(sheet_name, dtype=str)
        sheet_chunks = _chunk_dataframe(
            df, source, access_role, etag,
            sheet=sheet_name, doc_type="xlsx",
        )
        chunks.extend(sheet_chunks)
        logger.debug(f"{source} [{sheet_name}]: {len(sheet_chunks)} row chunks")

    logger.info(f"{source}: {len(chunks)} Excel row chunks across {len(xl.sheet_names)} sheet(s)")
    return chunks
