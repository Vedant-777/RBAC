"""
Latency tracker – response time monitoring.
Tracks endpoint latency and provides percentile statistics.
"""

from __future__ import annotations

import logging
import statistics
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_lock = threading.Lock()


@dataclass
class LatencyRecord:
    timestamp: str
    endpoint: str
    latency_ms: float


# In-memory store keyed by endpoint
_latency_history: dict[str, list[LatencyRecord]] = defaultdict(list)


def track_latency(endpoint: str, latency_ms: float) -> None:
    """Record a latency measurement for an endpoint."""
    record = LatencyRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        endpoint=endpoint,
        latency_ms=round(latency_ms, 2),
    )
    with _lock:
        _latency_history[endpoint].append(record)
    logger.debug("Latency recorded: %s = %.2f ms", endpoint, latency_ms)


def get_latency_stats(endpoint: str | None = None) -> dict[str, Any]:
    """
    Return latency statistics.
    If *endpoint* is None, return stats for all endpoints.
    """
    with _lock:
        if endpoint:
            records = list(_latency_history.get(endpoint, []))
            return _compute_stats(endpoint, records)
        else:
            result = {}
            for ep, records in _latency_history.items():
                result[ep] = _compute_stats(ep, list(records))
            return result


def _compute_stats(endpoint: str, records: list[LatencyRecord]) -> dict[str, Any]:
    """Compute latency percentiles for a list of records."""
    if not records:
        return {
            "endpoint": endpoint,
            "count": 0,
            "avg_ms": 0,
            "p50_ms": 0,
            "p95_ms": 0,
            "p99_ms": 0,
            "min_ms": 0,
            "max_ms": 0,
        }

    values = [r.latency_ms for r in records]
    sorted_vals = sorted(values)

    return {
        "endpoint": endpoint,
        "count": len(values),
        "avg_ms": round(statistics.mean(values), 2),
        "p50_ms": round(sorted_vals[len(sorted_vals) // 2], 2),
        "p95_ms": round(sorted_vals[int(len(sorted_vals) * 0.95)], 2) if len(sorted_vals) > 1 else sorted_vals[0],
        "p99_ms": round(sorted_vals[int(len(sorted_vals) * 0.99)], 2) if len(sorted_vals) > 1 else sorted_vals[0],
        "min_ms": round(min(values), 2),
        "max_ms": round(max(values), 2),
    }


def get_recent_latency(endpoint: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return recent latency records for an endpoint."""
    with _lock:
        records = list(reversed(_latency_history.get(endpoint, [])[-limit:]))
    return [
        {
            "timestamp": r.timestamp,
            "endpoint": r.endpoint,
            "latency_ms": r.latency_ms,
        }
        for r in records
    ]


def reset_latency() -> None:
    """Clear all latency history (for testing)."""
    with _lock:
        _latency_history.clear()
