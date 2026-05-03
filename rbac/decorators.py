"""
Decorators – @require_role helper for route-level authorisation.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable

from fastapi import HTTPException, Request

from core.exceptions import AuthorisationError

logger = logging.getLogger(__name__)


def require_role(*allowed_roles: str) -> Callable:
    """
    FastAPI dependency / decorator that checks the current user has at
    least one of the *allowed_roles*.

    Usage::

        @app.get("/admin-only")
        @require_role("admin")
        async def admin_panel(request: Request):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # FastAPI injects Request via dependency injection
            request: Request | None = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                raise HTTPException(status_code=500, detail="Request object not found")

            user = getattr(request.state, "user", None)
            if user is None:
                raise HTTPException(status_code=401, detail="Not authenticated")

            user_roles: list[str] = user.get("roles", [])
            if not any(role in allowed_roles for role in user_roles):
                logger.warning(
                    "Access denied: user '%s' (roles=%s) tried to access route requiring %s",
                    user.get("username"),
                    user_roles,
                    allowed_roles,
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"Requires one of roles: {', '.join(allowed_roles)}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def get_current_user(request: Request) -> dict[str, Any]:
    """
    FastAPI dependency – extracts the current user from request.state.
    Must be used after AuthMiddleware.
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
