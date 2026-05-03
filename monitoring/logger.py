"""
Logger – structured log events for the application.
Configures JSON-formatted logging with contextual fields.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from core.config import get_settings


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach extra fields (e.g., user_id, request_id)
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])

        return json.dumps(log_entry)


def setup_logging() -> None:
    """
    Configure root logger with JSON formatter.
    Call once at application startup.
    """
    settings = get_settings()
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers
    root.handlers.clear()

    # Console handler with JSON output
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(JSONFormatter())
    root.addHandler(console)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    root.info("Logging initialised at level=%s", settings.LOG_LEVEL)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger (convenience wrapper)."""
    return logging.getLogger(name)


def log_event(logger_name: str, level: str, message: str, **data: Any) -> None:
    """
    Emit a structured log event with arbitrary key-value data.

    Usage::

        log_event("rag", "info", "Query processed", user_id="abc", latency_ms=42)
    """
    _logger = logging.getLogger(logger_name)
    record = _logger.makeRecord(
        name=logger_name,
        level=getattr(logging, level.upper(), logging.INFO),
        fn="",
        lno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    record.extra_data = data  # type: ignore[attr-defined]
    _logger.handle(record)
