"""
Shared helpers used across the application.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    """Return the current UTC timestamp (timezone-aware)."""
    return datetime.now(timezone.utc)


def generate_id() -> str:
    """Return a new UUID4 string."""
    return str(uuid.uuid4())


def file_hash(path: Path | str, algorithm: str = "sha256") -> str:
    """Compute a hex-digest hash of a file (default SHA-256)."""
    h = hashlib.new(algorithm)
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """
    Split *text* into overlapping chunks of approximately *chunk_size* chars.
    Tries to break on sentence boundaries when possible.
    """
    if not text:
        return []

    sentences = text.replace("\n", " ").split(". ")
    chunks: list[str] = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        candidate = f"{current_chunk}. {sentence}" if current_chunk else sentence

        if len(candidate) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # keep overlap from the tail of the previous chunk
            overlap_text = current_chunk[-overlap:] if overlap else ""
            current_chunk = f"{overlap_text} {sentence}".strip()
        else:
            current_chunk = candidate

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def timer() -> dict[str, Any]:
    """
    Simple context-manager-like timer.

    Usage::

        t = timer()
        t["start"]()
        # … work …
        elapsed = t["stop"]()
    """
    state: dict[str, float] = {}

    def start() -> None:
        state["t0"] = time.perf_counter()

    def stop() -> float:
        state["elapsed"] = time.perf_counter() - state["t0"]
        return state["elapsed"]

    return {"start": start, "stop": stop, "state": state}


def truncate(text: str, max_length: int = 200) -> str:
    """Truncate text to *max_length* chars, adding '…' if trimmed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"
