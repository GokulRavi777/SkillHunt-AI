"""Tests for Language Enforcement Guardrail (Strictly English Only)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock
import pytest
from dotenv import load_dotenv

from examples.vani_interview.orchestration.conversation import (
    NON_ENGLISH_WARNING,
    ConversationManager,
)

load_dotenv("d:/Downloads/agents/examples/vani_interview/.env")


@pytest.fixture
def conversation_manager() -> ConversationManager:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "mock_key"
    return ConversationManager(api_key=api_key)


def test_is_non_english_native_scripts(conversation_manager: ConversationManager) -> None:
    # Hindi (Devanagari)
    assert conversation_manager.is_non_english("नमस्ते क्या आप मुझे सुन सकते हैं?")
    # Tamil
    assert conversation_manager.is_non_english("வணக்கம் நான் தமிழில் பேசுகிறேன்")
    # Telugu
    assert conversation_manager.is_non_english("నమస్కారం ఎలా ఉన్నారు?")


def test_is_non_english_romanized(conversation_manager: ConversationManager) -> None:
    # Romanized Hindi (Hinglish)
    assert conversation_manager.is_non_english("mujhe nahi pata kya bol rahe ho")
    assert conversation_manager.is_non_english("aapka naam kya hai")
    assert conversation_manager.is_non_english("theek hai bhai bolo")

    # Romanized Tamil (Tanglish)
    assert conversation_manager.is_non_english("enna solreenga enakku puriyala")
    assert conversation_manager.is_non_english("vanakkam romba nandri")
    assert conversation_manager.is_non_english("theriyathu")


def test_is_non_english_language_switch_request(conversation_manager: ConversationManager) -> None:
    assert conversation_manager.is_non_english("Can we speak in Hindi?")
    assert conversation_manager.is_non_english("Please speak Tamil")
    assert conversation_manager.is_non_english("Can you explain this in Hindi?")


def test_is_english_valid(conversation_manager: ConversationManager) -> None:
    # Valid candidate utterances in English should NOT trigger the non-English guardrail
    assert not conversation_manager.is_non_english("Hello! I am ready to begin.")
    assert not conversation_manager.is_non_english("In Python, lists are mutable while tuples are immutable.")
    assert not conversation_manager.is_non_english("Can you please repeat the question?")
    assert not conversation_manager.is_non_english("Wait a second, please hold on for a minute.")
    assert not conversation_manager.is_non_english("I don't know the answer to this question.")


@pytest.mark.asyncio
async def test_process_turn_enforces_english(conversation_manager: ConversationManager) -> None:
    await conversation_manager.initialize()
    conversation_manager.bind_session("cand_test", "room_test")

    # When candidate speaks Hindi
    response_hindi = await conversation_manager.process_turn("kya aap hindi me baat kar sakte ho?")
    assert response_hindi == NON_ENGLISH_WARNING
    # Assessment should remain awaiting readiness, 0 questions fetched
    assert len(conversation_manager.asked_question_ids) == 0

    # When candidate speaks Tamil
    response_tamil = await conversation_manager.process_turn("enna solreenga puriyala")
    assert response_tamil == NON_ENGLISH_WARNING
    assert len(conversation_manager.asked_question_ids) == 0
