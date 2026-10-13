from langchain_huggingface import HuggingFaceEmbeddings
from tenacity import retry, retry_if_exception_type, wait_exponential, stop_after_attempt
from qdrant_client.http.exceptions import UnexpectedResponse as ClientError, ResponseHandlingException as ServerError

from config import cfg
from utils import logger

embed = HuggingFaceEmbeddings(
    model_name=cfg.embedding_model,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

BATCH_SIZE = 100


@retry(
    retry=retry_if_exception_type((ClientError, ServerError)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _embed_single_query(text: str) -> list[float]:
    """Embed a single query string."""
    return embed.embed_documents([text])[0]  # wrap in list, unwrap result


def _embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of documents."""
    return embed.embed_documents(texts)


def embed_single(text: str) -> list[float]:
    """Generate a query embedding for retrieval."""
    vec = _embed_single_query(text)

    if len(vec) != cfg.embedding_dimensions:
        raise ValueError(
            f"Embedding dimension mismatch: got {len(vec)}, "
            f"expected {cfg.embedding_dimensions}"
        )
    return vec


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts in batches for ingestion.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors.
    """
    all_vectors: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i: i + BATCH_SIZE]
        vectors = _embed_batch(batch)
        all_vectors.extend(vectors)
        logger.debug(f"Embedded batch {i // BATCH_SIZE + 1} ({len(batch)} texts)")

    if any(len(v) != cfg.embedding_dimensions for v in all_vectors):
        raise ValueError(
            f"Embedding dimension mismatch in batch: "
            f"expected {cfg.embedding_dimensions}"
        )

    return all_vectors