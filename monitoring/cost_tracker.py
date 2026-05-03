"""
Cost tracker – token usage and estimated cost tracking.
Stores usage data in memory and provides aggregation helpers.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.config import get_settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()


@dataclass
class UsageRecord:
    """A single LLM usage event."""
    timestamp: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


# In-memory store (replace with DB in production)
_usage_history: list[UsageRecord] = []


def record_usage(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> UsageRecord:
    """Record a single LLM usage event and compute estimated cost."""
    settings = get_settings()

    cost = (
        (prompt_tokens / 1000) * settings.COST_PER_1K_INPUT_TOKENS
        + (completion_tokens / 1000) * settings.COST_PER_1K_OUTPUT_TOKENS
    )

    record = UsageRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        estimated_cost_usd=round(cost, 6),
    )

    with _lock:
        _usage_history.append(record)

    logger.info(
        "Usage recorded: %d tokens (prompt=%d, completion=%d), cost=$%.6f",
        record.total_tokens,
        prompt_tokens,
        completion_tokens,
        cost,
    )
    return record


def get_usage_summary() -> dict[str, Any]:
    """Return aggregate usage statistics."""
    with _lock:
        records = list(_usage_history)

    if not records:
        return {
            "total_requests": 0,
            "total_tokens": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cost_usd": 0.0,
        }

    return {
        "total_requests": len(records),
        "total_tokens": sum(r.total_tokens for r in records),
        "total_prompt_tokens": sum(r.prompt_tokens for r in records),
        "total_completion_tokens": sum(r.completion_tokens for r in records),
        "total_cost_usd": round(sum(r.estimated_cost_usd for r in records), 6),
        "avg_tokens_per_request": round(
            sum(r.total_tokens for r in records) / len(records), 1
        ),
    }


def get_recent_usage(limit: int = 50) -> list[dict[str, Any]]:
    """Return the most recent *limit* usage records as dicts."""
    with _lock:
        recent = list(reversed(_usage_history[-limit:]))
    return [
        {
            "timestamp": r.timestamp,
            "model": r.model,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "total_tokens": r.total_tokens,
            "estimated_cost_usd": r.estimated_cost_usd,
        }
        for r in recent
    ]


def reset_usage() -> None:
    """Clear all usage history (for testing)."""
    with _lock:
        _usage_history.clear()
