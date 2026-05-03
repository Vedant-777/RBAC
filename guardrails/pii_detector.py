"""
PII Detector – regex-based detection of phone numbers, emails,
government IDs, and other personally identifiable information.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PIIMatch:
    """Represents a detected PII instance."""
    pii_type: str
    value: str
    start: int
    end: int


# ── PII patterns ────────────────────────────────────────────────────────────

PII_PATTERNS: dict[str, re.Pattern] = {
    "phone_number": re.compile(
        r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    ),
    "email": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    ),
    "government_id": re.compile(
        r"\b\d{12}\b"  # 12-digit government ID (e.g., Aadhaar)
    ),
    "ssn": re.compile(
        r"\b\d{3}-\d{2}-\d{4}\b"  # US Social Security Number
    ),
    "credit_card": re.compile(
        r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
    ),
    "ip_address": re.compile(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    ),
}


def detect_pii(text: str) -> list[PIIMatch]:
    """
    Scan *text* for PII patterns and return all matches.
    """
    matches: list[PIIMatch] = []
    for pii_type, pattern in PII_PATTERNS.items():
        for m in pattern.finditer(text):
            matches.append(
                PIIMatch(
                    pii_type=pii_type,
                    value=m.group(),
                    start=m.start(),
                    end=m.end(),
                )
            )
    if matches:
        logger.warning("Detected %d PII instance(s): %s", len(matches), [m.pii_type for m in matches])
    return matches


def contains_pii(text: str) -> bool:
    """Return True if any PII is detected in *text*."""
    return len(detect_pii(text)) > 0


def redact_pii(text: str) -> str:
    """Replace all detected PII in *text* with ``[REDACTED]``."""
    matches = detect_pii(text)
    if not matches:
        return text

    # Process from end to start so indices stay valid
    result = text
    for match in sorted(matches, key=lambda m: m.start, reverse=True):
        result = result[: match.start] + f"[REDACTED-{match.pii_type.upper()}]" + result[match.end :]
    return result
