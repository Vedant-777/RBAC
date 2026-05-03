"""
Database – MongoDB setup with PyMongo.
Provides a singleton MongoClient, database handle, and collection accessors.
"""

from __future__ import annotations

import logging
from typing import Any

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

from core.config import get_settings

logger = logging.getLogger(__name__)

_client: MongoClient | None = None
_db: Database | None = None


def get_client() -> MongoClient:
    """Return the singleton MongoClient (lazy-initialised)."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = MongoClient(settings.MONGODB_URI)
        logger.info("MongoDB client connected to cluster")
    return _client


def get_database() -> Database:
    """Return the application database handle."""
    global _db
    if _db is None:
        settings = get_settings()
        _db = get_client()[settings.MONGODB_DB_NAME]
        logger.info("Using database: %s", settings.MONGODB_DB_NAME)
    return _db


def get_db() -> Database:
    """FastAPI dependency – returns the MongoDB database handle."""
    return get_database()


# ── Collection accessors ────────────────────────────────────────────────────

def users_collection() -> Collection:
    return get_database()["users"]


def roles_collection() -> Collection:
    return get_database()["roles"]


def permissions_collection() -> Collection:
    return get_database()["permissions"]


def document_access_collection() -> Collection:
    return get_database()["document_access"]


# ── Index creation (idempotent) ─────────────────────────────────────────────

def init_db() -> None:
    """
    Create MongoDB indexes for performance and uniqueness constraints.
    Safe to call multiple times (indexes are created only if missing).
    """
    db = get_database()

    # Users
    db["users"].create_index("username", unique=True)
    db["users"].create_index("email", unique=True)

    # Roles
    db["roles"].create_index("name", unique=True)

    # Permissions
    db["permissions"].create_index("name", unique=True)

    # Document access
    db["document_access"].create_index([("role_id", 1), ("doc_id", 1)])
    db["document_access"].create_index("doc_id")

    logger.info("MongoDB indexes ensured")


def close_db() -> None:
    """Close the MongoDB client connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB client closed")
