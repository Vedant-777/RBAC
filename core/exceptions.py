"""
Custom exception types for the application.
Each exception maps to a specific HTTP status code via the global handler
registered in main.py.
"""

from __future__ import annotations


class AppException(Exception):
    """Base exception for IntelliFusion."""

    def __init__(self, message: str = "An unexpected error occurred", status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


# ── Authentication / Authorisation ──────────────────────────────────────────
class AuthenticationError(AppException):
    """Raised when credentials are missing or invalid."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message=message, status_code=401)


class AuthorisationError(AppException):
    """Raised when the user lacks the required role / permission."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, status_code=403)


# ── RAG pipeline ────────────────────────────────────────────────────────────
class DocumentNotFoundError(AppException):
    """Raised when a requested document or chunk cannot be located."""

    def __init__(self, message: str = "Document not found"):
        super().__init__(message=message, status_code=404)


class EmbeddingError(AppException):
    """Raised when embedding generation fails."""

    def __init__(self, message: str = "Failed to generate embeddings"):
        super().__init__(message=message, status_code=502)


class GenerationError(AppException):
    """Raised when the LLM call fails."""

    def __init__(self, message: str = "LLM generation failed"):
        super().__init__(message=message, status_code=502)


# ── Guardrails ──────────────────────────────────────────────────────────────
class GuardrailViolation(AppException):
    """Raised when input or output fails a guardrail check."""

    def __init__(self, message: str = "Content blocked by guardrail"):
        super().__init__(message=message, status_code=422)


class PIIDetectedError(GuardrailViolation):
    """Raised when PII is detected in input."""

    def __init__(self, message: str = "PII detected in input – blocked"):
        super().__init__(message=message)


class OutOfScopeError(GuardrailViolation):
    """Raised when the query is outside the allowed scope."""

    def __init__(self, message: str = "Query is out of scope"):
        super().__init__(message=message)
