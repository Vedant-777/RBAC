"""
Dashboard data – aggregate stats API.
Collects data from cost_tracker, latency_tracker, and vector_store
to power a monitoring dashboard.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from monitoring.cost_tracker import get_recent_usage, get_usage_summary
from monitoring.latency_tracker import get_latency_stats

logger = logging.getLogger(__name__)


def get_dashboard_data() -> dict[str, Any]:
    """
    Aggregate all monitoring data into a single payload
    suitable for a dashboard UI.
    """
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cost": get_usage_summary(),
        "latency": get_latency_stats(),
        "recent_usage": get_recent_usage(limit=20),
    }


def get_health_status() -> dict[str, Any]:
    """Quick health check data."""
    cost = get_usage_summary()
    latency = get_latency_stats()

    # Simple health heuristic
    status = "healthy"
    issues: list[str] = []

    if isinstance(latency, dict):
        for ep, stats in latency.items():
            if isinstance(stats, dict) and stats.get("p95_ms", 0) > 5000:
                status = "degraded"
                issues.append(f"High p95 latency on {ep}: {stats['p95_ms']}ms")

    return {
        "status": status,
        "issues": issues,
        "total_requests": cost.get("total_requests", 0),
        "total_cost_usd": cost.get("total_cost_usd", 0.0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
