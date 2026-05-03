"""
Document loader – load PDF and TXT files into raw text.
Supports loading documents from the MongoDB `documents` collection.
"""

from __future__ import annotations

import logging
import io
import hashlib
from pathlib import Path
from typing import Any

from core.database import get_database

logger = logging.getLogger(__name__)


def load_txt_content(content: bytes) -> str:
    """Read a plain-text file content and return its string."""
    return content.decode("utf-8", errors="replace")


def load_pdf_content(content: bytes) -> str:
    """
    Extract text from a PDF bytes using PyPDF2.
    Falls back to empty string per page on extraction errors.
    """
    try:
        from PyPDF2 import PdfReader
    except ImportError as exc:
        raise ImportError(
            "PyPDF2 is required for PDF loading. Install it with: pip install PyPDF2"
        ) from exc

    reader = PdfReader(io.BytesIO(content))
    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
            pages.append(text)
        except Exception:
            logger.warning("Could not extract text from a page")
            pages.append("")
    return "\n\n".join(pages)


LOADERS = {
    ".txt": load_txt_content,
    ".md": load_txt_content,
    ".pdf": load_pdf_content,
}


def file_hash_bytes(content: bytes, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    h.update(content)
    return h.hexdigest()


def load_all_documents(directory: Path | str | None = None) -> list[dict[str, Any]]:
    """
    Fetch all documents from MongoDB and extract text.
    (directory argument is kept for compatibility but ignored)
    """
    db = get_database()
    docs: list[dict[str, Any]] = []
    
    for doc in db["documents"].find():
        filename = doc.get("filename", "")
        content = doc.get("content")
        
        if not content:
            continue
            
        ext = Path(filename).suffix.lower()
        loader = LOADERS.get(ext)
        
        if loader is None:
            logger.warning(f"Unsupported file type: {ext} for {filename}")
            continue

        try:
            text = loader(content)
            docs.append({
                "id": doc["_id"],
                "filename": filename,
                "extension": ext,
                "hash": file_hash_bytes(content),
                "text": text,
            })
            logger.info("Loaded: %s", filename)
        except Exception as exc:
            logger.error("Failed to load %s: %s", filename, exc)
            
    logger.info("Total documents loaded from MongoDB: %d", len(docs))
    return docs
