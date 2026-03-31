"""
Hybrid relevance filter — combines LLM intent check + vector similarity threshold.
"""

from typing import List, Dict, Any

import config


def check_relevance(
    is_tax_related: bool,
    results: List[Dict[str, Any]],
    threshold: float | None = None,
) -> Dict[str, Any]:
    """
    Determine whether the retrieved results are relevant.

    Logic:
      1. If the LLM flagged the query as non-tax → irrelevant.
      2. If the best similarity score < threshold → irrelevant.

    Parameters
    ----------
    is_tax_related : bool
        From the query rewriter / intent classifier.
    results : list[dict]
        Retrieved chunks with "score" keys.
    threshold : float, optional
        Minimum cosine similarity (default from config).

    Returns
    -------
    dict
        On irrelevant: {"status": "irrelevant", "message": "..."}
        On relevant:    {"status": "relevant", "results": <filtered results>}
    """
    threshold = threshold or config.SIMILARITY_THRESHOLD

    # ── Condition 1: intent gate ───────────────────────────────────────
    if not is_tax_related:
        return {
            "status": "irrelevant",
            "message": "Query not related to income tax",
        }

    # ── Condition 2: similarity gate ───────────────────────────────────
    if not results:
        return {
            "status": "irrelevant",
            "message": "No matching documents found",
        }

    max_score = max(r["score"] for r in results)
    if max_score < threshold:
        return {
            "status": "irrelevant",
            "message": (
                f"Retrieved documents below relevance threshold "
                f"(best score {max_score:.4f} < {threshold})"
            ),
        }

    # Keep only chunks that pass the threshold
    filtered = [r for r in results if r["score"] >= threshold]

    return {
        "status": "relevant",
        "results": filtered,
    }
