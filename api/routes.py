"""
Routes – FastAPI route definitions (MongoDB version).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import os
import shutil
from pymongo.database import Database

from .dependencies import get_current_user, get_current_user_payload, require_roles
from .schemas import (
    DashboardResponse,
    HealthResponse,
    LoginRequest,
    MessageResponse,
    QueryRequest,
    QueryResponse,
    RegisterRequest,
    RoleAssignRequest,
    TokenResponse,
    UserResponse,
)
from core.database import get_db
from core.exceptions import GuardrailViolation
from monitoring.dashboard_data import get_dashboard_data, get_health_status
from rbac.auth import login, register_user
from rbac.models import get_user_role_names
from rbac.permissions import get_allowed_doc_ids
from rag.pipeline import ask

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
rag_router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])
admin_router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])
monitoring_router = APIRouter(prefix="/api/v1/monitoring", tags=["Monitoring"])


# ═══════════════════════════════════════════════════════════════════════════
# AUTH ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@auth_router.post("/login", response_model=TokenResponse)
def api_login(body: LoginRequest, db: Database = Depends(get_db)):
    result = login(db, body.username, body.password)
    return result


@auth_router.post("/register", response_model=MessageResponse)
def api_register(body: RegisterRequest, db: Database = Depends(get_db)):
    logger.info("Registration request: username=%s, role=%s", body.username, body.role)
    if body.role not in ["admin", "manager", "employee", "intern"]:
        raise HTTPException(status_code=400, detail="Invalid role for public registration")
    register_user(db, body.username, body.email, body.password, role_name=body.role)
    return MessageResponse(message="Registration successful")


@auth_router.get("/me", response_model=UserResponse)
def api_me(user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    role_names = get_user_role_names(user, db["roles"])
    return UserResponse(
        id=user["_id"], username=user["username"], email=user["email"],
        roles=role_names, is_active=user.get("is_active", True),
    )


# ═══════════════════════════════════════════════════════════════════════════
# RAG ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@rag_router.post("/query", response_model=QueryResponse)
def api_query(
    body: QueryRequest,
    payload: dict[str, Any] = Depends(get_current_user_payload),
    db: Database = Depends(get_db),
):
    user_roles = payload.get("roles", [])
    allowed_docs = get_allowed_doc_ids(db, user_roles)
    try:
        result = ask(query=body.query, user_role=user_roles[0] if user_roles else "unknown", allowed_doc_ids=allowed_docs)
    except GuardrailViolation as exc:
        logger.warning("Guardrail blocked query: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("RAG pipeline error: %s", exc)
        # Extract clean error message for the user
        err_str = str(exc)
        if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "503" in err_str:
            detail = "The AI service is temporarily overloaded. Please wait a moment and try again."
            status = 429
        elif "quota" in err_str.lower():
            detail = "API quota exceeded. Please try again later."
            status = 429
        else:
            detail = "An error occurred while processing your query. Please try again."
            status = 502
        raise HTTPException(status_code=status, detail=detail)
    return QueryResponse(
        answer=result["answer"], sources=result["sources"], model=result["model"],
        usage=result.get("usage", {}), latency_ms=result["latency_ms"],
    )


@rag_router.get("/documents")
def api_list_docs(payload: dict = Depends(get_current_user_payload), db: Database = Depends(get_db)):
    from core.utils import generate_id, utc_now
    roles = payload.get("roles", [])
    allowed_ids = get_allowed_doc_ids(db, roles)
    
    docs = list(db["documents"].find({}, {"content": 0}))
        
    return [{"id": d["_id"], "name": d["filename"]} for d in docs]


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@admin_router.get("/users", response_model=list[UserResponse], dependencies=[Depends(require_roles("admin"))])
def api_list_users(db: Database = Depends(get_db)):
    users = list(db["users"].find())
    result = []
    for u in users:
        role_names = get_user_role_names(u, db["roles"])
        result.append(UserResponse(
            id=u["_id"], username=u["username"], email=u["email"],
            roles=role_names, is_active=u.get("is_active", True),
        ))
    return result


@admin_router.post("/assign-role", response_model=MessageResponse, dependencies=[Depends(require_roles("admin"))])
def api_assign_role(body: RoleAssignRequest, db: Database = Depends(get_db)):
    user = db["users"].find_one({"username": body.username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role = db["roles"].find_one({"name": body.role_name})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role["_id"] not in user.get("role_ids", []):
        db["users"].update_one({"_id": user["_id"]}, {"$addToSet": {"role_ids": role["_id"]}})
    return MessageResponse(message=f"Role '{body.role_name}' assigned to '{body.username}'")


@admin_router.post("/documents", dependencies=[Depends(require_roles("admin"))])
def api_upload_doc(file: UploadFile = File(...), db: Database = Depends(get_db)):
    from core.utils import generate_id, utc_now
    from rag.pipeline import ingest_single_document
    
    content = file.file.read()
    
    doc_id = generate_id()
    existing_doc = db["documents"].find_one({"filename": file.filename})
    
    if not existing_doc:
        db["documents"].insert_one({
            "_id": doc_id,
            "filename": file.filename,
            "content": content,
            "uploaded_at": utc_now()
        })
    else:
        doc_id = existing_doc["_id"]
        db["documents"].update_one(
            {"_id": doc_id},
            {"$set": {"content": content, "uploaded_at": utc_now()}}
        )
    
    # Automatically ingest into the FAISS vector index
    try:
        chunks_added = ingest_single_document(doc_id, file.filename, content)
        logger.info("Ingested %s into vector store: %d chunks", file.filename, chunks_added)
    except Exception as exc:
        logger.error("Failed to ingest %s into vector store: %s", file.filename, exc)
        # Don't fail the upload – document is saved in MongoDB and can be re-indexed later
        
    return {"message": "Document uploaded and indexed successfully", "doc_id": doc_id}


@admin_router.delete("/documents/{doc_id}", dependencies=[Depends(require_roles("admin"))])
def api_delete_doc(doc_id: str, db: Database = Depends(get_db)):
    from rag.pipeline import get_vector_store
    
    result = db["documents"].delete_one({"_id": doc_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Also remove from FAISS index
    try:
        store = get_vector_store()
        removed = store.delete_by_doc_id(doc_id)
        if removed:
            store.save()
            logger.info("Removed %d vectors for doc_id=%s from index", removed, doc_id)
    except Exception as exc:
        logger.error("Failed to remove doc from vector store: %s", exc)
    
    return {"message": "Document deleted successfully"}


@admin_router.post("/reindex", dependencies=[Depends(require_roles("admin"))])
def api_reindex():
    """Rebuild the entire FAISS vector index from all MongoDB documents."""
    from rag.pipeline import rebuild_vector_store
    try:
        store = rebuild_vector_store()
        return {"message": f"Re-index complete. {store.count} vectors in index."}
    except Exception as exc:
        logger.error("Re-index failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Re-index failed: {exc}")


# ═══════════════════════════════════════════════════════════════════════════
# MONITORING ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@monitoring_router.get("/health", response_model=HealthResponse)
def api_health():
    return get_health_status()


@monitoring_router.get("/dashboard", response_model=DashboardResponse, dependencies=[Depends(require_roles("admin", "manager"))])
def api_dashboard():
    return get_dashboard_data()
