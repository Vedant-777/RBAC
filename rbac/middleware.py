"""
Middleware – request auth check for FastAPI.
Extracts and validates the JWT from the Authorization header and
attaches user info to the request state.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from core.exceptions import AuthenticationError
from rbac.auth import decode_access_token

logger = logging.getLogger(__name__)

# Paths that do NOT require authentication
PUBLIC_PATHS = {
    "/",
    "/chat",
    "/dashboard",
    "/documents",
    "/policies",
    "/compliance",
    "/audit-logs",
    "/team-access",
    "/login_abstract.png",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/monitoring/health",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces JWT authentication on protected routes.
    Attaches ``request.state.user`` with decoded token payload.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip auth for public paths and OPTIONS (CORS preflight)
        if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_access_token(token)
        except AuthenticationError as exc:
            logger.warning("Auth failed: %s", exc.message)
            return JSONResponse(status_code=401, content={"detail": exc.message})

        # Attach user info to the request for downstream use
        request.state.user = payload
        return await call_next(request)
