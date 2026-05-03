"""
RBAC models – User, Role, Permission (MongoDB document schemas).
Uses Pydantic for validation and PyMongo for persistence.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from core.utils import generate_id, utc_now


# ── Enums ───────────────────────────────────────────────────────────────────

class RoleName(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    EMPLOYEE = "employee"
    INTERN = "intern"


class PermissionType(str, enum.Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"


# ── Document schemas ────────────────────────────────────────────────────────

class UserDocument(BaseModel):
    """Schema for a User document in MongoDB."""
    id: str = Field(default_factory=generate_id, alias="_id")
    username: str
    email: str
    hashed_password: str
    is_active: bool = True
    role_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    model_config = {"populate_by_name": True}

    def to_mongo(self) -> dict[str, Any]:
        """Convert to a MongoDB-compatible dict."""
        data = self.model_dump(by_alias=True)
        return data

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "UserDocument":
        """Create from a MongoDB document."""
        if doc is None:
            return None
        return cls(**doc)


class RoleDocument(BaseModel):
    """Schema for a Role document in MongoDB."""
    id: str = Field(default_factory=generate_id, alias="_id")
    name: str
    description: str = ""
    doc_access_level: str = "public"  # "public" | "confidential" | "all"
    permission_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {"populate_by_name": True}

    def to_mongo(self) -> dict[str, Any]:
        data = self.model_dump(by_alias=True)
        return data

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "RoleDocument":
        if doc is None:
            return None
        return cls(**doc)


class PermissionDocument(BaseModel):
    """Schema for a Permission document in MongoDB."""
    id: str = Field(default_factory=generate_id, alias="_id")
    name: str
    resource: str  # e.g. "documents", "users"
    action: str    # "read" | "write" | "delete"
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {"populate_by_name": True}

    def to_mongo(self) -> dict[str, Any]:
        data = self.model_dump(by_alias=True)
        return data

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "PermissionDocument":
        if doc is None:
            return None
        return cls(**doc)


class DocumentAccessEntry(BaseModel):
    """Schema for a DocumentAccess entry in MongoDB."""
    id: str = Field(default_factory=generate_id, alias="_id")
    role_id: str
    doc_id: str
    doc_filename: str = ""
    access_level: str = "read"  # "read" | "write"
    granted_at: datetime = Field(default_factory=utc_now)

    model_config = {"populate_by_name": True}

    def to_mongo(self) -> dict[str, Any]:
        data = self.model_dump(by_alias=True)
        return data

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "DocumentAccessEntry":
        if doc is None:
            return None
        return cls(**doc)


# ── Helper functions for User role resolution ──────────────────────────────

def get_user_role_names(user_doc: dict[str, Any], roles_collection) -> list[str]:
    """
    Given a user document and the roles collection, return a list of
    role name strings for that user.
    """
    role_ids = user_doc.get("role_ids", [])
    if not role_ids:
        return []
    roles = roles_collection.find({"_id": {"$in": role_ids}})
    return [r["name"] for r in roles]


def user_has_role(user_doc: dict[str, Any], role_name: str, roles_collection) -> bool:
    """Check if a user has a specific role."""
    return role_name in get_user_role_names(user_doc, roles_collection)
