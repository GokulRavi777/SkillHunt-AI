"""Unit tests for LangChain and MCP orchestration."""

from __future__ import annotations

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from examples.vani_interview.orchestration.conversation import ConversationManager
from examples.vani_interview.orchestration.llm import create_gemini_llm
from examples.vani_interview.orchestration.mcp_client import create_mcp_client
from langchain_core.messages import AIMessage


def test_create_gemini_llm_missing_key():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Gemini API key is required"):
            create_gemini_llm()


def test_create_gemini_llm_empty_model():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"}):
        with pytest.raises(ValueError, match="Gemini model name cannot be empty"):
            create_gemini_llm(model="")


def test_create_gemini_llm_valid():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"}):
        llm = create_gemini_llm(model="gemini-3.5-flash-lite")
        assert llm.model == "gemini-3.5-flash-lite"


def test_create_mcp_client_stdio():
    client = create_mcp_client(transport="stdio")
    assert client is not None


def test_create_mcp_client_sse():
    client = create_mcp_client(transport="sse", server_url="http://127.0.0.1:8000/sse")
    assert client is not None


@pytest.mark.asyncio
async def test_conversation_manager_reset():
    manager = ConversationManager(model="gemini-3.5-flash-lite")
    manager.reset()
    assert len(manager.messages) == 2
    assert manager.active_skill == "Python"
    assert manager.active_difficulty == "Beginner"
    assert manager.asked_question_ids == []
    assert manager.recorded_responses == []


@pytest.mark.asyncio
async def test_conversation_manager_process_empty_turn():
    manager = ConversationManager(model="gemini-3.5-flash-lite")
    manager._initialized = True
    reply = await manager.process_turn("")
    assert "listening" in reply.lower()
