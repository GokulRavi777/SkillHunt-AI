"""LangChain Google GenAI LLM factory for VANI 2.0."""

from __future__ import annotations

import os
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI


def create_gemini_llm(
    *,
    model: str = "gemini-3.5-flash-lite",
    api_key: str | None = None,
    temperature: float = 0.7,
    max_tokens: int | None = 1000,
    **kwargs: Any,
) -> ChatGoogleGenerativeAI:
    """Initialize Gemini using LangChain Google GenAI integration.

    Args:
        model: Exact model name to use. Defaults to 'gemini-3.5-flash-lite'.
        api_key: Optional Gemini API key. Defaults to GEMINI_API_KEY or GOOGLE_API_KEY.
        temperature: Sampling temperature for generation.
        max_tokens: Maximum tokens in response.
        **kwargs: Additional parameters for ChatGoogleGenerativeAI.

    Returns:
        ChatGoogleGenerativeAI instance.
    """
    resolved_key = (
        api_key
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )

    if not resolved_key or not resolved_key.strip():
        raise ValueError(
            "Gemini API key is required. Set GEMINI_API_KEY or GOOGLE_API_KEY in your environment."
        )

    if not model or not model.strip():
        raise ValueError("Gemini model name cannot be empty.")

    # Preserve exact requested model, do not silently substitute
    return ChatGoogleGenerativeAI(
        model=model.strip(),
        google_api_key=resolved_key.strip(),
        temperature=temperature,
        max_output_tokens=max_tokens,
        **kwargs,
    )
