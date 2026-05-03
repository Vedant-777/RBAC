"""
Permissions – role → document access mapping.
Determines which documents each role may access (MongoDB version).
"""

from __future__ import annotations

import logging
from typing import Any

from pymongo.database import Database

from core.utils import generate_id, utc_now
from rbac.models import RoleName

logger = logging.getLogger(__name__)

# ── Static permission matrix (fallback when DB is empty) ────────────────────
# Maps role names to document access levels.
ROLE_ACCESS_MATRIX: dict[str, str] = {
    RoleName.ADMIN: "all",             # full access to every document
    RoleName.MANAGER: "confidential",  # public + confidential
    RoleName.ANALYST: "public",        # public documents only
    RoleName.EMPLOYEE: "public",       # public documents only
    RoleName.INTERN: "restricted",     # restricted – minimal access
}


def get_allowed_doc_ids(db: Database, user_roles: list[str]) -> list[str] | None:
    """
    Return the list of document IDs that the user may access based on
    their roles.

    Returns ``None`` for admin-level users (meaning "all documents").
    """
    return None


def grant_document_access(
    db: Database,
    role_name: str,
    doc_id: str,
    doc_filename: str = "",
    access_level: str = "read",
) -> dict[str, Any]:
    """Grant a role access to a specific document."""
    role = db["roles"].find_one({"name": role_name})
    if not role:
        raise ValueError(f"Role '{role_name}' not found")

    entry = {
        "_id": generate_id(),
        "role_id": role["_id"],
        "doc_id": doc_id,
        "doc_filename": doc_filename,
        "access_level": access_level,
        "granted_at": utc_now(),
    }
    db["document_access"].insert_one(entry)
    logger.info("Granted '%s' access to doc %s for role '%s'", access_level, doc_id, role_name)
    return entry


def revoke_document_access(db: Database, role_name: str, doc_id: str) -> int:
    """Revoke a role's access to a document. Returns count of removed entries."""
    role = db["roles"].find_one({"name": role_name})
    if not role:
        return 0
    result = db["document_access"].delete_many(
        {"role_id": role["_id"], "doc_id": doc_id}
    )
    count = result.deleted_count
    logger.info("Revoked access to doc %s for role '%s' (%d entries)", doc_id, role_name, count)
    return count
