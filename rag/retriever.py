"""
Retriever – similarity search with optional RBAC filtering.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from rag.embeddings import embed_query
from rag.vector_store import VectorStore
from core.config import get_settings

logger = logging.getLogger(__name__)


def retrieve(
    query: str,
    store: VectorStore,
    top_k: int | None = None,
    allowed_doc_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Embed *query*, search the vector store, and return the top results.

    Parameters
    ----------
    query : str
        The user's natural-language question.
    store : VectorStore
        An initialised (or loaded) VectorStore instance.
    top_k : int, optional
        Number of results to return (defaults to settings.TOP_K).
    allowed_doc_ids : list[str], optional
        If provided, only chunks whose ``doc_id`` is in this list will be
        returned.  This is the RBAC enforcement point.

    Returns
    -------
    list[dict]
        Each dict contains ``text``, ``doc_id``, ``filename``, ``score``, etc.
    """
    settings = get_settings()
    top_k = top_k or settings.TOP_K

    # Embed the query
    query_vector = embed_query(query)

    # When RBAC filtering is active, fetch more candidates and post-filter.
    fetch_k = top_k * 3 if allowed_doc_ids else top_k
    raw_results = store.search(query_vector, top_k=fetch_k)

    # Post-filter by allowed doc IDs (RBAC)
    if allowed_doc_ids is not None:
        allowed_set = set(allowed_doc_ids)
        raw_results = [r for r in raw_results if r.get("doc_id") in allowed_set]
        logger.info(
            "RBAC filter: %d results kept (allowed docs: %d)",
            len(raw_results),
            len(allowed_set),
        )

    results = raw_results[:top_k]
    logger.info("Retrieved %d chunks for query: %s", len(results), query[:80])
    return results
