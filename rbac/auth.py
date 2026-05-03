"""
Auth – login, registration, and JWT token issue / verification.
Uses MongoDB for user persistence.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext
from pymongo.database import Database

from core.config import get_settings
from core.exceptions import AuthenticationError
from core.utils import generate_id, utc_now
from rbac.models import UserDocument, get_user_role_names

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plain-text password."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plain-text password against its hash."""
    return pwd_context.verify(plain, hashed)


# ── JWT helpers ─────────────────────────────────────────────────────────────

def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT containing *data*."""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT.  Raises AuthenticationError on failure."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError(f"Invalid token: {exc}")


# ── Login flow ──────────────────────────────────────────────────────────────

def authenticate_user(db: Database, username: str, password: str) -> dict[str, Any]:
    """Validate credentials and return the user document."""
    user_doc = db["users"].find_one({"username": username})
    if not user_doc or not verify_password(password, user_doc["hashed_password"]):
        raise AuthenticationError("Invalid username or password")
    if not user_doc.get("is_active", True):
        raise AuthenticationError("Account is deactivated")
    logger.info("User '%s' authenticated successfully", username)
    return user_doc


def register_user(
    db: Database,
    username: str,
    email: str,
    password: str,
    role_name: str = "employee"
) -> dict[str, Any]:
    """Create a new user and assign a role."""
    if db["users"].find_one({"username": username}):
        raise AuthenticationError("Username already exists")
    if db["users"].find_one({"email": email}):
        raise AuthenticationError("Email already registered")

    user = UserDocument(
        username=username,
        email=email,
        hashed_password=hash_password(password),
    )
    user_dict = user.to_mongo()
    
    # Assign role
    role = db["roles"].find_one({"name": role_name})
    if not role:
        from rbac.models import RoleDocument
        new_role = RoleDocument(name=role_name, description=f"{role_name.capitalize()} role").to_mongo()
        db["roles"].insert_one(new_role)
        role = new_role
    
    user_dict["role_ids"] = [role["_id"]]

    db["users"].insert_one(user_dict)
    logger.info("Registered new user: %s with role: %s", username, role_name)
    return user_dict


def login(db: Database, username: str, password: str) -> dict[str, Any]:
    """Authenticate and return an access token + user info."""
    user_doc = authenticate_user(db, username, password)
    role_names = get_user_role_names(user_doc, db["roles"])

    token = create_access_token(
        data={
            "sub": user_doc["_id"],
            "username": user_doc["username"],
            "roles": role_names,
        }
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_doc["_id"],
            "username": user_doc["username"],
            "roles": role_names,
        },
    }
