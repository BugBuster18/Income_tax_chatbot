"""
Central configuration for the Income Tax RAG pipeline.
All tuneable parameters live here so every module stays decoupled.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "rag_docs"
FAISS_INDEX_PATH = BASE_DIR / "data" / "faiss_index"
CHUNKS_CACHE_PATH = BASE_DIR / "data" / "chunks_cache.json"

# ── Gemini ─────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_LLM_MODEL = "gemini-2.5-flash"
GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-001" 

# ── Chunking ───────────────────────────────────────────────────────────
CHUNK_SIZE = 400
CHUNK_OVERLAP = 50

# ── Retrieval ──────────────────────────────────────────────────────────
TOP_K = 5
SIMILARITY_THRESHOLD = 0.5

# ── Embedding dimension (text-embedding-004 produces 768-d vectors) ───
EMBEDDING_DIM = 3072 
