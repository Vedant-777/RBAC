"""
Scope checker – detect out-of-scope or off-topic queries.
Uses a keyword blocklist and optional semantic similarity.
"""

from __future__ import annotations

import logging
import re

from core.config import get_settings
from core.exceptions import OutOfScopeError

logger = logging.getLogger(__name__)


def check_scope(query: str) -> bool:
    """
    Return True if the query is within scope, raise OutOfScopeError otherwise.

    Checks:
    1. Blocked keywords (from settings).
    2. Overly short or nonsensical queries.
    """
    settings = get_settings()
    query_lower = query.lower().strip()

    # ── Check blocked keywords ──────────────────────────────────────────────
    for keyword in settings.BLOCKED_KEYWORDS:
        # Use word-boundary matching to avoid false positives
        if re.search(rf"\b{re.escape(keyword)}\b", query_lower):
            logger.warning("Out-of-scope keyword detected: '%s'", keyword)
            raise OutOfScopeError(
                f"Your query appears to be about '{keyword}', which is outside "
                f"the scope of this assistant. Please ask questions related to "
                f"your organisation's documents."
            )

    # ── Check for gibberish / too short ─────────────────────────────────────
    if len(query_lower) < 3:
        raise OutOfScopeError("Query is too short. Please provide a meaningful question.")

    # ── Check for excessive special characters (potential injection) ─────────
    alpha_ratio = sum(c.isalpha() for c in query_lower) / max(len(query_lower), 1)
    if alpha_ratio < 0.3:
        logger.warning("Query has low alpha ratio (%.2f): potential injection", alpha_ratio)
        raise OutOfScopeError("Query contains too many special characters.")

    return True
