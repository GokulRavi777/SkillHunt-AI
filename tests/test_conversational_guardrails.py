"""Comprehensive tests for the 10 Conversational Behaviour Guardrails in VANI 2.0."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock
import pytest
from dotenv import load_dotenv

from examples.vani_interview.mcp_server.data import InMemorySessionStore
from examples.vani_interview.mcp_server.server import repeat_active_question
from examples.vani_interview.orchestration.conversation import (
    NO_COACHING_RESPONSE,
    OFF_TOPIC_BOUNDARY_RESPONSE,
    REPEAT_LIMIT_REACHED_RESPONSE,
    ConversationManager,
)

load_dotenv("d:/Downloads/agents/examples/vani_interview/.env")


@pytest.fixture
def conversation_manager() -> ConversationManager:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "mock_key"
    return ConversationManager(api_key=api_key)


def test_no_answer_coaching_detection(conversation_manager: ConversationManager) -> None:
    """Guardrail 2: No answer coaching or revealing expected answers."""
    assert conversation_manager.is_coaching_or_answer_request("What is the answer?")
    assert conversation_manager.is_coaching_or_answer_request("Can you tell me the answer?")
    assert conversation_manager.is_coaching_or_answer_request("Give me the solution please")
    assert conversation_manager.is_coaching_or_answer_request("What should I say to this?")
    assert not conversation_manager.is_coaching_or_answer_request("I think lists are mutable in Python.")


def test_candidate_request_boundaries_detection(conversation_manager: ConversationManager) -> None:
    """Guardrail 7: Candidate request boundaries (off-topic redirection)."""
    assert conversation_manager.is_off_topic_or_boundary_request("What is the weather today?")
    assert conversation_manager.is_off_topic_or_boundary_request("Tell me a joke")
    assert conversation_manager.is_off_topic_or_boundary_request("Who is the prime minister?")
    assert conversation_manager.is_off_topic_or_boundary_request("How old are you?")
    assert not conversation_manager.is_off_topic_or_boundary_request("Can you please repeat the question?")


def test_repetition_detection(conversation_manager: ConversationManager) -> None:
    """Guardrail 6: Repetition request detection."""
    assert conversation_manager.is_repeat_request("Can you repeat the question?")
    assert conversation_manager.is_repeat_request("Could you say that again?")
    assert conversation_manager.is_repeat_request("Pardon, I didn't hear you")
    assert not conversation_manager.is_repeat_request("Yes, I am ready to begin.")


@pytest.mark.asyncio
async def test_coaching_request_intercepted(conversation_manager: ConversationManager) -> None:
    """Guardrail 2: Direct turn interception when candidate asks for answers."""
    await conversation_manager.initialize()
    conversation_manager.bind_session("cand_test", "room_test")
    conversation_manager.last_asked_question = "What is a list in Python?"

    response = await conversation_manager.process_turn("What is the answer?")
    assert response == NO_COACHING_RESPONSE
    # 0 questions should be fetched or advanced
    assert len(conversation_manager.asked_question_ids) == 0


@pytest.mark.asyncio
async def test_off_topic_request_intercepted(conversation_manager: ConversationManager) -> None:
    """Guardrail 7: Direct turn interception when candidate asks off-topic questions."""
    await conversation_manager.initialize()
    conversation_manager.bind_session("cand_test", "room_test")

    response = await conversation_manager.process_turn("What is the weather outside?")
    assert response == OFF_TOPIC_BOUNDARY_RESPONSE


@pytest.mark.asyncio
async def test_repetition_limits_enforced(conversation_manager: ConversationManager) -> None:
    """Guardrail 6: Repetition limit capped at 2 times per question."""
    await conversation_manager.initialize()
    conversation_manager.bind_session("cand_test", "room_test")
    q_text = "What is the difference between a mutable and an immutable data type in Python?"
    conversation_manager.last_asked_question = q_text
    conversation_manager.question_repeat_count = 0

    # Repeat 1
    resp_1 = await conversation_manager.process_turn("Could you repeat that?")
    assert q_text in resp_1
    assert conversation_manager.question_repeat_count == 1

    # Repeat 2
    resp_2 = await conversation_manager.process_turn("Sorry, can you say that again?")
    assert q_text in resp_2
    assert conversation_manager.question_repeat_count == 2

    # Repeat 3 (Limit exceeded)
    resp_3 = await conversation_manager.process_turn("Please repeat once more")
    assert resp_3 == REPEAT_LIMIT_REACHED_RESPONSE
    assert conversation_manager.question_repeat_count == 2


def test_session_store_repetition_and_clarification_limits() -> None:
    """Guardrail 6: State-level tracking of repeats and clarifications."""
    store = InMemorySessionStore()
    store.record_question("py_beg_1", "What is mutability in Python?")
    assert store.can_repeat_question()
    assert store.record_question_repeat()  # count = 1
    assert store.can_repeat_question()
    assert store.record_question_repeat()  # count = 2
    assert not store.can_repeat_question()
    assert not store.record_question_repeat()  # rejected

    # Clarifications
    assert store.can_clarify_question()
    assert store.record_question_clarification()  # count = 1
    assert not store.can_clarify_question()


def test_conversational_behaviour_prompts_configured() -> None:
    """Guardrails 1, 3, 4, 5, 8, 9, 10: Verify prompt coverage for conversational rules."""
    from examples.vani_interview.orchestration.prompts import ORCHESTRATION_SYSTEM_PROMPT
    from examples.vani_interview.prompts import VANI_SYSTEM_PROMPT

    # 1. Neutral acknowledgement
    assert "Neutral Acknowledgement" in ORCHESTRATION_SYSTEM_PROMPT
    assert "avoid excessive praise" in VANI_SYSTEM_PROMPT.lower()

    # 3 & 4. Incomplete answer & Vague answer
    assert "Incomplete Answer Detection" in ORCHESTRATION_SYSTEM_PROMPT
    assert "Vague Answer Clarification" in ORCHESTRATION_SYSTEM_PROMPT

    # 5. No leading questions
    assert "No Leading Questions" in ORCHESTRATION_SYSTEM_PROMPT
    assert "no leading questions" in VANI_SYSTEM_PROMPT.lower()

    # 8. No false answer validation
    assert "No False Answer Validation" in ORCHESTRATION_SYSTEM_PROMPT
    assert "no false answer validation" in VANI_SYSTEM_PROMPT.lower()

    # 9. Professional interviewer tone
    assert "Professional Interviewer Tone and Topic Boundaries" in ORCHESTRATION_SYSTEM_PROMPT

    # 10. Prevent premature question advancement
    assert "Prevent Premature Question Advancement" in ORCHESTRATION_SYSTEM_PROMPT
