"""
Pipeline – orchestrate the full RAG flow.
Ties together guardrails → retrieval → generation → output filtering.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from core.config import get_settings
from guardrails.guardrail_chain import run_input_guardrails, run_output_guardrails
from monitoring.latency_tracker import track_latency
from rag.generator import generate
from rag.retriever import retrieve
from rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Module-level store (loaded once, reused across requests)
_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Return the singleton VectorStore, loading from disk if needed."""
    global _store
    if _store is None:
        try:
            _store = VectorStore.load()
            logger.info("Loaded existing FAISS index with %d vectors", _store.count)
        except FileNotFoundError:
            logger.warning("No persisted index found – creating empty store")
            _store = VectorStore()
    return _store


def rebuild_vector_store() -> VectorStore:
    """
    Rebuild the FAISS index from all documents in MongoDB.
    Called after document upload/delete to keep the index in sync.
    """
    global _store
    from rag.document_loader import load_all_documents
    from rag.embeddings import embed_texts
    from core.utils import chunk_text

    settings = get_settings()

    logger.info("Rebuilding FAISS vector store from MongoDB...")

    docs = load_all_documents()
    if not docs:
        logger.warning("No documents found in MongoDB – creating empty store")
        _store = VectorStore()
        _store.save()
        return _store

    # Chunk all documents
    all_chunks: list[str] = []
    all_metadata: list[dict] = []

    for doc in docs:
        chunks = chunk_text(
            doc["text"],
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP,
        )
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadata.append({
                "doc_id": doc["id"],
                "filename": doc["filename"],
                "chunk_index": i,
                "text": chunk,
            })

    logger.info("Created %d chunk(s) from %d document(s)", len(all_chunks), len(docs))

    # Generate embeddings
    logger.info("Generating embeddings...")
    embeddings = embed_texts(all_chunks)
    logger.info("Embeddings shape: %s", embeddings.shape)

    # Create and save new vector store
    _store = VectorStore(dimension=embeddings.shape[1])
    _store.add(embeddings, all_metadata)
    _store.save()

    logger.info("Rebuild complete! Index saved with %d vectors.", _store.count)
    return _store


def ingest_single_document(doc_id: str, filename: str, content: bytes) -> int:
    """
    Ingest a single document into the FAISS index without full rebuild.
    Returns the number of chunks added.
    """
    global _store
    from rag.document_loader import LOADERS
    from rag.embeddings import embed_texts
    from core.utils import chunk_text
    from pathlib import Path

    settings = get_settings()
    store = get_vector_store()

    # Remove old vectors for this doc_id if any
    removed = store.delete_by_doc_id(doc_id)
    if removed:
        logger.info("Removed %d old vectors for doc_id=%s", removed, doc_id)

    # Extract text from the document
    ext = Path(filename).suffix.lower()
    loader = LOADERS.get(ext)
    if loader is None:
        logger.warning("Unsupported file type: %s for %s", ext, filename)
        return 0

    try:
        text = loader(content)
    except Exception as exc:
        logger.error("Failed to extract text from %s: %s", filename, exc)
        return 0

    if not text.strip():
        logger.warning("No text extracted from %s", filename)
        return 0

    # Chunk the text
    chunks = chunk_text(text, chunk_size=settings.CHUNK_SIZE, overlap=settings.CHUNK_OVERLAP)
    if not chunks:
        return 0

    metadata_list = []
    for i, chunk in enumerate(chunks):
        metadata_list.append({
            "doc_id": doc_id,
            "filename": filename,
            "chunk_index": i,
            "text": chunk,
        })

    # Generate embeddings and add to store
    embeddings = embed_texts(chunks)
    store.add(embeddings, metadata_list)
    store.save()

    logger.info("Ingested %s: %d chunks added to index (total: %d)", filename, len(chunks), store.count)
    return len(chunks)


def ask(
    query: str,
    user_role: str = "admin",
    allowed_doc_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    End-to-end RAG pipeline.

    1. Run input guardrails (PII, scope, length).
    2. Retrieve relevant chunks (RBAC-filtered).
    3. Generate an answer via the LLM.
    4. Run output guardrails (sanitisation).

    Parameters
    ----------
    query : str
        The user's question.
    user_role : str
        Role name (used for logging / guardrail context).
    allowed_doc_ids : list[str] | None
        If supplied, restricts retrieval to these document IDs.

    Returns
    -------
    dict
        Keys: ``answer``, ``sources``, ``model``, ``usage``, ``latency_ms``.
    """
    start = time.perf_counter()

    # 1 ── Input guardrails
    run_input_guardrails(query)

    # 2 ── Retrieval
    store = get_vector_store()
    chunks = retrieve(query, store, allowed_doc_ids=allowed_doc_ids)

    if not chunks:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "answer": "Access Blocked / Information Not Found. I couldn't find any relevant documents to answer your question. Note: Your current role permissions may restrict you from accessing confidential documents containing this information.",
            "sources": [],
            "model": get_settings().LLM_MODEL,
            "usage": {},
            "latency_ms": elapsed_ms,
        }

    # 3 ── Generation
    result = generate(chunks, query)

    # 4 ── Output guardrails
    answer = run_output_guardrails(result["answer"])

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    # Track latency
    track_latency(endpoint="rag.ask", latency_ms=elapsed_ms)

    sources = list({c.get("filename", "unknown") for c in chunks})

    logger.info("Pipeline complete in %.1f ms (role=%s)", elapsed_ms, user_role)
    return {
        "answer": answer,
        "sources": sources,
        "model": result["model"],
        "usage": result["usage"],
        "latency_ms": elapsed_ms,
    }
