"""
Recursive text chunker — splits documents into overlapping chunks.
"""

from typing import List, Dict


def _recursive_split(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Recursively split *text* by paragraph → sentence → character boundaries.

    Parameters
    ----------
    chunk_size : int
        Maximum characters per chunk.
    overlap : int
        Number of overlapping characters between consecutive chunks.
    """
    # Try splitting by decreasing granularity
    separators = ["\n\n", "\n", ". ", " "]

    for sep in separators:
        parts = text.split(sep)
        if len(parts) > 1:
            break
    else:
        # Fallback: hard character split
        parts = [text]

    chunks: List[str] = []
    current = ""

    for part in parts:
        candidate = (current + sep + part).strip() if current else part.strip()

        if len(candidate) > chunk_size and current:
            chunks.append(current.strip())
            # Overlap: keep tail of current chunk
            current = current[-overlap:] + sep + part if overlap else part
        else:
            current = candidate

    if current.strip():
        chunks.append(current.strip())

    # If any chunk is still too large, split it further
    final: List[str] = []
    for chunk in chunks:
        if len(chunk) > chunk_size:
            final.extend(_hard_split(chunk, chunk_size, overlap))
        else:
            final.append(chunk)

    return final


def _hard_split(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Character-level sliding-window split (last resort)."""
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return [c for c in chunks if c]


def chunk_documents(
    documents: List[Dict[str, str]],
    chunk_size: int = 400,
    overlap: int = 50,
) -> List[Dict[str, str]]:
    """
    Chunk a list of loaded documents.

    Returns
    -------
    list[dict]
        Each dict has:
        - "text"   : chunk text
        - "source" : originating filename
    """
    all_chunks: List[Dict[str, str]] = []

    for doc in documents:
        parts = _recursive_split(doc["content"], chunk_size, overlap)
        for part in parts:
            all_chunks.append({
                "text": part,
                "source": doc["filename"],
            })

    print(f"[chunker] Created {len(all_chunks)} chunk(s) from {len(documents)} document(s)")
    return all_chunks
