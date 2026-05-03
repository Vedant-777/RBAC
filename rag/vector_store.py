"""
Vector store – FAISS index CRUD operations.
Manages creating, saving, loading, and searching a FAISS flat-L2 index
alongside a parallel metadata store (pickled list).
"""

from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from core.config import get_settings

logger = logging.getLogger(__name__)

try:
    import faiss
except ImportError:
    faiss = None  # handled at runtime


class VectorStore:
    """Thin wrapper around a FAISS index + metadata list."""

    def __init__(self, dimension: int | None = None):
        if faiss is None:
            raise ImportError("faiss-cpu is required. Install with: pip install faiss-cpu")

        settings = get_settings()
        self.dimension = dimension or settings.EMBEDDING_DIMENSION
        self.index: faiss.IndexFlatL2 = faiss.IndexFlatL2(self.dimension)
        self.metadata: list[dict[str, Any]] = []

    # ── CRUD ────────────────────────────────────────────────────────────────

    def add(self, embeddings: np.ndarray, metadata_list: list[dict[str, Any]]) -> None:
        """Add vectors and their metadata to the store."""
        if embeddings.shape[0] != len(metadata_list):
            raise ValueError("embeddings and metadata_list must have the same length")
        self.index.add(embeddings)
        self.metadata.extend(metadata_list)
        logger.info("Added %d vectors (total: %d)", embeddings.shape[0], self.index.ntotal)

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Return the *top_k* nearest neighbours.

        Each result dict contains the original metadata plus ``score``
        (L2 distance – lower is better).
        """
        if self.index.ntotal == 0:
            logger.warning("Search called on empty index")
            return []

        distances, indices = self.index.search(query_vector, min(top_k, self.index.ntotal))
        results: list[dict[str, Any]] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            entry = {**self.metadata[idx], "score": float(dist)}
            results.append(entry)
        return results

    def delete_by_doc_id(self, doc_id: str) -> int:
        """
        Remove all vectors belonging to *doc_id* and rebuild the index.
        Returns the number of vectors removed.
        """
        keep_indices = [i for i, m in enumerate(self.metadata) if m.get("doc_id") != doc_id]
        removed = len(self.metadata) - len(keep_indices)
        if removed == 0:
            return 0

        # Reconstruct vectors for kept indices
        kept_vectors = np.array(
            [self.index.reconstruct(int(i)) for i in keep_indices], dtype=np.float32
        )
        kept_metadata = [self.metadata[i] for i in keep_indices]

        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []
        if len(kept_vectors) > 0:
            self.add(kept_vectors, kept_metadata)
        logger.info("Removed %d vectors for doc_id=%s", removed, doc_id)
        return removed

    @property
    def count(self) -> int:
        return self.index.ntotal

    # ── Persistence ─────────────────────────────────────────────────────────

    def save(self, path: str | Path | None = None) -> None:
        """Persist the index + metadata to disk."""
        settings = get_settings()
        path = Path(path or settings.FAISS_INDEX_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, str(path))
        meta_path = path.with_suffix(".meta")
        with open(meta_path, "wb") as f:
            pickle.dump(self.metadata, f)
        logger.info("Saved index (%d vectors) to %s", self.index.ntotal, path)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "VectorStore":
        """Load an index + metadata from disk."""
        settings = get_settings()
        path = Path(path or settings.FAISS_INDEX_PATH)
        meta_path = path.with_suffix(".meta")

        if not path.exists():
            raise FileNotFoundError(f"Index file not found: {path}")

        store = cls.__new__(cls)
        store.index = faiss.read_index(str(path))
        store.dimension = store.index.d

        if meta_path.exists():
            with open(meta_path, "rb") as f:
                store.metadata = pickle.load(f)
        else:
            store.metadata = [{} for _ in range(store.index.ntotal)]

        logger.info("Loaded index (%d vectors) from %s", store.index.ntotal, path)
        return store
