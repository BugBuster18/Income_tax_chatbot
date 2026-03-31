"""
Embedding module — converts text chunks into dense vectors via Gemini.
Includes rate-limit handling for the free tier (100 req/min).
"""

import time
from typing import List

import numpy as np
from google import genai
from google.genai import errors as genai_errors

import config


def get_client() -> genai.Client:
    """Return a configured Gemini client."""
    return genai.Client(api_key=config.GEMINI_API_KEY)


def _embed_batch_with_retry(
    client: genai.Client,
    batch: List[str],
    max_retries: int = 5,
) -> list:
    """
    Embed a single batch, retrying on 429 (rate-limit) errors
    with exponential back-off.
    """
    for attempt in range(max_retries):
        try:
            result = client.models.embed_content(
                model=config.GEMINI_EMBEDDING_MODEL,
                contents=batch,
            )
            return [emb.values for emb in result.embeddings]

        except genai_errors.ClientError as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = min(2 ** attempt * 10, 60)  # 10s, 20s, 40s, 60s, 60s
                print(f"[embedder] Rate limited — waiting {wait}s "
                      f"(attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise  # Non-rate-limit error → propagate immediately

    raise RuntimeError("[embedder] Exceeded max retries for embedding batch")


def embed_texts(texts: List[str], client: genai.Client | None = None) -> np.ndarray:
    """
    Embed a list of texts using the configured Gemini embedding model.

    Sends small batches with delays between them to stay under
    the free-tier rate limit (100 requests / minute).

    Parameters
    ----------
    texts : list[str]
        Raw text strings to embed.
    client : genai.Client, optional
        Reuse an existing client; creates one if not provided.

    Returns
    -------
    np.ndarray
        Shape (len(texts), EMBEDDING_DIM).
    """
    if client is None:
        client = get_client()

    all_embeddings: List[List[float]] = []

    # Keep batches small (20 texts each) so we can pace requests
    # and stay under 100 req/min on the free tier.
    batch_size = 20
    total_batches = (len(texts) + batch_size - 1) // batch_size

    for batch_num, i in enumerate(range(0, len(texts), batch_size), start=1):
        batch = texts[i : i + batch_size]

        print(f"[embedder] Embedding batch {batch_num}/{total_batches} "
              f"({len(batch)} texts)...")

        embeddings = _embed_batch_with_retry(client, batch)
        all_embeddings.extend(embeddings)

        # Pace ourselves: wait between batches (skip after last batch)
        if batch_num < total_batches:
            time.sleep(1.5)  # ~40 batches/min → well within 100 req/min

    vectors = np.array(all_embeddings, dtype="float32")
    print(f"[embedder] Embedded {vectors.shape[0]} text(s) → {vectors.shape[1]}-d vectors")
    return vectors


def embed_query(query: str, client: genai.Client | None = None) -> np.ndarray:
    """Embed a single query string. Returns shape (1, EMBEDDING_DIM)."""
    return embed_texts([query], client=client)
