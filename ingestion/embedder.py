"""
Embedding client — Gemini.

Wraps the Google Gemini embeddings API with:
  - Automatic batching (max 100 texts per request)
  - Exponential-backoff retry on rate-limit / transient errors
  - Dimension validation against config
"""
from __future__ import annotations

import time
from typing import Sequence

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from config import cfg
from utils import logger

#genai.configure(api_key=cfg.gemini_api_key)
embed = HuggingFaceEmbeddings(
    model_name=cfg.embedding_model,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

BATCH_SIZE = 100   # Gemini embedContent supports batching up to 100 texts


@retry(
    retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
)
def _embed_batch(texts: list[str]) -> list[list[float]]:
    # result = genai.embed_content(
    #     model=cfg.embedding_model,           # e.g. "models/text-embedding-004"
    #     content=texts,
    #     task_type="RETRIEVAL_DOCUMENT",      # use RETRIEVAL_QUERY at query time
    #     output_dimensionality=cfg.embedding_dimensions,
    # )
    result = embed.embed_documents(
        texts

    )

    return result         # list of vectors, same order as input


@retry(
    retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
)
def _embed_single_query(text: str) -> list[float]:
    """Query-time embedding uses RETRIEVAL_QUERY task type for better accuracy."""
    # result = genai.embed_content(
        #     model=cfg.embedding_model,           # e.g. "models/text-embedding-004"
        #     content=texts,
        #     task_type="RETRIEVAL_DOCUMENT",      # use RETRIEVAL_QUERY at query time
        #     output_dimensionality=cfg.embedding_dimensions,
        # )
    result = embed.embed_documents(
        text

    )
   
    return result    


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """
    Embed a list of texts (ingestion), batching automatically.

    Args:
        texts: Strings to embed.

    Returns:
        List of float vectors in the same order as input.
    """
    texts = list(texts)
    all_vectors: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        logger.debug(f"Embedding batch {i // BATCH_SIZE + 1} ({len(batch)} texts)…")
        vectors = _embed_batch(batch)

        # Sanity-check dimensions
        for vec in vectors:
            if len(vec) != cfg.embedding_dimensions:
                raise ValueError(
                    f"Embedding dimension mismatch: got {len(vec)}, "
                    f"expected {cfg.embedding_dimensions}"
                )

        all_vectors.extend(vectors)
        if i + BATCH_SIZE < len(texts):
            time.sleep(0.05)

    logger.info(f"Embedded {len(all_vectors)} texts")
    return all_vectors


def embed_single(text: str) -> list[float]:
    """Query-time embedding (uses RETRIEVAL_QUERY task type)."""
    vec = _embed_single_query(text)
    if len(vec) != cfg.embedding_dimensions:
        raise ValueError(
            f"Embedding dimension mismatch: got {len(vec)}, "
            f"expected {cfg.embedding_dimensions}"
        )
    return vec