"""
RAGAS eval – RAG accuracy evaluation.
Provides helpers to compute retrieval and generation quality metrics.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def evaluate_retrieval(
    query: str,
    retrieved_chunks: list[dict[str, Any]],
    ground_truth_doc_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Evaluate retrieval quality.

    Metrics:
    - **context_relevance**: ratio of retrieved chunks that match ground-truth docs.
    - **retrieval_count**: number of chunks retrieved.
    - **hit_rate**: 1.0 if any ground-truth doc is in the results, else 0.0.
    """
    retrieval_count = len(retrieved_chunks)

    if ground_truth_doc_ids is None:
        return {
            "retrieval_count": retrieval_count,
            "context_relevance": None,
            "hit_rate": None,
            "note": "No ground truth provided – unable to compute precision metrics.",
        }

    gt_set = set(ground_truth_doc_ids)
    hits = [c for c in retrieved_chunks if c.get("doc_id") in gt_set]

    context_relevance = len(hits) / retrieval_count if retrieval_count > 0 else 0.0
    hit_rate = 1.0 if hits else 0.0

    result = {
        "retrieval_count": retrieval_count,
        "context_relevance": round(context_relevance, 4),
        "hit_rate": hit_rate,
        "relevant_chunks": len(hits),
    }
    logger.info("Retrieval eval: %s", result)
    return result


def evaluate_answer(
    query: str,
    answer: str,
    retrieved_chunks: list[dict[str, Any]],
    ground_truth_answer: str | None = None,
) -> dict[str, Any]:
    """
    Evaluate answer quality (simplified – no external model call).

    Metrics:
    - **answer_length**: character count of the answer.
    - **faithfulness_proxy**: rough check if the answer uses words from context.
    - **answer_relevance**: rough check if the answer relates to the query.
    """
    # Faithfulness proxy: fraction of answer words found in context
    context_text = " ".join(c.get("text", "") for c in retrieved_chunks).lower()
    answer_words = set(answer.lower().split())
    context_words = set(context_text.split())
    overlap = answer_words & context_words
    faithfulness = len(overlap) / max(len(answer_words), 1)

    # Answer relevance proxy: fraction of query words found in answer
    query_words = set(query.lower().split())
    query_overlap = query_words & answer_words
    relevance = len(query_overlap) / max(len(query_words), 1)

    result = {
        "answer_length": len(answer),
        "faithfulness_proxy": round(faithfulness, 4),
        "answer_relevance_proxy": round(relevance, 4),
    }

    if ground_truth_answer:
        gt_words = set(ground_truth_answer.lower().split())
        gt_overlap = gt_words & answer_words
        result["ground_truth_overlap"] = round(
            len(gt_overlap) / max(len(gt_words), 1), 4
        )

    logger.info("Answer eval: %s", result)
    return result


def full_evaluation(
    query: str,
    answer: str,
    retrieved_chunks: list[dict[str, Any]],
    ground_truth_doc_ids: list[str] | None = None,
    ground_truth_answer: str | None = None,
) -> dict[str, Any]:
    """Run both retrieval and answer evaluations."""
    return {
        "retrieval": evaluate_retrieval(query, retrieved_chunks, ground_truth_doc_ids),
        "answer": evaluate_answer(query, answer, retrieved_chunks, ground_truth_answer),
    }
