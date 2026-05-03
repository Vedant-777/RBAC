"""
Input filter – pre-LLM validation.
Runs all checks on user input before it reaches the RAG pipeline.
"""

from __future__ import annotations

import logging

from core.config import get_settings
from core.exceptions import GuardrailViolation, PIIDetectedError
from guardrails.pii_detector import contains_pii, detect_pii
from guardrails.scope_checker import check_scope

logger = logging.getLogger(__name__)


def validate_input(query: str) -> str:
    """
    Validate and sanitise user input.

    Checks performed:
    1. Length limit.
    2. PII detection (block if found).
    3. Scope check (block off-topic queries).
    4. Basic sanitisation (strip, normalise whitespace).

    Returns the sanitised query string.
    Raises GuardrailViolation subclasses on failure.
    """
    settings = get_settings()

    # ── 1. Length check ─────────────────────────────────────────────────────
    if len(query) > settings.MAX_INPUT_LENGTH:
        raise GuardrailViolation(
            f"Query exceeds maximum length of {settings.MAX_INPUT_LENGTH} characters."
        )

    if not query.strip():
        raise GuardrailViolation("Query cannot be empty.")

    # ── 2. PII detection ───────────────────────────────────────────────────
    pii_matches = detect_pii(query)
    if pii_matches:
        types_found = list({m.pii_type for m in pii_matches})
        logger.warning("PII blocked in input: %s", types_found)
        raise PIIDetectedError(
            f"Your query contains sensitive information ({', '.join(types_found)}). "
            f"Please remove personal data before submitting."
        )

    # ── 3. Scope check ─────────────────────────────────────────────────────
    check_scope(query)

    # ── 4. Sanitise ────────────────────────────────────────────────────────
    sanitised = " ".join(query.split())  # collapse whitespace
    logger.info("Input validated (%d chars)", len(sanitised))
    return sanitised
