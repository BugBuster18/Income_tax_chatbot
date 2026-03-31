"""
FAISS vector store — build, save, and load a similarity index.
"""

import json
from pathlib import Path
from typing import List, Dict

import faiss
import numpy as np

import config


def build_index(vectors: np.ndarray) -> faiss.IndexFlatIP:
    """
    Build a FAISS inner-product (cosine after L2-normalisation) index.

    Parameters
    ----------
    vectors : np.ndarray
        Shape (N, D) — one vector per chunk.

    Returns
    -------
    faiss.IndexFlatIP
    """
    # L2-normalise so inner product == cosine similarity
    faiss.normalize_L2(vectors)
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    print(f"[vector_store] Built FAISS index with {index.ntotal} vectors (dim={dim})")
    return index


def save_index(
    index: faiss.IndexFlatIP,
    chunks: List[Dict[str, str]],
    index_dir: Path | None = None,
) -> None:
    """Persist FAISS index + chunk metadata to disk."""
    index_dir = index_dir or config.FAISS_INDEX_PATH
    index_dir.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(index_dir / "index.faiss"))

    with open(index_dir / "chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"[vector_store] Saved index + chunks to {index_dir}")


def load_index(
    index_dir: Path | None = None,
) -> tuple[faiss.IndexFlatIP, List[Dict[str, str]]] | None:
    """
    Load a previously saved FAISS index + chunk metadata.

    Returns None if the files do not exist.
    """
    index_dir = index_dir or config.FAISS_INDEX_PATH
    index_path = index_dir / "index.faiss"
    chunks_path = index_dir / "chunks.json"

    if not index_path.exists() or not chunks_path.exists():
        return None

    index = faiss.read_index(str(index_path))

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"[vector_store] Loaded existing index ({index.ntotal} vectors) from {index_dir}")
    return index, chunks
