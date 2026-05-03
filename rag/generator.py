"""
Generator – LLM call + prompt construction.
Sends the retrieved context and user query to the LLM and returns the answer.
Supports both OpenAI and Google Gemini as LLM providers.
"""

from __future__ import annotations

import logging
import time as _time
from typing import Any

from core.config import get_settings
from core.exceptions import GenerationError
from monitoring.cost_tracker import record_usage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are IntelliFusion, an enterprise AI assistant.
Answer the user's question based on the context provided below.
If the user asks a broad question like what something is, synthesize the available context to provide a helpful overview.
If the context contains absolutely no relevant information to answer the question, say "Access Blocked / Information Not Found. I don't have enough information to answer that. Note: Your current role permissions may restrict you from accessing confidential documents containing this information."
Be concise, accurate, and professional.

Context:
{context}
"""


def build_prompt(context_chunks: list[dict[str, Any]], query: str) -> tuple[str, str]:
    """
    Assemble the system instruction and user query.
    Returns (system_instruction, user_query).
    """
    context_text = "\n\n---\n\n".join(
        f"[Source: {c.get('filename', 'unknown')}]\n{c.get('text', '')}"
        for c in context_chunks
    )

    system_instruction = SYSTEM_PROMPT.format(context=context_text)
    logger.info(f"--- RAG PROMPT START ---\n{system_instruction}\n--- RAG PROMPT END ---")
    return system_instruction, query


def _generate_openai(
    system_instruction: str,
    user_query: str,
    temperature: float,
) -> dict[str, Any]:
    """Generate using OpenAI API (GPT-4o-mini, GPT-4o, etc.)."""
    settings = get_settings()

    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    max_retries = 3
    response = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_query},
                ],
                temperature=temperature,
                max_tokens=1024,
            )
            break
        except Exception as retry_exc:
            err_str = str(retry_exc)
            if attempt < max_retries and ("429" in err_str or "rate" in err_str.lower() or "503" in err_str or "500" in err_str):
                wait_time = 2 ** (attempt + 1)
                logger.warning("Service overloaded (attempt %d/%d), retrying in %ds...", attempt + 1, max_retries, wait_time)
                _time.sleep(wait_time)
            else:
                raise

    if response is None:
        raise GenerationError("LLM generation failed after retries")

    answer_text = response.choices[0].message.content or ""
    usage = {
        "prompt_tokens": response.usage.prompt_tokens or 0,
        "completion_tokens": response.usage.completion_tokens or 0,
        "total_tokens": response.usage.total_tokens or 0,
    }

    return {"answer": answer_text, "model": settings.LLM_MODEL, "usage": usage}


def _generate_gemini(
    system_instruction: str,
    user_query: str,
    temperature: float,
) -> dict[str, Any]:
    """Generate using Google Gemini API."""
    settings = get_settings()

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    max_retries = 3
    response = None
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=user_query,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=temperature,
                    max_output_tokens=1024,
                ),
            )
            break
        except Exception as retry_exc:
            err_str = str(retry_exc)
            if attempt < max_retries and ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "503" in err_str or "UNAVAILABLE" in err_str or "500" in err_str):
                wait_time = 2 ** (attempt + 1)
                logger.warning("Service overloaded (attempt %d/%d), retrying in %ds...", attempt + 1, max_retries, wait_time)
                _time.sleep(wait_time)
            else:
                raise

    if response is None:
        raise GenerationError("LLM generation failed after retries")

    answer_text = response.text or ""
    usage_meta = getattr(response, "usage_metadata", None)
    if usage_meta:
        usage = {
            "prompt_tokens": getattr(usage_meta, "prompt_token_count", 0) or 0,
            "completion_tokens": getattr(usage_meta, "candidates_token_count", 0) or 0,
            "total_tokens": getattr(usage_meta, "total_token_count", 0) or 0,
        }
    else:
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    return {"answer": answer_text, "model": settings.LLM_MODEL, "usage": usage}


def _generate_groq(
    system_instruction: str,
    user_query: str,
    temperature: float,
) -> dict[str, Any]:
    """Generate using Groq API (OpenAI-compatible)."""
    settings = get_settings()

    from openai import OpenAI

    client = OpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )

    max_retries = 3
    response = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_query},
                ],
                temperature=temperature,
                max_tokens=1024,
            )
            break
        except Exception as retry_exc:
            err_str = str(retry_exc)
            if attempt < max_retries and ("429" in err_str or "rate" in err_str.lower() or "503" in err_str or "500" in err_str):
                wait_time = 2 ** (attempt + 1)
                logger.warning("Groq service overloaded (attempt %d/%d), retrying in %ds...", attempt + 1, max_retries, wait_time)
                _time.sleep(wait_time)
            else:
                raise

    if response is None:
        raise GenerationError("Groq generation failed after retries")

    answer_text = response.choices[0].message.content or ""
    usage = {
        "prompt_tokens": response.usage.prompt_tokens or 0,
        "completion_tokens": response.usage.completion_tokens or 0,
        "total_tokens": response.usage.total_tokens or 0,
    }

    return {"answer": answer_text, "model": settings.LLM_MODEL, "usage": usage}


def generate(
    context_chunks: list[dict[str, Any]],
    query: str,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """
    Call the LLM and return::

        {
            "answer": "…",
            "model": "gpt-4o-mini",
            "usage": {"prompt_tokens": …, "completion_tokens": …, "total_tokens": …},
        }
    """
    settings = get_settings()
    system_instruction, user_query = build_prompt(context_chunks, query)

    try:
        if settings.LLM_PROVIDER == "openai":
            result = _generate_openai(system_instruction, user_query, temperature)
        elif settings.LLM_PROVIDER == "groq":
            result = _generate_groq(system_instruction, user_query, temperature)
        else:
            result = _generate_gemini(system_instruction, user_query, temperature)
    except GenerationError:
        raise
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        raise GenerationError(f"LLM generation error: {exc}") from exc

    # Track cost
    record_usage(
        model=result["model"],
        prompt_tokens=result["usage"]["prompt_tokens"],
        completion_tokens=result["usage"]["completion_tokens"],
    )

    logger.info("Generated answer (%d tokens) using model=%s provider=%s",
                result["usage"]["total_tokens"], result["model"], settings.LLM_PROVIDER)
    return result
