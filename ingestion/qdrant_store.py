"""
Qdrant vector store wrapper.

Handles:
  - Collection creation / verification on startup
  - Batch upsert of Chunk objects with full metadata payloads
  - Indexed payload fields for fast RBAC pre-filtering
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from config import cfg
from utils import logger
from utils import Chunk, QueryResult

UPSERT_BATCH_SIZE = 100


def _build_client() -> QdrantClient:
    kwargs: dict = {"url": cfg.qdrant_url}
    if cfg.qdrant_api_key:
        kwargs["api_key"] = cfg.qdrant_api_key
    return QdrantClient(**kwargs)


def _make_point_id(source: str, chunk_index: int) -> str:
    """
    Deterministic UUID derived from source key + chunk position.
    Guarantees that re-ingesting the same document overwrites existing
    points rather than creating duplicates.
    """
    raw = f"{source}:{chunk_index}".encode()
    hex_digest = hashlib.md5(raw).hexdigest()
    return str(uuid.UUID(hex_digest))


def ensure_collection(client: QdrantClient | None = None) -> QdrantClient:
    """
    Ensure the Qdrant collection exists with the correct vector config
    and payload indexes on `access_role` and `source` for fast filtering.

    Creates the collection if absent; does nothing if it already exists.

    Returns:
        Configured QdrantClient instance.
    """
    client = client or _build_client()

    existing = {c.name for c in client.get_collections().collections}

    if cfg.qdrant_collection not in existing:
        client.create_collection(
            collection_name=cfg.qdrant_collection,
            vectors_config=VectorParams(
                size=cfg.embedding_dimensions,
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"Created Qdrant collection '{cfg.qdrant_collection}'")

        client.create_payload_index(
            collection_name=cfg.qdrant_collection,
            field_name="access_role",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        client.create_payload_index(
            collection_name=cfg.qdrant_collection,
            field_name="source",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info("Payload indexes created on 'access_role' and 'source'")
    else:
        logger.debug(f"Collection '{cfg.qdrant_collection}' already exists — skipping creation")

    return client


def upsert_chunks(
    chunks: list[Chunk],
    vectors: list[list[float]],
    client: QdrantClient | None = None,
) -> int:
    """
    Upsert Chunk objects with deterministic point IDs to prevent duplicates.

    Point ID is derived from (source, chunk_index) so re-ingesting the same
    document overwrites existing vectors rather than stacking new ones.

    Args:
        chunks:   Chunk objects from the chunkers.
        vectors:  Corresponding embedding vectors (same order as chunks).
        client:   Optional pre-built QdrantClient.

    Returns:
        Total number of points upserted.
    """
    assert len(chunks) == len(vectors), "chunks and vectors must have equal length"
    client = client or _build_client()

    points: list[PointStruct] = []
    for chunk_index, (chunk, vector) in enumerate(zip(chunks, vectors)):
        payload = {
            "text": chunk.text,
            "parent_text": chunk.parent_text,
            **asdict(chunk.metadata),
        }
        point_id = _make_point_id(chunk.metadata.source, chunk_index)
        points.append(PointStruct(
            id=point_id,
            vector=vector,
            payload=payload,
        ))

    total = 0
    for i in range(0, len(points), UPSERT_BATCH_SIZE):
        batch = points[i : i + UPSERT_BATCH_SIZE]
        client.upsert(collection_name=cfg.qdrant_collection, points=batch)
        total += len(batch)
        logger.debug(f"Upserted batch {i // UPSERT_BATCH_SIZE + 1} ({len(batch)} points)")

    logger.info(f"Total upserted: {total} points into '{cfg.qdrant_collection}'")
    return total


def delete_by_source(source: str, client: QdrantClient | None = None) -> None:
    """
    Delete all points for a given source document (by S3 key).
    Use before re-ingesting an updated document.
    """
    client = client or _build_client()
    client.delete(
        collection_name=cfg.qdrant_collection,
        points_selector=Filter(
            must=[FieldCondition(key="source", match=MatchAny(any=[source]))]
        ),
    )
    logger.info(f"Deleted all points for source: {source}")