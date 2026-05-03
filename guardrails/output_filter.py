"""
Output filter – post-LLM sanitisation.
Cleans the LLM response before returning to the user.
"""

from __future__ import annotations

import logging
import re

from guardrails.pii_detector import redact_pii

logger = logging.getLogger(__name__)

# Patterns to strip from LLM output
_INTERNAL_PATTERNS: list[re.Pattern] = [
    re.compile(r"\[Source:.*?\]", re.IGNORECASE),   # remove source annotations
    re.compile(r"<\|.*?\|>"),                         # strip special tokens
    re.compile(r"```\s*$"),                            # trailing code fences
]

# Phrases the LLM should never expose
_FORBIDDEN_PHRASES = [
    "as an ai language model",
    "i cannot provide medical advice",
    "i'm just an ai",
    "openai",
    "chatgpt",
]


def sanitise_output(text: str) -> str:
    """
    Clean and sanitise LLM output.

    Steps:
    1. Redact any PII that leaked through.
    2. Remove internal/source annotations.
    3. Strip forbidden phrases.
    4. Trim whitespace.
    """
    if not text:
        return text

    # 1 ── PII redaction
    text = redact_pii(text)

    # 2 ── Strip internal patterns
    for pattern in _INTERNAL_PATTERNS:
        text = pattern.sub("", text)

    # 3 ── Replace forbidden phrases
    text_lower = text.lower()
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in text_lower:
            logger.warning("Stripped forbidden phrase from output: '%s'", phrase)
            # Case-insensitive replacement
            text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)

    # 4 ── Whitespace cleanup
    text = re.sub(r"\n{3,}", "\n\n", text)  # max 2 consecutive newlines
    text = text.strip()

    return text
