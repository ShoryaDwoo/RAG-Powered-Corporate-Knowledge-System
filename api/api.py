"""
FastAPI application — chat/query only.

Endpoints:
  POST /query        — Employee asks a question; role resolved from employee_id
  POST /query/stream — Streaming version of /query (token by token)
  GET  /health       — Liveness check
"""
from __future__ import annotations

import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from retrieval.retriever import search
from retrieval.generator import generate_answer, generate_answer_stream
from config import ROLE_PERMISSIONS
from config.settings import get_role_for_employee
from utils import logger

app = FastAPI(
    title="HR RAG Pipeline",
    description="Document-aware RAG with Qdrant + AWS S3 + RBAC",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    employee_id: str
    question: str
    top_k: int = 5


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    role_used: str


# ── Helpers ───────────────────────────────────────────────────────

def _resolve_role(employee_id: str) -> str:
    role = get_role_for_employee(employee_id)
    if role is None:
        raise HTTPException(
            status_code=403,
            detail=f"Employee ID '{employee_id}' not found or has no assigned role.",
        )
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{role}' is not a recognised role.",
        )
    return role


def _get_results(body: QueryRequest, role: str):
    results = search(
        question=body.question,
        employee_role=role,
        top_k=body.top_k,
    )
    # Keep only the top result for the LLM — fastest, most focused answer
    top = results[:1]

    if top:
        r = top[0]
        logger.info(
            f"Top result | score={r.score:.4f} | source={r.source}"
        )

    return top


# ── Endpoints ─────────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse)
async def query(body: QueryRequest):
    role = _resolve_role(body.employee_id)
    logger.info(f"/query | employee_id={body.employee_id} | role={role} | question={body.question[:80]!r}")

    top = _get_results(body, role)
    answer = generate_answer(body.question, top)
    sources = [r.source for r in top]

    return QueryResponse(answer=answer, sources=sources, role_used=role)


@app.post("/query/stream")
async def query_stream(body: QueryRequest):
    role = _resolve_role(body.employee_id)
    logger.info(f"/query/stream | employee_id={body.employee_id} | role={role} | question={body.question[:80]!r}")

    top = _get_results(body, role)
    sources = [r.source for r in top]

    async def event_stream():
        async for token in generate_answer_stream(body.question, top):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok"}