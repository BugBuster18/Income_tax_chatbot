"""
Context builder — assembles the final structured output from the pipeline.
"""

from typing import List, Dict, Any


def build_context(
    original_query: str,
    rewritten_query: str,
    relevant_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build the structured RAG output.

    Returns
    -------
    dict
        {
          "status": "success",
          "query": <original>,
          "rewritten_query": <rewritten>,
          "contexts": [<chunk texts>]
        }
    """
    contexts = [r["text"] for r in relevant_results]

    output = {
        "status": "success",
        "query": original_query,
        "rewritten_query": rewritten_query,
        "contexts": contexts,
    }

    print(f"[context_builder] Built context with {len(contexts)} chunk(s)")
    return output


def build_irrelevant_response(message: str) -> Dict[str, Any]:
    """Return a standardised 'irrelevant' response."""
    return {
        "status": "irrelevant",
        "message": message,
    }
