"""
Pydantic schemas – request / response models for the API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


# ── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field(default="employee")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


# ── RAG / Query ─────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000, description="User's question")
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    model: str
    usage: dict[str, Any] = {}
    latency_ms: float


# ── Documents ───────────────────────────────────────────────────────────────

class DocumentInfo(BaseModel):
    id: str
    filename: str
    extension: str
    hash: str
    chunk_count: int = 0


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    total: int


# ── Users / Roles ───────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    roles: list[str]
    is_active: bool


class RoleAssignRequest(BaseModel):
    username: str
    role_name: str


# ── Monitoring ──────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    issues: list[str] = []
    total_requests: int = 0
    total_cost_usd: float = 0.0
    timestamp: str


class DashboardResponse(BaseModel):
    generated_at: str
    cost: dict[str, Any]
    latency: dict[str, Any]
    recent_usage: list[dict[str, Any]]


# ── Generic ─────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    detail: str | None = None
