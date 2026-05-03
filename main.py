"""
Main – FastAPI application entrypoint.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from __init__ import __app_name__, __version__
from api.routes import admin_router, auth_router, monitoring_router, rag_router
from core.config import get_settings
from core.database import close_db, init_db
from core.exceptions import AppException
from monitoring.logger import setup_logging
from rbac.middleware import AuthMiddleware

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=__app_name__,
        version=__version__,
        description="Enterprise RAG with RBAC, Guardrails & Monitoring (MongoDB)",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(AuthMiddleware)

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(auth_router)
    app.include_router(rag_router)
    app.include_router(admin_router)
    app.include_router(monitoring_router)

    @app.get("/")
    async def root():
        return RedirectResponse(url="/dashboard")

    @app.get("/login_abstract.png")
    async def get_login_image():
        return FileResponse(Path(__file__).parent / "frontend" / "login_abstract.png")

    @app.get("/chat")
    async def chat_ui():
        html_path = Path(__file__).parent / "frontend" / "index.html"
        return FileResponse(html_path, media_type="text/html")

    @app.get("/dashboard")
    async def dashboard_ui():
        html_path = Path(__file__).parent / "frontend" / "dashboard.html"
        return FileResponse(html_path, media_type="text/html")

    @app.get("/policies")
    async def policies_ui():
        html_path = Path(__file__).parent / "frontend" / "policies.html"
        return FileResponse(html_path, media_type="text/html")

    @app.get("/documents")
    async def documents_ui():
        html_path = Path(__file__).parent / "frontend" / "documents.html"
        return FileResponse(html_path, media_type="text/html")

    @app.get("/compliance")
    async def compliance_ui():
        html_path = Path(__file__).parent / "frontend" / "compliance.html"
        return FileResponse(html_path, media_type="text/html")

    @app.get("/audit-logs")
    async def audit_logs_ui():
        html_path = Path(__file__).parent / "frontend" / "audit_logs.html"
        return FileResponse(html_path, media_type="text/html")

    @app.get("/team-access")
    async def team_access_ui():
        html_path = Path(__file__).parent / "frontend" / "team_access.html"
        return FileResponse(html_path, media_type="text/html")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.on_event("startup")
    async def on_startup():
        setup_logging()
        init_db()
        logger.info("%s v%s started (env=%s, db=MongoDB)", __app_name__, __version__, settings.APP_ENV)

    @app.on_event("shutdown")
    async def on_shutdown():
        close_db()
        logger.info("Application shutdown – MongoDB connection closed")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
