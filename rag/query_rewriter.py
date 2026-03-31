"""
Query rewriter + intent classifier — uses Gemini LLM to:
  1. Rewrite the user query for better retrieval.
  2. Classify whether the query is related to Indian income tax.
"""

import json
from typing import Dict, Any

from google import genai

import config


SYSTEM_PROMPT = """\
You are a query optimization engine for a vector database retrieval system focused on Indian Income Tax.

Your tasks:
1. Determine whether the user query is related to Indian income tax.
2. If YES:
   - Transform the query into a highly optimized retrieval query.
3. If NO:
   - Mark it as not related.

---

# RULES

1. Expand the query with relevant income tax concepts, sections, and keywords.
2. Include related deductions, exemptions, regimes, and conditions if applicable.
3. Add synonyms and alternate phrasings commonly found in tax documents.
4. Include structured hints such as:
   - income type (salary, business, capital gains)
   - tax regime (old vs new)
   - relevant sections (80C, 80D, 24, 10, etc.)
5. DO NOT explain anything.
6. DO NOT answer the question.
7. Keep the optimized query concise but information-dense.

---

# OUTPUT FORMAT (STRICT JSON)

{
  "is_tax_related": true/false,
  "rewritten_query": "optimized query string or empty string if not relevant"
}
"""


def rewrite_query(
    user_query: str,
    client: genai.Client | None = None,
) -> Dict[str, Any]:
    """
    Call Gemini to rewrite the query and classify intent.

    Parameters
    ----------
    user_query : str
        Raw user input query.

    Returns
    -------
    dict
        {
            "rewritten_query": str,
            "is_tax_related": bool
        }
    """
    if client is None:
        client = genai.Client(api_key=config.GEMINI_API_KEY)

    # 🔹 LLM Call
    response = client.models.generate_content(
        model=config.GEMINI_LLM_MODEL,
        contents=f"User Query:\n{user_query}",  # Improved context
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
        ),
    )

    raw = response.text.strip()

    # 🔹 Remove markdown code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(lines).strip()

    # 🔹 Safe JSON parsing
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Response is not a JSON object")
    except Exception:
        print(f"[query_rewriter] WARNING: invalid LLM response:\n{raw}")
        parsed = {
            "rewritten_query": user_query,
            "is_tax_related": False,
        }

    # 🔹 Ensure keys exist
    parsed["is_tax_related"] = bool(parsed.get("is_tax_related", False))

    if not parsed.get("rewritten_query"):
        parsed["rewritten_query"] = user_query

    # 🔹 Critical: prevent irrelevant queries from going to FAISS
    if not parsed["is_tax_related"]:
        parsed["rewritten_query"] = ""

    # 🔹 Debug logs
    print(f"[query_rewriter] Rewritten: {parsed['rewritten_query']}")
    print(f"[query_rewriter] Tax-related: {parsed['is_tax_related']}")

    return parsed