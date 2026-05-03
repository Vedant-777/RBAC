"""
Dependencies – shared dependency injection for FastAPI routes.
Provides MongoDB database handle and current-user extraction.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request
from pymongo.database import Database

from core.database import get_db


def get_current_user_payload(request: Request) -> dict[str, Any]:
    """Extract the current user's JWT payload from request state."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def get_current_user(
    payload: dict[str, Any] = Depends(get_current_user_payload),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Resolve the full User document from MongoDB."""
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user_doc = db["users"].find_one({"_id": user_id})
    if user_doc is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not user_doc.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account deactivated")
    return user_doc


def require_roles(*roles: str):
    """FastAPI dependency factory that enforces role requirements."""
    def checker(payload: dict[str, Any] = Depends(get_current_user_payload)):
        user_roles = payload.get("roles", [])
        if not any(r in roles for r in user_roles):
            raise HTTPException(status_code=403, detail=f"Requires one of: {', '.join(roles)}")
        return payload
    return checker
