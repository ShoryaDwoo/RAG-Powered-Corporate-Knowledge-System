"""
Retriever — RBAC-enforced semantic search against Qdrant.

Security guarantee:
  The access_role filter is passed to Qdrant as a query_filter.
  This runs BEFORE the ANN (approximate nearest-neighbour) search,
  so restricted chunks never enter the similarity computation.
  They are mathematically invisible to the query.

Parent-child promotion:
  For PDF chunks, parent_text (full page) is returned to the LLM
  instead of the small child chunk used for vector matching.
"""
from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny

from config import cfg, ROLE_PERMISSIONS
from ingestion.embedder import embed_single
from ingestion.qdrant_store import _build_client
from utils import logger
from utils import QueryResult


def _allowed_roles(employee_role: str) -> list[str]:
    """
    Return the list of access_role values the employee is permitted to see.
    Defaults to Public-only if the role is unrecognised.
    """
    roles = ROLE_PERMISSIONS.get(employee_role)
    if roles is None:
        logger.warning(f"Unknown role '{employee_role}' — defaulting to Public only")
        return ["Public"]
    return roles


def search(
    question: str,
    employee_role: str,
    top_k: int | None = None,
    client: QdrantClient | None = None,
) -> list[QueryResult]:
    """
    Perform an RBAC-filtered semantic search.

    Args:
        question:      The employee's natural-language query.
        employee_role: The employee's RBAC role (read from verified JWT).
        top_k:         Number of results to return (defaults to cfg.top_k).
        client:        Optional pre-built QdrantClient.

    Returns:
        List of QueryResult objects sorted by cosine similarity (best first).
        For PDF hits, QueryResult.text contains the parent page text.
    """
    top_k = top_k or cfg.top_k
    client = client or _build_client()

    allowed = _allowed_roles(employee_role)
    logger.debug(f"Role '{employee_role}' → allowed roles: {allowed}")

    # ── Build RBAC pre-filter ─────────────────────────────────────
    rbac_filter = Filter(
        must=[
            FieldCondition(
                key="access_role",
                match=MatchAny(any=allowed),
            )
        ]
    )

    # ── Embed the query ───────────────────────────────────────────
    query_vector = embed_single(question)

    # ── Filtered ANN search ───────────────────────────────────────
    hits = client.search(
        collection_name=cfg.qdrant_collection,
        query_vector=query_vector,
        query_filter=rbac_filter,
        limit=top_k,
        with_payload=True,
    )

    # ── Build results, promoting parent_text for PDF hits ─────────
    results: list[QueryResult] = []
    for hit in hits:
        payload = hit.payload or {}
        doc_type = payload.get("doc_type", "")

        # PDF: serve full parent page to LLM; others: serve child/row text
        llm_text = (
            payload.get("parent_text") or payload.get("text", "")
            if doc_type == "pdf"
            else payload.get("text", "")
        )

        results.append(QueryResult(
            text=llm_text,
            score=hit.score,
            source=payload.get("source", ""),
            doc_type=doc_type,
            page=payload.get("page"),
        ))

    logger.info(
        f"Query returned {len(results)} results for role '{employee_role}' "
        f"(allowed: {allowed})"
    )
    return results
