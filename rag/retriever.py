"""
Retriever — queries the FAISS index and returns top-K results with scores.
"""

from typing import List, Dict, Any

import faiss
import numpy as np

import config
from rag.embedder import embed_query


def retrieve(
    query: str,
    index: faiss.IndexFlatIP,
    chunks: List[Dict[str, str]],
    top_k: int | None = None,
    client=None,
) -> List[Dict[str, Any]]:
    """
    Retrieve the top-K most similar chunks for a given query.

    Parameters
    ----------
    query : str
        The (rewritten) user query.
    index : faiss.IndexFlatIP
        Pre-built FAISS index.
    chunks : list[dict]
        Chunk metadata parallel to the index vectors.
    top_k : int, optional
        Number of results (default from config).
    client : genai.Client, optional
        Gemini client for embedding.

    Returns
    -------
    list[dict]
        Each dict has "text", "source", and "score".
    """
    top_k = top_k or config.TOP_K

    # Embed the query
    query_vec = embed_query(query, client=client)  # shape (1, D)
    faiss.normalize_L2(query_vec)

    # Search
    scores, indices = index.search(query_vec, top_k)

    results: List[Dict[str, Any]] = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue  # FAISS sentinel for "no result"
        results.append({
            "text": chunks[idx]["text"],
            "source": chunks[idx].get("source", ""),
            "score": round(float(score), 4),
        })

    print(f"[retriever] Retrieved {len(results)} chunk(s)  "
          f"(top score: {results[0]['score'] if results else 'N/A'})")
    return results
