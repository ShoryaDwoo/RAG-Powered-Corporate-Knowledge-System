"""
FastAPI application — chat/query only.

Endpoints:
  POST /query   — Employee asks a question; role resolved from employee_id
  GET  /health  — Liveness check

Ingestion is handled by the GitHub Actions workflow (run_ingest.py), not via API.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from retrieval.retriever import search
from retrieval.generator import generate_answer
from config import ROLE_PERMISSIONS
from config.settings import  get_role_for_employee
from utils import logger

app = FastAPI(
    title="HR RAG Pipeline",
    description="Document-aware RAG with Qdrant + AWS S3 + RBAC",
    version="2.0.0",
)


# ── Request / Response schemas ────────────────────────────────────

class QueryRequest(BaseModel):
    employee_id: str
    question: str
    top_k: int = 5

class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    role_used: str


# ── Endpoints ──────────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse)
async def query(body: QueryRequest):
    """
    Employee chat/query endpoint.

    Resolves the employee's role from their employee_id, then performs
    an RBAC-filtered semantic search and generates a grounded answer.
    """
    role = get_role_for_employee(body.employee_id)
    if role is None:
        raise HTTPException(
            status_code=403,
            detail=f"Employee ID '{body.employee_id}' not found or has no assigned role.",
        )
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{role}' is not a recognised role.",
        )

    logger.info(f"/query | employee_id={body.employee_id} | role={role} | question={body.question[:80]!r}")

    results = search(
        question=body.question,
        employee_role=role,
        top_k=body.top_k,
    )
    for i, result in enumerate(results, 1):
        print(f"\n--- RETRIEVED RESULT #{i} ---")
        print(f"Score: {result.score}")
        print(f"Source: {result.source}")
        print(f"Text: {result.text[:1500]}")

        
    answer = generate_answer(body.question, results)
    sources = list({r.source for r in results})

    return QueryResponse(answer=answer, sources=sources, role_used=role)


@app.get("/health")
async def health():
    return {"status": "ok"}
