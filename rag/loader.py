"""
Document loader — reads every .txt file from the rag_docs directory.
"""

from pathlib import Path
from typing import List, Dict


def load_documents(docs_dir: Path) -> List[Dict[str, str]]:
    """
    Load all .txt files from *docs_dir*.

    Returns
    -------
    list[dict]
        Each dict has:
        - "filename": stem of the file
        - "content" : full text content
    """
    documents: List[Dict[str, str]] = []

    if not docs_dir.exists():
        print(f"[loader] Warning: directory '{docs_dir}' does not exist.")
        return documents

    for filepath in sorted(docs_dir.glob("*.txt")):
        text = filepath.read_text(encoding="utf-8", errors="ignore").strip()
        if text:
            documents.append({
                "filename": filepath.stem,
                "content": text,
            })

    print(f"[loader] Loaded {len(documents)} document(s) from {docs_dir}")
    return documents
