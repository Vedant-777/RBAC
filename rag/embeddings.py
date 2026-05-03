"""
Embeddings – generate vector embeddings using Google Gemini.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from core.config import get_settings

logger = logging.getLogger(__name__)

_client: Any = None


def _get_gemini_client():
    """Lazy-initialise and return the Google GenAI client."""
    global _client
    if _client is None:
        try:
            from google import genai
        except ImportError as exc:
            raise ImportError(
                "google-genai package is required. Install with: pip install google-genai"
            ) from exc
        settings = get_settings()
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> np.ndarray:
    """
    Generate embeddings for a list of text strings using Google Gemini.

    Returns an ``np.ndarray`` of shape ``(len(texts), dimension)``.
    """
    settings = get_settings()
    client = _get_gemini_client()

    logger.info("Generating embeddings for %d text(s) with model=%s", len(texts), settings.EMBEDDING_MODEL)

    from google.genai import types

    all_embeddings: list[list[float]] = []

    # Google Gemini embed_content supports batching natively
    batch_size = 100  # conservative batch size
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.models.embed_content(
            model=settings.EMBEDDING_MODEL,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.EMBEDDING_DIMENSION,
            ),
        )
        for emb in response.embeddings:
            all_embeddings.append(emb.values)

    return np.array(all_embeddings, dtype=np.float32)


def embed_query(query: str) -> np.ndarray:
    """Embed a single query string.  Returns shape ``(1, dimension)``."""
    return embed_texts([query], task_type="RETRIEVAL_QUERY")
