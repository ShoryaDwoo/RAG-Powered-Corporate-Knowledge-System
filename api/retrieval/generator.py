"""
RAG generator — Groq primary, Ollama fallback, Redis cache.
Cache key: hash of (question + top source) — same question hits cache instantly.
"""
from __future__ import annotations

import hashlib
import json
from typing import AsyncGenerator

import httpx
import redis.asyncio as aioredis
import requests
from groq import Groq, APIConnectionError, APITimeoutError, APIStatusError

from config import cfg
from utils import logger, QueryResult

SYSTEM_PROMPT = """You are a helpful HR and internal systems assistant.
Answer the employee's question using ONLY the context passages provided below.
If the answer is not contained in the context, say:
"I don't have that information in the documents available to me."
Do not invent or infer details not present in the context.
Cite the source document name when relevant."""

GROQ_MODEL = "llama-3.1-8b-instant"

_groq_client = Groq(api_key=cfg.groq_api_key_key)

# ── Redis client (async) ──────────────────────────────────────────
_redis: aioredis.Redis = aioredis.from_url(
    cfg.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


# ── Cache helpers ─────────────────────────────────────────────────

def _cache_key(question: str, results: list[QueryResult]) -> str:
    """
    Deterministic cache key from question + top source.
    Same question against the same document = cache hit.
    """
    top_source = results[0].source if results else "none"
    raw = f"{question.strip().lower()}::{top_source}"
    return "hr_rag:" + hashlib.md5(raw.encode()).hexdigest()


async def _get_cache(key: str) -> str | None:
    try:
        value = await _redis.get(key)
        if value:
            logger.info(f"Cache HIT: {key}")
        return value
    except Exception as exc:
        logger.warning(f"Redis get failed: {exc}")
        return None


async def _set_cache(key: str, value: str) -> None:
    try:
        await _redis.set(key, value, ex=cfg.redis_cache_ttl)
        logger.info(f"Cache SET: {key} (TTL={cfg.redis_cache_ttl}s)")
    except Exception as exc:
        logger.warning(f"Redis set failed: {exc}")


# ── Shared helpers ────────────────────────────────────────────────

def _build_context(question: str, results: list[QueryResult]) -> str:
    context_parts = []
    for i, r in enumerate(results, 1):
        source_label = r.source
        if r.page is not None:
            source_label += f" (page {r.page})"
        text = " ".join(r.text.split()[:300])
        context_parts.append(f"[{i}] Source: {source_label}\n{text}")
    return "\n\n---\n\n".join(context_parts)


def _no_results_msg() -> str:
    return (
        "I couldn't find any relevant information in the documents "
        "available to you. Please contact HR directly."
    )


# ── Sync ──────────────────────────────────────────────────────────

def generate_answer(
    question: str,
    results: list[QueryResult],
) -> str:
    """Sync generation — no cache (use streaming endpoint instead)."""
    if not results:
        return _no_results_msg()

    context_block = _build_context(question, results)

    try:
        logger.debug(f"Groq sync | {len(results)} chunks | model={GROQ_MODEL}")
        response = _groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context_block}\n\nEmployee question: {question}"},
            ],
            temperature=0.1,
            max_tokens=512,
            stream=False,
        )
        answer = (response.choices[0].message.content or "").strip()
        logger.info(f"Groq answer ({len(answer)} chars)")
        return answer

    except (APIConnectionError, APITimeoutError, APIStatusError) as exc:
        logger.warning(f"Groq failed ({exc}) — falling back to Ollama")
        return _ollama_sync(question, context_block)


def _ollama_sync(question: str, context_block: str) -> str:
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Context:\n{context_block}\n\n"
        f"Employee question: {question}\n\nAnswer:"
    )
    try:
        res = requests.post(
            f"{cfg.ollama_url}/api/generate",
            json={
                "model": cfg.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 512, "num_ctx": 2048},
            },
            timeout=120,
        )
        res.raise_for_status()
        return res.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        logger.error(f"Ollama unreachable at {cfg.ollama_url}")
        return "The assistant is currently unavailable. Please contact HR directly."
    except requests.exceptions.Timeout:
        logger.error("Ollama timed out")
        return "The assistant timed out. Please try again."
    except requests.exceptions.HTTPError as exc:
        logger.error(f"Ollama HTTP error: {exc}")
        return "The assistant encountered an error. Please try again."


# ── Streaming (with Redis cache) ──────────────────────────────────

async def generate_answer_stream(
    question: str,
    results: list[QueryResult],
) -> AsyncGenerator[str, None]:
    """
    Async streaming — checks Redis cache first.
    Cache hit:  yields full answer instantly, no LLM call.
    Cache miss: streams from Groq (or Ollama), saves to cache when done.
    """
    if not results:
        yield _no_results_msg()
        return

    cache_key = _cache_key(question, results)

    # ── Cache hit ──
    cached = await _get_cache(cache_key)
    if cached:
        yield cached
        return

    context_block = _build_context(question, results)
    full_answer: list[str] = []

    # ── Groq stream ──
    groq_ok = False
    try:
        logger.debug(f"Groq stream | {len(results)} chunks | model={GROQ_MODEL}")
        stream = _groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context_block}\n\nEmployee question: {question}"},
            ],
            temperature=0.1,
            max_tokens=512,
            stream=True,
        )
        for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            if token:
                full_answer.append(token)
                yield token
        groq_ok = True

    except (APIConnectionError, APITimeoutError, APIStatusError) as exc:
        logger.warning(f"Groq stream failed ({exc}) — falling back to Ollama")

    # ── Ollama stream fallback ──
    if not groq_ok:
        async for token in _ollama_stream(question, context_block):
            full_answer.append(token)
            yield token

    # ── Save to cache ──
    if full_answer:
        await _set_cache(cache_key, "".join(full_answer))


async def _ollama_stream(
    question: str,
    context_block: str,
) -> AsyncGenerator[str, None]:
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Context:\n{context_block}\n\n"
        f"Employee question: {question}\n\nAnswer:"
    )
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{cfg.ollama_url}/api/generate",
                json={
                    "model": cfg.ollama_model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {"temperature": 0.1, "num_predict": 512, "num_ctx": 2048},
                },
            ) as res:
                res.raise_for_status()
                async for line in res.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    token = data.get("response", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break

    except httpx.ConnectError:
        logger.error(f"Ollama unreachable at {cfg.ollama_url}")
        yield "The assistant is currently unavailable. Please contact HR directly."
    except httpx.TimeoutException:
        logger.error("Ollama stream timed out")
        yield "The assistant timed out. Please try again."
    except httpx.HTTPStatusError as exc:
        logger.error(f"Ollama HTTP error: {exc}")
        yield "The assistant encountered an error. Please try again."