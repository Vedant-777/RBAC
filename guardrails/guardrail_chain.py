"""
Guardrail chain – run all guardrail checks in sequence.
Single entry point for input and output guardrails.
"""

from __future__ import annotations

import logging
from typing import Any

from guardrails.input_filter import validate_input
from guardrails.output_filter import sanitise_output

logger = logging.getLogger(__name__)


def run_input_guardrails(query: str) -> str:
    """
    Execute all input guardrails and return the sanitised query.
    Raises GuardrailViolation (or subclass) if any check fails.
    """
    logger.debug("Running input guardrails on query (%d chars)", len(query))
    sanitised = validate_input(query)
    logger.debug("Input guardrails passed")
    return sanitised


def run_output_guardrails(text: str) -> str:
    """
    Execute all output guardrails and return the cleaned text.
    """
    logger.debug("Running output guardrails on response (%d chars)", len(text))
    cleaned = sanitise_output(text)
    logger.debug("Output guardrails passed")
    return cleaned
