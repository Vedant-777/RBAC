"""
Configuration – env vars & settings.
Reads from .env via pydantic-settings and exposes a cached `get_settings()`.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


# ── project paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # project root
DATA_DIR = BASE_DIR / "data"
RAW_DOCS_DIR = DATA_DIR / "raw_docs"
VECTOR_INDEX_DIR = DATA_DIR / "vector_index"
PROCESSED_DIR = DATA_DIR / "processed"


class Settings(BaseSettings):
    """Central application settings pulled from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── application ─────────────────────────────────────────────────────────
    APP_NAME: str = "IntelliFusion"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── MongoDB ─────────────────────────────────────────────────────────────
    MONGODB_URI: str = ""
    MONGODB_DB_NAME: str = "intellifusion"

    # ── JWT / auth ──────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60

    # ── Google Gemini / Embeddings ────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIMENSION: int = 768

    # ── LLM Provider ────────────────────────────────────────────────────────
    LLM_PROVIDER: str = "gemini"  # "openai" or "gemini"
    LLM_MODEL: str = "gemini-2.5-flash"

    # ── OpenAI ──────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""

    # ── Groq ────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""

    # ── FAISS ───────────────────────────────────────────────────────────────
    FAISS_INDEX_PATH: str = str(VECTOR_INDEX_DIR / "index.faiss")
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 100
    TOP_K: int = 5

    # ── guardrails ──────────────────────────────────────────────────────────
    MAX_INPUT_LENGTH: int = 2000
    BLOCKED_KEYWORDS: list[str] = [
        "sports", "politics", "movies", "celebrities", "gossip",
    ]

    # ── monitoring / cost ───────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    COST_PER_1K_INPUT_TOKENS: float = 0.00015
    COST_PER_1K_OUTPUT_TOKENS: float = 0.0006


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
