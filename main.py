"""
Income Tax RAG Pipeline — main entry point.

Flow:
  1. Load & chunk documents (or reload cached FAISS index)
  2. Accept user query
  3. Rewrite + classify intent (LLM)
  4. Retrieve top-K chunks (FAISS)
  5. Hybrid relevance filter
  6. Build structured output
"""

import json
import sys

from google import genai

import config
from rag.loader import load_documents
from rag.chunker import chunk_documents
from rag.embedder import embed_texts
from rag.vector_store import build_index, save_index, load_index
from rag.retriever import retrieve
from rag.query_rewriter import rewrite_query
from rag.relevance import check_relevance
from rag.context_builder import build_irrelevant_response
from rag.structured_generator import generate_structured_data
from rag.final_response_generator import generate_final_response

sys.path.append(str(config.BASE_DIR / "rule_engine" / "Mini-project"))
try:
    from validator import validate_all
except ImportError as e:
    print(f"Warning: Could not import rule_engine. validator: {e}")
    validate_all = None


# ── Index initialisation ───────────────────────────────────────────────

def initialise_index(force_rebuild: bool = False):
    """
    Load existing FAISS index from disk, or build a new one from
    the documents in data/rag_docs.

    Returns (index, chunks).
    """
    if not force_rebuild:
        cached = load_index()
        if cached is not None:
            return cached

    # Build from scratch
    documents = load_documents(config.DATA_DIR)
    if not documents:
        print("[main] No documents found. Add .txt files to data/rag_docs/ and retry.")
        sys.exit(1)

    chunks = chunk_documents(documents, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    texts = [c["text"] for c in chunks]

    vectors = embed_texts(texts)
    index = build_index(vectors)
    save_index(index, chunks)

    return index, chunks


# ── Pipeline ───────────────────────────────────────────────────────────

def run_pipeline(user_query: str, index, chunks, client: genai.Client):
    """
    Execute the full RAG pipeline for a single query.

    Returns a structured dict (success or irrelevant).
    """
    # Step 1 — rewrite + classify
    rewrite_result = rewrite_query(user_query, client=client)
    rewritten = rewrite_result["rewritten_query"]
    is_tax = rewrite_result["is_tax_related"]

    # Step 2 — early exit if non-tax
    if not is_tax:
        return build_irrelevant_response("Query not related to income tax")

    # Step 3 — retrieve
    results = retrieve(rewritten, index, chunks, client=client)

    # Step 4 — hybrid relevance check
    rel = check_relevance(is_tax, results)

    if rel["status"] == "irrelevant":
        return build_irrelevant_response(rel["message"])

    # Step 5 — generate structured JSON from contexts
    contexts = [r["text"] for r in rel["results"]]
    
    current_query = user_query
    while True:
        structured_res = generate_structured_data(current_query, contexts, client=client)

        if structured_res.get("status") == "need_more_info":
            question = structured_res.get("question", "I need more information to proceed.")
            try:
                user_reply = input(f"\n[System]: {question}\n>> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                sys.exit(0)
                
            if not user_reply or user_reply.lower() in ("quit", "exit", "q"):
                print("\nBye!")
                sys.exit(0)
                
            current_query += f"\nSystem asked: {question}\nUser clarified: {user_reply}"
        else:
            break

    if structured_res.get("status") == "success" and validate_all is not None:
        # Step 6 — Pass the generated structured JSON to Rule Engine (which internally uses Z3)
        user_data = structured_res.get("data", {})
        print("\n[main] Passing extracted structured data to Rule Engine...")
        validation_result = validate_all(user_data)
        
        # Combine RAG success with validation info
        print("[main] Generating final explanation from LLM...")
        final_answer = generate_final_response(current_query, validation_result, client=client)
        
        return {
            "status": "success",
            "extracted_data": user_data,
            "rule_engine_result": validation_result,
            "final_answer": final_answer
        }
        
    return structured_res


# ── CLI ────────────────────────────────────────────────────────────────

def main():
    if not config.GEMINI_API_KEY:
        print("ERROR: Set the GEMINI_API_KEY environment variable first.")
        sys.exit(1)

    print("=" * 60)
    print("  Income Tax RAG Pipeline")
    print("=" * 60)

    index, chunks = initialise_index()
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    print("\nReady. Type a query (or 'quit' to exit).\n")

    while True:
        try:
            user_input = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        result = run_pipeline(user_input, index, chunks, client)
        if "final_answer" in result:
            print("\n" + "="*60)
            print("  INTERMEDIARY STEPS (DEBUG)  ")
            print("="*60)
            debug_info = {
                "extracted_data": result.get("extracted_data"),
                "rule_engine_result": result.get("rule_engine_result")
            }
            print(json.dumps(debug_info, indent=2, ensure_ascii=False))
            print("\n" + "="*60)
            print("  TAX CALCULATION SUMMARY  ")
            print("="*60)
            print(result["final_answer"])
            print("="*60 + "\n")
        else:
            print("\n" + json.dumps(result, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
