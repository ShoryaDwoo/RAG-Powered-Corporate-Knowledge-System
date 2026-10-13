"""
RAG generator — uses self-hosted Ollama LLM on EC2.
"""
from __future__ import annotations

import requests
from config import cfg
from utils import logger, QueryResult

SYSTEM_PROMPT = """You are a helpful HR and internal systems assistant.
Answer the employee's question using ONLY the context passages provided below.
If the answer is not contained in the context, say:
"I don't have that information in the documents available to me."
Do not invent or infer details not present in the context.
Cite the source document name when relevant."""


def generate_answer(
    question: str,
    results: list[QueryResult],
    model: str | None = None,
) -> str:
    """
    Generate a grounded answer from retrieved context chunks
    using the self-hosted Ollama LLM.

    Args:
        question: The employee's original question.
        results:  QueryResult objects from the retriever (already RBAC-filtered).
        model:    Ollama model name (defaults to cfg.ollama_model).

    Returns:
        The model's answer as a string.
    """
    model = model or cfg.ollama_model

    if not results:
        return (
            "I couldn't find any relevant information in the documents "
            "available to you. Please contact HR directly."
        )

    # Build numbered context block
    context_parts = []
    for i, r in enumerate(results, 1):
        source_label = r.source
        if r.page is not None:
            source_label += f" (page {r.page})"
        context_parts.append(f"[{i}] Source: {source_label}\n{r.text}")

    context_block = "\n\n---\n\n".join(context_parts)

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Context:\n{context_block}\n\n"
        f"Employee question: {question}\n\n"
        f"Answer:"
    )

    logger.debug(f"Sending {len(results)} chunks to Ollama '{model}' at {cfg.ollama_url}")

    try:
        response = requests.post(
            f"{cfg.ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 1024,
                    "num_ctx": 4096,
                },
            },
            timeout=120,
        )
        response.raise_for_status()
        answer = response.json().get("response", "").strip()

    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to Ollama at {cfg.ollama_url}")
        return "The assistant is currently unavailable. Please contact HR directly."

    except requests.exceptions.Timeout:
        logger.error("Ollama request timed out after 120s")
        return "The assistant timed out. Please try again."

    except requests.exceptions.HTTPError as exc:
        logger.error(f"Ollama HTTP error: {exc}")
        return "The assistant encountered an error. Please try again."

    logger.info(f"Generated answer ({len(answer)} chars) via {model}")
    return answer